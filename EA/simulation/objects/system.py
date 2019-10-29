from objects.gallery_tuning import ContentSourcefrom objects.object_enums import ResetReasonfrom objects.persistence_groups import PersistenceGroupsfrom sims4.tuning.tunable import Tunablefrom sims4.utils import exception_protectedimport build_buyimport servicesimport sims4import sims4.logLOG_CHANNEL = 'Objects'logger = sims4.log.Logger(LOG_CHANNEL)production_logger = sims4.log.ProductionLogger(LOG_CHANNEL)
class SystemTuning:
    build_buy_lockout_duration = Tunable(int, 5, description='Number of seconds an object should stay locked for after it is manipulated in Build/Buy.')

@exception_protected
def c_api_get_object_definition(obj_id, zone_id):
    obj = find_object(obj_id)
    if obj is None:
        return
    return obj.definition.id

@exception_protected
def c_api_get_object_def_state(obj_id, zone_id):
    obj = find_object(obj_id)
    if obj is None:
        return
    return obj.state_index

def c_api_get_object_attributes(obj_id, zone_id):
    obj = find_object(obj_id)
    if obj is None:
        return
    return (obj.definition.id, obj.state_index, obj.transform, obj.routing_surface)

def create_script_object(definition_or_id, obj_state=0, **kwargs):
    from objects.definition import Definition
    if isinstance(definition_or_id, Definition):
        definition = definition_or_id
    else:
        definition = services.definition_manager().get(definition_or_id, obj_state=obj_state)
        if definition is None:
            logger.error('Unable to create a script object for definition id: {0}', definition_or_id)
            return
    return definition.instantiate(obj_state=obj_state, **kwargs)

@exception_protected
def c_api_create_object(zone_id, def_id, obj_id, obj_state, loc_type, content_source=ContentSource.DEFAULT):
    return create_object(def_id, obj_id=obj_id, obj_state=obj_state, loc_type=loc_type, content_source=content_source)

@exception_protected
def c_api_set_part_owner(zone_id, part_owner_id, part_id):
    part_owner = find_object(part_owner_id)
    part = find_object(part_id)
    if part_owner is None or part is None:
        return False
    part.part_owner = part_owner
    return True

@exception_protected
def c_api_start_delaying_posture_graph_adds():
    pass

@exception_protected
def c_api_stop_delaying_posture_graph_adds():
    pass

def create_object(definition_or_id, obj_id=0, init=None, post_add=None, loc_type=None, content_source=ContentSource.DEFAULT, **kwargs):
    from objects.base_object import BaseObject
    from objects.object_enums import ItemLocation
    added_to_object_manager = False
    obj = None
    if loc_type is None:
        loc_type = ItemLocation.ON_LOT
    try:
        zone_id = services.current_zone_id()
        zone_id = 0 if zone_id is None else zone_id
        from objects.definition import Definition
        if isinstance(definition_or_id, Definition):
            fallback_definition_id = build_buy.get_vetted_object_defn_guid(zone_id, obj_id, definition_or_id.id)
            if fallback_definition_id != definition_or_id.id:
                definition_or_id = fallback_definition_id
        else:
            definition_or_id = build_buy.get_vetted_object_defn_guid(zone_id, obj_id, definition_or_id)
        if definition_or_id is None:
            return
        obj = create_script_object(definition_or_id, **kwargs)
        if obj is None:
            return
        if not isinstance(obj, BaseObject):
            logger.error('Type {0} is not a valid managed object.  It is not a subclass of BaseObject.', type(obj))
            return
        if init is not None:
            init(obj)
        if loc_type == ItemLocation.FROM_WORLD_FILE or loc_type == ItemLocation.FROM_CONDITIONAL_LAYER:
            obj.persistence_group = PersistenceGroups.IN_OPEN_STREET
        obj.item_location = ItemLocation(loc_type) if loc_type is not None else ItemLocation.INVALID_LOCATION
        obj.id = obj_id
        obj.content_source = content_source
        if loc_type == ItemLocation.ON_LOT or (loc_type == ItemLocation.FROM_WORLD_FILE or (loc_type == ItemLocation.FROM_OPEN_STREET or loc_type == ItemLocation.HOUSEHOLD_INVENTORY)) or loc_type == ItemLocation.FROM_CONDITIONAL_LAYER:
            obj.object_manager_for_create.add(obj)
        elif loc_type == ItemLocation.SIM_INVENTORY or loc_type == ItemLocation.OBJECT_INVENTORY:
            services.current_zone().inventory_manager.add(obj)
        else:
            logger.error('Unsupported loc_type passed to create_script_object.  We likely need to update this code path.', owner='mduke')
        added_to_object_manager = True
        if post_add is not None:
            post_add(obj)
        return obj
    finally:
        if added_to_object_manager or obj is not None:
            import _weakrefutils
            _weakrefutils.clear_weak_refs(obj)

def _get_id_for_obj_or_id(obj_or_id):
    from objects.base_object import BaseObject
    if isinstance(obj_or_id, BaseObject):
        return obj_or_id.id
    return int(obj_or_id)

