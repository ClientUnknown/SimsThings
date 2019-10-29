from event_testing.results import TestResultfrom sims4.resources import Typesfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableVariant, Tunable, TunableReference, TunablePackSafeReferencefrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport event_testing.test_baseimport servicesimport sims4.resources
class HolidaysRunningTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'count_pre_holiday_time': Tunable(description='\n            Should holidays that are in pre-holiday mode count?\n            ', tunable_type=bool, default=False), 'invert': Tunable(description='\n            Invert the results of this test.\n            ', tunable_type=bool, default=False)}

    def _evaluate(self, test):
        active_household = services.active_household()
        if active_household is None:
            return TestResult(False, 'There is no active household to test against.', tooltip=test.tooltip)
        holiday_tracker = active_household.holiday_tracker
        if self.count_pre_holiday_time:
            holiday_active = holiday_tracker.get_active_or_upcoming_holiday() is not None
        else:
            holiday_active = holiday_tracker.active_holiday_id is not None
        if self.invert:
            if holiday_active:
                return TestResult(False, "A holiday is active, but we don't want any to be.", tooltip=test.tooltip)
        elif not holiday_active:
            return TestResult(False, 'No holiday is active, but we want one to be.', tooltip=test.tooltip)
        return TestResult.TRUE

class SpecificHolidaysTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'holiday_drama_node': TunablePackSafeReference(description='\n            The holiday drama node we are interested in.\n            ', manager=services.get_instance_manager(Types.DRAMA_NODE), class_restrictions=('HolidayDramaNode',)), 'count_pre_holiday_time': Tunable(description='\n            Should drama nodes that are in pre-holiday mode count?\n            ', tunable_type=bool, default=False), 'invert': Tunable(description='\n            Invert the results of this test.\n            ', tunable_type=bool, default=False)}

    def _evaluate(self, test):
        drama_scheduler = services.drama_scheduler_service()
        drama_node_in_required_state = False
        if self.holiday_drama_node is None:
            if self.invert:
                return TestResult.TRUE
            return TestResult(False, 'Requesting node that is not in this pack.')
        for node in drama_scheduler.active_nodes_gen():
            if type(node) is not self.holiday_drama_node:
                pass
            else:
                if node.is_running:
                    drama_node_in_required_state = True
                    break
                if self.count_pre_holiday_time and node.is_in_preholiday:
                    drama_node_in_required_state = True
                    break
        if self.invert:
            if drama_node_in_required_state:
                return TestResult(False, '{} found running.', self.holiday_drama_node)
        elif not drama_node_in_required_state:
            return TestResult(False, '{} not in requested state.', self.holiday_drama_node)
        return TestResult.TRUE

class HolidayTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'test_behavior': TunableVariant(description='\n            The type of holiday test we want to run.\n            ', default='holidays_running', holidays_running=HolidaysRunningTest.TunableFactory(), specific_holiday_running=SpecificHolidaysTest.TunableFactory())}

    def get_expected_args(self):
        return {}

    def __call__(self):
        return self.test_behavior._evaluate(self)

class TraditionTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'tradition_filter': TunableWhiteBlackList(description='\n            A white and black list for checking if traditions are active.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.HOLIDAY_TRADITION), pack_safe=True))}

    def get_expected_args(self):
        return {}

    def __call__(self):
        active_household = services.active_household()
        if active_household is None:
            return TestResult(False, 'There is no active household for traditions to be active', tooltip=self.tooltip)
        active_traditions = [type(tradition) for tradition in active_household.holiday_tracker.get_active_traditions()]
        if not self.tradition_filter.test_collection(active_traditions):
            return TestResult(False, 'Active traditions do not meet white/black requirements.', tooltip=self.tooltip)
        return TestResult.TRUE
