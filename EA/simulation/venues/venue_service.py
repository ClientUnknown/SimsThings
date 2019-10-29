import randomfrom protocolbuffers import GameplaySaveData_pb2 as gameplay_serializationfrom build_buy import get_current_venuefrom open_street_director.open_street_director_request import OpenStreetDirectorRequestFactoryfrom sims4.callback_utils import CallableListfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableSimMinutefrom sims4.utils import classpropertyfrom situations.service_npcs.modify_lot_items_tuning import ModifyAllLotItemsfrom venues.venue_constants import ZoneDirectorRequestTypefrom world.region import get_region_instance_from_zone_idimport alarmsimport build_buyimport clockimport persistence_error_typesimport servicesimport sims4.logimport sims4.resourcesimport telemetry_helperimport zone_directorTELEMETRY_GROUP_VENUE = 'VENU'TELEMETRY_HOOK_TIMESPENT = 'TMSP'TELEMETRY_FIELD_VENUE = 'venu'TELEMETRY_FIELD_VENUE_TIMESPENT = 'vtsp'venue_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_VENUE)try:
    import _zone
except ImportError:

    class _zone:
        pass
logger = sims4.log.Logger('Venue', default_owner='manus')
class VenueService(Service):
    SPECIAL_EVENT_SCHEDULE_DELAY = TunableSimMinute(description='\n        Number of real time seconds to wait after the loading screen before scheduling\n        special events.\n        ', default=10.0)
    VENUE_CLEANUP_ACTIONS = ModifyAllLotItems.TunableFactory()
    ELAPSED_TIME_SINCE_LAST_VISIT_FOR_CLEANUP = TunableSimMinute(description='\n        If more than this amount of sim minutes has elapsed since the lot was\n        last visited, the auto cleanup will happen.\n        ', default=720, minimum=0)

    def __init__(self):
        self._persisted_background_event_id = None
        self._persisted_special_event_id = None
        self._special_event_start_alarm = None
        self._venue = None
        self._zone_director = None
        self._requested_zone_directors = []
        self._prior_zone_director_proto = None
        self._open_street_director_requests = []
        self._prior_open_street_director_proto = None
        self.build_buy_edit_mode = False
        self.on_venue_type_changed = CallableList()
        self._venue_start_time = None

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_VENUE_SERVICE

    @property
    def venue(self):
        return self._venue

    def venue_is_type(self, required_type):
        if type(self.venue) is required_type:
            return True
        return False

    def _set_venue(self, venue_type):
        if venue_type is None:
            logger.error('Zone {} has invalid venue type.', services.current_zone().id)
            return False
        if type(self._venue) is venue_type:
            return False
        if self._venue is not None:
            self._venue.shut_down()
            if self._special_event_start_alarm is not None:
                alarms.cancel_alarm(self._special_event_start_alarm)
                self._special_event_start_alarm = None
        self._send_venue_time_spent_telemetry()
        new_venue = venue_type()
        self._venue = new_venue
        self._venue_start_time = services.time_service().sim_now
        return True

    def _send_venue_time_spent_telemetry(self):
        if self._venue is None or self._venue_start_time is None:
            return
        time_spent_mins = (services.time_service().sim_now - self._venue_start_time).in_minutes()
        if time_spent_mins:
            with telemetry_helper.begin_hook(venue_telemetry_writer, TELEMETRY_HOOK_TIMESPENT) as hook:
                hook.write_guid(TELEMETRY_FIELD_VENUE, self._venue.guid64)
                hook.write_int(TELEMETRY_FIELD_VENUE_TIMESPENT, time_spent_mins)

    def get_venue_tuning(self, zone_id):
        venue_tuning = None
        venue_type = get_current_venue(zone_id)
        if venue_type is not None:
            venue_tuning = services.venue_manager().get(venue_type)
        return venue_tuning

    def change_venue_type_at_runtime(self, venue_type):
        if self.build_buy_edit_mode:
            return
        type_changed = self._set_venue(venue_type)
        if self._venue is not None:
            zone_director = self._venue.create_zone_director_instance()
            self.change_zone_director(zone_director, run_cleanup=True)
            self.create_situations_during_zone_spin_up()
            if self._zone_director.should_create_venue_background_situation:
                self._venue.schedule_background_events(schedule_immediate=True)
                self._venue.schedule_special_events(schedule_immediate=False)
                self._venue.schedule_club_gatherings(schedule_immediate=True)
            self.on_venue_type_changed()
            for sim in services.sim_info_manager().instanced_sims_on_active_lot_gen():
                sim.sim_info.add_venue_buffs()

    def make_venue_type_zone_director_request(self):
        if self._venue is None:
            raise RuntimeError('Venue type must be determined before requesting a zone director.')
        zone_director = self._venue.create_zone_director_instance()
        self.request_zone_director(zone_director, ZoneDirectorRequestType.AMBIENT_VENUE)

    def setup_lot_premade_status(self):
        services.active_lot().flag_as_premade(True)

    def _select_zone_director(self):
        if self._requested_zone_directors is None:
            raise RuntimeError('Cannot select a zone director twice')
        if not self._requested_zone_directors:
            raise RuntimeError('At least one zone director must be requested')
        requested_zone_directors = self._requested_zone_directors
        self._requested_zone_directors = None
        requested_zone_directors.sort()
        (_, zone_director, preserve_state) = requested_zone_directors[0]
        self._set_zone_director(zone_director, True)
        if self._prior_zone_director_proto:
            self._zone_director.load(self._prior_zone_director_proto, preserve_state=preserve_state)
            self._prior_zone_director_proto = None
        self._setup_open_street_director()

    def _setup_open_street_director(self):
        street = services.current_street()
        if street is not None and street.open_street_director is not None:
            self._open_street_director_requests.append(OpenStreetDirectorRequestFactory(street.open_street_director, priority=street.open_street_director.priority))
        self._zone_director.setup_open_street_director_manager(self._open_street_director_requests, self._prior_open_street_director_proto)
        self._open_street_director_requests = None
        self._prior_open_street_director_proto = None

    @property
    def has_zone_director(self):
        return self._zone_director is not None

    def get_zone_director(self):
        return self._zone_director

    def request_zone_director(self, zone_director, request_type, preserve_state=True):
        if self._requested_zone_directors is None:
            raise RuntimeError('Cannot request a new zone director after one has been selected.')
        if zone_director is None:
            raise ValueError('Cannot request a None zone director.')
        for (prior_request_type, prior_zone_director, _) in self._requested_zone_directors:
            if prior_request_type == request_type:
                raise ValueError('Multiple requests for zone directors with the same request type {}.  Original: {} New: {}'.format(request_type, prior_zone_director, zone_director))
        self._requested_zone_directors.append((request_type, zone_director, preserve_state))

    def change_zone_director(self, zone_director, run_cleanup):
        if self._zone_director is None:
            raise RuntimeError('Cannot request a new zone director before one has been selected.')
        if self._zone_director is zone_director:
            raise ValueError('Attempting to change zone director to the same instance')
        self._set_zone_director(zone_director, run_cleanup)

    def _set_zone_director(self, zone_director, run_cleanup):
        if self._zone_director is not None:
            if run_cleanup:
                self._zone_director.process_cleanup_actions()
            else:
                for cleanup_action in self._zone_director._cleanup_actions:
                    zone_director.add_cleanup_action(cleanup_action)
            if zone_director is not None:
                zone_director.transfer_open_street_director(self._zone_director)
            self._zone_director.on_shutdown()
        self._zone_director = zone_director
        if self._zone_director is not None:
            self._zone_director.on_startup()

    def request_open_street_director(self, open_street_director_request):
        if services.current_zone().is_zone_running:
            self._zone_director.request_new_open_street_director(open_street_director_request)
            return
        self._open_street_director_requests.append(open_street_director_request)

    def determine_which_situations_to_load(self):
        self._zone_director.determine_which_situations_to_load()

    def on_client_connect(self, client):
        zone = services.current_zone()
        venue_type = get_current_venue(zone.id)
        logger.assert_raise(venue_type is not None, 'Venue Type is None in on_client_connect for zone:{}', zone, owner='sscholl')
        venue_tuning = self.get_venue_tuning(zone.id)
        if venue_tuning is not None:
            self._set_venue(venue_tuning)

    def on_cleanup_zone_objects(self, client):
        zone = services.current_zone()
        if client.household_id != zone.lot.owner_household_id:
            time_elapsed = zone.time_elapsed_since_last_save()
            if time_elapsed.in_minutes() > self.ELAPSED_TIME_SINCE_LAST_VISIT_FOR_CLEANUP:
                cleanup = VenueService.VENUE_CLEANUP_ACTIONS()
                cleanup.modify_objects()

    def stop(self):
        self._send_venue_time_spent_telemetry()
        if self.build_buy_edit_mode:
            return
        self._set_zone_director(None, True)

    def create_situations_during_zone_spin_up(self):
        self._zone_director.create_situations_during_zone_spin_up()
        self.initialize_venue_schedules()

    def handle_active_lot_changing_edge_cases(self):
        self._zone_director.handle_active_lot_changing_edge_cases()

    def initialize_venue_schedules(self):
        if not self._zone_director.should_create_venue_background_situation:
            return
        if self._venue is not None:
            self._venue.set_active_event_ids(self._persisted_background_event_id, self._persisted_special_event_id)
            situation_manager = services.current_zone().situation_manager
            schedule_immediate = self._persisted_background_event_id is None or self._persisted_background_event_id not in situation_manager
            self._venue.schedule_background_events(schedule_immediate=schedule_immediate)
            self._venue.schedule_club_gatherings(schedule_immediate=schedule_immediate)

    def process_traveled_and_persisted_and_resident_sims_during_zone_spin_up(self, traveled_sim_infos, zone_saved_sim_infos, plex_group_saved_sim_infos, open_street_saved_sim_infos, injected_into_zone_sim_infos):
        self._zone_director.process_traveled_and_persisted_and_resident_sims(traveled_sim_infos, zone_saved_sim_infos, plex_group_saved_sim_infos, open_street_saved_sim_infos, injected_into_zone_sim_infos)

    def setup_special_event_alarm(self):
        special_event_time_span = clock.interval_in_sim_minutes(self.SPECIAL_EVENT_SCHEDULE_DELAY)
        self._special_event_start_alarm = alarms.add_alarm(self, special_event_time_span, self._schedule_venue_special_events, repeating=False)

    def _schedule_venue_special_events(self, alarm_handle):
        if self._venue is not None:
            self._venue.schedule_special_events(schedule_immediate=True)

    def is_zone_valid_for_venue_type(self, zone_id, venue_types, compatible_region=None):
        if not zone_id:
            return False
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        venue_type = venue_manager.get(build_buy.get_current_venue(zone_id))
        if venue_type not in venue_types:
            return False
        elif compatible_region is not None:
            venue_region = get_region_instance_from_zone_id(zone_id)
            if venue_region is None or not compatible_region.is_region_compatible(venue_region):
                return False
        return True

    def has_zone_for_venue_type(self, venue_types, compatible_region=None):
        for _ in self.get_zones_for_venue_type_gen(*venue_types, compatible_region=compatible_region):
            return True
        return False

    def get_zones_for_venue_type_gen(self, *venue_types, compatible_region=None):
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        for neighborhood_proto in services.get_persistence_service().get_neighborhoods_proto_buf_gen():
            for lot_owner_info in neighborhood_proto.lots:
                zone_id = lot_owner_info.zone_instance_id
                if self.is_zone_valid_for_venue_type(zone_id, venue_types, compatible_region=compatible_region):
                    yield zone_id

    def get_zone_and_venue_type_for_venue_types(self, venue_types, compatible_region=None):
        possible_zones = []
        for venue_type in venue_types:
            for zone in self.get_zones_for_venue_type_gen(venue_type, compatible_region=compatible_region):
                possible_zones.append((zone, venue_type))
        if possible_zones:
            return random.choice(possible_zones)
        return (None, None)

    def save(self, zone_data=None, open_street_data=None, **kwargs):
        if self._venue is not None:
            venue_data = zone_data.gameplay_zone_data.venue_data
            if self._venue.active_background_event_id is not None:
                venue_data.background_situation_id = self._venue.active_background_event_id
            if self._venue.active_special_event_id is not None:
                venue_data.special_event_id = self._venue.active_special_event_id
            if self._zone_director is not None:
                zone_director_data = gameplay_serialization.ZoneDirectorData()
                self._zone_director.save(zone_director_data, open_street_data)
                venue_data.zone_director = zone_director_data
            else:
                if self._prior_open_street_director_proto is not None:
                    open_street_data.open_street_director = self._prior_open_street_director_proto
                if self._prior_zone_director_proto is not None:
                    venue_data.zone_director = self._prior_zone_director_proto

    def load(self, zone_data=None, **kwargs):
        if zone_data is not None and zone_data.HasField('gameplay_zone_data') and zone_data.gameplay_zone_data.HasField('venue_data'):
            venue_data = zone_data.gameplay_zone_data.venue_data
            if venue_data.HasField('background_situation_id'):
                self._persisted_background_event_id = venue_data.background_situation_id
            if venue_data.HasField('special_event_id'):
                self._persisted_special_event_id = venue_data.special_event_id
            if venue_data.HasField('zone_director'):
                self._prior_zone_director_proto = gameplay_serialization.ZoneDirectorData()
                self._prior_zone_director_proto.CopyFrom(venue_data.zone_director)
        open_street_id = services.current_zone().open_street_id
        open_street_data = services.get_persistence_service().get_open_street_proto_buff(open_street_id)
        if open_street_data is not None and open_street_data.HasField('open_street_director'):
            self._prior_open_street_director_proto = gameplay_serialization.OpenStreetDirectorData()
            self._prior_open_street_director_proto.CopyFrom(open_street_data.open_street_director)

    def on_loading_screen_animation_finished(self):
        if self._zone_director is not None:
            self._zone_director.on_loading_screen_animation_finished()
