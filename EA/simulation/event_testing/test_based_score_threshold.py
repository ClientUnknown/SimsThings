from event_testing.resolver import RESOLVER_PARTICIPANTfrom event_testing.results import TestResultfrom interactions import ParticipantTypefrom sims4.math import Operatorfrom sims4.tuning.tunable import TunableSingletonFactory, TunableThreshold, TunableEnumEntry, TunableReferenceimport event_testing.test_baseimport servicesimport sims4.loglogger = sims4.log.Logger('Tests')
class TestBasedScoreThresholdTest(event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'description': 'Gate availability by a statistic on the actor or target.', 'who': TunableEnumEntry(ParticipantType, ParticipantType.Actor, description='Who or what to apply this test to.'), 'test_based_score': TunableReference(services.test_based_score_manager(), description='The specific cumulative test.  This is pack safe because this particular test was being used for module tuning, so be careful that you are not referencing from one pack to the next.', pack_safe=True), 'threshold': TunableThreshold(description="The threshold to control availability based on the statistic's value")}

    def __init__(self, who, test_based_score, threshold, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)
        self.who = who
        self.test_based_score = test_based_score
        self.threshold = threshold

    def get_expected_args(self):
        return {'resolver': RESOLVER_PARTICIPANT}

    def __call__(self, resolver=None):
        if self.test_based_score is None:
            return TestResult(False, 'Failed, no test_based_score provided.')
        score = self.test_based_score.get_score(resolver)
        if not self.threshold.compare(score):
            operator_symbol = Operator.from_function(self.threshold.comparison).symbol
            return TestResult(False, 'Failed {}. Current Score: {}. Operator: {}. Threshold: {}', self.test_based_score.__name__, score, operator_symbol, self.threshold, tooltip=self.tooltip)
        return TestResult.TRUE
TunableTestBasedScoreThresholdTest = TunableSingletonFactory.create_auto_factory(TestBasedScoreThresholdTest)