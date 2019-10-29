import timefrom sims4.sim_irq_service import yield_zone_idfrom sims4.utils import exception_protected, c_api_can_failfrom telemetry_helper import TelemetryTuningimport clockimport game_servicesimport indexed_managerimport native.animationimport pathsimport server.accountimport servicesimport sims.sim_spawnerimport sims4.core_servicesimport sims4.geometryimport sims4.gsi.http_serviceimport sims4.logimport sims4.perf_logimport sims4.zone_utilsimport telemetry_helperlogger = sims4.log.Logger('AreaServer', default_owner='manus')status = sims4.log.Logger('Status', default_owner='manus')service_perf_logger = sims4.perf_log.get_logger('ServicePerf', default_owner='pingebretson')SYSTEM_HOUSEHOLD_ID = 1WORLDBUILDER_ZONE_ID = 1SUCCESS_CODE = 0EXCEPTION_ERROR_CODE = -1TIMEOUT_ERROR_CODE = -2NO_ACCOUNT_ERROR_CODE = -3NO_CLIENT_ERROR_CODE = -4NO_HOUSEHOLD_ERROR_CODE = -5LOADSIMS_FAILED_ERROR_CODE = -6SIM_NOT_FOUND_ERROR_CODE = -7CLIENT_DISCONNECTED_ERROR_CODE = -8TELEMETRY_GROUP_AREA = 'AREA'TELEMETRY_HOOK_ZONE_EXIT = 'EXIT'TELEMETRY_FIELD_NPC_COUNT = 'npcc'TELEMETRY_FIELD_PLAYER_COUNT = 'plyc'area_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_AREA)
class synchronous(object):
    __slots__ = ('callback_index', 'zone_id_index', 'session_id_index')

    def __init__(self, callback_index=None, zone_id_index=None, session_id_index=None):
        self.callback_index = callback_index
        self.zone_id_index = zone_id_index
        self.session_id_index = session_id_index

    def __call__(self, fn):

        def wrapped(*args, **kwargs):

            def run_callback(ret):
                if self.callback_index is not None:
                    finally_fn = args[self.callback_index]
                    if self.zone_id_index is not None:
                        if self.session_id_index is not None:
                            finally_fn(args[self.zone_id_index], args[self.session_id_index], ret)
                        else:
                            finally_fn(args[self.zone_id_index], ret)
                    else:
                        finally_fn(ret)

            def finally_wrap(*args, **kwargs):
                ret = EXCEPTION_ERROR_CODE
                try:
                    ret = fn(*args, **kwargs)
                finally:
                    run_callback(ret)

            finally_wrap(*args, **kwargs)
            return SUCCESS_CODE

        return wrapped

@exception_protected(log_invoke=True)
def c_api_server_init(initial_ticks):
    services.start_global_services(initial_ticks)
    native.animation.enable_native_reaction_event_handling(False)
    sims4.geometry.PolygonFootprint.set_global_enabled(True)
    status.info('c_api_server_init: Server initialized')
    return SUCCESS_CODE

@exception_protected
def c_api_server_init_tick():
    return sims4.core_services.start_service_tick()

@exception_protected(default_return=EXCEPTION_ERROR_CODE)
def c_api_server_ready():
    if paths.DEBUG_AVAILABLE:
        try:
            import pydevd
            pydevd.on_break_point_hook = clock.on_break_point_hook
        except ImportError:
            logger.exception('Unable to initialize gameplay components of the PyDev debugger due to exception.')
    return SUCCESS_CODE

@exception_protected
def c_api_server_tick(absolute_ticks):
    sims4.core_services.on_tick()
    game_services.on_tick()
    clock_service = services.server_clock_service()
    previous_ticks = clock_service.ticks()
    if absolute_ticks < previous_ticks:
        absolute_ticks = previous_ticks
    clock_service.tick_server_clock(absolute_ticks)
    if services._zone_manager is not None:
        zone = services._zone_manager.current_zone
        if zone is not None and zone.is_instantiated:
            persistence_service = services.get_persistence_service()
            if persistence_service is not None and persistence_service.save_timeline:
                persistence_service.save_timeline.simulate(services.time_service().sim_now)
                return SUCCESS_CODE
            zone.update(absolute_ticks)
    services.get_distributor_service().on_tick()
    return SUCCESS_CODE

@synchronous(callback_index=0)
@exception_protected(log_invoke=True)
def c_api_server_shutdown(callback):
    sims4.gsi.http_service.stop_http_server()
    services.stop_global_services()
    status.info('c_api_server_shutdown: Server shutdown')
    return SUCCESS_CODE

