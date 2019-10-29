from business.business_enums import BusinessQualityTypefrom event_testing import test_basefrom event_testing.results import TestResultfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, OptionalTunable, TunableIntervalfrom sims4.tuning.tunable import Tunablefrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport services
class BusinessAllowsNewCustomersTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'customers_allowed': Tunable(description='\n            If checked this will test if new customers are currently allowed\n            to show up on a business lot. \n            \n            If unchecked this will test if new customers are not allowed to \n            show up currently. \n            ', tunable_type=bool, default=True)}

    def get_expected_args(self):
        return {}

    def __call__(self):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is None:
            return TestResult(False, 'Not currently on a business lot.')
        zone_director = services.venue_service().get_zone_director()
        if zone_director is None:
            return TestResult(False, 'There is no zone_director for this zone.')
        from business.business_zone_director_mixin import BusinessZoneDirectorMixin
        if not isinstance(zone_director, BusinessZoneDirectorMixin):
            return TestResult(False, 'The current zone director does not implement the BusinessZoneDirectorMixin interface.')
        if zone_director.allows_new_customers():
            if not self.customers_allowed:
                return TestResult(False, 'Business does allow new customers but the test is for not allowing them.')
        elif self.customers_allowed:
            return TestResult(False, 'Business does not allow new customers and the test is for allowing them.')
        return TestResult.TRUE

class BusinessSettingTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'quality_setting': OptionalTunable(description='\n            A test to see if the current business has certain settings set by the owner.\n            ', tunable=TunableWhiteBlackList(description='\n                Use of this white/black list will check whether or not the \n                current on-lot business is set to certain quality settings.\n                ', tunable=TunableEnumEntry(description='\n                    Business Quality Type from business settings.\n                    ', tunable_type=BusinessQualityType, default=BusinessQualityType.INVALID, invalid_enums=(BusinessQualityType.INVALID,))), disabled_name='ignore', enabled_name='test'), 'star_rating': OptionalTunable(description='\n            A test to see if the current business is within a star rating range.\n            ', tunable=TunableInterval(description="\n                If the business's star rating is within this range, this test passes.\n                ", tunable_type=float, default_lower=0, default_upper=5, minimum=0), disabled_name='ignore', enabled_name='test')}

    def get_expected_args(self):
        return {}

    def __call__(self):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is None:
            return TestResult(False, 'Not currently on a business lot.')
        if self.quality_setting is not None and not self.quality_setting.test_item(business_manager.quality_setting):
            return TestResult(False, 'Business is set to {}'.format(business_manager.quality_setting))
        if self.star_rating is not None:
            business_star_rating = business_manager.get_star_rating()
            if business_star_rating not in self.star_rating:
                return TestResult(False, 'Business star rating is {}'.format(business_star_rating))
        return TestResult.TRUE
