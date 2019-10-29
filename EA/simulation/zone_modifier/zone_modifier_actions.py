import randomfrom audio.primitive import TunablePlayAudio, play_tunable_audiofrom clock import interval_in_real_secondsfrom event_testing.resolver import SingleSimResolver, GlobalResolverfrom event_testing.results import TestResultfrom event_testing.tests import TunableTestSetfrom event_testing.tests_with_data import TunableParticipantRanInteractionTestfrom interactions import ParticipantTypefrom interactions.utils.camera import TunableCameraShakefrom interactions.utils.loot import LootActionsfrom objects.object_creation import ObjectCreationOpfrom scheduler import WeeklySchedule, ScheduleEntryfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableSet, TunableEnumEntry, TunableList, AutoFactoryInit, TunableReference, HasTunableSingletonFactory, TunableFactory, TunableVariant, TunablePercent, TunablePackSafeReference, TunableThreshold, TunableRealSecond, Tunable, TunableInterval, OptionalTunable, TunableTuplefrom situations.service_npcs.modify_lot_items_tuning import ModifyAllLotItemsfrom snippets import define_snippetfrom tag import TunableTagsfrom tunable_utils.tunable_blacklist import TunableBlacklistimport alarmsimport clockimport enumimport event_testingimport servicesimport sims4logger = sims4.log.Logger('ZoneModifierAction', default_owner='jdimailig')
class ZoneModifierActionBehavior(enum.Int):
    ONCE = 0
    ONCE_IF_SIMS_EXIST = 1
    ONCE_IF_ACTIVE_SIM_ON_LOT = 2

class ZoneModifierActionVariants(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, loot=ZoneModifierBroadcastLoot.TunableFactory(), quake=ZoneModifierTriggerQuake.TunableFactory(), modify_lot_items=ZoneModifierModifyLotItems.TunableFactory(), service_npc_request=ZoneModifierRequestServiceNPC.TunableFactory(), play_sound=ZoneModifierPlaySound.TunableFactory(), spawn_objects=ZoneModifierSpawnObjects.TunableFactory(), default='loot', **kwargs)

class TunableSimsThreshold(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'tests': TunableTestSet(description='\n            Tests to be performed on active Sims\n            '), 'threshold': TunableThreshold(description='\n            Checks against the number of Sims, Needs to \n            pass for the TunableSimsThreshold test to pass\n            ')}

    def test_sim_requirements(self, sims):
        count = 0
        for sim in sims:
            resolver = SingleSimResolver(sim.sim_info)
            if self.tests.run_tests(resolver):
                count += 1
        return self.threshold.compare(count)

class ZoneModifierAction(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'behavior': TunableEnumEntry(description='\n            Under what conditions the action should be applied.\n            \n            May be one of the following:\n            - Always applied.\n            - Applied only if there are Sims on the lot.\n            - Applied only if the active Sim is on the lot.\n            ', tunable_type=ZoneModifierActionBehavior, default=ZoneModifierActionBehavior.ONCE), 'threshold_requirements': TunableList(description='\n            Number of Sims required on active lot in order for the \n            action to be applied\n            ', tunable=TunableSimsThreshold.TunableFactory()), 'chance': TunablePercent(description='\n            Chance that this action will occur.\n            ', default=100)}

    def perform(self):
        if self._can_perform_action():
            self._perform_action()

    def _can_perform_action(self):
        if random.random() >= self.chance:
            return False
        if self.behavior == ZoneModifierActionBehavior.ONCE:
            return self._check_threshold_requirements()
        if self.behavior == ZoneModifierActionBehavior.ONCE_IF_ACTIVE_SIM_ON_LOT:
            active_sim = services.get_active_sim()
            if active_sim is not None and active_sim.is_on_active_lot() and self._check_threshold_requirements():
                return True
        elif self.behavior == ZoneModifierActionBehavior.ONCE_IF_SIMS_EXIST:
            sims = list(services.sim_info_manager().instanced_sims_on_active_lot_gen())
            if any(sims) and self._check_threshold_requirements(sims):
                return True
        return False

    def _check_threshold_requirements(self, sims=None):
        if not self.threshold_requirements:
            return True
        if sims is None:
            sims = list(services.sim_info_manager().instanced_sims_on_active_lot_gen())
        return all(requirement.test_sim_requirements(sims) for requirement in self.threshold_requirements)

    def _perform_action(self):
        raise NotImplementedError

    @property
    def _additional_resolver_participants(self):
        return {ParticipantType.PickedZoneId: frozenset()}

    def sim_resolver(self, sim_info):
        return SingleSimResolver(sim_info, additional_participants=self._additional_resolver_participants)

