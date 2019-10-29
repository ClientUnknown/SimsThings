from contextlib import contextmanagerimport collectionsimport functoolsimport itertoolsimport operatorimport refrom animation.posture_manifest import AnimationParticipantfrom event_testing.resolver import DoubleSimResolverfrom objects import ALL_HIDDEN_REASONSfrom objects.slots import RuntimeSlotfrom postures.posture_tuning import PostureTuningfrom sims.sim_info_types import Speciesfrom sims4.callback_utils import consume_exceptionsfrom sims4.collections import enumdictfrom sims4.log import Loggerfrom sims4.math import vector3_almost_equalfrom sims4.repr_utils import standard_reprfrom sims4.tuning.tunable import Tunablefrom singletons import DEFAULTimport animation.posture_manifestimport assertionsimport enumimport event_testingimport objects.components.typesimport postures.posture_scoringimport routingimport servicesimport sims4.callback_utilsimport sims4.reloadlogger = Logger('PostureGraph')BODY_INDEX = 0CARRY_INDEX = 1SURFACE_INDEX = 2BODY_POSTURE_TYPE_INDEX = 0BODY_TARGET_INDEX = 1CARRY_POSTURE_TYPE_INDEX = 0CARRY_TARGET_INDEX = 1CARRY_HAND_INDEX = 2SURFACE_TARGET_INDEX = 0SURFACE_SLOT_TYPE_INDEX = 1SURFACE_SLOT_TARGET_INDEX = 2with sims4.reload.protected(globals()):
    _enable_cache_count = 0
    _cached_object_manager = None
    _cached_valid_objects = None
    _cached_runtime_slots = None
    _cached_sim_instances = None
    new_object = None
@contextmanager
def _object_addition(obj):
    global new_object
    new_object = obj
    try:
        yield None
    finally:
        new_object = None

class PostureSpecVariable(enum.Int):
    ANYTHING = 200
    INTERACTION_TARGET = 201
    CARRY_TARGET = 302
    SURFACE_TARGET = 203
    CONTAINER_TARGET = 204
    HAND = 205
    POSTURE_TYPE_CARRY_NOTHING = 206
    POSTURE_TYPE_CARRY_OBJECT = 207
    SLOT = 208
    SLOT_TEST_DEFINITION = 209
    DESTINATION_FILTER = 211
    BODY_TARGET_FILTERED = 212
    SLOT_TARGET = 213

    def __repr__(self):
        return self.name

@contextmanager
def _cache_thread_specific_info():
    global _cached_runtime_slots, _enable_cache_count, _cached_object_manager, _cached_valid_objects, _cached_sim_instances
    _cached_runtime_slots = {}
    _enable_cache_count += 1
    try:
        if _enable_cache_count == 1:
            with sims4.callback_utils.invoke_enter_exit_callbacks(sims4.callback_utils.CallbackEvent.POSTURE_GRAPH_BUILD_ENTER, sims4.callback_utils.CallbackEvent.POSTURE_GRAPH_BUILD_EXIT), consume_exceptions():
                yield None
        else:
            yield None
    finally:
        _enable_cache_count -= 1
        if not _enable_cache_count:
            _cached_object_manager = None
            _cached_valid_objects = None
            _cached_runtime_slots = None
            _cached_sim_instances = None

def with_caches(func):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with _cache_thread_specific_info():
            return func(*args, **kwargs)

    return wrapper

def object_manager():
    global _cached_object_manager
    if _enable_cache_count:
        if _cached_object_manager is None:
            _cached_object_manager = services.object_manager()
        return _cached_object_manager
    return services.object_manager()

def instanced_sims():
    global _cached_sim_instances
    if _enable_cache_count:
        if _cached_sim_instances is None:
            sim_info_manager = services.sim_info_manager()
            _cached_sim_instances = frozenset([instanced_sim for instanced_sim in sim_info_manager.instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS)])
        return _cached_sim_instances
    sim_info_manager = services.sim_info_manager()
    return frozenset([instanced_sim for instanced_sim in sim_info_manager.instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS)])

def valid_objects():
    global _cached_valid_objects
    if _enable_cache_count:
        if _cached_valid_objects is None:
            _cached_valid_objects = _valid_objects_helper()
        return _cached_valid_objects
    return _valid_objects_helper()

def _valid_objects_helper():
    result = set()
    posture_graph_service = services.posture_graph_service()
    for obj in object_manager().values():
        if not obj.is_valid_posture_graph_object:
            pass
        elif obj.is_sim or obj.is_hidden():
            pass
        elif posture_graph_service.has_built_for_zone_spin_up or not obj.provided_mobile_posture_affordances:
            pass
        elif obj.parts:
            result.update(obj.parts)
        else:
            result.add(obj)
    if new_object is not None:
        if new_object.parts:
            result.update(new_object.parts)
        else:
            result.add(new_object)
    return frozenset(result)

def _simple_id_str(obj):
    return str(obj)

def _str_for_variable(value):
    result = 'None'
    if value is not None:
        result = str(value).split('.')[-1]
    return result

def _str_for_type(value):
    if value is None:
        return 'None'
    if isinstance(value, PostureSpecVariable):
        return _str_for_variable(value)
    return value.__name__

def _str_for_object(value):
    if value is None:
        return 'None'
    if isinstance(value, PostureSpecVariable):
        return _str_for_variable(value)
    return _simple_id_str(value)

def _str_for_slot_type(value):
    if value is None:
        return 'None'
    if isinstance(value, PostureSpecVariable):
        return _str_for_variable(value)
    return value.__name__.split('_')[-1]

def variables_match(a, b, var_map=None, allow_owner_to_match_parts=True):
    if a == b:
        return True
    if PostureSpecVariable.ANYTHING in (a, b):
        return True
    if None in (a, b):
        return False
    if PostureSpecVariable.BODY_TARGET_FILTERED in (a, b):
        if a == PostureSpecVariable.BODY_TARGET_FILTERED:
            if any([not filter.matches(b) for filter in var_map[PostureSpecVariable.BODY_TARGET_FILTERED]]):
                return False
        elif any([not filter.matches(a) for filter in var_map[PostureSpecVariable.BODY_TARGET_FILTERED]]):
            return False
        return True
    if var_map:
        a = var_map.get(a, a)
        b = var_map.get(b, b)
        return variables_match(a, b, None, allow_owner_to_match_parts)
    if isinstance(a, PostureSpecVariable) or isinstance(b, PostureSpecVariable):
        return True
    if a.id != b.id:
        return False
    elif a.is_part and b.is_part:
        return False
    return allow_owner_to_match_parts

