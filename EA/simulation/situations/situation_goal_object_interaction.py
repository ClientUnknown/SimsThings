from event_testing.results import TestResultfrom event_testing.tests_with_data import TunableParticipantRanInteractionTestfrom interactions import ParticipantType, ParticipantTypeSimfrom sims4.tuning.tunable import TunableVariantfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_goal import SituationGoalimport event_testing.state_testsimport event_testing.test_variantsimport objects.object_testsimport servicesimport sims.sim_info_testsimport statistics.skill_testsimport world.world_tests
class TunableSituationGoalActorObjectPostTestVariant(TunableVariant):

    def __init__(self, description='A single tunable test.', **kwargs):
        super().__init__(state=event_testing.state_tests.TunableStateTest(locked_args={'who': ParticipantType.Object, 'tooltip': None}), statistic=event_testing.statistic_tests.StatThresholdTest.TunableFactory(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), skill_tag=statistics.skill_tests.SkillTagThresholdTest.TunableFactory(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), mood=sims.sim_info_tests.MoodTest.TunableFactory(locked_args={'who': ParticipantTypeSim.Actor, 'tooltip': None}), location=world.world_tests.LocationTest.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'tooltip': None}), sim_info=sims.sim_info_tests.SimInfoTest.TunableFactory(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), trait=sims.sim_info_tests.TraitTest.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'tooltip': None}), topic=event_testing.test_variants.TunableTopicTest(locked_args={'subject': ParticipantType.Actor, 'target_sim': ParticipantType.TargetSim, 'tooltip': None}), buff=sims.sim_info_tests.BuffTest.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'tooltip': None}), motive=event_testing.statistic_tests.MotiveThresholdTest.TunableFactory(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), situation_job=event_testing.test_variants.TunableSituationJobTest(locked_args={'participant': ParticipantType.Actor, 'tooltip': None}), object_criteria=objects.object_tests.ObjectCriteriaTest.TunableFactory(locked_args={'tooltip': None}), description=description, **kwargs)

class TunableSituationGoalActorObjectPostTestSet(event_testing.tests.TestListLoadingMixin):
    DEFAULT_LIST = event_testing.tests.TestList()

    def __init__(self, description=None, **kwargs):
        if description is None:
            description = 'A list of tests.  All tests must succeed to pass the TestSet.'
        super().__init__(description=description, tunable=TunableSituationGoalActorObjectPostTestVariant(), **kwargs)

class SituationGoalObjectInteraction(SituationGoal):
    INSTANCE_TUNABLES = {'_goal_test': TunableParticipantRanInteractionTest(locked_args={'participant': ParticipantType.Actor, 'tooltip': None}, tuning_group=GroupNames.TESTS), '_post_tests': TunableSituationGoalActorObjectPostTestSet(description='\n                A set of tests that must all pass when the player satisfies the goal_test \n                for the goal to be consider completed.', tuning_group=GroupNames.TESTS)}

    @classmethod
    def can_be_given_as_goal(cls, actor, situation, **kwargs):
        result = super(SituationGoalObjectInteraction, cls).can_be_given_as_goal(actor, situation)
        if not result:
            return result
        return TestResult.TRUE

    def setup(self):
        super().setup()
        services.get_event_manager().register_tests(self, (self._goal_test,))

    def _decommision(self):
        services.get_event_manager().unregister_tests(self, (self._goal_test,))
        super()._decommision()

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        if not resolver(self._goal_test):
            return False
        return super()._run_goal_completion_tests(sim_info, event, resolver)
