import argparseimport functoolsimport gcimport timefrom services.tuning_managers import InstanceTuningManagersfrom sims4.resources import INSTANCE_TUNING_DEFINITIONSfrom sims4.tuning.instance_manager import TuningInstanceManagerfrom sims4.tuning.tunable import Tunable, TunableReferenceimport game_servicesimport pathsimport sims4.reloadimport sims4.service_managertry:
    import _zone
except ImportError:

    class _zone:

        @staticmethod
        def invite_sims_to_zone(*_, **__):
            pass

        @staticmethod
        def get_house_description_id(*_, **__):
            pass

        @staticmethod
        def get_building_type(*_, **__):
            return 0

        @staticmethod
        def get_rent(*_, **__):
            return 0

        @staticmethod
        def get_lot_description_id(*_, **__):
            pass

        @staticmethod
        def get_world_description_id(*_, **__):
            pass

        @staticmethod
        def get_world_id(*_, **__):
            pass

        @staticmethod
        def get_world_and_lot_description_id_from_zone_id(*_, **__):
            pass

        @staticmethod
        def get_hide_from_lot_picker(*_, **__):
            pass

        @staticmethod
        def is_event_enabled(*_, **__):
            pass
invite_sims_to_zone = _zone.invite_sims_to_zoneget_house_description_id = _zone.get_house_description_idis_event_enabled = _zone.is_event_enabledget_building_type = _zone.get_building_typeget_rent = _zone.get_rentget_lot_description_id = _zone.get_lot_description_idget_world_description_id = _zone.get_world_description_idget_world_id = _zone.get_world_idget_world_and_lot_description_id_from_zone_id = _zone.get_world_and_lot_description_id_from_zone_idget_hide_from_lot_picker = _zone.get_hide_from_lot_pickerwith sims4.reload.protected(globals()):
    tuning_managers = InstanceTuningManagers()
    get_instance_manager = tuning_managers.__getitem__
    _account_service = None
    _zone_manager = None
    _server_clock_service = None
    _persistence_service = None
    _distributor_service = None
    _intern_service = None
    definition_manager = None
    snippet_manager = None
    _terrain_object = None
    _object_leak_tracker = Nonefor definition in INSTANCE_TUNING_DEFINITIONS:
    accessor_name = definition.manager_name
    accessor = functools.partial(tuning_managers.__getitem__, definition.TYPE_ENUM_VALUE)
    globals()[accessor_name] = accessorproduction_logger = sims4.log.ProductionLogger('Services')logger = sims4.log.Logger('Services')time_delta = Nonegc_collection_enable = True
class TimeStampService(sims4.service_manager.Service):

    def start(self):
        global gc_collection_enable, time_delta
        if gc_collection_enable:
            gc.disable()
            production_logger.info('GC disabled')
            gc_collection_enable = False
        else:
            gc.enable()
            production_logger.info('GC enabled')
            gc_collection_enable = True
        time_stamp = time.time()
        production_logger.info('TimeStampService start at {}'.format(time_stamp))
        logger.info('TimeStampService start at {}'.format(time_stamp))
        if time_delta is None:
            time_delta = time_stamp
        else:
            time_delta = time_stamp - time_delta
            production_logger.info('Time delta from loading start is {}'.format(time_delta))
            logger.info('Time delta from loading start is {}'.format(time_delta))
        return True

def start_global_services(initial_ticks):
    global _account_service, _zone_manager, _distributor_service, _intern_service
    create_server_clock(initial_ticks)
    from distributor.distributor_service import DistributorService
    from intern_service import InternService
    from server.account_service import AccountService
    from services.persistence_service import PersistenceService
    from services.terrain_service import TerrainService
    from sims4.tuning.serialization import FinalizeTuningService
    from zone_manager import ZoneManager
    parser = argparse.ArgumentParser()
    parser.add_argument('--python_autoleak', default=False, action='store_true')
    (args, unused_args) = parser.parse_known_args()
    if args.python_autoleak:
        create_object_leak_tracker()
    _account_service = AccountService()
    _zone_manager = ZoneManager()
    _distributor_service = DistributorService()
    _intern_service = InternService()
    init_critical_services = [server_clock_service(), get_persistence_service()]
    services = [_distributor_service, _intern_service, _intern_service.get_start_interning(), TimeStampService]
    instantiated_tuning_managers = []
    for definition in INSTANCE_TUNING_DEFINITIONS:
        instantiated_tuning_managers.append(tuning_managers[definition.TYPE_ENUM_VALUE])
    services.append(TuningInstanceManager(instantiated_tuning_managers))
    services.extend([FinalizeTuningService, TimeStampService, _intern_service.get_stop_interning(), TerrainService, _zone_manager, _account_service])
    sims4.core_services.start_services(init_critical_services, services)