def _get_origin_spec(default_body_posture, origin_carry):
    origin_body = PostureAspectBody((default_body_posture, None))
    origin_surface = PostureAspectSurface((None, None, None))
    origin_node = PostureSpec((origin_body, origin_carry, origin_surface))
    return origin_node

def get_origin_carry():
    return PostureAspectCarry((PostureSpecVariable.POSTURE_TYPE_CARRY_NOTHING, None, PostureSpecVariable.HAND))

def get_origin_spec(default_body_posture):
    origin_carry = get_origin_carry()
    return _get_origin_spec(default_body_posture, origin_carry)

def get_origin_spec_carry(default_body_posture):
    origin_carry = PostureAspectCarry((PostureSpecVariable.POSTURE_TYPE_CARRY_OBJECT, PostureSpecVariable.CARRY_TARGET, PostureSpecVariable.HAND))
    return _get_origin_spec(default_body_posture, origin_carry)

def get_pick_up_spec_sequence(node_origin, surface_target, body_target=None):
    default_body_posture = node_origin[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]
    default_surface_target = node_origin[SURFACE_INDEX][SURFACE_TARGET_INDEX]
    origin = get_origin_spec(default_body_posture)
    origin_carry = get_origin_spec_carry(default_body_posture)
    if body_target is None:
        slot_type = None
        target_var = None
        target = surface_target
    else:
        slot_type = PostureSpecVariable.SLOT
        target_var = PostureSpecVariable.CARRY_TARGET
        target = body_target
    move_to_surface = PostureSpec((PostureAspectBody((default_body_posture, target)), origin[CARRY_INDEX], PostureAspectSurface((None, None, None))))
    address_surface = PostureSpec((PostureAspectBody((default_body_posture, target)), origin[CARRY_INDEX], PostureAspectSurface((surface_target, slot_type, target_var))))
    address_surface_carry = PostureSpec((address_surface[BODY_INDEX], origin_carry[CARRY_INDEX], PostureAspectSurface((surface_target, None, None))))
    address_surface_target = address_surface[SURFACE_INDEX][SURFACE_TARGET_INDEX]
    if default_surface_target is address_surface_target:
        return (address_surface, address_surface_carry)
    return (move_to_surface, address_surface, address_surface_carry)

def get_put_down_spec_sequence(default_body_posture, surface_target, body_target=None):
    body_target = body_target or surface_target
    origin = get_origin_spec(default_body_posture)
    origin_carry = get_origin_spec_carry(default_body_posture)
    slot_type = PostureSpecVariable.SLOT
    target_var = PostureSpecVariable.CARRY_TARGET
    address_surface = PostureSpec((PostureAspectBody((default_body_posture, body_target)), origin[CARRY_INDEX], PostureAspectSurface((surface_target, slot_type, target_var))))
    address_surface_carry = PostureSpec((address_surface[BODY_INDEX], origin_carry[CARRY_INDEX], PostureAspectSurface((surface_target, None, None))))
    return (address_surface_carry, address_surface)

@assertions.hot_path
def node_matches_spec(node, spec, var_map, allow_owner_to_match_parts):
    node_body = node[BODY_INDEX]
    node_body_target = node_body[BODY_TARGET_INDEX]
    node_body_posture_type = node_body[BODY_POSTURE_TYPE_INDEX]
    spec_surface = spec[SURFACE_INDEX]
    node_surface = node[SURFACE_INDEX]
    spec_body = spec[BODY_INDEX]
    if spec_body is not None:
        spec_body_target = spec_body[BODY_TARGET_INDEX]
        spec_body_posture_type = spec_body[BODY_POSTURE_TYPE_INDEX]
    else:
        spec_body_target = PostureSpecVariable.ANYTHING
        spec_body_posture_type = node_body_posture_type
    if spec_body_posture_type != node_body_posture_type:
        return False
    if not variables_match(node_body_target, spec_body_target, var_map, allow_owner_to_match_parts):
        return False
    if node_body_posture_type.mobile and (node_body_target is not None and (spec_surface is None or spec_surface[SURFACE_TARGET_INDEX] is None)) and spec_body_target == PostureSpecVariable.ANYTHING:
        return False
    carry_index = CARRY_INDEX
    spec_carry = spec[carry_index]
    if spec_carry is not None:
        node_carry = node[carry_index]
        carry_posture_type_index = CARRY_POSTURE_TYPE_INDEX
        if node_carry[carry_posture_type_index] != spec_carry[carry_posture_type_index]:
            return False
        carry_target_index = CARRY_TARGET_INDEX
        if not variables_match(node_carry[carry_target_index], spec_carry[carry_target_index], var_map, allow_owner_to_match_parts):
            return False
    if (spec_surface is None or spec_surface[SURFACE_TARGET_INDEX] is None) and node_surface is not None and node_body_posture_type.mobile:
        node_surface_target = node_surface[SURFACE_TARGET_INDEX]
        if node_surface_target is not None:
            return False
    if spec_surface is not None:
        if not variables_match(node_surface[SURFACE_TARGET_INDEX], spec_surface[SURFACE_TARGET_INDEX], var_map, allow_owner_to_match_parts):
            return False
        if node_surface[SURFACE_SLOT_TYPE_INDEX] != spec_surface[SURFACE_SLOT_TYPE_INDEX]:
            return False
        elif not variables_match(node_surface[SURFACE_SLOT_TARGET_INDEX], spec_surface[SURFACE_SLOT_TARGET_INDEX], var_map, allow_owner_to_match_parts):
            return False
    return True

