from date_and_time import create_time_spanfrom sims4.tuning.tunable import TunableList, TunableReferencefrom situations.situation_curve import SituationCurvefrom situations.situation_guest_list import SituationGuestListfrom venues.scheduling_zone_director import SchedulingZoneDirectorfrom venues.zone_director_venue_proxy import ZoneDirectorVenueProxyimport alarmsimport servicesimport sims4.resourcesimport telemetry_helperlogger = sims4.log.Logger('CareerEventZoneDirector', default_owner='tingyul')TELEMETRY_GROUP_CAREER_ZONE_DIRECTOR = 'CZOD'TELEMETRY_HOOK_ZONE_DIRECTOR_START = 'CZOS'TELEMETRY_HOOK_ZONE_DIRECTOR_END = 'CZOE'TELEMETRY_CAREER_ID = 'cari'TELEMETRY_CAREER_DURATION = 'zdur'career_zone_director_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_CAREER_ZONE_DIRECTOR)
class CareerEventZoneDirector(SchedulingZoneDirector):
    DESIRED_SITUATION_INTERVAL = 15
    DESIRED_SITUATION_LIST_GUID = 1463143823
    BACKGROUND_SITUATION_LIST_GUID = 1781924741
    INSTANCE_TUNABLES = {'background_situations': TunableList(description='\n            A list of background situations.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SITUATION), pack_safe=True)), 'desired_situations': SituationCurve.TunableFactory(description='\n            Situations that are created depending on what time of the day it is.\n            ')}

    def __init__(self, *args, career_event, **kwargs):
        super().__init__(*args, **kwargs)
        self._background_situation_ids = list()
        self._career_event = career_event
        self._situation_alarm_handle = None
        self._situation_ids = []
        self._start_time = None

    def on_startup(self):
        super().on_startup()
        self._situation_alarm_handle = alarms.add_alarm(self, create_time_span(minutes=self.DESIRED_SITUATION_INTERVAL), self._on_desired_situation_request, repeating=True)

    def on_shutdown(self):
        if self._situation_alarm_handle is not None:
            alarms.cancel_alarm(self._situation_alarm_handle)
            self._situation_alarm_handle = None
        super().on_shutdown()

    def on_career_event_stop(self):
        pass

    @property
    def supports_open_street_director(self):
        return False

    def send_startup_telemetry_event(self):
        with telemetry_helper.begin_hook(career_zone_director_telemetry_writer, TELEMETRY_HOOK_ZONE_DIRECTOR_START, sim_info=self._career_event.sim_info) as hook:
            hook.write_guid(TELEMETRY_CAREER_ID, self._career_event.career.guid64)
        self._start_time = services.time_service().sim_now

    def send_shutdown_telemetry_event(self):
        current_zone = services.current_zone()
        if current_zone is not None and current_zone.is_zone_shutting_down:
            return
        duration = (services.time_service().sim_now - self._start_time).in_minutes()
        with telemetry_helper.begin_hook(career_zone_director_telemetry_writer, TELEMETRY_HOOK_ZONE_DIRECTOR_END, sim_info=self._career_event.sim_info) as hook:
            hook.write_guid(TELEMETRY_CAREER_ID, self._career_event.career.guid64)
            hook.write_int(TELEMETRY_CAREER_DURATION, duration)

    def _load_custom_zone_director(self, zone_director_proto, reader):
        for situation_data_proto in zone_director_proto.situations:
            if situation_data_proto.situation_list_guid == self.DESIRED_SITUATION_LIST_GUID:
                self._situation_ids.extend(situation_data_proto.situation_ids)
            elif situation_data_proto.situation_list_guid == self.BACKGROUND_SITUATION_LIST_GUID:
                self._background_situation_ids.extend(situation_data_proto.situation_ids)
        super()._load_custom_zone_director(zone_director_proto, reader)

    def _save_custom_zone_director(self, zone_director_proto, writer):
        situation_data_proto = zone_director_proto.situations.add()
        situation_data_proto.situation_list_guid = self.DESIRED_SITUATION_LIST_GUID
        situation_data_proto.situation_ids.extend(self._prune_stale_situations(self._situation_ids))
        background_data_proto = zone_director_proto.situations.add()
        background_data_proto.situation_list_guid = self.BACKGROUND_SITUATION_LIST_GUID
        background_data_proto.situation_ids.extend(self._prune_stale_situations(self._background_situation_ids))
        super()._save_custom_zone_director(zone_director_proto, writer)

    def _on_desired_situation_request(self, *_, **__):
        situation_manager = services.get_zone_situation_manager()
        self._situation_ids = self._prune_stale_situations(self._situation_ids)
        desired_situation_count = self.desired_situations.get_desired_sim_count()
        while desired_situation_count.lower_bound > len(self._situation_ids):
            (situation_type, params) = self.desired_situations.get_situation_and_params()
            if situation_type is None:
                break
            guest_list = SituationGuestList(invite_only=True, filter_requesting_sim_id=self._career_event.sim_info.sim_id)
            situation_id = situation_manager.create_situation(situation_type, guest_list=guest_list, spawn_sims_during_zone_spin_up=True, creation_source=self.instance_name, **params)
            self._situation_ids.append(situation_id)

    def _decide_whether_to_load_zone_situation_seed(self, seed):
        if not super()._decide_whether_to_load_zone_situation_seed(seed):
            return False
        elif seed.situation_id == self._career_event.get_event_situation_id() or seed.situation_id in self._situation_ids or seed.situation_id in self._background_situation_ids:
            return True
        return False

    def _decide_whether_to_load_open_street_situation_seed(self, seed):
        return False

    def _request_background_situations(self):
        situation_manager = services.get_zone_situation_manager()
        existing = [situation_manager.get(uid) for uid in self._background_situation_ids if uid in situation_manager]
        existing.sort(key=lambda s: s.guid64)
        requested_types = list(self.background_situations)
        requested_types.sort(key=lambda s: s.guid64)
        self._background_situation_ids.clear()
        for requested_type in reversed(requested_types):
            while existing and existing[-1].guid64 > requested_type.guid64:
                existing.pop()
            if existing and existing[-1].guid64 == requested_type.guid64:
                situation = existing.pop()
                self._background_situation_ids.append(situation.id)
            else:
                guest_list = SituationGuestList(invite_only=True, filter_requesting_sim_id=self._career_event.sim_info.sim_id)
                situation_id = situation_manager.create_situation(requested_type, guest_list=guest_list, spawn_sims_during_zone_spin_up=True, user_facing=False, creation_source=self.instance_name)
                self._background_situation_ids.append(situation_id)

    def create_situations_during_zone_spin_up(self):
        self._on_desired_situation_request()
        self._request_background_situations()
        return super().create_situations_during_zone_spin_up()

class CareerEventZoneDirectorProxy(CareerEventZoneDirector, ZoneDirectorVenueProxy):
    pass
