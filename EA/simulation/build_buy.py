from contextlib import contextmanagerfrom objects import ALL_HIDDEN_REASONSfrom sims4.callback_utils import CallableListfrom sims4.log import Loggerimport enumimport id_generatorimport protocolbuffers.FileSerialization_pb2 as file_serializationimport pythonutilsimport routingimport servicesimport sims4.reloadimport sims4.utilswith sims4.reload.protected(globals()):
    _build_buy_enter_callbacks = CallableList()
    _build_buy_exit_callbacks = CallableList()
class ObjectOriginLocation(enum.Int, export=False):
    UNKNOWN = 0
    ON_LOT = 1
    SIM_INVENTORY = 2
    HOUSEHOLD_INVENTORY = 3
    OBJECT_INVENTORY = 4
    LANDING_STRIP = 5

class FloorFeatureType(enum.Int):
    BURNT = 0
    LEAF = 1
try:
    import _buildbuy
except ImportError:

    class _buildbuy:

        @staticmethod
        def get_wall_contours(*_, **__):
            return []

        @staticmethod
        def add_object_to_buildbuy_system(*_, **__):
            pass

        @staticmethod
        def remove_object_from_buildbuy_system(*_, **__):
            pass

        @staticmethod
        def invalidate_object_location(*_, **__):
            pass

        @staticmethod
        def get_stair_count(*_, **__):
            pass

        @staticmethod
        def update_object_attributes(*_, **__):
            pass

        @staticmethod
        def test_location_for_object(*_, **__):
            pass

        @staticmethod
        def has_floor_at_location(*_, **__):
            pass

        @staticmethod
        def is_location_outside(*_, **__):
            return True

        @staticmethod
        def is_location_natural_ground(*_, **__):
            return True

        @staticmethod
        def is_location_pool(*_, **__):
            return True

        @staticmethod
        def get_pool_edges(*_, **__):
            return True

        @staticmethod
        def get_pool_size_at_location(*_, **__):
            pass

        @staticmethod
        def get_all_block_polygons(*_, **__):
            pass

        @staticmethod
        def get_object_slotset(*_, **__):
            pass

        @staticmethod
        def get_object_placement_flags(*_, **__):
            pass

        @staticmethod
        def get_object_buy_category_flags(*_, **__):
            pass

        @staticmethod
        def get_block_id(*_, **__):
            pass

        @staticmethod
        def get_user_in_bb(*_, **__):
            pass

        @staticmethod
        def init_bb_force_exit(*_, **__):
            pass

        @staticmethod
        def bb_force_exit(*_, **__):
            pass

        @staticmethod
        def get_object_decosize(*_, **__):
            pass

        @staticmethod
        def get_object_catalog_name(*_, **__):
            pass

        @staticmethod
        def get_object_catalog_description(*_, **__):
            pass

        @staticmethod
        def get_object_is_deletable(*_, **__):
            pass

        @staticmethod
        def get_object_can_depreciate(*_, **__):
            pass

        @staticmethod
        def get_household_inventory_value(*_, **__):
            pass

        @staticmethod
        def get_object_has_tag(*_, **__):
            pass

        @staticmethod
        def get_object_all_tags(*_, **__):
            pass

        @staticmethod
        def get_pool_polys(*_, **__):
            pass

        @staticmethod
        def get_current_venue(*_, **__):
            pass

        @staticmethod
        def get_current_venue_config(*_, **__):
            pass

        @staticmethod
        def update_gameplay_unlocked_products(*_, **__):
            pass

        @staticmethod
        def has_floor_feature(*_, **__):
            pass

        @staticmethod
        def get_floor_feature(*_, **__):
            pass

        @staticmethod
        def set_floor_feature(*_, **__):
            pass

        @staticmethod
        def begin_update_floor_features(*_, **__):
            pass

        @staticmethod
        def end_update_floor_features(*_, **__):
            pass

        @staticmethod
        def find_floor_feature(*_, **__):
            pass

        @staticmethod
        def list_floor_features(*_, **__):
            pass

        @staticmethod
        def scan_floor_features(*_, **__):
            pass

        @staticmethod
        def get_variant_group_id(*_, **__):
            pass

        @staticmethod
        def get_vetted_object_defn_guid(zone_id, obj_id, definition_id):
            return definition_id

        @staticmethod
        def get_replacement_object(*_, **__):
            pass

        @staticmethod
        def is_household_inventory_available(household_id):
            return True

        @staticmethod
        def get_lowest_level_allowed(*_, **__):
            return -2

        @staticmethod
        def get_highest_level_allowed(*_, **__):
            return 4

        @staticmethod
        def get_object_pack_by_key(*_, **__):
            return 0

        @staticmethod
        def load_conditional_objects(*_, **__):
            return (True, tuple())

        @staticmethod
        def mark_conditional_objects_loaded(*_, **__):
            pass

        @staticmethod
        def set_client_conditional_layer_active(*_, **__):
            pass

        @staticmethod
        def get_location_plex_id(*_, **__):
            pass

        @staticmethod
        def get_plex_outline(*_, **__):
            pass

        @staticmethod
        def set_plex_visibility(*_, **__):
            pass

        @staticmethod
        def request_season_weather_interpolation(*_, **__):
            pass

        @staticmethod
        def set_active_lot_decoration(*_, **__):
            pass

        @staticmethod
        def get_active_lot_decoration(*_, **__):
            pass
