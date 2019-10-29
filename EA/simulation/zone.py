import collectionsimport gcimport mathimport randomimport weakreffrom protocolbuffers import FileSerialization_pb2 as serializationfrom protocolbuffers.Consts_pb2 import MGR_OBJECT, MGR_SITUATION, MGR_PARTY, MGR_SOCIAL_GROUP, MGR_TRAVEL_GROUPfrom animation import get_throwaway_animation_contextfrom animation.animation_drift_monitor import animation_drift_monitor_on_zone_shutdownfrom careers.career_service import CareerServicefrom clock import ClockSpeedModefrom crafting.photography_service import PhotographyServicefrom date_and_time import DateAndTime, TimeSpan, MILLISECONDS_PER_SECONDfrom event_testing import test_eventsfrom interactions.constraints import create_constraint_set, Constraintfrom objects.object_enums import ResetReasonfrom sims.rebate_manager import RebateCategoryEnumfrom sims.royalty_tracker import RoyaltyAlarmManagerfrom sims4 import protocol_buffer_utils, reloadfrom sims4.callback_utils import CallableList, CallableListPreventingRecursionfrom sims4.tuning.tunable import TunableEnumWithFilterfrom situations.npc_hosted_situations import NPCHostedSituationServicefrom world import region, streetfrom world.lot import Lotfrom world.region import Regionfrom world.spawn_point import SpawnPointOption, SpawnPointfrom world.spawn_point_enums import SpawnPointRequestReasonfrom world.travel_group_manager import TravelGroupManagerfrom world.world_spawn_point import WorldSpawnPointimport adaptive_clock_speedimport alarmsimport areaserverimport cachesimport cameraimport clockimport distributor.systemimport game_servicesimport gsi_handlers.routing_handlersimport indexed_managerimport interactions.constraintsimport interactions.utilsimport persistence_moduleimport placementimport routingimport servicesimport sims4.logimport sims4.randomimport tagimport telemetry_helperimport zone_typeswith sims4.reload.protected(globals()):
    gc_count_log = NoneTELEMETRY_GROUP_GCSTATS = 'GCST'TELEMETRY_HOOK_ZONESHUTDOWN = 'ZNSH'TELEMETRY_GCCOUNT = 'gcct'TELEMETRY_ZONETIME = 'ztim'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_GCSTATS)logger = sims4.log.Logger('Zone')TickMetric = collections.namedtuple('TickMetric', ['absolute_ticks', 'sim_now', 'clock_speed', 'clock_speed_multiplier', 'game_time', 'multiplier_type'])
def set_debug_lag(duration):
    pass