def stop_global_services():
    global _zone_manager, _account_service, _event_manager, _server_clock_service, _persistence_service, _distributor_service, _intern_service, _object_leak_tracker
    _zone_manager.shutdown()
    _zone_manager = None
    tuning_managers.clear()
    _account_service = None
    _event_manager = None
    _server_clock_service = None
    _persistence_service = None
    _distributor_service = None
    _intern_service = None
    if _object_leak_tracker is not None:
        _object_leak_tracker = None

def create_object_leak_tracker(start=False):
    global _object_leak_tracker
    from performance.object_leak_tracker import ObjectLeakTracker
    if _object_leak_tracker is None:
        _object_leak_tracker = ObjectLeakTracker()
        if start:
            _object_leak_tracker.start_tracking()
        return True
    return False

def get_object_leak_tracker():
    return _object_leak_tracker

def get_zone_manager():
    return _zone_manager

def current_zone():
    if _zone_manager is not None:
        return _zone_manager.current_zone

def current_zone_id():
    if _zone_manager is not None:
        return sims4.zone_utils.zone_id

def current_zone_info():
    zone = current_zone()
    return zone.get_zone_info()

def current_region():
    zone = current_zone()
    if zone is not None:
        return zone.region

def current_street():
    zone = current_zone()
    if zone is not None:
        return zone.street

def get_zone(zone_id, allow_uninstantiated_zones=False):
    if _zone_manager is not None:
        return _zone_manager.get(zone_id, allow_uninstantiated_zones=allow_uninstantiated_zones)

def active_lot():
    zone = current_zone()
    if zone is not None:
        return zone.lot

def active_lot_id():
    lot = active_lot()
    if lot is not None:
        return lot.lot_id

def client_object_managers():
    if game_services.service_manager is not None:
        return game_services.service_manager.client_object_managers
    return ()

def sim_info_manager():
    return game_services.service_manager.sim_info_manager

def posture_graph_service(zone_id=None):
    if zone_id is None:
        zone = current_zone()
        if zone is not None:
            return zone.posture_graph_service
        return
    return _zone_manager.get(zone_id).posture_graph_service

def sim_spawner_service(zone_id=None):
    if zone_id is None:
        return current_zone().sim_spawner_service
    return _zone_manager.get(zone_id).sim_spawner_service

def locator_manager():
    return current_zone().locator_manager

def object_manager(zone_id=None):
    if zone_id is None:
        zone = current_zone()
        if zone is not None:
            return zone.object_manager
        return
    return _zone_manager.get(zone_id).object_manager

def inventory_manager(zone_id=None):
    if zone_id is None:
        zone = current_zone()
        if zone is not None:
            return zone.inventory_manager
        return
    return _zone_manager.get(zone_id).inventory_manager

def prop_manager(zone_id=None):
    if zone_id is None:
        zone = current_zone()
    else:
        zone = _zone_manager.get(zone_id)
    if zone is not None:
        return zone.prop_manager

def social_group_manager():
    return current_zone().social_group_manager

def client_manager():
    return game_services.service_manager.client_manager

def get_first_client():
    return client_manager().get_first_client()

def get_selectable_sims():
    return get_first_client().selectable_sims

def owning_household_id_of_active_lot():
    zone = current_zone()
    if zone is not None:
        return zone.lot.owner_household_id

def owning_household_of_active_lot():
    zone = current_zone()
    if zone is not None:
        return household_manager().get(zone.lot.owner_household_id)

def get_active_sim():
    client = client_manager().get_first_client()
    if client is not None:
        return client.active_sim

def active_sim_info():
    client = client_manager().get_first_client()
    if client is not None:
        return client.active_sim_info

def active_household():
    client = client_manager().get_first_client()
    if client is not None:
        return client.household

def active_household_id():
    client = client_manager().get_first_client()
    if client is not None:
        return client.household_id

def active_household_lot_id():
    household = active_household()
    if household is not None:
        home_zone = get_zone(household.home_zone_id)
        if home_zone is not None:
            lot = home_zone.lot
            if lot is not None:
                return lot.lot_id

def privacy_service():
    return current_zone().privacy_service

def autonomy_service():
    return current_zone().autonomy_service

def get_aging_service():
    return game_services.service_manager.aging_service

def get_cheat_service():
    return game_services.service_manager.cheat_service

def neighborhood_population_service():
    return current_zone().neighborhood_population_service

def get_reset_and_delete_service():
    return current_zone().reset_and_delete_service

def venue_service():
    return current_zone().venue_service

def zone_spin_up_service():
    return current_zone().zone_spin_up_service

def household_manager():
    return game_services.service_manager.household_manager

def travel_group_manager(zone_id=None):
    if zone_id is None:
        zone = current_zone()
        if zone is not None:
            return zone.travel_group_manager
        return
    return _zone_manager.get(zone_id).travel_group_manager

def utilities_manager(household_id):
    _utilities_manager = game_services.service_manager.utilities_manager
    return _utilities_manager.get_manager_for_household(household_id)

def ui_dialog_service():
    return current_zone().ui_dialog_service

def config_service():
    return game_services.service_manager.config_service

