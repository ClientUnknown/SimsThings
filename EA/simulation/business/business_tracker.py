from _collections import defaultdictfrom collections import Counterfrom business.business_enums import BusinessTypefrom business.business_manager import BusinessManagerfrom business.business_tuning import BusinessTuningfrom distributor.rollback import ProtocolBufferRollbackfrom zone_types import ZoneStateimport game_servicesimport servicesimport sims4.loglogger = sims4.log.Logger('Business', default_owner='trevor')
class BusinessTracker:

    def __init__(self, owner_household_id, business_type):
        self._owner_household_id = owner_household_id
        self._business_type = business_type
        self._business_managers = defaultdict(lambda : BusinessManager(business_type))
        self._additional_employee_slots = Counter()
        self._business_type_tuning_data = services.business_service().get_business_tuning_data_for_business_type(business_type)
        current_zone = services.current_zone()
        if current_zone is not None:
            if current_zone.is_zone_running:
                self._register_perk_callbacks()
            else:
                current_zone.register_callback(ZoneState.HOUSEHOLDS_AND_SIM_INFOS_LOADED, self._register_perk_callbacks)
        self._additional_markup_multiplier = 0
        self._additional_customer_count = 0

    @property
    def business_type(self):
        return self._business_type

    @property
    def business_managers(self):
        return self._business_managers

    @property
    def is_on_lot_with_open_business(self):
        business_manager = self.get_business_manager_for_zone()
        return business_manager is not None and business_manager.is_open

    @property
    def business_type_tuning_data(self):
        return self._business_type_tuning_data

    @property
    def additional_markup_multiplier(self):
        return self._additional_markup_multiplier

    @property
    def addtitional_customer_count(self):
        return self._additional_customer_count

    @property
    def owner_household_id(self):
        return self._owner_household_id

    def _get_owner_household(self):
        return services.household_manager().get(self._owner_household_id)

    def save_data(self, business_tracker_msg):
        business_tracker_msg.additional_markup_multiplier = self._additional_markup_multiplier
        business_tracker_msg.additional_customer_count = self._additional_customer_count
        for (employee_type, additional_slot_count) in self._additional_employee_slots.items():
            with ProtocolBufferRollback(business_tracker_msg.additional_employee_slot_data) as additional_slot_data:
                additional_slot_data.employee_type = employee_type
                additional_slot_data.additional_slot_count = additional_slot_count
        for (zone_id, manager) in self._business_managers.items():
            with ProtocolBufferRollback(business_tracker_msg.business_manager_data) as business_manager_data:
                business_manager_data.zone_id = zone_id
                manager.save_data(business_manager_data.business_data)

    def load_data(self, business_tracker_msg):
        self._additional_markup_multiplier = business_tracker_msg.additional_markup_multiplier
        self._additional_customer_count = business_tracker_msg.additional_customer_count
        self._additional_employee_slots.clear()
        for additional_slot_data in business_tracker_msg.additional_employee_slot_data:
            self._additional_employee_slots[additional_slot_data.employee_type] = additional_slot_data.additional_slot_count
        for manager_save_data in business_tracker_msg.business_manager_data:
            loaded_manager = self.make_owner(self._owner_household_id, manager_save_data.zone_id)
            loaded_manager.load_data(manager_save_data.business_data)

    def load_legacy_data(self, retail_store_data):
        loaded_manager = self.make_owner(self._owner_household_id, retail_store_data.retail_zone_id)
        loaded_manager.load_data(retail_store_data, is_legacy=True)

    def set_legacy_additional_employee_slot(self, additional_slots):
        self._additional_employee_slots[BusinessTuning.LEGACY_RETAIL_ADDITIONAL_SLOT_EMPLOYEE_TYPE] = additional_slots

    def on_protocols_loaded(self):
        current_zone = services.current_zone()
        if current_zone is not None:
            business_manager = self.get_business_manager_for_zone(current_zone.id)
            if business_manager is not None:
                business_manager.on_protocols_loaded()
            current_zone.register_callback(ZoneState.HOUSEHOLDS_AND_SIM_INFOS_LOADED, self._register_perk_callbacks)

    def on_zone_load(self):
        for business_manager in self._business_managers.values():
            business_manager.on_zone_load()
        if not self.is_on_lot_with_open_business:
            owner_household = self._get_owner_household()
            if owner_household is None:
                return
            owner_household.bucks_tracker.deactivate_all_temporary_perk_timers_of_type(self.business_type_tuning_data.bucks)

    def on_client_disconnect(self):
        business_manager = self.get_business_manager_for_zone()
        if business_manager is not None:
            business_manager.on_client_disconnect()
        owner_household = self._get_owner_household()
        if owner_household is None:
            return
        owner_household.bucks_tracker.remove_perk_unlocked_callback(self.business_type_tuning_data.bucks, self._business_perk_unlocked_callback)
        owner_household.bucks_tracker.deactivate_all_temporary_perk_timers_of_type(self.business_type_tuning_data.bucks)

    def _register_perk_callbacks(self):
        if not game_services.service_manager.is_traveling:
            owner_household = self._get_owner_household()
            if owner_household is not None:
                owner_household.bucks_tracker.add_perk_unlocked_callback(self._business_type_tuning_data.bucks, self._business_perk_unlocked_callback)
        business_manager = self.get_business_manager_for_zone()
        if business_manager is not None:
            business_manager.on_registered_perk_callback()

    def run_off_lot_simulation(self):
        current_zone_id = services.current_zone_id()
        for business_manager in self._business_managers.values():
            if business_manager.business_zone_id != current_zone_id and business_manager.is_open:
                business_manager.run_off_lot_simulation()

    def get_business_manager_for_zone(self, zone_id=None):
        if zone_id is None:
            zone_id = services.current_zone_id()
        return self._business_managers.get(zone_id, None)

    def make_owner(self, owner_household_id, business_zone_id):
        if self.business_type == BusinessType.RETAIL:
            from retail.retail_manager import RetailManager
            self._business_managers[business_zone_id] = RetailManager()
        elif self.business_type == BusinessType.RESTAURANT:
            from restaurants.restaurant_manager import RestaurantManager
            self._business_managers[business_zone_id] = RestaurantManager()
        elif self.business_type == BusinessType.VET:
            from vet.vet_clinic_manager import VetClinicManager
            self._business_managers[business_zone_id] = VetClinicManager()
        business_manager = self._business_managers[business_zone_id]
        business_manager.set_owner_household_id(owner_household_id)
        business_manager.set_zone_id(business_zone_id)
        return self._business_managers[business_zone_id]

    def remove_owner(self, business_zone_id):
        del self._business_managers[business_zone_id]

    def increment_additional_employee_slots(self, employee_type):
        employee_type_tuning_data = self.business_type_tuning_data.employee_data_map.get(employee_type, None)
        if employee_type_tuning_data is None:
            logger.error("Trying to increment additional employee slots for business type: {} but employee type: {} doesn't exist.", self.business_type, employee_type)
            return
        if self._additional_employee_slots[employee_type] >= employee_type_tuning_data.employee_count_max - employee_type_tuning_data.employee_count_default:
            logger.error('Attempting to add additional slots beyond the max limit of {}', employee_type_tuning_data.employee_count_max)
            return
        self._additional_employee_slots[employee_type] += 1

    def get_additional_employee_slots(self, employee_type):
        return self._additional_employee_slots[employee_type]

    def add_additional_markup_multiplier(self, delta):
        self._additional_markup_multiplier = max(0, self._additional_markup_multiplier + delta)

    def add_additional_customer_count(self, delta):
        self._additional_customer_count = sims4.math.clamp(0, self._additional_customer_count + delta, 13)

    def _business_perk_unlocked_callback(self, perk):
        if perk.temporary_perk_information is None:
            return
        if self.is_on_lot_with_open_business:
            return
        owning_household = self._get_owner_household()
        if owning_household is not None:
            owning_household.bucks_tracker.deactivate_temporary_perk_timer(perk)
