from _collections import defaultdictimport itertoolsfrom business.business_enums import BusinessTypefrom business.business_tracker import BusinessTrackerfrom business.business_tuning import BusinessTuningfrom date_and_time import create_time_spanfrom distributor.rollback import ProtocolBufferRollbackfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableRangefrom sims4.utils import classpropertyimport alarmsimport game_servicesimport persistence_error_typesimport servicesimport sims4.loglogger = sims4.log.Logger('Business', default_owner='trevor')
class BusinessService(Service):
    HOURS_BETWEEN_OFF_LOT_SIMULATIONS = TunableRange(description='\n        The number of hours between off lot simulations for business.\n        ', tunable_type=int, default=4, minimum=4, maximum=24)
    EMPLOYEE_ADDITIONAL_IMMUNITY = TunableRange(description="\n        This unit less number will be a boost the employee's importance when\n        the culling system scores this Sim. Higher the number, lower the\n        probability this Sim being culled.\n        \n        Performance WARNING: Remember that employees can be hired by many\n        households via rotational gameplay. This number has to balance the\n        desire to keep this Sim around as well as supporting multiple player\n        families with businesses.\n        ", tunable_type=int, default=10, minimum=0)

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_BUSINESS_SERVICE

    def __init__(self):
        self._business_trackers = defaultdict(list)
        self._off_lot_churn_alarm_handle = None

    def _stop_off_lot_churn_alarm(self):
        if self._off_lot_churn_alarm_handle is not None:
            alarms.cancel_alarm(self._off_lot_churn_alarm_handle)
            self._off_lot_churn_alarm_handle = None

    def _start_off_lot_churn_alarm(self):
        self._off_lot_churn_alarm_handle = alarms.add_alarm(self, create_time_span(hours=BusinessService.HOURS_BETWEEN_OFF_LOT_SIMULATIONS), self._off_lot_churn_callback, repeating=True, use_sleep_time=False)

    def _off_lot_churn_callback(self, alarm_handle):
        trackers = self.get_business_trackers_for_household(services.active_household_id())
        if not trackers:
            return
        for tracker in trackers:
            tracker.run_off_lot_simulation()

    def on_client_disconnect(self, client):
        self._stop_off_lot_churn_alarm()
        for business_tracker in itertools.chain.from_iterable(self._business_trackers.values()):
            business_tracker.on_client_disconnect()

    def on_enter_main_menu(self):
        self._business_trackers.clear()

    def make_owner(self, owner_household_id, business_type, business_zone_id):
        business_tracker = self._get_or_create_tracker_for_household(owner_household_id, business_type)
        business_tracker.make_owner(owner_household_id, business_zone_id)

    def remove_owner(self, zone_id, household_id=None):
        business_tracker = self._get_tracker_for_business_in_zone(zone_id, household_id=household_id)
        business_tracker.remove_owner(zone_id)

    def get_business_trackers_for_household(self, household_id):
        return self._business_trackers.get(household_id, None)

    def get_retail_manager_for_zone(self, zone_id=None):
        business_manager = self.get_business_manager_for_zone(zone_id=zone_id)
        if business_manager is not None and business_manager.business_type == BusinessType.RETAIL:
            return business_manager

    def get_business_manager_for_zone(self, zone_id=None):
        check_active_zone = False
        current_zone_id = services.current_zone_id()
        if zone_id is None:
            zone_id = current_zone_id
            check_active_zone = True
        elif zone_id == current_zone_id:
            check_active_zone = True
        for business_tracker in itertools.chain.from_iterable(self._business_trackers.values()):
            business_manager = business_tracker.get_business_manager_for_zone(zone_id=zone_id)
            if business_manager:
                return business_manager
        if check_active_zone:
            zone_director = services.venue_service().get_zone_director()
            return getattr(zone_director, 'business_manager', None)

    def get_business_tracker_for_household(self, household_id, business_type):
        for business_tracker in self._business_trackers[household_id]:
            if business_tracker.business_type == business_type:
                return business_tracker

    def increment_additional_employee_slots(self, household_id, business_type, employee_type):
        business_tracker = self.get_business_tracker_for_household(household_id, business_type)
        if business_tracker is None:
            logger.error('Trying to increment additional employee slots for business_type: {} owned by household id: {} but no tracker exists.', business_type, household_id)
            return
        business_tracker.increment_additional_employee_slots(employee_type)

    def increment_additional_markup(self, household_id, business_type, markup_increment):
        business_tracker = self.get_business_tracker_for_household(household_id, business_type)
        if business_tracker is None:
            logger.error('Trying to increment additional markup for business type: {} owned by household id: {} but no tracker exists.', business_type, household_id)
            return
        business_tracker.add_additional_markup_multiplier(markup_increment)

    def increment_additional_customer_count(self, household_id, business_type, count_increment):
        business_tracker = self.get_business_tracker_for_household(household_id, business_type)
        if business_tracker is None:
            logger.error('Trying to increment additional markup for business type: {} owned by household id: {} but no tracker exists.', business_type, household_id)
            return
        business_tracker.add_additional_customer_count(count_increment)

    def _get_or_create_tracker_for_household(self, owner_household_id, business_type):
        business_tracker = self.get_business_tracker_for_household(owner_household_id, business_type)
        if business_tracker is not None:
            return business_tracker
        household = services.household_manager().get(owner_household_id)
        business_tracker = BusinessTracker(household.id, business_type)
        self._business_trackers[owner_household_id].append(business_tracker)
        return business_tracker

    def _get_tracker_for_business_in_zone(self, zone_id, household_id=None):
        if household_id is None:
            business_trackers = self._business_trackers.values()
        else:
            business_trackers = self.get_business_trackers_for_household(household_id)
        if business_trackers is None:
            return
        for tracker in business_trackers:
            if tracker.get_business_manager_for_zone(zone_id) is not None:
                return tracker

    def get_business_managers_for_household(self, household_id=None):
        if household_id is None:
            active_household = services.active_household()
            if active_household is None:
                return
            household_id = active_household.id
        business_trackers = self.get_business_trackers_for_household(household_id)
        if business_trackers is None:
            return
        return {zone_id: manager for tracker in business_trackers for (zone_id, manager) in tracker.business_managers.items()}

    @classmethod
    def get_business_tuning_data_for_business_type(cls, business_type):
        return BusinessTuning.BUSINESS_TYPE_TO_BUSINESS_DATA_MAP.get(business_type, None)

    def on_zone_load(self):
        for business_trackers in self._business_trackers.values():
            for tracker in business_trackers:
                tracker.on_zone_load()
        self._start_off_lot_churn_alarm()
        self.send_business_data_to_client()

    def on_build_buy_enter(self):
        self.send_business_data_to_client()
        business_manager = self.get_business_manager_for_zone()
        if business_manager is not None:
            business_manager.on_build_buy_enter()

    def on_build_buy_exit(self):
        business_manager = self.get_business_manager_for_zone()
        if business_manager is not None:
            business_manager.on_build_buy_exit()

    def clear_owned_business(self, household_id):
        if household_id not in self._business_trackers:
            return
        zone_manager = services.get_zone_manager()
        business_trackers = self._business_trackers[household_id]
        for business_tracker in business_trackers:
            for zone_id in business_tracker.business_managers:
                zone_manager.clear_lot_ownership(zone_id)
        del self._business_trackers[household_id]

    def save(self, save_slot_data=None, **kwargs):
        business_service_data = save_slot_data.gameplay_data.business_service_data
        business_service_data.Clear()
        for (household_id, business_trackers) in self._business_trackers.items():
            for tracker in business_trackers:
                with ProtocolBufferRollback(business_service_data.business_tracker_data) as business_tracker_data:
                    business_tracker_data.household_id = household_id
                    business_tracker_data.business_type = tracker.business_type
                    tracker.save_data(business_tracker_data)

    def on_all_households_and_sim_infos_loaded(self, client):
        business_owning_household_ids = set(self._business_trackers.keys())
        all_households_ids = set(services.household_manager())
        invalid_household_ids = business_owning_household_ids - all_households_ids
        for household_id in invalid_household_ids:
            self.clear_owned_business(household_id)

    def are_business_trackers_valid(self, business_tracker_save_datas):
        for business_tracker in itertools.chain(*self._business_trackers.values()):
            business_tracker_data = None
            for business_tracker_data in business_tracker_save_datas:
                if business_tracker.owner_household_id == business_tracker_data.household_id and business_tracker.business_type == business_tracker_data.business_type:
                    if len(business_tracker.business_managers) != len(business_tracker_data.business_manager_data):
                        return False
                    break
            return False
        return True

    def process_zone_loaded(self):
        if game_services.service_manager.is_traveling:
            for business_tracker in itertools.chain(*self._business_trackers.values()):
                business_tracker.on_protocols_loaded()
            return
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        if not save_slot_data_msg.gameplay_data.HasField('business_service_data'):
            self._business_trackers.clear()
            return
        if self._business_trackers and self.are_business_trackers_valid(save_slot_data_msg.gameplay_data.business_service_data.business_tracker_data):
            for business_tracker in itertools.chain(*self._business_trackers.values()):
                business_tracker.on_protocols_loaded()
            return
        self._business_trackers.clear()
        for business_tracker_data in save_slot_data_msg.gameplay_data.business_service_data.business_tracker_data:
            business_tuning_data = self.get_business_tuning_data_for_business_type(business_tracker_data.business_type)
            if business_tuning_data is None:
                pass
            else:
                business_tracker = BusinessTracker(business_tracker_data.household_id, business_tracker_data.business_type)
                business_tracker.load_data(business_tracker_data)
                self._business_trackers[business_tracker_data.household_id].append(business_tracker)

    def load_legacy_data(self, household, household_proto):
        legacy_save_data = None
        if hasattr(household_proto.gameplay_data, 'retail_data'):
            legacy_save_data = household_proto.gameplay_data.retail_data
        if not legacy_save_data:
            return
        business_tuning_data = self.get_business_tuning_data_for_business_type(BusinessType.RETAIL)
        if business_tuning_data is None:
            return
        retail_business_tracker = self.get_business_tracker_for_household(household.id, BusinessType.RETAIL)
        if retail_business_tracker is None:
            retail_business_tracker = BusinessTracker(household.id, BusinessType.RETAIL)
            self._business_trackers[household.id].append(retail_business_tracker)
        for retail_store_data in legacy_save_data:
            retail_business_tracker.load_legacy_data(retail_store_data)
            retail_store_data.Clear()
        additional_employee_slot = household_proto.gameplay_data.additional_employee_slots
        retail_business_tracker.set_legacy_additional_employee_slot(additional_employee_slot)

    def send_business_data_to_client(self):
        business_managers_dict = self.get_business_managers_for_household()
        if not business_managers_dict:
            return
        for business_manager in business_managers_dict.values():
            business_manager.send_data_to_client()

    def get_culling_npc_score(self, sim_info):
        if self.is_employee_of_any_business(sim_info):
            return self.EMPLOYEE_ADDITIONAL_IMMUNITY
        return 0

    def is_employee_of_any_business(self, sim_info):
        for business_trackers in self._business_trackers.values():
            for tracker in business_trackers:
                for business_manager in tracker.business_managers.values():
                    if business_manager.is_employee(sim_info):
                        return True
        return False
