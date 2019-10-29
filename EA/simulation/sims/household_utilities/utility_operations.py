from objects.components.needs_state_value import NeedsStateValuefrom sims.household_utilities.utility_types import Utilities, UtilityShutoffReasonPriorityfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableEnumEntry, AutoFactoryInit, HasTunableFactory, TunableList, TunableVariantimport servicesimport sims4.loglogger = sims4.log.Logger('UtilityOperations', default_owner='rmccord')
class ShutOffUtilityModifier(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'utility': TunableEnumEntry(description='\n            The household utility we want to modify.\n            ', tunable_type=Utilities, default=Utilities.POWER), 'shutoff_tooltip': TunableLocalizedStringFactory(description='\n            A tooltip to show when an interaction cannot be run due to this\n            utility being shutoff.\n            '), 'shutoff_reason': TunableEnumEntry(description='\n            The priority of our shutoff reason. This determines how important\n            the shutoff tooltip is relative to other reasons the utility is\n            being shutoff.\n            ', tunable_type=UtilityShutoffReasonPriority, default=UtilityShutoffReasonPriority.NO_REASON)}

    def start(self, household_id):
        utilities_manager = services.utilities_manager(household_id)
        utilities_manager.shut_off_utility(self.utility, self.shutoff_reason, self.shutoff_tooltip)

    def stop(self, household_id):
        utilities_manager = services.utilities_manager(household_id)
        utilities_manager.restore_utility(self.utility, self.shutoff_reason)

class UtilityModifierState(HasTunableFactory, AutoFactoryInit, NeedsStateValue):
    FACTORY_TUNABLES = {'utility_modifiers': TunableList(description='\n            Modifiers for household utilities. These are applied to the\n            utilities of the household that owns this object.\n            ', tunable=TunableVariant(description='    \n                The utility and modifer we want to apply.\n                ', shut_off=ShutOffUtilityModifier.TunableFactory(), default='shut_off'))}

    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target

    def start(self, *_, **__):
        if self.target is None:
            logger.error('Applying utility modifiers for a None household in state {}', self.state_value)
            return
        household_owner_id = self.target.get_household_owner_id()
        if not household_owner_id:
            return
        for utility_modifier in self.utility_modifiers:
            modifier = utility_modifier()
            modifier.start(household_owner_id)

    def stop(self, *_, **__):
        if self.target is None:
            logger.error('Removing utility modifiers for a None household in state {}', self.state_value)
            return
        household_owner_id = self.target.get_household_owner_id()
        if not household_owner_id:
            return
        if services.current_zone().is_zone_shutting_down:
            return
        for utility_modifier in self.utility_modifiers:
            modifier = utility_modifier()
            modifier.stop(household_owner_id)
