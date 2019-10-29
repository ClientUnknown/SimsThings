import collectionsfrom alarms import add_alarmfrom business.business_enums import BusinessTypefrom date_and_time import date_and_time_from_week_time, create_time_spanfrom sims4 import PropertyStreamWriterfrom sims4.math import clampfrom sims4.service_manager import Servicefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposeimport alarmsimport clockimport servicesimport sims4.loglogger = sims4.log.Logger('ServiceNPCManager')
class ServiceNpcSituationCreationParams:

    def __init__(self, hiring_household, service_npc_type, user_specified_data_id, is_recurring):
        self.hiring_household = hiring_household
        self.service_npc_type = service_npc_type
        self.user_specified_data_id = user_specified_data_id
        self.is_recurring = is_recurring

class ServiceNpcService(Service):

    def __init__(self):
        self._service_npc_requests = []
        self._auto_scheduled_services_enabled = True
        self._bill_collection_alarms = {}
        self._active_service_sim_infos = collections.defaultdict(set)

    def request_service(self, household, service_npc_tuning, from_load=False, user_specified_data_id=None, is_recurring=False):
        if self.is_service_already_in_request_list(household, service_npc_tuning):
            return
        service_record = household.get_service_npc_record(service_npc_tuning.guid64)
        if service_record.hired and not from_load:
            return
        service_record.hired = True
        service_record.recurring = is_recurring
        service_record.user_specified_data_id = user_specified_data_id
        if from_load:
            min_alarm_time_span = None
        else:
            min_alarm_time_span = clock.interval_in_sim_minutes(service_npc_tuning.request_offset)
        min_duration_remaining = service_npc_tuning.min_duration_left_for_arrival_on_lot()
        situation_creation_params = ServiceNpcSituationCreationParams(household, service_npc_tuning, user_specified_data_id, is_recurring)
        service_npc_request = service_npc_tuning.work_hours(start_callback=self._send_service_npc, min_alarm_time_span=min_alarm_time_span, min_duration_remaining=min_duration_remaining, extra_data=situation_creation_params)
        self._service_npc_requests.append(service_npc_request)
        request_trigger_time = service_npc_request.get_alarm_finishing_time()
        if service_npc_tuning.bill_time_of_day is not None:
            self._service_start_time = services.time_service().sim_now
            time_span = self._service_start_time.time_till_next_day_time(service_npc_tuning.bill_time_of_day.time_of_day)
            repeating_time_span = create_time_span(days=1)
            self._bill_collection_alarms[service_npc_tuning.guid64] = add_alarm(self, time_span, lambda _: self._run_bill_collection(household, service_npc_tuning), repeating=True, repeating_time_span=repeating_time_span)
        return request_trigger_time

    def _send_service_npc(self, scheduler, alarm_data, situation_creation_params):
        household = situation_creation_params.hiring_household
        service_npc_type = situation_creation_params.service_npc_type
        if self._auto_scheduled_services_enabled or service_npc_type.auto_schedule_on_client_connect():
            return
        service_record = household.get_service_npc_record(service_npc_type.guid64)
        preferred_sim_id = service_record.get_preferred_sim_id()
        situation_type = service_npc_type.situation
        user_specified_data_id = situation_creation_params.user_specified_data_id
        now = services.time_service().sim_now
        situation_manager = services.get_zone_situation_manager()
        is_situation_running = situation_manager.is_situation_running(situation_type)
        if service_record.time_last_started_service is not None and alarm_data.start_time is not None:
            alarm_start_time_absolute = date_and_time_from_week_time(now.week(), alarm_data.start_time)
            if service_record.time_last_started_service >= alarm_start_time_absolute and not service_npc_type.full_time_npc:
                return
            if service_npc_type.full_time_npc and is_situation_running:
                return
        if not (service_record.time_last_started_service is None or service_npc_type.full_time_npc):
            service_record.time_last_started_service = now
            service_record.time_last_finished_service = None
        duration = alarm_data.end_time - now.time_since_beginning_of_week()
        min_duration = service_npc_type.min_duration_left_for_arrival_on_lot()
        if duration < min_duration:
            service_npc_type.fake_perform(household)
            return
        min_duration = service_npc_type.min_work_duration()
        max_duration = service_npc_type.max_work_duration()
        duration = clamp(min_duration, duration.in_minutes(), max_duration)
        guest_list = self._generate_situation_guest_list(preferred_sim_id, service_npc_type, household)
        situation_creation_params_writer = PropertyStreamWriter()
        situation_creation_params_writer.write_uint64('household_id', household.id)
        situation_creation_params_writer.write_uint64('service_npc_type_id', service_npc_type.guid64)
        if user_specified_data_id is not None:
            situation_creation_params_writer.write_uint64('user_specified_data_id', user_specified_data_id)
        situation_creation_params_writer.write_bool('is_recurring', situation_creation_params.is_recurring)
        if service_npc_type.full_time_npc:
            duration = 0
            if is_situation_running:
                return
        self._situation_id = situation_manager.create_situation(situation_type, guest_list, user_facing=False, duration_override=duration, custom_init_writer=situation_creation_params_writer)

    def register_service_npc(self, sim_id, service_npc_type):
        self._active_service_sim_infos[sim_id].add(service_npc_type)

    def get_sim_filter_gsi_name(self):
        return str(self)

    def _generate_situation_guest_list(self, preferred_sim_id, service_npc_type, hiring_household):
        guest_list = SituationGuestList(invite_only=True)
        blacklist_sim_ids = hiring_household.get_all_fired_service_npc_ids()
        if preferred_sim_id is not None:
            guest_info = SituationGuestInfo.construct_from_purpose(preferred_sim_id, service_npc_type.situation.default_job(), SituationInvitationPurpose.PREFERRED)
            guest_info.expectation_preference = True
            guest_list.add_guest_info(guest_info)
            return guest_list
        if service_npc_type.exclusive_to_household:
            household_manager = services.household_manager()
            if household_manager is None:
                logger.error('Household manager is None when service npc is being scheduled for service type {}', service_npc_type)
                return guest_list
            for household in household_manager.values():
                if household.id == hiring_household:
                    pass
                else:
                    blacklist_sim_ids.update(household.get_preferred_service_npcs())
        worker_filter = service_npc_type.situation.default_job().filter
        filter_results = services.sim_filter_service().submit_matching_filter(sim_filter=worker_filter, allow_yielding=False, blacklist_sim_ids=blacklist_sim_ids, gsi_source_fn=self.get_sim_filter_gsi_name)
        if not filter_results:
            return guest_list
        for result in filter_results:
            guest_info = SituationGuestInfo.construct_from_purpose(result.sim_info.sim_id, service_npc_type.situation.default_job(), SituationInvitationPurpose.PREFERRED)
            guest_info.expectation_preference = True
            guest_list.add_guest_info(guest_info)
        return guest_list

    def _run_bill_collection(self, household, service_npc_type):
        service_record = household.get_service_npc_record(service_npc_type.guid64, add_if_no_record=False)
        if service_record is None:
            logger.error('Service NPC {} for household {} is has no record but its still trying to collect', service_npc_type, household, owner='camilogarcia')
            return
        include_up_front_cost = True if service_record.time_last_finished_service is None else False
        now = services.time_service().sim_now
        service_record.time_last_finished_service = now
        time_worked = now - (service_record.time_last_started_service or now)
        time_worked_in_hours = time_worked.in_hours()
        billed_amount = 0
        total_cost = service_npc_type.get_cost(time_worked_in_hours, include_up_front_cost=include_up_front_cost)
        if total_cost > 0:
            (paid_amount, billed_amount) = service_npc_type.try_charge_for_service(household, total_cost)
        if billed_amount > 0:
            if household.bills_manager.is_any_utility_delinquent():
                service_npc_type.display_payment_notification(household, paid_amount, billed_amount, service_npc_type.bill_time_of_day.delinquent_npc_quit_notification)
                situation_manager = services.get_zone_situation_manager()
                running_situation = situation_manager.get_situation_by_type(service_npc_type.situation)
                if running_situation is not None:
                    service_sim = running_situation.service_sim()
                    if service_sim is not None:
                        service_record.add_fired_sim(service_sim.id)
                        service_record.remove_preferred_sim(service_sim.id)
                        self.on_service_sim_fired(service_sim.id, service_npc_type)
                services.current_zone().service_npc_service.cancel_service(household, service_npc_type)
                return
            service_npc_type.display_payment_notification(household, paid_amount, billed_amount, service_npc_type.bill_time_of_day.fail_to_pay_notification)
        if service_npc_type.full_time_npc:
            service_record.time_last_started_service = now

    def cancel_service(self, household, service_npc_type):
        for request in tuple(self._service_npc_requests):
            situation_creation_params = request.extra_data
            schedule_household = situation_creation_params.hiring_household
            request_service_npc_tuning = situation_creation_params.service_npc_type
            if household == schedule_household and request_service_npc_tuning is service_npc_type:
                request.destroy()
                self._service_npc_requests.remove(request)
        service_record = household.get_service_npc_record(service_npc_type.guid64, add_if_no_record=False)
        if service_record is not None:
            service_record.on_cancel_service()
        if service_npc_type.full_time_npc:
            situation_manager = services.get_zone_situation_manager()
            running_situation = situation_manager.get_situation_by_type(service_npc_type.situation)
            if running_situation is not None:
                situation_manager.destroy_situation_by_id(running_situation.id)
        bill_alarm = self._bill_collection_alarms.pop(service_npc_type.guid64, None)
        if bill_alarm is not None:
            alarms.cancel_alarm(bill_alarm)
            bill_alarm = None

    def on_service_sim_fired(self, sim_id, service_npc_type):
        service_type_set = self._active_service_sim_infos.get(sim_id)
        if service_npc_type in service_type_set:
            service_type_set.remove(service_npc_type)
            if not service_type_set:
                del self._active_service_sim_infos[sim_id]

    def is_service_already_in_request_list(self, household, service_npc_type):
        for request in self._service_npc_requests:
            situation_creation_params = request.extra_data
            schedule_household = situation_creation_params.hiring_household
            request_service_npc_tuning = situation_creation_params.service_npc_type
            if household == schedule_household and request_service_npc_tuning is service_npc_type:
                return True
        return False

    def on_all_households_and_sim_infos_loaded(self, client):
        household = client.household
        if household is None:
            return
        household_manager = services.household_manager()
        if household_manager is None:
            return
        service_npc_manager = services.service_npc_manager()
        for npc_household in household_manager.values():
            npc_household.load_fixup_service_npcs()
            preferred_npc_data = npc_household.get_all_prefered_sim_id_service_id()
            if preferred_npc_data is None:
                pass
            else:
                for (sim_id, service_type) in preferred_npc_data:
                    service_npc_tuning = service_npc_manager.get(service_type)
                    if service_npc_tuning is not None:
                        self.register_service_npc(sim_id, service_npc_tuning)
        if household.id != services.active_lot().owner_household_id:
            return
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None and business_manager.business_type != BusinessType.INVALID:
            return
        all_hired_service_npcs = household.get_all_hired_service_npcs()
        for service_npc_resource_key in services.service_npc_manager().types:
            service_npc_tuning = services.service_npc_manager().get(service_npc_resource_key)
            if not service_npc_tuning.auto_schedule_on_client_connect():
                if service_npc_tuning.guid64 in all_hired_service_npcs:
                    is_recurring = False
                    user_specified_data_id = None
                    if service_npc_tuning.auto_schedule_on_client_connect():
                        is_recurring = True
                    else:
                        service_npc_record = household.get_service_npc_record(service_npc_tuning.guid64, add_if_no_record=False)
                        if service_npc_record:
                            is_recurring = service_npc_record.recurring
                            user_specified_data_id = service_npc_record.user_specified_data_id
                    self.request_service(household, service_npc_tuning, from_load=True, is_recurring=is_recurring, user_specified_data_id=user_specified_data_id)
            is_recurring = False
            user_specified_data_id = None
            if service_npc_tuning.auto_schedule_on_client_connect():
                is_recurring = True
            else:
                service_npc_record = household.get_service_npc_record(service_npc_tuning.guid64, add_if_no_record=False)
                if service_npc_record:
                    is_recurring = service_npc_record.recurring
                    user_specified_data_id = service_npc_record.user_specified_data_id
            self.request_service(household, service_npc_tuning, from_load=True, is_recurring=is_recurring, user_specified_data_id=user_specified_data_id)

    def on_cleanup_zone_objects(self, client):
        time_of_last_save = services.current_zone().time_of_last_save()
        now = services.time_service().sim_now
        self._fake_perform_services_if_necessary(time_of_last_save, now)

    def get_culling_npc_score(self, sim_id):
        service_tuning_set = self._active_service_sim_infos.get(sim_id)
        max_additional_culling_immunity = 0
        if service_tuning_set is not None:
            for service_tuning in service_tuning_set:
                if service_tuning.additional_culling_immunity:
                    max_additional_culling_immunity = max(max_additional_culling_immunity, service_tuning.additional_culling_immunity)
        return max_additional_culling_immunity

    def _fake_perform_services_if_necessary(self, time_period_start, now):
        for scheduler in self._service_npc_requests:
            situation_creation_params = scheduler.extra_data
            household = situation_creation_params.hiring_household
            service_npc_type = situation_creation_params.service_npc_type
            service_record = household.get_service_npc_record(service_npc_type.guid64, add_if_no_record=False)
            if service_record is None:
                pass
            else:
                (time_until_service_arrives, alarm_data_entries) = scheduler.time_until_next_scheduled_event(time_period_start, schedule_immediate=True)
                if len(alarm_data_entries) != 1:
                    logger.error('There are {} alarm data entries instead of 1 when fake performing services: {}', len(alarm_data_entries), alarm_data_entries, owner='bhill')
                else:
                    alarm_data = alarm_data_entries[0]
                    time_service_starts = time_period_start + time_until_service_arrives
                    time_service_would_end = alarm_data.end_time
                    min_service_duration = service_npc_type.min_duration_left_for_arrival_on_lot()
                    if not now < time_service_starts:
                        if now + min_service_duration <= time_service_would_end:
                            pass
                        elif service_record.time_last_started_service is not None and service_record.time_last_started_service >= time_service_starts:
                            pass
                        else:
                            service_npc_type.fake_perform(household)
                            service_record.time_last_started_service = time_service_starts
                            service_record.time_last_finished_service = min(now, time_service_would_end)
                            if service_record.recurring or not service_npc_type.full_time_npc:
                                self.cancel_service(household, service_npc_type)
