from collections import OrderedDictimport itertoolsfrom protocolbuffers import Venue_pb2from business.business_enums import BusinessTypefrom business.business_zone_director_mixin import BusinessZoneDirectorMixinfrom clock import interval_in_sim_minutesfrom sims.outfits.outfit_enums import OutfitCategoryfrom sims.sim_info_base_wrapper import SimInfoBaseWrapperfrom sims.sim_info_types import Genderfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableReference, HasTunableSingletonFactory, AutoFactoryInit, TunableMapping, TunableRange, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom situations.service_npcs.modify_lot_items_tuning import TunableObjectMatchesDefinitionOrTagTestfrom situations.situation_curve import SituationCurvefrom venues.scheduling_zone_director import SchedulingZoneDirectorfrom venues.visitor_situation_on_arrival_zone_director_mixin import VisitorSituationOnArrivalZoneDirectorMixinfrom vet.vet_clinic_manager import VetClinicManagerfrom vet.vet_clinic_tuning import VetClinicTuning, VetEmployeeOutfitTypefrom vet.vet_clinic_utils import get_vet_clinic_zone_directorimport build_buyimport servicesimport sims4.logimport simslogger = sims4.log.Logger('Vet Clinic', default_owner='jdimailig')SUPPORTED_BUSINESS_TYPES = (BusinessType.VET,)TRACKED_VET_ASSIGNMENTS_VETS = 'vet_assignments_vets'TRACKED_VET_ASSIGNMENTS_CUSTOMERS = 'vet_assignments_customers_{}'TRACKED_WAITING_SITUATION_IDS = 'waiting_situation_ids'TRACKED_WAITING_SITUATION_CUSTOMERS = 'waiting_situation_customer_ids_{}'CTA_DISABLED = 'cta_disabled'
class _ObjectBasedWaitingCustomerCap(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'object_count_waiting_customer_cap': TunableMapping(description='\n            For each amount defined, set the cap to waiting customers.\n            \n            For this test we are using number of Vet Clinic exam tables.\n            \n            If the actual count exceeds the all the keys,\n            then it will use the cap for the key with the highest value.\n            ', set_default_as_first_entry=True, key_type=Tunable(description='\n                Number of exam tables.\n                ', tunable_type=int, default=0), value_type=TunableRange(description='\n                Value to cap waiting customers at.\n                ', tunable_type=int, default=2, minimum=0))}

    def get_cap_amount(self):
        zone_director = get_vet_clinic_zone_director()
        if zone_director is None:
            return 0
        exam_table_thresholds = sorted(self.object_count_waiting_customer_cap.keys(), reverse=True)
        num_exam_tables = zone_director.num_exam_tables
        for threshold in exam_table_thresholds:
            if num_exam_tables >= threshold:
                return self.object_count_waiting_customer_cap[threshold]
        return 0

