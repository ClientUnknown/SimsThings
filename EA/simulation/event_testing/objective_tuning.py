from clubs.club_tests import ClubTestfrom crafting.photography_tests import TookPhotoTestfrom drama_scheduler.drama_node_tests import FestivalRunningTestfrom event_testing import TargetIdTypesfrom event_testing.event_data_const import ObjectiveDataStorageTypefrom event_testing.results import TestResultNumericfrom event_testing.test_events import TestEventfrom interactions import ParticipantType, ParticipantTypeSingleSim, ParticipantTypeSim, ParticipantTypeActorTargetSimfrom relationships.relationship_tests import TunableRelationshipTest, RelationshipBitTestfrom seasons.season_tests import SeasonTestfrom sims import unlock_tracker_testsfrom sims.sim_info_types import Agefrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, OptionalTunable, TunableEnumSetfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom vfx import TunablePlayEffectVariantimport aspirations.aspiration_testsimport enumimport event_testing.results as resultsimport event_testing.test_variantsimport event_testing.testsimport event_testing.tests_with_data as tests_with_dataimport objects.object_testsimport servicesimport sims.sim_info_testsimport sims4.logimport sims4.tuning.tunableimport statistics.skill_testsimport tagimport world.world_testsimport zone_testslogger = sims4.log.Logger('ObjectiveTuning', default_owner='jjacobson')
class ParticipantTypeActorHousehold(enum.IntFlags):
    Actor = ParticipantType.Actor
    ActiveHousehold = ParticipantType.ActiveHousehold

class ParticipantTypeTargetAllRelationships(enum.IntFlags):
    TargetSim = ParticipantType.TargetSim
    AllRelationships = ParticipantType.AllRelationships

