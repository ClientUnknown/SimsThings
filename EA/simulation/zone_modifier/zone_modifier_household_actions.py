from sims.household_utilities.utility_operations import ShutOffUtilityModifierfrom sims4.tuning.tunable import TunableVariant, TunableList, HasTunableSingletonFactory, AutoFactoryInit
class ZoneModifierHouseholdActionVariants(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, shut_off_utilities=ZoneModifierHouseholdShutOffUtility.TunableFactory(), default='shut_off_utilities', **kwargs)

class ZoneModifierHouseholdAction(HasTunableSingletonFactory, AutoFactoryInit):

    def start_action(self, household_id):
        raise NotImplementedError

    def stop_action(self, household_id):
        raise NotImplementedError

class ZoneModifierHouseholdShutOffUtility(ZoneModifierHouseholdAction):
    FACTORY_TUNABLES = {'utilities': TunableList(description='\n            A list of utilities to shut off.\n            ', tunable=ShutOffUtilityModifier.TunableFactory())}

    def start_action(self, household_id):
        for utility_shut_off in self.utilities:
            shut_off = utility_shut_off()
            shut_off.start(household_id)

    def stop_action(self, household_id):
        for utility_shut_off in self.utilities:
            shut_off = utility_shut_off()
            shut_off.stop(household_id)