class VetClinicZoneDirector(BusinessZoneDirectorMixin, VisitorSituationOnArrivalZoneDirectorMixin, SchedulingZoneDirector):
    INSTANCE_TUNABLES = {'customer_situation_type_curve': SituationCurve.TunableFactory(description="\n            When customer situations are being generated, they'll be pulled\n            based on the tuning in this.\n            \n            The desired count in this tuning is not used.\n            \n            Otherwise it situation count is pulled from business multipliers.\n            ", tuning_group=GroupNames.BUSINESS, get_create_params={'user_facing': False}), 'employee_situation': TunableReference(description='\n            Employee situation to put employees in. \n            ', manager=services.get_instance_manager(Types.SITUATION), tuning_group=GroupNames.BUSINESS), 'exam_table_test': TunableObjectMatchesDefinitionOrTagTest(description='\n            Tests used to count number of exam tables that are in this zone.  \n            The number of these found will limit the number of customers \n            situations that are generated.\n            ', tuning_group=GroupNames.BUSINESS), 'podium_call_to_action': TunableReference(description='\n            Call to action to use to highlight the vet podium when visiting the vet.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CALL_TO_ACTION)), 'waiting_customer_cap': _ObjectBasedWaitingCustomerCap.TunableFactory()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._num_exam_tables = 0
        self._default_uniform = {}
        self._custom_uniform = {}
        self._vet_to_customer_assignments = {}
        self._waiting_situations = OrderedDict()
        self._reservations = {}
        self._has_cta_been_seen = False
        self._cta_disabled = False

    def _save_custom_zone_director(self, zone_director_proto, writer):
        writer.write_uint64s(TRACKED_VET_ASSIGNMENTS_VETS, list(self._vet_to_customer_assignments.keys()))
        for (vet_id, customer_assignments) in self._vet_to_customer_assignments.items():
            writer.write_uint64s(TRACKED_VET_ASSIGNMENTS_CUSTOMERS.format(vet_id), list(customer_assignments))
        writer.write_uint64s(TRACKED_WAITING_SITUATION_IDS, list(self._waiting_situations.keys()))
        for (situation_id, waiting_situations) in self._waiting_situations.items():
            writer.write_uint64s(TRACKED_WAITING_SITUATION_CUSTOMERS.format(situation_id), list(waiting_situations))
        writer.write_bool(CTA_DISABLED, self._cta_disabled)
        super()._save_custom_zone_director(zone_director_proto, writer)

    def _load_custom_zone_director(self, zone_director_proto, reader):
        if reader is not None:
            vets_with_assigned_customers = reader.read_uint64s(TRACKED_VET_ASSIGNMENTS_VETS, [])
            for vet_id in vets_with_assigned_customers:
                assigned_customers = reader.read_uint64s(TRACKED_VET_ASSIGNMENTS_CUSTOMERS.format(vet_id), [])
                if assigned_customers:
                    self._vet_to_customer_assignments[vet_id] = list(assigned_customers)
            waiting_situation_ids = reader.read_uint64s(TRACKED_WAITING_SITUATION_IDS, [])
            for situation_id in waiting_situation_ids:
                situation_customers = reader.read_uint64s(TRACKED_WAITING_SITUATION_CUSTOMERS.format(situation_id), [])
                if situation_customers:
                    self._waiting_situations[situation_id] = list(situation_customers)
            self._cta_disabled = reader.read_bool(CTA_DISABLED, False)
        super()._load_custom_zone_director(zone_director_proto, reader)

    def on_startup(self):
        super().on_startup()
        self._load_default_uniforms()
        self.refresh_configuration()

    def clear_state(self):
        self._vet_to_customer_assignments.clear()
        self._waiting_situations.clear()
        self._reservations.clear()

    def on_loading_screen_animation_finished(self):
        if any(sim_info.is_pet for sim_info in self._traveled_sim_infos):
            self._trigger_podium_call_to_action()
        super().on_loading_screen_animation_finished()

    def handle_sim_summon_request(self, sim_info, purpose):
        super().handle_sim_summon_request(sim_info, purpose)
        if sim_info.is_pet:
            self._trigger_podium_call_to_action()

    def _trigger_podium_call_to_action(self):
        if services.current_zone().active_household_changed_between_save_and_load() or services.current_zone().time_has_passed_in_world_since_zone_save():
            self._cta_disabled = False
        if self._cta_disabled:
            return
        if self._has_cta_been_seen or self._business_manager.is_active_household_and_zone():
            return
        services.call_to_action_service().begin(self.podium_call_to_action, self)
        self._has_cta_been_seen = True

    def on_cta_ended(self, value):
        self._cta_disabled = True

    def on_shutdown(self):
        if self._business_manager is not None:
            self._business_manager.prepare_for_off_lot_simulation()
        super().on_shutdown()

    def on_exit_buildbuy(self):
        super().on_exit_buildbuy()
        self.refresh_configuration()

    def create_situations_during_zone_spin_up(self):
        if self.business_manager is not None and self.business_manager.is_open:
            if services.current_zone().time_has_passed_in_world_since_zone_save() or services.current_zone().active_household_changed_between_save_and_load():
                self.clear_state()
            self._business_manager.start_already_opened_business()
            self._on_customer_situation_request()
        super().create_situations_during_zone_spin_up()

    def _process_traveled_sim(self, sim_info):
        current_zone = services.current_zone()
        if current_zone.is_first_visit_to_zone or (current_zone.time_has_passed_in_world_since_zone_save() or current_zone.active_household_changed_between_save_and_load()) or not (sim_info.startup_sim_location is not None and services.active_lot().is_position_on_lot(sim_info.startup_sim_location.transform.translation)):
            super()._process_traveled_sim(sim_info)
        else:
            self._request_spawning_of_sim_at_location(sim_info, sims.sim_spawner_service.SimSpawnReason.TRAVELING)

    def _process_zone_saved_sim(self, sim_info):
        if services.current_zone().time_has_passed_in_world_since_zone_save() or services.current_zone().active_household_changed_between_save_and_load():
            business_manager = services.business_service().get_business_manager_for_zone()
            if business_manager is not None and business_manager.is_employee(sim_info):
                self._on_reinitiate_zone_saved_sim(sim_info)
            else:
                self._on_clear_zone_saved_sim(sim_info)
        else:
            super()._process_zone_saved_sim(sim_info)

    def _should_create_npc_business_manager(self):
        return True

    def _get_new_npc_business_manager(self):
        npc_business_manager = VetClinicManager()
        npc_business_manager.set_zone_id(services.current_zone_id())
        npc_business_manager.set_owner_household_id(None)
        return npc_business_manager

    def _get_employee_situation_for_employee_type(self, employee_type):
        return self.employee_situation

    def _get_npc_employee_situation_for_employee_type(self, employee_type):
        return self.employee_situation

    def _get_desired_employee_count(self, employee_type):
        return self._num_exam_tables

    def _on_customer_situation_request(self):
        self.remove_stale_customer_situations()
        desired_situation_count = self._get_num_desired_customer_situations()
        current_customer_count = len(self._customer_situation_ids)
        if current_customer_count >= desired_situation_count:
            waiting_customers = sum(1 for _ in self.customer_situations_gen(lambda s: not s.customer_has_been_seen))
            waiting_customer_cap = self.waiting_customer_cap.get_cap_amount()
            if waiting_customer_cap <= waiting_customers:
                return
        (new_customer_situation, params) = self.customer_situation_type_curve.get_situation_and_params()
        if new_customer_situation is None:
            return
        else:
            situation_id = self.start_customer_situation(new_customer_situation, create_params=params)
            if situation_id is None:
                logger.info('Trying to create a new customer situation for vet clinic but failed.')
                return

    def apply_zone_outfit(self, sim_info, situation):
        (outfit_data, outfit_key) = self.get_zone_outfit(sim_info)
        if outfit_data is not None:
            sim_info.generate_merged_outfit(outfit_data, (OutfitCategory.CAREER, 0), sim_info.get_current_outfit(), outfit_key)
            sim_info.set_current_outfit((OutfitCategory.CAREER, 0))
            sim_info.resend_current_outfit()

    def get_zone_outfit(self, sim_info):
        gender = sim_info.clothing_preference_gender
        (outfit_index, outfit_data) = self._custom_uniform.get(gender, (0, None))
        if outfit_data is None:
            outfit_data = self._default_uniform.get(gender, None)
        return (outfit_data, (OutfitCategory.CAREER, outfit_index))

    def _load_default_uniforms(self):
        self._default_uniform[Gender.MALE] = self._load_uniform_from_resource(VetClinicTuning.UNIFORM_EMPLOYEE_MALE)
        self._default_uniform[Gender.FEMALE] = self._load_uniform_from_resource(VetClinicTuning.UNIFORM_EMPLOYEE_FEMALE)

    def _load_uniform_from_resource(self, uniform_resource):
        sim_info_wrapper = SimInfoBaseWrapper()
        sim_info_wrapper.load_from_resource(uniform_resource)
        sim_info_wrapper.set_current_outfit((OutfitCategory.CAREER, 0))
        return sim_info_wrapper

    def refresh_configuration(self):
        self._update_from_venue_config()
        self._update_exam_table_count()

    def _update_from_venue_config(self):
        config_data = build_buy.get_current_venue_config(services.current_zone_id())
        if config_data is None:
            return
        vet_clinic_config = Venue_pb2.VetClinicConfiguration()
        vet_clinic_config.ParseFromString(config_data)
        self._custom_uniform.clear()
        for (i, outfit_data) in enumerate(vet_clinic_config.outfits):
            if i not in VetEmployeeOutfitType:
                break
            gender = Gender.MALE if i == VetEmployeeOutfitType.MALE_EMPLOYEE else Gender.FEMALE
            sim_info_wrapper = None
            mannequin_data = outfit_data.mannequin
            if mannequin_data.HasField('mannequin_id'):
                sim_info_wrapper = SimInfoBaseWrapper()
                sim_info_wrapper.load_sim_info(outfit_data.mannequin)
                sim_info_wrapper.set_current_outfit((OutfitCategory.CAREER, 0))
            self._custom_uniform[gender] = (outfit_data.outfit_index, sim_info_wrapper)

    def _update_exam_table_count(self):
        self._num_exam_tables = sum(1 for obj in services.object_manager().get_valid_objects_gen() if self.exam_table_test(objects=(obj,)))
        if self._business_manager is not None:
            self._business_manager.set_exam_table_count(self._num_exam_tables)

    @property
    def num_exam_tables(self):
        return self._num_exam_tables

    def _get_num_desired_customer_situations(self):
        business_manager = self._business_manager
        if business_manager is None or business_manager.is_owned_by_npc:
            return self._num_exam_tables
        situation_count = business_manager.get_ideal_customer_count()
        tracker = services.business_service().get_business_tracker_for_household(business_manager.owner_household_id, business_manager.business_type)
        situation_count += tracker.addtitional_customer_count
        return situation_count

    def on_customers_waiting(self, situation_id, customer_ids, player_situation=False):
        self._waiting_situations[situation_id] = customer_ids
        if player_situation:
            self._waiting_situations.move_to_end(situation_id, last=False)

    def on_vet_assigned(self, situation_id, vet_id, customer_ids):
        if situation_id in self._reservations:
            del self._reservations[situation_id]
        if situation_id in self._waiting_situations:
            del self._waiting_situations[situation_id]
        self._vet_to_customer_assignments[vet_id] = customer_ids

    def on_customer_situation_being_destroyed(self, situation_id):
        if situation_id in self._waiting_situations:
            del self._waiting_situations[situation_id]
        if situation_id in self._reservations:
            del self._reservations[situation_id]

    def remove_from_vet(self, vet_id):
        if vet_id in self._vet_to_customer_assignments.keys():
            del self._vet_to_customer_assignments[vet_id]

    def is_assigned_to_vet(self, customer_id, vet_id=None):
        if vet_id is not None:
            customers = self._vet_to_customer_assignments.get(vet_id, tuple())
            return customer_id in customers
        for cust_id in itertools.chain(self._vet_to_customer_assignments.values()):
            if cust_id == customer_id:
                return True
        return False

    def is_waiting_for_services(self, customer_sim_id):
        for situation_id in self._waiting_situations:
            if customer_sim_id in self._waiting_situations[situation_id]:
                return True
        return False

    def is_vet_attending_any_customers(self, vet_id):
        if vet_id in self._vet_to_customer_assignments.keys():
            return len(self._vet_to_customer_assignments[vet_id]) > 0
        return False

    def customer_situations_gen(self, criteria_test=None):
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._customer_situation_ids:
            situation = situation_manager.get(situation_id)
            if situation is None:
                pass
            elif criteria_test is None:
                yield situation
            elif criteria_test(situation):
                yield situation

    def waiting_sims_gen(self, potential_reserver_id):
        now = services.time_service().sim_now
        for situation_id in self._waiting_situations:
            if situation_id in self._reservations:
                reservation = self._reservations[situation_id]
                if not now < reservation['expiration'] or reservation['reserver_id'] != potential_reserver_id:
                    pass
                else:
                    for sim_id in self._waiting_situations[situation_id]:
                        yield services.object_manager().get(sim_id)
            else:
                for sim_id in self._waiting_situations[situation_id]:
                    yield services.object_manager().get(sim_id)

    def reserve_waiting_sim(self, reserved_sim_id, reserver_id):
        for situation_id in self._waiting_situations:
            if reserved_sim_id in self._waiting_situations[situation_id]:
                self._reservations[situation_id] = {'expiration': services.time_service().sim_now + interval_in_sim_minutes(30), 'reserver_id': reserver_id}

    def bill_owner_for_treatment(self, sim):
        if self._business_manager is not None:
            for customer_situation in self.customer_situations_gen():
                if not customer_situation.is_sim_in_situation(sim):
                    pass
                else:
                    self._business_manager.bill_owner_for_treatment(*customer_situation.get_payment_data())
                    customer_situation.apply_value_of_service()
                    break

    @property
    def supported_business_types(self):
        return SUPPORTED_BUSINESS_TYPES