def _spec_matches_request(sim, spec, var_map):
    if spec[SURFACE_INDEX][SURFACE_SLOT_TYPE_INDEX] is not None:
        slot_manifest = var_map.get(PostureSpecVariable.SLOT)
        if slot_manifest is not None:
            surface = spec[SURFACE_INDEX][SURFACE_TARGET_INDEX]
            if not slot_manifest.slot_types.intersection(surface.get_provided_slot_types()):
                return False
            carry_target = slot_manifest.actor
            if hasattr(carry_target, 'manager') and not carry_target.has_component(objects.components.types.CARRYABLE_COMPONENT):
                current_parent_slot = carry_target.parent_slot
                if current_parent_slot is None:
                    return False
                if current_parent_slot.owner != surface:
                    return False
                if not slot_manifest.slot_types.intersection(current_parent_slot.slot_types):
                    return False
                else:
                    destination_filter = var_map.get(PostureSpecVariable.DESTINATION_FILTER)
                    if destination_filter is not None and not destination_filter(spec, var_map):
                        return False
            else:
                destination_filter = var_map.get(PostureSpecVariable.DESTINATION_FILTER)
                if destination_filter is not None and not destination_filter(spec, var_map):
                    return False
        else:
            destination_filter = var_map.get(PostureSpecVariable.DESTINATION_FILTER)
            if destination_filter is not None and not destination_filter(spec, var_map):
                return False
    return True

def _in_var_map(obj, var_map):
    for target in var_map.values():
        if isinstance(target, objects.game_object.GameObject) and target.is_same_object_or_part(obj):
            return True
    return False

def destination_autonomous_availability_test(sim, body_target_obj, interaction):
    if body_target_obj is interaction.sim:
        return True
    if body_target_obj is sim.parent:
        return True
    if interaction.ignore_autonomy_rules_if_user_directed and interaction.is_user_directed:
        return True
    return sim.autonomy_component.is_object_autonomously_available(body_target_obj, interaction)

def destination_test(sim, node, destination_specs, var_map, additional_test_fn, interaction):
    sims4.sim_irq_service.yield_to_irq()
    body_index = node[BODY_INDEX]
    if not body_index[BODY_POSTURE_TYPE_INDEX].is_animation_available_for_species(sim.species):
        return False
    body_target = body_index[BODY_TARGET_INDEX]
    if body_target is not None:
        body_target_obj = body_target.part_owner if body_target.is_part else body_target
        if sim.current_object_set_as_head is not None and sim.current_object_set_as_head() is body_target_obj:
            return False
        if any(_in_var_map(child, var_map) for child in body_target.parenting_hierarchy_gen()) or not destination_autonomous_availability_test(sim, body_target_obj, interaction):
            return False
    if not any(node_matches_spec(node, destination_spec, var_map, True) for destination_spec in destination_specs):
        return False
    if not node.validate_destination(destination_specs, var_map, interaction, sim):
        return False
    elif additional_test_fn is not None and not additional_test_fn(node, var_map):
        return False
    return True

class PostureAspectBody(tuple):
    __slots__ = ()
    posture_type = property(operator.itemgetter(BODY_POSTURE_TYPE_INDEX))
    target = property(operator.itemgetter(BODY_TARGET_INDEX))

    def __str__(self):
        return '{}@{}'.format(self[BODY_POSTURE_TYPE_INDEX].name, self[BODY_TARGET_INDEX])

    def __repr__(self):
        return standard_repr(self, tuple(self))

class PostureAspectCarry(tuple):
    __slots__ = ()
    posture_type = property(operator.itemgetter(CARRY_POSTURE_TYPE_INDEX))
    target = property(operator.itemgetter(CARRY_TARGET_INDEX))

    def __str__(self):
        if self[CARRY_TARGET_INDEX] is None:
            return self[CARRY_POSTURE_TYPE_INDEX].name
        return '<{} {}>'.format(self[CARRY_POSTURE_TYPE_INDEX].name, self[CARRY_TARGET_INDEX])

    def __repr__(self):
        return standard_repr(self, tuple(self))

class PostureAspectSurface(tuple):
    __slots__ = ()
    target = property(operator.itemgetter(SURFACE_TARGET_INDEX))
    slot_type = property(operator.itemgetter(SURFACE_SLOT_TYPE_INDEX))
    slot_target = property(operator.itemgetter(SURFACE_SLOT_TARGET_INDEX))

    def __str__(self):
        if self[SURFACE_SLOT_TYPE_INDEX] is None:
            if self[SURFACE_TARGET_INDEX] is None:
                return 'No Surface'
            return '@Surface: ' + str(self[SURFACE_TARGET_INDEX])
        if self[SURFACE_SLOT_TARGET_INDEX] is None:
            slot_str = '(EmptySlot)'
        else:
            slot_str = '(TargetInSlot)'
        return 'Surface: ' + str(self[SURFACE_TARGET_INDEX]) + slot_str

    def __repr__(self):
        return standard_repr(self, tuple(self))

