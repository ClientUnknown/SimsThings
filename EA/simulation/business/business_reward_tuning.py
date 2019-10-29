import servicesimport sims4.logfrom business.business_enums import BusinessType, BusinessEmployeeTypefrom rewards.reward_enums import RewardDestination, RewardTypefrom rewards.tunable_reward_base import TunableRewardBasefrom sims4.tuning.tunable import TunableEnumEntry, Tunablefrom sims4.utils import constpropertylogger = sims4.log.Logger('Business', default_owner='trevor')
class TunableRewardAdditionalEmployeeSlot(TunableRewardBase):
    FACTORY_TUNABLES = {'business_type': TunableEnumEntry(description='\n            The business type to which this reward should be given.\n            ', tunable_type=BusinessType, default=BusinessType.INVALID, invalid_enums=(BusinessType.INVALID,)), 'employee_type': TunableEnumEntry(description='\n            The employee type to increment the slot count.\n            ', tunable_type=BusinessEmployeeType, default=BusinessEmployeeType.INVALID, invalid_enums=(BusinessEmployeeType.INVALID,))}

    def __init__(self, *args, business_type, employee_type, **kwargs):
        super().__init__(*args, **kwargs)
        self.business_type = business_type
        self.employee_type = employee_type

    @constproperty
    def reward_type():
        return RewardType.ADDITIONAL_EMPLOYEE_SLOT

    def get_resource_key(self):
        return NotImplementedError

    def open_reward(self, sim_info, **kwargs):
        household = sim_info.household
        if household is None:
            logger.error('SimInfo {} has no associated household.', sim_info)
            return
        services.business_service().increment_additional_employee_slots(household.id, self.business_type, self.employee_type)

class TunableRewardAdditionalMarkup(TunableRewardBase):
    FACTORY_TUNABLES = {'business_type': TunableEnumEntry(description='\n            The business type to which this reward should be given.\n            ', tunable_type=BusinessType, default=BusinessType.INVALID, invalid_enums=(BusinessType.INVALID,)), 'markup_increment': Tunable(description='\n            The amount to increment the markup multiplier for the tuned business\n            type. You can also use the to decrement the markup multiplier but\n            the code will never allow a negative multiplier. This change is\n            permanent across all business types so use with caution!\n            ', tunable_type=float, default=0)}

    def __init__(self, *args, business_type, markup_increment, **kwargs):
        super().__init__(*args, **kwargs)
        self.business_type = business_type
        self.markup_increment = markup_increment

    @constproperty
    def reward_type():
        return RewardType.ADDITIONAL_BUSINESS_MARKUP

    def get_resource_key(self):
        return NotImplementedError

    def open_reward(self, sim_info, **kwargs):
        household = sim_info.household
        if household is None:
            logger.error('SimInfo {} has no associated household.', sim_info)
            return
        services.business_service().increment_additional_markup(household.id, self.business_type, self.markup_increment)

class TunableRewardAdditionalCustomerCount(TunableRewardBase):
    FACTORY_TUNABLES = {'business_type': TunableEnumEntry(description='\n            The business type to which this reward should be given.\n            ', tunable_type=BusinessType, default=BusinessType.INVALID, invalid_enums=(BusinessType.INVALID,)), 'customer_count_increment': Tunable(description='\n            The amount to increment the customer count for the tuned business\n            type. You can also use this to decrement the customer count but the\n            code will never allow a negative customer count or the sim cap to be\n            violated. This change is permanent across all business types so use\n            with caution!\n            ', tunable_type=float, default=0)}

    def __init__(self, *args, business_type, customer_count_increment, **kwargs):
        super().__init__(*args, **kwargs)
        self.business_type = business_type
        self.customer_count_increment = customer_count_increment

    @constproperty
    def reward_type():
        return RewardType.ADDITIONAL_BUSINESS_CUSTOMER_COUNT

    def get_resource_key(self):
        return NotImplementedError

    def open_reward(self, sim_info, **kwargs):
        household = sim_info.household
        if household is None:
            logger.error('SimInfo {} has no associated household.', sim_info)
            return
        services.business_service().increment_additional_customer_count(household.id, self.business_type, self.customer_count_increment)
