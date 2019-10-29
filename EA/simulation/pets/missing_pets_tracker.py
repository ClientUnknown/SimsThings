from _collections import dequefrom builtins import intimport randomfrom date_and_time import TimeSpanfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom event_testing.results import EnqueueResultfrom event_testing.tests import TunableTestSetfrom filters.sim_filter_service import SimFilterGlobalBlacklistReasonfrom households.household_tracker import HouseholdTrackerfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.priority import Priorityfrom objects import ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZEDfrom sims.sim_info_types import Age, Speciesfrom sims4.tuning.tunable import TunableSimMinute, TunablePercent, TunableReference, TunablePackSafeReference, TunableMapping, TunableEnumEntry, Tunable, TunableIntervalfrom tag import Tagfrom ui.ui_dialog_notification import UiDialogNotification, TunableUiDialogNotificationSnippetimport alarmsimport clockimport routingimport servicesimport sims4
class MissingPetsTracker(HouseholdTracker):
    RUN_AWAY_CHANCE = TunablePercent(description='\n        Chance for the pet to run away.\n        ', default=50)
    RUN_AWAY_INTERACTION = TunablePackSafeReference(description='\n        Affordance to push on pet to run away.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
    RUN_AWAY_INTERACTION_TAG = TunableEnumEntry(description='\n        Tag to specify the run away interaction.\n        ', tunable_type=Tag, default=Tag.INVALID, pack_safe=True)
    RUN_AWAY_LOOT_FOR_HOUSEHOLD = TunablePackSafeReference(description='\n        A reference to a loot to be added to household members when their pet \n        runs away.\n        ', manager=services.get_instance_manager(sims4.resources.Types.ACTION))
    RUN_AWAY_NOTIFICATION = TunableUiDialogNotificationSnippet(description='\n        A notification to be displayed when the pet runs away.\n        ', pack_safe=True)
    TEST_INTERVAL = TunableSimMinute(description='\n        How often a pet should have its relationships and motives checked to see \n        if it should run away.\n        ', default=60, minimum=5)
    MOTIVE_TESTS_CAT = TunableTestSet(description='\n        A set of motive tests that must pass for a cat to run away\n        ')
    MOTIVE_TESTS_DOG = TunableTestSet(description='\n        A set of motive tests that must pass for a dog to run away\n        ')
    MOTIVE_TESTS_NUM_RESULTS_STORE = Tunable(description='\n        The number of motive test results to store.\n        ', tunable_type=int, default=10)
    MOTIVE_TESTS_NUM_RESULTS_PASS = Tunable(description='\n        The number of motive tests that need to be pass results to make the pet run away .\n        ', tunable_type=int, default=5)
    RELATIONSHIP_TESTS = TunableTestSet(description='\n        A set of relationship tests that must pass for a pet to run away\n        ')
    ADDITIONAL_RUNAWAY_TESTS = TunableTestSet(description='\n        An additional set of tests that must pass in order for the pet to run away.\n        ')
    RETURN_INTERVAL = TunableSimMinute(description='\n        The number of sim minutes until the pet must return.\n        ', default=1000, minimum=1)
    RETURN_INTERACTION = TunablePackSafeReference(description='\n        Affordance to push on pet when it returns.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
    COOLDOWN_INTERVAL = TunableSimMinute(description='\n        The number of sim minutes after a pet returns during which pets from \n        the same household cannot run away.\n        ', default=1000, minimum=1)
    DEFAULT_AWAY_ACTIONS = TunableMapping(description='\n        Map of species to the default away action to run when a pet is missing.\n        ', key_type=TunableEnumEntry(description='\n            The species of the pet that is missing.\n            ', tunable_type=Species, default=Species.DOG, invalid_enums=(Species.INVALID,)), value_type=TunableReference(description='\n            The default away action to be run when a pet is missing.\n            ', manager=services.get_instance_manager(sims4.resources.Types.AWAY_ACTION), pack_safe=True))
    MISSING_PET_TRAIT = TunablePackSafeReference(description='\n        A reference to a trait to be added to missing pets. \n        ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT))
    POST_ALERT_EFFECTIVENESS = TunableInterval(description='\n        The value by which the amount of time remaining for the pet to return\n        is reduced by when posting an alert.\n        ', tunable_type=float, default_lower=0, default_upper=1, minimum=0, maximum=1)
    SKEWER_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        A notification to be dislayed when the whistle is pressed in the skewer while the pet\n        is missing.\n        ')

    def __init__(self, household, *args, **kwargs):
        self._household = household
        self._initialize_pet_tracker_attributes()

    def _initialize_pet_tracker_attributes(self):
        self._missing_pet_id = 0
        self._test_alarm = None
        self._return_alarm = None
        self._cooldown_alarm = None
        self._motive_test_results = {}
        self._return_pet_on_zone_load = False
        self._running_away = False
        self._alert_posted = False

    @property
    def missing_pet_id(self):
        return self._missing_pet_id

    @missing_pet_id.setter
    def missing_pet_id(self, value):
        self._missing_pet_id = value

    @property
    def missing_pet_info(self):
        if self.missing_pet_id == 0:
            return
        return services.sim_info_manager().get(self.missing_pet_id)

    @property
    def alert_posted(self):
        return self._alert_posted

    def is_pet_missing(self, pet_info):
        return self._missing_pet_id == pet_info.id

    def on_all_households_and_sim_infos_loaded(self):
        if self._household.is_active_household and self.missing_pet_id == 0 and self._test_alarm is None:
            test_interval = clock.interval_in_sim_minutes(self.TEST_INTERVAL)
            self._add_test_alarm(test_interval)

    def restore_missing_state(self):
        if self._missing_pet_id == 0:
            return
        missing_pet_info = self.missing_pet_info
        if missing_pet_info is None:
            self._clear_missing_pet_data(self._missing_pet_id)
            if self._test_alarm is None:
                test_interval = clock.interval_in_sim_minutes(self.TEST_INTERVAL)
                self._add_test_alarm(test_interval)
            return
        pet_sim = missing_pet_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED)
        if self._return_pet_on_zone_load:
            self._return_pet_on_zone_load = False
            self._return_pet(missing_pet_info)
        else:
            sim_filter_service = services.sim_filter_service()
            sim_filter_service.add_sim_id_to_global_blacklist(self._missing_pet_id, SimFilterGlobalBlacklistReason.MISSING_PET)
            zone_restored_sis = services.current_zone().should_restore_sis()
            if zone_restored_sis and missing_pet_info.has_loaded_si_state:
                return
            if self._push_run_away_affordance(pet_sim):
                pet_sim.set_allow_route_instantly_when_hitting_marks(True)

    def _run_tests(self):
        if self.missing_pet_id != 0 or self._running_away:
            return
        if self._household.is_active_household and self._household.home_zone_id != services.current_zone_id():
            return
        for pet in self._household.instanced_pets_gen():
            if pet.sim_info.age < Age.ADULT:
                pass
            elif random.random() <= self.RUN_AWAY_CHANCE:
                resolver = SingleSimResolver(pet.sim_info)
                if not self.ADDITIONAL_RUNAWAY_TESTS.run_tests(resolver):
                    pass
                else:
                    should_run_away = self._run_relationship_tests(pet.sim_info)
                    if not should_run_away:
                        if pet.id not in self._motive_test_results:
                            self._motive_test_results[pet.id] = deque(maxlen=self.MOTIVE_TESTS_NUM_RESULTS_STORE)
                        self._motive_test_results[pet.id].append(1 if self._run_motive_tests(pet.sim_info) else 0)
                        should_run_away = sum(self._motive_test_results[pet.id]) >= self.MOTIVE_TESTS_NUM_RESULTS_PASS
                    if should_run_away:
                        self.run_away(pet.sim_info)

    def _run_relationship_tests(self, pet_info):
        num_sims = 0
        num_rel_tests_passed = 0
        for sim in self._household.instanced_sims_gen():
            if sim.sim_info.species == Species.HUMAN:
                num_sims += 1
                resolver = DoubleSimResolver(pet_info, sim.sim_info)
                if self.RELATIONSHIP_TESTS.run_tests(resolver):
                    num_rel_tests_passed += 1
        return num_rel_tests_passed > num_sims/2

    def _run_motive_tests(self, pet_info):
        resolver = SingleSimResolver(pet_info)
        if pet_info.species == Species.DOG:
            return self.MOTIVE_TESTS_DOG.run_tests(resolver).result
        elif pet_info.species == Species.CAT:
            return self.MOTIVE_TESTS_CAT.run_tests(resolver).result
        return False

    def run_away(self, pet_info):
        if self.missing_pet_id != 0 or self._running_away:
            return
        if self._household.is_active_household and self._household.home_zone_id != services.current_zone_id():
            return
        if self._cooldown_alarm is not None:
            return
        pet = pet_info.get_sim_instance()
        if pet is None:
            return
        spawn_point = services.current_zone().get_spawn_point(lot_id=services.active_lot_id())
        routing_location = routing.Location(spawn_point.get_approximate_center(), sims4.math.Quaternion.ZERO(), spawn_point.routing_surface)
        if not routing.test_connectivity_pt_pt(pet.routing_location, routing_location, pet.routing_context):
            return
        if self._push_run_away_affordance(pet):
            if self.RUN_AWAY_NOTIFICATION is not None:
                dialog = self.RUN_AWAY_NOTIFICATION(pet_info, SingleSimResolver(pet_info))
                dialog.show_dialog()
            self._running_away = True

    def _push_run_away_affordance(self, pet_sim):
        if pet_sim is None or self.RUN_AWAY_INTERACTION is None:
            return EnqueueResult.NONE
        if not pet_sim.queue.can_queue_visible_interaction():
            return EnqueueResult.NONE
        if pet_sim.queue.has_duplicate_super_affordance(self.RUN_AWAY_INTERACTION, pet_sim, pet_sim):
            return EnqueueResult.NONE
        context = InteractionContext(pet_sim, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.LAST)
        result = pet_sim.push_super_affordance(self.RUN_AWAY_INTERACTION, pet_sim, context)
        return result

    def run_away_succeeded(self, pet_info):
        self._running_away = False
        if self._missing_pet_id != 0:
            return
        self._missing_pet_id = pet_info.id
        pet_info.add_trait(self.MISSING_PET_TRAIT)
        away_action = self.DEFAULT_AWAY_ACTIONS.get(pet_info.species)
        services.hidden_sim_service().hide_sim(pet_info.id, default_away_action=away_action)
        if self._test_alarm:
            alarms.cancel_alarm(self._test_alarm)
            self._test_alarm = None
        return_interval = clock.interval_in_sim_minutes(self.RETURN_INTERVAL)
        self._add_return_alarm(return_interval)
        for sim_info in self._household.sim_info_gen():
            if sim_info.id != pet_info.id:
                resolver = DoubleSimResolver(sim_info, pet_info)
                self.RUN_AWAY_LOOT_FOR_HOUSEHOLD.apply_to_resolver(resolver)
        sim_filter_service = services.sim_filter_service()
        sim_filter_service.add_sim_id_to_global_blacklist(pet_info.id, SimFilterGlobalBlacklistReason.MISSING_PET)
        services.get_first_client().send_selectable_sims_update()

    def run_away_interaction_released(self, pet_info):
        if self.missing_pet_id == 0:
            self._running_away = False
        else:
            self._return_pet(pet_info)

    def intercept_skewer_command(self, pet_info):
        dialog = self.SKEWER_NOTIFICATION(pet_info, SingleSimResolver(pet_info))
        dialog.show_dialog()

    def post_alert(self):
        if self._return_alarm is None:
            return
        remaining_time = self._return_alarm.get_remaining_time()
        alarms.cancel_alarm(self._return_alarm)
        remaining_time *= 1 - self.POST_ALERT_EFFECTIVENESS.random_float()
        self._add_return_alarm(remaining_time)
        self._alert_posted = True

    def cancel_run_away_interaction(self):
        if self._household.is_active_household and self._household.home_zone_id != services.current_zone_id():
            self._return_pet_on_zone_load = True
            return
        pet = self.missing_pet_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED)
        for interaction in pet.get_running_and_queued_interactions_by_tag({self.RUN_AWAY_INTERACTION_TAG}):
            interaction.cancel(FinishingType.NATURAL, cancel_reason_msg='Return missing pet.', ignore_must_run=True)

    def _return_pet(self, pet_info):
        if services.current_zone().is_zone_shutting_down:
            return
        pet = pet_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED)
        if pet is not None and self.RETURN_INTERACTION is not None:
            context = InteractionContext(pet, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
            pet.push_super_affordance(self.RETURN_INTERACTION, pet, context)
        pet_info.remove_trait(self.MISSING_PET_TRAIT)
        self._clear_missing_pet_data(pet_info.id)
        cooldown_interval = clock.interval_in_sim_minutes(self.COOLDOWN_INTERVAL)
        self._add_cooldown_alarm(cooldown_interval)

    def _clear_missing_pet_data(self, pet_id):
        self._missing_pet_id = 0
        self._alert_posted = False
        if self._return_alarm is not None:
            alarms.cancel_alarm(self._return_alarm)
            self._return_alarm = None
        sim_filter_service = services.sim_filter_service()
        global_blacklist = sim_filter_service.get_global_blacklist()
        if pet_id in global_blacklist:
            sim_filter_service.remove_sim_id_from_global_blacklist(pet_id, SimFilterGlobalBlacklistReason.MISSING_PET)
        services.hidden_sim_service().unhide_sim(pet_id)
        services.get_first_client().send_selectable_sims_update()

    def _cooldown_complete(self):
        self._cooldown_alarm = None
        test_interval = clock.interval_in_sim_minutes(self.TEST_INTERVAL)
        self._add_test_alarm(test_interval)

    def household_lod_cleanup(self):
        self._initialize_pet_tracker_attributes()

    def save_data(self, household_msg):
        if self._missing_pet_id != 0:
            household_msg.missing_pet_tracker_data.missing_pet_id = self._missing_pet_id
        if self._test_alarm is not None:
            household_msg.missing_pet_tracker_data.test_alarm_finishing_time = self._test_alarm.get_remaining_time().in_ticks()
        if self._return_alarm is not None:
            household_msg.missing_pet_tracker_data.return_alarm_finishing_time = self._return_alarm.get_remaining_time().in_ticks()
        if self._cooldown_alarm is not None:
            household_msg.missing_pet_tracker_data.cooldown_alarm_finishing_time = self._cooldown_alarm.get_remaining_time().in_ticks()
        household_msg.missing_pet_tracker_data.return_pet_on_zone_load = self._return_pet_on_zone_load
        household_msg.missing_pet_tracker_data.running_away = self._running_away
        household_msg.missing_pet_tracker_data.alert_posted = self._alert_posted
        for (pet_id, test_results) in self._motive_test_results.items():
            with ProtocolBufferRollback(household_msg.missing_pet_tracker_data.motive_test_results) as msg:
                msg.pet_id = pet_id
                for result in test_results:
                    msg.test_results.append(result)

    def load_data(self, household_proto):
        self._missing_pet_id = household_proto.missing_pet_tracker_data.missing_pet_id
        self._return_pet_on_zone_load = household_proto.missing_pet_tracker_data.return_pet_on_zone_load
        self._running_away = household_proto.missing_pet_tracker_data.running_away
        self._alert_posted = household_proto.missing_pet_tracker_data.alert_posted
        if household_proto.missing_pet_tracker_data.test_alarm_finishing_time != 0:
            test_alarm_interval = household_proto.missing_pet_tracker_data.test_alarm_finishing_time
            test_interval = TimeSpan(test_alarm_interval)
            self._add_test_alarm(test_interval)
        if household_proto.missing_pet_tracker_data.return_alarm_finishing_time != 0:
            return_alarm_interval = household_proto.missing_pet_tracker_data.return_alarm_finishing_time
            return_interval = TimeSpan(return_alarm_interval)
            self._add_return_alarm(return_interval)
        if household_proto.missing_pet_tracker_data.cooldown_alarm_finishing_time != 0:
            cooldown_alarm_interval = household_proto.missing_pet_tracker_data.cooldown_alarm_finishing_time
            cooldown_interval = clock.TimeSpan(cooldown_alarm_interval)
            self._add_cooldown_alarm(cooldown_interval)

    def fix_up_data(self):
        if self._missing_pet_id != 0 and self._missing_pet_id is not None and self._household.get_sim_info_by_id(self._missing_pet_id) is None:
            self._clear_missing_pet_data(self._missing_pet_id)

    def _add_test_alarm(self, interval):
        repeat_interval = clock.interval_in_sim_minutes(self.TEST_INTERVAL)
        self._test_alarm = alarms.add_alarm(self, interval, lambda _: self._run_tests(), repeating=True, repeating_time_span=repeat_interval, cross_zone=True)

    def _add_return_alarm(self, interval):
        self._return_alarm = alarms.add_alarm(self, interval, lambda _: self.cancel_run_away_interaction(), cross_zone=True)

    def _add_cooldown_alarm(self, interval):
        self._cooldown_alarm = alarms.add_alarm(self, interval, lambda _: self._cooldown_complete(), cross_zone=True)

    def get_missing_pet_data_for_gsi(self):
        data = {}
        data['household_id'] = str(self._household.id)
        data['household'] = self._household.name
        if self.missing_pet_id != 0:
            sim_info_manager = services.sim_info_manager()
            sim_info = sim_info_manager.get(self.missing_pet_id)
            data['sim_id'] = str(self.missing_pet_id)
            data['sim'] = sim_info.full_name
        if self._test_alarm is not None:
            data['run_test_absolute'] = str(self._test_alarm._element_handle.when)
            data['run_test_time_left'] = str(self._test_alarm.get_remaining_time())
        if self._return_alarm is not None:
            data['return_time_absolute'] = str(self._return_alarm._element_handle.when)
            data['return_time_left'] = str(self._return_alarm.get_remaining_time())
        if self._cooldown_alarm is not None:
            data['cooldown_absolute'] = str(self._cooldown_alarm._element_handle.when)
            data['cooldown_time_left'] = str(self._cooldown_alarm.get_remaining_time())
        return data
