from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import cached_testfrom interactions import ParticipantTypefrom sims.household_utilities.utility_types import Utilitiesfrom sims4.tuning.tunable import TunableEnumEntry, TunableTuple, Tunable, AutoFactoryInit, HasTunableSingletonFactory, TunableVariant, TunableSetimport services
class UtilityTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    PARTICIPANT_HOUSEHOLD = 'participant_household'
    ACTIVE_HOUSEHOLD = 'active_household'
    ACTIVE_LOT_HOUSEHOLD = 'active_lot_household'
    FACTORY_TUNABLES = {'household_to_test': TunableVariant(description='\n            A variant that decides where the household to test comes from.\n            ', participant_household=TunableTuple(description="\n                Either the participant's household if they are a Sim or the\n                owning household if they are not.\n                ", participant=TunableEnumEntry(description='\n                    The subject whose household is the object of this delinquency test.\n                    ', tunable_type=ParticipantType, default=ParticipantType.Actor, invalid_enums=(ParticipantType.Invalid,)), locked_args={'household_source': PARTICIPANT_HOUSEHOLD}), active_household=TunableTuple(description='\n                The household being controlled by the player.\n                ', locked_args={'household_source': ACTIVE_HOUSEHOLD}), active_lot_household=TunableTuple(description='\n                The household that owns the active lot.\n                ', locked_args={'household_source': ACTIVE_LOT_HOUSEHOLD}), default='active_lot_household'), 'utility_states': TunableSet(description='\n            List of utilities and whether they are required to be active or not.\n            ', tunable=TunableTuple(description='\n                Tuple containing a utility and its required active state.\n                ', utility=TunableEnumEntry(Utilities, None), require_active=Tunable(description='\n                    Whether this utility is required to be active or not.\n                    ', tunable_type=bool, default=True)))}

    def get_expected_args(self):
        if self.household_to_test.household_source == UtilityTest.PARTICIPANT_HOUSEHOLD:
            return {'test_targets': self.subject}

    @cached_test
    def __call__(self, test_targets=None):
        if self.household_to_test.household_source == UtilityTest.ACTIVE_LOT_HOUSEHOLD:
            target_households = {services.owning_household_of_active_lot()}
        elif self.household_to_test.household_source == UtilityTest.ACTIVE_HOUSEHOLD:
            target_households = {services.active_household()}
        elif self.household_to_test.household_source == UtilityTest.PARTICIPANT_HOUSEHOLD:
            target_households = set()
            for target in test_targets:
                if target.is_sim:
                    target_households.add(target.household)
                else:
                    target_household = services.household_manager().get(target.get_household_owner_id())
                    if target_household is not None:
                        target_households.add(target_household)
        for household in target_households:
            for utility_state in self.utility_states:
                if household is None:
                    if utility_state.require_active:
                        return TestResult(False, 'UtilitiesTest: Required {} to be active, but there is no household. Check participant tuning.', utility_state.utility, tooltip=self.tooltip)
                        if services.utilities_manager(household.id).is_utility_active(utility_state.utility) != utility_state.require_active:
                            return TestResult(False, 'UtilitiesTest: Household utility status for the {} is not correct.', utility_state.utility, tooltip=self.tooltip)
                elif services.utilities_manager(household.id).is_utility_active(utility_state.utility) != utility_state.require_active:
                    return TestResult(False, 'UtilitiesTest: Household utility status for the {} is not correct.', utility_state.utility, tooltip=self.tooltip)
        return TestResult.TRUE
