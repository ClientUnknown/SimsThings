from sims4.tuning.tunable_base import GroupNamesimport event_testing.testsimport objects.object_testsimport servicesimport sims4.tuning.instancesimport situations.situation_goal
class SituationGoalPurchasedObject(situations.situation_goal.SituationGoal):
    INSTANCE_TUNABLES = {'purchased_object_test': objects.object_tests.ObjectPurchasedTest.TunableFactory(tuning_group=GroupNames.TESTS)}

    def setup(self):
        super().setup()
        services.get_event_manager().register(self, self.purchased_object_test.test_events)

    def _decommision(self):
        services.get_event_manager().unregister(self, self.purchased_object_test.test_events)
        super()._decommision()

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        if not resolver(self.purchased_object_test):
            return False
        return super()._run_goal_completion_tests(sim_info, event, resolver)

    @property
    def _numerical_token(self):
        return int(self.purchased_object_test.value)
sims4.tuning.instances.lock_instance_tunables(SituationGoalPurchasedObject, _iterations=1, _post_tests=event_testing.tests.TestList())