def travel_service():
    return current_zone().travel_service

def sim_quadtree():
    return current_zone().sim_quadtree

def single_part_condition_list():
    return current_zone().single_part_condition_list

def multi_part_condition_list():
    return current_zone().multi_part_condition_list

def get_event_manager():
    return game_services.service_manager.event_manager_service

def get_current_venue():
    service = venue_service()
    if service is not None:
        return service.venue

def get_intern_service():
    return _intern_service

def get_zone_situation_manager(zone_id=None):
    if zone_id is None:
        return current_zone().situation_manager
    return _zone_manager.get(zone_id).situation_manager

def npc_hosted_situation_service():
    return current_zone().n_p_c_hosted_situation_service

def ensemble_service():
    return current_zone().ensemble_service

def sim_filter_service(zone_id=None):
    if zone_id is None:
        return current_zone().sim_filter_service
    return _zone_manager.get(zone_id).sim_filter_service

def get_photography_service():
    return current_zone().photography_service

def social_group_cluster_service():
    return current_zone().social_group_cluster_service

def on_client_connect(client):
    sims4.core_services.service_manager.on_client_connect(client)
    game_services.service_manager.on_client_connect(client)
    current_zone().service_manager.on_client_connect(client)

def on_client_disconnect(client):
    sims4.core_services.service_manager.on_client_disconnect(client)
    if game_services.service_manager.allow_shutdown:
        game_services.service_manager.on_client_disconnect(client)
    current_zone().service_manager.on_client_disconnect(client)

def on_enter_main_menu():
    pass

def account_service():
    return _account_service

def business_service():
    bs = game_services.service_manager.business_service
    return bs

def call_to_action_service():
    return game_services.service_manager.call_to_action_service

def trend_service():
    return game_services.service_manager.trend_service

def time_service():
    return game_services.service_manager.time_service

def game_clock_service():
    return game_services.service_manager.game_clock

def server_clock_service():
    if _server_clock_service is None:
        return
    return _server_clock_service

def create_server_clock(initial_ticks):
    global _server_clock_service
    import clock
    _server_clock_service = clock.ServerClock(ticks=initial_ticks)

def get_master_controller():
    return current_zone().master_controller

def get_persistence_service():
    global _persistence_service
    if _persistence_service is None:
        from services.persistence_service import PersistenceService
        _persistence_service = PersistenceService()
    return _persistence_service

def get_distributor_service():
    return _distributor_service

def get_fire_service():
    return current_zone().fire_service

def get_career_service():
    return current_zone().career_service

def get_story_progression_service():
    return current_zone().story_progression_service

def daycare_service():
    zone = current_zone()
    if zone is not None:
        return zone.daycare_service

def get_adoption_service():
    return current_zone().adoption_service

def get_laundry_service():
    zone = current_zone()
    if zone is not None and hasattr(zone, 'laundry_service'):
        return zone.laundry_service

def get_landlord_service():
    return getattr(game_services.service_manager, 'landlord_service', None)

def get_club_service():
    return getattr(game_services.service_manager, 'club_service', None)

def get_culling_service():
    return current_zone().culling_service

def get_gardening_service():
    return current_zone().gardening_service

def drama_scheduler_service():
    return current_zone().drama_schedule_service

def get_plex_service():
    return current_zone().plex_service

def get_door_service():
    return current_zone().door_service

def get_zone_modifier_service():
    return current_zone().zone_modifier_service

def get_demographics_service():
    return current_zone().demographics_service

def get_service_npc_service():
    return current_zone().service_npc_service

def conditional_layer_service():
    return current_zone().conditional_layer_service

def get_sickness_service():
    return game_services.service_manager.sickness_service

def get_curfew_service():
    return game_services.service_manager.curfew_service

def get_locale():
    client = get_first_client()
    return client.account.locale

def relationship_service():
    return game_services.service_manager.relationship_service

def hidden_sim_service():
    return game_services.service_manager.hidden_sim_service

def weather_service():
    return getattr(game_services.service_manager, 'weather_service', None)

def season_service():
    return getattr(game_services.service_manager, 'season_service', None)

def lot_decoration_service():
    return getattr(game_services.service_manager, 'lot_decoration_service', None)

def get_style_service():
    return game_services.service_manager.style_service

def get_tutorial_service():
    return game_services.service_manager.tutorial_service

def calendar_service():
    return current_zone().calendar_service

def get_rabbit_hole_service():
    return game_services.service_manager.rabbit_hole_service

def holiday_service():
    return getattr(game_services.service_manager, 'holiday_service', None)

def global_policy_service():
    return getattr(game_services.service_manager, 'global_policy_service', None)

def narrative_service():
    return getattr(game_services.service_manager, 'narrative_service', None)

def get_object_lost_and_found_service():
    return game_services.service_manager.object_lost_and_found_service

def c_api_gsi_dump():
    import server_commands.developer_commands
    server_commands.developer_commands.gsi_dump()