logger = Logger('BuildBuy')
def remove_floor_feature(ff_type, pos, surface):
    zone_id = services.current_zone_id()
    set_floor_feature(zone_id, ff_type, pos, surface, 0)

def remove_object_from_buildbuy_system(obj_id, zone_id, persist=True):
    _buildbuy.remove_object_from_buildbuy_system(obj_id, zone_id, persist)
get_wall_contours = _buildbuy.get_wall_contoursadd_object_to_buildbuy_system = _buildbuy.add_object_to_buildbuy_systeminvalidate_object_location = _buildbuy.invalidate_object_locationget_stair_count = _buildbuy.get_stair_countupdate_object_attributes = _buildbuy.update_object_attributestest_location_for_object = _buildbuy.test_location_for_objecthas_floor_at_location = _buildbuy.has_floor_at_locationis_location_outside = _buildbuy.is_location_outsideis_location_natural_ground = _buildbuy.is_location_natural_groundis_location_pool = _buildbuy.is_location_poolget_pool_size_at_location = _buildbuy.get_pool_size_at_locationget_pool_edges = _buildbuy.get_pool_edgesget_all_block_polygons = _buildbuy.get_all_block_polygonsget_object_slotset = _buildbuy.get_object_slotsetget_block_id = _buildbuy.get_block_idget_user_in_build_buy = _buildbuy.get_user_in_bbinit_build_buy_force_exit = _buildbuy.init_bb_force_exitbuild_buy_force_exit = _buildbuy.bb_force_exitget_object_decosize = _buildbuy.get_object_decosizeget_object_catalog_name = _buildbuy.get_object_catalog_nameget_object_catalog_description = _buildbuy.get_object_catalog_descriptionget_object_is_deletable = _buildbuy.get_object_is_deletableget_object_can_depreciate = _buildbuy.get_object_can_depreciateget_household_inventory_value = _buildbuy.get_household_inventory_valueget_object_has_tag = _buildbuy.get_object_has_tagget_object_all_tags = _buildbuy.get_object_all_tagsget_pool_polys = _buildbuy.get_pool_polysget_current_venue_config = _buildbuy.get_current_venue_configupdate_gameplay_unlocked_products = _buildbuy.update_gameplay_unlocked_productshas_floor_feature = _buildbuy.has_floor_featureget_floor_feature = _buildbuy.get_floor_featureset_floor_feature = _buildbuy.set_floor_featurebegin_update_floor_features = _buildbuy.begin_update_floor_featuresend_update_floor_features = _buildbuy.end_update_floor_featuresfind_floor_feature = _buildbuy.find_floor_featurelist_floor_features = _buildbuy.list_floor_featuresscan_floor_features = _buildbuy.scan_floor_featuresget_vetted_object_defn_guid = _buildbuy.get_vetted_object_defn_guidget_replacement_object = _buildbuy.get_replacement_objectget_lowest_level_allowed = _buildbuy.get_lowest_level_allowedget_highest_level_allowed = _buildbuy.get_highest_level_allowedget_object_pack_by_key = _buildbuy.get_object_pack_by_keyload_conditional_objects = _buildbuy.load_conditional_objectsmark_conditional_objects_loaded = _buildbuy.mark_conditional_objects_loadedset_client_conditional_layer_active = _buildbuy.set_client_conditional_layer_activeget_variant_group_id = _buildbuy.get_variant_group_idis_household_inventory_available = _buildbuy.is_household_inventory_availableget_location_plex_id = _buildbuy.get_location_plex_idget_plex_outline = _buildbuy.get_plex_outlineset_plex_visibility = _buildbuy.set_plex_visibilityrequest_season_weather_interpolation = _buildbuy.request_season_weather_interpolationset_active_lot_decoration = _buildbuy.set_active_lot_decorationget_active_lot_decoration = _buildbuy.get_active_lot_decoration
def get_current_venue(zone_id):
    return _buildbuy.get_current_venue(services.get_plex_service().get_master_zone_id(zone_id))