class TunableObjectiveTestVariant(TunableVariant):

    def __init__(self, description='A tunable test supported for use as an objective.', **kwargs):
        super().__init__(at_work=event_testing.test_variants.AtWorkTest.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'tooltip': None}), buff_added=sims.sim_info_tests.BuffAddedTest.TunableFactory(locked_args={'tooltip': None}), career_attendence=tests_with_data.TunableCareerAttendenceTest(locked_args={'tooltip': None}), career_promoted=event_testing.test_variants.CareerPromotedTest.TunableFactory(locked_args={'tooltip': None}), career_test=event_testing.test_variants.TunableCareerTest.TunableFactory(locked_args={'subjects': ParticipantType.Actor, 'tooltip': None}), collected_item_test=event_testing.test_variants.CollectedItemTest.TunableFactory(locked_args={'tooltip': None}), collection_test=event_testing.test_variants.TunableCollectionThresholdTest(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), crafted_item=objects.object_tests.CraftedItemTest.TunableFactory(locked_args={'tooltip': None}), familial_trigger_test=tests_with_data.TunableFamilyAspirationTriggerTest(locked_args={'tooltip': None}), generation_created=tests_with_data.GenerationTest.TunableFactory(locked_args={'tooltip': None}), has_buff=sims.sim_info_tests.BuffTest.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'tooltip': None}), household_size=event_testing.test_variants.HouseholdSizeTest.TunableFactory(locked_args={'participant': ParticipantType.Actor, 'tooltip': None}), in_multiple_moods=event_testing.tests_with_data.InMultipleMoodsTest.TunableFactory(locked_args={'tooltip': None}), inventory=objects.object_tests.InventoryTest.TunableFactory(locked_args={'tooltip': None}), mood_test=sims.sim_info_tests.MoodTest.TunableFactory(locked_args={'who': ParticipantTypeSim.Actor, 'tooltip': None}), object_criteria=objects.object_tests.ObjectCriteriaTest.TunableFactory(locked_args={'tooltip': None}), object_purchase_test=objects.object_tests.ObjectPurchasedTest.TunableFactory(locked_args={'tooltip': None}), offspring_created_test=tests_with_data.OffspringCreatedTest.TunableFactory(locked_args={'tooltip': None}), ran_away_action_test=tests_with_data.TunableParticipantRanAwayActionTest(locked_args={'participant': ParticipantTypeActorTargetSim.Actor, 'tooltip': None}), ran_interaction_test=tests_with_data.TunableParticipantRanInteractionTest(locked_args={'participant': ParticipantType.Actor, 'tooltip': None}), relationship=TunableRelationshipTest(participant_type_override=(ParticipantTypeTargetAllRelationships, ParticipantTypeTargetAllRelationships.AllRelationships), locked_args={'tooltip': None}), relationship_bit=RelationshipBitTest.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'target': ParticipantType.TargetSim, 'tooltip': None}), season_test=SeasonTest.TunableFactory(locked_args={'tooltip': None}), selected_aspiration_test=aspirations.aspiration_tests.SelectedAspirationTest.TunableFactory(locked_args={'who': ParticipantTypeSingleSim.Actor, 'tooltip': None}), selected_aspiration_track_test=aspirations.aspiration_tests.SelectedAspirationTrackTest.TunableFactory(locked_args={'who': ParticipantTypeSingleSim.Actor, 'tooltip': None}), simoleons_earned=tests_with_data.TunableSimoleonsEarnedTest(locked_args={'tooltip': None}), simoleon_value=event_testing.test_variants.TunableSimoleonsTest(locked_args={'subject': ParticipantType.Actor, 'tooltip': None}), situation_running_test=event_testing.test_variants.TunableSituationRunningTest(locked_args={'tooltip': None}), skill_tag=statistics.skill_tests.SkillTagThresholdTest.TunableFactory(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), statistic=event_testing.statistic_tests.StatThresholdTest.TunableFactory(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), ranked_statistic=event_testing.statistic_tests.RankedStatThresholdTest.TunableFactory(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), total_simoleons_earned=event_testing.test_variants.TunableTotalSimoleonsEarnedTest(locked_args={'tooltip': None}), total_interaction_time_elapsed_by_tag=tests_with_data.TunableTotalTimeElapsedByTagTest(locked_args={'tooltip': None}), total_relationship_bit=tests_with_data.TunableTotalRelationshipBitTest(locked_args={'tooltip': None}), total_simoleons_earned_by_tag=tests_with_data.TunableTotalSimoleonsEarnedByTagTest(locked_args={'tooltip': None}), total_time_played=event_testing.test_variants.TunableTotalTimePlayedTest(locked_args={'tooltip': None}), total_zones_traveled=tests_with_data.TunableTotalTravelTest(locked_args={'tooltip': None}), trait=sims.sim_info_tests.TraitTest.TunableFactory(participant_type_override=(ParticipantTypeActorHousehold, ParticipantTypeActorHousehold.Actor), locked_args={'tooltip': None}), unlock_earned=event_testing.test_variants.TunableUnlockedTest(locked_args={'participant': ParticipantType.Actor, 'tooltip': None}), unlock_tracker_amount=sims.unlock_tracker_tests.UnlockTrackerAmountTest.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'tooltip': None}), whim_completed_test=tests_with_data.WhimCompletedTest.TunableFactory(locked_args={'tooltip': None}), zone=zone_tests.ZoneTest.TunableFactory(locked_args={'tooltip': None}), location_test=world.world_tests.LocationTest.TunableFactory(location_tests={'is_outside': False, 'is_natural_ground': False, 'is_in_slot': False, 'is_on_active_lot': False, 'is_on_level': False}), club_tests=ClubTest.TunableFactory(locked_args={'tooltip': None, 'club': ClubTest.CLUB_FROM_EVENT_DATA, 'room_for_new_members': None, 'subject_passes_membership_criteria': None, 'subject_can_join_more_clubs': None}), photo_taken=TookPhotoTest.TunableFactory(description='\n                A test for player taken photos.\n                '), purchase_perk_test=event_testing.test_variants.PurchasePerkTest.TunableFactory(description='\n                A test for which kind of perk is being purchased.\n                '), club_bucks_earned=event_testing.test_variants.TotalClubBucksEarnedTest.TunableFactory(description='\n                A test for how many club bucks have been earned by the Sim.\n                ', locked_args={'tooltip': None}), time_in_club_gatherings=event_testing.test_variants.TimeInClubGatheringsTest.TunableFactory(description='\n                A test for how much total time a Sim has spent in club \n                gatherings.\n                ', locked_args={'tooltip': None}), event_ran_successfully=event_testing.test_variants.EventRanSuccessfullyTest.TunableFactory(description='\n                This is a simple test that always returns true whenever one of\n                the tuned test events is processed.\n                ', locked_args={'tooltip': None}), festival_running=FestivalRunningTest.TunableFactory(description='\n                This is a test that triggers when the festival begins.\n                ', locked_args={'tooltip': None}), bucks_perk_unlocked=event_testing.test_variants.BucksPerkTest.TunableFactory(description='\n                A test for which kind of bucks perk is being unlocked\n                ', locked_args={'tooltip': None}), description=description, **kwargs)

