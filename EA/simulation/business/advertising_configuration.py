from business.business_enums import BusinessAdvertisingTypefrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableMapping, TunableEnumEntry, TunableTuple, TunableRange, OptionalTunableimport sims4logger = sims4.log.Logger('Business', default_owner='jdimailig')
class AdvertisingConfiguration(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'default_advertising_type': OptionalTunable(description='\n            Set the default advertising type for the initial business.  This\n            should map to a key in advertising_data_map.\n            ', tunable=TunableEnumEntry(description='\n                The Advertising Type .\n                ', tunable_type=BusinessAdvertisingType, default=BusinessAdvertisingType.INVALID, invalid_enums=(BusinessAdvertisingType.INVALID,)), disabled_name='No_Default_Advertisement_Type'), 'advertising_data_map': TunableMapping(description='\n            The mapping between advertising type and the data for that type.\n            ', key_type=TunableEnumEntry(description='\n                The Advertising Type .\n                ', tunable_type=BusinessAdvertisingType, default=BusinessAdvertisingType.INVALID, invalid_enums=(BusinessAdvertisingType.INVALID,)), value_type=TunableTuple(description='\n                Data associated with this advertising type.\n                ', cost_per_hour=TunableRange(description='\n                    How much, per hour, it costs to use this advertising type.\n                    ', tunable_type=int, default=10, minimum=0), customer_count_multiplier=TunableRange(description='\n                    This amount is multiplied by the ideal customer count for owned\n                    restaurants.\n                    ', tunable_type=float, default=0.8, minimum=0)))}

    def get_advertising_cost_per_hour(self, advertising_type):
        config = self.advertising_data_map.get(advertising_type, None)
        if config is not None:
            return config.cost_per_hour
        logger.error('There is no cost per hour tuned for advertising type {}'.format(advertising_type))
        return 0.0

    def get_customer_count_multiplier(self, advertising_type):
        config = self.advertising_data_map.get(advertising_type, None)
        if config is not None:
            return config.customer_count_multiplier
        logger.error('There is no customer count multiplier tuned for advertising type {}'.format(advertising_type))
        return 1.0