def register_build_buy_enter_callback(callback):
    _build_buy_enter_callbacks.register(callback)

def unregister_build_buy_enter_callback(callback):
    _build_buy_enter_callbacks.unregister(callback)

def register_build_buy_exit_callback(callback):
    _build_buy_exit_callbacks.register(callback)

def unregister_build_buy_exit_callback(callback):
    _build_buy_exit_callbacks.unregister(callback)

class HouseholdInventoryFlags(enum.IntFlags):
    FORCE_OWNERSHIP = 1
    DESTROY_OBJECT = 2

def move_object_to_household_inventory(obj, failure_flags=0, object_location_type=ObjectOriginLocation.ON_LOT):
    placement_flags = get_object_placement_flags(obj.definition.id)
    if PlacementFlags.NON_INVENTORYABLE in placement_flags:
        obj.destroy(cause="Can't add non inventoriable objects to household inventory.")
        return False
    else:
        household_id = obj.get_household_owner_id()
        active_household = services.active_household()
        household = services.household_manager().get(household_id)
        if household_id is None or household is None:
            if failure_flags & HouseholdInventoryFlags.FORCE_OWNERSHIP:
                household_id = active_household.id
                household = active_household
                obj.set_household_owner_id(household_id)
            else:
                if failure_flags & HouseholdInventoryFlags.DESTROY_OBJECT:
                    obj.destroy(cause="Can't add unowned objects to household inventory.")
                    return False
                return False
    return False
    obj.on_hovertip_requested()
    obj.new_in_inventory = True
    obj.remove_reference_from_parent()
    stack_count = obj.stack_count()
    obj.set_stack_count(1)
    if is_household_inventory_available(household_id):
        zone_id = services.current_zone_id()
        try:
            _buildbuy.add_object_to_household_inventory(obj.id, household_id, zone_id, household.account.id, object_location_type, stack_count)
        except KeyError as e:
            logger.error('Failed to add {} to {} inventory. Exception: {}', obj, household, e, owner='manus')
            return False
    else:
        household_msg = services.get_persistence_service().get_household_proto_buff(household_id)
        if household_msg is not None:
            for i in range(stack_count):
                object_data = obj.save_object(household_msg.inventory.objects)
                if object_data is not None and i != 0:
                    object_data.id = id_generator.generate_object_id()
            obj.destroy(cause='Add to household inventory')
        else:
            return False
    return True

def has_any_objects_in_household_inventory(object_list, household_id):
    household = services.household_manager().get(household_id)
    zone_id = services.current_zone_id()
    _buildbuy.has_any_objects_in_household_inventory(object_list, household_id, zone_id, household.account.id)

def find_objects_in_household_inventory(definition_ids, household_id):
    return _buildbuy.find_objects_in_household_inventory(definition_ids, household_id)

