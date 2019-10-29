from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import cached_testfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactoryimport services
class PlayerPopulationTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):

    def get_expected_args(self):
        return {}

    @cached_test
    def __call__(self):
        culling_service = services.get_culling_service()
        max_player_population = culling_service.get_max_player_population()
        if max_player_population:
            household_manager = services.household_manager()
            player_population = sum(len(household) for household in household_manager.values() if household.is_player_household)
            if player_population >= max_player_population:
                return TestResult(False, 'Over the maximum player population ({}/{})', player_population, max_player_population, tooltip=lambda *_, **__: self.tooltip(player_population, max_player_population))
        return TestResult.TRUE
