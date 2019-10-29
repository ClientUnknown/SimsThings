from collections import Counterimport argparseimport collectionsimport itertoolsimport timefrom careers import coworkerfrom crafting.recipe import destroy_unentitled_craftablesfrom objects import ALL_HIDDEN_REASONS, componentsfrom objects.components.types import PORTAL_COMPONENT, FOOTPRINT_COMPONENTfrom persistence_error_types import ErrorCodes, generate_exception_code, generate_exception_callstackfrom sims4.localization import TunableLocalizedStringfrom traits.sim_info_fixup_action import SimInfoFixupActionTimingfrom world.lot_tuning import GlobalLotTuningAndCleanupfrom world.mailbox_owner_helper import MailboxOwnerHelperfrom world.premade_sim_fixup_helper import PremadeSimFixupHelperimport build_buyimport cachesimport enumimport game_servicesimport pythonutilsimport routingimport servicesimport sims4.command_scriptimport sims4.logimport sims4.service_managerimport telemetry_helperTELEMETRY_GROUP_ZONE = 'ZONE'TELEMETRY_HOOK_ZONE_LOAD = 'LOAD'TELEMETRY_HOOK_ZONE_FAIL = 'FAIL'TELEMETRY_HOOK_INVALID_OBJECTS = 'IOBJ'TELEMETRY_FIELD_NPC_COUNT = 'npcc'TELEMETRY_FIELD_PLAYER_COUNT = 'plyc'TELEMETRY_FIELD_ERROR_CODE = 'code'TELEMETRY_FIELD_STACK_HASH = 'hash'TELEMETRY_FIELD_OBJECTS_COUNT = 'objc'TELEMETRY_FIELD_TOP5_OBJ_ID = 't5oi'TELEMETRY_FIELD_TOP5_OBJ_COUNT = 't5oc'zone_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_ZONE)logger = sims4.log.Logger('ZoneSpinUpService')
class ZoneSpinUpStatus(enum.Int, export=False):
    CREATED = 0
    INITIALIZED = 1
    SEQUENCED = 2
    RUNNING = 3
    COMPLETED = 4
    ERRORED = 5

class _ZoneSpinUpStateResult(enum.Int, export=False):
    WAITING = 0
    DONE = 1

class _ZoneSpinUpState:

    def __init__(self):
        self._task = None
        self._timestamp_on_enter = None

    def exception_error_code(self):
        return ErrorCodes.GENERIC_ERROR

    def on_enter(self):
        logger.debug('{}.on_enter at {}', self.__class__.__name__, services.time_service().sim_now)
        self._timestamp_on_enter = time.time()
        return _ZoneSpinUpStateResult.DONE

    def on_update(self):
        return _ZoneSpinUpStateResult.DONE

    def on_exit(self):
        delta_time = time.time() - self._timestamp_on_enter
        logger.debug('{}.on_exit at {} time spent {:0.02f} sec', self.__class__.__name__, services.time_service().sim_now, delta_time)