class ZoneModifierSimLootMixin:
    FACTORY_TUNABLES = {'loots': TunableSet(description='\n            Loot(s) to apply.  Loot applied to Sims must be configured\n            against Actor participant type.\n            \n            This loot op does not occur in an interaction context,\n            so other participant types may not be supported.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), pack_safe=True))}

    def apply_loots_to_sims_on_active_lot(self):
        self.apply_loots_to_sims(services.sim_info_manager().instanced_sims_on_active_lot_gen())

    def apply_loots_to_sims(self, sims):
        for sim in sims:
            self.apply_loots_to_sim(sim)

    def apply_loots_to_sim(self, sim):
        resolver = self.sim_resolver(sim.sim_info)
        for loot_action in self.loots:
            loot_action.apply_to_resolver(resolver)

    def apply_loots_to_random_sim_on_active_lot(self):
        sims = list(services.sim_info_manager().instanced_sims_on_active_lot_gen())
        if len(sims) == 0:
            return
        chosen_sim = random.choice(sims)
        self.apply_loots_to_sim(chosen_sim)

class ZoneModifierPlaySound(ZoneModifierAction):
    FACTORY_TUNABLES = {'sound_effect': TunablePlayAudio(description='\n            Sound to play.\n            '), 'duration': TunableRealSecond(description='\n            How long the sound should play for, in seconds.\n            After this duration, the sound will be stopped.\n            ', default=5, minimum=1)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_sound_handle = None

    def _perform_action(self):
        if self._stop_sound_handle is not None:
            return
        self._sound = play_tunable_audio(self.sound_effect)
        self._stop_sound_handle = alarms.add_alarm(services.get_active_sim(), interval_in_real_seconds(self.duration), self._stop_sound)

    def _stop_sound(self, *args):
        if self._sound is None:
            return
        self._sound.stop()
        self._sound = None
        self._stop_sound_handle.cancel()
        self._stop_sound_handle = None

class ZoneModifierTriggerQuake(ZoneModifierSimLootMixin, ZoneModifierAction):
    FACTORY_TUNABLES = {'shake_effect': TunableCameraShake.TunableFactory(description='\n            Tunable camera shake effect which will occur at the given trigger time.\n            '), 'play_sound': ZoneModifierPlaySound.TunableFactory(description='\n            Sound to play when a quake occurs\n            ', locked_args={'behavior': ZoneModifierActionBehavior.ONCE, 'threshold_requirements': ()})}

    def _perform_action(self):
        self.play_sound.perform()
        self.shake_effect.shake_camera()
        self.apply_loots_to_sims_on_active_lot()

class ZoneModifierRequestServiceNPC(ZoneModifierAction):
    FACTORY_TUNABLES = {'service_npc': TunablePackSafeReference(services.get_instance_manager(Types.SERVICE_NPC))}

    def _perform_action(self):
        if self.service_npc is None:
            return
        household = services.owning_household_of_active_lot()
        if household is None:
            return
        services.current_zone().service_npc_service.request_service(household, self.service_npc, user_specified_data_id=None, is_recurring=False)

class ZoneModifierBroadcastLoot(ZoneModifierSimLootMixin, ZoneModifierAction):
    ALL_SIMS_ON_LOT = 'AllSimsOnLot'
    ACTIVE_SIM_ONLY = 'ActiveSimOnly'
    RANDOM_SIM_ON_LOT = 'RandomSimOnLot'
    FACTORY_TUNABLES = {'loot_distribution': TunableVariant(description='\n            How to distribute the loot.  By default, distributes the loots\n            to all the Sims on the active lot.\n            \n            Another behavior is to only distribute to the active Sim. This\n            option could be used for things like TNS or global situations.\n            ', locked_args={'all_sims_on_lot': ALL_SIMS_ON_LOT, 'active_sim_only': ACTIVE_SIM_ONLY, 'random_sim_on_lot': RANDOM_SIM_ON_LOT}, default='all_sims_on_lot')}

    def _perform_action(self):
        distribution_type = self.loot_distribution
        if distribution_type == self.ACTIVE_SIM_ONLY:
            active_sim = services.get_active_sim()
            if active_sim is None:
                return
            self.apply_loots_to_sims([active_sim])
        elif distribution_type == self.ALL_SIMS_ON_LOT:
            self.apply_loots_to_sims_on_active_lot()
        elif distribution_type == self.RANDOM_SIM_ON_LOT:
            self.apply_loots_to_random_sim_on_active_lot()

class ZoneModifierModifyLotItems(ZoneModifierAction):
    FACTORY_TUNABLES = {'actions': ModifyAllLotItems.TunableFactory(description='\n            Actions to apply to all lot objects on active lot.\n            '), 'modification_chance': TunablePercent(description='\n            The chance that an object will be affected. We will reroll this\n            chance for each object being modified.\n            ', default=100)}

    def criteria(self, obj):
        if random.random() >= self.modification_chance:
            return False
        return obj.is_on_active_lot()

    def _perform_action(self):
        self.actions().modify_objects(object_criteria=self.criteria)

class ZoneModifierSpawnObjects(ZoneModifierAction):
    FACTORY_TUNABLES = {'creation_op': ObjectCreationOp.TunableFactory(description='\n            The operation that will create the objects.\n            ', locked_args={'destroy_on_placement_failure': True}), 'iterations': OptionalTunable(description='\n            Random range of iterations we will run the creation op for.  Will\n            default to 1 iteration if untuned. \n            ', tunable=TunableInterval(tunable_type=int, default_lower=0, default_upper=1, minimum=0, maximum=10)), 'spawn_delay': OptionalTunable(description='\n            Random range of real world seconds, will be converted to sim\n            minutes during run time.  When running multiple iterations,\n            each iteration will get its own randomized delay within \n            the specified range.  Objects queued for spawning this way do \n            not persist through a save/load.\n            ', tunable=TunableInterval(tunable_type=TunableRealSecond, default_lower=0.0, default_upper=1.0, minimum=0)), 'spawn_threshold': OptionalTunable(description='\n            Defines a threshold of instanced objects to limit spawning.\n            ', tunable=TunableTuple(tags=TunableTags(description='\n                    Set of tags that objects must match against in order to \n                    count towards the threshold.\n                    '), match_any=Tunable(description='\n                    If set to false, objects must match all tags to count towards\n                    the threshold.\n                    ', tunable_type=bool, default=False), threshold=Tunable(description='Threshold of objects that match\n                    the tuned tags.  If the number of matching instanced objects\n                    is >= to this threshold, we will not spawn any objects.  Otherwise\n                    we will perform as many iterations as possible to stay under\n                    the tuned threshold.\n                    For example if the threshold is 5, the creation op is creating 3 objects,\n                    and we currently have 3 matching objects on the lot.  We would\n                    perform 0 iterations and spawn no objects.  \n                    ', tunable_type=int, default=1)))}

    def _scale_iterations_to_threshold(self, iterations):
        if self.spawn_threshold is None:
            return iterations
        object_manager = services.object_manager()
        num_matching = object_manager.get_num_objects_matching_tags(self.spawn_threshold.tags, self.spawn_threshold.match_any)
        allowance = self.spawn_threshold.threshold - num_matching
        num_spawning = iterations*self.creation_op.quantity
        if allowance <= 0:
            return 0
        if num_spawning <= allowance:
            return iterations
        else:
            return allowance//self.creation_op.quantity

    def _on_alarm_callback(self):
        if self.creation_op is None:
            return
        resolver = GlobalResolver()
        self.creation_op.apply_to_resolver(resolver)

    def _perform_action(self):
        if self.creation_op is None:
            return
        resolver = GlobalResolver()
        iterations = self.iterations.random_int() if self.iterations is not None else 1
        iterations = self._scale_iterations_to_threshold(iterations)
        delay = self.spawn_delay
        zone_modifier_service = services.get_zone_modifier_service()
        for _ in range(iterations):
            if delay is not None:
                delay_time_span = clock.interval_in_real_seconds(delay.random_float())
                zone_modifier_service.create_action_alarm(delay_time_span, self._on_alarm_callback)
            else:
                self.creation_op.apply_to_resolver(resolver)
(_, ZoneModifierActionVariantSnippet) = define_snippet('zone_modifier_action', ZoneModifierActionVariants())
class ZoneModifierActionContinuation(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'action': ZoneModifierActionVariantSnippet(description='\n            Action to run after the initial actions complete\n            '), 'delay_time': TunableRealSecond(description='\n            Real world seconds to wait after the initial actions complete before\n            running the continuation action.\n            ', default=0.0)}

    def _on_alarm_callback(self):
        if self.action is None:
            logger.error('Zone Modifier Continuation Action is None', owner='bnguyen')
            return
        self.action.perform()

    def perform_action(self):
        if self.action is None:
            logger.error('Zone Modifier Continuation Action is None', owner='bnguyen')
            return
        if self.delay_time is not None:
            zone_modifier_service = services.get_zone_modifier_service()
            delay_time_span = clock.interval_in_real_seconds(self.delay_time)
            zone_modifier_service.create_action_alarm(delay_time_span, self._on_alarm_callback)
        else:
            self.action.perform()

class ZoneModifierWeeklySchedule(WeeklySchedule):

    class ZoneModifierWeeklyScheduleEntry(ScheduleEntry):

        @staticmethod
        def _callback(instance_class, tunable_name, source, value, **kwargs):
            setattr(value, 'zone_modifier', instance_class)

        FACTORY_TUNABLES = {'execute_on_removal': Tunable(description='\n                If checked, this schedule entry is executed when the modifier is\n                removed while the zone is running.\n                ', tunable_type=bool, default=False), 'callback': _callback, 'continuation_actions': TunableList(tunable=ZoneModifierActionContinuation.TunableFactory(description='\n                    A continuing action to run after the initial zone mod actions.\n                    ')), 'chance': TunablePercent(description='\n                Chance that this schedule entry as a whole will occur.\n                ', default=100)}

    @TunableFactory.factory_option
    def schedule_entry_data(pack_safe=True):
        return {'schedule_entries': TunableList(description='\n                A list of event schedules. Each event is a mapping of days of the\n                week to a start_time and duration.\n                ', tunable=ZoneModifierWeeklySchedule.ZoneModifierWeeklyScheduleEntry.TunableFactory(schedule_entry_data={'tuning_name': 'actions', 'tuning_type': TunableList(tunable=ZoneModifierActionVariantSnippet(description='\n                                Action to perform during the schedule entry.\n                                '))}), unique_entries=True)}

class ZoneModifierTriggerInteractions(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'test': TunableParticipantRanInteractionTest(description='\n            Criteria for an interaction to be able to satisfy this trigger.\n            ', locked_args={'participant': ParticipantType.Actor, 'tooltip': None}), 'blacklist': TunableBlacklist(description='\n            A black list specifying any affordances that should never be included,\n            even if they match the trigger criteria.\n            ', tunable=TunableReference(manager=services.affordance_manager(), pack_safe=True))}
    expected_kwargs = (('sims', event_testing.test_constants.SIM_INSTANCE), ('interaction', event_testing.test_constants.FROM_EVENT_DATA))

    def get_expected_args(self):
        return dict(self.expected_kwargs)

    def __call__(self, interaction=None, sims=None):
        if interaction is None:
            return TestResult(False, 'interaction is null')
        if not self.blacklist.test_item(interaction.affordance):
            return TestResult(False, 'Failed affordance check: {} is in blacklist {}', interaction.affordance, self)
        return self.test(interaction=interaction, sims=sims)

    def applies_to_event(self, event):
        return event in self.test.test_events

class ZoneInteractionTriggers(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'trigger_conditions': TunableList(description='\n            Check the if a specified interaction(s) ran to see if it will\n            trigger the specified loot.\n            ', tunable=ZoneModifierTriggerInteractions.TunableFactory()), 'on_interaction_loot': TunableSet(description='\n            Loot applied to the Sim when the actor participant performs\n            an interaction that matches the criteria.\n            ', tunable=LootActions.TunableReference(pack_safe=True))}

    def handle_interaction_event(self, sim_info, event, resolver):
        for test in self.trigger_conditions:
            if test.applies_to_event(event) and resolver(test):
                for loot in self.on_interaction_loot:
                    loot.apply_to_resolver(resolver)
                break

    def get_trigger_tests(self):
        tests = list()
        for trigger_conditions in self.trigger_conditions:
            tests.append(trigger_conditions.test)
        return tests
