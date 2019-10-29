from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import cached_testfrom interactions import ParticipantTypeSingleSimfrom sims.occult.occult_enums import OccultTypefrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, Tunable
class OccultFormAvailabilityTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The Sim to which this test applies.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor, invalid_enums=(ParticipantTypeSingleSim.Invalid,)), 'occult_type': TunableEnumEntry(description='\n            The occult type to test against.\n            ', tunable_type=OccultType, default=OccultType.VAMPIRE), 'negate': Tunable(description='\n            If checked, negate the outcome such that if it would pass it will\n            now fail and vice-versa.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'sims': self.subject}

    @cached_test
    def __call__(self, sims):
        if not sims:
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, 'OccultFormAvailableTest: participant type {} did not result in a sim.', self.subject, tooltip=self.tooltip)
        for sim in sims:
            occult_tracker = sim.occult_tracker
            if not occult_tracker.has_occult_type(self.occult_type):
                if self.negate:
                    return TestResult.TRUE
                return TestResult(False, 'OccultFormAvailableTest: participant {} does not have the tuned occult type {}.', self.subject, self.occult_type, tooltip=self.tooltip)
            if not occult_tracker.is_occult_form_available:
                if self.negate:
                    return TestResult.TRUE
                return TestResult(False, 'OccultFormAvailableTest: participant {} has the provided occult type {} but is flagged as not having the occult form available.', self.subject, self.occult_type, tooltip=self.tooltip)
        if self.negate:
            return TestResult(False, 'OccultFormAvailableTest: The test passed but the negate option was checked.')
        return TestResult.TRUE