class _ObjectiveCompletionType(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'increment_vfx': OptionalTunable(description='\n            If enabled, we will play an effect when this objective type\n            increments its data.\n            ', tunable=TunablePlayEffectVariant(description='\n                Effect to play on the Sim when they increment the data for this\n                objective completion type.\n                \n                Note: This effect should be one shot and not expect any sort of\n                lifetime.\n                '))}

    def on_increment_objective_data(self, event_data_tracker):
        if self.increment_vfx and not event_data_tracker.simless:
            sim_info = event_data_tracker.owner_sim_info
            if sim_info is not None:
                sim = sim_info.get_sim_instance()
                if sim is not None:
                    vfx = self.increment_vfx(sim)
                    vfx.start_one_shot()

    def get_number_required(self, test):
        raise NotImplementedError

    def get_if_money(self, test):
        return False

    @property
    def data_type(self):
        raise NotImplementedError

    def increment_data(self, objective, resolver, event_data_tracker, result, additional_result):
        raise NotImplementedError

    def check_objective_validity(self, objective):
        pass

    def check_if_should_test(self, resolver):
        return not resolver.on_zone_load

class SimInfoStatisticObjectiveTrack(_ObjectiveCompletionType):

    def get_number_required(self, test):
        return sims4.math.MAX_INT32

    @property
    def data_type(self):
        return ObjectiveDataStorageType.CountData

    def increment_data(self, objective, resolver, event_data_tracker, result, additional_result):
        data_object = event_data_tracker.data_object
        if result and additional_result:
            data_object.add_objective_value(objective, 1)
            self.on_increment_objective_data(event_data_tracker)
        count = data_object.get_objective_count(objective)
        return results.TestResultNumeric(False, 'Objective: not possible because sim info panel member.', current_value=count, goal_value=0, is_money=False)

class _IterationsObjectiveTrack(_ObjectiveCompletionType):
    FACTORY_TUNABLES = {'iterations_required_to_pass': sims4.tuning.tunable.TunableRange(description='\n            The number of times that the objective test must pass in order\n            for the objective to be considered complete.\n            ', tunable_type=int, default=1, minimum=1)}

    def get_number_required(self, test):
        return self.iterations_required_to_pass

    @property
    def data_type(self):
        return ObjectiveDataStorageType.CountData

    def increment_data(self, objective, resolver, event_data_tracker, result, additional_result):
        data_object = event_data_tracker.data_object
        if result and additional_result:
            data_object.add_objective_value(objective, 1)
            self.on_increment_objective_data(event_data_tracker)
        count = data_object.get_objective_count(objective)
        if count < self.get_number_required(objective.objective_test):
            return results.TestResultNumeric(False, 'Objective: not possible because sim info panel member.', current_value=count, goal_value=self.iterations_required_to_pass, is_money=False)
        return results.TestResult.TRUE

