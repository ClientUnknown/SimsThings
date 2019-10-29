from event_testing.results import TestResultfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, Tunableimport event_testing.test_baseimport services
class CurfewTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'curfew_active': Tunable(description='\n            If True the test will return True if the current lot is under\n            curfew restrictions. If not checked it will only return True when\n            outside of curfew enforced hours.\n            ', tunable_type=bool, default=True)}

    def get_expected_args(self):
        return {}

    def __call__(self):
        lot_curfew_active = services.get_curfew_service().is_curfew_active_on_lot_id(services.current_zone_id())
        if self.curfew_active == lot_curfew_active:
            return TestResult.TRUE
        return TestResult(False, 'Curfew Active is supposed to be {} and it is {}', self.curfew_active, lot_curfew_active, tooltip=self.tooltip)
