import operatorfrom event_testing.results import TestResult, ExecuteResultfrom interactions import ParticipantTypefrom interactions.aop import AffordanceObjectPairfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom interactions.base.mixer_interaction import MixerInteractionfrom interactions.base.super_interaction import SuperInteractionfrom interactions.constraints import create_constraint_set, ANYWHERE, Nowherefrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.join_liability import JOIN_INTERACTION_LIABILITY, JoinInteractionLiabilityfrom sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuningfrom sims4.tuning.tunable import TunableReference, Tunable, TunableList, TunableTuple, OptionalTunable, TunableEnumEntry, TunableVariantfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethod, classpropertyfrom singletons import DEFAULTfrom ui.ui_dialog_generic import UiDialogTextInputOkCancel, UiDialogTextInputOkimport element_utilsimport interactionsimport servicesimport sims4.logimport sims4.mathimport sims4.resourceslogger = sims4.log.Logger('Interactions')
class ProxyInteraction(SuperInteraction):
    INSTANCE_SUBCLASSES_ONLY = True

    @classproperty
    def proxy_name(cls):
        return '[Proxy]'

    @classmethod
    def generate(cls, proxied_affordance):

        class ProxyInstance(cls, proxied_affordance):
            INSTANCE_SUBCLASSES_ONLY = True

            @classproperty
            def proxied_affordance(cls):
                return proxied_affordance

            @classmethod
            def get_interaction_type(cls):
                return proxied_affordance.get_interaction_type()

        ProxyInstance.__name__ = cls.proxy_name + proxied_affordance.__name__
        return ProxyInstance

    @classmethod
    def potential_pie_menu_sub_interactions_gen(cls, target, context, scoring_gsi_handler=None, **kwargs):
        pass

class JoinInteraction(ProxyInteraction):
    create_join_solo_solo = TunableLocalizedStringFactory(default=3134556480, description='Interaction name wrapper for when a solo Sim joins another solo Sim.')
    INSTANCE_SUBCLASSES_ONLY = True

    @classmethod
    def generate(cls, proxied_affordance, join_interaction, joinable_info):
        result = super().generate(proxied_affordance)
        result.join_interaction = join_interaction
        result.joinable_info = joinable_info
        return result

    @classproperty
    def proxy_name(cls):
        return '[Join]'

    @classproperty
    def allow_user_directed(cls):
        return True

    @classmethod
    def _can_rally(cls, *args, **kwargs):
        return False

    @classmethod
    def _test(cls, *args, **kwargs):
        return super()._test(*args, join=True, **kwargs)

    @flexmethod
    def get_name(cls, inst, target=DEFAULT, context=DEFAULT, **kwargs):
        if inst is not None:
            return super(JoinInteraction, inst).get_name(target=target, context=context, **kwargs)
        join_target = cls.get_participant(participant_type=ParticipantType.JoinTarget, sim=context.sim, target=target, **kwargs)
        original_name = super(JoinInteraction, cls).get_name(target=target, context=context, **kwargs)
        localization_args = (original_name, join_target)
        if cls.joinable_info.join_available and cls.joinable_info.join_available.loc_custom_join_name is not None:
            return cls.joinable_info.join_available.loc_custom_join_name(*localization_args)
        return cls.create_join_solo_solo(*localization_args)

    def run_pre_transition_behavior(self, *args, **kwargs):
        if self.join_interaction.has_been_canceled:
            self.cancel(FinishingType.INTERACTION_INCOMPATIBILITY, cancel_reason_msg='The joined interaction has been canceled.')
        return super().run_pre_transition_behavior(*args, **kwargs)

    def on_added_to_queue(self, *args, **kwargs):
        super().on_added_to_queue(*args, **kwargs)
        if self.joinable_info.link_joinable:
            self.join_interaction.add_liability(JOIN_INTERACTION_LIABILITY, JoinInteractionLiability(self))