class _UniqueTargetsObjectiveTrack(_ObjectiveCompletionType):
    FACTORY_TUNABLES = {'unique_targets_required_to_pass': sims4.tuning.tunable.TunableRange(description='\n            The number of unique targets that need to be obtained in order for\n            the Objective to complete.\n            ', tunable_type=int, default=1, minimum=1), 'id_to_check': sims4.tuning.tunable.TunableEnumEntry(description="\n            Uniqueness can be by either instance id or definition id. For\n            example, crafting 2 plates of mac and cheese will have the same\n            definition id but different instance id's.\n            ", tunable_type=TargetIdTypes, default=TargetIdTypes.DEFAULT)}

    def get_number_required(self, test):
        return self.unique_targets_required_to_pass

    @property
    def data_type(self):
        return ObjectiveDataStorageType.IdData

    def increment_data(self, objective, resolver, event_data_tracker, result, additional_result):
        data_object = event_data_tracker.data_object
        if result and additional_result:
            target_id = resolver.get_target_id(objective.objective_test, self.id_to_check)
            if target_id is not None:
                data_object.add_objective_value(objective, target_id)
                self.on_increment_objective_data(event_data_tracker)
        count = data_object.get_objective_count(objective)
        if count < self.unique_targets_required_to_pass:
            return results.TestResultNumeric(False, 'Objective: not enough iterations.', current_value=count, goal_value=self.unique_targets_required_to_pass, is_money=False)
        return results.TestResult.TRUE

    def check_objective_validity(self, objective):
        if not objective.objective_test.UNIQUE_TARGET_TRACKING_AVAILABLE:
            logger.error('Objective {} tuned with test {} that has no unique target tracking available.', objective, objective.objective_test)

class _TagChecklistObjectiveTrack(_ObjectiveCompletionType):
    FACTORY_TUNABLES = {'unique_tags_required_to_pass': sims4.tuning.tunable.TunableRange(description='\n            The number of unique tags that must be taken into account before\n            the Objective is considered complete.\n            ', tunable_type=int, default=1, minimum=1), 'tag_checklist': sims4.tuning.tunable.TunableList(description='\n            A list of tags that we care about for the purposes of completing\n            this objective.\n            ', tunable=sims4.tuning.tunable.TunableEnumEntry(description='\n                A tag that will be checked against for the purposes of\n                completing this Objective.\n                ', tunable_type=tag.Tag, default=tag.Tag.INVALID))}

    def get_number_required(self, test):
        return self.unique_tags_required_to_pass

    @property
    def data_type(self):
        return ObjectiveDataStorageType.IdData

    def increment_data(self, objective, resolver, event_data_tracker, result, additional_result):
        data_object = event_data_tracker.data_object
        if additional_result:
            tags_to_test = resolver.get_tags(objective.objective_test)
            for tag_from_test in tags_to_test:
                for tag_from_objective in self.tag_checklist:
                    if tag_from_test is tag_from_objective:
                        data_object.add_objective_value(objective, tag_from_objective)
                        self.on_increment_objective_data(event_data_tracker)
                        break
        count = data_object.get_objective_count(objective)
        if result and count < self.unique_tags_required_to_pass:
            return results.TestResultNumeric(False, 'Objective: not enough iterations.', current_value=count, goal_value=self.unique_tags_required_to_pass, is_money=False)
        return results.TestResult.TRUE

    def check_objective_validity(self, objective):
        if not objective.objective_test.TAG_CHECKLIST_TRACKING_AVAILABLE:
            logger.error('Objective {} tuned with test {} that has no tag checklist tracking avilable', objective, objective.objective_test)

class _UniqueLocationsObjectiveTrack(_ObjectiveCompletionType):
    FACTORY_TUNABLES = {'unique_locations_required_to_pass': sims4.tuning.tunable.TunableRange(description='\n            The number of unique locations that the tests need to complete at\n            in order for the Objective to complete.\n            ', tunable_type=int, default=1, minimum=1)}

    def get_number_required(self, test):
        return self.unique_locations_required_to_pass

    @property
    def data_type(self):
        return ObjectiveDataStorageType.IdData

    def increment_data(self, objective, resolver, event_data_tracker, result, additional_result):
        data_object = event_data_tracker.data_object
        if result and additional_result:
            data_object.add_objective_value(objective, resolver.sim_info.zone_id)
            self.on_increment_objective_data(event_data_tracker)
        count = data_object.get_objective_count(objective)
        if count < self.unique_locations_required_to_pass:
            return results.TestResultNumeric(False, 'Objective: not enough matching location iterations.', current_value=count, goal_value=self.unique_locations_required_to_pass, is_money=False)
        return results.TestResult.TRUE

