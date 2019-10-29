from interactions import ParticipantTypeSingleSimfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom retail.retail_utils import RetailUtilsfrom sims4.tuning.tunable import TunableEnumEntry, AutoFactoryInit, TunableVariant, TunableRange, TunableList, HasTunableSingletonFactoryimport sims4.loglogger = sims4.log.Logger('Retail', default_owner='trevor')
class RetailCustomerAdjustBrowseTime(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'time_multiplier': TunableRange(description='\n            The remaining time the customer has to browse will be multiplied by\n            this number. A value of 2.0 will double the remaining time, causing\n            the customer to spend more time browsing. A value of 0.5 will cut\n            the remaining browse time in half, causing the customer to move on\n            to the next state sooner. A value of 0 will instantly push the\n            customer to go to the next state. If the customer is not currently\n            in the browse state, this element will do nothing.\n            ', tunable_type=float, default=1, minimum=0)}

    def apply_action(self, sim, situation):
        situation.adjust_browse_time(self.time_multiplier)

class RetailCustomerAdjustTotalShopTime(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'time_multiplier': TunableRange(description='\n            The remaining time the customer has to shop will be multiplied by\n            this number. A value of 2.0 will double the remaining time, causing\n            the customer to shop more. A value of 0.5 will cut the remaining\n            browse time in half, causing the customer to shop less. A value of\n            0 will cause the customer to leave.\n            ', tunable_type=float, default=1, minimum=0)}

    def apply_action(self, sim, situation):
        situation.adjust_total_shop_time(self.time_multiplier)

class RetailCustomerAdjustPriceRange(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'min_price_adjustment_multiplier': TunableRange(description='\n            The amount to multiply the minimum price range for this customer.\n            ', tunable_type=float, default=1, minimum=0), 'max_price_adjustment_multiplier': TunableRange(description='\n            The amount to multiply the maximum price range for this customer.\n            ', tunable_type=float, default=1, minimum=0)}

    def apply_action(self, sim, situation):
        situation.adjust_price_range(min_multiplier=self.min_price_adjustment_multiplier, max_multiplier=self.max_price_adjustment_multiplier)

class RetailCustomerAction(XevtTriggeredElement):
    FACTORY_TUNABLES = {'customer': TunableEnumEntry(description='\n            The customer participant to which the action is applied.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.TargetSim), 'actions': TunableList(description='\n            The actions to apply to the customer.\n            ', tunable=TunableVariant(description='\n                The action to apply to the customer.\n                ', adjust_browse_time=RetailCustomerAdjustBrowseTime.TunableFactory(description="\n                    Change the browse time of the customer by some multiple of the\n                    remaining browse time. This does nothing if the customer isn't\n                    already browsing. (i.e. loitering customers won't be affected)\n                    "), adjust_total_shop_time=RetailCustomerAdjustTotalShopTime.TunableFactory(description='\n                    Change the total shop time of the customer by some multiple of\n                    the remaining shop time.\n                    '), adjust_min_max_price_range=RetailCustomerAdjustPriceRange.TunableFactory(description='\n                    Change the min and/or max price range of this customer.\n                    ')))}

    def _do_behavior(self):
        customer = self.interaction.get_participant(self.customer)
        if customer is None:
            logger.error('Got a None customer trying to run a RetailCustomerAction element.')
            return False
        situation = RetailUtils.get_retail_customer_situation_from_sim(customer)
        if situation is None:
            logger.warn("Trying to run a customer action on a sim that isn't running a retail situation.")
            return False
        for action in self.actions:
            action.apply_action(customer, situation)