class Zone:
    RESTRICTED_AUTONOMY_AREA_TAG = TunableEnumWithFilter(description='\n        The tag that defines the restricted autonomy area.\n        ', tunable_type=tag.Tag, default=tag.Tag.INVALID, invalid_enums=(tag.Tag.INVALID,), filter_prefixes=['func'])
    FESTIVAL_AUTONOMY_AREA_POINT_COUNT = 4
    force_route_instantly = False

    def __init__(self, zone_id, save_slot_data_id):
        self.id = zone_id
        self.neighborhood_id = 0
        self.open_street_id = 0
        self.lot = Lot(zone_id)
        self.region = None
        self.street = None
        self.entitlement_unlock_handlers = {}
        self.sim_quadtree = None
        self._world_spawn_point_locators = []
        self._world_spawn_points = {}
        self._dynamic_spawn_points = {}
        self._spawn_points_changed_callbacks = CallableList()
        self._zone_state = zone_types.ZoneState.ZONE_INIT
        self._zone_state_callbacks = {}
        self.all_transition_controllers = weakref.WeakSet()
        self.navmesh_change_callbacks = CallableListPreventingRecursion()
        self.wall_contour_update_callbacks = CallableListPreventingRecursion()
        self.foundation_and_level_height_update_callbacks = CallableListPreventingRecursion()
        self.navmesh_id = None
        self.is_in_build_buy = False
        self.objects_to_fixup_post_bb = None
        self._save_slot_data_id = save_slot_data_id
        self._royalty_alarm_manager = RoyaltyAlarmManager()
        self.current_navmesh_fence_id = 1
        self._time_of_last_save = clock.GameClock.NEW_GAME_START_TIME()
        self._time_of_zone_spin_up = None
        self._client_connect_speed = ClockSpeedMode.NORMAL
        self._first_visit_to_zone = None
        self._active_lot_arrival_spawn_point = None
        self._time_of_last_open_street_save = None
        for key in zone_types.ZoneState:
            if key != zone_types.ZoneState.ZONE_INIT:
                self._zone_state_callbacks[key] = CallableList()
        self._client = None
        self._tick_metrics = None
        self.service_manager = None
        self._restricted_open_street_autonomy_area = None
        self._should_perform_deferred_front_door_check = False
        self._gc_full_count = 0
        self.is_active_lot_clearing = False

    def __repr__(self):
        return '<Zone ID: {0:#x}>'.format(self.id)

    def ref(self, callback=None):
        return weakref.ref(self, callback)

    @property
    def is_zone_loading(self):
        return self._zone_state == zone_types.ZoneState.ZONE_INIT

    @property
    def are_sims_hitting_their_marks(self):
        return self._zone_state == zone_types.ZoneState.HITTING_THEIR_MARKS

    @property
    def is_zone_running(self):
        return self._zone_state == zone_types.ZoneState.RUNNING

    @property
    def is_zone_shutting_down(self):
        return self._zone_state == zone_types.ZoneState.SHUTDOWN_STARTED

    @property
    def is_households_and_sim_infos_loaded(self):
        return self._zone_state == zone_types.ZoneState.HOUSEHOLDS_AND_SIM_INFOS_LOADED

    @property
    def animate_instantly(self):
        return self._zone_state != zone_types.ZoneState.RUNNING

    @property
    def route_instantly(self):
        return self._zone_state != zone_types.ZoneState.RUNNING or self.force_route_instantly

    @property
    def force_process_transitions(self):
        return self._zone_state != zone_types.ZoneState.RUNNING

    @property
    def is_instantiated(self):
        return True

    @property
    def active_lot_arrival_spawn_point(self):
        return self._active_lot_arrival_spawn_point

    def _get_zone_proto(self):
        return services.get_persistence_service().get_zone_proto_buff(self.id)

    def get_current_fence_id_and_increment(self):
        current_id = self.current_navmesh_fence_id
        self.current_navmesh_fence_id = current_id + 1
        return current_id

    @property
    def is_first_visit_to_zone(self):
        logger.assert_raise(self._first_visit_to_zone is not None, 'You must wait until after load_zone() has been called before checking is_first_visit_to_zone.', owner='sscholl')
        return self._first_visit_to_zone

    def get_zone_info(self):
        world_description_id = services.get_world_description_id(self.world_id)
        lot_description_id = services.get_lot_description_id(self.lot.lot_id, world_description_id)
        neighborhood_id = self.neighborhood_id
        neighborhood_data = services.get_persistence_service().get_neighborhood_proto_buff(neighborhood_id)
        return (lot_description_id, world_description_id, neighborhood_id, neighborhood_data)

    def start_services(self, gameplay_zone_data, save_slot_data):
        _distributor = distributor.system.Distributor.instance()
        self.sim_quadtree = placement.get_sim_quadtree_for_zone(self.id)
        self.single_part_condition_list = weakref.WeakKeyDictionary()
        self.multi_part_condition_list = weakref.WeakKeyDictionary()
        services.get_event_manager().enable_event_manager()
        services.time_service().on_zone_startup()
        from adoption.adoption_service import AdoptionService
        from animation.arb_accumulator import ArbAccumulatorService
        from autonomy.autonomy_service import AutonomyService
        from broadcasters.broadcaster_service import BroadcasterService, BroadcasterRealTimeService
        from conditional_layers.conditional_layer_service import ConditionalLayerService
        from drama_scheduler.drama_scheduler import DramaScheduleService
        from ensemble.ensemble_service import EnsembleService
        from filters.demographics_service import DemographicsService
        from filters.neighborhood_population_service import NeighborhoodPopulationService
        from filters.sim_filter_service import SimFilterService
        from household_calendar.calendar_service import CalendarService
        from interactions.privacy import PrivacyService
        from laundry.laundry_service import LaundryService
        from objects.doors.door_service import DoorService
        from objects.gardening.gardening_service import GardeningService
        from objects.locators.locator_manager import LocatorManager
        from objects.object_manager import ObjectManager, PartyManager, InventoryManager, SocialGroupManager
        from objects.props.prop_manager import PropManager
        from plex.plex_service import PlexService
        from postures.posture_graph import PostureGraphService
        from services.cleanup_service import CleanupService
        from services.fire_service import FireService
        from services.reset_and_delete_service import ResetAndDeleteService
        from sims.culling.culling_service import CullingService
        from sims.daycare import DaycareService
        from sims.master_controller import MasterController
        from sims.sim_spawner_service import SimSpawnerService
        from sims4.sim_irq_service import SimIrqService
        from situations.ambient.ambient_service import AmbientService
        from situations.service_npcs.service_npc_manager import ServiceNpcService
        from situations.situation_manager import SituationManager
        from socials.clustering import ObjectClusterService, SocialGroupClusterService
        from story_progression.story_progression_service import StoryProgressionService
        from ui.ui_dialog_service import UiDialogService
        from venues.venue_service import VenueService
        from zone_modifier.zone_modifier_service import ZoneModifierService
        from zone_spin_up_service import ZoneSpinUpService
        service_list = [SimIrqService(), PlexService(), LocatorManager(), ResetAndDeleteService(), ObjectManager(manager_id=MGR_OBJECT), InventoryManager(manager_id=MGR_OBJECT), ConditionalLayerService(), DoorService(), PropManager(manager_id=MGR_OBJECT), TravelGroupManager(manager_id=MGR_TRAVEL_GROUP), PostureGraphService(), ArbAccumulatorService(None, None), AutonomyService(), SimSpawnerService(), EnsembleService(), SituationManager(manager_id=MGR_SITUATION), DemographicsService(), SimFilterService(), NPCHostedSituationService(), PartyManager(manager_id=MGR_PARTY), SocialGroupManager(manager_id=MGR_SOCIAL_GROUP), UiDialogService(), CalendarService(), DramaScheduleService(), ObjectClusterService(), SocialGroupClusterService(), NeighborhoodPopulationService(), ServiceNpcService(), VenueService(), AmbientService(), StoryProgressionService(), ZoneSpinUpService(), PrivacyService(), FireService(), ZoneModifierService(), BroadcasterService(), BroadcasterRealTimeService(), CleanupService(), CareerService(), DaycareService(), LaundryService(), PhotographyService(), AdoptionService(), CullingService(), GardeningService(), MasterController()]
        from sims4.service_manager import ServiceManager
        self.service_manager = ServiceManager()
        for service in service_list:
            if service is not None:
                self.service_manager.register_service(service)
        self.service_manager.start_services(zone=self, container=self, gameplay_zone_data=gameplay_zone_data, save_slot_data=save_slot_data)
        self.navmesh_alarm_handle = alarms.add_alarm_real_time(self, clock.interval_in_real_seconds(1), self._check_navmesh_updated_alarm_callback, repeating=True, use_sleep_time=False)
        self._royalty_alarm_manager.start_schedule()

    def update(self, absolute_ticks):
        game_clock = services.game_clock_service()
        time_service = services.time_service()
        season_service = services.season_service()
        weather_service = services.weather_service()
        narrative_service = services.narrative_service()
        if self._zone_state == zone_types.ZoneState.CLIENT_CONNECTED:
            game_clock.tick_game_clock(absolute_ticks)
        elif self._zone_state == zone_types.ZoneState.HITTING_THEIR_MARKS:
            time_service.update(time_slice=False)
            self.sim_filter_service.update()
            self.situation_manager.update()
            self.sim_spawner_service.update()
            self.broadcaster_service.update()
            self.broadcaster_real_time_service.update()
            self.zone_spin_up_service.update()
        elif self._zone_state == zone_types.ZoneState.RUNNING:
            game_clock.tick_game_clock(absolute_ticks)
            time_service.update()
            self.sim_filter_service.update()
            self.object_cluster_service.update()
            if narrative_service is not None:
                narrative_service.update()
            if game_clock.clock_speed != ClockSpeedMode.PAUSED:
                self.situation_manager.update()
                self.sim_spawner_service.update()
                self.broadcaster_service.update()
                self.broadcaster_real_time_service.update()
                self.story_progression_service.update()
                if season_service is not None:
                    season_service.update()
                if weather_service is not None:
                    weather_service.update()
                adaptive_clock_speed.AdaptiveClockSpeed.update_adaptive_speed()
        self._gather_tick_metrics(absolute_ticks)

    def _gather_tick_metrics(self, absolute_ticks):
        game_clock = services.game_clock_service()
        time_service = services.time_service()
        if self._tick_metrics is not None:
            self._tick_metrics.append(TickMetric(absolute_ticks=absolute_ticks, sim_now=time_service.sim_now, clock_speed=int(game_clock.clock_speed), clock_speed_multiplier=game_clock.current_clock_speed_scale(), game_time=game_clock.now(), multiplier_type=game_clock.clock_speed_multiplier_type))

    def start_gathering_tick_metrics(self):
        self._tick_metrics = []

    def stop_gathering_tick_metrics(self):
        self._tick_metrics = None

    @property
    def tick_data(self):
        return self._tick_metrics

    def do_zone_spin_up(self, household_id, active_sim_id):
        self.zone_spin_up_service.set_household_id_and_client_and_active_sim_id(household_id=household_id, client=self._client, active_sim_id=active_sim_id)
        game_clock = services.game_clock_service()
        time_service = services.time_service()
        self._time_of_zone_spin_up = time_service.sim_now
        self._initialize_clock_speed()
        game_clock.enter_zone_spin_up()
        self.zone_spin_up_service.start_playable_sequence()
        while not self.zone_spin_up_service.is_finished:
            time_service.update(time_slice=False)
            self.zone_spin_up_service.update()
            self.sim_filter_service.update()
            self.situation_manager.update()
            self.sim_spawner_service.update()
        if self.zone_spin_up_service.had_an_error:
            return False
        else:
            self._set_zone_state(zone_types.ZoneState.HITTING_THEIR_MARKS)
            self.zone_spin_up_service.start_hitting_their_marks_sequence()
            return True

    def _should_restore_saved_client_connect_speed(self):
        if self._client_connect_speed is None:
            return False
        if self.is_first_visit_to_zone:
            return False
        elif self.time_has_passed_in_world_since_zone_save():
            return False
        return True

    def _initialize_clock_speed(self):
        game_clock_service = services.game_clock_service()
        if self._should_restore_saved_client_connect_speed():
            if self._client_connect_speed == ClockSpeedMode.PAUSED:
                game_clock_service.set_clock_speed(ClockSpeedMode.NORMAL)
                game_clock_service.push_speed(self._client_connect_speed)
            else:
                game_clock_service.set_clock_speed(self._client_connect_speed)
            self._client_connect_speed = None
        else:
            game_clock_service.set_clock_speed(ClockSpeedMode.NORMAL)
        game_clock_service.push_speed(ClockSpeedMode.PAUSED, reason='Paused during camera lerp')

    def do_build_mode_zone_spin_up(self, household_id):
        self.zone_spin_up_service.set_household_id_and_client_and_active_sim_id(household_id=household_id, client=self._client, active_sim_id=None)
        self.zone_spin_up_service.start_build_mode_sequence()
        while not self.zone_spin_up_service.is_finished:
            self.zone_spin_up_service.update()
        if self.zone_spin_up_service.had_an_error:
            return False
        else:
            self._set_zone_state(zone_types.ZoneState.HITTING_THEIR_MARKS)
            self._set_zone_state(zone_types.ZoneState.RUNNING)
            self._set_initial_camera_focus()
            return True

    def on_hit_their_marks(self):
        self._set_zone_state(zone_types.ZoneState.RUNNING)
        game_clock = services.game_clock_service()
        game_clock.exit_zone_spin_up()
        self._set_initial_camera_focus()

    def _set_initial_camera_focus(self):
        client = self._client
        if camera.deserialize(client=client, active_sim=client.active_sim):
            return
        if client.active_sim is not None:
            camera.focus_on_sim(follow=True, client=client)
        else:
            camera.set_to_default()

    def on_soak_end(self):
        import argparse
        import services
        parser = argparse.ArgumentParser()
        parser.add_argument('--on_shutdown_commands')
        (args, unused_args) = parser.parse_known_args()
        args_dict = vars(args)
        shutdown_commands_file = args_dict.get('on_shutdown_commands')
        if shutdown_commands_file:
            clients = list(client for client in services.client_manager().values())
            if not clients:
                client_id = 0
            else:
                client_id = clients[0].id
            sims4.command_script.run_script(shutdown_commands_file, client_id)

    def on_teardown(self, client):
        logger.debug('Zone teardown started')
        object_leak_tracker = services.get_object_leak_tracker()
        if object_leak_tracker is not None:
            object_leak_tracker.unregister_gc_callback()
        self.on_soak_end()
        self._set_zone_state(zone_types.ZoneState.SHUTDOWN_STARTED)
        sims4.core_services.service_manager.on_zone_unload()
        game_services.service_manager.on_zone_unload()
        self.service_manager.on_zone_unload()
        logger.debug('Zone teardown: disable event manager')
        services.get_event_manager().disable_on_teardown()
        self.ui_dialog_service.disable_on_teardown()
        logger.debug('Zone teardown: destroy situations')
        self.situation_manager.destroy_situations_on_teardown()
        logger.debug('Zone teardown: flush sim_infos to client')
        services.sim_info_manager().flush_to_client_on_teardown()
        logger.debug('Zone teardown: remove Sims from master controller')
        self.master_controller.remove_all_sims_and_disable_on_teardown()
        logger.debug('Zone teardown: clear object manager caches')
        self.object_manager.clear_caches_on_teardown()
        posture_graph_service = services.current_zone().posture_graph_service
        posture_graph_service.on_teardown()
        self.object_cluster_service.on_teardown()
        logger.debug('Zone teardown: destroy objects and sims')
        all_objects = []
        all_objects.extend(self.prop_manager.values())
        all_objects.extend(self.inventory_manager.values())
        all_objects.extend(self.object_manager.values())
        services.get_reset_and_delete_service().trigger_batch_destroy(all_objects)
        if game_services.service_manager.allow_shutdown:
            logger.debug('Zone teardown: destroy sim infos')
            services.sim_info_manager().destroy_all_objects()
            logger.debug('Zone teardown: destroy households')
            services.household_manager().destroy_all_objects()
        indexed_manager.object_load_times.clear()
        logger.debug('Zone teardown: lot teardown')
        self.lot.on_teardown()
        logger.debug('Zone teardown:  services.on_client_disconnect')
        services.on_client_disconnect(client)
        logger.debug('Zone teardown:  time_service')
        time_service = services.time_service()
        time_service.on_teardown(game_services.service_manager.is_traveling)
        services.get_persistence_service().remove_save_locks()
        logger.debug('Zone teardown:  complete')
        self.zone_spin_up_service.do_clean_up()
        self._client = None

    def ensure_callable_list_is_empty(self, callable_list):
        while callable_list:
            callback = callable_list.pop()
            logger.error('Callback {} from CallableList {} was not unregistered before shutdown.', callback, callable_list, owner='tastle')

    def on_add(self):
        self._start_gc_tracking()
        object_leak_tracker = services.get_object_leak_tracker()
        if object_leak_tracker is not None:
            object_leak_tracker.start_tracking()

    def on_remove(self):
        logger.assert_log(self.is_zone_shutting_down, 'Attempting to shutdown the zone when it is not ready:{}', self._zone_state, owner='sscholl')
        interactions.constraints.RequiredSlot.clear_required_slot_cache()
        animation_drift_monitor_on_zone_shutdown()
        self.service_manager.stop_services(self)
        self.ensure_callable_list_is_empty(self.navmesh_change_callbacks)
        self.ensure_callable_list_is_empty(self.wall_contour_update_callbacks)
        self.ensure_callable_list_is_empty(self.foundation_and_level_height_update_callbacks)
        self._zone_state_callbacks.clear()
        caches.clear_all_caches(force=True)
        get_throwaway_animation_context()
        self._stop_gc_tracking()
        gc.collect()
        object_leak_tracker = services.get_object_leak_tracker()
        if object_leak_tracker is not None:
            object_leak_tracker.stop_tracking()

    def _start_gc_tracking(self):
        gc.callbacks.append(self._gc_callback)

    def _stop_gc_tracking(self):
        gc.callbacks.remove(self._gc_callback)
        if self._time_of_zone_spin_up is not None:
            now = services.time_service().sim_now
            time_in_zone = now - self._time_of_zone_spin_up
            minutes_in_zone = math.floor(time_in_zone.in_minutes())
            with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_ZONESHUTDOWN) as hook:
                hook.write_int(TELEMETRY_GCCOUNT, self._gc_full_count)
                hook.write_int(TELEMETRY_ZONETIME, minutes_in_zone)
            if gc_count_log is not None:
                gc_count_log.append((self.id, self._gc_full_count, minutes_in_zone))

    def _gc_callback(self, phase, info):
        generation = info['generation']
        if phase == 'stop':
            self._gc_full_count += 1

    def _check_for_leaked_managed_objects(self):

        def check_for_leaks(weak_set, type_name, ignore_types=None):
            gc.collect()
            leaks = list(weak_set)
            if ignore_types is not None:
                real_leaks = []
                for obj in leaks:
                    if type(obj) in ignore_types:
                        break
                    else:
                        real_leaks.append(obj)
                leaks = real_leaks
            if not leaks:
                return
            logger.warn('{} {}s leaked. {}', len(leaks), type_name, '' if _trace_all_leaks else 'Enable _trace_all_leaks in zone.py for potential callstacks. ', owner='mduke')
            for item in leaks:
                logger.warn('    {} "{}"', type(item).__name__, item)
            if _trace_all_leaks:
                time_stamp = time.time()
                for item in leaks:
                    find_object_refs(item, valid_refs={id(weak_set)})
                    if time.time() - time_stamp > 25:
                        logger.warn('{} leak detection terminated after 25ms.', type_name, owner='mduke')
                        break
                weak_set.clear()

        self.manager_reference_tracker.remove(self)
        check_for_leaks(self.all_interactions, 'interaction')
        ignore_managed_object_types = None
        if services.game_services.service_manager.is_traveling:
            import sims
            ignore_managed_object_types = set((sims.sim_info.SimInfo, sims.household.Household))
        check_for_leaks(self.manager_reference_tracker, 'managed object', ignore_types=ignore_managed_object_types)

    def on_objects_loaded(self):
        self._set_zone_state(zone_types.ZoneState.OBJECTS_LOADED)

    def on_client_connect(self, client):
        self._client = client
        self._set_zone_state(zone_types.ZoneState.CLIENT_CONNECTED)

    def on_households_and_sim_infos_loaded(self):
        self._set_zone_state(zone_types.ZoneState.HOUSEHOLDS_AND_SIM_INFOS_LOADED)

    def on_loading_screen_animation_finished(self):
        logger.debug('on_loading_screen_animation_finished')
        services.game_clock_service().restore_saved_clock_speed()
        services.sim_info_manager().on_loading_screen_animation_finished()
        services.get_event_manager().process_events_for_household(test_events.TestEvent.SimTravel, services.active_household(), zone_id=self.id)
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None:
            business_manager.on_loading_screen_animation_finished()
        services.venue_service().on_loading_screen_animation_finished()
        landlord_service = services.get_landlord_service()
        if landlord_service is not None:
            landlord_service.on_loading_screen_animation_finished()
        laundry_service = services.get_laundry_service()
        if laundry_service is not None:
            laundry_service.on_loading_screen_animation_finished()
        self.zone_spin_up_service.on_loading_screen_animation_finished()

    def _set_zone_state(self, state):
        logger.assert_raise(self._zone_state + 1 == state or state == zone_types.ZoneState.SHUTDOWN_STARTED, 'Illegal zone state change: {} to {}', self._zone_state, state, owner='sscholl')
        self._zone_state = state
        if state in self._zone_state_callbacks:
            self._zone_state_callbacks[state]()
            del self._zone_state_callbacks[state]

    def register_callback(self, callback_type, callback):
        if self._zone_state == zone_types.ZoneState.SHUTDOWN_STARTED:
            return
        if callback_type <= self._zone_state:
            callback()
            return
        self._zone_state_callbacks[callback_type].append(callback)

    def unregister_callback(self, callback_type, callback):
        if callback in self._zone_state_callbacks[callback_type]:
            self._zone_state_callbacks[callback_type].remove(callback)

    def find_object(self, obj_id, include_props=False):
        obj = self.object_manager.get(obj_id)
        if obj is None:
            obj = self.inventory_manager.get(obj_id)
        if include_props:
            obj = self.prop_manager.get(obj_id)
        return obj

    def spawn_points_gen(self):
        yield from self._world_spawn_points.values()
        yield from self._dynamic_spawn_points.values()

    def _get_spawn_point_by_id(self, spawn_point_id):
        if spawn_point_id in self._world_spawn_points:
            return self._world_spawn_points[spawn_point_id]
        elif spawn_point_id in self._dynamic_spawn_points:
            return self._dynamic_spawn_points[spawn_point_id]

    def set_up_world_spawn_points(self, locator_array):
        self._world_spawn_point_locators = locator_array

    def add_dynamic_spawn_point(self, spawn_point):
        self._dynamic_spawn_points[spawn_point.spawn_point_id] = spawn_point
        spawn_point.on_add()
        self._on_spawn_points_changed()

    def remove_dynamic_spawn_point(self, spawn_point):
        spawn_point.on_remove()
        self._dynamic_spawn_points.pop(spawn_point.spawn_point_id)
        self._on_spawn_points_changed()

    def get_spawn_point_ignore_constraint(self):
        objects_to_ignore = set()
        for spawn_point in self._world_spawn_points.values():
            objects_to_ignore.add(spawn_point.spawn_point_id)
        return Constraint(objects_to_ignore=objects_to_ignore, debug_name='IgnoreSpawnPointConstraint')

    def _get_spawn_points_with_lot_id_and_tags(self, sim_info=None, lot_id=None, sim_spawner_tags=None, except_lot_id=None, spawn_point_request_reason=SpawnPointRequestReason.DEFAULT):
        spawn_points = []
        if not sim_spawner_tags:
            return
        for spawn_point in self.spawn_points_gen():
            if lot_id is not None and spawn_point.lot_id != lot_id:
                pass
            elif except_lot_id is not None and spawn_point.lot_id == except_lot_id:
                pass
            else:
                tags = spawn_point.get_tags()
                if not tags.intersection(sim_spawner_tags):
                    pass
                elif not spawn_point.is_valid(sim_info=sim_info, spawn_point_request_reason=spawn_point_request_reason):
                    pass
                else:
                    spawn_points.append(spawn_point)
        if spawn_points:
            max_priority = max(p.spawn_point_priority for p in spawn_points)
            spawn_points = [p for p in spawn_points if p.spawn_point_priority == max_priority]
        return spawn_points

    def get_spawn_point(self, lot_id=None, sim_spawner_tags=None, must_have_tags=False, spawning_sim_info=None, spawn_point_request_reason=SpawnPointRequestReason.DEFAULT):
        spawn_points = list(self.spawn_points_gen())
        if not spawn_points:
            return
        spawn_points_with_tags = self._get_spawn_points_with_lot_id_and_tags(sim_info=spawning_sim_info, lot_id=lot_id, sim_spawner_tags=sim_spawner_tags, spawn_point_request_reason=spawn_point_request_reason)
        if not must_have_tags:
            spawn_points_with_tags = self._get_spawn_points_with_lot_id_and_tags(sim_info=spawning_sim_info, sim_spawner_tags=sim_spawner_tags, spawn_point_request_reason=spawn_point_request_reason)
        if spawn_points_with_tags or spawn_points_with_tags:
            return random.choice(spawn_points_with_tags)
        elif not must_have_tags:
            return random.choice(spawn_points)
        else:
            return
        return

    def get_spawn_points_constraint(self, sim_info=None, lot_id=None, sim_spawner_tags=None, except_lot_id=None, spawn_point_request_reason=SpawnPointRequestReason.DEFAULT, generalize=False):
        spawn_point_option = SpawnPointOption.SPAWN_ANY_POINT_WITH_CONSTRAINT_TAGS
        search_tags = sim_spawner_tags
        spawn_point_id = None
        original_spawn_point = None
        if sim_spawner_tags is None:
            spawn_point_option = sim_info.spawn_point_option if sim_info.spawn_point_option is not None else SpawnPointOption.SPAWN_SAME_POINT
            spawn_point_id = sim_info.spawn_point_id
            original_spawn_point = self._get_spawn_point_by_id(spawn_point_id)
            if spawn_point_option == SpawnPointOption.SPAWN_ANY_POINT_WITH_SAVED_TAGS or spawn_point_option == SpawnPointOption.SPAWN_DIFFERENT_POINT_WITH_SAVED_TAGS:
                search_tags = sim_info.spawner_tags
        points = []
        if sim_info is not None and search_tags is not None:
            spawn_points_with_tags = self._get_spawn_points_with_lot_id_and_tags(sim_info=sim_info, lot_id=lot_id, sim_spawner_tags=search_tags, except_lot_id=except_lot_id, spawn_point_request_reason=spawn_point_request_reason)
            if spawn_points_with_tags:
                for spawn_point in spawn_points_with_tags:
                    if spawn_point_option == SpawnPointOption.SPAWN_DIFFERENT_POINT_WITH_SAVED_TAGS and original_spawn_point is not None and spawn_point.spawn_point_id == original_spawn_point.spawn_point_id:
                        pass
                    else:
                        position_constraints = spawn_point.get_position_constraints(generalize=generalize)
                        if position_constraints:
                            points.extend(position_constraints)
                if spawn_point_option == SpawnPointOption.SPAWN_DIFFERENT_POINT_WITH_SAVED_TAGS and original_spawn_point and points:
                    approximate_center = original_spawn_point.get_approximate_center()
                    comparable_spawn_point_center = sims4.math.Vector3(approximate_center.x, 0.0, approximate_center.z)
                    weighted_points = [((comparable_spawn_point_center - point.single_point()[0]).magnitude(), point) for point in points]
                    selected_spawn_point = sims4.random.weighted_random_item(weighted_points)
                    return interactions.constraints.create_constraint_set(set(selected_spawn_point))
                if points:
                    return interactions.constraints.create_constraint_set(points)
        if spawn_point_option == SpawnPointOption.SPAWN_SAME_POINT and original_spawn_point:
            points = original_spawn_point.get_position_constraints(generalize=generalize)
            if points:
                return interactions.constraints.create_constraint_set(points)
        for spawn_point in self.spawn_points_gen():
            position_constraints = spawn_point.get_position_constraints(generalize=generalize)
            if position_constraints:
                points.extend(position_constraints)
        if points:
            return interactions.constraints.create_constraint_set(points)
        logger.warn('There are no spawn locations on this lot.  The corners of the lot are being used instead: {}', services.current_zone().lot, owner='rmccord')
        return self.get_lot_corners_constraint_set()

    def get_lot_corners_constraint_set(self):
        lot_center = self.lot.center
        lot_corners = services.current_zone().lot.corners
        routing_surface = routing.SurfaceIdentifier(services.current_zone().id, 0, routing.SurfaceType.SURFACETYPE_WORLD)
        constraint_list = []
        for corner in lot_corners:
            diff = lot_center - corner
            if diff.magnitude_squared() != 0:
                towards_center_vec = sims4.math.vector_normalize(lot_center - corner)*0.1
            else:
                towards_center_vec = sims4.math.Vector3.ZERO()
            new_corner = corner + towards_center_vec
            constraint_list.append(interactions.constraints.Position(new_corner, routing_surface=routing_surface))
        return create_constraint_set(constraint_list)

    def validate_spawn_points(self):
        if self._world_spawn_points or not self._dynamic_spawn_points:
            return
        dest_handles = set()
        lot_center = self.lot.center
        lot_corners = self.lot.corners
        routing_surface = routing.SurfaceIdentifier(self.id, 0, routing.SurfaceType.SURFACETYPE_WORLD)
        for corner in lot_corners:
            diff = lot_center - corner
            if diff.magnitude_squared() != 0:
                towards_center_vec = sims4.math.vector_normalize(lot_center - corner)*0.1
            else:
                towards_center_vec = sims4.math.Vector3.ZERO()
            new_corner = corner + towards_center_vec
            location = routing.Location(new_corner, sims4.math.Quaternion.IDENTITY(), routing_surface)
            dest_handles.add(routing.connectivity.Handle(location))
        for spawn_point in self.spawn_points_gen():
            spawn_point.validate_connectivity(dest_handles)
        self._on_spawn_points_changed()

    def register_spawn_points_changed_callback(self, callback):
        self._spawn_points_changed_callbacks.append(callback)

    def unregister_spawn_points_changed_callback(self, callback):
        self._spawn_points_changed_callbacks.remove(callback)

    def _on_spawn_points_changed(self):
        self._spawn_points_changed_callbacks()

    def _update_navmesh_id_if_neccessary(self):
        new_navmesh_id = interactions.utils.routing.routing.planner_build_id()
        if self.navmesh_id != new_navmesh_id:
            self.navmesh_id = new_navmesh_id
            self.check_perform_deferred_front_door_check()
            self.navmesh_change_callbacks()
            self._handle_live_drag_objects()
            if gsi_handlers.routing_handlers.build_archiver.enabled:
                gsi_handlers.routing_handlers.archive_build(new_navmesh_id)

    def _handle_live_drag_objects(self):
        client = services.client_manager().get_first_client()
        if client is not None:
            sim_info_manager = services.sim_info_manager()
            for live_drag_object in client.objects_moved_via_live_drag:
                footprint_polygon = live_drag_object.footprint_polygon
                if footprint_polygon is not None:
                    for sim in sim_info_manager.instanced_sims_gen():
                        if footprint_polygon.contains(sim.position):
                            sim.reset(ResetReason.RESET_EXPECTED, cause='Live Drag object with footprint dropped on Sim.')
            client.objects_moved_via_live_drag.clear()

    def check_perform_deferred_front_door_check(self):
        if self._should_perform_deferred_front_door_check:
            logger.info('Attempting to fix up doors, searching...')
            services.get_door_service().fix_up_doors()
            if not services.get_door_service().has_front_door():
                logger.info('No front door found.')
            self._should_perform_deferred_front_door_check = False

    def _check_navmesh_updated_alarm_callback(self, *_):
        try:
            self._update_navmesh_id_if_neccessary()
        except:
            logger.exception('Exception thrown while processing navmesh update callbacks. Eating this exception to prevent the alarm from self-destructing.', owner='tastle')

    def on_build_buy_enter(self):
        self.is_in_build_buy = True
        laundry_service = services.get_laundry_service()
        if laundry_service is not None:
            laundry_service.on_build_buy_enter()

    def on_build_buy_exit(self):
        self._update_navmesh_id_if_neccessary()
        self.is_in_build_buy = False
        self._add_expenditures_and_do_post_bb_fixup()
        services.active_lot().flag_as_premade(False)
        services.get_event_manager().process_events_for_household(test_events.TestEvent.OnExitBuildBuy, None)
        self._should_perform_deferred_front_door_check = True
        laundry_service = services.get_laundry_service()
        if laundry_service is not None:
            laundry_service.on_build_buy_exit()

    def on_active_lot_clearing_begin(self):
        self.is_active_lot_clearing = True

    def on_active_lot_clearing_end(self):
        self.is_active_lot_clearing = False

    def set_to_fixup_on_build_buy_exit(self, obj):
        if self.objects_to_fixup_post_bb is None:
            self.objects_to_fixup_post_bb = weakref.WeakSet()
        self.objects_to_fixup_post_bb.add(obj)

    def _add_expenditures_and_do_post_bb_fixup(self):
        if self.objects_to_fixup_post_bb is not None:
            household = self.lot.get_household()
            rebate_manager = household.rebate_manager if household is not None else None
            active_household_id = services.active_household_id()
            for obj in self.objects_to_fixup_post_bb:
                if rebate_manager is not None:
                    rebate_manager.add_rebate_for_object(obj.id, RebateCategoryEnum.BUILD_BUY)
                obj.try_post_bb_fixup(active_household_id=active_household_id)
            self.objects_to_fixup_post_bb = None

    @property
    def save_slot_data_id(self):
        return self._save_slot_data_id

    def save_zone(self, save_slot_data=None):
        zone_data_msg = self._get_zone_proto()
        zone_data_msg.ClearField('gameplay_zone_data')
        gameplay_zone_data = zone_data_msg.gameplay_zone_data
        gameplay_zone_data.lot_owner_household_id_on_save = self.lot.owner_household_id
        gameplay_zone_data.venue_type_id_on_save = self.venue_service.venue.guid64 if self.venue_service.venue is not None else 0
        gameplay_zone_data.active_household_id_on_save = services.active_household_id()
        travel_group = self.travel_group_manager.get_travel_group_by_zone_id(self.id)
        gameplay_zone_data.active_travel_group_id_on_save = travel_group.id if travel_group is not None else 0
        save_ticks = services.time_service().sim_now.absolute_ticks()
        game_clock = services.game_clock_service()
        gameplay_zone_data.game_time = save_ticks
        if game_clock.persistable_clock_speed == ClockSpeedMode.PAUSED:
            gameplay_zone_data.clock_speed_mode = ClockSpeedMode.PAUSED
        else:
            gameplay_zone_data.clock_speed_mode = ClockSpeedMode.NORMAL
        self.lot.save(gameplay_zone_data)
        num_spawn_points = len(self._world_spawn_points)
        spawn_point_ids = [0]*num_spawn_points
        for (spawn_point_id, spawn_point) in self._world_spawn_points.items():
            spawn_point_ids[spawn_point.spawn_point_index] = spawn_point_id
        zone_data_msg.ClearField('spawn_point_ids')
        zone_data_msg.spawn_point_ids.extend(spawn_point_ids)
        zone_objects_message = serialization.ZoneObjectData()
        object_list = serialization.ObjectList()
        zone_objects_message.zone_id = self.id
        persistence_service = services.get_persistence_service()
        open_street_data = persistence_service.get_open_street_proto_buff(self.open_street_id)
        if open_street_data is not None:
            open_street_data.Clear()
            add_proto_to_persistence = False
        else:
            open_street_data = serialization.OpenStreetsData()
            add_proto_to_persistence = True
        open_street_data.world_id = self.open_street_id
        open_street_data.nbh_id = self.neighborhood_id
        open_street_data.sim_time_on_save = save_ticks
        open_street_data.active_household_id_on_save = services.active_household_id()
        open_street_data.active_zone_id_on_save = self.id
        neighborhood_protocol_buffer = persistence_service.get_neighborhood_proto_buff(self.neighborhood_id)
        region_tuning = Region.REGION_DESCRIPTION_TUNING_MAP.get(neighborhood_protocol_buffer.region_id)
        store_travel_group_placed_objects = False
        if region_tuning.store_travel_group_placed_objects:
            store_travel_group_placed_objects = region_tuning.store_travel_group_placed_objects
        game_service_manager = game_services.service_manager
        game_service_manager.save_all_services(persistence_service, object_list=object_list, zone_data=zone_data_msg, open_street_data=open_street_data, store_travel_group_placed_objects=store_travel_group_placed_objects, save_slot_data=save_slot_data)
        self.service_manager.save_all_services(persistence_service, object_list=object_list, zone_data=zone_data_msg, open_street_data=open_street_data, store_travel_group_placed_objects=store_travel_group_placed_objects, save_slot_data=save_slot_data)
        zone_objects_message.objects = object_list
        if region_tuning is not None and add_proto_to_persistence:
            services.get_persistence_service().add_open_street_proto_buff(open_street_data)
        persistence_module.run_persistence_operation(persistence_module.PersistenceOpType.kPersistenceOpSaveZoneObjects, zone_objects_message, 0, None)

    def load_zone(self):
        zone_data_proto = self._get_zone_proto()
        gameplay_zone_data = zone_data_proto.gameplay_zone_data
        self.neighborhood_id = zone_data_proto.neighborhood_id
        self.open_street_id = zone_data_proto.world_id
        game_service_manager = game_services.service_manager
        game_service_manager.load_all_services(zone_data=zone_data_proto)
        self.service_manager.load_all_services(zone_data=zone_data_proto)
        self._first_visit_to_zone = not protocol_buffer_utils.has_field(gameplay_zone_data, 'venue_type_id_on_save')
        if gameplay_zone_data.HasField('game_time'):
            self._time_of_last_save = DateAndTime(gameplay_zone_data.game_time)
        if gameplay_zone_data.HasField('clock_speed_mode'):
            self._client_connect_speed = ClockSpeedMode(gameplay_zone_data.clock_speed_mode)
        open_street_data = services.get_persistence_service().get_open_street_proto_buff(self.open_street_id)
        if open_street_data is not None:
            self._time_of_last_open_street_save = DateAndTime(open_street_data.sim_time_on_save)
        if zone_data_proto.spawn_point_ids and len(zone_data_proto.spawn_point_ids) != len(self._world_spawn_point_locators):
            logger.error('Number of world spawn points {} does not match persisted count of {}. This is possible if world builder has added or removed spawn points since the last time this zone was visited. Resetting spawn point ids to recover from this error case. This might temporarily cause Sims to leave to random spawn points.', len(self._world_spawn_point_locators), len(zone_data_proto.spawn_point_ids), owner='tingyul')
            zone_data_proto.ClearField('spawn_point_ids')
        for (index, locator) in enumerate(self._world_spawn_point_locators):
            spawn_point_id = zone_data_proto.spawn_point_ids[index] if zone_data_proto.spawn_point_ids else None
            spawn_point = WorldSpawnPoint(index, locator, self.id, spawn_point_id=spawn_point_id)
            self._world_spawn_points[spawn_point.spawn_point_id] = spawn_point
            spawn_point.on_add()
        self._world_spawn_point_locators = None
        self.lot.load(gameplay_zone_data)
        for spawn_point in self._world_spawn_points.values():
            if spawn_point.has_tag(SpawnPoint.ARRIVAL_SPAWN_POINT_TAG) and spawn_point.lot_id == self.lot.lot_id:
                self._active_lot_arrival_spawn_point = spawn_point
        self.region = region.get_region_instance_from_zone_id(self.id)
        self.street = street.get_street_instance_from_zone_id(self.id)
        return True

    def lot_owner_household_changed_between_save_and_load(self):
        zone_data_proto = self._get_zone_proto()
        if zone_data_proto is None or self.lot is None:
            return False
        gameplay_zone_data = zone_data_proto.gameplay_zone_data
        if not protocol_buffer_utils.has_field(gameplay_zone_data, 'lot_owner_household_id_on_save'):
            return False
        return gameplay_zone_data.lot_owner_household_id_on_save != self.lot.owner_household_id

    def active_household_changed_between_save_and_load(self):
        zone_data_proto = self._get_zone_proto()
        if zone_data_proto is None:
            return False
        gameplay_zone_data = zone_data_proto.gameplay_zone_data
        if not protocol_buffer_utils.has_field(gameplay_zone_data, 'active_household_id_on_save'):
            return False
        if gameplay_zone_data.active_household_id_on_save == areaserver.SYSTEM_HOUSEHOLD_ID:
            return False
        return gameplay_zone_data.active_household_id_on_save != services.active_household_id()

    def travel_group_changed_between_save_and_load(self):
        zone_data_proto = self._get_zone_proto()
        if zone_data_proto is None:
            return False
        gameplay_zone_data = zone_data_proto.gameplay_zone_data
        if not protocol_buffer_utils.has_field(gameplay_zone_data, 'active_travel_group_id_on_save'):
            return False
        active_household_travel_group_id = 0
        active_household = services.active_household()
        if active_household is not None:
            travel_group = active_household.get_travel_group()
            if travel_group is not None:
                active_household_travel_group_id = travel_group.id
        return gameplay_zone_data.active_travel_group_id_on_save != active_household_travel_group_id

    def update_household_objects_ownership(self):
        zone_data_proto = self._get_zone_proto()
        if zone_data_proto is None:
            return
        venue_instance = self.venue_service.venue
        if venue_instance is None or not venue_instance.requires_front_door:
            return
        gameplay_zone_data = zone_data_proto.gameplay_zone_data
        if self.lot.owner_household_id == 0:
            travel_group = self.travel_group_manager.get_travel_group_by_zone_id(self.id)
            if travel_group is None or protocol_buffer_utils.has_field(gameplay_zone_data, 'active_travel_group_id_on_save') and gameplay_zone_data.active_travel_group_id_on_save != travel_group.id:
                self._set_zone_objects_household_owner_id(None)
        elif self.lot.owner_household_id == services.active_household_id() and protocol_buffer_utils.has_field(gameplay_zone_data, 'active_household_id_on_save') and gameplay_zone_data.lot_owner_household_id_on_save != services.active_household_id():
            self._set_zone_objects_household_owner_id(services.active_household_id())

    def disown_household_objects(self):
        self._set_zone_objects_household_owner_id(None)

    def _set_zone_objects_household_owner_id(self, household_id):
        for obj in services.object_manager(self.id).get_all():
            if obj.is_on_active_lot():
                obj.set_household_owner_id(household_id)
        for (_, inventory) in self.lot.get_all_object_inventories_gen():
            if inventory.owner is not None and inventory.owner.is_sim and inventory.owner.household_id != household_id:
                pass
            else:
                for inv_obj in inventory:
                    inv_obj.set_household_owner_id(household_id)

    def venue_type_changed_between_save_and_load(self):
        zone_data_proto = self._get_zone_proto()
        if zone_data_proto is None or self.venue_service.venue is None:
            return False
        else:
            gameplay_zone_data = zone_data_proto.gameplay_zone_data
            if not protocol_buffer_utils.has_field(gameplay_zone_data, 'venue_type_id_on_save'):
                return False
        return False

    def should_restore_sis(self):
        if self.time_has_passed_in_world_since_zone_save() or (self.venue_type_changed_between_save_and_load() or (self.lot_owner_household_changed_between_save_and_load() or self.active_household_changed_between_save_and_load())) or self.is_first_visit_to_zone:
            return False
        return True

    def get_active_lot_owner_household(self):
        if self.lot is None:
            return
        return services.household_manager().get(self.lot.owner_household_id)

    def time_of_last_save(self):
        return self._time_of_last_save

    def time_elapsed_since_last_save(self):
        time_elapsed = self._time_of_zone_spin_up - self._time_of_last_save
        return time_elapsed

    def time_has_passed_in_world_since_zone_save(self):
        if self.is_first_visit_to_zone:
            return False
        else:
            time_elapsed = self.time_elapsed_since_last_save()
            if time_elapsed > TimeSpan.ZERO:
                return True
        return False

    def time_elapsed_since_last_open_street_save(self):
        if self._time_of_last_open_street_save is None:
            return TimeSpan.ZERO
        time_elapsed = self._time_of_zone_spin_up - self._time_of_last_open_street_save
        return time_elapsed

    def time_has_passed_in_world_since_open_street_save(self):
        time_elapsed = self.time_elapsed_since_last_open_street_save()
        if time_elapsed > TimeSpan.ZERO:
            return True
        return False

    def _get_restricted_autonomy_polygon(self):
        if self._restricted_open_street_autonomy_area is not None:
            return self._restricted_open_street_autonomy_area
        points = [obj.position for obj in services.object_manager().get_objects_with_tag_gen(self.RESTRICTED_AUTONOMY_AREA_TAG)]
        if len(points) != self.FESTIVAL_AUTONOMY_AREA_POINT_COUNT:
            logger.error('Festival autonomy area not defined by exactly 4\n                         points.  {} points found.  Either we or trying to use\n                         the Restricted Autonomy Option on an open street that\n                         does not support it or World Building has not set up\n                         the open street correctly.\n                         ', len(points), owner='jjacobson')
            return
        center = sum(points, sims4.math.Vector3.ZERO())/len(points)
        points.sort(key=lambda k: sims4.math.atan2(k.x - center.x, k.z - center.z), reverse=True)
        self._restricted_open_street_autonomy_area = sims4.geometry.RestrictedPolygon(sims4.geometry.Polygon(points), [])
        return self._restricted_open_street_autonomy_area

    def is_point_in_restricted_autonomy_area(self, point):
        festival_polygon = self._get_restricted_autonomy_polygon()
        if festival_polygon is None:
            return False
        return festival_polygon.contains_point(point)
