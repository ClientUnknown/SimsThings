from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import TestEventfrom sims4.resources import Typesfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableReference, TunableVariantfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport services
class _ActiveNarrativeTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'narratives': TunableWhiteBlackList(tunable=TunableReference(manager=services.get_instance_manager(Types.NARRATIVE)))}

    def test(self, tooltip):
        if self.narratives.test_collection(services.narrative_service().active_narratives):
            return TestResult.TRUE
        return TestResult(False, 'Failed to pass narrative white/black list.', tooltip=tooltip)

class _LockedNarrativeTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'narratives': TunableWhiteBlackList(tunable=TunableReference(manager=services.get_instance_manager(Types.NARRATIVE)))}

    def test(self, tooltip):
        if self.narratives.test_collection(services.narrative_service().locked_narratives):
            return TestResult.TRUE
        return TestResult(False, 'Failed to pass narrative white/black list.', tooltip=tooltip)

class _CompletedNarrativeTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'narratives': TunableWhiteBlackList(tunable=TunableReference(manager=services.get_instance_manager(Types.NARRATIVE)))}

    def test(self, tooltip):
        if self.narratives.test_collection(services.narrative_service().completed_narratives):
            return TestResult.TRUE
        return TestResult(False, 'Failed to pass narrative white/black list.', tooltip=tooltip)

class NarrativeTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'test_type': TunableVariant(description='\n            The type of test to run.\n            ', active_narrative_test=_ActiveNarrativeTest.TunableFactory(), completed_narrative_test=_CompletedNarrativeTest.TunableFactory(), locked_narrative_test=_LockedNarrativeTest.TunableFactory(), default='active_narrative_test')}

    def get_expected_args(self):
        return {}

    def get_custom_event_registration_keys(self):
        keys = []
        narratives_to_register = self.test_type.narratives.get_items()
        for narrative in narratives_to_register:
            keys.append((TestEvent.NarrativesUpdated, narrative))
        return keys

    def __call__(self):
        return self.test_type.test(self.tooltip)
