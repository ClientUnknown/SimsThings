from protocolbuffers import UI_pb2from careers.career_enums import CareerCategory, WORK_CAREER_CATEGORIESfrom careers.career_ops import CareerTimeOffReasonfrom date_and_time import TimeSpan, DateAndTimefrom distributor.shared_messages import build_icon_info_msg, IconInfoDatafrom drama_scheduler.drama_node import BaseDramaNode, DramaNodeUiDisplayTypefrom drama_scheduler.drama_node_types import DramaNodeTypefrom holidays.holiday_globals import HolidayState, HolidayTuningfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableReference, OptionalTunablefrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_types import SituationCallbackOptionfrom tunable_time import TunableTimeSpanimport alarmsimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('HolidayDramaNode', default_owner='nsavalani')HOLIDAY_START_TIME_TOKEN = 'holiday_start_time_ticks'HOLIDAY_END_TIME_TOKEN = 'holiday_end_time_ticks'
class HolidayDramaNode(BaseDramaNode):
    INSTANCE_TUNABLES = {'pre_holiday_duration': TunableTimeSpan(description="\n            This duration is used to calculate the drama node's start time for\n            main holidays by subtracting the tuned amount from the globally \n            tuned start time. The player is notified with a reminder for the\n            holiday, and decorations will be put up in the neighborhood.\n            For surprise holidays, this should be set to 0, as surprise \n            holidays have no pre-holiday state.\n            ", default_hours=23, locked_args={'days': 0, 'minutes': 0}), 'holiday': TunableReference(description='\n            The holiday that this drama node starts.\n            ', manager=services.get_instance_manager(sims4.resources.Types.HOLIDAY_DEFINITION))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._holiday_alarm = None
        self._state = None
        self._situation_ids = []
        self._holiday_end_time = None
        self._active_household_id = None
        self._holiday_start_time = None

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.HOLIDAY

    @classproperty
    def persist_when_active(cls):
        return True

    @classproperty
    def simless(cls):
        return True

    @property
    def is_in_preholiday(self):
        return self._state == HolidayState.PRE_DAY

    @property
    def is_running(self):
        return self._state == HolidayState.RUNNING

    @property
    def holiday_id(self):
        return self.holiday.guid64

    @property
    def day(self):
        if self._holiday_start_time is not None:
            return int(self._holiday_start_time.absolute_days())
        actual_start_time = self._selected_time + self.pre_holiday_duration()
        return int(actual_start_time.absolute_days())

    def get_time_off_reason(self, sim_info, career_category, career_end_time):
        holiday_service = services.holiday_service()
        if self._state == HolidayState.SHUTDOWN or holiday_service is None:
            return CareerTimeOffReason.NO_TIME_OFF
        take_time_off = False
        if career_category == CareerCategory.School:
            take_time_off = holiday_service.get_holiday_time_off_school(self.holiday_id)
        elif career_category in WORK_CAREER_CATEGORIES:
            take_time_off = holiday_service.get_holiday_time_off_work(self.holiday_id)
        elif career_category == CareerCategory.Volunteer:
            take_time_off = False
        else:
            logger.error('Unexpected CareerCategory {} when determining if a holiday should give Sims time off.', career_category)
        if take_time_off and (self.is_running or self.get_calendar_start_time() < career_end_time):
            return HolidayTuning.HOLIDAY_TIME_OFF_REASON
        return CareerTimeOffReason.NO_TIME_OFF

    def create_calendar_entry(self):
        calendar_entry = super().create_calendar_entry()
        active_household = services.active_household()
        if active_household is not None:
            holiday_service = services.holiday_service()
            build_icon_info_msg(IconInfoData(icon_resource=holiday_service.get_holiday_display_icon(self.holiday_id)), holiday_service.get_holiday_display_name(self.holiday_id), calendar_entry.icon_info)
            calendar_entry.holiday_id = self.holiday_id
            for tradition in holiday_service.get_holiday_traditions(self.holiday_id):
                calendar_entry.tradition_ids.append(tradition.guid64)
        return calendar_entry

    def create_calendar_alert(self):
        if self.ui_display_type == DramaNodeUiDisplayType.POP_UP_HOLIDAY:
            return
        holiday_service = services.holiday_service()
        calendar_alert = super().create_calendar_alert()
        calendar_alart_description = holiday_service.get_holiday_calendar_alert_notification(self.holiday_id)
        if calendar_alart_description is not None:
            calendar_alert.description = calendar_alart_description(holiday_service.get_holiday_display_name(self.holiday_id))
        build_icon_info_msg(IconInfoData(icon_resource=holiday_service.get_holiday_display_icon(self.holiday_id)), holiday_service.get_holiday_display_name(self.holiday_id), calendar_alert.calendar_icon)
        for tradition in holiday_service.get_holiday_traditions(self.holiday_id):
            calendar_alert.tradition_ids.append(tradition.guid64)
        return calendar_alert

    def get_calendar_start_time(self):
        return self.selected_time.time_of_next_day_time(HolidayTuning.MAIN_HOLIDAY_START_TIME)

    def get_calendar_end_time(self):
        return self.get_calendar_start_time() + HolidayTuning.HOLIDAY_DURATION()

    def _run_pre_holiday(self, from_load=False):
        self._state = HolidayState.PRE_DAY
        now = services.time_service().sim_now
        time_to_holiday_start = now.time_till_next_day_time(HolidayTuning.MAIN_HOLIDAY_START_TIME)
        self._holiday_start_time = now + time_to_holiday_start
        self._holiday_alarm = alarms.add_alarm(self, time_to_holiday_start, lambda _: self._run_holiday())
        active_household = services.active_household()
        active_household.holiday_tracker.preactivate_holiday(self.holiday_id)
        self._active_household_id = active_household.id
        lot_decoration_service = services.lot_decoration_service()
        if lot_decoration_service is not None:
            lot_decoration_service.request_holiday_decorations(self, from_load=from_load)

    def _on_holiday_situation_ended(self, situation_id, callback_option, _):
        current_zone = services.current_zone()
        if current_zone.is_zone_shutting_down:
            return
        self._unregister_situation_ended_callbacks()
        self._end_holiday()
        active_household = services.active_household()
        if active_household is not None:
            active_household.holiday_tracker.cancel_holiday(self.holiday_id)

    def _register_situation_ended_callbacks(self):
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._situation_ids:
            situation_manager.register_for_callback(situation_id, SituationCallbackOption.END_OF_SITUATION, self._on_holiday_situation_ended)

    def _unregister_situation_ended_callbacks(self):
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._situation_ids:
            situation_manager.unregister_callback(situation_id, SituationCallbackOption.END_OF_SITUATION, self._on_holiday_situation_ended)

    def _run_holiday(self, from_load=False):
        self._state = HolidayState.RUNNING
        if not from_load:
            self._holiday_end_time = services.time_service().sim_now + HolidayTuning.HOLIDAY_DURATION()
            holiday_duration = HolidayTuning.HOLIDAY_DURATION()
        else:
            holiday_duration = self._holiday_end_time - services.time_service().sim_now
        self._holiday_alarm = alarms.add_alarm(self, holiday_duration, self._holiday_end_callback)
        active_household = services.active_household()
        holiday_tracker = active_household.holiday_tracker
        if holiday_tracker.is_holiday_cancelled(self.holiday_id):
            return
        holiday_tracker.activate_holiday(self.holiday_id, from_load=from_load)
        self._active_household_id = active_household.id
        lot_decoration_service = services.lot_decoration_service()
        if lot_decoration_service is not None:
            lot_decoration_service.request_holiday_decorations(self, from_load=from_load)
        if from_load:
            (situation_ids, sims_needing_situations) = holiday_tracker.load_holiday_situations(self.holiday_id)
            self._situation_ids.extend(situation_ids)
            if not sims_needing_situations:
                self._register_situation_ended_callbacks()
                return
        else:
            sims_needing_situations = [sim_info for sim_info in active_household.sim_infos if sim_info.is_human]
        holiday_service = services.holiday_service()
        holiday_goals = list(tradition.situation_goal for tradition in holiday_service.get_holiday_traditions(self.holiday_id))
        for sim_info in sims_needing_situations:
            situation_id = self._create_holiday_situation(sim_info, holiday_goals)
        self._register_situation_ended_callbacks()

    def on_sim_added(self, sim_info):
        if self._state != HolidayState.RUNNING:
            return
        holiday_goals = list(tradition.situation_goal for tradition in services.holiday_service().get_holiday_traditions(self.holiday_id))
        situation_id = self._create_holiday_situation(sim_info, holiday_goals)
        if situation_id:
            services.get_zone_situation_manager().register_for_callback(situation_id, SituationCallbackOption.END_OF_SITUATION, self._on_holiday_situation_ended)

    def _create_holiday_situation(self, sim_info, holiday_goals):
        guest_list = SituationGuestList(invite_only=True, host_sim_id=sim_info.id)
        guest_list.add_guest_info(SituationGuestInfo(sim_info.id, HolidayTuning.HOLIDAY_JOB, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP))
        situation_id = services.get_zone_situation_manager().create_situation(HolidayTuning.HOLIDAY_SITUATION, guest_list=guest_list, linked_sim_id=sim_info.id, dynamic_goals=holiday_goals)
        if situation_id:
            self._situation_ids.append(situation_id)
        return situation_id

    def _give_time_off_loot(self, sim_info, time_off_loot):
        if sim_info is not None and time_off_loot is not None:
            resolver = sim_info.get_resolver()
            time_off_loot.apply_to_resolver(resolver)

    def _end_holiday(self):
        active_household = services.active_household()
        if not active_household.holiday_tracker.is_holiday_cancelled(self.holiday_id):
            self._unregister_situation_ended_callbacks()
            for situation_id in self._situation_ids:
                services.get_zone_situation_manager().destroy_situation_by_id(situation_id)
            active_household.holiday_tracker.deactivate_holiday()

    def _holiday_end_callback(self, _):
        self._state = HolidayState.SHUTDOWN
        self._unregister_situation_ended_callbacks()
        self._end_holiday()
        services.drama_scheduler_service().complete_node(self.uid)

    def schedule(self, resolver, specific_time=None, time_modifier=TimeSpan.ZERO):
        self._state = HolidayState.INITIALIZED
        success = super().schedule(resolver, specific_time=specific_time, time_modifier=time_modifier)
        if success:
            services.calendar_service().mark_on_calendar(self, advance_notice_time=HolidayTuning.HOLIDAY_DURATION())
        return success

    def cleanup(self, from_service_stop=False):
        if self._holiday_alarm is not None:
            self._holiday_alarm.cancel()
            self._holiday_alarm = None
        services.calendar_service().remove_on_calendar(self.uid)
        super().cleanup(from_service_stop=from_service_stop)
        if self._state == HolidayState.PRE_DAY:
            household = services.household_manager().get(self._active_household_id)
            if household is not None:
                household.holiday_tracker.deactivate_pre_holiday()
        elif self._state == HolidayState.RUNNING:
            household = services.household_manager().get(self._active_household_id)
            if household is not None and not household.holiday_tracker.is_holiday_cancelled(self.holiday_id):
                household.holiday_tracker.deactivate_holiday()
        if self._state in (HolidayState.PRE_DAY, HolidayState.RUNNING, HolidayState.SHUTDOWN):
            lot_decoration_service = services.lot_decoration_service()
            if lot_decoration_service is not None:
                lot_decoration_service.cancel_decoration_requests_for(self)

    def _select_time(self, specific_time=None, time_modifier=TimeSpan.ZERO):
        if specific_time is None:
            result = super()._select_time(time_modifier=time_modifier)
            if not result:
                return result
            drama_scheduler_service = services.drama_scheduler_service()
            for drama_node in drama_scheduler_service.scheduled_nodes_gen():
                if drama_node.drama_node_type != DramaNodeType.HOLIDAY and drama_node.drama_node_type != DramaNodeType.PLAYER_PLANNED:
                    pass
                elif drama_node.day == self.day:
                    return False
            return True
        holiday_start_time = specific_time.time_of_next_day_time(HolidayTuning.MAIN_HOLIDAY_START_TIME)
        now = services.time_service().sim_now
        if holiday_start_time < now:
            return False
        selected_time = holiday_start_time + self.pre_holiday_duration()*-1
        if selected_time < now:
            selected_time = now + TimeSpan.ONE
        self._selected_time = selected_time
        return True

    def _save_custom_data(self, writer):
        if self._holiday_start_time is not None:
            writer.write_uint64(HOLIDAY_START_TIME_TOKEN, self._holiday_start_time.absolute_ticks())
        if self._holiday_end_time is not None:
            writer.write_uint64(HOLIDAY_END_TIME_TOKEN, self._holiday_end_time.absolute_ticks())

    def _load_custom_data(self, reader):
        holiday_start_time_ticks = reader.read_uint64(HOLIDAY_START_TIME_TOKEN, None)
        if holiday_start_time_ticks is not None:
            self._holiday_start_time = DateAndTime(holiday_start_time_ticks)
        holiday_end_time_ticks = reader.read_uint64(HOLIDAY_END_TIME_TOKEN, None)
        if holiday_end_time_ticks is not None:
            self._holiday_end_time = DateAndTime(holiday_end_time_ticks)
        if self._holiday_start_time and (self._holiday_end_time or self._holiday_start_time + HolidayTuning.HOLIDAY_DURATION() < services.time_service().sim_now):
            return False
        return True

    def resume(self):
        now = services.time_service().sim_now
        if now < self._holiday_start_time:
            self._run_pre_holiday(from_load=True)
        else:
            self._run_holiday(from_load=True)

    def _run(self):
        if self.pre_holiday_duration().in_ticks() == 0:
            self._run_holiday()
            self._holiday_start_time = services.time_service().sim_now
        else:
            self._run_pre_holiday()

    def load(self, drama_node_proto, schedule_alarm=True):
        super_success = super().load(drama_node_proto, schedule_alarm=schedule_alarm)
        if not super_success:
            return False
        services.calendar_service().mark_on_calendar(self, advance_notice_time=HolidayTuning.HOLIDAY_DURATION())
        return True
HOLIDAY_ID_TOKEN = 'holiday_id'
class CustomHolidayDramaNode(HolidayDramaNode):
    REMOVE_INSTANCE_TUNABLES = ('holiday',)

    def __init__(self, *args, holiday_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._holiday_id = holiday_id

    @property
    def holiday_id(self):
        return self._holiday_id

    def _save_custom_data(self, writer):
        super()._save_custom_data(writer)
        writer.write_uint64(HOLIDAY_ID_TOKEN, self._holiday_id)

    def _load_custom_data(self, reader):
        self._holiday_id = reader.read_uint64(HOLIDAY_ID_TOKEN, None)
        return super()._load_custom_data(reader)
