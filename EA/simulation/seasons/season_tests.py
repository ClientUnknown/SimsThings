from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import TestEventfrom seasons.seasons_enums import SeasonType, SeasonSegmentfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableEnumSet, OptionalTunable, Tunableimport services
class SeasonTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'seasons': TunableEnumSet(description='\n            Season(s) that we must be in to pass the test.\n            ', minlength=1, enum_type=SeasonType), 'time_of_season': OptionalTunable(TunableEnumSet(description='\n                Portion(s) of season(s) that we must be in to pass the test.\n                ', minlength=1, enum_type=SeasonSegment)), 'requires_seasons_pack': Tunable(description='\n            If checked, this test will require that the Seasons pack be \n            installed in order for the seasons test to pass.  If unchecked, \n            this test will automatically pass.\n            ', tunable_type=bool, default=True)}
    test_events = (TestEvent.SeasonChanged,)

    def get_expected_args(self):
        return {}

    def __call__(self):
        season_service = services.season_service()
        if season_service is None:
            if self.requires_seasons_pack:
                return TestResult(False, 'Season service not available.', tooltip=self.tooltip)
            return TestResult.TRUE
        if season_service.season not in self.seasons:
            return TestResult(False, 'Currently {}, but we want one of {}', season_service.season, self.seasons, tooltip=self.tooltip)
        if self.time_of_season is not None and season_service.season_content.get_segment(services.time_service().sim_now) not in self.time_of_season:
            return TestResult(False, 'Currently {}, but we want one of {}', season_service.season_content.get_segment(services.time_service().sim_now), self.time_of_season, tooltip=self.tooltip)
        return TestResult.TRUE
