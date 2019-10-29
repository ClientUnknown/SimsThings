from event_testing.resolver import DataResolverfrom event_testing.results import TestResultNumericfrom objects.object_tests import ObjectCriteriaTestfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactoryfrom sims4.tuning.tunable_base import GroupNamesimport objects.object_testsimport servicesimport sims4.tuningimport situations.situation_goal
class SituationGoalObjectCount(situations.situation_goal.SituationGoal, AutoFactoryInit, HasTunableSingletonFactory):
    INSTANCE_TUNABLES = {'object_criteria_test': objects.object_tests.ObjectCriteriaTest.TunableFactory(description='\n            Object criteria test to run to figure out how many objects\n            of the objects we care for are on the lot.\n            ', tuning_group=GroupNames.TESTS)}

    def __init__(self, *args, reader=None, **kwargs):
        super().__init__(*args, reader=reader, **kwargs)
        self._current_count = 0
        resolver = DataResolver(self._sim_info)
        test_result = resolver(self.object_criteria_test)
        if isinstance(test_result, TestResultNumeric):
            self._current_count = test_result.current_value

    def setup(self):
        super().setup()
        services.get_event_manager().register(self, self.object_criteria_test.test_events)

    def _decommision(self):
        services.get_event_manager().unregister(self, self.object_criteria_test.test_events)
        super()._decommision()

    def handle_event(self, sim_info, event, resolver):
        self._test_and_send_info(resolver)

    def _test_and_send_info(self, resolver):
        test_result = resolver(self.object_criteria_test)
        if isinstance(test_result, TestResultNumeric):
            self._current_count = test_result.current_value
        if self._current_count >= self.max_iterations or test_result:
            super()._on_goal_completed()
        else:
            self._on_iteration_completed()

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        return False

    @property
    def completed_iterations(self):
        return self._current_count

    @property
    def max_iterations(self):
        subject_specific_tests = self.object_criteria_test.subject_specific_tests
        if subject_specific_tests.subject_type == ObjectCriteriaTest.ALL_OBJECTS:
            return int(subject_specific_tests.quantity.value)
        else:
            return 1
sims4.tuning.instances.lock_instance_tunables(SituationGoalObjectCount, score_on_iteration_complete=None, _iterations=1)