@c_api_can_fail()
@exception_protected(default_return=EXCEPTION_ERROR_CODE, log_invoke=True)
def c_api_zone_init(zone_id, world_id, world_file, set_game_time_callback, gameplay_zone_data_bytes=None, save_slot_data_bytes=None):
    persistence_service = services.get_persistence_service()
    persistence_service.build_caches()
    zone_data_proto = persistence_service.get_zone_proto_buff(zone_id)
    if zone_data_proto is not None:
        gameplay_zone_data = zone_data_proto.gameplay_zone_data
    save_slot_data = persistence_service.get_save_slot_proto_buff()
    game_services.start_services(save_slot_data)
    zone = services._zone_manager.create_zone(zone_id, gameplay_zone_data, save_slot_data)
    zone.world_id = world_id
    sims4.zone_utils.set_current_zone_id(zone_id)
    zone.start_services(gameplay_zone_data, save_slot_data)
    zone_number = sims4.zone_utils.zone_numbers[zone_id]
    status.info('Zone {:#08x} (Zone #{}) initialized'.format(zone_id, zone_number))
    zone = services._zone_manager.get(zone_id)
    game_clock_service = services.game_clock_service()
    game_clock_service.set_game_time_callback = set_game_time_callback
    return SUCCESS_CODE

@synchronous(callback_index=1, zone_id_index=0)
@c_api_can_fail(error_return_values=(EXCEPTION_ERROR_CODE, TIMEOUT_ERROR_CODE, LOADSIMS_FAILED_ERROR_CODE))
@exception_protected(default_return=EXCEPTION_ERROR_CODE, log_invoke=True)
def c_api_zone_loaded(zone_id, callback):
    zone = services._zone_manager.get(zone_id)
    zone.on_objects_loaded()
    zone.load_zone()
    zone.zone_spin_up_service.process_zone_loaded()
    status.info('Zone {:#08x} loaded'.format(zone_id))
    return SUCCESS_CODE

@synchronous(callback_index=1, zone_id_index=0)
@c_api_can_fail(error_return_values=(EXCEPTION_ERROR_CODE, TIMEOUT_ERROR_CODE))
@exception_protected(default_return=EXCEPTION_ERROR_CODE, log_invoke=True)
def c_api_zone_shutdown(zone_id, callback):
    try:
        services._zone_manager.cleanup_uninstantiated_zones()
        services._zone_manager.remove_id(zone_id)
        game_services.stop_services()
    finally:
        status.info('Zone {:#08x} shutdown'.format(zone_id))
    sims4.zone_utils.set_current_zone_id(None)
    service_perf_logger.debug('Zone shutdown complete')
    return SUCCESS_CODE

@synchronous(callback_index=5, zone_id_index=4, session_id_index=0)
@c_api_can_fail(error_return_values=(EXCEPTION_ERROR_CODE, TIMEOUT_ERROR_CODE, NO_HOUSEHOLD_ERROR_CODE, SIM_NOT_FOUND_ERROR_CODE))
@exception_protected(default_return=EXCEPTION_ERROR_CODE, log_invoke=True)
def c_api_client_connect(session_id, account_id, household_id, persona_name, zone_id, callback, active_sim_id, locale='none', edit_lot_mode=False):
    account = services.account_service().get_account_by_id(account_id, try_load_account=True)
    if account is None:
        account = server.account.Account(account_id, persona_name)
    account.locale = locale
    TelemetryTuning.filter_tunable_hooks()
    zone = services.current_zone()
    client = services.client_manager().create_client(session_id, account, household_id)
    zone.on_client_connect(client)
    services.on_client_connect(client)
    yield_zone_id(services.current_zone_id())
    if client.household_id == SYSTEM_HOUSEHOLD_ID and not edit_lot_mode:
        status.info('Successful client connect in World Builder mode.')
        services.game_clock_service().restore_saved_clock_speed()
        return NO_HOUSEHOLD_ERROR_CODE
    else:
        spin_up_mode = 'BuildModeZoneSpinUp' if edit_lot_mode else 'FullZoneSpinUp'
        status.info('Client {:#08x} ({}) connected to zone {:#08x}. Mode: {}.', session_id, persona_name, zone_id, spin_up_mode)
        time_stamp = time.time()
        if edit_lot_mode:
            result = zone.do_build_mode_zone_spin_up(household_id)
        else:
            result = zone.do_zone_spin_up(household_id, active_sim_id)
        object_leak_tracker = services.get_object_leak_tracker()
        if object_leak_tracker is not None:
            object_leak_tracker.register_gc_callback()
        time_stamp = time.time() - time_stamp
        status.info('Completed {} with result {}. Total Time: {:0.02f} seconds.', spin_up_mode, result, time_stamp)
        if indexed_manager.capture_load_times:
            indexed_manager.object_load_times['lot_load'] = time_stamp
        service_perf_logger.debug('Zone startup complete')
        game_services.enable_shutdown()
        if not result:
            return EXCEPTION_ERROR_CODE
    return SUCCESS_CODE

