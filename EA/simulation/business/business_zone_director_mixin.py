from _collections import defaultdictfrom business.business_enums import BusinessEmployeeTypefrom date_and_time import create_time_spanfrom sims4.tuning.tunable import TunableSimMinute, TunableMapping, TunableEnumEntry, TunableReference, TunableTuple, TunableRange, TunableVariantfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposeimport alarmsimport servicesimport sims4.resourceslogger = sims4.log.Logger('Business', default_owner='trevor')DEFER_NPC_EMPLOYEE_COUNT_TO_ZONE_DIRECTOR = 'DeferToZoneDirector'
class BusinessZoneDirectorMixin:
    INSTANCE_TUNABLES = {'customer_situation_interval': TunableSimMinute(description='\n            The amount of time, in Sim minutes, between attempts to create new\n            customer situations.\n            ', default=10, tuning_group=GroupNames.BUSINESS), 'employee_situation_data': TunableMapping(description='\n            A mapping of Business Employee Type to the data required by the zone\n            director for starting situations.\n            ', key_type=TunableEnumEntry(description='\n                The Business Employee Type.\n                ', tunable_type=BusinessEmployeeType, default=BusinessEmployeeType.INVALID, invalid_enums=(BusinessEmployeeType.INVALID,)), key_name='Business_Employee_Type', value_type=TunableTuple(description='\n                The situation data, per business employee type, for this zone director.\n                ', situation_job=TunableReference(description='\n                    The Situation Job for this employee type.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), npc_employee_situation_count=TunableVariant(description='\n                    The number of situations to create at an NPC-owned business\n                    lot.\n                    ', tuned_count=TunableRange(tunable_type=int, minimum=0, default=3), default='tuned_count', locked_args={'defer_to_zone_director': DEFER_NPC_EMPLOYEE_COUNT_TO_ZONE_DIRECTOR})), value_name='Employee_Situation_Data', tuning_group=GroupNames.BUSINESS)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._business_manager = None
        self._customer_situation_alarm_handle = None
        self._customer_situation_ids = []
        self._employee_situation_ids = defaultdict(set)
        self._is_npc_store = False
        self._employee_situation_id_list = []
        self._customers_allowed = True

    def on_startup(self):
        super().on_startup()
        self._business_manager = services.business_service().get_business_manager_for_zone()
        if self._should_create_npc_business_manager():
            self._business_manager = self._get_new_npc_business_manager()
        self.create_customer_alarm()
        if self._business_manager is None and self._business_manager is not None:
            self._business_manager.update_employees()
            self._business_manager.try_open_npc_store()

    def _should_create_npc_business_manager(self):
        return False

    @property
    def business_manager(self):
        return self._business_manager

    @property
    def supported_business_types(self):
        raise NotImplementedError('Business Zone Directors should support at least one business type.')

    def on_shutdown(self):
        if self._customer_situation_alarm_handle is not None:
            alarms.cancel_alarm(self._customer_situation_alarm_handle)
            self._customer_situation_alarm_handle = None
        super().on_shutdown()

    @property
    def supports_open_street_director(self):
        if self._business_manager is None:
            return True
        if self._business_manager.owner_household_id is None:
            return True
        return not self._business_manager.is_open

    def _did_sim_overstay(self, sim_info):
        if self._business_manager is None:
            return super()._did_sim_overstay(sim_info)
        if self._business_manager.is_household_owner(sim_info.household_id):
            return False
        if sim_info.is_selectable:
            return False
        if self._business_manager.should_close_after_load():
            return True
        return super()._did_sim_overstay(sim_info)

    def start_employee_situations(self, employees, owned_by_npc=False):
        if self._business_manager is None:
            return
        if owned_by_npc or not employees:
            return
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None:
            return
        for (employee_sim_id, employee_data) in employees.items():
            self._start_employee_situation(employee_sim_id, employee_data, situation_manager)
        if owned_by_npc:
            self._start_npc_employee_situations()

    def start_customer_situation(self, situation, create_params=None):
        if self._business_manager is None:
            return
        situation_manager = services.get_zone_situation_manager()
        guest_list = situation.get_predefined_guest_list()
        if guest_list is None:
            guest_list = SituationGuestList(invite_only=True)
        params = {'user_facing': False} if create_params is None else create_params
        try:
            creation_source = self.instance_name
        except:
            creation_source = str(self)
        situation_id = situation_manager.create_situation(situation, guest_list=guest_list, spawn_sims_during_zone_spin_up=True, creation_source=creation_source, **params)
        if situation_id is None:
            logger.error('Failed to create customer situation: {}', situation, owner='tingyul')
            return
        self._customer_situation_ids.append(situation_id)
        return situation_id

    def _start_npc_employee_situations(self):
        if self._business_manager is None:
            return
        situation_manager = services.get_zone_situation_manager()
        try:
            creation_source = self.instance_name
        except:
            creation_source = str(self)
        for (employee_type, employee_situation_data) in self.employee_situation_data.items():
            desired_count = employee_situation_data.npc_employee_situation_count
            if desired_count == DEFER_NPC_EMPLOYEE_COUNT_TO_ZONE_DIRECTOR:
                desired_count = self._get_desired_employee_count(employee_type)
            num_to_create = desired_count - len(self._employee_situation_ids[employee_type])
            if num_to_create < 1:
                pass
            else:
                for _ in range(num_to_create):
                    situation_id = situation_manager.create_situation(self._get_npc_employee_situation_for_employee_type(employee_type), guest_list=SituationGuestList(invite_only=True), spawn_sims_during_zone_spin_up=True, user_facing=False, creation_source=creation_source)
                    self._employee_situation_ids[employee_type].add(situation_id)

    def _get_desired_employee_count(self, employee_type):
        raise NotImplementedError

    def get_employee_type_for_situation(self, employee_situation_id):
        for (employee_type, situation_ids) in self._employee_situation_ids.items():
            for situation_id in situation_ids:
                if situation_id == employee_situation_id:
                    return employee_type

    def on_remove_employee(self, sim_info):
        if self._business_manager is None:
            return
        situation_manager = services.get_zone_situation_manager()
        for situation_id_list in self._employee_situation_ids.values():
            for situation_id in tuple(situation_id_list):
                situation = situation_manager.get(situation_id)
                if situation is not None:
                    employee_sim_info = situation.get_employee_sim_info()
                    if employee_sim_info is not None and sim_info is employee_sim_info:
                        situation_manager.destroy_situation_by_id(situation_id)
                        situation_id_list.remove(situation_id)

    def on_add_employee(self, sim_info, employee_data):
        if self._business_manager is None:
            return
        if not self._business_manager.is_open:
            return
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None:
            return
        self._start_employee_situation(sim_info.id, employee_data, situation_manager)

    def _start_employee_situation(self, employee_sim_id, employee_data, situation_manager):
        employee_type = employee_data.employee_type
        employee_situation_data = self.employee_situation_data[employee_type]
        guest_list = SituationGuestList(invite_only=True)
        guest_info = SituationGuestInfo.construct_from_purpose(employee_sim_id, employee_situation_data.situation_job, SituationInvitationPurpose.CAREER)
        guest_info.expectation_preference = True
        guest_list.add_guest_info(guest_info)
        try:
            creation_source = self.instance_name
        except:
            creation_source = str(self)
        situation_id = situation_manager.create_situation(self._get_employee_situation_for_employee_type(employee_type), guest_list=guest_list, spawn_sims_during_zone_spin_up=True, user_facing=False, creation_source=creation_source)
        self._employee_situation_ids[employee_type].add(situation_id)

    def _customer_situation_alarm_callback(self, *_, **__):
        if self._business_manager is None or not self._business_manager.is_open:
            return
        self._on_customer_situation_request()

    def create_situations_during_zone_spin_up(self):
        super().create_situations_during_zone_spin_up()
        self._setup_employee_situation_map()
        if self._business_manager is not None and self._business_manager.is_open and self._business_manager.is_owned_by_npc:
            self._start_npc_employee_situations()

    def _populate_situation_employee_map(self):
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._employee_situation_id_list:
            situation = situation_manager.get(situation_id)
            if situation is None:
                logger.error('Save data included situation id {} that no longer exist on the manager', situation_id)
            else:
                employee_sim_info = situation.get_employee_sim_info()
                employee_data = self._business_manager.get_employee_data(employee_sim_info)
                if employee_data is None:
                    logger.error('No employee information for situation id {} and Sim {}', situation_id, employee_sim_info)
                else:
                    self._employee_situation_ids[employee_data.employee_type].add(situation_id)
        self._employee_situation_id_list.clear()

    def _validate_npc_situation_employee_map(self):
        situation_manager = services.get_zone_situation_manager()
        for (employee_type, situation_ids) in self._employee_situation_ids.items():
            for situation_id in list(situation_ids):
                situation = situation_manager.get(situation_id)
                if situation is None:
                    logger.error('Save data included situation id {} that no longer exist on the manager', situation_id)
                    self._employee_situation_ids[employee_type].remove(situation_id)

    def _setup_employee_situation_map(self):
        if self.business_manager is not None and self.business_manager.is_owned_by_npc:
            self._validate_npc_situation_employee_map()
        else:
            self._populate_situation_employee_map()

    def remove_stale_customer_situations(self):
        if self._business_manager is None:
            return
        situation_manager = services.get_zone_situation_manager()
        self._customer_situation_ids = [situation_id for situation_id in self._customer_situation_ids if situation_manager.get(situation_id) is not None]

    def _get_new_npc_business_manager(self):
        pass

    def _get_employee_situation_for_employee_type(self, employee_type):
        raise NotImplementedError

    def _get_npc_employee_situation_for_employee_type(self, employee_type):
        raise NotImplementedError

    def _on_customer_situation_request(self):
        raise NotImplementedError

    def allows_new_customers(self):
        return self._customers_allowed

    def set_customers_allowed(self, customers_allowed):
        if self._customers_allowed != customers_allowed:
            self._customers_allowed = customers_allowed
            if customers_allowed or self._customer_situation_alarm_handle:
                alarms.cancel_alarm(self._customer_situation_alarm_handle)
                self._customer_situation_alarm_handle = None
                self._on_customers_disallowed()
            else:
                self.create_customer_alarm()

    def _on_customers_disallowed(self):
        pass

    def _save_custom_zone_director(self, zone_director_proto, writer):
        self._save_customer_situations(zone_director_proto, writer)
        self._save_employee_situations(zone_director_proto, writer)
        super()._save_custom_zone_director(zone_director_proto, writer)

    def _save_customer_situations(self, zone_director_proto, writer):
        if self._customer_situation_ids:
            writer.write_uint64s('customer_situation_ids', self._customer_situation_ids)

    def _save_employee_situations(self, zone_director_proto, writer):
        if not self.business_manager.is_owned_by_npc:
            return
        if self._employee_situation_ids:
            writer.write_uint64s('npc_employee_situation_types', self._employee_situation_ids.keys())
            for (employee_type, situation_ids) in self._employee_situation_ids.items():
                writer.write_uint64s('npc_employee_situations_{}'.format(employee_type.value), situation_ids)

    def _load_custom_zone_director(self, zone_director_proto, reader):
        self._load_customer_situations(zone_director_proto, reader)
        self._load_employee_situations(zone_director_proto, reader)
        super()._load_custom_zone_director(zone_director_proto, reader)

    def _load_customer_situations(self, zone_director_proto, reader):
        if reader is not None:
            self._customer_situation_ids = reader.read_uint64s('customer_situation_ids', [])

    def _load_employee_situations(self, zone_director_proto, reader):
        if reader is not None:
            employee_situations = set()
            persisted_employee_types = reader.read_uint64s('npc_employee_situation_types', [])
            for employee_type in persisted_employee_types:
                employee_situations_for_type = reader.read_uint64s('npc_employee_situations_{}'.format(employee_type), [])
                if not employee_situations_for_type:
                    pass
                else:
                    employee_situations.update(employee_situations_for_type)
                    self._employee_situation_ids[BusinessEmployeeType(employee_type)] = set(employee_situations_for_type)

    def create_customer_alarm(self):
        self._customer_situation_alarm_handle = alarms.add_alarm(self, create_time_span(minutes=self.customer_situation_interval), self._customer_situation_alarm_callback, repeating=True)
