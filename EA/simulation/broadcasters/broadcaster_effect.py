from _collections import defaultdictfrom collections import Counter, namedtupleimport randomimport weakreffrom autonomy.autonomy_modifier import AutonomyModifierfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.priority import Priorityfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableReference, TunableVariant, OptionalTunable, TunableEnumEntry, Tunable, TunablePercent, TunableList, TunableRange, TunableEnumFlags, TunableTuple, TunableIntervalfrom sims4.utils import classpropertyfrom singletons import DEFAULTimport buffs.tunableimport servicesimport sims4.resources
class TunableBroadcasterEffectVariant(TunableVariant):

    def __init__(self, **kwargs):
        super().__init__(affordance=BroadcasterEffectAffordance.TunableFactory(), buff=BroadcasterEffectBuff.TunableFactory(), statistic_modifier=BroadcasterEffectStatisticModifier.TunableFactory(), self_state_change=BroadcasterEffectSelfStateChange.TunableFactory(), start_fire=BroadcasterEffectStartFire.TunableFactory(), loot=BroadcasterEffectLoot.TunableFactory(), state=BroadcasterEffectStateChange.TunableFactory(), self_buff=BroadcasterEffectSelfBuff.TunableFactory(), self_loot=BroadcasterEffectSelfLoot.TunableFactory(), **kwargs)

class _BroadcasterEffect(AutoFactoryInit, HasTunableSingletonFactory):

    @classproperty
    def apply_when_linked(cls):
        return False

    @classproperty
    def apply_when_removed(cls):
        return False

    def register_static_callbacks(self, broadcaster_request_owner, object_tuning_id=DEFAULT):
        pass

    def _should_apply_broadcaster_effect(self, broadcaster, affected_object):
        return True

    def apply_broadcaster_effect(self, broadcaster, affected_object):
        if self._should_apply_broadcaster_effect(broadcaster, affected_object):
            return self._apply_broadcaster_effect(broadcaster, affected_object)

    def _apply_broadcaster_effect(self, broadcaster, affected_object):
        raise NotImplementedError

    def remove_broadcaster_effect(self, broadcaster, affected_object):
        pass

class _BroadcasterEffectTested(_BroadcasterEffect):
    FACTORY_TUNABLES = {'tests': TunableTestSet(description='\n            Tests that must pass in order for the broadcaster effect to be\n            applied.\n            '), 'excluded_participants': OptionalTunable(description='\n            If enabled, these participants will be excluded from this broadcaster effect.\n            ', tunable=TunableEnumFlags(description='\n                A set of Participants that will be excluded from having this effect\n                applied to them. If the broadcaster comes from an interaction,\n                these participants will come from that interaction.\n                ', enum_type=ParticipantType, default=ParticipantType.Actor | ParticipantType.TargetSim))}

    def _should_apply_broadcaster_effect(self, broadcaster, affected_object):
        if broadcaster.interaction is not None and self.excluded_participants is not None:
            participants = broadcaster.interaction.get_participants(self.excluded_participants)
            if affected_object in participants:
                return False
            if affected_object.sim_info is not None and affected_object.sim_info in participants:
                return False
        resolver = broadcaster.get_resolver(affected_object)
        if not self.tests.run_tests(resolver):
            return False
        return super()._should_apply_broadcaster_effect(broadcaster, affected_object)