class PostureSpec(tuple):
    __slots__ = ()
    body = property(operator.itemgetter(BODY_INDEX))
    body_target = property(lambda self: self[BODY_INDEX] and self[BODY_INDEX][BODY_TARGET_INDEX])
    body_posture = property(lambda self: self[BODY_INDEX] and self[BODY_INDEX][BODY_POSTURE_TYPE_INDEX])
    carry = property(operator.itemgetter(CARRY_INDEX))
    carry_target = property(lambda self: self[CARRY_INDEX] and self[CARRY_INDEX][CARRY_TARGET_INDEX])
    carry_posture = property(lambda self: self[CARRY_INDEX] and self[CARRY_INDEX][CARRY_POSTURE_TYPE_INDEX])
    surface = property(operator.itemgetter(SURFACE_INDEX))
    surface_target = property(lambda self: self[SURFACE_INDEX] and self[SURFACE_INDEX][SURFACE_TARGET_INDEX])
    slot_type = property(lambda self: self[SURFACE_INDEX] and self[SURFACE_INDEX][SURFACE_SLOT_TYPE_INDEX])
    slot_target = property(lambda self: self[SURFACE_INDEX] and self[SURFACE_INDEX][SURFACE_SLOT_TARGET_INDEX])

    def clone(self, body=DEFAULT, carry=DEFAULT, surface=DEFAULT):
        if body is DEFAULT:
            body = self[BODY_INDEX]
        if carry is DEFAULT:
            carry = self[CARRY_INDEX]
        if surface is DEFAULT:
            surface = self[SURFACE_INDEX]
        return self.__class__((body, carry, surface))

    _attribute_definitions = (('_body_posture_name', str), ('_body_target_type', str), ('_body_target', str), ('_body_part', str), ('_is_carrying', str), ('_at_surface', str), ('_surface_target_type', str), ('_surface_target', str), ('_surface_part', str), ('_slot_target', str))

    @property
    def _body_posture_name(self):
        body = self[BODY_INDEX]
        if body is None:
            return
        body_posture_type = body[BODY_POSTURE_TYPE_INDEX]
        if body_posture_type is None:
            return
        return body_posture_type._posture_name

    @property
    def _body_target_type(self):
        body = self[BODY_INDEX]
        if body is None:
            return
        target = body[BODY_TARGET_INDEX]
        if target is None:
            return
        if target.is_part:
            target = target.part_owner
        return type(target).__name__

    @property
    def _body_target(self):
        body = self[BODY_INDEX]
        if body is None:
            return
        target = body[BODY_TARGET_INDEX]
        if target is None:
            return
        if isinstance(target, PostureSpecVariable):
            return target.name
        elif target.is_part:
            return target.part_owner
        return target

    @property
    def _body_target_with_part(self):
        body = self[BODY_INDEX]
        if body is None:
            return
        target = body[BODY_TARGET_INDEX]
        if target is None:
            return
        elif isinstance(target, PostureSpecVariable):
            return target.name
        return target

    @property
    def _body_part(self):
        body = self[BODY_INDEX]
        if body is None:
            return
        target = body[BODY_TARGET_INDEX]
        if target is None or isinstance(target, PostureSpecVariable):
            return
        elif target.is_part:
            return target.part_group_index

    @property
    def _is_carrying(self):
        carry = self[CARRY_INDEX]
        if carry is not None and carry[CARRY_TARGET_INDEX] is not None:
            return True
        return False

    @property
    def _at_surface(self):
        surface = self[SURFACE_INDEX]
        if surface is not None and surface[SURFACE_SLOT_TYPE_INDEX] is not None:
            return True
        return False

    @property
    def _surface_target_type(self):
        surface = self[SURFACE_INDEX]
        if surface is None:
            return
        target = surface[SURFACE_TARGET_INDEX]
        if target is None:
            return
        if isinstance(target, PostureSpecVariable):
            return target.name
        if target.is_part:
            target = target.part_owner
        return type(target).__name__

    @property
    def _surface_target(self):
        surface = self[SURFACE_INDEX]
        if surface is None:
            return
        target = surface[SURFACE_TARGET_INDEX]
        if target is None:
            return
        if isinstance(target, PostureSpecVariable):
            return target.name
        elif target.is_part:
            return target.part_owner
        return target

    @property
    def _surface_target_with_part(self):
        surface = self[SURFACE_INDEX]
        if surface is None:
            return
        target = surface[SURFACE_TARGET_INDEX]
        if target is None:
            return
        elif isinstance(target, PostureSpecVariable):
            return target.name
        return target

    @property
    def _surface_part(self):
        surface = self[SURFACE_INDEX]
        if surface is None:
            return
        target = surface[SURFACE_TARGET_INDEX]
        if target is None or isinstance(target, PostureSpecVariable):
            return
        elif target.is_part:
            return target.part_group_index

    @property
    def _slot_target(self):
        surface = self[SURFACE_INDEX]
        if surface[SURFACE_TARGET_INDEX] is not None:
            if surface[SURFACE_SLOT_TYPE_INDEX] is not None:
                slot_target = surface[SURFACE_SLOT_TARGET_INDEX]
                if slot_target is not None:
                    if isinstance(slot_target, PostureSpecVariable):
                        return slot_target.name
                    else:
                        return 'TargetInSlot'
                else:
                    return 'EmptySlot'
            else:
                return 'AtSurface'

    def __repr__(self):
        result = '{}@{}'.format(self._body_posture_name, _simple_id_str(self._body_target_with_part))
        carry = self[CARRY_INDEX]
        if carry is None:
            result += ', carry:any'
        elif self[CARRY_INDEX][CARRY_TARGET_INDEX] is not None:
            result += ', carry'
        surface = self[SURFACE_INDEX]
        if surface is None:
            result += ', surface:any'
        elif surface[SURFACE_SLOT_TYPE_INDEX] is not None:
            if surface[SURFACE_SLOT_TARGET_INDEX] is not None:
                result += ', surface:slot_target@{}'.format(_simple_id_str(self._surface_target_with_part))
            else:
                result += ', surface:empty_slot@{}'.format(_simple_id_str(self._surface_target_with_part))
        elif surface[SURFACE_TARGET_INDEX] is not None:
            result += ', surface:{}'.format(_simple_id_str(self._surface_target_with_part))
        return result

    def get_core_objects(self):
        body_target = self[BODY_INDEX][BODY_TARGET_INDEX]
        surface_target = self[SURFACE_INDEX][SURFACE_TARGET_INDEX]
        core_objects = set()
        if body_target is not None:
            core_objects.add(body_target)
            body_target_parent = body_target.parent
            if body_target_parent is not None:
                core_objects.add(body_target_parent)
        if surface_target is not None:
            core_objects.add(surface_target)
        return core_objects

    def get_relevant_objects(self):
        body_posture = self[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]
        body_target = self[BODY_INDEX][BODY_TARGET_INDEX]
        surface_target = self[SURFACE_INDEX][SURFACE_TARGET_INDEX]
        if body_posture.mobile and body_target is None and surface_target is None or body_posture is PostureTuning.SIM_CARRIED_POSTURE:
            return valid_objects()
        relevant_objects = self.get_core_objects()
        if body_target is not None:
            if body_target.is_part:
                relevant_objects.update(body_target.adjacent_parts_gen())
            relevant_objects.update(body_target.children)
        can_transition_to_carry = not body_posture.mobile or body_posture.mobile and body_target is None
        if can_transition_to_carry and body_posture.is_available_transition(PostureTuning.SIM_CARRIED_POSTURE):
            relevant_objects.update(instanced_sims())
        return relevant_objects

    def same_spec_except_slot(self, target):
        if self.body == target.body and self.carry == target.carry and self[SURFACE_INDEX][SURFACE_TARGET_INDEX] == target[SURFACE_INDEX][SURFACE_TARGET_INDEX]:
            return True
        return False

    def same_spec_ignoring_surface_if_mobile(self, target):
        if self.body_posture.mobile and self.body_posture == target.body_posture and self.carry == target.carry:
            return True
        return False

    def is_on_vehicle(self):
        target = self.body[BODY_TARGET_INDEX]
        if target is not None:
            return target.vehicle_component is not None
        return False

    def validate_destination(self, destination_specs, var_map, interaction, sim):
        if not any(self._validate_carry(destination_spec) for destination_spec in destination_specs):
            return False
        if not self._validate_subroot(interaction, sim):
            return False
        if not self._validate_surface(var_map, affordance=interaction.affordance):
            return False
        if not self._validate_body(interaction, sim):
            return False
        posture_graph_service = services.current_zone().posture_graph_service
        zone_director = services.venue_service().get_zone_director()
        for obj in (self.body_target, self.surface_target):
            if not obj is None:
                if isinstance(obj, PostureSpecVariable):
                    pass
                else:
                    if obj.valid_for_distribution and posture_graph_service.is_object_pending_deletion(obj):
                        return False
                    if obj.check_affordance_for_suppression(sim, interaction, user_directed=False):
                        return False
                    if not zone_director.zone_director_specific_destination_tests(sim, obj):
                        return False
        return True

    def _validate_body(self, interaction, sim):
        body = self[BODY_INDEX]
        if body is None:
            return True
        target = body[BODY_TARGET_INDEX]
        if target is None:
            return True
        else:
            affordance = interaction.affordance
            if sim is not interaction.sim:
                linked_interaction_type = interaction.linked_interaction_type
                if linked_interaction_type is not affordance:
                    affordance = linked_interaction_type
            if not (interaction.is_social and target.supports_affordance(affordance)):
                return False
        return True

    def _validate_carry(self, destination_spec):
        dest_carry = destination_spec[CARRY_INDEX]
        if dest_carry is None or dest_carry[CARRY_TARGET_INDEX] is None:
            if self[CARRY_INDEX][CARRY_TARGET_INDEX] is None:
                return True
            return False
        elif dest_carry == self[CARRY_INDEX]:
            return True
        return False

    def _validate_surface(self, var_map, affordance=None):
        surface_spec = self[SURFACE_INDEX]
        if surface_spec is None:
            return True
        surface = surface_spec[SURFACE_TARGET_INDEX]
        if surface is None:
            return True
        if affordance is not None and not surface.supports_affordance(affordance):
            return False
        slot_type = surface_spec[SURFACE_SLOT_TYPE_INDEX]
        if slot_type is None:
            return True
        slot_manifest_entry = var_map.get(slot_type)
        if slot_manifest_entry is None:
            return False
        else:
            runtime_slots = set(surface.get_runtime_slots_gen(slot_types=slot_manifest_entry.slot_types))
            slot_target = surface_spec[SURFACE_SLOT_TARGET_INDEX]
            child = var_map.get(slot_target)
            if child is None:
                if PostureSpecVariable.SLOT_TEST_DEFINITION not in var_map:
                    if any(runtime_slot.empty for runtime_slot in runtime_slots):
                        return True
                    return False
            else:
                current_slot = child.parent_slot
                if current_slot is not None and slot_manifest_entry.actor is child and current_slot in runtime_slots:
                    return True
        return False
        if PostureSpecVariable.SLOT_TEST_DEFINITION in var_map:
            slot_test_object = DEFAULT
            slot_test_definition = var_map[PostureSpecVariable.SLOT_TEST_DEFINITION]
        else:
            slot_test_object = child
            slot_test_definition = DEFAULT
        carry_target = self[CARRY_INDEX][CARRY_TARGET_INDEX]
        carry_target = var_map.get(carry_target)
        objects_to_ignore = (carry_target,) if carry_target is not None else DEFAULT
        for runtime_slot in runtime_slots:
            if runtime_slot.is_valid_for_placement(obj=slot_test_object, definition=slot_test_definition, objects_to_ignore=objects_to_ignore):
                return True
        return False

    def _validate_subroot(self, interaction, sim):
        body_posture = self.body_posture
        if sim is interaction.sim and body_posture._actor_required_part_definition is not None:
            if self.body_target.is_part and body_posture._actor_required_part_definition is not self.body_target.part_definition:
                return False
        elif sim is interaction.target and (body_posture._actor_b_required_part_definition is not None and self.body_target.is_part) and body_posture._actor_b_required_part_definition is not self.body_target.part_definition:
            return False
        return True

    @property
    def requires_carry_target_in_hand(self):
        return self[CARRY_INDEX][CARRY_TARGET_INDEX] is not None

    @property
    def requires_carry_target_in_slot(self):
        return self[SURFACE_INDEX][SURFACE_SLOT_TARGET_INDEX] is not None