@synchronous(callback_index=2, zone_id_index=1, session_id_index=0)
@c_api_can_fail(error_return_values=(EXCEPTION_ERROR_CODE, TIMEOUT_ERROR_CODE))
@exception_protected(default_return=EXCEPTION_ERROR_CODE, log_invoke=True)
def c_api_client_disconnect(session_id, zone_id, callback):
    logger.info('Client {0} disconnected in zone {1}', session_id, zone_id)
    status.info('Client {:#08x} disconnected from zone {:#08x}'.format(session_id, zone_id))
    return SUCCESS_CODE

def c_api_request_client_disconnect(session_id, zone_id, callback, is_traveling=False):
    service_perf_logger.debug('Request disconnect, travel = {}', 'True' if is_traveling else 'False')
    if is_traveling:
        game_services.disable_shutdown()

    def request_client_disconnect_gen(timeline):
        try:
            zone = services.current_zone()
            if zone is not None:
                client_manager = services.client_manager()
                client = client_manager.get(session_id)
                logger.info('Client {0} starting save of zone {1}', session_id, zone_id)
                yield from services.get_persistence_service().save_to_scratch_slot_gen(timeline)
                logger.info('Client {0} save completed for {1}', session_id, zone_id)
                with telemetry_helper.begin_hook(area_telemetry_writer, TELEMETRY_HOOK_ZONE_EXIT, household=client.household) as hook:
                    (player_sims, npc_sims) = services.sim_info_manager().get_player_npc_sim_count()
                    hook.write_int(TELEMETRY_FIELD_PLAYER_COUNT, player_sims)
                    hook.write_int(TELEMETRY_FIELD_NPC_COUNT, npc_sims)
                zone.on_teardown(client)
                if client is None:
                    logger.error('Client {0} not in client manager from zone {1}', session_id, zone_id)
                    return callback(zone_id, session_id, NO_CLIENT_ERROR_CODE)
                client_manager.remove(client)
            return callback(zone_id, session_id, SUCCESS_CODE)
        except:
            logger.exception('Error disconnecting the client')
            return callback(zone_id, session_id, EXCEPTION_ERROR_CODE)

    logger.info('Client {0} requesting disconnect in zone {1}', session_id, zone_id)
    if zone_id == WORLDBUILDER_ZONE_ID:
        callback(zone_id, session_id, SUCCESS_CODE)
        return SUCCESS_CODE
    persistence_service = services.get_persistence_service()
    persistence_service.save_using(request_client_disconnect_gen)
    return SUCCESS_CODE

@synchronous(callback_index=3, zone_id_index=1, session_id_index=0)
@c_api_can_fail(error_return_values=(EXCEPTION_ERROR_CODE, TIMEOUT_ERROR_CODE, LOADSIMS_FAILED_ERROR_CODE))
@exception_protected(default_return=EXCEPTION_ERROR_CODE, log_invoke=True)
def c_api_add_sims(session_id, zone_id, sim_ids, callback, add_to_skewer):
    zone = services._zone_manager.get(zone_id)
    if zone is None:
        return LOADSIMS_FAILED_ERROR_CODE
    client = services.client_manager().get(session_id)
    if client is None:
        services.sim_info_manager().add_sims_to_zone(sim_ids)
        return SUCCESS_CODE
    object_manager = services.object_manager()
    for sim_id in sim_ids:
        if sim_id in object_manager:
            logger.error('Attempt to add a sim who is already in the zone.  Native likely has a logic error.')
        else:
            ret = sims.sim_spawner.SimSpawner.load_sim(sim_id)
            if not ret:
                logger.error('Sim failed to load while spinning up sim_id: {}.', sim_id)
                return LOADSIMS_FAILED_ERROR_CODE
    if add_to_skewer:
        for sim_id in sim_ids:
            sim_info = services.sim_info_manager().get(sim_id)
            if sim_info is not None and client.household_id == sim_info.household_id:
                client.add_selectable_sim_info(sim_info)
    return SUCCESS_CODE

@exception_protected
def c_api_notify_client_in_main_menu():
    logger.info('client in main menu')
    services.on_enter_main_menu()

@exception_protected
def c_api_setup_sim_spawner_data(zone_id, locator_data):
    locator_manager = services.locator_manager()
    locator_manager.set_up_locators(locator_data)
    return SUCCESS_CODE

@c_api_can_fail()
@exception_protected(default_return=0)
def c_api_get_household_funds(zone_id, household_id):
    business_manager = services.business_service().get_business_manager_for_zone(zone_id)
    if business_manager is not None and business_manager.is_household_owner(household_id):
        return business_manager.funds.money
    else:
        household = services.household_manager().get(household_id)
        if household is not None:
            return household.funds.money
    return SUCCESS_CODE

@c_api_can_fail()
@exception_protected(default_return=0)
def c_api_get_simulator_debt():
    time_service = services.time_service()
    if time_service is None or time_service.sim_timeline is None:
        return 0
    delta = time_service.sim_future - time_service.sim_now
    return delta.in_minutes()
