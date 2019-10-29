from event_testing import test_basefrom event_testing.results import TestResultfrom event_testing.test_events import cached_testfrom interactions import ParticipantTypeActorTargetSimfrom routing.walkstyle.walkstyle_behavior import WalksStyleBehaviorfrom routing.walkstyle.walkstyle_tuning import TunableWalkstylefrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry
class WalkstyleCostTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject of this test.\n            ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor), 'walkstyle': TunableWalkstyle(description='\n            Walkstyle that will be evaluated.\n            ', pack_safe=True)}

    def get_expected_args(self):
        return {'test_targets': self.subject}

    @cached_test
    def __call__(self, test_targets=None):
        if test_targets is None:
            return TestResult(False, 'Teleport cost test failed due no targets.', tooltip=self.tooltip)
        if self.walkstyle is None:
            return TestResult(False, 'Walkstyle is not found, this is probably caused by a pack safe test.', tooltip=self.tooltip)
        for target_sim in test_targets:
            walkstyle_cost = WalksStyleBehavior.WALKSTYLE_COST.get(self.walkstyle, None)
            if walkstyle_cost is not None:
                current_value = target_sim.get_stat_value(walkstyle_cost.walkstyle_cost_statistic)
                if current_value is None:
                    return TestResult(False, 'Sim {} doesnt have the statitic needed for the walkstyle {}.', target_sim, self.walkstyle, tooltip=self.tooltip)
                if current_value - walkstyle_cost.cost < walkstyle_cost.walkstyle_cost_statistic.min_value:
                    return TestResult(False, 'Sim {} cannot afford the walkstyle {}.', target_sim, self.walkstyle, tooltip=self.tooltip)
        return TestResult.TRUE