class _StopCaching(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.STOP_CACHING_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        caches.skip_cache = True
        return _ZoneSpinUpStateResult.DONE

class _StartCaching(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.START_CACHING_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        caches.skip_cache = False
        caches.clear_all_caches(force=True)
        return _ZoneSpinUpStateResult.DONE

class _SetupPortalsState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.SETUP_PORTALS_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        object_manager = services.object_manager()
        for portal_object in object_manager.portal_cache_gen():
            if portal_object.provided_routing_surface is not None:
                pass
            else:
                portal_component = portal_object.get_component(PORTAL_COMPONENT)
                portal_component.finalize_portals()
        return _ZoneSpinUpStateResult.DONE

class _InitializeDoorServiceState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.INITIALIZED_FRONT_DOOR_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        door_service = services.get_door_service()
        door_service.fix_up_doors()
        return _ZoneSpinUpStateResult.DONE

class _SetMailboxOwnerState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.SET_MAILBOX_OWNER_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        helper = MailboxOwnerHelper()
        helper.assign_mailbox_owners()
        return _ZoneSpinUpStateResult.DONE

class _LoadHouseholdsAndSimInfosState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.LOAD_HOUSEHOLD_AND_SIM_INFO_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        services.household_manager().load_households()
        zone = services.current_zone()
        zone_spin_up_service = zone.zone_spin_up_service
        household_id = zone_spin_up_service._client_connect_data.household_id
        household = services.household_manager().get(household_id)
        client = zone_spin_up_service._client_connect_data.client
        account_service = services.account_service()
        account_service.on_load_options(client)
        zone.service_manager.on_zone_load()
        game_services.service_manager.on_zone_load()
        sims4.core_services.service_manager.on_zone_load()
        for sim_info in household.sim_info_gen():
            client.add_selectable_sim_info(sim_info, send_relationship_update=False)
        zone.on_households_and_sim_infos_loaded()
        zone.service_manager.on_all_households_and_sim_infos_loaded(client)
        game_services.service_manager.on_all_households_and_sim_infos_loaded(client)
        sims4.core_services.service_manager.on_all_households_and_sim_infos_loaded(client)
        services.ui_dialog_service().send_dialog_options_to_client()
        client.clean_and_send_remaining_relationship_info()
        services.current_zone().lot.send_lot_display_info()
        for obj in itertools.chain(services.object_manager().values(), services.inventory_manager().values()):
            if obj.live_drag_component is not None:
                obj.live_drag_component.resolve_live_drag_household_permission()
        return _ZoneSpinUpStateResult.DONE

class _PremadeSimFixupState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.PREMADE_SIM_FIXUP_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        helper = PremadeSimFixupHelper()
        helper.fix_up_premade_sims()
        return _ZoneSpinUpStateResult.DONE

class _SimInfoFixupState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.SIM_INFO_FIXUP_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        for sim_info in services.sim_info_manager().values():
            if sim_info.do_first_sim_info_load_fixups:
                sim_info.apply_fixup_actions(SimInfoFixupActionTiming.ON_FIRST_SIMINFO_LOAD)
        for sim_info in services.active_household():
            sim_info.apply_fixup_actions(SimInfoFixupActionTiming.ON_ADDED_TO_ACTIVE_HOUSEHOLD)
        return _ZoneSpinUpStateResult.DONE

class _SelectZoneDirectorState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.SELECT_ZONE_DIRECTOR_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        venue_service = services.venue_service()
        venue_service.setup_lot_premade_status()
        venue_service.make_venue_type_zone_director_request()
        situation_manager = services.get_zone_situation_manager()
        situation_manager.create_seeds_during_zone_spin_up()
        situation_manager.make_situation_seed_zone_director_requests()
        services.drama_scheduler_service().make_zone_director_requests()
        venue_service._select_zone_director()
        venue_service.determine_which_situations_to_load()
        return _ZoneSpinUpStateResult.DONE

class _DetectAndCleanupInvalidObjectsState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.DETECT_AND_CLEANUP_INVALID_OBJECTS

    def on_enter(self):
        super().on_enter()
        counter = Counter()
        for o in tuple(services.object_manager().values()):
            if sims4.math.vector3_almost_equal(o.position, sims4.math.Vector3.ZERO(), epsilon=0.1):
                counter[o.definition] += 1
                o.destroy(source=self, cause='Object being destroyed from _DetectAndCleanupInvalidObjectsState for sitting on the world origin.')
        if counter:
            log = ''
            top5_obj_id = ''
            top5_obj_count = ''
            counter_count = 0
            for (o, count) in counter.most_common():
                log += '\n{:5} {:75} Tags: {}'.format(count, str(o), o.build_buy_tags)
                if counter_count < 5:
                    counter_count += 1
                    top5_obj_id += '{}, '.format(o.id)
                    top5_obj_count += '{}, '.format(count)
            total_objects = sum(x for x in counter.values())
            logger.error('{} invalid objects detected at worlds origin. {}', total_objects, log, owner='manus')
            self._send_invalid_objects_telemetry(total_objects, top5_obj_id, top5_obj_count)
        services.object_manager().process_invalid_unparented_objects()
        return _ZoneSpinUpStateResult.DONE

    def _send_invalid_objects_telemetry(self, total_objects, top5_obj_id, top5_obj_count):
        with telemetry_helper.begin_hook(zone_telemetry_writer, TELEMETRY_HOOK_INVALID_OBJECTS) as hook:
            hook.write_int(TELEMETRY_FIELD_OBJECTS_COUNT, total_objects)
            hook.write_string(TELEMETRY_FIELD_TOP5_OBJ_ID, top5_obj_id)
            hook.write_string(TELEMETRY_FIELD_TOP5_OBJ_COUNT, top5_obj_count)

class _SetObjectOwnershipState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.SET_OBJECT_OWNERSHIP_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        current_zone = services.current_zone()
        current_zone.update_household_objects_ownership()
        return _ZoneSpinUpStateResult.DONE

class _PrepareLotState(_ZoneSpinUpState):

    def on_enter(self):
        super().on_enter()
        zone = services.current_zone()
        client = zone.zone_spin_up_service._client_connect_data.client
        destroy_unentitled_craftables()
        game_services.service_manager.on_cleanup_zone_objects(client)
        zone.service_manager.on_cleanup_zone_objects(client)
        venue_service = services.venue_service()
        zone_director = venue_service.get_zone_director()
        if zone_director is not None:
            zone_director.on_cleanup_zone_objects()
            if not zone_director.was_loaded:
                zone_director.prepare_lot()
        services.current_zone().posture_graph_service.build_during_zone_spin_up()
        pythonutils.try_highwater_gc()
        return _ZoneSpinUpStateResult.DONE

    def exception_error_code(self):
        return ErrorCodes.CLEANUP_STATE_FAILED

class _SpawnSimsState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.SPAWN_SIM_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        client = services.client_manager().get_first_client()
        services.sim_info_manager().on_spawn_sims_for_zone_spin_up(client)
        return _ZoneSpinUpStateResult.DONE

class _WaitForNavmeshState(_ZoneSpinUpState):

    def __init__(self):
        super().__init__()
        self._sent_fence_id = None

    def exception_error_code(self):
        return ErrorCodes.WAIT_FOR_NAVMESH_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        zone = services.current_zone()
        fence_id = zone.get_current_fence_id_and_increment()
        self._sent_fence_id = fence_id
        routing.flush_planner(False)
        routing.add_fence(fence_id)
        return _ZoneSpinUpStateResult.WAITING

    def on_update(self):
        last_fence_id = routing.get_last_fence()
        if last_fence_id < self._sent_fence_id:
            return _ZoneSpinUpStateResult.WAITING
        return _ZoneSpinUpStateResult.DONE

class _RestoreSIState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.RESTORE_SI_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        zone = services.current_zone()
        if not zone.should_restore_sis():
            logger.debug('NOT restoring interactions in zone spin up', owner='sscholl')
            return _ZoneSpinUpStateResult.DONE
        logger.debug('Restoring interactions in zone spin up', owner='sscholl')
        services.sim_info_manager().restore_sim_si_state()
        return _ZoneSpinUpStateResult.DONE

class _GlobalLotTuningAndCleanupState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.GLOBAL_LOT_TUNING_AND_CLEANUP_FAILED

    def on_enter(self):
        super().on_enter()
        zone = services.current_zone()
        GlobalLotTuningAndCleanup.cleanup_objects(lot=zone.lot)
        return _ZoneSpinUpStateResult.DONE

class _RestoreCareerState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.RESTORE_CAREER_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        services.get_career_service().restore_career_state()
        coworker.fixup_coworker_relationship_bit()
        return _ZoneSpinUpStateResult.DONE

class _RestoreMissingPetsState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.RESTORE_MISSING_PETS_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        owning_household = services.owning_household_of_active_lot()
        if owning_household is not None:
            owning_household.missing_pet_tracker.restore_missing_state()
        return _ZoneSpinUpStateResult.DONE

class _RestoreRabbitHoleState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.RESTORE_RABBIT_HOLES_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        services.get_rabbit_hole_service().restore_rabbit_hole_state()
        return _ZoneSpinUpStateResult.DONE

class _SituationCommonState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.SITUATION_COMMON_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        situation_manager = services.get_zone_situation_manager()
        situation_manager.create_situations_during_zone_spin_up()
        venue_service = services.current_zone().venue_service
        venue_service.create_situations_during_zone_spin_up()
        zone_director = venue_service.get_zone_director()
        if zone_director.open_street_director is not None:
            zone_director.open_street_director.create_situations_during_zone_spin_up()
        services.get_career_service().create_career_event_situations_during_zone_spin_up()
        situation_manager.on_all_situations_created_during_zone_spin_up()
        services.drama_scheduler_service().on_situation_creation_during_zone_spin_up()
        return _ZoneSpinUpStateResult.DONE

class _FixupInventoryState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.FIXUP_INVENTORY_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        for sim_info in services.sim_info_manager().values():
            sim_info.fixup_inventory()
        return _ZoneSpinUpStateResult.DONE

class _DestroyUnclaimedObjectsState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.DESTROY_UNCLAIMED_OBJECTS_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        services.object_manager().destroy_unclaimed_objects()
        return _ZoneSpinUpStateResult.DONE

class _WaitForSimSpawnerService(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.WAIT_FOR_BOUNCER_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        sim_spawner_service = services.sim_spawner_service()
        sim_spawner_service.batch_spawn_during_zone_spin_up()
        return _ZoneSpinUpStateResult.WAITING

    def on_update(self):
        super().on_update()
        if not services.sim_spawner_service().batch_spawning_complete:
            return _ZoneSpinUpStateResult.WAITING
        client = services.client_manager().get_first_client()
        services.sim_info_manager().on_spawn_sim_for_zone_spin_up_completed(client)
        services.venue_service().get_zone_director().on_spawn_sim_for_zone_spin_up_completed()
        services.current_zone().venue_service.handle_active_lot_changing_edge_cases()
        services.get_zone_situation_manager().on_all_sims_spawned_during_zone_spin_up()
        club_service = services.get_club_service()
        if club_service is not None:
            club_service.on_finish_waiting_for_sim_spawner_service()
        else:
            current_zone_id = services.current_zone_id()
            household = services.active_household()
            if household.home_zone_id != current_zone_id:
                sim_info_manager = services.sim_info_manager()
                traveled_sims = sim_info_manager.get_traveled_to_zone_sim_infos()
                if len(traveled_sims) > 1:
                    services.ensemble_service().create_travel_ensemble_if_neccessary(traveled_sims)
        services.ensemble_service().on_all_sims_spawned_during_zone_spin_up()
        return _ZoneSpinUpStateResult.DONE

    def on_exit(self):
        active_household_id = services.active_household_id()
        sim_info_manager = services.sim_info_manager()
        for script_object in sim_info_manager.instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS):
            script_object.finalize(active_household_id=active_household_id)
        super().on_exit()

class _ZoneModifierSpinUpState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.ZONE_MODIFIER_SPIN_UP_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        zone_modifier_service = services.get_zone_modifier_service()
        if zone_modifier_service:
            zone_modifier_service.spin_up()
        return _ZoneSpinUpStateResult.DONE

class _PrerollAutonomyState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.PREROLL_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        caches.skip_cache = False
        sim_info_manager = services.sim_info_manager()
        for sim in sim_info_manager.instanced_sims_gen():
            weather_aware_component = sim.weather_aware_component
            if weather_aware_component is not None:
                weather_aware_component.on_preroll_autonomy()
        sim_info_manager.run_preroll_autonomy()
        return _ZoneSpinUpStateResult.DONE

    def on_exit(self):
        super().on_exit()
        caches.skip_cache = True

class _AwayActionsState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.AWAY_ACTION_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        client = services.client_manager().get_first_client()
        home_zone_id = client.household.home_zone_id
        if home_zone_id == 0:
            return _ZoneSpinUpStateResult.DONE
        zone_manager = services.get_zone_manager()
        loaded_zones = set()
        loaded_zones.add(services.current_zone_id())
        for sim_info in services.sim_info_manager().values():
            if sim_info.is_selectable:
                start_away_actions = True
                sim_zone_id = sim_info.zone_id
                if sim_zone_id == 0:
                    start_away_actions = False
                elif sim_zone_id not in loaded_zones:
                    zone_manager.load_uninstantiated_zone_data(sim_zone_id)
                    loaded_zones.add(sim_zone_id)
                travel_group = sim_info.travel_group
                if travel_group is not None:
                    if travel_group.zone_id == 0:
                        start_away_actions = False
                    elif travel_group.zone_id not in loaded_zones:
                        zone_manager.load_uninstantiated_zone_data(travel_group.zone_id)
                        loaded_zones.add(travel_group.zone_id)
                if sim_info.away_action_tracker is not None:
                    if start_away_actions:
                        if sim_info.away_action_tracker.is_sim_info_valid_to_run_away_actions():
                            sim_info.away_action_tracker.start()
                    else:
                        sim_info.away_action_tracker.stop()
                    if sim_info.away_action_tracker is not None:
                        sim_info.away_action_tracker.stop()
            elif sim_info.away_action_tracker is not None:
                sim_info.away_action_tracker.stop()
        home_zone_id = client.household.home_zone_id
        if home_zone_id not in loaded_zones:
            zone_manager.load_uninstantiated_zone_data(home_zone_id)
        return _ZoneSpinUpStateResult.DONE

class _PushSimsToGoHomeState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.PUSH_SIMS_GO_HOME_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        sim_info_manager = services.sim_info_manager()
        if sim_info_manager:
            sim_info_manager.push_sims_to_go_home()
        return _ZoneSpinUpStateResult.DONE

class _FinalizeObjectsState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.FINALIZE_OBJECT_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        active_household_id = services.active_household_id()
        object_manager = services.object_manager()
        for script_object in tuple(object_manager.get_all()):
            script_object.finalize(active_household_id=active_household_id)
        water_terrain_object_cache = object_manager.water_terrain_object_cache
        water_terrain_object_cache.refresh()
        build_buy.register_build_buy_exit_callback(water_terrain_object_cache.refresh)
        return _ZoneSpinUpStateResult.DONE

class _SetupSurfacePortalsState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.SETUP_PORTALS_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        object_manager = services.object_manager()
        for portal_object in object_manager.portal_cache_gen():
            if portal_object.provided_routing_surface is not None:
                portal_component = portal_object.get_component(PORTAL_COMPONENT)
                portal_component.finalize_portals()
        return _ZoneSpinUpStateResult.DONE

class _SetActiveSimState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.SET_ACTIVE_SIM_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        zone = services.current_zone()
        zone_spin_up_service = zone.zone_spin_up_service
        active_sim_id = zone_spin_up_service._client_connect_data.active_sim_id
        client = zone_spin_up_service._client_connect_data.client
        if active_sim_id and client.set_active_sim_by_id(active_sim_id) or client.active_sim is None:
            client.set_next_sim()
        client.resend_active_sim_info()
        active_household = services.active_household()
        if active_household is not None:
            active_household.on_active_sim_set()
        return _ZoneSpinUpStateResult.DONE

class _ScheduleStartupDramaNodesState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.SCHEDULE_STARTUP_DRAMA_NODES_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        services.drama_scheduler_service().schedule_nodes_on_startup()
        return _ZoneSpinUpStateResult.DONE

class _DestinationWorldCleanUp(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.DESTINATION_WORLD_CLEAN_UP_FAILED

    def on_enter(self):
        super().on_enter()
        travel_group_manager = services.travel_group_manager()
        travel_group_manager.return_objects_left_in_destination_world()
        travel_group_manager.clean_objects_left_in_destination_world()
        return _ZoneSpinUpStateResult.DONE

class _StartupCommandsState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.START_UP_COMMANDS_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        parser = argparse.ArgumentParser()
        parser.add_argument('--on_startup_commands')
        (args, unused_args) = parser.parse_known_args()
        args_dict = vars(args)
        startup_commands_file = args_dict.get('on_startup_commands')
        if not startup_commands_file:
            return _ZoneSpinUpStateResult.DONE
        clients = list(client for client in services.client_manager().values())
        if not clients:
            client_id = 0
        else:
            client_id = clients[0].id
        sims4.command_script.run_script(startup_commands_file, client_id)
        return _ZoneSpinUpStateResult.DONE

class _EditModeSequenceCompleteState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.EDIT_MODE_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        zone = services.current_zone()
        zone.venue_service.build_buy_edit_mode = True
        services.household_manager().load_households()
        zone.on_households_and_sim_infos_loaded()
        client = zone.zone_spin_up_service._client_connect_data.client
        club_service = services.get_club_service()
        if club_service is not None:
            club_service.on_all_households_and_sim_infos_loaded(client)
        relationship_service = services.relationship_service()
        if relationship_service is not None:
            relationship_service.on_all_households_and_sim_infos_loaded(client)
        situation_manager = services.get_zone_situation_manager()
        situation_manager.spin_up_for_edit_mode()
        object_manager = services.object_manager()
        water_terrain_object_cache = object_manager.water_terrain_object_cache
        build_buy.register_build_buy_exit_callback(water_terrain_object_cache.refresh)
        for obj in object_manager.values():
            footprint_component = obj.get_component(FOOTPRINT_COMPONENT)
            if footprint_component is not None:
                footprint_component.on_finalize_load()
        services.game_clock_service().restore_saved_clock_speed()
        return _ZoneSpinUpStateResult.DONE

class _FinalPlayableState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.FINAL_PLAYABLE_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        zone = services.current_zone()
        zone_spin_up_service = zone.zone_spin_up_service
        zone.venue_service.setup_special_event_alarm()
        zone.ambient_service.begin_walkbys()
        client = zone_spin_up_service._client_connect_data.client
        if client is not None:
            with telemetry_helper.begin_hook(zone_telemetry_writer, TELEMETRY_HOOK_ZONE_LOAD, household=client.household) as hook:
                (player_sims, npc_sims) = services.sim_info_manager().get_player_npc_sim_count()
                hook.write_int(TELEMETRY_FIELD_PLAYER_COUNT, player_sims)
                hook.write_int(TELEMETRY_FIELD_NPC_COUNT, npc_sims)
        services.get_persistence_service().try_send_once_per_session_telemetry()
        client.household.telemetry_tracker.initialize_alarms()
        zone_spin_up_service.apply_save_lock()
        return _ZoneSpinUpStateResult.DONE

class _StartNoWaitingState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.START_NO_WAITING_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        zone = services.current_zone()
        zone.zone_spin_up_service.disallow_waiting = True

class _EndNoWaitingState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.END_NO_WAITING_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        zone = services.current_zone()
        zone.zone_spin_up_service.disallow_waiting = False

class _HittingTheirMarksState(_ZoneSpinUpState):

    def __init__(self):
        super().__init__()
        self._countdown = 30

    def exception_error_code(self):
        return ErrorCodes.HITTING_THEIR_MARKS_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        services.game_clock_service().advance_for_hitting_their_marks()
        return _ZoneSpinUpStateResult.WAITING

    def on_update(self):
        super().on_update()
        self._countdown -= 1
        if self._countdown <= 0:
            services.active_lot().on_hit_their_marks()
            services.sim_spawner_service().on_hit_their_marks()
            services.get_zone_situation_manager().on_hit_their_marks_during_zone_spin_up()
            services.current_zone().on_hit_their_marks()
            return _ZoneSpinUpStateResult.DONE
        services.game_clock_service().advance_for_hitting_their_marks()
        return _ZoneSpinUpStateResult.WAITING

class _UpdateObjectivesState(_ZoneSpinUpState):

    def exception_error_code(self):
        return ErrorCodes.UPDATE_OBJECTIVES_STATE_FAILED

    def on_enter(self):
        super().on_enter()
        event_manager = services.get_event_manager()
        event_manager.register_events_for_update()
        client = services.get_first_client()
        client.refresh_achievement_data()
        for sim_info in client.selectable_sims:
            if sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                sim_info.start_aspiration_tracker_on_instantiation()
        event_manager.unregister_unused_handlers()
        event_manager.register_events_for_objectives()
        return _ZoneSpinUpStateResult.DONE
ClientConnectData = collections.namedtuple('ClientConnectData', ['household_id', 'client', 'active_sim_id'])
class ZoneSpinUpService(sims4.service_manager.Service):
    SAVE_LOCK_TOOLTIP = TunableLocalizedString(description='\n            The tooltip/message to show when the player when the game is in the\n            process of finishing up the load and waiting for the loading screen\n            animation finished call to be sent.\n            ')

    def __init__(self):
        self._current_state = None
        self._cur_state_index = -1
        self._client_connect_data = None
        self._status = ZoneSpinUpStatus.CREATED
        self._state_sequence = None
        self.disallow_waiting = False

    def get_lock_save_reason(self):
        return ZoneSpinUpService.SAVE_LOCK_TOOLTIP

    @property
    def _edit_mode_state_sequence(self):
        return (_EditModeSequenceCompleteState,)

    @property
    def _playable_sequence(self):
        return (_StopCaching, _LoadHouseholdsAndSimInfosState, _PremadeSimFixupState, _SimInfoFixupState, _SetupPortalsState, _SelectZoneDirectorState, _DestinationWorldCleanUp, _DetectAndCleanupInvalidObjectsState, _SetObjectOwnershipState, _FinalizeObjectsState, _SetupSurfacePortalsState, _WaitForNavmeshState, _SpawnSimsState, _SituationCommonState, _FixupInventoryState, _DestroyUnclaimedObjectsState, _WaitForSimSpawnerService, _ZoneModifierSpinUpState, _PrepareLotState, _AwayActionsState, _InitializeDoorServiceState, _SetMailboxOwnerState, _StartNoWaitingState, _RestoreRabbitHoleState, _RestoreSIState, _GlobalLotTuningAndCleanupState, _RestoreCareerState, _RestoreMissingPetsState, _PrerollAutonomyState, _PushSimsToGoHomeState, _SetActiveSimState, _ScheduleStartupDramaNodesState, _StartupCommandsState, _StartCaching, _FinalPlayableState, _EndNoWaitingState)

    @property
    def _hitting_their_marks_state_sequence(self):
        return (_HittingTheirMarksState, _UpdateObjectivesState)

    def set_household_id_and_client_and_active_sim_id(self, household_id, client, active_sim_id):
        logger.assert_raise(self._status == ZoneSpinUpStatus.CREATED, 'Attempting to initialize the zone_spin_up_process more than once.', owner='sscholl')
        self._client_connect_data = ClientConnectData(household_id, client, active_sim_id)
        self._status = ZoneSpinUpStatus.INITIALIZED

    def stop(self):
        self.do_clean_up()

    @property
    def is_finished(self):
        return self._status >= ZoneSpinUpStatus.COMPLETED

    @property
    def had_an_error(self):
        return self._status == ZoneSpinUpStatus.ERRORED

    def _start_sequence(self, sequence):
        logger.assert_raise(self._status >= ZoneSpinUpStatus.INITIALIZED, 'Attempting to start the zone_spin_up_process when not initialized.', owner='sscholl')
        self._current_state = None
        self._cur_state_index = -1
        self._status = ZoneSpinUpStatus.SEQUENCED
        self._state_sequence = sequence

    def start_playable_sequence(self):
        self._start_sequence(self._playable_sequence)

    def start_build_mode_sequence(self):
        self._start_sequence(self._edit_mode_state_sequence)

    def start_hitting_their_marks_sequence(self):
        self._start_sequence(self._hitting_their_marks_state_sequence)

    def update(self):
        logger.assert_raise(self._status != ZoneSpinUpStatus.CREATED and self._status != ZoneSpinUpStatus.INITIALIZED, 'Attempting to update the zone_spin_up_process that has not been initialized.', owner='sscholl')
        if self._status >= ZoneSpinUpStatus.COMPLETED:
            return
        if self._status == ZoneSpinUpStatus.SEQUENCED:
            self._status = ZoneSpinUpStatus.RUNNING
        try:
            if self._current_state is not None:
                state_result = self._current_state.on_update()
                if state_result == _ZoneSpinUpStateResult.DONE:
                    self._current_state.on_exit()
            else:
                state_result = _ZoneSpinUpStateResult.DONE
            while state_result == _ZoneSpinUpStateResult.DONE:
                self._cur_state_index += 1
                if self._cur_state_index >= len(self._state_sequence):
                    self._status = ZoneSpinUpStatus.COMPLETED
                    break
                else:
                    self._current_state = self._state_sequence[self._cur_state_index]()
                    state_result = self._current_state.on_enter()
                    if state_result == _ZoneSpinUpStateResult.DONE:
                        self._current_state.on_exit()
                    if state_result == _ZoneSpinUpStateResult.WAITING and self.disallow_waiting:
                        logger.error("State {} is trying to wait when it's not allowed to.", self._current_state, owner='tingyul')
        except Exception as e:
            self._status = ZoneSpinUpStatus.ERRORED
            error_code = self._current_state.exception_error_code()
            dialog = services.persistence_service.PersistenceTuning.LOAD_ERROR_REQUEST_RESTART(services.current_zone())
            if dialog is not None:
                error_string = generate_exception_code(error_code, e)
                dialog.show_dialog(additional_tokens=(error_string,))
            logger.exception('Exception raised while processing zone spin up sequence: {}', e)
            with telemetry_helper.begin_hook(zone_telemetry_writer, TELEMETRY_HOOK_ZONE_FAIL) as hook:
                exception_callstack = generate_exception_callstack(e)
                hook.write_int(TELEMETRY_FIELD_ERROR_CODE, error_code)
                hook.write_int(TELEMETRY_FIELD_STACK_HASH, sims4.hash_util.hash64(exception_callstack))

    def do_clean_up(self):
        self._current_state = None
        self._cur_state_index = -1
        self._client_connect_data = None

    def process_zone_loaded(self):
        services.business_service().process_zone_loaded()

    def apply_save_lock(self):
        services.get_persistence_service().lock_save(self)

    def on_loading_screen_animation_finished(self):
        services.get_persistence_service().unlock_save(self)