class AskToJoinInteraction(ProxyInteraction, ImmediateSuperInteraction):
    create_invite_solo_any = TunableLocalizedStringFactory(default=974662056, description='Interaction name wrapper for inviting a solo Sim.')
    INSTANCE_SUBCLASSES_ONLY = True

    @classproperty
    def proxy_name(cls):
        return '[AskToJoin]'

    def __init__(self, *args, **kwargs):
        ImmediateSuperInteraction.__init__(self, *args, **kwargs)

    def _trigger_interaction_start_event(self):
        pass

    def _trigger_interaction_complete_test_event(self):
        pass

    @classmethod
    def generate(cls, proxied_affordance, join_sim, join_interaction, joinable_info):
        result = super().generate(proxied_affordance)
        result.join_sim = join_sim
        result.join_interaction = join_interaction
        result.joinable_info = joinable_info
        return result

    @classproperty
    def allow_autonomous(cls):
        return False

    @classproperty
    def allow_user_directed(cls):
        return True

    @classmethod
    def test(cls, target, context, **kwargs):
        join_context = context.clone_for_sim(cls.join_sim)
        return cls.proxied_affordance.test(target, join_context, join=True, **kwargs)

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        original_name = super(ProxyInteraction, inst_or_cls)._get_name(target=target, context=context, **kwargs)
        localization_args = (original_name, inst_or_cls.join_sim)
        if cls.joinable_info.invite_available and cls.joinable_info.invite_available.loc_custom_invite_name is not None:
            return cls.joinable_info.invite_available.loc_custom_invite_name(*localization_args)
        return inst_or_cls.create_invite_solo_any(*localization_args)

    def _push_join_interaction(self, join_sim):
        join_interaction = JoinInteraction.generate(self.proxied_affordance, join_interaction=self.join_interaction, joinable_info=self.joinable_info)
        join_context = InteractionContext(join_sim, self.context.source, self.priority, insert_strategy=QueueInsertStrategy.NEXT)
        join_sim.push_super_affordance(join_interaction, self.target, join_context, **self.interaction_parameters)

    def _do_perform_gen(self, timeline):
        self._push_join_interaction(self.join_sim)
        return True

    @flexmethod
    def create_localized_string(cls, inst, localized_string_factory, *tokens, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        interaction_tokens = (inst_or_cls.join_sim, inst_or_cls.join_interaction.sim)
        return localized_string_factory(*interaction_tokens + tokens)

class AggregateSuperInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'aggregated_affordances': TunableList(description='\n                A list of affordances composing this aggregate.  Distance\n                estimation will be used to break ties if there are multiple\n                valid interactions at the same priority level.\n                ', tunable=TunableTuple(description='\n                    An affordance and priority entry.\n                    ', priority=Tunable(description='\n                        The relative priority of this affordance compared to\n                        other affordances in this aggregate.\n                        ', tunable_type=int, default=0), affordance=SuperInteraction.TunableReference(description='\n                        The aggregated affordance.\n                        ', pack_safe=True)), tuning_group=GroupNames.GENERAL), 'sim_to_push_affordance_on': TunableEnumEntry(description='\n                The Sim to push the affordance on.  If this is Actor, the\n                affordance will be pushed as a continuation of this.\n                ', tunable_type=ParticipantType, default=ParticipantType.Actor, tuning_group=GroupNames.TRIGGERS), 'use_aggregated_affordance_constraints': Tunable(description="\n            If enabled, this interaction will pull it's constraints from the\n            interaction constraints of the aggregated affordances. The benefit\n            is that we are compatible with interactions we intend to run, even\n            if they have constraints different from one another. This prevents\n            us from having to add a bunch of tests to those affordances and a\n            generic constraint here.\n            ", tunable_type=bool, default=False, tuning_group=GroupNames.CONSTRAINTS)}
    _allow_user_directed = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._valid_aops = None

    @classproperty
    def affordances(cls):
        return (a.affordance.get_interaction_type() for a in cls.aggregated_affordances)

    @classmethod
    def _aops_sorted_gen(cls, target, **interaction_parameters):
        affordances = []
        for aggregated_affordance in cls.aggregated_affordances:
            aop = AffordanceObjectPair(aggregated_affordance.affordance, target, aggregated_affordance.affordance, None, **interaction_parameters)
            affordances.append((aggregated_affordance.priority, aop))
        return sorted(affordances, key=operator.itemgetter(0), reverse=True)

    @flexmethod
    def _get_tested_aops(cls, inst, target, context, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        if inst is not None and inst._valid_aops is not None:
            return inst._valid_aops
        aops_valid = []
        cls._allow_user_directed = False
        for (priority, aop) in inst_or_cls._aops_sorted_gen(target, **interaction_parameters):
            test_result = aop.test(context)
            if test_result:
                if aop.affordance.allow_user_directed:
                    cls._allow_user_directed = True
                aops_valid.append((aop, priority))
        if inst is not None:
            inst._valid_aops = aops_valid
        return aops_valid

    @flexmethod
    def test(cls, inst, target=DEFAULT, context=DEFAULT, super_interaction=None, skip_safe_tests=False, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        result = super(__class__, inst_or_cls).test(target=target, context=context, super_interaction=super_interaction, skip_safe_tests=skip_safe_tests, **interaction_parameters)
        if result:
            target = target if target is not DEFAULT else inst.target
            context = context if context is not DEFAULT else inst.context
            context = context.clone_for_sim(cls.get_participant(participant_type=cls.sim_to_push_affordance_on, sim=context.sim, target=target))
            valid_aops = inst_or_cls._get_tested_aops(target, context, **interaction_parameters)
            result = TestResult.TRUE if valid_aops else TestResult(False, 'No sub-affordances passed their tests.')
        return result

    @classmethod
    def consumes_object(cls):
        for affordance_tuple in cls.aggregated_affordances:
            if affordance_tuple.affordance.consumes_object():
                return True
        return False

    @classproperty
    def allow_user_directed(cls):
        return cls._allow_user_directed

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        inst_or_cls = cls if inst is None else inst
        yield from super(SuperInteraction, inst_or_cls)._constraint_gen(sim, target, participant_type=participant_type)
        if inst_or_cls.use_aggregated_affordance_constraints:
            aggregated_constraints = []
            affordances = []
            affordances = [aop.super_affordance for (aop, _) in inst._valid_aops]
            affordances = affordances if inst is not None and inst._valid_aops is not None and affordances else [affordance_tuple.affordance for affordance_tuple in inst_or_cls.aggregated_affordances]
            if not affordances:
                yield Nowhere
            for aggregated_affordance in affordances:
                intersection = ANYWHERE
                constraint_gen = aggregated_affordance.constraint_gen
                constraint_gen = super(SuperInteraction, aggregated_affordance)._constraint_gen
                for constraint in constraint_gen(sim, inst_or_cls.get_constraint_target(target), participant_type=participant_type):
                    intersection = constraint.intersect(intersection)
                    if not intersection.valid:
                        pass
                aggregated_constraints.append(intersection)
            if aggregated_constraints:
                yield create_constraint_set(aggregated_constraints, debug_name='AggregatedConstraintSet')

    def _do_perform_gen(self, timeline):
        sim = self.get_participant(self.sim_to_push_affordance_on)
        if sim == self.context.sim:
            context = self.context.clone_for_continuation(self)
        else:
            context = context.clone_for_sim(sim)
        max_priority = None
        aops_valid = []
        self._valid_aops = None
        valid_aops = self._get_tested_aops(self.target, context, **self.interaction_parameters)
        for (aop, priority) in valid_aops:
            if priority < max_priority:
                break
            aops_valid.append(aop)
            max_priority = priority
        if not aops_valid:
            logger.warn('Failed to find valid super affordance in AggregateSuperInteraction: {}, did we not run its test immediately before executing it?', self)
            return ExecuteResult.NONE
        compatible_interactions = []
        for aop in aops_valid:
            interaction_result = aop.interaction_factory(context)
            if not interaction_result:
                raise RuntimeError('Failed to generate interaction from aop {}. {} [rmccord]'.format(aop, interaction_result))
            interaction = interaction_result.interaction
            if self.use_aggregated_affordance_constraints:
                if interactions.si_state.SIState.test_compatibility(interaction, force_concrete=True):
                    compatible_interactions.append(interaction)
            compatible_interactions.append(interaction)
        if not compatible_interactions:
            return ExecuteResult.NONE
        interactions_by_distance = []
        for interaction in compatible_interactions:
            if len(compatible_interactions) == 1:
                distance = 0
            else:
                (distance, _, _) = interaction.estimate_distance()
            if distance is not None:
                interactions_by_distance.append((distance, interaction))
            else:
                interactions_by_distance.append((sims4.math.MAX_INT32, interaction))
        (_, interaction) = min(interactions_by_distance, key=operator.itemgetter(0))
        return AffordanceObjectPair.execute_interaction(interaction)

class AggregateMixerInteraction(MixerInteraction):
    INSTANCE_TUNABLES = {'aggregated_affordances': TunableList(description='\n                A list of affordances composing this aggregate. A random one\n                will be chosen from sub-action weights if multiple interactions\n                pass at the same priority.\n                ', tunable=TunableTuple(description='\n                    An affordance and priority entry.\n                    ', priority=Tunable(description='\n                        The relative priority of this affordance compared to\n                        other affordances in this aggregate.\n                        ', tunable_type=int, default=0), affordance=MixerInteraction.TunableReference(description='\n                        The aggregated affordance.\n                        ', pack_safe=True)), tuning_group=GroupNames.GENERAL)}
    _allow_user_directed = True

    @classmethod
    def _aops_sorted_gen(cls, target, context, super_interaction=DEFAULT, **interaction_parameters):
        affordances = []
        source_interaction = context.sim.posture.source_interaction if super_interaction == DEFAULT else super_interaction
        for aggregated_affordance in cls.aggregated_affordances:
            aop = AffordanceObjectPair(aggregated_affordance.affordance, target, source_interaction.affordance, source_interaction, **interaction_parameters)
            affordances.append((aggregated_affordance.priority, aop))
        return sorted(affordances, key=operator.itemgetter(0), reverse=True)

    @classmethod
    def _test(cls, target, context, **interaction_parameters):
        result = super()._test(target, context, **interaction_parameters)
        if not result:
            return result
        cls._allow_user_directed = False
        context = context.clone_for_sim(sim=context.sim)
        for (_, aop) in cls._aops_sorted_gen(target, context, **interaction_parameters):
            result = aop.test(context)
            if result:
                if aop.affordance.allow_user_directed:
                    cls._allow_user_directed = True
                return result
        return TestResult(False, 'No sub-affordances passed their tests.')

    @classmethod
    def consumes_object(cls):
        for aggregated_affordance in cls.aggregated_affordances:
            if aggregated_affordance.affordance.consumes_object():
                return True
        return False

    @classproperty
    def allow_user_directed(cls):
        return cls._allow_user_directed

    def _do_perform_gen(self, timeline):
        context = self.context.clone_for_continuation(self)
        max_priority = None
        aops_valid = []
        invalid_aops_with_result = []
        for (priority, aop) in self._aops_sorted_gen(self.target, context, super_interaction=self.super_interaction, **self.interaction_parameters):
            if priority < max_priority:
                break
            test_result = aop.test(context)
            if max_priority is not None and test_result:
                aops_valid.append(aop)
                max_priority = priority
            else:
                invalid_aops_with_result.append((aop, test_result))
        if not aops_valid:
            logger.error('Failed to find valid mixer affordance in AggregateMixerInteraction: {}, did we not run its test immediately before executing it?\n{}', self, invalid_aops_with_result, owner='rmccord')
            return ExecuteResult.NONE
        interactions_by_weight = []
        for aop in aops_valid:
            interaction_result = aop.interaction_factory(context)
            if not interaction_result:
                raise RuntimeError('Failed to generate interaction from aop {}. {} [rmccord]'.format(aop, interaction_result))
            interaction = interaction_result.interaction
            if len(aops_valid) == 1:
                weight = 0
            else:
                weight = interaction.affordance.calculate_autonomy_weight(context.sim)
            interactions_by_weight.append((weight, interaction))
        if not interactions_by_weight:
            return ExecuteResult.NONE
        (_, interaction) = max(interactions_by_weight, key=operator.itemgetter(0))
        return AffordanceObjectPair.execute_interaction(interaction)

class RenameImmediateInteraction(ImmediateSuperInteraction):
    TEXT_INPUT_NEW_NAME = 'new_name'
    TEXT_INPUT_NEW_DESCRIPTION = 'new_description'
    INSTANCE_TUNABLES = {'display_name_rename': OptionalTunable(TunableLocalizedStringFactory(description="If set, this localized string will be used as the interaction's display name if the object has been previously renamed.")), 'rename_dialog': TunableVariant(description='\n            The rename dialog to show when running this interaction.\n            ', ok_dialog=UiDialogTextInputOk.TunableFactory(text_inputs=(TEXT_INPUT_NEW_NAME, TEXT_INPUT_NEW_DESCRIPTION)), ok_cancel_dialog=UiDialogTextInputOkCancel.TunableFactory(text_inputs=(TEXT_INPUT_NEW_NAME, TEXT_INPUT_NEW_DESCRIPTION)))}

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        target = inst.target if inst is not None else target
        if inst_or_cls.display_name_rename is not None and target.has_custom_name():
            display_name = inst_or_cls.display_name_rename
        else:
            display_name = inst_or_cls.display_name
        return inst_or_cls.create_localized_string(display_name, target=target, context=context, **kwargs)

    def _run_interaction_gen(self, timeline):
        target_name_component = self.target.name_component

        def on_response(dialog):
            if not dialog.accepted:
                return
            name = dialog.text_input_responses.get(self.TEXT_INPUT_NEW_NAME)
            description = dialog.text_input_responses.get(self.TEXT_INPUT_NEW_DESCRIPTION)
            target = self.target
            if target is not None:
                if name is not None:
                    target.set_custom_name(name, actor_sim_id=self._sim.id)
                if description is not None:
                    target.set_custom_description(description)
                self._update_ui_metadata(target)
            sequence = self._build_outcome_sequence()
            services.time_service().sim_timeline.schedule(element_utils.build_element(sequence))

        text_input_overrides = {}
        (template_name, template_description) = target_name_component.get_template_name_and_description()
        text_input_overrides[self.TEXT_INPUT_NEW_NAME] = None
        if self.target.has_custom_name():
            text_input_overrides[self.TEXT_INPUT_NEW_NAME] = lambda *_, **__: LocalizationHelperTuning.get_object_name(self.target)
        elif template_name is not None:
            text_input_overrides[self.TEXT_INPUT_NEW_NAME] = template_name
        text_input_overrides[self.TEXT_INPUT_NEW_DESCRIPTION] = None
        if self.target.has_custom_description():
            text_input_overrides[self.TEXT_INPUT_NEW_DESCRIPTION] = lambda *_, **__: LocalizationHelperTuning.get_object_description(self.target)
        elif template_description is not None:
            text_input_overrides[self.TEXT_INPUT_NEW_DESCRIPTION] = template_description
        dialog = self.rename_dialog(self.sim, self.get_resolver())
        dialog.show_dialog(on_response=on_response, text_input_overrides=text_input_overrides)
        return True

    def build_outcome(self):
        pass

    def _update_ui_metadata(self, updated_object):
        updated_object.update_ui_metadata()
        current_inventory = updated_object.get_inventory()
        if current_inventory is not None:
            current_inventory.push_inventory_item_update_msg(updated_object)

class ImposterSuperInteraction(SuperInteraction):

    def __init__(self, *args, interaction_name=None, interaction_icon_info=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._old_interaction_name = interaction_name
        self._old_icon_info = interaction_icon_info

    @flexmethod
    def get_name(cls, inst, *args, **kwargs):
        if inst is not None:
            return inst._old_interaction_name
        return super().get_name(*args, **kwargs)

    @flexmethod
    def get_icon_info(cls, inst, *args, **kwargs):
        if inst is not None:
            return inst._old_icon_info
        return super().get_icon_info(*args, **kwargs)

    def _exited_pipeline(self, *args, **kwargs):
        try:
            super()._exited_pipeline(*args, **kwargs)
        finally:
            self._old_interaction_name = None
            self._old_icon_info = None