def get_carry_posture_aop(sim, carry_target):
    from postures.posture_interactions import HoldObject
    context = sim.create_posture_interaction_context()
    for aop in carry_target.potential_interactions(context):
        if issubclass(aop.affordance, HoldObject):
            return aop
    logger.error('Sim {} The carry_target: ({}) has no SIs of type HoldObjectCheck that your object has a Carryable Component.', sim, carry_target, owner='camilogarcia')

class PostureOperation:
    DEFAULT_COST_KEY = 'default_cost'
    COST_NOMINAL = Tunable(description='\n        A nominal cost to simple operations just to prevent them from being\n        free.\n        ', tunable_type=float, default=0.1)
    COST_STANDARD = Tunable(description='\n        A cost for standard posture operations (such as changing postures or\n        targets).\n        ', tunable_type=float, default=1.0)

    class OperationBase:
        __slots__ = ()

        def apply(self, node):
            raise NotImplementedError()

        def validate(self, sim, var_map, original_body_target=None):
            return True

        def get_validator(self, next_node):
            return self.validate

        def cost(self, node):
            return {PostureOperation.DEFAULT_COST_KEY: PostureOperation.COST_NOMINAL}

        @property
        def debug_cost_str_list(self):
            pass

        def associated_aop(self, sim, var_map):
            pass

        def is_equivalent_to(self, other):
            raise NotImplementedError

        def get_constraint(self, sim, node, var_map):
            pass

        def set_target(self, target):
            pass

    class BodyTransition(OperationBase):
        __slots__ = ('_posture_type', '_species_to_aops', '_disallowed_ages', 'target')

        def __init__(self, posture_type, species_to_aops, target=None, disallowed_ages=None):
            self._posture_type = posture_type
            self._species_to_aops = species_to_aops
            if disallowed_ages is None:
                disallowed_ages_from_aops = {}
                for (species, aop) in species_to_aops.items():
                    disallowed_ages_from_aops[species] = event_testing.test_utils.get_disallowed_ages(aop.affordance)
                self._disallowed_ages = enumdict(Species, disallowed_ages_from_aops)
            else:
                self._disallowed_ages = enumdict(Species, disallowed_ages)
            if target is None:
                self.target = next(iter(self._species_to_aops.values())).target
            else:
                self.target = target

        def is_equivalent_to(self, other):
            return type(self) == type(other) and (self._species_to_aops[Species.HUMAN].is_equivalent_to(other._species_to_aops[Species.HUMAN]) and self._posture_type == other._posture_type)

        def __repr__(self):
            return '{}({})'.format(type(self).__name__, _str_for_type(self._posture_type))

        @property
        def posture_type(self):
            return self._posture_type

        def set_target(self, target):
            self.target = target

        def all_associated_aops_gen(self):
            for (species, aop) in self._species_to_aops.items():
                yield (species, aop)

        def add_associated_aop(self, species, aop):
            self._species_to_aops[species] = aop

        def associated_aop(self, sim, var_map):
            if sim.species in self._species_to_aops:
                return self._species_to_aops[sim.species]
            logger.error("Trying to get aop for {} in BodyOperation: {} which doesn't exist, using human instead", sim.species, self)
            if Species.HUMAN not in self._species_to_aops:
                logger.error('Failed to get fallback aop for Human species for Sim {} in body operation {}', sim, self)
                return
            return self._species_to_aops[Species.HUMAN]

        def cost(self, node):
            body_index = BODY_INDEX
            body_posture_type_index = BODY_POSTURE_TYPE_INDEX
            body_target_index = BODY_TARGET_INDEX
            curr_body = node[body_index]
            curr_body_target = curr_body[body_target_index]
            curr_posture_type = curr_body[body_posture_type_index]
            next_posture_type = self._posture_type
            current_mobile = curr_posture_type.mobile
            next_mobile = next_posture_type.mobile
            next_body_target = self.target
            base_cost = 0
            if current_mobile != next_mobile:
                base_cost += postures.posture_scoring.PostureScoring.ENTER_EXIT_OBJECT_COST
            if not next_mobile:
                if vector3_almost_equal(curr_body_target.position, next_body_target.position):
                    base_cost += postures.posture_scoring.PostureScoring.INNER_NON_MOBILE_TO_NON_MOBILE_COINCIDENT_COST
                else:
                    base_cost += postures.posture_scoring.PostureScoring.INNER_NON_MOBILE_TO_NON_MOBILE_COST
            if curr_body_target is not next_body_target and (current_mobile or curr_posture_type.multi_sim):
                base_cost += PostureOperation.COST_STANDARD
            costs = dict(curr_posture_type.get_transition_costs(next_posture_type))
            for key in costs:
                costs[key] += base_cost
            return costs

        @property
        def debug_cost_str_list(self):
            return []

        def apply(self, spec):
            if spec[CARRY_INDEX][CARRY_TARGET_INDEX] is not None and not self.posture_type._supports_carry:
                return
            surface_target = spec[SURFACE_INDEX][SURFACE_TARGET_INDEX]
            destination_target = self.target
            if surface_target is not None and destination_target is None:
                return
            body = spec[BODY_INDEX]
            source_target = body[BODY_TARGET_INDEX]
            source_posture_type = body[BODY_POSTURE_TYPE_INDEX]
            if source_posture_type.unconstrained or surface_target is not None and self.posture_type.unconstrained and self.posture_type is not PostureTuning.SIM_CARRIED_POSTURE:
                return
            dest_target_is_not_none = destination_target is not None
            dest_target_parent = None
            if dest_target_is_not_none and (surface_target is not None and destination_target is body.target) and destination_target is not surface_target:
                dest_target_parent = destination_target.parent
                if dest_target_parent is not surface_target:
                    return
            if source_posture_type is self._posture_type:
                if source_target is destination_target:
                    return
                if source_posture_type.mobile and dest_target_is_not_none and source_target is not None:
                    return
            elif source_posture_type.mobile and surface_target is None:
                if self._posture_type.mobile or dest_target_is_not_none and source_target is not None and source_target != destination_target:
                    return
            elif source_posture_type.mobile or not (self._posture_type.mobile and destination_target is not None and self._posture_type.is_vehicle):
                return
            if dest_target_is_not_none and destination_target.is_part and not destination_target.supports_posture_type(self._posture_type):
                return
            targets_match = source_target is destination_target or (destination_target is None or source_target is None)
            if not source_posture_type.is_available_transition(self._posture_type, targets_match):
                return
            if spec[CARRY_INDEX][CARRY_TARGET_INDEX] is not None:
                if destination_target.is_surface():
                    return
                dest_target_parent = dest_target_parent or destination_target.parent
                if dest_target_parent is not None and dest_target_parent.is_surface():
                    return
            if (self._posture_type.unconstrained or destination_target is not None and surface_target is None and destination_target is not body.target) and surface_target is not None:
                dest_target_parent = dest_target_parent or destination_target.parent
                if dest_target_parent is not surface_target:
                    return spec.clone(body=PostureAspectBody((self._posture_type, destination_target)), surface=PostureAspectSurface((destination_target.parent, None, None)))
            return spec.clone(body=PostureAspectBody((self._posture_type, destination_target)))

        def validate(self, node, sim, var_map, original_body_target=None):
            if sim.species in self._disallowed_ages and sim.sim_info.age in self._disallowed_ages[sim.species]:
                return False
            if sim.species not in self._species_to_aops:
                return False
            node_body_target = original_body_target if original_body_target is not None else node.body_target
            if not node.body_posture.is_valid_target(sim, node_body_target):
                return False
            body_target = self.target
            if not self.posture_type.is_valid_target(sim, body_target):
                return False
            resolver = DoubleSimResolver(sim, body_target)
            if not node[BODY_INDEX].posture_type.is_valid_transition(self.posture_type, resolver):
                return False
            if body_target is None:
                return True
            for supported_posture_info in body_target.supported_posture_types:
                if supported_posture_info.posture_type is not self.posture_type:
                    pass
                else:
                    required_clearance = supported_posture_info.required_clearance
                    if required_clearance is None:
                        pass
                    else:
                        transform_vector = body_target.transform.transform_vector(sims4.math.Vector3(0, 0, required_clearance))
                        new_transform = sims4.math.Transform(body_target.transform.translation + transform_vector, body_target.transform.orientation)
                        (result, _) = body_target.check_line_of_sight(new_transform, verbose=True)
                        if not result == routing.RAYCAST_HIT_TYPE_IMPASSABLE:
                            if result == routing.RAYCAST_HIT_TYPE_LOS_IMPASSABLE:
                                return False
                        return False
            next_body_target = node_body_target
            if next_body_target is not None:
                if body_target.is_sim and not next_body_target.is_connected(body_target, ignore_all_objects=True):
                    return False
                elif next_body_target.is_sim and not body_target.is_connected(next_body_target, ignore_all_objects=True):
                    return False
            return True

        def get_validator(self, next_node):
            return functools.partial(self.validate, next_node)

    class PickUpObject(OperationBase):
        __slots__ = ('_posture_type', '_target')

        def __init__(self, posture_type, target):
            self._posture_type = posture_type
            self._target = target

        def __repr__(self):
            return '{}({}, {})'.format(type(self).__name__, _str_for_type(self._posture_type), _str_for_object(self._target))

        @classmethod
        def get_pickup_cost(self, node):
            cost = PostureOperation.COST_STANDARD
            if not node[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile:
                cost += PostureOperation.COST_NOMINAL
            return cost

        def cost(self, node):
            return {PostureOperation.DEFAULT_COST_KEY: self.get_pickup_cost(node)}

        def is_equivalent_to(self, other):
            return type(self) == type(other) and (self._posture_type == other._posture_type and self._target == other._target)

        def associated_aop(self, sim, var_map):
            return get_carry_posture_aop(sim, var_map[self._target])

        def apply(self, node, enter_carry_while_holding=False):
            if self._target is None:
                return
            carry = node[CARRY_INDEX]
            if carry is not None and carry[CARRY_TARGET_INDEX] is not None:
                return
            if not node[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]._supports_carry:
                return
            surface = node[SURFACE_INDEX]
            surface_target = surface[SURFACE_TARGET_INDEX]
            slot_type = surface[SURFACE_SLOT_TYPE_INDEX]
            slot_target = surface[SURFACE_SLOT_TARGET_INDEX]
            carry_aspect = PostureAspectCarry((self._posture_type, self._target, PostureSpecVariable.HAND))
            if slot_target is None:
                surface_aspect = PostureAspectSurface((surface_target, slot_type, slot_target))
            else:
                surface_aspect = PostureAspectSurface((surface_target, None, None))
            return node.clone(carry=carry_aspect, surface=surface_aspect)

        def validate(self, node, sim, var_map, original_body_target=None):
            real_target = var_map[self._target]
            if real_target is None or not real_target.has_component(objects.components.types.CARRYABLE_COMPONENT):
                return False
            body = node[BODY_INDEX]
            if body[BODY_POSTURE_TYPE_INDEX].mobile:
                surface_target = node[SURFACE_INDEX][SURFACE_TARGET_INDEX]
                if surface_target is not None:
                    if real_target.parent is None or not real_target.parent.is_same_object_or_part(surface_target):
                        return False
                elif real_target.parent is not None:
                    return False
            else:
                if real_target.parent is None and real_target.is_in_sim_inventory():
                    return True
                if body[BODY_POSTURE_TYPE_INDEX].unconstrained:
                    if real_target.parent is None:
                        return False
                    if body[BODY_TARGET_INDEX] is None:
                        return False
                    parent = body[BODY_TARGET_INDEX].parent
                    if parent is None:
                        return False
                    if real_target.parent is not parent:
                        return False
                else:
                    constraint = self.get_constraint(sim, node, var_map)
                    for sub_constraint in constraint:
                        if sub_constraint.routing_surface is not None and sub_constraint.routing_surface != body[BODY_TARGET_INDEX].routing_surface:
                            pass
                        elif sub_constraint.geometry is not None and sub_constraint.geometry.contains_point(body[BODY_TARGET_INDEX].position):
                            break
                    return False
            return True

        def get_validator(self, next_node):
            return functools.partial(self.validate, next_node)

        def get_constraint(self, sim, node, var_map, **kwargs):
            carry_target = var_map[PostureSpecVariable.CARRY_TARGET]
            from carry.carry_postures import CarrySystemInventoryTarget, CarrySystemRuntimeSlotTarget, CarrySystemTerrainTarget
            if carry_target.is_in_inventory():
                surface = node[SURFACE_INDEX]
                surface_target = surface[SURFACE_TARGET_INDEX]
                if surface_target is not None and surface_target.inventory_component is not None:
                    carry_system_target = CarrySystemInventoryTarget(sim, carry_target, False, surface_target)
                else:
                    carry_system_target = CarrySystemInventoryTarget(sim, carry_target, False, carry_target.get_inventory().owner)
            elif carry_target.parent_slot is not None:
                carry_system_target = CarrySystemRuntimeSlotTarget(sim, carry_target, False, carry_target.parent_slot)
            else:
                if carry_target.is_sim:
                    carry_constraint = carry_target.posture.get_carry_constraint()
                    if carry_constraint is not None:
                        from interactions.constraints import Anywhere
                        constraint_total = Anywhere()
                        for constraint_factory in carry_constraint:
                            constraint = constraint_factory.create_constraint(sim, target=carry_target)
                            constraint_total = constraint_total.intersect(constraint)

                        def constraint_resolver(animation_participant, default=None):
                            if animation_participant == AnimationParticipant.ACTOR:
                                return sim
                            if animation_participant == AnimationParticipant.CARRY_TARGET:
                                return carry_target
                            elif animation_participant in (AnimationParticipant.SURFACE, AnimationParticipant.TARGET, PostureSpecVariable.INTERACTION_TARGET):
                                return carry_target.posture_state.body.target
                            return default

                        constraint_total = constraint_total.apply_posture_state(None, constraint_resolver)
                        return constraint_total
                carry_system_target = CarrySystemTerrainTarget(sim, carry_target, False, carry_target.transform)
            return carry_system_target.get_constraint(sim, **kwargs)

    STANDARD_PICK_UP_OP = PickUpObject(PostureSpecVariable.POSTURE_TYPE_CARRY_OBJECT, PostureSpecVariable.CARRY_TARGET)

    class PutDownObject(OperationBase):
        __slots__ = ('_posture_type', '_target')

        def __init__(self, posture_type, target):
            self._posture_type = posture_type
            self._target = target

        def is_equivalent_to(self, other):
            return type(self) == type(other) and (self._posture_type == other._posture_type and self._target == other._target)

        def cost(self, node):
            cost = PostureOperation.COST_STANDARD
            if not node[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile:
                cost += PostureOperation.COST_NOMINAL
            return {PostureOperation.DEFAULT_COST_KEY: cost}

        def __repr__(self):
            return '{}({}, {})'.format(type(self).__name__, _str_for_type(self._posture_type), _str_for_object(self._target))

        def apply(self, node):
            carry_aspect = PostureAspectCarry((self._posture_type, None, PostureSpecVariable.HAND))
            return node.clone(carry=carry_aspect)

    class PutDownObjectOnSurface(OperationBase):
        __slots__ = ('_posture_type', '_surface_target', '_slot_type', '_slot_target')

        def __init__(self, posture_type, surface, slot_type, target):
            self._posture_type = posture_type
            self._surface_target = surface
            self._slot_type = slot_type
            self._slot_target = target

        def is_equivalent_to(self, other):
            return type(self) == type(other) and (self._surface_target == other._surface_target and (self._slot_type == other._slot_type and (self._posture_type == other._posture_type and self._slot_target == other._slot_target)))

        def cost(self, node):
            cost = PostureOperation.COST_STANDARD
            if not node[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile:
                cost += PostureOperation.COST_NOMINAL
            return {PostureOperation.DEFAULT_COST_KEY: cost}

        def __repr__(self):
            return '{}({}, {}, {}, {})'.format(type(self).__name__, _str_for_type(self._posture_type), _str_for_object(self._surface_target), _str_for_slot_type(self._slot_type), _str_for_object(self._slot_target))

        def apply(self, node):
            surface = node[SURFACE_INDEX]
            if surface[SURFACE_TARGET_INDEX] != self._surface_target:
                return
            spec_slot_type = surface[SURFACE_SLOT_TYPE_INDEX]
            if spec_slot_type is not None and spec_slot_type != self._slot_type:
                return
            if surface[SURFACE_SLOT_TARGET_INDEX] != None:
                return
            if node[CARRY_INDEX][CARRY_TARGET_INDEX] is None:
                return
            target = node[BODY_INDEX][BODY_TARGET_INDEX]
            if target is not None and not (target == self._surface_target or target.parent == self._surface_target):
                return
            carry_aspect = PostureAspectCarry((self._posture_type, None, PostureSpecVariable.HAND))
            surface_aspect = PostureAspectSurface((self._surface_target, self._slot_type, self._slot_target))
            return node.clone(carry=carry_aspect, surface=surface_aspect)

        def get_constraint(self, sim, node, var_map):
            carry_target = var_map[PostureSpecVariable.CARRY_TARGET]
            parent_slot = var_map.get(PostureSpecVariable.SLOT)
            if PostureSpecVariable.SLOT not in var_map:
                from interactions.constraints import Nowhere
                return Nowhere('PutDownObjectOnSurface.get_constraint, Trying to put an object down, but there is no slot specified. Sim: {}, Node: {}, Var_Map: {}', sim, node, var_map)
            if parent_slot is None or not isinstance(parent_slot, RuntimeSlot):
                if isinstance(parent_slot, animation.posture_manifest.SlotManifestEntry):
                    for parent_slot in self._surface_target.get_runtime_slots_gen(slot_types=parent_slot.slot_types):
                        break
                    raise RuntimeError('Failed to resolve slot on {} of type {}'.format(self._surface_target, parent_slot.slot_types))
                else:
                    for parent_slot in self._surface_target.get_runtime_slots_gen(slot_types={parent_slot}):
                        break
                    raise RuntimeError('Failed to resolve slot on {} of type {}'.format(self._surface_target, {parent_slot}))
            from carry.carry_postures import CarrySystemRuntimeSlotTarget
            carry_system_target = CarrySystemRuntimeSlotTarget(sim, carry_target, True, parent_slot)
            return carry_system_target.get_constraint(sim)

    class TargetAlreadyInSlot(OperationBase):
        __slots__ = ('_slot_target', '_surface_target', '_slot_type')

        def __init__(self, slot_target, surface, slot_type):
            self._slot_target = slot_target
            self._surface_target = surface
            self._slot_type = slot_type

        def __repr__(self):
            return '{}({}, {}, {})'.format(type(self).__name__, _str_for_object(self._slot_target), _str_for_object(self._surface_target), _str_for_slot_type(self._slot_type))

        def is_equivalent_to(self, other):
            return type(self) == type(other) and (self._surface_target == other._surface_target and (self._slot_type == other._slot_type and self._slot_target == other._slot_target))

        def apply(self, node):
            if self._slot_target is not None and node[CARRY_INDEX][CARRY_TARGET_INDEX] is not None:
                return
            surface_spec = node[SURFACE_INDEX]
            if surface_spec[SURFACE_TARGET_INDEX] is not None:
                return
            if surface_spec[SURFACE_SLOT_TARGET_INDEX] is not None:
                return
            target = node[BODY_INDEX][BODY_TARGET_INDEX]
            if target is None:
                return
            if target.is_surface():
                if target is not self._surface_target:
                    return
            elif self._surface_target not in (target, target.parent):
                return
            surface_aspect = PostureAspectSurface((self._surface_target, self._slot_type, self._slot_target))
            return node.clone(surface=surface_aspect)

        def validate(self, sim, var_map, original_body_target=None):
            slot_child = self._slot_target
            if slot_child is None:
                return True
            child = var_map.get(slot_child)
            if child is None:
                return True
            surface = self._surface_target
            if surface is None:
                return False
            if isinstance(child, PostureSpecVariable):
                return False
            if child.parent != surface:
                return False
            slot_type = self._slot_type
            if slot_type is None:
                return True
            slot_manifest = var_map.get(slot_type)
            if slot_manifest is None:
                return True
            else:
                current_slot = child.parent_slot
                if current_slot in surface.get_runtime_slots_gen(slot_types=slot_manifest.slot_types):
                    return True
            return False

    class ForgetSurface(OperationBase):
        __slots__ = ()

        def __init__(self):
            pass

        def __repr__(self):
            return '{}()'.format(type(self).__name__)

        def is_equivalent_to(self, other):
            return type(self) == type(other)

        def apply(self, node):
            surface = node[SURFACE_INDEX]
            if surface[SURFACE_TARGET_INDEX] is not None:
                surface_aspect = PostureAspectSurface((None, None, None))
                return node.clone(surface=surface_aspect)

    FORGET_SURFACE_OP = ForgetSurface()
