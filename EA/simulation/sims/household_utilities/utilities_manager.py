from event_testing.results import TestResultfrom interactions.interaction_finisher import FinishingTypefrom sims.household_utilities.utility_types import UtilityShutoffReasonPriority, Utilitiesfrom sims4.service_manager import Serviceimport objects.components.typesimport servicesimport sims4.loglogger = sims4.log.Logger('UtilitiesManager', default_owner='rmccord')
class UtilityInfo:

    def __init__(self, utility, active=True):
        self._utility = utility
        self._active = active
        self._shutoff_reasons = {}

    @property
    def utility(self):
        return self._utility

    @property
    def active(self):
        return self._active

    def get_priority_shutoff_tooltip(self):
        reason = max(UtilityShutoffReasonPriority.NO_REASON, [reason for reason in self._shutoff_reasons if reason is not None])
        tooltip = self._shutoff_reasons[reason] if reason != UtilityShutoffReasonPriority.NO_REASON else None
        return tooltip

    def add_shutoff_reason(self, shutoff_reason, tooltip=None):
        self._active = False
        self._shutoff_reasons[shutoff_reason] = tooltip

    def remove_shutoff_reason(self, shutoff_reason):
        if shutoff_reason in self._shutoff_reasons:
            del self._shutoff_reasons[shutoff_reason]
        if not self._shutoff_reasons:
            self._active = True

class UtilitiesManager(Service):

    def __init__(self):
        self._household_managers = dict()

    def get_manager_for_household(self, household_id):
        if household_id not in self._household_managers:
            self._household_managers[household_id] = HouseholdUtilitiesManager(household_id)
        return self._household_managers[household_id]

class HouseholdUtilitiesManager:

    def __init__(self, household_id):
        self._household_id = household_id
        self._utilities = {u: UtilityInfo(u) for u in Utilities}

    def get_utility_info(self, utility):
        return self._utilities[utility]

    def is_utility_active(self, utility):
        return self.get_utility_info(utility).active

    def test_utility_info(self, utilities):
        if utilities is None:
            return TestResult.TRUE
        for utility in utilities:
            utility_info = self.get_utility_info(utility)
            if utility_info is not None and not utility_info.active:
                return TestResult(False, 'Bills: Interaction requires a utility that is shut off.', tooltip=utility_info.get_priority_shutoff_tooltip())
        return TestResult.TRUE

    def shut_off_utility(self, utility, reason, tooltip=None, from_load=False):
        utility_info = self.get_utility_info(utility)
        if utility == Utilities.POWER and utility_info.active:
            self._shutoff_power_utilities(from_load=from_load)
        utility_info.add_shutoff_reason(reason, tooltip=tooltip)
        self._cancel_delinquent_interactions(utility)

    def restore_utility(self, utility, reason):
        utility_info = self.get_utility_info(utility)
        utility_info.remove_shutoff_reason(reason)
        if utility == Utilities.POWER and utility_info.active:
            self._startup_power_utilities()
        self._clear_delinquency_if_needed()

    def _clear_delinquency_if_needed(self):
        power_info = self.get_utility_info(Utilities.POWER)
        water_info = self.get_utility_info(Utilities.WATER)
        if water_info.active:
            for obj in services.object_manager().valid_objects():
                state_component = obj.state_component
                if state_component is None:
                    pass
                else:
                    state_component.clear_delinquent_states()

    def _cancel_delinquent_interactions(self, delinquent_utility):
        household_id = services.owning_household_id_of_active_lot()
        if household_id != self._household_id:
            return
        for sim in services.sim_info_manager().instanced_sims_gen():
            for interaction in sim.si_state:
                utility_info = interaction.utility_info
                if utility_info is None:
                    pass
                elif delinquent_utility in utility_info:
                    interaction.cancel(FinishingType.FAILED_TESTS, 'Household Utilities. Interaction violates current delinquency state of household.')
        for obj in services.object_manager().valid_objects():
            state_component = obj.state_component
            if state_component is None:
                pass
            else:
                state_component.apply_delinquent_states(utility=delinquent_utility)

    def _startup_power_utilities(self):
        self._exec_on_objects_with_component(objects.components.types.LIGHTING_COMPONENT, lambda component: component.on_power_on())

    def _shutoff_power_utilities(self, from_load=False):
        self._exec_on_objects_with_component(objects.components.types.LIGHTING_COMPONENT, lambda component: component.on_power_off(from_load=from_load))

    def _exec_on_objects_with_component(self, component_type, func):
        object_manager = services.object_manager()
        plex_service = services.get_plex_service()
        for obj in object_manager.get_all_objects_with_component_gen(component_type):
            if obj.get_household_owner_id() != self._household_id:
                pass
            elif plex_service.is_active_zone_a_plex() and plex_service.get_plex_zone_at_position(obj.position, obj.level) is None:
                pass
            else:
                func(obj.get_component(component_type))
