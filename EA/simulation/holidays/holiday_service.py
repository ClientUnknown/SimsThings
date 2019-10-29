from _collections import defaultdictfrom protocolbuffers import GameplaySaveData_pb2from date_and_time import DAYS_PER_WEEK, create_time_span, DATE_AND_TIME_ZEROfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.resolver import DataResolverfrom holidays.custom_holiday import CustomHolidayfrom holidays.holiday_ops import SendHolidayInfofrom id_generator import generate_object_idfrom seasons.seasons_enums import SeasonLength, SeasonTypefrom seasons.seasons_tuning import SeasonsTuningfrom sims4.common import Packfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunablePackSafeReferencefrom sims4.utils import classpropertyimport persistence_error_typesimport servicesimport sims4.loglogger = sims4.log.Logger('Holiday', default_owner='jjacobson')
class YearOfHolidays:

    def __init__(self, season_length):
        self._season_length = season_length
        self._holidays = defaultdict(dict)

    def holidays_to_schedule_gen(self):
        for (season, season_data) in self._holidays.items():
            for (day, holiday_id) in season_data.items():
                yield (season, day, holiday_id)

    def get_holiday_data(self, holiday_id_for_data):
        for (season, day, holiday_id) in self.holidays_to_schedule_gen():
            if holiday_id == holiday_id_for_data:
                return (season, day)
        return (None, None)

    def add_holiday(self, season, day, holiday_id):
        season_length = int(SeasonsTuning.SEASON_LENGTH_OPTIONS[self._season_length]().in_days())
        if day > season_length:
            day_in_week = day % DAYS_PER_WEEK
            day = day_in_week + season_length - DAYS_PER_WEEK
        if day in self._holidays[season]:
            return
        self._holidays[season][day] = holiday_id

    def remove_holiday(self, holiday_id_to_remove):
        for holidays in tuple(self._holidays.values()):
            for (day, holiday_id) in tuple(holidays.items()):
                if holiday_id == holiday_id_to_remove:
                    del holidays[day]
                    return

    def save(self, msg):
        msg.season_length = self._season_length
        for (season, season_map) in self._holidays.items():
            for (day, holiday_id) in season_map.items():
                with ProtocolBufferRollback(msg.holidays) as holiday_time_msg:
                    holiday_time_msg.holiday_id = holiday_id
                    holiday_time_msg.day = day
                    holiday_time_msg.season = season

    def load(self, msg):
        for holiday_time_data in msg.holidays:
            season = SeasonType(holiday_time_data.season)
            self._holidays[season][holiday_time_data.day] = holiday_time_data.holiday_id