def remove_object_from_household_inventory(object_id, household):
    zone_id = services.current_zone_id()
    return _buildbuy.remove_object_from_household_inventory(object_id, household.id, zone_id, household.account.id)

def object_exists_in_household_inventory(sim_id, household_id):
    zone_id = services.current_zone_id()
    return _buildbuy.object_exists_in_household_inventory(sim_id, household_id, zone_id)

def __reload__(old_module_vars):
    pass

class BuyCategory(enum.IntFlags):
    UNUSED = 1
    APPLIANCES = 2
    ELECTRONICS = 4
    ENTERTAINMENT = 8
    UNUSED_2 = 16
    LIGHTING = 32
    PLUMBING = 64
    DECOR = 128
    KIDS = 256
    STORAGE = 512
    COMFORT = 2048
    SURFACE = 4096
    VEHICLE = 8192
    DEFAULT = 2147483648

class PlacementFlags(enum.IntFlags, export=False):
    CENTER_ON_WALL = 1
    EDGE_AGAINST_WALL = 2
    ADJUST_HEIGHT_ON_WALL = 4
    CEILING = 8
    IMMOVABLE_BY_USER = 16
    DIAGONAL = 32
    ROOF = 64
    REQUIRES_FENCE = 128
    SHOW_OBJ_IF_WALL_DOWN = 256
    SLOTTED_TO_FENCE = 512
    REQUIRES_SLOT = 1024
    ALLOWED_ON_SLOPE = 2048
    REPEAT_PLACEMENT = 4096
    NON_DELETEABLE = 8192
    NON_INVENTORYABLE = 16384
    NON_ABANDONABLE = 32768
    REQUIRES_TERRAIN = 65536
    ENCOURAGE_INDOOR = 131072
    ENCOURAGE_OUTDOOR = 262144
    NON_DELETABLE_BY_USER = 524288
    NON_INVENTORYABLE_BY_USER = 1048576
    REQUIRES_WATER_SURFACE = 2097152
    ALLOWED_IN_FOUNTAIN = 4194304
    GROUNDED_AGAINST_WALL = 8388608
    NOT_BLUEPRINTABLE = 16777216
    IS_HUMAN = 33554432
    ALLOWED_ON_WATER_SURFACE = 67108864
    ALLOWED_IN_POOL = 134217728
    ON_WALL_TOP = 268435456
    FORCE_DESIGNABLE = 536870912
    ALWAYS_BLUEPRINTABLE = 1073741824
    WALL_OPTIONAL = 2147483648
    REQUIRES_WALL = CENTER_ON_WALL | EDGE_AGAINST_WALL
    WALL_GRAPH_PLACEMENT = REQUIRES_WALL | REQUIRES_FENCE
    SNAP_TO_WALL = REQUIRES_WALL | ADJUST_HEIGHT_ON_WALL
BUILD_BUY_OBJECT_LEAK_DISABLED = 'in build buy'WALL_OBJECT_POSITION_PADDING = 0.25
def get_object_placement_flags(*args, **kwargs):
    return PlacementFlags(_buildbuy.get_object_placement_flags(*args, **kwargs))

def get_object_buy_category_flags(*args, **kwargs):
    return BuyCategory(_buildbuy.get_object_buy_category_flags(*args, **kwargs))

def get_all_objects_with_flags_gen(objs, buy_category_flags):
    for obj in objs:
        if not get_object_buy_category_flags(obj.definition.id) & buy_category_flags:
            pass
        else:
            yield obj

@sims4.utils.exception_protected
def c_api_wall_contour_update(zone_id, wall_type):
    if wall_type == 0 or wall_type == 2:
        services.get_zone(zone_id).wall_contour_update_callbacks()

@sims4.utils.exception_protected
def c_api_foundation_and_level_height_update(zone_id):
    services.get_zone(zone_id).foundation_and_level_height_update_callbacks()

@sims4.utils.exception_protected
def c_api_navmesh_update(zone_id):
    pass

