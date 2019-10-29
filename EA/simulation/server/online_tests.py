from cas.cas import is_online_entitledfrom event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import cached_testfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, Tunable, TunableEnumEntry, TunableEntitlementimport mtximport server.config_serviceimport services
class IsLiveEventActive(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'event_id': Tunable(description='\n            The string associated with the live event to be tested. If that\n            live event is active, this test will return True.\n            ', tunable_type=str, default='Undefined')}

    def get_expected_args(self):
        return {}

    @cached_test
    def __call__(self):
        if not services.is_event_enabled(self.event_id):
            return TestResult(False, 'Event is not active.', tooltip=self.tooltip)
        return TestResult.TRUE

class IsOnlineTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'negate': Tunable(description='\n            If checked the test will pass if the user is not online.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {}

    @cached_test
    def __call__(self):
        if is_online_entitled():
            if self.negate:
                return TestResult(False, 'IsOnlineTest is looking for the user to be not online, but they are.', tooltip=self.tooltip)
            return TestResult.TRUE
        elif self.negate:
            return TestResult.TRUE
        else:
            return TestResult(False, 'IsOnlineTest is looking for the user to be online, but they are.', tooltip=self.tooltip)

class IsEntitledTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'negate': Tunable(description='\n            If checked the test will pass if the user is not entitled.\n            ', tunable_type=bool, default=False), 'entitlement': TunableEntitlement(description='\n            Entitlement to check against.\n            ')}

    def get_expected_args(self):
        return {}

    @cached_test
    def __call__(self):
        if mtx.has_entitlement(self.entitlement):
            if self.negate:
                return TestResult(False, 'IsOnlineTest is looking for the user to be not online, but they are.', tooltip=self.tooltip)
        else:
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, 'IsOnlineTest is looking for the user to be online, but they are.', tooltip=self.tooltip)
        return TestResult.TRUE

class ContentModeTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'mode': TunableEnumEntry(description='\n            Test returns true if the mode matches this enum.\n            ', tunable_type=server.config_service.ContentModes, default=server.config_service.ContentModes.PRODUCTION)}

    def get_expected_args(self):
        return {}

    @cached_test
    def __call__(self):
        current_mode = services.config_service().content_mode
        if current_mode != self.mode:
            return TestResult(False, 'Current content mode in the ConfigService does not allow this interaction.', tooltip=self.tooltip)
        return TestResult.TRUE