class _UniqueWorldsObjectiveTrack(_ObjectiveCompletionType):
    FACTORY_TUNABLES = {'unique_worlds_required_to_pass': sims4.tuning.tunable.TunableRange(description='\n            The number of Unique Streets the Objective tests must pass on for\n            this Objective to be considered complete.\n            ', tunable_type=int, default=1, minimum=1)}

    def get_number_required(self, test):
        return self.unique_worlds_required_to_pass

    @property
    def data_type(self):
        return ObjectiveDataStorageType.IdData

    def increment_data(self, objective, resolver, event_data_tracker, result, additional_result):
        data_object = event_data_tracker.data_object
        if result and additional_result:
            zone_id = resolver.sim_info.zone_id
            world_id = services.get_persistence_service().get_world_id_from_zone(zone_id)
            world_desc_id = services.get_world_description_id(world_id)
            if world_desc_id == 0:
                return results.TestResult(False, 'Unable to determine world for Zone {}', zone_id)
            if world_desc_id is not None:
                data_object.add_objective_value(objective, world_id)
                self.on_increment_objective_data(event_data_tracker)
        count = data_object.get_objective_count(objective)
        if count < self.unique_worlds_required_to_pass:
            return results.TestResultNumeric(False, 'Objective: not enough matching world iterations.', current_value=count, goal_value=self.unique_worlds_required_to_pass, is_money=False)
        return results.TestResult.TRUE

class _IterationsSingleSituation(_ObjectiveCompletionType):
    FACTORY_TUNABLES = {'iterations_required_to_pass': sims4.tuning.tunable.TunableRange(description='\n            The number of times that the objective test must pass in a\n            single situation for the objective to be considered complete.\n            ', tunable_type=int, default=1)}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_situation_id = 0

    def get_number_required(self, test):
        return self.iterations_required_to_pass

    @property
    def data_type(self):
        return ObjectiveDataStorageType.CountData

    def increment_data(self, objective, resolver, event_data_tracker, result, additional_result):
        data_object = event_data_tracker.data_object
        if result and additional_result:
            sim = resolver.sim_info.get_sim_instance()
            if sim is None:
                return results.TestResultNumeric(False, "Objective: Couldn't find sim instance.", current_value=data_object.get_objective_count(objective), goal_value=self.iterations_required_to_pass, is_money=False)
            user_facing_situation_id = 0
            for situation in services.get_zone_situation_manager().get_situations_sim_is_in(sim):
                if situation.is_user_facing:
                    user_facing_situation_id = situation.id
                    break
            if user_facing_situation_id == 0:
                return results.TestResultNumeric(False, 'Objective: Sim is not currently in a situation.', current_value=data_object.get_objective_count(objective), goal_value=self.iterations_required_to_pass, is_money=False)
            if user_facing_situation_id != self.current_situation_id:
                self.current_situation_id = user_facing_situation_id
                data_object.reset_objective_count(objective)
            data_object.add_objective_value(objective, 1)
            self.on_increment_objective_data(event_data_tracker)
        count = data_object.get_objective_count(objective)
        if count < self.iterations_required_to_pass:
            return results.TestResultNumeric(False, 'Objective: not enough iterations.', current_value=count, goal_value=self.iterations_required_to_pass, is_money=False)
        return results.TestResult.TRUE

class _UseTestResult(_ObjectiveCompletionType):
    FACTORY_TUNABLES = {'only_use_result_on_home_zone': sims4.tuning.tunable.Tunable(description='\n            If checked then no results will be calculated or replaced if\n            the test event is triggered on a lot other than the sim\'s home\n            zone.\n            \n            This is useful for tests such as "Having a lot value worth X" where\n            we would like to retain the value of the Sim\'s home within the UI\n            no matter which lot they are traveling to.\n            ', tunable_type=bool, default=False)}

    def get_number_required(self, test):
        return test.goal_value()

    @property
    def data_type(self):
        return ObjectiveDataStorageType.CountData

    def get_if_money(self, test):
        return test.is_goal_value_money

    def check_if_should_test(self, resolver):
        if not self.only_use_result_on_home_zone:
            return True
        active_household = services.active_household()
        if active_household is None:
            return False
        return active_household.home_zone_id == services.current_zone_id()

    def increment_data(self, objective, resolver, event_data_tracker, result, additional_result):
        data_object = event_data_tracker.data_object
        if result:
            data_object.set_objective_value(objective, self.get_number_required(objective.objective_test))
            self.on_increment_objective_data(event_data_tracker)
            return results.TestResult.TRUE
        if not isinstance(result, TestResultNumeric):
            return result
        else:
            data_object.set_objective_value(objective, result.current_value)
            self.on_increment_objective_data(event_data_tracker)
            return result

    def check_objective_validity(self, objective):
        if objective.additional_tests:
            logger.error('Additional tests tuned on objective {}.  These tests will not be run with the Use Test Result Completion type.', objective)