@sims4.utils.exception_protected
def c_api_modify_household_funds(amount:int, household_id:int, reason, zone_id:int):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is not None:
        business_manager.modify_funds(amount, from_item_sold=False)
        return True
    household_manager = services.household_manager()
    household = household_manager.get(household_id)
    if household is None:
        if household_manager.try_add_pending_household_funds(household_id, amount, reason):
            return True
        logger.error('Invalid Household id {} when attempting to modify household funds.', household_id)
        return False
    elif amount > 0:
        household.funds.add(amount, reason, count_as_earnings=False)
    elif amount < 0:
        return household.funds.try_remove(-amount, reason)
    return True

@sims4.utils.exception_protected
def c_api_buildbuy_session_begin(zone_id:int, account_id:int):
    current_zone = services.current_zone()
    posture_graph_service = current_zone.posture_graph_service
    posture_graph_service.on_enter_buildbuy()
    current_zone.on_build_buy_enter()
    object_leak_tracker = services.get_object_leak_tracker()
    if object_leak_tracker is not None:
        object_leak_tracker.add_disable_reason(BUILD_BUY_OBJECT_LEAK_DISABLED)
    resource_keys = []
    if services.get_career_service().get_career_event_situation_is_running():
        household = services.active_household()
    else:
        household = current_zone.get_active_lot_owner_household()
    if household is not None:
        for unlock in household.build_buy_unlocks:
            resource_keys.append(unlock)
    update_gameplay_unlocked_products(resource_keys, zone_id, account_id)
    services.business_service().on_build_buy_enter()
    services.get_reset_and_delete_service().on_build_buy_enter()
    _build_buy_enter_callbacks()
    return True

@sims4.utils.exception_protected
def buildbuy_session_end(zone_id):
    services.object_manager(zone_id).rebuild_objects_to_ignore_portal_validation_cache()
    for obj in services.object_manager(zone_id).get_all():
        obj.on_buildbuy_exit()
    posture_graph_service = services.current_zone().posture_graph_service
    posture_graph_service.on_exit_buildbuy()
    _build_buy_exit_callbacks()
    pythonutils.try_highwater_gc()
    venue_type = get_current_venue(zone_id)
    logger.assert_raise(venue_type is not None, ' Venue Type is None in buildbuy session end for zone id:{}', zone_id, owner='sscholl')
    if venue_type is not None:
        venue_tuning = services.venue_manager().get(venue_type)
        services.current_zone().venue_service.change_venue_type_at_runtime(venue_tuning)
        zone_director = services.venue_service().get_zone_director()
        if zone_director is not None:
            zone_director.on_exit_buildbuy()
    services.business_service().on_build_buy_exit()
    services.current_zone().on_build_buy_exit()
    services.get_reset_and_delete_service().on_build_buy_exit()
    services.object_manager().clear_objects_to_ignore_portal_validation_cache()

@sims4.utils.exception_protected
def c_api_buildbuy_venue_type_changed(zone_id):
    venue_type = get_current_venue(zone_id)
    logger.assert_raise(venue_type is not None, ' Venue Type is None in buildbuy session end for zone id:{}', zone_id, owner='sscholl')
    if venue_type is not None:
        venue_tuning = services.venue_manager().get(venue_type)
        services.current_zone().venue_service.change_venue_type_at_runtime(venue_tuning)

@sims4.utils.exception_protected
def c_api_buildbuy_session_end(zone_id:int, account_id:int, pending_navmesh_rebuild:bool=False):
    zone = services.get_zone(zone_id)
    fence_id = zone.get_current_fence_id_and_increment()
    routing.flush_planner(False)
    routing.add_fence(fence_id)
    object_leak_tracker = services.get_object_leak_tracker()
    if object_leak_tracker is not None:
        object_leak_tracker.remove_disable_reason(BUILD_BUY_OBJECT_LEAK_DISABLED)
    return True

@sims4.utils.exception_protected
def c_api_buildbuy_get_save_object_data(zone_id:int, obj_id:int):
    obj = services.get_zone(zone_id).find_object(obj_id)
    if obj is None:
        return
    object_list = file_serialization.ObjectList()
    save_data = obj.save_object(object_list.objects, from_bb=True)
    return save_data