class HolidayService(Service):
    CUSTOM_HOLIDAY_DRAMA_NODE = TunablePackSafeReference(description='\n        The drama node to construct to run a custom holiday.\n        ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE))

    def __init__(self):
        self._holidays = {}
        self._holiday_times = {}

    @classproperty
    def required_packs(cls):
        return (Pack.EP05,)

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_HOLIDAY_SERVICE

    def _schedule_holiday(self, holiday_id):
        resolver = DataResolver(None)
        season_service = services.season_service()
        current_season_length = season_service.season_length_option
        season_data = {season_type: season_content for (season_type, season_content) in season_service.get_four_seasons()}
        drama_scheduler = services.drama_scheduler_service()
        (season, day) = self._holiday_times[current_season_length].get_holiday_data(holiday_id)
        if season is None:
            logger.error('Trying to schedule holiday of id {} which is not actually scheduled to run at any time.')
            return
        holiday_start_time = season_data[season].start_time + create_time_span(days=day)
        drama_scheduler.schedule_node(HolidayService.CUSTOM_HOLIDAY_DRAMA_NODE, resolver, specific_time=holiday_start_time, holiday_id=holiday_id)

    def _schedule_all_holidays(self, holiday_ids_to_ignore=()):
        resolver = DataResolver(None)
        season_service = services.season_service()
        current_season_length = season_service.season_length_option
        season_data = {season_type: season_content for (season_type, season_content) in season_service.get_four_seasons()}
        drama_scheduler = services.drama_scheduler_service()
        for (season, day, holiday_id) in self._holiday_times[current_season_length].holidays_to_schedule_gen():
            if holiday_id in holiday_ids_to_ignore:
                pass
            else:
                holiday_start_time = season_data[season].start_time + create_time_span(days=day)
                drama_scheduler.schedule_node(HolidayService.CUSTOM_HOLIDAY_DRAMA_NODE, resolver, specific_time=holiday_start_time, holiday_id=holiday_id)

    def on_season_content_changed(self):
        drama_scheduler = services.drama_scheduler_service()
        drama_scheduler.cancel_scheduled_nodes_with_types((HolidayService.CUSTOM_HOLIDAY_DRAMA_NODE,))
        for drama_node in tuple(drama_scheduler.get_running_nodes_by_class(HolidayService.CUSTOM_HOLIDAY_DRAMA_NODE)):
            if drama_node.is_running:
                pass
            else:
                drama_scheduler.complete_node(drama_node.uid)
        self._schedule_all_holidays()
        holidays = {}
        for drama_node in tuple(drama_scheduler.scheduled_nodes_gen()):
            if drama_node.drama_node_type != DramaNodeType.HOLIDAY:
                pass
            else:
                day = drama_node.day
                existing_node = holidays.get(day)
                if existing_node is None:
                    holidays[day] = drama_node
                elif type(existing_node) is HolidayService.CUSTOM_HOLIDAY_DRAMA_NODE:
                    drama_scheduler.cancel_scheduled_node(drama_node.uid)
                else:
                    drama_scheduler.cancel_scheduled_node(existing_node.uid)
                    holidays[day] = drama_node

    def on_all_households_and_sim_infos_loaded(self, client):
        holiday_ids_to_ignore = {drama_node.holiday_id for drama_node in services.drama_scheduler_service().all_nodes_gen() if type(drama_node) is HolidayService.CUSTOM_HOLIDAY_DRAMA_NODE}
        if not self._holiday_times:
            for season_length in SeasonLength:
                self._holiday_times[season_length] = YearOfHolidays(season_length)
            for (season_type, season_content) in services.season_service().get_four_seasons():
                for (season_length, holiday, day_of_season) in season_content.get_all_holiday_data():
                    self._holiday_times[season_length].add_holiday(season_type, day_of_season, holiday.guid64)
        self._schedule_all_holidays(holiday_ids_to_ignore)

    def add_a_holiday(self, holiday_proto, season, day):
        holiday_id = generate_object_id()
        new_holiday = CustomHoliday(holiday_id, None)
        self._holidays[holiday_id] = new_holiday
        new_holiday.load_holiday(holiday_proto)
        for holiday_time in self._holiday_times.values():
            holiday_time.add_holiday(season, day, holiday_id)
        self._schedule_holiday(holiday_id)

    def remove_a_holiday(self, holiday_id):
        drama_scheduler_service = services.drama_scheduler_service()
        for drama_node in tuple(drama_scheduler_service.scheduled_nodes_gen()):
            if drama_node.drama_node_type != DramaNodeType.HOLIDAY:
                pass
            elif drama_node.holiday_id != holiday_id:
                pass
            else:
                drama_scheduler_service.cancel_scheduled_node(drama_node.uid)
        for drama_node in tuple(drama_scheduler_service.active_nodes_gen()):
            if drama_node.drama_node_type != DramaNodeType.HOLIDAY:
                pass
            elif drama_node.holiday_id != holiday_id:
                pass
            else:
                drama_scheduler_service.complete_node(drama_node.uid)
        for holiday_year_data in self._holiday_times.values():
            holiday_year_data.remove_holiday(holiday_id)
        if holiday_id in self._holidays:
            del self._holidays[holiday_id]

    def is_valid_holiday_id(self, holiday_id):
        return self._get_holiday_data(holiday_id) is not None

    def _get_holiday_data(self, holiday_id):
        holiday_data = self._holidays.get(holiday_id)
        if holiday_data is None:
            holiday_data = services.get_instance_manager(sims4.resources.Types.HOLIDAY_DEFINITION).get(holiday_id)
        return holiday_data

    def get_holiday_traditions(self, holiday_id):
        return self._get_holiday_data(holiday_id).traditions

    def get_holiday_display_name(self, holiday_id):
        return self._get_holiday_data(holiday_id).display_name

    def get_holiday_display_icon(self, holiday_id):
        return self._get_holiday_data(holiday_id).display_icon

    def get_holiday_time_off_work(self, holiday_id):
        return self._get_holiday_data(holiday_id).time_off_work

    def get_holiday_time_off_school(self, holiday_id):
        return self._get_holiday_data(holiday_id).time_off_school

    def get_holiday_calendar_alert_notification(self, holiday_id):
        return self._get_holiday_data(holiday_id).calendar_alert_description

    def get_decoration_preset(self, holiday_id):
        return self._get_holiday_data(holiday_id).decoration_preset

    def get_holiday_audio_sting(self, holiday_id):
        return self._get_holiday_data(holiday_id).audio_sting

    def can_holiday_be_modified(self, holiday_id):
        return self._get_holiday_data(holiday_id).can_be_modified

    def send_holiday_info_message(self, holiday_id):
        holiday_data = self._get_holiday_data(holiday_id)
        send_holiday_info = SendHolidayInfo(holiday_id, holiday_data.display_name, holiday_data.display_icon, holiday_data.time_off_work, holiday_data.time_off_school, holiday_data.traditions, holiday_data.can_be_modified, holiday_data.decoration_preset)
        distributor = Distributor.instance()
        distributor.add_op_with_no_owner(send_holiday_info)

    def save(self, save_slot_data=None, **kwargs):
        holiday_service_proto = GameplaySaveData_pb2.PersistableHolidayService()
        for custom_holiday in self._holidays.values():
            with ProtocolBufferRollback(holiday_service_proto.holidays) as holiday_data:
                custom_holiday.save_holiday(holiday_data)
        for calendar in self._holiday_times.values():
            with ProtocolBufferRollback(holiday_service_proto.calendars) as calendar_msg:
                calendar.save(calendar_msg)
        save_slot_data.gameplay_data.holiday_service = holiday_service_proto

    def load(self, zone_data=None):
        save_slot_data = services.get_persistence_service().get_save_slot_proto_buff()
        msg = save_slot_data.gameplay_data.holiday_service
        holiday_manager = services.get_instance_manager(sims4.resources.Types.HOLIDAY_DEFINITION)
        for custom_holiday_msg in msg.holidays:
            holiday_type = holiday_manager.get(custom_holiday_msg.holiday_type)
            custom_holiday = CustomHoliday(custom_holiday_msg.holiday_type, holiday_type)
            custom_holiday.load_holiday(custom_holiday_msg)
            self._holidays[custom_holiday.holiday_id] = custom_holiday
        for holiday_calendar in msg.calendars:
            calendar_length = SeasonLength(holiday_calendar.season_length)
            self._holiday_times[calendar_length] = YearOfHolidays(calendar_length)
            self._holiday_times[calendar_length].load(holiday_calendar)

    def modify_holiday(self, holiday_proto):
        holiday_id = holiday_proto.holiday_type
        current_traditions = set(self.get_holiday_traditions(holiday_id))
        previous_preset = self.get_decoration_preset(holiday_id)
        if holiday_id not in self._holidays:
            holiday_manager = services.get_instance_manager(sims4.resources.Types.HOLIDAY_DEFINITION)
            holiday_type = holiday_manager.get(holiday_id)
            self._holidays[holiday_id] = CustomHoliday(holiday_id, holiday_type)
        self._holidays[holiday_id].load_holiday(holiday_proto)
        ordered_traditions = self.get_holiday_traditions(holiday_id)
        new_traditions = set(ordered_traditions)
        added_traditions = new_traditions.difference(current_traditions)
        removed_traditions = current_traditions.difference(new_traditions)
        active_household = services.active_household()
        if active_household is None:
            return
        active_household.holiday_tracker.on_holiday_modified(holiday_id, added_traditions, removed_traditions, ordered_traditions, previous_preset is not self.get_decoration_preset(holiday_id))