class _BroadcasterEffectTestedOneShot(_BroadcasterEffectTested):
    FACTORY_TUNABLES = {'affected_object_cap': OptionalTunable(description='\n            If enabled, specify the maximum number of objects that can\n            be affected by this particular effect, per broadcaster. This\n            is a soft- cap, since the data does not persist across\n            multiple broadcaster requests nor save games.\n            ', tunable=TunableRange(description='\n                The maximum number of objects that can be affected by\n                this broadcaster.\n                ', tunable_type=int, minimum=1, default=1))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._object_counter = weakref.WeakKeyDictionary()

    def _should_apply_broadcaster_effect(self, broadcaster, affected_object):
        result = super()._should_apply_broadcaster_effect(broadcaster, affected_object)
        if not result:
            return result
        if self.affected_object_cap is not None:
            if broadcaster not in self._object_counter:
                self._object_counter[broadcaster] = 0
            if self._object_counter[broadcaster] >= self.affected_object_cap:
                return False
            self._object_counter[broadcaster] += 1
        return result

class BroadcasterEffectBuff(_BroadcasterEffectTested):
    FACTORY_TUNABLES = {'buff': buffs.tunable.TunableBuffReference(description='\n            The buff to apply while the broadcaster actively affects the Sim.\n            '), 'remove_buff': Tunable(description='\n            If enabled, the buff is automatically cleared on broadcaster\n            ends. If disabled, the buff will remain.\n            ', tunable_type=bool, default=True)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._buff_handles = {}

    @classproperty
    def apply_when_linked(cls):
        return True

    def _apply_broadcaster_effect(self, broadcaster, affected_object):
        if not affected_object.is_sim:
            return
        key = (affected_object.id, broadcaster.broadcaster_id)
        if key not in self._buff_handles:
            if self.remove_buff:
                handle_id = affected_object.add_buff(self.buff.buff_type, buff_reason=self.buff.buff_reason)
                if handle_id:
                    self._buff_handles[key] = handle_id
            else:
                affected_object.add_buff_from_op(self.buff.buff_type, buff_reason=self.buff.buff_reason)

    def remove_broadcaster_effect(self, broadcaster, affected_object):
        if not affected_object.is_sim:
            return
        key = (affected_object.id, broadcaster.broadcaster_id)
        if key in self._buff_handles:
            affected_object.remove_buff(self._buff_handles[key])
            del self._buff_handles[key]
RandomStateKey = namedtuple('RandomStateKey', ('object_id', 'state'))
class BroadcasterEffectStateChange(_BroadcasterEffectTested):
    FACTORY_TUNABLES = {'state_change_on_enter': TunableList(description='\n            A list of states to randomize between every time an object enters\n            the broadcaster, or the broadcaster pulses.\n            ', tunable=TunableReference(description='\n                A state value to randomly consider setting on objects that\n                enter this broadcaster.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',)), minlength=1), 'state_change_on_exit': TunableReference(description='\n            The state change to apply the the object stops being affected.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._state_ref_counts = Counter()
        self._broadcaster_object_dict = defaultdict(list)

    @classproperty
    def apply_when_linked(cls):
        return True

    def _get_counter_key(self, object_id):
        return RandomStateKey(object_id=object_id, state=self.state_change_on_exit.state)

    def _has_ref_count(self, broadcaster_id, object_id):
        if broadcaster_id not in self._broadcaster_object_dict:
            return False
        return object_id in self._broadcaster_object_dict[broadcaster_id]

    def _apply_broadcaster_effect(self, broadcaster, affected_object):
        if affected_object.is_sim:
            return
        random_state = random.choice(self.state_change_on_enter)
        broadcaster_id = broadcaster.id
        object_id = affected_object.id
        key = self._get_counter_key(object_id)
        if not self._has_ref_count(broadcaster_id, object_id):
            self._broadcaster_object_dict[broadcaster_id].append(object_id)
            self._state_ref_counts[key] += 1
        affected_object.set_state(random_state.state, random_state)

    def remove_broadcaster_effect(self, broadcaster, affected_object):
        if affected_object.is_sim:
            return
        broadcaster_id = broadcaster.id
        object_id = affected_object.id
        if self._has_ref_count(broadcaster_id, object_id):
            key = self._get_counter_key(object_id)
            self._broadcaster_object_dict[broadcaster_id].remove(object_id)
            if not self._broadcaster_object_dict[broadcaster_id]:
                del self._broadcaster_object_dict[broadcaster_id]
            self._state_ref_counts[key] -= 1
            if not self._state_ref_counts[key]:
                affected_object.set_state(self.state_change_on_exit.state, self.state_change_on_exit)
                del self._state_ref_counts[key]

class BroadcasterEffectAffordance(_BroadcasterEffectTestedOneShot):
    FACTORY_TUNABLES = {'affordances': TunableList(description='\n            A list of affordances to choose from to push as a result of the\n            broadcaster.\n            ', tunable=TunableTuple(description='\n                A tuple of affordance to push and weight for how likely the\n                affordance is to be picked.\n                ', affordance=TunableReference(description='\n                    The affordance to push on Sims affected by the broadcaster.\n                    ', manager=services.affordance_manager(), pack_safe=True), weight=TunableRange(description='\n                    How likely this affordance is to be picked.\n                    ', tunable_type=int, minimum=1, default=1))), 'affordance_target': OptionalTunable(description='\n            If enabled, the pushed interaction will target a specified\n            participant.\n            ', tunable=TunableEnumEntry(description='\n                The participant to be targeted by the pushed interaction.\n                ', tunable_type=ParticipantType, default=ParticipantType.Object), enabled_by_default=True), 'affordance_priority': TunableEnumEntry(description='\n            The priority at which the specified affordance is to be pushed.\n            ', tunable_type=Priority, default=Priority.Low), 'affordance_run_priority': OptionalTunable(description="\n            If enabled, specify the priority at which the affordance runs. This\n            may be different than 'affordance_priority'. For example. you might\n            want an affordance to push at high priority such that it cancels\n            existing interactions, but it runs at a lower priority such that it\n            can be more easily canceled.\n            ", tunable=TunableEnumEntry(description='\n                The run priority for the specified affordance.\n                ', tunable_type=Priority, default=Priority.Low)), 'affordance_must_run_next': Tunable(description="\n            If set, the affordance will be inserted at the beginning of the\n            Sim's queue.\n            ", tunable_type=bool, default=False), 'actor_can_violate_privacy_from_owning_interaction': Tunable(description='\n            If enabled, the actor of the pushed affordance will be allowed to\n            violate the privacy region from the owning interaction. If\n            disabled, the actor of the pushed affordance will not be able to\n            violate the privacy region created by the owning interaction.\n            ', tunable_type=bool, default=True)}

    def register_static_callbacks(self, broadcaster_request_owner, object_tuning_id=DEFAULT):
        register_privacy_callback = getattr(broadcaster_request_owner, 'register_sim_can_violate_privacy_callback', None)
        if register_privacy_callback is not None:
            register_privacy_callback(self._on_privacy_violation, object_tuning_id=object_tuning_id)

    def _on_privacy_violation(self, interaction, sim):
        if self.actor_can_violate_privacy_from_owning_interaction:
            (affordance_target, context) = self._get_target_and_context(interaction.get_resolver(), sim)
            for entry in self.affordances:
                if not sim.test_super_affordance(entry.affordance, affordance_target, context):
                    return False
            return True
        return False

    def _get_target_and_context(self, resolver, affected_object):
        affordance_target = resolver.get_participant(self.affordance_target) if self.affordance_target is not None else None
        if affordance_target.is_sim:
            affordance_target = affordance_target.get_sim_instance()
        insert_strategy = QueueInsertStrategy.NEXT if affordance_target is not None and self.affordance_must_run_next else QueueInsertStrategy.LAST
        context = InteractionContext(affected_object, InteractionContext.SOURCE_SCRIPT, self.affordance_priority, run_priority=self.affordance_run_priority, insert_strategy=insert_strategy)
        return (affordance_target, context)

    def _select_and_push_affordance(self, affected_object, target, context):
        weighted_options = [(entry.weight, entry.affordance) for entry in self.affordances]
        if not weighted_options:
            return
        affordance = sims4.random.weighted_random_item(weighted_options)
        affected_object.push_super_affordance(affordance, target, context)

    def _apply_broadcaster_effect(self, broadcaster, affected_object):
        if not affected_object.is_sim:
            return
        if broadcaster.interaction is not None:
            participants = broadcaster.interaction.get_participants(ParticipantType.AllSims)
            if affected_object in participants:
                return
        (affordance_target, context) = self._get_target_and_context(broadcaster.get_resolver(affected_object), affected_object)
        self._select_and_push_affordance(affected_object, affordance_target, context)

class BroadcasterEffectStatisticModifier(_BroadcasterEffectTested):
    FACTORY_TUNABLES = {'statistic': TunableReference(description='\n            The statistic to be affected by the modifier.\n            ', manager=services.statistic_manager()), 'modifier': Tunable(description='\n            The modifier to apply to the tuned statistic.\n            ', tunable_type=float, default=0)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._modifier_handles = {}

    @classproperty
    def apply_when_linked(cls):
        return True

    def _apply_broadcaster_effect(self, broadcaster, affected_object):
        key = (affected_object.id, broadcaster.broadcaster_id)
        if key not in self._modifier_handles:
            autonomy_modifier = AutonomyModifier(statistic_modifiers={self.statistic: self.modifier})
            handle_id = affected_object.add_statistic_modifier(autonomy_modifier)
            if handle_id:
                self._modifier_handles[key] = handle_id

    def remove_broadcaster_effect(self, broadcaster, affected_object):
        key = (affected_object.id, broadcaster.broadcaster_id)
        if key in self._modifier_handles:
            affected_object.remove_statistic_modifier(self._modifier_handles[key])
            del self._modifier_handles[key]

class BroadcasterEffectSelfStateChange(_BroadcasterEffectTested):
    FACTORY_TUNABLES = {'enter_state_value': TunableReference(description='\n            The state value to enter when first object gets close.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue'), 'exit_state_value': TunableReference(description='\n            The state value to enter when last object leaves.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue')}

    @classproperty
    def apply_when_linked(cls):
        return True

    def _apply_broadcaster_effect(self, broadcaster, affected_object):
        if broadcaster.get_affected_object_count() == 1:
            broadcasting_object = broadcaster.broadcasting_object
            if broadcasting_object is not None:
                state_value = self.enter_state_value
                broadcasting_object.set_state(state_value.state, state_value)

    def remove_broadcaster_effect(self, broadcaster, affected_object):
        if broadcaster.get_affected_object_count() == 0:
            broadcasting_object = broadcaster.broadcasting_object
            if broadcasting_object is not None:
                state_value = self.exit_state_value
                broadcasting_object.set_state(state_value.state, state_value)

class BroadcasterEffectSelfBuff(_BroadcasterEffectTested):
    FACTORY_TUNABLES = {'broadcastee_count_interval': TunableInterval(description='\n            If the number of objects within this broadcaster is in this\n            interval, the buff will be applied. Includes lower and upper.\n            ', tunable_type=int, default_lower=1, default_upper=2, minimum=1, maximum=20), 'buff': buffs.tunable.TunableBuffReference(description='\n            The buff to apply\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._buff_handles = dict()

    @classproperty
    def apply_when_linked(cls):
        return True

    def _count_is_within_interval(self, broadcaster):
        object_count = broadcaster.get_affected_object_count()
        return object_count in self.broadcastee_count_interval

    def _on_object_number_changed(self, broadcaster):
        if self._count_is_within_interval(broadcaster):
            if broadcaster not in self._buff_handles:
                broadcasting_object = broadcaster.broadcasting_object
                self._buff_handles[broadcaster] = broadcasting_object.add_buff(self.buff.buff_type, buff_reason=self.buff.buff_reason)
        elif broadcaster in self._buff_handles:
            broadcasting_object = broadcaster.broadcasting_object
            if broadcasting_object is not None:
                broadcasting_object.remove_buff(self._buff_handles[broadcaster])
            del self._buff_handles[broadcaster]

    def _apply_broadcaster_effect(self, broadcaster, affected_object):
        self._on_object_number_changed(broadcaster)

    def remove_broadcaster_effect(self, broadcaster, affected_object):
        self._on_object_number_changed(broadcaster)

class BroadcasterEffectSelfLoot(_BroadcasterEffectTested):
    FACTORY_TUNABLES = {'broadcastee_count_interval': TunableInterval(description='\n            If the number of objects within this broadcaster is in this\n            interval, loot will be awarded. Includes lower and upper.\n            ', tunable_type=int, default_lower=1, default_upper=2, minimum=0), 'loot_list': TunableList(description='\n            A list of loot operations.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), 'apply_loot_on_remove': Tunable(description="\n            If enabled, determine whether or not we want to apply this broadcaster's\n            loot when the broadcaster is removed.\n            True means we will apply the loot on removal of the broadcaster\n            False means we will apply the loot as soon as enough sims enter the constraint\n            ", tunable_type=bool, default=True)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._observing_objs = set()

    @classproperty
    def apply_when_linked(cls):
        return True

    @classproperty
    def apply_when_removed(cls):
        return True

    def _count_is_within_interval(self, broadcaster):
        object_count = len(self._observing_objs)
        return object_count in self.broadcastee_count_interval

    def apply_broadcaster_loot(self, broadcaster):
        if self.apply_loot_on_remove:
            self._try_apply_loot(broadcaster)
        self._observing_objs = set()

    def _apply_broadcaster_effect(self, broadcaster, affected_object):
        if self._should_apply_broadcaster_effect(broadcaster, affected_object):
            self._observing_objs.add(affected_object.id)
        if not self.apply_loot_on_remove:
            self._try_apply_loot(broadcaster)

    def _try_apply_loot(self, broadcaster):
        if self._count_is_within_interval(broadcaster):
            resolver = broadcaster.get_resolver(broadcaster.broadcasting_object)
            for loot_action in self.loot_list:
                loot_action.apply_to_resolver(resolver)

class BroadcasterEffectStartFire(_BroadcasterEffectTestedOneShot):
    FACTORY_TUNABLES = {'percent_chance': TunablePercent(description='\n            A value between 0 - 100 which represents the percent chance to \n            start a fire when reacting to the broadcaster.\n            ', default=50)}

    def _apply_broadcaster_effect(self, broadcaster, affected_object):
        if random.random() <= self.percent_chance:
            fire_service = services.get_fire_service()
            fire_service.spawn_fire_at_object(affected_object)

class BroadcasterEffectLoot(_BroadcasterEffectTestedOneShot):
    FACTORY_TUNABLES = {'loot_list': TunableList(description='\n            A list of loot operations.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))}

    def _apply_broadcaster_effect(self, broadcaster, affected_object):
        resolver = broadcaster.get_resolver(affected_object)
        for loot_action in self.loot_list:
            loot_action.apply_to_resolver(resolver)