@sims4.utils.exception_protected
def c_api_buildbuy_lot_traits_changed(zone_id:int):
    services.get_zone_modifier_service().on_zone_modifiers_updated(zone_id)

@sims4.utils.exception_protected
def c_api_house_inv_obj_added(zone_id, household_id, obj_id, obj_def_id):
    household = services.household_manager().get(household_id)
    if household is None:
        current_zone = services.current_zone()
        logger.error('Invalid Household with id: {} when being notified object (id: {} def id: {}) has been added to household inventory. IsZoneLoading:{} ', household_id, obj_id, obj_def_id, current_zone.is_zone_loading)
        return
    collection_tracker = household.collection_tracker
    collection_tracker.check_add_collection_item(household, obj_id, obj_def_id)

@sims4.utils.exception_protected
def c_api_house_inv_obj_removed(zone_id, household_id, obj_id, obj_def_id):
    pass

@sims4.utils.exception_protected
def c_api_set_object_location(zone_id, obj_id, routing_surface, transform):
    obj = services.object_manager().get(obj_id)
    if obj is None:
        logger.error('Trying to place an invalid object id: {}', obj_id, owner='camilogarcia')
        return
    obj.move_to(routing_surface=routing_surface, transform=transform)

@sims4.utils.exception_protected
def c_api_set_object_location_ex(zone_id, obj_id, routing_surface, transform, parent_id, parent_type_info, slot_hash):
    obj = services.get_zone(zone_id).find_object(obj_id)
    if obj is None:
        return
    parent = services.object_manager().get(parent_id) if parent_id else None
    obj.parent_type_info = parent_type_info
    obj.set_parent(parent, transform=transform, slot_hash=slot_hash, routing_surface=routing_surface)

@sims4.utils.exception_protected
def c_api_on_apply_blueprint_lot_begin(zone_id):
    for sim in services.sim_info_manager().instanced_sims_on_active_lot_gen(allow_hidden_flags=ALL_HIDDEN_REASONS):
        sim.fgl_reset_to_landing_strip()
    from objects.components.mannequin_component import set_mannequin_group_sharing_mode, MannequinGroupSharingMode
    set_mannequin_group_sharing_mode(MannequinGroupSharingMode.ACCEPT_THEIRS)

@sims4.utils.exception_protected
def c_api_on_apply_blueprint_lot_end(zone_id):
    from objects.components.mannequin_component import set_mannequin_group_sharing_mode, MannequinGroupSharingMode
    set_mannequin_group_sharing_mode(MannequinGroupSharingMode.ACCEPT_MERGED)

@sims4.utils.exception_protected
def c_api_on_lot_clearing_begin(zone_id):
    zone = services.get_zone(zone_id)
    zone.on_active_lot_clearing_begin()

@sims4.utils.exception_protected
def c_api_on_lot_clearing_end(zone_id):
    zone = services.get_zone(zone_id)
    zone.on_active_lot_clearing_end()

@contextmanager
def floor_feature_update_context(*args, **kwargs):
    try:
        begin_update_floor_features(*args, **kwargs)
        yield None
    finally:
        end_update_floor_features(*args, **kwargs)

@sims4.utils.exception_protected
def c_api_buildbuy_get_mannequin(mannequin_id):
    persistence_service = services.get_persistence_service()
    if persistence_service is not None:
        mannequin_data = persistence_service.get_mannequin_proto_buff(mannequin_id)
        if mannequin_data is not None:
            return mannequin_data.SerializeToString()

@sims4.utils.exception_protected
def c_api_buildbuy_delete_mannequin(mannequin_id):
    persistence_service = services.get_persistence_service()
    if persistence_service is not None:
        persistence_service.del_mannequin_proto_buff(mannequin_id)

@sims4.utils.exception_protected
def c_api_buildbuy_update_mannequin(mannequin_id, mannequin_data):
    persistence_service = services.get_persistence_service()
    if persistence_service is not None:
        persistence_service.del_mannequin_proto_buff(mannequin_id)
        sim_info_data_proto = persistence_service.add_mannequin_proto_buff()
        sim_info_data_proto.ParseFromString(mannequin_data)