class BaseObjective:
    INSTANCE_TUNABLES = {'display_text': TunableLocalizedStringFactory(description='\n            The single line description of the objective as it appears in\n            various panels.\n            ', allow_none=True, export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'display_age_list': OptionalTunable(description='\n            If enabled, the Sim must be one of the specified ages for the\n            Objective to be displayed in the UI.  This does not create any\n            Gameplay side checks to prevent this Objective from being completed\n            anyways.\n            ', tunable=TunableEnumSet(enum_type=Age, enum_default=Age.ADULT, default_enum_list=[Age.TODDLER, Age.CHILD, Age.TEEN, Age.YOUNGADULT, Age.ADULT, Age.ELDER]), enabled_by_default=False, export_class_name='DisplayAgeListOptionalTunable', export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'satisfaction_points': sims4.tuning.tunable.Tunable(description='\n            The number of satisfaction points received upon the completion of\n            this Objective.\n            ', tunable_type=int, default=0, export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.REWARDS), 'resettable': sims4.tuning.tunable.Tunable(description='\n            Setting this allows for this objective to reset back to zero for\n            certain uses, such as for Whim Set activation.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.SPECIAL_CASES), 'tooltip': TunableLocalizedStringFactory(description='\n            The tooltip of the Objective.\n            ', allow_none=True, export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'relative_to_unlock_moment': sims4.tuning.tunable.Tunable(description="\n            If true this objective will start counting from the moment of\n            assignment or reset instead of over the total lifetime of a Sim,\n            most useful for Careers and Whimsets.\n            \n            Note: this effect is only for 'Total' data tests (tests that used\n            persisted save data)\n             ", tunable_type=bool, default=False, tuning_group=GroupNames.SPECIAL_CASES)}

    @classmethod
    def setup_objective(cls, event_data_tracker, milestone):
        raise NotImplementedError

    def cleanup_objective(self, event_data_tracker, milestone):
        raise NotImplementedError

    @classmethod
    def goal_value(cls):
        raise NotImplementedError

    @classproperty
    def is_goal_value_money(cls):
        return False

    @classmethod
    def run_test(cls, event, resolver, event_data_tracker):
        return results.TestResult(False, "Objective doesn't complete utilizing tests.")

    @classmethod
    def reset_objective(cls, objective_data):
        pass

class Objective(BaseObjective, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.OBJECTIVE)):
    INSTANCE_TUNABLES = {'objective_test': TunableObjectiveTestVariant(description='\n            The test to run in order to mark this Objective as complete.\n            ', tuning_group=GroupNames.CORE), 'additional_tests': event_testing.tests.TunableTestSet(description='\n            Additional tests that must be true when the Objective Test passes\n            in order for the Objective consider having passed.\n            \n            Note: This does not run if you are using Use Test Result as the\n            Objective Completion Type.\n            ', tuning_group=GroupNames.CORE), 'objective_completion_type': TunableVariant(iterations=_IterationsObjectiveTrack.TunableFactory(), sim_info_statistic=SimInfoStatisticObjectiveTrack.TunableFactory(), unique_targets=_UniqueTargetsObjectiveTrack.TunableFactory(), unique_locations=_UniqueLocationsObjectiveTrack.TunableFactory(), unique_worlds=_UniqueWorldsObjectiveTrack.TunableFactory(), tag_checklist=_TagChecklistObjectiveTrack.TunableFactory(), iterations_single_situation=_IterationsSingleSituation.TunableFactory(), use_test_result=_UseTestResult.TunableFactory(), default='iterations', description='\n           The type of check that will be used to determine the counting method\n           of when this Objective will be considered complete.  See the comment\n           on each choice for more information.\n           -------------------------------------------------------------------\n           Primary Cases\n           - Iterations: Each time the tests pass we will add 1 to the\n               iterations counter.  When the test passes a certain number of\n               iterations.\n               \n           - Use Test Result: The Objective\'s completion and display within the\n               UI is entirely dependent on the result from the test rather than\n               counting the number of times that the tests passed.  Additional\n               tests cannot be used in conjunction with this.\n           -------------------------------------------------------------------\n           Special Cases:\n           - Unique Targets: Works similar to the \'Iterations\' completion type\n               except that instead of just doing a singular count a \'target\' id\n               extracted from the test will be stored off instead.  When enough\n               unique ids have been stored off then the objective will\n               complete.  Not all tests support this completion type.  See the\n               comment on the type itself for a list.  If you would like to\n               have a new test supported, talk to your GPE partner.\n           \n           - Unique Locations: Works similar to the \'Iterations\' completion\n               type except that instead of just doing a singular count the\n               zone id will be store off instead.  When the tests have been\n               completed in enough zones then the Objective will complete.\n            \n            - Unique Worlds: Works just like \'Unique Locations\' except that it\n                tracks Streets rather than specific zones.\n           \n           - Tag Checklist: Track an iteration count of one completion per tag \n               tuned on the list. Ex. Paint 4 paintings of different genres,\n               in this case you would tune a count of "4" and add all genre\n               tags to the tag list. Each painting created would only count if\n               it was not from a genre tag previously entered. In order to\n               support this functionality, each painting object created would\n               need to be tagged with it\'s genre upon creation, which can be\n               tuned in Recipe.\n           \n           - Iterations Single Situation: This tests the total number of times\n               that the tests have passed during a single situation.  If the\n               situation ends, the count will reset when the tests pass the\n               for first time during a new situation.  The objective is\n               considered complete when the the number of times it has passed\n               is equal to the tuned number of times it should pass.\n           \n           - Sim Info Statistic: Works like the \'Iterations\' completion type\n               except that it never actually completes.  Primarily used for\n               the Sim Info Statistics panel which uses Aspirations that don\'t\n               actually complete.\n           ', tuning_group=GroupNames.CORE)}

    @classmethod
    def setup_objective(cls, event_data_tracker, milestone):
        services.get_event_manager().register_tests(milestone, (cls.objective_test,))

    @classmethod
    def cleanup_objective(cls, event_data_tracker, milestone):
        pass

    @classmethod
    def goal_value(cls):
        return cls.objective_completion_type.get_number_required(cls.objective_test)

    @classproperty
    def is_goal_value_money(cls):
        return cls.objective_completion_type.get_if_money(cls.objective_test)

    @classproperty
    def data_type(cls):
        return cls.objective_completion_type.data_type

    @classmethod
    def _verify_tuning_callback(cls):
        cls.objective_test.validate_tuning_for_objective(cls)
        cls.objective_completion_type.check_objective_validity(cls)
        if cls.objective_test.USES_DATA_OBJECT:
            pass

    @classmethod
    def _get_current_iterations_test_result(cls, objective_data):
        return results.TestResultNumeric(False, 'Objective: not enough iterations.', current_value=objective_data.get_objective_count(cls.guid64), goal_value=cls.objective_completion_type.get_number_required(), is_money=False)

    @classmethod
    def run_test(cls, event, resolver, event_data_tracker):
        if event not in cls.objective_test.test_events and event != TestEvent.UpdateObjectiveData:
            return results.TestResult(False, 'Objective test not present in event set.')
        if not cls.objective_completion_type.check_if_should_test(resolver):
            return results.TestResult(False, 'Objective completion type prevents testing this objective.')
        test_result = resolver(cls.objective_test, data_object=event_data_tracker.data_object, objective_guid64=cls.guid64)
        if test_result:
            additional_test_results = cls.additional_tests.run_tests(resolver)
        else:
            additional_test_results = results.TestResult.NONE
        return cls.objective_completion_type.increment_data(cls, resolver, event_data_tracker, test_result, additional_test_results)

    @classmethod
    def reset_objective(cls, objective_data):
        objective_data.reset_objective_count(cls)
        cls.set_starting_point(objective_data)

    @classmethod
    def set_starting_point(cls, objective_data):
        if cls.relative_to_unlock_moment:
            cls.objective_test.save_relative_start_values(cls.guid64, objective_data)
            return True
        return False