def _get_obj_for_obj_or_id(obj_or_id):
    from objects.base_object import BaseObject
    if not isinstance(obj_or_id, BaseObject):
        obj = services.object_manager().get(obj_or_id)
        if obj is None:
            logger.error('Could not find the target id {} for a RequiredTargetParam in the object manager.', obj_or_id)
        return obj
    return obj_or_id

@exception_protected
def c_api_destroy_object(zone_id, obj_or_id):
    obj = _get_obj_for_obj_or_id(obj_or_id)
    if obj is not None:
        return obj.destroy(source=obj, cause='Destruction request from C.')
    return False

@exception_protected
def c_api_reset_object(zone_id, obj_or_id):
    return reset_object(obj_or_id, expected=True, cause='Build/Buy')

def reset_object(obj_or_id, expected, cause=None):
    obj = _get_obj_for_obj_or_id(obj_or_id)
    if obj is not None:
        obj.reset(ResetReason.RESET_EXPECTED if expected else ResetReason.RESET_ON_ERROR, None, cause)
        return True
    return False

def remove_object_from_client(obj_or_id, **kwargs):
    obj = _get_obj_for_obj_or_id(obj_or_id)
    manager = obj.manager
    if obj.id in manager:
        manager.remove_from_client(obj, **kwargs)
        return True
    return False

def create_prop(definition_or_id, is_basic=False, **kwargs):
    from objects.prop_object import BasicPropObject, PropObject
    cls_override = BasicPropObject if is_basic else PropObject
    return create_object(definition_or_id, cls_override=cls_override, **kwargs)

def create_prop_with_footprint(definition_or_id, **kwargs):
    from objects.prop_object import PropObjectWithFootprint
    return create_object(definition_or_id, cls_override=PropObjectWithFootprint, **kwargs)

@exception_protected
def c_api_find_object(obj_id, zone_id):
    return find_object(obj_id)

def find_object(obj_id, **kwargs):
    return services.current_zone().find_object(obj_id, **kwargs)

@exception_protected
def c_api_get_objects(zone_id):
    return get_objects()

def get_objects():
    return services.object_manager().get_all()

@exception_protected
def c_api_set_object_state_index(obj_id, state_index, zone_id):
    obj = find_object(obj_id)
    obj.set_object_def_state_index(state_index)

@exception_protected(default_return=False)
def c_api_set_build_buy_lockout(zone_id, obj_or_id, lockout_state, permanent_lock=False):
    obj = _get_obj_for_obj_or_id(obj_or_id)
    if obj is not None:
        obj.set_build_buy_lockout_state(False, None)
        return True
        obj.set_build_buy_lockout_state(lockout_state, SystemTuning.build_buy_lockout_duration)
        return True
    return False

@exception_protected(default_return=-1)
def c_api_set_parent_object(obj_id, parent_id, transform, joint_name, slot_hash, zone_id):
    set_parent_object(obj_id, parent_id, transform, joint_name, slot_hash)

@exception_protected
def c_api_get_buildbuy_use_flags(zone_id, object_id):
    obj = find_object(object_id)
    return obj.build_buy_use_flags

@exception_protected
def c_api_set_buildbuy_use_flags(zone_id, object_id, build_buy_use_flags):
    obj = find_object(object_id)
    if obj is not None:
        obj.build_buy_use_flags = build_buy_use_flags
        return True
    return False

def set_parent_object(obj_id, parent_id, transform=sims4.math.Transform.IDENTITY(), joint_name=None, slot_hash=0):
    obj = find_object(obj_id)
    parent_obj = find_object(parent_id)
    obj.set_parent(parent_obj, transform, joint_name_or_hash=joint_name, slot_hash=slot_hash)

@exception_protected(default_return=-1)
def c_api_clear_parent_object(obj_id, transform, zone_id, surface):
    obj = find_object(obj_id)
    obj.clear_parent(transform, surface)

@exception_protected
def c_api_get_parent(obj_id, zone_id):
    obj = find_object(obj_id, include_props=True)
    if obj is not None:
        return obj.bb_parent

@exception_protected(default_return=0)
def c_api_get_slot_hash(obj_id, zone_id):
    obj = find_object(obj_id, include_props=True)
    if obj is not None:
        return obj.bone_name_hash
    return 0

@exception_protected(default_return=0)
def c_api_set_slot_hash(obj_id, zone_id, slot_hash):
    obj = find_object(obj_id)
    if obj is not None:
        obj.slot_hash = slot_hash

@exception_protected(default_return=iter(()))
def c_api_get_all_children_gen(obj_id):
    obj = find_object(obj_id)
    if obj is not None:
        try:
            yield from obj.get_all_children_gen()
        except AttributeError:
            pass

@exception_protected(default_return=True)
def c_api_clear_default_children(obj_id):
    obj = find_object(obj_id, include_props=True)
    if obj is not None:
        try:
            obj.clear_default_children()
            return True
        except AttributeError:
            logger.error('Trying to clear children, but obj({}) does not support functionality', obj)
    return False
