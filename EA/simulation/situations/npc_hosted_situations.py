import argparsefrom clock import interval_in_sim_minutes, ClockSpeedModefrom distributor.shared_messages import build_icon_info_msg, IconInfoDatafrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableTuple, TunableReference, TunableSimMinute, OptionalTunablefrom tunable_time import TunableTimeOfDayfrom ui.ui_dialog import UiDialogOkCancel, UiDialogResponse, ButtonTypefrom ui.ui_dialog_picker import UiSimPickerimport alarmsimport build_buyimport servicesimport sims4.resourceslogger = sims4.log.Logger('NPCHostedSituations', default_owner='jjacobson')TELEMETRY_GROUP_SITUATIONS = 'SITU'TELEMETRY_HOOK_SITUATION_INVITED = 'INVI'TELEMETRY_HOOK_SITUATION_ACCEPTED = 'ACCE'TELEMETRY_HOOK_SITUATION_REJECTED = 'REJE'TELEMETRY_SITUATION_TYPE_ID = 'type'TELEMETRY_GUEST_COUNT = 'gcou'TELEMETRY_CHOSEN_ZONE = 'czon'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_SITUATIONS)
class NPCHostedSituationDialog(UiDialogOkCancel):
    FACTORY_TUNABLES = {'bring_other_sims': OptionalTunable(description='\n            If enabled then the tuned dialog will appear \n            ', tunable=TunableTuple(picker_dialog=UiSimPicker.TunableFactory(description='\n                    The picker dialog to show when selecting Sims to invite to\n                    the event.\n                    '), travel_with_filter=TunableReference(description='\n                    The sim filter that will be used to select sims to bring to\n                    the situation as well.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER)), text=TunableLocalizedStringFactory(description='\n                    The "Yes, with friends" text.\n                    '), situation_job=TunableReference(description='\n                    The situation job that sims who are picked from this picker\n                    will be put into.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)))), 'zone_title': TunableLocalizedStringFactory(description='\n            The localized string to use for displaying the zone data.\n            Token 0 is the venue type of the zone; Token 1 is the lot name.\n            ')}
    BRING_OTHER_SIMS_RESPONSE_ID = 1

    @property
    def responses(self):
        if self.bring_other_sims is not None:
            return (UiDialogResponse(dialog_response_id=ButtonType.DIALOG_RESPONSE_OK, text=self.text_ok, ui_request=UiDialogResponse.UiDialogUiRequest.NO_REQUEST), UiDialogResponse(dialog_response_id=NPCHostedSituationDialog.BRING_OTHER_SIMS_RESPONSE_ID, text=self.bring_other_sims.text, ui_request=UiDialogResponse.UiDialogUiRequest.NO_REQUEST), UiDialogResponse(dialog_response_id=ButtonType.DIALOG_RESPONSE_CANCEL, text=self.text_cancel, ui_request=UiDialogResponse.UiDialogUiRequest.NO_REQUEST))
        return super().responses

    def build_msg(self, zone_id=None, **kwargs):
        msg = super().build_msg(**kwargs)
        if zone_id is None:
            return msg
        persistence_service = services.get_persistence_service()
        zone_data = persistence_service.get_zone_proto_buff(zone_id)
        if zone_data is None:
            return msg
        venue_type_id = build_buy.get_current_venue(zone_id)
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        venue_instance = venue_manager.get(venue_type_id)
        if venue_instance is None:
            return msg
        msg.lot_title = self.zone_title(venue_instance.display_name, zone_data.name)
        build_icon_info_msg(IconInfoData(icon_resource=venue_instance.venue_icon), venue_instance.display_name, msg.venue_icon)
        return msg

class NPCHostedSituationService(Service):
    WELCOME_WAGON_TUNING = TunableTuple(description='\n        Tuning dedicated to started the welcome wagon.\n        ', situation=TunableReference(description='\n            The welcome wagon situation.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION)), minimum_time_to_start_situation=TunableSimMinute(description='\n            The minimum amount of time since the service started that the\n            welcome wagon will begin.\n            ', default=60, minimum=0), available_time_of_day=TunableTuple(description='\n            The start and end times that determine the time that the welcome\n            wagon can begin.  This has nothing to do with the end time of the\n            situation.  The duration of the situation can last beyond the times\n            tuned here.\n            ', start_time=TunableTimeOfDay(description='\n                The start time that the welcome wagon can begin.\n                '), end_time=TunableTimeOfDay(description='\n                The end time that the welcome wagon can begin.\n                ')))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._welcome_wagon_alarm = None
        self._suspended = False

    def _start_welcome_wagon(self, _):
        situation_manager = services.get_zone_situation_manager()
        if situation_manager.is_user_facing_situation_running():
            self._schedule_welcome_wagon()
            return
        active_household = services.active_household()
        for sim_info in active_household.can_live_alone_info_gen():
            if sim_info.is_instanced():
                break
        self._schedule_welcome_wagon()
        return
        narrative_service = services.narrative_service()
        welcome_wagon_situation = narrative_service.get_possible_replacement_situation(NPCHostedSituationService.WELCOME_WAGON_TUNING.situation)
        guest_list = welcome_wagon_situation.get_predefined_guest_list()
        if guest_list is None:
            active_household.needs_welcome_wagon = False
            return
        game_clock_services = services.game_clock_service()
        if game_clock_services.clock_speed == ClockSpeedMode.SUPER_SPEED3:
            game_clock_services.set_clock_speed(ClockSpeedMode.NORMAL)
        situation_manager.create_situation(welcome_wagon_situation, guest_list=guest_list, user_facing=False, scoring_enabled=False)

    def on_all_households_and_sim_infos_loaded(self, client):
        self._schedule_welcome_wagon()

    def _schedule_welcome_wagon(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--no_welcome_wagon', default=False, action='store_true')
        (args, unused_args) = parser.parse_known_args()
        if args.no_welcome_wagon:
            return
        active_household = services.active_household()
        if not active_household.needs_welcome_wagon:
            return
        if services.current_zone_id() != active_household.home_zone_id:
            return
        minimum_time = interval_in_sim_minutes(NPCHostedSituationService.WELCOME_WAGON_TUNING.minimum_time_to_start_situation)
        now = services.time_service().sim_now
        possible_time = now + minimum_time
        if possible_time.time_between_day_times(NPCHostedSituationService.WELCOME_WAGON_TUNING.available_time_of_day.start_time, NPCHostedSituationService.WELCOME_WAGON_TUNING.available_time_of_day.end_time):
            time_till_welcome_wagon = minimum_time
        else:
            time_till_welcome_wagon = now.time_till_next_day_time(NPCHostedSituationService.WELCOME_WAGON_TUNING.available_time_of_day.start_time)
        self._welcome_wagon_alarm = alarms.add_alarm(self, time_till_welcome_wagon, self._start_welcome_wagon)

    def suspend_welcome_wagon(self):
        self._suspended = True
        self._cancel_alarm()

    def resume_welcome_wagon(self):
        self._suspended = False
        self._schedule_welcome_wagon()

    def _cancel_alarm(self):
        if self._welcome_wagon_alarm is not None:
            alarms.cancel_alarm(self._welcome_wagon_alarm)

    def stop(self):
        super().stop()
        self._cancel_alarm
