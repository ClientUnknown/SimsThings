from collections import OrderedDict, namedtuple, defaultdictfrom contextlib import contextmanagerfrom platform import nodeimport collectionsimport functoolsimport itertoolsimport operatorimport timeimport weakrefimport xml.etreefrom caches import BarebonesCachefrom sims4 import reloadfrom sims4.callback_utils import CallableTestListfrom sims4.collections import frozendict, enumdictfrom sims4.geometry import test_point_in_compound_polygon, QtCirclefrom sims4.log import Logger, StackVarfrom sims4.repr_utils import standard_angle_repr, suppress_quotesfrom sims4.service_manager import Servicefrom sims4.sim_irq_service import yield_to_irqfrom sims4.tuning.geometric import TunableVector2from sims4.tuning.tunable import Tunable, TunableReference, TunableList, TunableMapping, TunableEnumEntryfrom sims4.utils import enumerate_reversedfrom singletons import DEFAULTimport algosimport cachesimport enumimport sims4.geometryimport sims4.mathimport sims4.reloadfrom animation.posture_manifest import SlotManifestEntry, AnimationParticipantfrom animation.posture_manifest_constants import SWIM_AT_NONE_CONSTRAINT, STAND_AT_NONE_CONSTRAINTfrom balloon.passive_balloons import PassiveBalloonsfrom element_utils import build_element, maybefrom event_testing.results import TestResultfrom indexed_manager import CallbackTypesfrom interactions import ParticipantType, constraintsfrom interactions.aop import AffordanceObjectPairfrom interactions.constraints import create_transform_geometry, Anywhere, ANYWHERE, RequiredSlotSingle, create_constraint_set, Constraint, Nowherefrom interactions.context import InteractionContext, QueueInsertStrategy, InteractionSourcefrom interactions.interaction_finisher import FinishingTypefrom interactions.priority import Priorityfrom interactions.utils import routing_constantsfrom interactions.utils.interaction_liabilities import RESERVATION_LIABILITY, ReservationLiabilityfrom interactions.utils.routing import FollowPath, get_route_element_for_path, SlotGoalfrom interactions.utils.routing_constants import TransitionFailureReasonsfrom objects import ALL_HIDDEN_REASONSfrom objects.definition import Definitionfrom objects.helpers.user_footprint_helper import push_route_awayfrom objects.object_enums import ResetReasonfrom objects.pools import pool_utilsfrom objects.proxy import ProxyObjectfrom postures import DerailReasonfrom postures.base_postures import create_puppet_posturesfrom postures.generic_posture_node import SimPostureNodefrom postures.posture import Posturefrom postures.posture_errors import PostureGraphError, PostureGraphMiddlePathErrorfrom postures.posture_scoring import PostureScoring, may_reserve_posture_targetfrom postures.posture_specs import PostureSpecVariable, PostureSpec, PostureOperation, get_origin_spec, get_origin_spec_carry, with_caches, SURFACE_INDEX, BODY_INDEX, SURFACE_TARGET_INDEX, BODY_TARGET_INDEX, BODY_POSTURE_TYPE_INDEX, CARRY_INDEX, CARRY_TARGET_INDEX, SURFACE_SLOT_TYPE_INDEX, SURFACE_SLOT_TARGET_INDEX, get_pick_up_spec_sequence, get_put_down_spec_sequence, destination_test, PostureAspectBody, PostureAspectSurface, _object_additionfrom postures.posture_state_spec import create_body_posture_state_specfrom postures.posture_tuning import PostureTuningfrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom reservation.reservation_handler_multi import ReservationHandlerMultifrom routing import SurfaceTypefrom routing.connectivity import RoutingHandlefrom routing.formation.formation_tuning import FormationTuningfrom routing.formation.formation_type_base import FormationRoutingTypefrom sims.sim_info_types import Speciesfrom world.ocean_tuning import OceanTuningimport build_buyimport debugvisimport element_utilsimport elementsimport event_testing.test_utilsimport gsi_handlers.posture_graph_handlersimport indexed_managerimport interactions.utils.routingimport posturesimport primitives.routing_utilsimport routingimport servicesimport terrainMAX_RIGHT_PATHS = 30NON_OPTIMAL_PATH_DESTINATION = 1000PLACEMENT_FOOTPRINT_HASH_SET = frozenset({sims4.hash_util.hash32('_ftp_placementShape')})logger = Logger('PostureGraph')with sims4.reload.protected(globals()):
    SIM_DEFAULT_POSTURE_TYPE = None
    SIM_DEFAULT_AOPS = None
    SIM_DEFAULT_OPERATION = None
    STAND_AT_NONE = None
    STAND_AT_NONE_CARRY = None
    STAND_AT_NONE_NODES = None
    SIM_SWIM_POSTURE_TYPE = None
    SIM_SWIM_AOPS = None
    SIM_SWIM_OPERATION = None
    SWIM_AT_NONE = None
    SWIM_AT_NONE_CARRY = None
    SWIM_AT_NONE_NODES = None
    _MOBILE_NODES_AT_NONE = None
    _MOBILE_NODES_AT_NONE_CARRY = None
    _DEFAULT_MOBILE_NODES = None
    enable_debug_goals_visualization = False
    on_transition_destinations_changed = sims4.callback_utils.CallableList()InsertionIndexAndSpec = namedtuple('InsertionIndexAndSpec', ['index', 'spec'])
def set_transition_destinations(sim, source_goals, destination_goals, selected_source=None, selected_destination=None, preserve=False, draw_both_sets=False):
    if False and on_transition_destinations_changed:
        transition_destinations = []
        transition_sources = []
        max_dest_cost = 0
        for slot_goal in source_goals:
            slot_transform = sims4.math.Transform(slot_goal.location.position, slot_goal.location.orientation)
            slot_constraint = interactions.constraints.Transform(slot_transform, routing_surface=slot_goal.routing_surface_id)
            if slot_goal is selected_source:
                slot_constraint.was_selected = True
            else:
                slot_constraint.was_selected = False
            transition_sources.append(slot_constraint)
        for slot_goal in destination_goals:
            if slot_goal.cost > max_dest_cost:
                max_dest_cost = slot_goal.cost
            slot_transform = sims4.math.Transform(slot_goal.location.position, slot_goal.location.orientation)
            slot_constraint = interactions.constraints.Transform(slot_transform, routing_surface=slot_goal.routing_surface_id)
            if slot_goal is selected_destination:
                slot_constraint.was_selected = True
            else:
                slot_constraint.was_selected = False
            transition_destinations.append((slot_goal.path_id, slot_constraint, slot_goal.cost))
        on_transition_destinations_changed(sim, transition_destinations, transition_sources, max_dest_cost, preserve=preserve)

def _is_sim_carry(interaction, sim):
    if sim.parent is not None:
        return True
    if interaction.carry_target is sim:
        return True
    if interaction.is_putdown and interaction.target is sim:
        return True
    elif interaction.is_social and interaction.target is sim and interaction.sim is sim.parent:
        return True
    return False

class DistanceEstimator:

    def __init__(self, posture_service, sim, interaction, constraint):
        self.posture_service = posture_service
        self.sim = sim
        self.interaction = interaction
        preferred_objects = interaction.preferred_objects
        self.preferred_objects = preferred_objects
        self.constraint = constraint
        routing_context = sim.get_routing_context()

        @caches.BarebonesCache
        def estimate_connectivity_distance(locations):
            (source_location, dest_location) = locations
            source_locations = ((source_location.transform.translation, source_location.routing_surface),)
            dest_locations = ((dest_location.transform.translation, dest_location.routing_surface),)
            try:
                distance = primitives.routing_utils.estimate_distance_between_multiple_points(source_locations, dest_locations, routing_context)
            except Exception as e:
                logger.warn('{}', e, owner='camilogarcia', trigger_breakpoint=True)
                distance = None
            distance = sims4.math.MAX_FLOAT if distance is None else distance
            return distance

        self.estimate_distance = estimate_distance = estimate_connectivity_distance

        @caches.BarebonesCache
        def get_preferred_object_cost(obj):
            return postures.posture_scoring.PostureScoring.get_preferred_object_cost((obj,), preferred_objects)

        self.get_preferred_object_cost = get_preferred_object_cost

        @caches.BarebonesCache
        def get_inventory_distance(sim_location_inv_node_location_and_mobile):
            (sim_location, inv, node_location, node_body_posture_is_mobile) = sim_location_inv_node_location_and_mobile
            min_dist = sims4.math.MAX_FLOAT
            include_node_location = not node_body_posture_is_mobile or sim_location != node_location
            for owner in inv.owning_objects_gen():
                (routing_position, _) = Constraint.get_validated_routing_position(owner)
                routing_location = routing.Location(routing_position, orientation=owner.orientation, routing_surface=owner.routing_surface)
                distance = estimate_distance((sim_location, routing_location))
                if distance >= min_dist:
                    pass
                else:
                    distance += get_preferred_object_cost(owner)
                    if distance >= min_dist:
                        pass
                    else:
                        if include_node_location:
                            distance += estimate_distance((routing_location, node_location))
                        if distance < min_dist:
                            min_dist = distance
            return min_dist

        self.get_inventory_distance = get_inventory_distance

        @caches.BarebonesCache
        def estimate_location_distance(sim_location_and_target_location_and_mobile):
            (sim_location, target_location, node_body_posture_is_mobile) = sim_location_and_target_location_and_mobile
            if interaction.target is None:
                return estimate_distance((sim_location, target_location))
            carry_target = interaction.carry_target
            if carry_target is None:
                return estimate_distance((sim_location, target_location))
            inv = interaction.target.get_inventory()
            if inv is None:
                interaction_target_routing_location = interaction.target.routing_location
                if interaction_target_routing_location == target_location:
                    return estimate_distance((sim_location, target_location))
                if interaction_target_routing_location.routing_surface.type == SurfaceType.SURFACETYPE_OBJECT:
                    interaction_target_world_routing_location = interaction_target_routing_location.get_world_surface_location()
                else:
                    interaction_target_world_routing_location = None
                if interaction.is_put_in_inventory and node_body_posture_is_mobile and sim_location == target_location:
                    distance = estimate_distance((sim_location, interaction_target_routing_location))
                    if interaction_target_world_routing_location is not None:
                        world_distance = estimate_distance((sim_location, interaction_target_world_routing_location))
                        distance = min(distance, world_distance)
                    return distance
                distance = estimate_distance((sim_location, interaction_target_routing_location)) + estimate_distance((interaction_target_routing_location, target_location))
                if interaction_target_world_routing_location is not None:
                    world_distance = estimate_distance((sim_location, interaction_target_world_routing_location)) + estimate_distance((interaction_target_world_routing_location, target_location))
                    distance = min(distance, world_distance)
                return distance
            if inv.owner.is_sim:
                if inv.owner is not sim:
                    return NON_OPTIMAL_PATH_DESTINATION
                return estimate_distance((sim_location, target_location))
            return get_inventory_distance((sim_location, inv, target_location, node_body_posture_is_mobile))

        self.estimate_location_distance = estimate_location_distance

class PathType(enum.Int, export=False):
    LEFT = 0
    MIDDLE_LEFT = 1
    MIDDLE_RIGHT = 2
    RIGHT = 3

class SegmentedPath:

    def __init__(self, posture_graph, sim, source, destination_specs, var_map, constraint, valid_edge_test, interaction, is_complete=True, distance_estimator=None):
        self.posture_graph = posture_graph
        self.sim = sim
        self.interaction = interaction
        self.source = source
        self.valid_edge_test = valid_edge_test
        self.var_map = var_map
        self._var_map_resolved = None
        self.constraint = constraint
        self.is_complete = is_complete
        if is_complete:
            is_sim_carry = _is_sim_carry(interaction, sim)
            source_body_target = source.body_target
            if is_sim_carry:
                destination_specs = dict(destination_specs)
            elif source_body_target is None:
                destination_specs = {dest: spec for (dest, spec) in destination_specs.items() if dest.body_target is None}
            else:
                if source_body_target.is_part:
                    source_body_target = source_body_target.part_owner
                destination_specs = {dest: spec for (dest, spec) in destination_specs.items() if source_body_target.is_same_object_or_part(dest.body_target)}
        if not destination_specs:
            raise ValueError('Segmented paths need destinations.')
        self.destination_specs = destination_specs
        self.destinations = destination_specs.keys()
        if distance_estimator is None:
            distance_estimator = DistanceEstimator(self.posture_graph, self.sim, self.interaction, constraint)
        self._distance_estimator = distance_estimator

    def teardown(self):
        pass

    @property
    def var_map_resolved(self):
        if self._var_map_resolved is None:
            return self.var_map
        return self._var_map_resolved

    @var_map_resolved.setter
    def var_map_resolved(self, value):
        self._var_map_resolved = value

    def check_validity(self, sim):
        source_spec = sim.posture_state.get_posture_spec(self.var_map)
        return source_spec == self.source

    def generate_left_paths(self):
        left_path_gen = self.posture_graph._left_path_gen(self.sim, self.source, self.destinations, self.interaction, self.constraint, self.var_map, self.valid_edge_test, is_complete=self.is_complete)
        for path_left in left_path_gen:
            path_left.segmented_path = self
            yield path_left

    def generate_right_paths(self, sim, path_left):
        if path_left[-1] in self.destinations and len(self.destinations) == 1:
            cost = self.posture_graph._get_goal_cost(self.sim, self.interaction, self.constraint, self.var_map, path_left[-1])
            path_right = algos.Path([path_left[-1]], cost)
            path_right.segmented_path = self
            yield path_right
            return
        allow_carried = False
        if self.is_complete:
            left_destinations = (path_left[-1],)
        else:
            carry = self.var_map.get(PostureSpecVariable.CARRY_TARGET)
            if carry is sim:
                left_destinations = (path_left[-1],)
                allow_carried = True
            else:
                for constraint in self.constraint:
                    if not constraint.posture_state_spec is not None or not carry is not self.sim or constraint.posture_state_spec.references_object(carry):
                        break
                carry = None
                if carry is not None and path_left[-1].carry_target is None and carry is None or isinstance(carry, Definition):
                    left_destinations = services.posture_graph_service().all_mobile_nodes_at_none_no_carry
                elif carry.is_in_inventory() or carry.parent not in (None, self.sim):
                    left_destinations = STAND_AT_NONE_NODES
                else:
                    left_destinations = (STAND_AT_NONE_CARRY,)
        self.left_destinations = left_destinations
        paths_right = self.posture_graph._right_path_gen(self.sim, self.interaction, self._distance_estimator, left_destinations, self.destinations, self.var_map, self.constraint, self.valid_edge_test, path_left, allow_carried=allow_carried)
        for path_right in paths_right:
            path_right.segmented_path = self
            yield path_right

    def generate_middle_paths(self, path_left, path_right):
        if self.is_complete:
            yield None
            return
        middle_paths = self.posture_graph._middle_path_gen(path_left, path_right, self.sim, self.interaction, self._distance_estimator, self.var_map)
        for path_middle in middle_paths:
            path_middle.segmented_path = self
            yield path_middle

    @property
    def _path(self):
        return algos.Path(list(getattr(self, '_path_left', ['...?'])) + list(getattr(self, '_path_middle', ['...', '...?']) or [])[1:] + list(getattr(self, '_path_right', ['...', '...?']))[1:])

    def __repr__(self):
        if self.is_complete:
            return 'CompleteSegmentedPath(...)'
        return 'SegmentedPath(...)'

class Connectivity:

    def __init__(self, best_complete_path, source_destination_sets, source_middle_sets, middle_destination_sets):
        self.best_complete_path = best_complete_path
        self.source_destination_sets = source_destination_sets
        self.source_middle_sets = source_middle_sets
        self.middle_destination_sets = middle_destination_sets

    def __repr__(self):
        return 'Connectivity%r' % (tuple(self),)

    def __bool__(self):
        return any(self)

    def __iter__(self):
        return iter((self.best_complete_path, self.source_destination_sets, self.source_middle_sets, self.middle_destination_sets))

    def __getitem__(self, i):
        return (self.best_complete_path, self.source_destination_sets, self.source_middle_sets, self.middle_destination_sets)[i]

class TransitionSequenceStage(enum.Int, export=False):
    EMPTY = ...
    TEMPLATES = ...
    PATHS = ...
    CONNECTIVITY = ...
    ROUTES = ...
    ACTOR_TARGET_SYNC = ...
    COMPLETE = ...

class SequenceId(enum.Int, export=False):
    DEFAULT = 0
    PICKUP = 1
    PUTDOWN = 2
_MobileNode = namedtuple('_MobileNode', ('graph_node', 'prev'))COST_DELIMITER_STR = '----------------------------------'
def _shortest_path_gen(sim, sources, destinations, *args, **kwargs):
    if gsi_handlers.posture_graph_handlers.archiver.enabled:
        gsi_handlers.posture_graph_handlers.log_path_cost(sim, COST_DELIMITER_STR, COST_DELIMITER_STR, (COST_DELIMITER_STR,))
        gsi_handlers.posture_graph_handlers.add_heuristic_fn_score(sim, '', COST_DELIMITER_STR, COST_DELIMITER_STR, '')

    def is_destination(node):
        if isinstance(node, _MobileNode):
            node = node.graph_node
        return node in destinations

    fake_paths = algos.shortest_path_gen(sources, is_destination, *args, **kwargs)
    for fake_path in fake_paths:
        path = algos.Path([node.graph_node if isinstance(node, _MobileNode) else node for node in fake_path], fake_path.cost)
        yield path

def set_transition_failure_reason(sim, reason, target_id=None, transition_controller=None):
    if transition_controller is None:
        transition_controller = sim.transition_controller
    if transition_controller is not None:
        transition_controller.set_failure_target(sim, reason, target_id=target_id)

def _cache_global_sim_default_values():
    global SIM_DEFAULT_POSTURE_TYPE, STAND_AT_NONE, STAND_AT_NONE_CARRY, STAND_AT_NONE_NODES, SIM_DEFAULT_AOPS, SIM_DEFAULT_OPERATION, SIM_SWIM_POSTURE_TYPE, SWIM_AT_NONE, SWIM_AT_NONE_CARRY, SWIM_AT_NONE_NODES, SIM_SWIM_AOPS, SIM_SWIM_OPERATION, _MOBILE_NODES_AT_NONE, _MOBILE_NODES_AT_NONE_CARRY, _DEFAULT_MOBILE_NODES
    SIM_DEFAULT_POSTURE_TYPE = PostureGraphService.get_default_affordance(Species.HUMAN).provided_posture_type
    STAND_AT_NONE = get_origin_spec(SIM_DEFAULT_POSTURE_TYPE)
    STAND_AT_NONE_CARRY = get_origin_spec_carry(SIM_DEFAULT_POSTURE_TYPE)
    STAND_AT_NONE_NODES = (STAND_AT_NONE, STAND_AT_NONE_CARRY)
    SIM_DEFAULT_AOPS = enumdict(Species, {species: AffordanceObjectPair(affordance, None, affordance, None, force_inertial=True) for (species, affordance) in PostureGraphService.SIM_DEFAULT_AFFORDANCES.items()})
    SIM_DEFAULT_OPERATION = PostureOperation.BodyTransition(SIM_DEFAULT_POSTURE_TYPE, SIM_DEFAULT_AOPS)
    SIM_SWIM_POSTURE_TYPE = PostureGraphService.get_default_swim_affordance(Species.HUMAN).provided_posture_type
    SWIM_AT_NONE = get_origin_spec(SIM_SWIM_POSTURE_TYPE)
    SWIM_AT_NONE_CARRY = get_origin_spec_carry(SIM_SWIM_POSTURE_TYPE)
    SWIM_AT_NONE_NODES = (SWIM_AT_NONE, SWIM_AT_NONE_CARRY)
    SIM_SWIM_AOPS = enumdict(Species, {species: AffordanceObjectPair(affordance, None, affordance, None, force_inertial=True) for (species, affordance) in PostureGraphService.SWIM_DEFAULT_AFFORDANCES.items()})
    SIM_SWIM_OPERATION = PostureOperation.BodyTransition(SIM_SWIM_POSTURE_TYPE, SIM_SWIM_AOPS)
    _MOBILE_NODES_AT_NONE = {STAND_AT_NONE}
    _MOBILE_NODES_AT_NONE_CARRY = {STAND_AT_NONE_CARRY}
    _DEFAULT_MOBILE_NODES = {STAND_AT_NONE, STAND_AT_NONE_CARRY}
    for affordance in PostureGraphService.POSTURE_PROVIDING_AFFORDANCES:
        if affordance.provided_posture_type is not None and affordance.provided_posture_type.mobile and not affordance.provided_posture_type.skip_route:
            posture_type = affordance.provided_posture_type
            mobile_node_at_none = get_origin_spec(posture_type)
            _MOBILE_NODES_AT_NONE.add(mobile_node_at_none)
            _DEFAULT_MOBILE_NODES.add(mobile_node_at_none)
            if posture_type._supports_carry:
                mobile_node_at_none_carry = get_origin_spec_carry(posture_type)
                _MOBILE_NODES_AT_NONE_CARRY.add(mobile_node_at_none_carry)
                _DEFAULT_MOBILE_NODES.add(mobile_node_at_none_carry)

def get_mobile_posture_constraint(posture=None, target=None):
    posture_manifests = []
    body_target = target
    if posture is not None:
        if posture is SIM_DEFAULT_POSTURE_TYPE:
            return STAND_AT_NONE_CONSTRAINT
        if posture is SIM_SWIM_POSTURE_TYPE:
            return SWIM_AT_NONE_CONSTRAINT
        if not posture.mobile:
            logger.error('Cannot create mobile posture constraint from non-mobile posture {}', posture)
            return Nowhere('Mobile posture override {} is not actually mobile.', posture)
        else:
            posture_manifests = [posture.get_provided_postures()]
            if posture_manifests or target is not None:
                for mobile_posture in target.provided_mobile_posture_types:
                    posture_manifests.append(mobile_posture.get_provided_postures())
                    body_target = None
                    break
            elif target.routing_component is None:
                body_target = PostureSpecVariable.ANYTHING
            constraints = []
            for manifest in posture_manifests:
                posture_state_spec = create_body_posture_state_spec(manifest, body_target=body_target)
                constraint = Constraint(debug_name='MobilePosture@None', posture_state_spec=posture_state_spec)
                constraints.append(constraint)
            if constraints:
                return create_constraint_set(constraints, debug_name='MobilePostureConstraints')
    if posture_manifests or target is not None:
        for mobile_posture in target.provided_mobile_posture_types:
            posture_manifests.append(mobile_posture.get_provided_postures())
            body_target = None
            break
    elif target.routing_component is None:
        body_target = PostureSpecVariable.ANYTHING
    constraints = []
    for manifest in posture_manifests:
        posture_state_spec = create_body_posture_state_spec(manifest, body_target=body_target)
        constraint = Constraint(debug_name='MobilePosture@None', posture_state_spec=posture_state_spec)
        constraints.append(constraint)
    if constraints:
        return create_constraint_set(constraints, debug_name='MobilePostureConstraints')
    return STAND_AT_NONE_CONSTRAINT

def is_object_mobile_posture_compatible(obj):
    return any(posture_type.posture_objects is not None for posture_type in obj.provided_mobile_posture_types)

@contextmanager
def supress_posture_graph_build(rebuild=True):
    posture_graph_service = services.current_zone().posture_graph_service
    posture_graph_service.disable_graph_building()
    try:
        yield None
    finally:
        posture_graph_service.enable_graph_building()
        if rebuild:
            posture_graph_service.rebuild()

def can_remove_blocking_sims(sim, interaction, required_targets):
    need_to_cancel = []
    blocking_sims = set()
    for obj in required_targets:
        obj_users = obj.get_users()
        if obj.is_part:
            obj = obj.part_owner
            obj_users = obj.get_users()
        for blocking_sim in obj_users:
            if blocking_sim is sim:
                pass
            else:
                if not blocking_sim.is_sim:
                    return (False, need_to_cancel, blocking_sims)
                for blocking_si in blocking_sim.si_state:
                    if not obj.is_same_object_or_part(blocking_si.target):
                        pass
                    else:
                        if blocking_si.can_shoo and blocking_si.priority >= interaction.priority:
                            return (False, need_to_cancel, blocking_sims)
                        need_to_cancel.append(blocking_si)
                        blocking_sims.add(blocking_sim)
    return (True, need_to_cancel, blocking_sims)

class TransitionSpec:
    DISTANCE_TO_FADE_SIM_OUT = Tunable(description='\n        Distance at which a Sim will start fading out if tuned as such.\n        ', tunable_type=float, default=5.0)

    def __init__(self, path_spec, posture_spec, var_map, sequence_id=SequenceId.DEFAULT, portal_obj=None, portal_id=None):
        self.posture_spec = posture_spec
        self._path_spec = path_spec
        self.var_map = var_map
        self.path = None
        self.final_constraint = None
        self._transition_interactions = {}
        self.sequence_id = sequence_id
        self.locked_params = frozendict()
        self._additional_reservation_handlers = []
        self.handle_slot_reservations = False
        self._portal_ref = portal_obj.ref() if portal_obj is not None else None
        self.portal_id = portal_id
        self.created_posture_state = None

    @property
    def mobile(self):
        return self.posture_spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile

    @property
    def is_failure_path(self):
        return self._path_spec.is_failure_path

    @property
    def final_si(self):
        return self._path_spec._final_si

    @property
    def is_carry(self):
        return self.posture_spec[CARRY_INDEX][CARRY_TARGET_INDEX] is not None

    @property
    def targets_empty_slot(self):
        surface_spec = self.posture_spec[SURFACE_INDEX]
        if surface_spec[SURFACE_SLOT_TYPE_INDEX] is not None and surface_spec[SURFACE_SLOT_TARGET_INDEX] is None:
            return True
        return False

    @property
    def portal_obj(self):
        if self._portal_ref is not None:
            return self._portal_ref()

    @portal_obj.setter
    def portal_obj(self, value):
        if value is None:
            self._portal_ref = None
        elif issubclass(value.__class__, ProxyObject):
            self._portal_ref = value.ref()
        else:
            self._portal_ref = weakref.ref(value)

    def transition_interactions(self, sim):
        if sim in self._transition_interactions:
            return self._transition_interactions[sim]
        return []

    def test_transition_interactions(self, sim, interaction):
        if sim in self._transition_interactions:
            for (si, _) in self._transition_interactions[sim]:
                if si is interaction:
                    pass
                elif si is not None and not si.aop.test(si.context):
                    return False
        return True

    def get_multi_target_interaction(self, sim):
        final_si = self._path_spec._final_si
        if sim in self._transition_interactions:
            for (si, _) in self._transition_interactions[sim]:
                if si is not final_si:
                    return si

    def set_path(self, path, final_constraint):
        self.path = path
        if final_constraint is not None and final_constraint.tentative:
            logger.warn("TransitionSpec's final constraint is tentative, this will not work correctly so the constraint will be ignored. This may interfere with slot reservation.", owner='jpollak')
        else:
            self.final_constraint = final_constraint

    def transfer_route_to(self, other_spec):
        other_spec.path = self.path
        self.path = None

    def add_transition_interaction(self, sim, interaction, var_map):
        if interaction is not None and not interaction.get_participant_type(sim) == ParticipantType.Actor:
            return
        if sim not in self._transition_interactions:
            self._transition_interactions[sim] = []
        self._transition_interactions[sim].append((interaction, var_map))

    def set_locked_params(self, locked_params):
        self.locked_params = locked_params

    def __repr__(self):
        args = [self.posture_spec]
        kwargs = {}
        if self.path is not None:
            args.append(suppress_quotes('has_route'))
        if self.locked_params:
            kwargs['locked_params'] = self.locked_params
        if self.final_constraint is not None:
            kwargs['final_constraint'] = self.final_constraint
        return standard_angle_repr(self, *args, **kwargs)

    def release_additional_reservation_handlers(self):
        for handler in self._additional_reservation_handlers:
            handler.end_reservation()
        self._additional_reservation_handlers.clear()

    def remove_props_created_to_reserve_slots(self, sim):
        if self._transition_interactions is not None:
            for (reservation_si, _) in self._transition_interactions.get(sim, ()):
                if reservation_si is not None:
                    reservation_si.animation_context.clear_reserved_slots()

    def do_reservation(self, sim, is_failure_path=False):

        def cancel_reservations():
            for handler in reserve_object_handlers:
                handler.end_reservation()

        def add_reservation(handler, test_only=False):
            reserve_result = handler.may_reserve()
            if not reserve_result:
                logger.info('Transition Reservation Failure, Obj: {}, Handler: {}', reserve_result.result_obj, handler)
                set_transition_failure_reason(sim, TransitionFailureReasons.RESERVATION, target_id=reserve_result.result_obj.id)
                if not test_only:
                    cancel_reservations()
                return reserve_result
            if not test_only:
                handler.begin_reservation()
                reserve_object_handlers.add(handler)
            return reserve_result

        try:
            reserve_object_handlers = set()
            reservations_sis = []
            reservation_spec = self
            if reservation_spec is not None:
                if sim in reservation_spec._transition_interactions:
                    reservations_sis.extend(reservation_spec._transition_interactions[sim])
                reservation_spec = self._path_spec.get_next_transition_spec(reservation_spec)
                if reservation_spec is not None and reservation_spec.path is not None:
                    break
            if is_failure_path and not reservations_sis:
                return False
            for (si, _) in reservations_sis:
                if si is None:
                    pass
                else:
                    if si.is_putdown:
                        (target_si, _) = si.get_target_si()
                        if target_si is not None:
                            si = target_si
                            sim = si.sim
                    if si.get_liability(RESERVATION_LIABILITY) is not None:
                        pass
                    else:
                        handler = si.get_interaction_reservation_handler(sim=sim)
                        if is_failure_path and handler is None:
                            pass
                        else:
                            if handler is not None:
                                handlers = []
                                if is_failure_path:
                                    reserve_result = add_reservation(handler, test_only=True)
                                else:
                                    reserve_result = add_reservation(handler)
                                if not reserve_result:
                                    if si.source == InteractionSource.BODY_CANCEL_AOP or si.source == InteractionSource.CARRY_CANCEL_AOP:
                                        logger.warn('{} failed to pass reservation tests as a cancel AOP. Result: {}', si, reserve_result, owner='cgast')
                                    else:
                                        if si.priority == Priority.Low:
                                            return False
                                        (able_to_cancel_blockers, need_to_cancel, blocking_sims) = can_remove_blocking_sims(sim, si, handler.get_targets())
                                        if not able_to_cancel_blockers:
                                            return False
                                        if need_to_cancel:
                                            for blocking_si in need_to_cancel:
                                                blocking_si.cancel_user('Sim was kicked out by another Sim with a higher priority interaction.')
                                            for blocking_sim in blocking_sims:
                                                push_route_away(blocking_sim)
                                            sim.queue.transition_controller.add_blocked_si(si)
                                            sim.queue.transition_controller.derail(DerailReason.WAIT_FOR_BLOCKING_SIMS, sim)
                                        return False
                                        if is_failure_path:
                                            return False
                                        handlers.append(handler)
                                        liability = ReservationLiability(handlers)
                                        si.add_liability(RESERVATION_LIABILITY, liability)
                                        next_spec = self._path_spec.get_next_transition_spec(self)
                                        if next_spec is not None:
                                            target_set = set()
                                            target_set.add(next_spec.posture_spec.body_target)
                                            target_set.add(next_spec.posture_spec.surface_target)
                                            for target in target_set:
                                                if not target is None:
                                                    if handler is not None and target in handler.get_targets():
                                                        pass
                                                    else:
                                                        target_handler = ReservationHandlerMulti(sim, target, reservation_interaction=si, reservation_limit=None)
                                                        if add_reservation(target_handler):
                                                            self._additional_reservation_handlers.append(target_handler)
                                if is_failure_path:
                                    return False
                                handlers.append(handler)
                                liability = ReservationLiability(handlers)
                                si.add_liability(RESERVATION_LIABILITY, liability)
                            next_spec = self._path_spec.get_next_transition_spec(self)
                            if next_spec is not None:
                                target_set = set()
                                target_set.add(next_spec.posture_spec.body_target)
                                target_set.add(next_spec.posture_spec.surface_target)
                                for target in target_set:
                                    if not target is None:
                                        if handler is not None and target in handler.get_targets():
                                            pass
                                        else:
                                            target_handler = ReservationHandlerMulti(sim, target, reservation_interaction=si, reservation_limit=None)
                                            if add_reservation(target_handler):
                                                self._additional_reservation_handlers.append(target_handler)
            if is_failure_path:
                return False
            if self.handle_slot_reservations:
                object_to_ignore = []
                for (transition_si, _) in self._transition_interactions[sim]:
                    if transition_si.process.previous_ico is not None:
                        object_to_ignore.append(transition_si.process.previous_ico)
                    if hasattr(transition_si, 'process') and transition_si.process is not None and transition_si.process.current_ico is not None:
                        object_to_ignore.append(transition_si.process.current_ico)
                cur_spec = self
                slot_manifest_entries = []
                while cur_spec is not None:
                    if cur_spec.path is not None:
                        break
                    if cur_spec is not self and cur_spec.handle_slot_reservations:
                        if PostureSpecVariable.SLOT in cur_spec.var_map:
                            slot_entry = cur_spec.var_map[PostureSpecVariable.SLOT]
                            if slot_entry is not None:
                                slot_manifest_entries.append(slot_entry)
                                cur_spec.handle_slot_reservations = False
                        else:
                            logger.error('Trying to reserve a surface with no PostureSpecVariable.SLOT in the var_map.\n    Sim: {}\n    Spec: {}\n    Var_map: {}\n    Transition: {}', sim, cur_spec, cur_spec.var_map, cur_spec._path_spec.path)
                    cur_spec = self._path_spec.get_next_transition_spec(cur_spec)
                if slot_manifest_entries:
                    final_animation_context = self.final_si.animation_context
                    for slot_manifest_entry in slot_manifest_entries:
                        slot_result = final_animation_context.update_reserved_slots(slot_manifest_entry, sim, objects_to_ignore=object_to_ignore)
                        if not slot_result:
                            set_transition_failure_reason(sim, TransitionFailureReasons.RESERVATION, target_id=slot_manifest_entry.target.id if slot_manifest_entry.target is not None else None)
                            cancel_reservations()
                            return TestResult(False, 'Slot Reservation Failed for {}'.format(self.final_si))
            return TestResult.TRUE
        except:
            cancel_reservations()
            logger.exception('Exception reserving for transition: {}', self)
            raise

    def get_approaching_portal(self):
        next_transition_spec = self._path_spec.get_next_transition_spec(self)
        if next_transition_spec is not None and next_transition_spec.portal_obj is not None:
            return (next_transition_spec.portal_obj, next_transition_spec.portal_id)
        return (None, None)

    def get_transition_route(self, sim, fade_out, lock_out_socials, dest_posture):
        if self.path is None:
            return
        fade_sim_out = fade_out or sim.is_hidden()
        reserve = True
        fire_service = services.get_fire_service()

        def route_callback(distance_left):
            nonlocal reserve, fade_sim_out
            if self.is_failure_path or distance_left < FollowPath.DISTANCE_TO_RECHECK_STAND_RESERVATION and sim.routing_component.on_slot is not None:
                transition_controller = sim.queue.transition_controller
                excluded_sims = transition_controller.get_transitioning_sims() if transition_controller is not None else ()
                violators = tuple(violator for violator in sim.routing_component.get_stand_slot_reservation_violators(excluded_sims=excluded_sims) if violator.parent not in excluded_sims)
                if violators:
                    if transition_controller is not None:
                        transition_controller.derail(DerailReason.WAIT_FOR_BLOCKING_SIMS, sim)
                    return FollowPath.Action.CANCEL
            if reserve and distance_left < FollowPath.DISTANCE_TO_RECHECK_INUSE:
                reserve = False
                (portal_obj, portal_id) = self.get_approaching_portal()
                if portal_obj is not None:
                    portal_cost_override = portal_obj.get_portal_cost_override(portal_id)
                    if portal_cost_override == routing.PORTAL_USE_LOCK:
                        transition_controller = sim.queue.transition_controller
                        if transition_controller is not None:
                            transition_controller.derail(DerailReason.WAIT_FOR_BLOCKING_SIMS, sim)
                        return FollowPath.Action.CANCEL
                    if portal_obj.lock_portal_on_use(portal_id):
                        portal_obj.set_portal_cost_override(portal_id, routing.PORTAL_USE_LOCK, sim=sim)
                if not self.do_reservation(sim, is_failure_path=self.is_failure_path):
                    return FollowPath.Action.CANCEL
            if distance_left < TransitionSpec.DISTANCE_TO_FADE_SIM_OUT:
                if fade_sim_out:
                    fade_sim_out = False
                    dest_posture.sim.fade_out()
                if lock_out_socials:
                    sim.socials_locked = True
            time_now = services.time_service().sim_now
            if self.is_failure_path or time_now > sim.next_passive_balloon_unlock_time:
                PassiveBalloons.request_passive_balloon(sim, time_now)
            if fire_service.check_for_catching_on_fire(sim):
                if sim.queue.running is not None:
                    sim.queue.running.route_fail_on_transition_fail = False
                return FollowPath.Action.CANCEL
            return FollowPath.Action.CONTINUE

        def should_fade_in():
            if not fade_sim_out:
                return self.path.length() > 0
            return False

        return build_element((maybe(should_fade_in, build_element(lambda _: dest_posture.sim.fade_in())), get_route_element_for_path(sim, self.path, interaction=sim.queue.transition_controller.interaction, callback_fn=route_callback, handle_failure=True)))

class PathSpec:

    def __init__(self, path, path_cost, var_map, destination_spec, final_constraint, spec_constraint, path_as_posture_specs=True, is_failure_path=False, allow_tentative=False, failed_path_type=None):
        if path is not None and path_as_posture_specs:
            self._path = []
            for posture_spec in path:
                self._path.append(TransitionSpec(self, posture_spec, var_map))
        else:
            self._path = path
            if self._path is not None:
                for transition_spec in self._path:
                    transition_spec._path_spec = self
        self.cost = path_cost
        self.destination_spec = destination_spec
        self.completed_path = False
        self._path_progress = 0
        self._is_failure_path = is_failure_path
        self._failed_path_type = failed_path_type
        if allow_tentative or final_constraint is not None and final_constraint.tentative:
            logger.warn("PathSpec's final constraint is tentative, this will not work correctly so the constraint will be ignored. This may interfere with slot reservation.", owner='jpollak')
            self._final_constraint = None
        else:
            self._final_constraint = final_constraint
        self._spec_constraint = spec_constraint
        self._final_si = None

    def __repr__(self):
        if self._path:
            posture_specs = ['({}{}{})'.format(transition_spec.posture_spec, '(R)' if transition_spec.path is not None else '', '(P)' if transition_spec.portal_obj is not None else '') for transition_spec in self._path]
            if self.is_failure_path:
                return 'FAILURE PATH: PathSpec[{}]'.format('->'.join(posture_specs))
            else:
                return 'PathSpec[{}]'.format('->'.join(posture_specs))
        return 'PathSpec[Empty]'

    def __bool__(self):
        return bool(self._path)

    @property
    def path(self):
        if self._path is not None:
            return [transition_spec.posture_spec for transition_spec in self._path]
        return []

    @property
    def transition_specs(self):
        return self._path

    @property
    def path_progress(self):
        return self._path_progress

    @property
    def total_cost(self):
        return self.cost + self.routing_cost

    @property
    def routing_cost(self):
        routing_cost = 0
        if self._path is not None:
            for trans_spec in self._path:
                if trans_spec.path is not None:
                    routing_cost += trans_spec.path.length()
        return routing_cost

    @property
    def var_map(self):
        if self._path is not None:
            return self._path[self._path_progress].var_map
        return [{}]

    @property
    def remaining_path(self):
        if self._path is not None and not self.completed_path:
            return [transition_spec.posture_spec for transition_spec in self._path[self._path_progress:]]
        return []

    @property
    def is_failure_path(self):
        return self._is_failure_path

    @property
    def failed_path_type(self):
        return self._failed_path_type

    def remaining_original_transition_specs(self):
        original_transition_specs = []
        if not self.completed_path:
            for spec in self._path[self._path_progress:]:
                if spec.sequence_id == SequenceId.DEFAULT:
                    original_transition_specs.append(spec)
        return original_transition_specs

    @property
    def previous_posture_spec(self):
        previous_progress = self._path_progress - 1
        if previous_progress < 0 or previous_progress >= len(self._path):
            return
        return self._path[previous_progress].posture_spec

    @property
    def previous_transition_spec(self):
        previous_progress = self._path_progress - 1
        if previous_progress < 0 or previous_progress >= len(self._path):
            return
        return self._path[previous_progress]

    @property
    def final_constraint(self):
        if self._final_constraint is not None:
            return self._final_constraint
        if self._path is None:
            return
        for transition_spec in reversed(self._path):
            if transition_spec.final_constraint is not None:
                return transition_spec.final_constraint

    @property
    def final_routing_location(self):
        for transition_spec in reversed(self._path):
            if transition_spec.path is not None:
                return transition_spec.path.final_location

    @property
    def spec_constraint(self):
        return self._spec_constraint

    def advance_path(self):
        new_progress = self._path_progress + 1
        if new_progress < len(self._path):
            self._path_progress = new_progress
        else:
            self.completed_path = True

    def get_spec(self):
        return self._path[self._path_progress].posture_spec

    def get_transition_spec(self):
        return self._path[self._path_progress]

    def get_transition_should_reserve(self):
        for (i, transition_spec) in enumerate_reversed(self._path):
            if transition_spec.path is not None:
                return self._path_progress >= i
        return True

    def get_next_transition_spec(self, transition_spec):
        if self._path is None:
            return
        for (index, cur_transition_spec) in enumerate(self._path):
            if cur_transition_spec is transition_spec:
                next_index = index + 1
                if next_index < len(self._path):
                    return self._path[next_index]

    def cleanup_path_spec(self, sim):
        transition_specs = self.transition_specs
        if transition_specs is None:
            return
        cleanup_portal_costs = not services.current_zone().is_zone_shutting_down
        for transition_spec in transition_specs:
            if transition_spec.created_posture_state is not None:
                for aspect in transition_spec.created_posture_state.aspects:
                    if aspect not in sim.posture_state.aspects:
                        aspect.reset()
                transition_spec.created_posture_state = None
            if transition_spec.path is not None:
                transition_spec.path.remove_intended_location_from_quadtree()
            portal_obj = transition_spec.portal_obj
            if cleanup_portal_costs and portal_obj is not None and sim not in portal_obj.get_users():
                portal_obj.clear_portal_cost_override(transition_spec.portal_id, sim=sim)
            for (interaction, _) in transition_spec.transition_interactions(sim):
                if interaction is not None and interaction not in sim.queue and interaction not in sim.si_state:
                    interaction.release_liabilities()

    def insert_transition_specs_at_index(self, i, new_specs):
        self._path[i:i] = new_specs

    def combine(self, *path_specs):
        full_path = self._path
        cost = self.cost
        final_constraint = self.final_constraint
        spec_constraint = self.spec_constraint
        is_failure_path = False
        for path_spec in path_specs:
            if not path_spec._path:
                raise AssertionError('Trying to combine two paths when one of them is None!')
            if full_path[-1].posture_spec != path_spec._path[0].posture_spec:
                raise AssertionError("Trying to combine two paths that don't have a common node on the ends {} != {}.\nThis may be caused by handles being generated for complete paths.".format(self.path[-1], path_spec.path[0]))
            if full_path[-1].mobile and path_spec._path[0].path is not None:
                full_path = list(itertools.chain(full_path, path_spec._path))
            else:
                if full_path[-1].locked_params:
                    path_spec._path[0].locked_params = full_path[-1].locked_params
                if full_path[-1].portal_obj:
                    path_spec._path[0].portal_obj = full_path[-1].portal_obj
                    path_spec._path[0].portal_id = full_path[-1].portal_id
                if full_path[-1].path is not None:
                    path_spec._path[0].path = full_path[-1].path
                full_path = list(itertools.chain(full_path[:-1], path_spec._path))
            cost = cost + path_spec.cost
            final_constraint = path_spec.final_constraint
            spec_constraint = path_spec.spec_constraint
            is_failure_path = is_failure_path or path_spec.is_failure_path
        return PathSpec(full_path, cost, None, path_spec.destination_spec, final_constraint, spec_constraint, path_as_posture_specs=False, is_failure_path=is_failure_path)

    def get_carry_sim_merged_path_spec(self):
        if not any(n[BODY_INDEX][BODY_TARGET_INDEX] is not None and n[BODY_INDEX][BODY_TARGET_INDEX].is_sim for n in self.path):
            return self
        else:
            other_index = None
            for (index, node) in enumerate(self.path):
                node_target = node[BODY_INDEX][BODY_TARGET_INDEX]
                if node_target is None:
                    pass
                else:
                    for (_other_index, other_node) in enumerate(self.path[index + 1:]):
                        if node == other_node:
                            other_index = _other_index + index + 1
                            break
                    if other_index:
                        break
            if other_index:
                full_path = self._path[:index] + self._path[other_index:]
                return PathSpec(full_path, self.cost, self.var_map, self.destination_spec, self.final_constraint, self.spec_constraint, path_as_posture_specs=False, is_failure_path=self._is_failure_path, failed_path_type=self._failed_path_type)
        return self

    def get_stand_to_carry_sim_direct_path_spec(self):
        if self is EMPTY_PATH_SPEC or self.path[0][BODY_INDEX][BODY_POSTURE_TYPE_INDEX] is not SIM_DEFAULT_POSTURE_TYPE:
            return self
        else:
            sim_stand_posture_index = 0
            sim_carried_posture_index = 0
            sim_carried_posture_type = PostureTuning.SIM_CARRIED_POSTURE
            for (index, node) in enumerate(self.path):
                node_posture_type = node[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]
                if node_posture_type is SIM_DEFAULT_POSTURE_TYPE:
                    sim_stand_posture_index = index
                elif node_posture_type is sim_carried_posture_type:
                    sim_carried_posture_index = index
                    break
            if sim_carried_posture_index - sim_stand_posture_index > 1:
                full_path = self._path[:1] + self._path[sim_carried_posture_index:]
                return PathSpec(full_path, self.cost, self.var_map, self.destination_spec, self.final_constraint, self.spec_constraint, path_as_posture_specs=False, is_failure_path=self._is_failure_path, failed_path_type=self._failed_path_type)
        return self

    def edge_exists(self, spec_a_type, spec_b_type):
        for (cur_spec, next_spec) in zip(self.path, self.path[1:]):
            cur_spec_type = cur_spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]
            next_spec_type = next_spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]
            if cur_spec_type == spec_a_type and next_spec_type == spec_b_type:
                return True
        return False

    def get_failure_reason_and_object_id(self):
        if self._path is not None:
            for trans_spec in self._path:
                if trans_spec.path is not None and trans_spec.path.is_route_fail():
                    return (trans_spec.path.nodes.plan_failure_path_type, trans_spec.path.nodes.plan_failure_object_id)
        return (None, None)

    def create_route_nodes(self, path, portal_obj=None, portal_id=None):
        final_node = self._path[-1]
        if not final_node.mobile:
            raise ValueError('PathSpec: Trying to turn a non-mobile node into a route: {}'.format(self._path))
        if portal_obj is None:
            posture_specs = (final_node.posture_spec,)
        else:
            (posture_spec_enter, posture_spec_exit) = portal_obj.get_posture_change(portal_id, final_node.posture_spec)
            if posture_spec_enter is posture_spec_exit:
                posture_specs = (posture_spec_enter,)
            else:
                posture_specs = (posture_spec_enter, posture_spec_exit)
        if len(posture_specs) == 1:
            new_transition_spec = TransitionSpec(self, posture_specs[0], final_node.var_map, portal_obj=portal_obj, portal_id=portal_id)
        else:
            new_transition_spec = TransitionSpec(self, posture_specs[0], final_node.var_map)
        new_transition_spec.set_path(path, None)
        prev_posture_type = self._path[-1].posture_spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]
        next_posture_type = new_transition_spec.posture_spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]
        if not prev_posture_type.is_available_transition(next_posture_type):
            return False
        self._path.append(new_transition_spec)
        for posture_spec in posture_specs[1:]:
            new_transition_spec = TransitionSpec(self, posture_spec, final_node.var_map, portal_obj=portal_obj, portal_id=portal_id)
            self._path.append(new_transition_spec)
        return True

    def attach_route_and_params(self, path, locked_params, final_constraint, reverse=False):
        if reverse:
            sequence = reversed(self._path)
        else:
            sequence = self._path
        previous_spec = None
        route_spec = None
        locked_param_spec = None
        carry_spec = None
        for transition_spec in sequence:
            if not transition_spec.posture_spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].unconstrained:
                if route_spec is None:
                    route_spec = previous_spec if previous_spec is not None else transition_spec
                if reverse and previous_spec is not None:
                    locked_param_spec = previous_spec
                else:
                    locked_param_spec = transition_spec
                break
            if transition_spec.is_carry:
                carry_spec = transition_spec
            if carry_spec is None and route_spec is None:
                if reverse or transition_spec.posture_spec[BODY_INDEX][BODY_TARGET_INDEX] is not None:
                    route_spec = previous_spec if previous_spec is not None else transition_spec
                elif previous_spec.posture_spec[CARRY_INDEX][CARRY_TARGET_INDEX] is not None != transition_spec.posture_spec[CARRY_INDEX][CARRY_TARGET_INDEX] is not None:
                    route_spec = previous_spec
            previous_spec = transition_spec
        if locked_param_spec is None:
            locked_param_spec = transition_spec
        if route_spec is None:
            route_spec = transition_spec
        route_spec.set_path(path, final_constraint)
        locked_param_spec.set_locked_params(locked_params)
        if carry_spec is not None:
            carry_spec.set_locked_params(locked_params)

    def adjust_route_for_sim_inventory(self):
        spec_to_destination = None
        spec_for_pick_up_route = None
        for transition_spec in reversed(self._path):
            if transition_spec.path is not None:
                if transition_spec.path.portal_obj is not None:
                    return
                if spec_to_destination is None:
                    spec_to_destination = transition_spec
                else:
                    spec_for_pick_up_route = transition_spec
                    break
        if spec_to_destination is not None and spec_for_pick_up_route is not None and spec_to_destination.path.length_squared() > 0:
            spec_to_destination.transfer_route_to(spec_for_pick_up_route)

    def unlock_portals(self, sim):
        if self._path is not None:
            for transition_spec in self._path:
                portal_obj = transition_spec.portal_obj
                if portal_obj is not None:
                    portal_obj.clear_portal_cost_override(transition_spec.portal_id, sim=sim)

    def finalize(self, sim):
        if self.path is not None and len(self.path) > 0:
            final_destination = self.path[-1]
            final_var_map = self._path[-1].var_map
            interaction_target = final_var_map[PostureSpecVariable.INTERACTION_TARGET]
            if interaction_target is not None:
                for path_node in self._path:
                    if PostureSpecVariable.INTERACTION_TARGET not in path_node.var_map:
                        pass
                    else:
                        for obj in final_destination.get_core_objects():
                            if obj.id != interaction_target.id:
                                pass
                            else:
                                new_interaction_target = interaction_target.resolve_retarget(obj)
                                path_node.var_map += {PostureSpecVariable.INTERACTION_TARGET: new_interaction_target}
            carry_target = final_var_map[PostureSpecVariable.CARRY_TARGET]
            if carry_target is not None and carry_target.is_in_sim_inventory(sim=sim):
                self.adjust_route_for_sim_inventory()
            body_posture_target = sim.posture.target
            if body_posture_target is not None and sim.posture.mobile and self.path[0][BODY_INDEX][BODY_TARGET_INDEX] != body_posture_target:
                start_spec = sim.posture_state.get_posture_spec(self.var_map)
                self._path.insert(0, TransitionSpec(self, start_spec, self.var_map))

    def process_transitions(self, start_spec, get_new_sequence_fn):
        new_transitions = []
        transitions_len = len(self._path)
        prev_transition = None
        for (i, transition) in enumerate(self._path):
            k = i + 1
            next_transition = None
            if k < transitions_len:
                next_transition = self._path[k]
            new_sequence = get_new_sequence_fn(i, prev_transition, transition, next_transition)
            if self.validate_new_sequence(prev_transition, new_sequence, next_transition, get_new_sequence_fn, start_spec):
                if new_sequence:
                    new_transitions.extend(new_sequence)
            else:
                new_transitions.append(transition)
            if len(new_transitions) >= 1:
                prev_transition = new_transitions[-1]
        self._path = new_transitions

    def validate_new_sequence(self, prev_transition, new_sequence, next_transition, get_new_sequence_fn, start_spec):
        validate = services.current_zone().posture_graph_service._can_transition_between_nodes
        if new_sequence:
            if prev_transition is None:
                if not validate(start_spec, new_sequence[0].posture_spec):
                    self.handle_validate_error_msg(start_spec, new_sequence[0].posture_spec, get_new_sequence_fn, start_spec)
                    return False
            elif not validate(prev_transition.posture_spec, new_sequence[0].posture_spec):
                self.handle_validate_error_msg(prev_transition.posture_spec, new_sequence[0].posture_spec, get_new_sequence_fn, start_spec)
                return False
            if len(new_sequence) > 1:
                for (curr_trans, next_trans) in zip(new_sequence[0:], new_sequence[1:]):
                    if not validate(curr_trans.posture_spec, next_trans.posture_spec):
                        self.handle_validate_error_msg(curr_trans.posture_spec, next_trans.posture_spec, get_new_sequence_fn, start_spec)
                        return False
            if next_transition and not validate(new_sequence[-1].posture_spec, next_transition.posture_spec):
                self.handle_validate_error_msg(new_sequence[-1].posture_spec or prev_transition.posture_spec, next_transition.posture_spec, get_new_sequence_fn, start_spec)
                return False
        elif prev_transition is None and next_transition and not validate(start_spec, next_transition.posture_spec):
            self.handle_validate_error_msg(start_spec, next_transition.posture_spec, get_new_sequence_fn, start_spec)
            return False
        elif prev_transition and next_transition and not validate(prev_transition.posture_spec, next_transition.posture_spec):
            self.handle_validate_error_msg(prev_transition.posture_spec, next_transition.posture_spec, get_new_sequence_fn, start_spec)
            return False
        return True

    def handle_validate_error_msg(self, posture_spec_a, posture_spec_b, mod_function, start_spec):
        logger.error('--- FAIL: validate_new_sequence({}) ---', mod_function.__name__)
        logger.error('Start Spec: {}', start_spec)
        logger.error('Full Path:')
        for (index, posture_spec) in enumerate(self.path):
            logger.error('    {}: {}', index, posture_spec)
        logger.error('Failure:', posture_spec_a, posture_spec_b)
        logger.error('    posture_spec_a: {}', posture_spec_a)
        logger.error('    posture_spec_b: {}', posture_spec_b)

    @staticmethod
    def remove_non_surface_to_surface_transitions(i, prev_transition_spec, transition_spec, next_transition_spec):
        prev_transition = prev_transition_spec.posture_spec if prev_transition_spec is not None else None
        transition = transition_spec.posture_spec
        next_transition = next_transition_spec.posture_spec if next_transition_spec is not None else None
        if next_transition is not None and ((prev_transition is None or prev_transition[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile) and (transition[SURFACE_INDEX][SURFACE_TARGET_INDEX] is None and (next_transition[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile and next_transition[SURFACE_INDEX][SURFACE_TARGET_INDEX] is not None))) and (prev_transition is None or prev_transition[CARRY_INDEX] == next_transition[CARRY_INDEX] or next_transition is None):
            return ()
        return (transition_spec,)

    @staticmethod
    def remove_extra_mobile_transitions(i, prev_transition_spec, transition_spec, next_transition_spec):
        prev_transition = prev_transition_spec.posture_spec if prev_transition_spec is not None else None
        transition = transition_spec.posture_spec
        next_transition = next_transition_spec.posture_spec if next_transition_spec is not None else None
        if prev_transition is None or next_transition is None:
            return (transition_spec,)
        if prev_transition[CARRY_INDEX] == next_transition[CARRY_INDEX] and (prev_transition[SURFACE_INDEX] == next_transition[SURFACE_INDEX] and prev_transition[BODY_INDEX][BODY_TARGET_INDEX] == next_transition[BODY_INDEX][BODY_TARGET_INDEX]) and transition[BODY_INDEX][BODY_POSTURE_TYPE_INDEX] == next_transition[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]:
            return ()
        if prev_transition[SURFACE_INDEX][SURFACE_TARGET_INDEX] != transition[SURFACE_INDEX][SURFACE_TARGET_INDEX] or transition[SURFACE_INDEX][SURFACE_TARGET_INDEX] != next_transition[SURFACE_INDEX][SURFACE_TARGET_INDEX]:
            return (transition_spec,)
        if prev_transition[CARRY_INDEX][CARRY_TARGET_INDEX] != transition[CARRY_INDEX][CARRY_TARGET_INDEX] or transition[CARRY_INDEX][CARRY_TARGET_INDEX] != next_transition[CARRY_INDEX][CARRY_TARGET_INDEX]:
            return (transition_spec,)
        if prev_transition[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile or next_transition_spec.path is not None:
            return (transition_spec,)
        if prev_transition[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile and (transition[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile and next_transition[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile) and services.current_zone().posture_graph_service._can_transition_between_nodes(prev_transition, next_transition):
            return ()
        return (transition_spec,)

    def flag_slot_reservations(self):
        for (prev_transition_spec, cur_transition_spec) in zip(self._path, self._path[1:]):
            if prev_transition_spec.sequence_id != cur_transition_spec.sequence_id:
                pass
            elif not cur_transition_spec.posture_spec[SURFACE_INDEX][SURFACE_TARGET_INDEX]:
                pass
            elif prev_transition_spec.is_carry and not cur_transition_spec.is_carry:
                prev_transition_spec.handle_slot_reservations = True
            elif prev_transition_spec.targets_empty_slot or cur_transition_spec.targets_empty_slot:
                prev_transition_spec.handle_slot_reservations = True

    def generate_transition_interactions(self, sim, final_si, transition_success):
        if self._path is None:
            return True
        self._final_si = final_si
        transition_aops = OrderedDict()
        context = InteractionContext(sim, InteractionContext.SOURCE_POSTURE_GRAPH, final_si.priority, run_priority=final_si.run_priority, insert_strategy=QueueInsertStrategy.NEXT, must_run_next=True)
        preload_outfit_set = set()
        exit_change = sim.posture_state.body.saved_exit_clothing_change
        if exit_change is not None:
            preload_outfit_set.add(exit_change)
        posture_graph_service = services.posture_graph_service()
        for (i, cur_transition_spec) in enumerate(self._path[1:], start=1):
            cur_posture_spec = cur_transition_spec.posture_spec
            outfit_change = cur_transition_spec.posture_spec.body.posture_type.outfit_change
            if outfit_change:
                entry_change = outfit_change.get_on_entry_outfit(final_si, sim_info=sim.sim_info)
                if entry_change is not None:
                    preload_outfit_set.add(entry_change)
            portal_obj = cur_transition_spec.portal_obj
            if portal_obj is not None:
                portal_id = cur_transition_spec.portal_id
                portal_entry_outfit = portal_obj.get_on_entry_outfit(final_si, portal_id, sim_info=sim.sim_info)
                if portal_entry_outfit is not None:
                    preload_outfit_set.add(portal_entry_outfit)
                portal_exit_outfit = portal_obj.get_on_exit_outfit(final_si, portal_id, sim_info=sim.sim_info)
                if portal_exit_outfit is not None:
                    preload_outfit_set.add(portal_exit_outfit)
            for prev_transition_spec in reversed(self._path[:i]):
                if prev_transition_spec.sequence_id == cur_transition_spec.sequence_id:
                    prev_posture_spec = prev_transition_spec.posture_spec
                    break
            prev_posture_spec = None
            aop_list = []
            var_map = cur_transition_spec.var_map
            edge_info = posture_graph_service.get_edge(prev_posture_spec, cur_posture_spec, return_none_on_failure=True)
            aop = None
            if edge_info is not None:
                for operation in edge_info.operations:
                    op_aop = operation.associated_aop(sim, var_map)
                    if op_aop is not None:
                        aop = op_aop
            if aop is not None:
                aop_list.append((aop, var_map))
            transition_aops[i] = aop_list
        added_final_si = False
        for (i, aops) in reversed(list(transition_aops.items())):
            for (aop, var_map) in aops:
                final_valid_combinables = final_si.get_combinable_interactions_with_safe_carryables()
                existing_si_set = {final_si} if not final_valid_combinables else set(itertools.chain((final_si,), final_valid_combinables))
                for existing_si in existing_si_set:
                    if added_final_si or aop.is_equivalent_to_interaction(existing_si):
                        si = existing_si
                        added_final_si = True
                        break
                execute_result = aop.interaction_factory(context)
                if not execute_result:
                    return False
                si = execute_result.interaction
                self._path[i].add_transition_interaction(sim, si, var_map)
                si.add_preload_outfit_changes(preload_outfit_set)
            if not aops:
                self._path[i].add_transition_interaction(sim, None, self._path[i].var_map)
        if added_final_si or transition_success:
            self._path[-1].add_transition_interaction(sim, final_si, self._path[-1].var_map)
            final_si.add_preload_outfit_changes(preload_outfit_set)
        if not preload_outfit_set:
            current_position_on_active_lot = services.active_lot().is_position_on_lot(sim.position)
            if current_position_on_active_lot and not sim.is_outside:
                level = sim.routing_surface.secondary_id
                if sim.intended_position_on_active_lot and build_buy.is_location_outside(sim.zone_id, sim.intended_position, level):
                    sim.preload_outdoor_streetwear_change(final_si, preload_outfit_set)
        sim.set_preload_outfits(preload_outfit_set)
        return True
with reload.protected(globals()):
    EMPTY_PATH_SPEC = PathSpec(None, 0, {}, None, None, None)
    NO_CONNECTIVITY = Connectivity(EMPTY_PATH_SPEC, None, None, None)
class NodeData(namedtuple('NodeData', ('canonical_node', 'predecessors', 'successors'))):
    __slots__ = ()

    def __new__(cls, canonical_node, predecessors=(), successors=()):
        return super().__new__(cls, canonical_node, set(predecessors), set(successors))

class PostureGraph(collections.MutableMapping):

    def __init__(self):
        self._nodes = {}
        self._subsets = defaultdict(set)
        self._quadtrees = defaultdict(sims4.geometry.QuadTree)
        self._objects_pending_deletion = set()
        self.proxy_sim = None
        self.cached_sim_nodes = weakref.WeakKeyDictionary()
        self.cached_vehicle_nodes = set()
        self.cached_postures_to_object_ids = defaultdict(set)
        self._mobile_nodes_at_none = set()
        self._mobile_nodes_at_none_no_carry = set()
        self._mobile_nodes_at_none_carry = set()

    def __len__(self):
        return len(self._nodes)

    def __iter__(self):
        return iter(self._nodes)

    def __bool__(self):
        return bool(self._nodes)

    def __getitem__(self, key):
        key = self._get_transform_key(key)
        return self._nodes[key]

    def __setitem__(self, key, value):
        self._nodes[key] = value

    def __delitem__(self, key):
        del self._nodes[key]

    def __contains__(self, key):
        key = self._get_transform_key(key)
        return key in self._nodes

    def get(self, key, default=None):
        key = self._get_transform_key(key)
        if key in self._nodes:
            return self._nodes[key]
        return default

    def _get_transform_key(self, key):
        body = key[BODY_INDEX]
        if body is not None:
            body_target = body[BODY_TARGET_INDEX]
            if body_target.is_sim:
                posture_type = body[BODY_POSTURE_TYPE_INDEX]
                key = key.clone(body=PostureAspectBody((posture_type, self.proxy_sim)))
        return key

    @property
    def nodes(self):
        return self.keys()

    @property
    def vehicle_nodes(self):
        return self.cached_vehicle_nodes

    def cache_global_mobile_nodes(self):
        self._mobile_nodes_at_none.update(_DEFAULT_MOBILE_NODES)
        self._mobile_nodes_at_none_no_carry.update(_MOBILE_NODES_AT_NONE)
        self._mobile_nodes_at_none_carry.update(_MOBILE_NODES_AT_NONE_CARRY)

    def setup_provided_mobile_nodes(self):
        object_manager = services.object_manager()
        for obj in object_manager.get_posture_providing_objects():
            self.add_mobile_posture_provider_nodes(obj)

    @property
    def all_mobile_nodes_at_none(self):
        return self._mobile_nodes_at_none

    @property
    def all_mobile_nodes_at_none_no_carry(self):
        return self._mobile_nodes_at_none_no_carry

    @property
    def all_mobile_nodes_at_none_carry(self):
        return self._mobile_nodes_at_none_carry

    @property
    def mobile_posture_providing_affordances(self):
        object_manager = services.object_manager()
        affordances = set()
        for obj in object_manager.get_posture_providing_objects():
            affordances.update(obj.provided_mobile_posture_affordances)
        return affordances

    def get_canonical_node(self, node):
        node_data = self.get(node)
        if node_data is None:
            return node
        return node_data.canonical_node

    def remove_node(self, node):
        target = node.body_target or node.surface_target
        if target is not None and target != PostureSpecVariable.ANYTHING:
            self.remove_from_quadtree(target, node)
            body_type = node[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]
            if body_type.is_vehicle:
                self.cached_vehicle_nodes.remove(node)
        for key in self._get_subset_keys(node):
            if key in self._subsets:
                self._subsets[key].remove(node)
                if not self._subsets[key]:
                    del self._subsets[key]
        node_data = self[node]
        for successor in node_data.successors:
            self[successor].predecessors.remove(node)
        for predecessor in node_data.predecessors:
            self[predecessor].successors.remove(node)
        del self[node]

    def remove_from_quadtree(self, obj, node):
        level = obj.level
        if level is None:
            return
        quadtree = self._quadtrees[level]
        quadtree.remove(node)

    def add_to_quadtree(self, obj, node):
        level = obj.level
        if level is None:
            return
        bounding_box = obj.get_bounding_box()
        quadtree = self._quadtrees[level]
        quadtree.insert(node, bounding_box)

    def add_successor(self, node, successor):
        node = self.get_canonical_node(node)
        successor = self.get_canonical_node(successor)
        self._add_node(node)
        self[node].successors.add(successor)
        self._add_node(successor)
        self[successor].predecessors.add(node)

    def _add_node(self, node):
        if node in self:
            return
        self[node] = NodeData(node)
        target = None
        body = node[BODY_INDEX]
        if body is not None:
            target = body[BODY_TARGET_INDEX]
        if target is None:
            surface = node[SURFACE_INDEX]
            if surface is not None:
                target = surface[SURFACE_TARGET_INDEX]
        if target is not None and target != PostureSpecVariable.ANYTHING and not target.is_sim:
            self.add_to_quadtree(target, node)
            body_type = node[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]
            if body_type.is_vehicle:
                self.cached_vehicle_nodes.add(node)
        for key in self._get_subset_keys(node):
            self._subsets[key].add(node)

    def get_successors(self, node, default=DEFAULT):
        node_data = self.get(node)
        if node_data is not None:
            return node_data.successors
        if default is DEFAULT:
            raise KeyError('Node {} not in posture graph.'.format(node))
        return default

    def get_predecessors(self, node, default=DEFAULT):
        node_data = self.get(node)
        if node_data is not None:
            return node_data.predecessors
        if default is DEFAULT:
            raise KeyError('Node {} not in posture graph.'.format(node))
        return default

    @staticmethod
    def _get_subset_keys(node_or_spec):
        keys = set()
        posture_type = node_or_spec.body and node_or_spec.body.posture_type
        if posture_type is not None:
            keys.add(('posture_type', posture_type))
        carry_target = node_or_spec.carry_target
        keys.add(('carry_target', carry_target))
        body_target = node_or_spec.body_target
        body_target = getattr(body_target, 'part_owner', None) or body_target
        if node_or_spec.surface is not None:
            original_surface_target = node_or_spec.surface_target
            surface_target = getattr(original_surface_target, 'part_owner', None) or original_surface_target
            keys.add(('slot_target', node_or_spec.slot_target))
            slot_type = node_or_spec.slot_type
            if slot_type is not None and slot_type != PostureSpecVariable.SLOT:
                keys.add(('slot_type', slot_type))
            if surface_target == PostureSpecVariable.CONTAINER_TARGET:
                surface_target = node_or_spec.body_target
            if surface_target is None:
                if body_target is not None and (isinstance(body_target, PostureSpecVariable) or body_target.is_surface()):
                    keys.add(('surface_target', body_target))
                    keys.add(('has_a_surface', True))
                else:
                    keys.add(('has_a_surface', False))
            elif surface_target not in (PostureSpecVariable.ANYTHING, PostureSpecVariable.SURFACE_TARGET):
                keys.add(('surface_target', surface_target))
                keys.add(('has_a_surface', True))
            elif surface_target == PostureSpecVariable.SURFACE_TARGET:
                keys.add(('has_a_surface', True))
            if not isinstance(original_surface_target, PostureSpecVariable):
                for slot_type in original_surface_target.get_provided_slot_types():
                    keys.add(('slot_type', slot_type))
        else:
            surface_target = None
        if node_or_spec.body is not None:
            if body_target != PostureSpecVariable.ANYTHING:
                keys.add(('body_target', body_target))
                if body_target != PostureSpecVariable.BODY_TARGET_FILTERED:
                    keys.add(('body_target', PostureSpecVariable.BODY_TARGET_FILTERED))
            elif surface_target is None and posture_type.mobile:
                keys.add(('body_target', None))
        if ('body_target', None) in keys and ('slot_target', None) in keys:
            keys.add(('body_target and slot_target', None))
        return keys

    @caches.cached(key=lambda _, constraint: constraint)
    def nodes_matching_constraint_geometry(self, constraint):
        if any(sub_constraint.routing_surface is None or sub_constraint.geometry is None for sub_constraint in constraint):
            return
        nodes = set()
        for sub_constraint in constraint:
            floor = sub_constraint.routing_surface.secondary_id
            quadtree = self._quadtrees[floor]
            for polygon in sub_constraint.geometry.polygon:
                (lower_bound, upper_bound) = polygon.bounds()
                bounding_box = sims4.geometry.QtRect(sims4.math.Vector2(lower_bound.x, lower_bound.z), sims4.math.Vector2(upper_bound.x, upper_bound.z))
                nodes.update(quadtree.query(bounding_box))
        nodes |= self._subsets[('body_target and slot_target', None)]
        return nodes

    def nodes_for_object_gen(self, obj):
        if obj.is_part:
            owner = obj.part_owner
            nodes = self._subsets.get(('body_target', owner), set()) | self._subsets.get(('surface_target', owner), set())
            for node in nodes:
                if node.body_target is obj or node.surface_target is obj:
                    yield node
        else:
            if obj.is_sim:
                obj = self.proxy_sim
            nodes = self._subsets.get(('body_target', obj), set()) | self._subsets.get(('surface_target', obj), set())
            yield from nodes

    def _get_nodes_internal_gen(self, nodes):
        for node in nodes:
            if not node.body_target is not None or node.body_target.is_sim:
                yield from self.sim_carry_nodes_gen(node)
            else:
                yield node

    def get_matching_nodes_gen(self, specs, slot_types, constraint=None):
        nodes = set()
        for spec in specs:
            if slot_types:
                spec_nodes = set()
                for slot_type in slot_types:
                    surface = PostureAspectSurface((spec.surface.target, slot_type, spec.surface.slot_target))
                    slot_type_spec = spec.clone(surface=surface)
                    keys = self._get_subset_keys(slot_type_spec)
                    if not keys:
                        raise AssertionError('No keys returned for a specific slot type!')
                    subsets = {key: self._subsets[key] for key in keys}
                    intersection = functools.reduce(operator.and_, sorted(subsets.values(), key=len))
                    spec_nodes.update(intersection)
            else:
                keys = self._get_subset_keys(spec)
                if not keys:
                    yield from self._get_nodes_internal_gen(self.nodes)
                subsets = {key: self._subsets[key] for key in keys}
                spec_nodes = set(functools.reduce(operator.and_, sorted(subsets.values(), key=len)))
            target = spec.body_target or spec.surface_target
            if constraint:
                quadtree_subset = self.nodes_matching_constraint_geometry(constraint)
                if quadtree_subset is not None:
                    spec_nodes &= quadtree_subset
            nodes.update(spec_nodes)
        yield from self._get_nodes_internal_gen(nodes)

    def sim_carry_nodes_gen(self, carried_node):
        sim_info_manager = services.sim_info_manager()
        for sim in sim_info_manager.instanced_sims_gen():
            sim_node = self.cached_sim_nodes.get(sim)
            sim_node = carried_node.clone(body=PostureAspectBody((carried_node.body_posture, sim)))
            self.cached_sim_nodes[sim] = sim_node
            yield sim_node

    def vehicle_nodes_gen(self):
        for node in self.cached_vehicle_nodes:
            yield node

    def add_mobile_posture_provider_nodes(self, new_obj):
        for mobile_posture in new_obj.provided_mobile_posture_types:
            add_nodes = False if self.cached_postures_to_object_ids[mobile_posture] else True
            if new_obj.id not in self.cached_postures_to_object_ids[mobile_posture]:
                self.cached_postures_to_object_ids[mobile_posture].add(new_obj.id)
            if add_nodes and not mobile_posture.skip_route:
                mobile_node_at_none = get_origin_spec(mobile_posture)
                self._mobile_nodes_at_none.add(mobile_node_at_none)
                self._mobile_nodes_at_none_no_carry.add(mobile_node_at_none)
                if mobile_posture._supports_carry:
                    mobile_node_at_none_carry = get_origin_spec_carry(mobile_posture)
                    self._mobile_nodes_at_none.add(mobile_node_at_none_carry)
                    self._mobile_nodes_at_none_carry.add(mobile_node_at_none_carry)

    def remove_mobile_posture_provider_nodes(self, old_obj):
        for mobile_posture in old_obj.provided_mobile_posture_types:
            if old_obj.id in self.cached_postures_to_object_ids[mobile_posture]:
                self.cached_postures_to_object_ids[mobile_posture].remove(old_obj.id)
            remove_nodes = False if self.cached_postures_to_object_ids[mobile_posture] else True
            if remove_nodes and not mobile_posture.skip_route:
                mobile_node_at_none = get_origin_spec(mobile_posture)
                self._mobile_nodes_at_none.remove(mobile_node_at_none)
                self._mobile_nodes_at_none_no_carry.remove(mobile_node_at_none)
                if mobile_posture._supports_carry:
                    mobile_node_at_none_carry = get_origin_spec_carry(mobile_posture)
                    self._mobile_nodes_at_none.remove(mobile_node_at_none_carry)
                    self._mobile_nodes_at_none_carry.remove(mobile_node_at_none_carry)

    def clear(self):
        super().clear()
        self._subsets.clear()
        self._quadtrees.clear()
        self._objects_pending_deletion.clear()
        self.cached_vehicle_nodes.clear()
        self.cached_postures_to_object_ids.clear()
        self._mobile_nodes_at_none.clear()
        self._mobile_nodes_at_none_carry.clear()
        self._mobile_nodes_at_none_no_carry.clear()
        self.proxy_sim = None

class EdgeInfo(namedtuple('_EdgeInfo', ['operations', 'validate', 'species_to_cost_dict'])):
    __slots__ = ()

    def cost(self, species):
        if species in self.species_to_cost_dict:
            return self.species_to_cost_dict[species]
        return self.species_to_cost_dict[PostureOperation.DEFAULT_COST_KEY]

def _get_species_to_aop_tunable_mapping(*, description):
    return TunableMapping(description=description, key_type=TunableEnumEntry(description='\n            The species that this affordance is intended for.\n            ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), value_type=TunableReference(description='\n            The default interaction to push for Sims of this species.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True))

class PostureGraphService(Service):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        for affordance in PostureGraphService.POSTURE_PROVIDING_AFFORDANCES:
            posture_type = affordance.provided_posture_type
            if posture_type.mobile and posture_type.unconstrained and affordance not in PostureGraphService.SIM_DEFAULT_AFFORDANCES:
                logger.error(' Posture Providing Affordance {} provides a\n                mobile, unconstrained, posture but is not tied to an object.\n                You likely want to add this to the Provided Mobile Posture\n                Affordances on the object this posture requires. For example,\n                Oceans and Pools provide swim and float postures.\n                ', affordance, owner='rmccord')

    SIM_DEFAULT_AFFORDANCES = _get_species_to_aop_tunable_mapping(description="\n        The interactions for Sims' default postures. These interactions are used\n        to kickstart Sims; are pushed on them after resets, and are used as the\n        default cancel replacement interaction.\n        ")
    SWIM_DEFAULT_AFFORDANCES = _get_species_to_aop_tunable_mapping(description="\n        The interactions for Sims' default swimming postures. These interactions\n        are used as a Sim's default affordance while in a pool.\n        ")
    CARRIED_DEFAULT_AFFORDANCES = _get_species_to_aop_tunable_mapping(description='\n        The interactions for Sims\' default "Be Carried" postures. These\n        interactions are used whenever Sims are transitioning into such\n        postures.\n        ')
    POSTURE_PROVIDING_AFFORDANCES = TunableList(description='\n        Additional posture providing interactions that are not tuned on any\n        object. This allows us to add additional postures for sims to use.\n        Example: Kneel on floor.\n        ', tunable=TunableReference(description='\n            Interaction that provides a posture.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True), verify_tunable_callback=_verify_tunable_callback)
    INCREMENTAL_REBUILD_THRESHOLD = Tunable(description='\n        The posture graph will do a full rebuild when exiting build/buy if\n        there have been more than this number of modifications to the posture\n        graph. Otherwise, an incremental rebuild will be done, which is much\n        faster for small numbers of operations, but slower for large numbers.\n        Talk to a gameplay engineer before changing this value.\n        ', tunable_type=int, default=10)

    def __init__(self):
        self._graph = PostureGraph()
        self._edge_info = {}
        self._goal_costs = {}
        self._zone_loaded = False
        self._disable_graph_update_count = 0
        self._incremental_update_count = None
        self._mobile_posture_objects_quadtree = sims4.geometry.QuadTree()

    @property
    def has_built_for_zone_spin_up(self):
        return self._zone_loaded

    def _clear(self):
        self._graph.clear()
        self._edge_info.clear()

    def rebuild(self):
        if indexed_manager.capture_load_times:
            time_stamp = time.time()
        if self._disable_graph_update_count == 0:
            self._clear()
            self.build()
        if indexed_manager.capture_load_times:
            time_spent_rebuilding = time.time() - time_stamp
            indexed_manager.object_load_times['posture_graph'] = time_spent_rebuilding

    def disable_graph_building(self):
        self._disable_graph_update_count += 1

    def enable_graph_building(self):
        self._disable_graph_update_count -= 1

    @staticmethod
    def get_default_affordance(species):
        if species in PostureGraphService.SIM_DEFAULT_AFFORDANCES:
            return PostureGraphService.SIM_DEFAULT_AFFORDANCES[species]
        else:
            logger.warn("Requesting default affordance for {} and it doesn't exist in PostureGraphService.SIM_DEFAULT_AFFORDANCES, using human instead.", species)
            return PostureGraphService.SIM_DEFAULT_AFFORDANCES[Species.HUMAN]

    @staticmethod
    def get_default_aop(species):
        if SIM_DEFAULT_AOPS is None:
            _cache_global_sim_default_values()
        if species in SIM_DEFAULT_AOPS:
            return SIM_DEFAULT_AOPS[species]
        else:
            logger.warn("Requesting default aop for {} and it doesn't exist in PostureGraphService.SIM_DEFAULT_AOPS, using human instead.")
            return SIM_DEFAULT_AOPS[Species.HUMAN]

    @staticmethod
    def get_default_swim_affordance(species):
        if species in PostureGraphService.SWIM_DEFAULT_AFFORDANCES:
            return PostureGraphService.SWIM_DEFAULT_AFFORDANCES[species]
        else:
            logger.warn("Requesting default swim affordance for {} and it doesn't exist in PostureGraphService.SWIM_DEFAULT_AFFORDANCES, using human instead.", species)
            return PostureGraphService.SWIM_DEFAULT_AFFORDANCES[Species.HUMAN]

    @staticmethod
    def get_swim_aop(species):
        if SIM_SWIM_AOPS is None:
            _cache_global_sim_default_values()
        if species in SIM_SWIM_AOPS:
            return SIM_SWIM_AOPS[species]
        else:
            logger.warn("Requesting default swim aop for {} and it doesn't exist in PostureGraphService.SIM_SWIM_AOPS, using human instead.")
            return SIM_SWIM_AOPS[Species.HUMAN]

    def on_enter_buildbuy(self):
        self._incremental_update_count = 0

    def on_exit_buildbuy(self):
        if self._incremental_update_count is None:
            logger.warn('Posture graph incremental update count is None when exiting build/buy. This can only happen if there is a mismatch between calls to on_enter_buildbuy() and on_exit_buildbuy(). The posture graph will be rebuilt just to be cautious.', owner='bhill')
            self.rebuild()
        elif self._incremental_update_count > self.INCREMENTAL_REBUILD_THRESHOLD:
            logger.info('Exiting build/buy and executing full posture graph rebuild.')
            self.rebuild()
        else:
            logger.info('Exiting build/buy and the incremental posture graph rebuild was good enough. (Only {} changes made)', self._incremental_update_count)
        self._incremental_update_count = None

    def start(self):
        self._clear()
        if SIM_DEFAULT_AOPS is None:
            _cache_global_sim_default_values()
        self.build()

    @contextmanager
    def __reload_context__(oldobj, newobj):
        try:
            yield None
        finally:
            if isinstance(oldobj, PostureGraphService):
                _cache_global_sim_default_values()
                newobj._graph.cache_global_mobile_nodes()

    def on_teardown(self):
        self._zone_loaded = False
        object_manager = services.object_manager()
        object_manager.unregister_callback(CallbackTypes.ON_OBJECT_ADD, self._on_object_added)
        object_manager.unregister_callback(CallbackTypes.ON_OBJECT_REMOVE, self._on_object_deleted)

    def build_during_zone_spin_up(self):
        skip_cache = caches.skip_cache
        caches.skip_cache = False
        self._zone_loaded = True
        self.rebuild()
        object_manager = services.object_manager()
        object_manager.register_callback(CallbackTypes.ON_OBJECT_ADD, self._on_object_added)
        object_manager.register_callback(CallbackTypes.ON_OBJECT_REMOVE, self._on_object_deleted)
        caches.skip_cache = skip_cache

    def add_node(self, node, operations):
        nodes = []
        next_node = node
        for operation in operations:
            nodes.append(next_node)
            next_node = operation.apply(next_node)
            if next_node is None:
                return
        if not PostureGraphService._validate_node_for_graph(next_node):
            return
        if next_node in self._graph.get_successors(node, ()):
            return
        species_to_cost_dict = None
        validate = CallableTestList()
        for (source_node, operation) in zip(nodes, operations):
            if species_to_cost_dict is None:
                species_to_cost_dict = operation.cost(source_node)
            else:
                temp_cost_dict = operation.cost(source_node)
                current_default_cost = species_to_cost_dict[PostureOperation.DEFAULT_COST_KEY]
                new_default_cost = temp_cost_dict[PostureOperation.DEFAULT_COST_KEY]
                for species in species_to_cost_dict:
                    if species in temp_cost_dict:
                        species_to_cost_dict[species] += temp_cost_dict.pop(species)
                    else:
                        species_to_cost_dict[species] += new_default_cost
                for species in temp_cost_dict:
                    species_to_cost_dict[species] = current_default_cost + temp_cost_dict.pop(species)
            validate.append(operation.get_validator(source_node))
        edge_info = EdgeInfo(operations, validate, species_to_cost_dict)
        self._graph.add_successor(node, next_node)
        self._edge_info[(node, next_node)] = edge_info
        return next_node

    def update_generic_sim_carry_node(self, sim, from_init=False):
        if self._graph.proxy_sim is None:
            if from_init and sim.is_selectable:
                self._graph.proxy_sim = SimPostureNode(sim)
                return True
            else:
                return False
        return True

    def _obj_triggers_posture_graph_update(self, obj):
        if obj.is_sim:
            return
        if self._disable_graph_update_count:
            return False
        if not obj.is_valid_posture_graph_object:
            return False
        elif obj.parts == []:
            return False
        else:
            return True
        return True

    def on_mobile_posture_object_added_during_zone_spinup(self, new_obj):
        self._on_object_added(new_obj)

    @with_caches
    def _on_object_added(self, new_obj):
        if new_obj.is_part or not self._obj_triggers_posture_graph_update(new_obj):
            return
        if self._incremental_update_count is not None:
            self._incremental_update_count += 1
            if self._incremental_update_count > self.INCREMENTAL_REBUILD_THRESHOLD:
                return
        objects = set()

        def add_object_to_build(obj_to_add):
            if obj_to_add.parts:
                objects.update(obj_to_add.parts)
            else:
                objects.add(obj_to_add)

        add_object_to_build(new_obj)
        for child in new_obj.children:
            if child.is_valid_posture_graph_object:
                add_object_to_build(child)
        open_set = set()
        closed_set = set(self._graph.nodes)
        all_ancestors = set().union(*(obj.ancestry_gen() for obj in objects))
        for ancestor in all_ancestors:
            if not ancestor.parts:
                open_set.update(self._graph.nodes_for_object_gen(ancestor))
        closed_set -= open_set
        if new_obj.is_sim:
            if self._graph.proxy_sim is None:
                for closed_node in tuple(closed_set):
                    body_posture = closed_node[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]
                    body_target = closed_node[BODY_INDEX][BODY_TARGET_INDEX]
                    can_transition_to_carry = not body_posture.mobile or body_posture.mobile and body_target is None
                    if can_transition_to_carry and body_posture.is_available_transition(PostureTuning.SIM_CARRIED_POSTURE):
                        closed_set.discard(closed_node)
        else:
            for closed_node in tuple(closed_set):
                if closed_node[BODY_INDEX][BODY_POSTURE_TYPE_INDEX] is PostureTuning.SIM_CARRIED_POSTURE:
                    closed_set.discard(closed_node)
        provided_posture_aops = []
        mobile_affordances_and_postures = [(affordance, affordance.provided_posture_type) for affordance in new_obj.provided_mobile_posture_affordances]
        for (affordance, mobile_posture) in mobile_affordances_and_postures:
            if len(self._graph.cached_postures_to_object_ids[mobile_posture]) == 1:
                provided_posture_aops.append(AffordanceObjectPair(affordance, None, affordance, None))
        if provided_posture_aops:
            body_operations_dict = PostureGraphService.get_body_operation_dict(provided_posture_aops)
            for (source_posture_type, destination_posture_type) in Posture._posture_transitions:
                body_operation = body_operations_dict.get(destination_posture_type)
                if body_operation is None:
                    pass
                elif source_posture_type is not SIM_DEFAULT_POSTURE_TYPE and source_posture_type not in body_operations_dict:
                    pass
                else:
                    new_node = self.add_node(get_origin_spec(source_posture_type), (body_operation,))
                    if new_node is not None:
                        open_set.add(new_node)
                    if source_posture_type._supports_carry:
                        new_node = self.add_node(get_origin_spec_carry(source_posture_type), (body_operation,))
                        if new_node is not None:
                            open_set.add(new_node)
        for (node, obj) in itertools.product(self._graph.all_mobile_nodes_at_none, objects):
            ops = []
            self._expand_and_append_node_object(node, obj, ops)
            for operations in ops:
                new_node = self.add_node(node, operations)
                if new_node is not None and new_node not in closed_set:
                    open_set.add(new_node)
        with _object_addition(new_obj):
            self._build(open_set, closed_set)

    def get_proxied_sim(self):
        if self._graph.proxy_sim is None:
            return
        return self._graph.proxy_sim.sim_proxied

    def is_object_pending_deletion(self, obj):
        return obj in self._graph._objects_pending_deletion

    @with_caches
    def _on_object_deleted(self, obj):
        if not self._obj_triggers_posture_graph_update(obj):
            return
        if not obj.remove_children_from_posture_graph_on_delete:
            return
        if self._incremental_update_count is not None:
            self._incremental_update_count += 1
            if self._incremental_update_count > self.INCREMENTAL_REBUILD_THRESHOLD:
                return
        if not obj.get_users(sims_only=True):
            self.finalize_object_deletion(obj)
            return
        self._graph._objects_pending_deletion.add(obj)

    def finalize_object_deletion(self, obj):
        for node in self._graph.nodes_for_object_gen(obj):
            for successor in self._graph.get_successors(node, ()):
                self._edge_info.pop((node, successor), None)
            for predecessor in self._graph.get_predecessors(node, ()):
                self._edge_info.pop((predecessor, node), None)
            self._graph.remove_node(node)
        for mobile_posture in obj.provided_mobile_posture_types:
            if len(self._graph.cached_postures_to_object_ids[mobile_posture]) == 1:
                mobile_node_at_none = get_origin_spec(mobile_posture)
                self._graph.remove_node(mobile_node_at_none)
                if mobile_posture._supports_carry:
                    mobile_node_at_none_carry = get_origin_spec_carry(mobile_posture)
                    self._graph.remove_node(mobile_node_at_none_carry)
        self._graph._objects_pending_deletion.discard(obj)

    @contextmanager
    @with_caches
    def object_moving(self, obj):
        if self._zone_loaded and obj.is_sim:
            yield None
            return
        if obj.routing_component is not None and obj.routing_component.is_moving:
            sims = obj.get_users(sims_only=True)
            for sim in sims:
                posture_state = sim.posture_state
                if not posture_state is not None or posture_state.body.target is obj:
                    posture_state.body.invalidate_slot_constraints()
            yield None
            return
        if obj.is_valid_posture_graph_object:
            self._on_object_deleted(obj)
        try:
            yield None
        finally:
            if obj.is_valid_posture_graph_object:
                self._on_object_added(obj)

    def _expand_node(self, node):
        ops = []
        for obj in node.get_relevant_objects():
            if not obj.is_valid_posture_graph_object:
                pass
            elif obj.is_sim:
                self._expand_and_append_node_sim(node, obj, ops)
            else:
                self._expand_and_append_node_object(node, obj, ops)
        ops.append((SIM_DEFAULT_OPERATION,))
        if node.body_posture.supports_swim:
            ops.append((SIM_SWIM_OPERATION,))
        if node[SURFACE_INDEX] is not None:
            ops.append((PostureOperation.FORGET_SURFACE_OP, SIM_DEFAULT_OPERATION))
            if node[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile:
                ops.append((PostureOperation.FORGET_SURFACE_OP,))
        if node[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]._supports_carry:
            ops.append((PostureOperation.STANDARD_PICK_UP_OP,))
        return ops

    @staticmethod
    def get_body_operation_dict(posture_aops):
        body_operations_dict = {}
        for aop in posture_aops:
            body_operation = aop.get_provided_posture_change()
            if body_operation is None:
                pass
            else:
                body_op_posture_type = body_operation.posture_type
                if body_op_posture_type in body_operations_dict:
                    for (species, aop) in body_operation.all_associated_aops_gen():
                        body_operations_dict[body_op_posture_type].add_associated_aop(species, aop)
                else:
                    body_operations_dict[body_operation.posture_type] = body_operation
        return body_operations_dict

    @caches.cached(maxsize=None)
    def _expand_object_surface(self, obj, surface):
        ops = []
        if surface is not None:
            put_down = PostureOperation.PutDownObjectOnSurface(PostureSpecVariable.POSTURE_TYPE_CARRY_NOTHING, surface, PostureSpecVariable.SLOT, PostureSpecVariable.CARRY_TARGET)
            ops.append((put_down,))
            surface_ops = self._expand_surface(surface)
            ops.extend(surface_ops)
        posture_aops = obj.get_posture_aops_gen()
        if obj.is_part:
            posture_aops = filter(obj.supports_affordance, posture_aops)
        body_operations_dict = self.get_body_operation_dict(posture_aops)
        for body_operation in body_operations_dict.values():
            if obj.parts:
                if body_operation.posture_type.unconstrained:
                    ops.append((body_operation,))
                    if surface is not None:
                        ops.extend((body_operation,) + ops for ops in surface_ops)
            ops.append((body_operation,))
            if surface is not None:
                ops.extend((body_operation,) + ops for ops in surface_ops)
        if obj.inventory_component is not None:
            at_surface = PostureOperation.TargetAlreadyInSlot(None, obj, None)
            ops.append((at_surface,))
        return ops

    def _expand_and_append_node_object(self, node, obj, out_ops):
        surface = None
        if obj.is_surface():
            surface = obj
        else:
            parent = obj.parent
            if obj.add_to_posture_graph_if_parented or parent.is_surface():
                surface = parent
        out_ops.extend(self._expand_object_surface(obj, surface))
        if surface is not obj:
            return
        if node.body_target not in (None, obj):
            return
        species_to_affordances = enumdict(Species)
        species_to_disallowed_ages = defaultdict(set)
        for (species, affordance) in self.SIM_DEFAULT_AFFORDANCES.items():
            if obj.is_part and not obj.supports_posture_type(affordance.provided_posture_type):
                pass
            else:
                species_to_affordances[species] = AffordanceObjectPair(affordance, obj, affordance, None)
                species_to_disallowed_ages[species] = event_testing.test_utils.get_disallowed_ages(affordance)
        if not species_to_affordances:
            return
        body_operation = PostureOperation.BodyTransition(SIM_DEFAULT_POSTURE_TYPE, species_to_affordances, target=obj, disallowed_ages=species_to_disallowed_ages)
        out_ops.append((body_operation,))

    def _expand_and_append_node_sim(self, node, obj, out_ops):
        logger.assert_log(obj.is_sim, '_expand_and_append_node_sim can only be called with a Sim object')
        species_to_affordances = enumdict(Species)
        species_to_disallowed_ages = defaultdict(set)
        for (species, affordance) in self.CARRIED_DEFAULT_AFFORDANCES.items():
            if not obj.supports_posture_type(affordance.provided_posture_type):
                pass
            else:
                species_to_affordances[species] = AffordanceObjectPair(affordance, obj, affordance, None)
                species_to_disallowed_ages[species] = event_testing.test_utils.get_disallowed_ages(affordance)
        if not species_to_affordances:
            return
        if obj.age not in species_to_disallowed_ages[obj.species]:
            return
        if not self.update_generic_sim_carry_node(obj, from_init=True):
            return
        body_operation = PostureOperation.BodyTransition(PostureTuning.SIM_CARRIED_POSTURE, species_to_affordances, target=self._graph.proxy_sim, disallowed_ages=species_to_disallowed_ages)
        out_ops.append((body_operation,))

    def _expand_surface(self, surface):
        ops = []
        existing_carryable_slotted_target = PostureOperation.TargetAlreadyInSlot(PostureSpecVariable.CARRY_TARGET, surface, PostureSpecVariable.SLOT)
        ops.append((existing_carryable_slotted_target,))
        existing_noncarryable_slotted_target = PostureOperation.TargetAlreadyInSlot(PostureSpecVariable.SLOT_TARGET, surface, PostureSpecVariable.SLOT)
        ops.append((existing_noncarryable_slotted_target,))
        empty_surface = PostureOperation.TargetAlreadyInSlot(None, surface, PostureSpecVariable.SLOT)
        ops.append((empty_surface,))
        at_surface = PostureOperation.TargetAlreadyInSlot(None, surface, None)
        ops.append((at_surface,))
        forget_surface = PostureOperation.FORGET_SURFACE_OP
        ops.append((forget_surface,))
        return ops

    @staticmethod
    @caches.cached(maxsize=4096)
    def _validate_node_for_graph(node):
        surface = node[SURFACE_INDEX]
        target = node[BODY_INDEX][BODY_TARGET_INDEX]
        if (surface is None or surface[SURFACE_TARGET_INDEX] is None) and target is not None and not node[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile:
            target_parent = target.parent
            if target_parent is not None and not target.is_set_as_head:
                return False
            elif target_parent is None and target.is_surface():
                return False
        return True

    def _build(self, open_set, closed_set):
        while open_set:
            node = open_set.pop()
            closed_set.add(node)
            for operations in self._expand_node(node):
                new_node = self.add_node(node, operations)
                if new_node is not None and new_node not in closed_set:
                    open_set.add(new_node)
        caches.clear_all_caches()

    @with_caches
    def build(self):
        open_set = set(STAND_AT_NONE_NODES)
        closed_set = set()
        self._graph.cache_global_mobile_nodes()
        self._graph.setup_provided_mobile_nodes()
        self._edge_info[(STAND_AT_NONE, STAND_AT_NONE)] = EdgeInfo((SIM_DEFAULT_OPERATION,), lambda *_, **__: True, 0)
        provided_posture_aops = [AffordanceObjectPair(affordance, None, affordance, None) for affordance in self.POSTURE_PROVIDING_AFFORDANCES]
        mobile_affordances = self._graph.mobile_posture_providing_affordances
        provided_posture_aops.extend([AffordanceObjectPair(affordance, None, affordance, None) for affordance in mobile_affordances])
        body_operations_dict = PostureGraphService.get_body_operation_dict(provided_posture_aops)
        for (source_posture_type, destination_posture_type) in Posture._posture_transitions:
            body_operation = body_operations_dict.get(destination_posture_type)
            if body_operation is None:
                pass
            elif source_posture_type is not SIM_DEFAULT_POSTURE_TYPE and source_posture_type not in body_operations_dict:
                pass
            else:
                new_node = self.add_node(get_origin_spec(source_posture_type), (body_operation,))
                if new_node is not None:
                    open_set.add(new_node)
                if source_posture_type._supports_carry:
                    new_node = self.add_node(get_origin_spec_carry(source_posture_type), (body_operation,))
                    if new_node is not None:
                        open_set.add(new_node)
        self._build(open_set, closed_set)

    def nodes_matching_constraint_geometry(self, constraint):
        return self._graph.nodes_matching_constraint_geometry(constraint)

    @property
    def all_mobile_nodes_at_none_no_carry(self):
        return self._graph.all_mobile_nodes_at_none_no_carry

    @property
    def all_mobile_nodes_at_none_carry(self):
        return self._graph.all_mobile_nodes_at_none_carry

    @property
    def all_mobile_nodes_at_none(self):
        return self._graph.all_mobile_nodes_at_none

    @property
    def mobile_posture_providing_affordances(self):
        return self._graph.mobile_posture_providing_affordances

    def add_mobile_posture_provider(self, obj):
        self._graph.add_mobile_posture_provider_nodes(obj)

    def remove_mobile_posture_provider(self, obj):
        self._graph.remove_mobile_posture_provider_nodes(obj)

    def distance_fn(self, sim, var_map, interaction, curr_node, next_node):
        if isinstance(curr_node, _MobileNode):
            curr_node = curr_node.graph_node
        if isinstance(next_node, _MobileNode):
            next_node = next_node.graph_node
        if curr_node == next_node:
            return 0
        cost = 0
        next_body = next_node[BODY_INDEX]
        next_body_target = next_body[BODY_TARGET_INDEX]
        if gsi_handlers.posture_graph_handlers.archiver.enabled:
            cost_str_list = []
        if next_body_target is not None:
            if next_body_target.is_sim:
                guaranteed_si_count = sum(1 for _ in next_body_target.si_state.all_guaranteed_si_gen())
                if guaranteed_si_count:
                    cost += guaranteed_si_count*PostureScoring.CARRYING_SIM_BUSY_PENALTY
                    if gsi_handlers.posture_graph_handlers.archiver.enabled:
                        cost_str_list.append('CARRYING_SIM_BUSY_PENALTY: {}'.format(PostureScoring.CARRYING_SIM_BUSY_PENALTY))
                relationship_tracker = next_body_target.relationship_tracker
                if not relationship_tracker.has_bit(sim.sim_id, RelationshipGlobalTuning.CAREGIVER_RELATIONSHIP_BIT):
                    cost += PostureScoring.CARRYING_SIM_NON_CAREGIVER_PENALTY
                    if gsi_handlers.posture_graph_handlers.archiver.enabled:
                        cost_str_list.append('CARRYING_SIM_NON_CAREGIVER_PENALTY: {}'.format(PostureScoring.CARRYING_SIM_NON_CAREGIVER_PENALTY))
                if not relationship_tracker.has_bit(sim.sim_id, RelationshipGlobalTuning.HAS_MET_RELATIONSHIP_BIT):
                    cost += PostureScoring.CARRYING_SIM_HAS_NOT_MET_PENALTY
                    if gsi_handlers.posture_graph_handlers.archiver.enabled:
                        cost_str_list.append('CARRYING_SIM_HAS_NOT_MET_PENALTY: {}'.format(PostureScoring.CARRYING_SIM_HAS_NOT_MET_PENALTY))
            elif not may_reserve_posture_target(sim, next_node, next_body_target):
                cost += PostureScoring.OBJECT_RESERVED_PENALTY
                if gsi_handlers.posture_graph_handlers.archiver.enabled:
                    cost_str_list.append('OBJECT_RESERVED_PENALTY: {}'.format(PostureScoring.OBJECT_RESERVED_PENALTY))
        (edge_info, _) = self._get_edge_info(curr_node, next_node)
        edge_cost = edge_info.cost(sim.species)
        cost += edge_cost
        if gsi_handlers.posture_graph_handlers.archiver.enabled:
            for operation in edge_info.operations:
                cost_str_list.append('OpCost({}): {}'.format(type(operation).__name__, edge_cost))
                operation_cost_str_list = operation.debug_cost_str_list
                if operation_cost_str_list is not None:
                    for operation_cost_str in operation_cost_str_list:
                        cost_str_list.append('\t' + operation_cost_str)
            cost_str_list.insert(0, 'Score: {}'.format(cost))
            logger.debug('Score: {}, curr_node: {}, next_node: {}', cost, curr_node, next_node)
            gsi_handlers.posture_graph_handlers.log_path_cost(sim, curr_node, next_node, cost_str_list)
        return cost

    def _get_edge_info(self, node, successor):
        original_node_body_target = None
        original_successor_body_target = None
        if node.body_target.is_sim:
            original_node_body_target = node.body_target
            node = node.clone(body=PostureAspectBody((PostureTuning.SIM_CARRIED_POSTURE, self._graph.proxy_sim)))
        if successor.body_target.is_sim:
            original_successor_body_target = successor.body_target
            successor = successor.clone(body=PostureAspectBody((PostureTuning.SIM_CARRIED_POSTURE, self._graph.proxy_sim)))
        edge_info = self._edge_info[(node, successor)]
        if node.body_target is not None and successor.body_target is not None and original_successor_body_target is not None:
            for operation in edge_info.operations:
                operation.set_target(original_successor_body_target)
        return (edge_info, original_node_body_target)

    def _adjacent_nodes_gen(self, sim, get_successors_fn, valid_edge_test, constraint, var_map, node, *, allow_pickups, allow_putdowns, allow_carried, reverse_path):
        node = node.graph_node
        is_mobile_at_none = isinstance(node, _MobileNode) and node.body_posture.mobile and (node.body_target is None and node.surface_target is None)
        is_routing_vehicle = False
        for sub_constraint in constraint:
            if sub_constraint.posture_state_spec is None:
                pass
            else:
                posture_specs = [posture_spec for (posture_spec, var_map) in sub_constraint.posture_state_spec.get_posture_specs_gen() if posture_spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX] == node[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]]
                for spec in posture_specs:
                    if spec[BODY_INDEX][BODY_TARGET_INDEX] in PostureSpecVariable or node[BODY_INDEX][BODY_TARGET_INDEX] is spec[BODY_INDEX][BODY_TARGET_INDEX]:
                        is_routing_vehicle = True
                        break
        skip_adjacent = reverse_path or node.body_posture.is_vehicle and is_mobile_at_none or is_routing_vehicle
        skip_adjacent = False
        if node.body_posture.mobile and node.body_posture.skip_route and allow_carried or skip_adjacent:
            return

        def _edge_validation(forward_nodes, successor_node):
            if valid_edge_test is not None and not valid_edge_test(*forward_nodes):
                return
            (edge_info, node_body_target) = self._get_edge_info(*forward_nodes)
            if not edge_info.validate(sim, var_map, original_body_target=node_body_target):
                return
            elif successor_node.body_posture.mobile:
                return _MobileNode(successor_node, node)
            else:
                return successor_node
            return successor_node

        for successor in get_successors_fn(node):
            body_target = successor.body_target
            if not skip_adjacent or not body_target is None:
                if not body_target.is_sim:
                    pass
                else:
                    forward_nodes = (successor, node) if reverse_path else (node, successor)
                    (first, second) = forward_nodes
                    if allow_pickups or not first.carry_target is None or second.carry_target is not None:
                        pass
                    elif allow_putdowns or not first.carry_target is not None or second.carry_target is None:
                        pass
                    elif not body_target is not None or body_target.is_sim:
                        for carry_succesor in self._graph.sim_carry_nodes_gen(successor):
                            if node.body_target is carry_succesor.body_target:
                                pass
                            else:
                                carry_forward_nodes = (carry_succesor, node) if reverse_path else (node, carry_succesor)
                                (first_carry, second_carry) = carry_forward_nodes
                                if allow_pickups or not first_carry.carry_target is None or second_carry.carry_target is not None:
                                    pass
                                elif allow_putdowns or not first_carry.carry_target is not None or second_carry.carry_target is None:
                                    pass
                                else:
                                    return_node = _edge_validation(carry_forward_nodes, carry_succesor)
                                    if return_node is not None:
                                        yield return_node
                    else:
                        return_node = _edge_validation(forward_nodes, successor)
                        if return_node is not None:
                            yield return_node

    @staticmethod
    def _get_destination_locations_for_estimate(route_target, mobile_node):
        locations = route_target.get_position_and_routing_surface_for_posture(mobile_node)
        return locations

    def get_vehicle_destination_target(self, source, destinations):
        if source.body_target is None:
            return
        destination_body_target = None
        for dest in destinations:
            if not dest.body_posture.is_vehicle:
                return
            if destination_body_target is not None and destination_body_target != dest.body_target:
                return
            else:
                destination_body_target = dest.body_target
                if destination_body_target is not None and source.body_target.id == destination_body_target.id:
                    return destination_body_target
        if destination_body_target is not None and source.body_target.id == destination_body_target.id:
            return destination_body_target

    def _left_path_gen(self, sim, source, destinations, interaction, constraint, var_map, valid_edge_test, is_complete):
        carry_target = var_map.get(PostureSpecVariable.CARRY_TARGET)
        allow_carried = False
        sim_routing_context = sim.get_routing_context()
        if is_complete:
            if source[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile and source[SURFACE_INDEX][SURFACE_TARGET_INDEX] is None and not source[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].is_vehicle:
                return
            search_destinations = set(destinations) - self._graph.all_mobile_nodes_at_none
            if not search_destinations:
                return
        elif carry_target is sim:
            destination_body = PostureAspectBody((PostureTuning.SIM_CARRIED_POSTURE, interaction.sim))
            destination_surface = PostureAspectSurface((None, None, None))
            search_destinations = {source.clone(body=destination_body, surface=destination_surface)}
            allow_carried = True
        else:
            search_destinations = set(STAND_AT_NONE_NODES)
            if sim.is_human:
                search_destinations.update(self._graph.all_mobile_nodes_at_none_no_carry)
                if source.body_posture.is_vehicle and source in destinations:
                    search_destinations.update(self._graph.vehicle_nodes)
                else:
                    vehicle_destination_target = self.get_vehicle_destination_target(source, destinations)
                    if vehicle_destination_target is not None:
                        search_destinations.update(self._graph.nodes_for_object_gen(vehicle_destination_target))
            else:
                search_destinations.update(self._graph.all_mobile_nodes_at_none)
        distance_fn = functools.partial(self.distance_fn, sim, var_map, interaction)
        allow_pickups = False
        if carry_target.is_in_sim_inventory(sim=sim):
            allow_pickups = True
        elif carry_target.parent is not None and (carry_target.parent.is_same_object_or_part(sim.posture_state.surface_target) or carry_target.parent.is_same_object_or_part(sim)):
            allow_pickups = True
        else:
            sim_constraint = interactions.constraints.Transform(sim.intended_transform, routing_surface=sim.intended_routing_surface)
            carry_constraint = carry_target.get_carry_transition_constraint(sim, carry_target.position, carry_target.routing_surface, mobile=False)
            if carry_target.parent is not None:
                ignored_objects = (sim.posture_state.body_target, sim.posture_state.surface_target)
            else:
                ignored_objects = (sim.posture_state.body_target,)
            (result, _) = carry_target.check_line_of_sight(sim.intended_transform, ignored_objects=ignored_objects, for_carryable=True)
            allow_pickups = True
        allow_putdowns = allow_pickups
        adjacent_nodes_gen = functools.partial(self._adjacent_nodes_gen, sim, self._graph.get_successors, valid_edge_test, constraint, var_map, reverse_path=False, allow_pickups=allow_pickups, allow_putdowns=allow_putdowns, allow_carried=allow_carried)

        def left_distance_fn(curr_node, next_node):
            if isinstance(curr_node, _MobileNode):
                curr_node = curr_node.graph_node
            if isinstance(next_node, _MobileNode):
                next_node = next_node.graph_node
            if next_node is None:
                if curr_node in destinations:
                    return self._get_goal_cost(sim, interaction, constraint, var_map, curr_node)
                return 0.0
            return distance_fn(curr_node, next_node)

        def heuristic_fn_left(node):
            is_mobile_node = isinstance(node, _MobileNode)
            if is_mobile_node:
                graph_node = node.graph_node
                node = node.prev
                heuristic = 0
            else:
                graph_node = node
                heuristic = postures.posture_specs.PostureOperation.COST_STANDARD
            if node.body_target is None or node.body_posture.is_vehicle:
                return 0
            if is_mobile_node and node.body_target.is_sim:
                return 0
            locations = node.body_target.get_locations_for_posture(graph_node)
            source_locations = ((source_location.transform.translation, source_location.routing_surface if source_location.routing_surface is not None else node.body_target.routing_surface) for source_location in locations)
            destination_locations = []
            carry_target = var_map[PostureSpecVariable.CARRY_TARGET]
            if carry_target is None or carry_target.definition is carry_target:
                needs_constraint_dests = False
                for dest in destinations:
                    if dest.body_target is not None:
                        destination_locations += self._get_destination_locations_for_estimate(dest.body_target, graph_node)
                    elif dest.surface_target is not None:
                        destination_locations += self._get_destination_locations_for_estimate(dest.surface_target, graph_node)
                    else:
                        needs_constraint_dests = True
                if any(sub_constraint.geometry for sub_constraint in constraint):
                    for sub_constraint in constraint:
                        if not sub_constraint.geometry is None:
                            if sub_constraint.routing_surface is None:
                                pass
                            else:
                                for polygon in sub_constraint.geometry.polygon:
                                    for polygon_corner in polygon:
                                        destination_locations.append((polygon_corner, sub_constraint.routing_surface))
            elif carry_target.is_in_inventory():
                inv = carry_target.get_inventory()
                if inv.owner is not None and inv.owner.is_sim:
                    return heuristic
                for owner in inv.owning_objects_gen():
                    destination_locations += self._get_destination_locations_for_estimate(owner, graph_node)
            else:
                destination_locations += self._get_destination_locations_for_estimate(carry_target, graph_node)
            heuristic += primitives.routing_utils.estimate_distance_between_multiple_points(source_locations, destination_locations, sim_routing_context)
            if gsi_handlers.posture_graph_handlers.archiver.enabled:
                gsi_handlers.posture_graph_handlers.add_heuristic_fn_score(sim, 'left', node, graph_node, heuristic)
            return heuristic

        paths = _shortest_path_gen(sim, (source,), search_destinations, adjacent_nodes_gen, left_distance_fn, heuristic_fn_left)
        for path in paths:
            path = algos.Path(list(path), path.cost - left_distance_fn(path[-1], None))
            yield path

    def clear_goal_costs(self):
        self._get_goal_cost.cache.clear()

    @caches.cached
    def _get_goal_cost(self, sim, interaction, constraint, var_map, dest):
        cost = self._goal_costs.get(dest, 0.0)
        node_target = dest.body_target
        if not dest[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].is_vehicle:
            cost += constraint.constraint_cost(node_target.position, node_target.orientation)
        if not (node_target is not None and any(c.cost for c in constraint)):
            return cost
        participant_type = interaction.get_participant_type(sim)
        animation_resolver_fn = interaction.get_constraint_resolver(None)
        (_, routing_data) = self._get_locations_from_posture(sim, dest, var_map, interaction=interaction, participant_type=participant_type, animation_resolver_fn=animation_resolver_fn, final_constraint=constraint)
        final_constraint = routing_data[0]
        if final_constraint is None:
            final_constraint = constraint
        if not final_constraint.valid:
            return sims4.math.MAX_FLOAT
        cost += final_constraint.cost
        return cost

    def _right_path_gen(self, sim, interaction, distance_estimator, left_destinations, destinations, var_map, constraint, valid_edge_test, path_left, *, allow_carried):
        adjacent_nodes_gen = functools.partial(self._adjacent_nodes_gen, sim, self._graph.get_predecessors, valid_edge_test, constraint, var_map, reverse_path=True, allow_pickups=False, allow_putdowns=True, allow_carried=allow_carried)

        def reversed_distance_fn(curr_node, next_node):
            if next_node is None:
                return 0.0
            return self.distance_fn(sim, var_map, interaction, next_node, curr_node)

        weighted_sources = {dest: self._get_goal_cost(sim, interaction, constraint, var_map, dest) for dest in destinations}
        for node in reversed(path_left):
            if node.body_target:
                locations = node.body_target.get_locations_for_posture(path_left[-1])
                if locations:
                    sim_location = locations[0]
                    break
        sim_location = sim.routing_location
        sim_routing_context = sim.get_routing_context()

        @BarebonesCache
        def heuristic_fn_right(node):
            if isinstance(node, _MobileNode):
                graph_node = node.graph_node
                node = node.prev
            else:
                graph_node = node
            node_body_posture_is_mobile = node.body_posture.mobile
            body_target = node[BODY_INDEX][BODY_TARGET_INDEX]
            if body_target is interaction.sim:
                return postures.posture_specs.PostureOperation.COST_STANDARD
            distances = set()
            if node.body_target is not None:
                locations = node.body_target.get_locations_for_posture(graph_node)
                if locations:
                    body_target_distance = min(distance_estimator.estimate_location_distance((sim_location, location, node_body_posture_is_mobile)) for location in locations)
                    if node.body_target is not None:
                        routing_context = sim_routing_context
                        if node.body_target.is_sim:
                            routing_context = node.body_target.routing_context
                        body_target_locations = self._get_destination_locations_for_estimate(node.body_target, graph_node)
                        destination_locations = []
                        for dest in destinations:
                            if dest.body_target is not None:
                                destination_locations += self._get_destination_locations_for_estimate(dest.body_target, graph_node)
                        body_target_distance += primitives.routing_utils.estimate_distance_between_multiple_points(body_target_locations, destination_locations, routing_context)
                    distances.add(body_target_distance)
            if node.surface_target is not None:
                locations = node.surface_target.get_locations_for_posture(graph_node)
                if locations:
                    distances.add(min(distance_estimator.estimate_location_distance((sim_location, location, node_body_posture_is_mobile)) for location in locations))
            if not distances:
                sim_routing_location = (sim.position, sim.routing_surface)
                for sub_constraint in constraint:
                    routing_positions = sub_constraint.routing_positions
                    if not routing_positions:
                        pass
                    elif sub_constraint.routing_surface is None:
                        pass
                    else:
                        routing_surfaces = sub_constraint.get_all_valid_routing_surfaces(empty_set_for_invalid=True)
                        if not routing_surfaces:
                            pass
                        else:
                            routing_positions = [(position, routing_surface) for position in routing_positions for routing_surface in routing_surfaces]
                            distance = primitives.routing_utils.estimate_distance_between_multiple_points((sim_routing_location,), routing_positions)
                            distances.add(distance)
            if not distances:
                distances.add(distance_estimator.estimate_location_distance((sim_location, sim_location, node_body_posture_is_mobile)))
            heuristic = min(distances) if distances else postures.posture_specs.PostureOperation.COST_STANDARD
            if graph_node != path_left[-1]:
                heuristic += postures.posture_specs.PostureOperation.COST_STANDARD
            if gsi_handlers.posture_graph_handlers.archiver.enabled:
                gsi_handlers.posture_graph_handlers.add_heuristic_fn_score(sim, 'right', node, path_left[-1], heuristic)
            return heuristic

        if gsi_handlers.posture_graph_handlers.archiver.enabled:
            gsi_handlers.posture_graph_handlers.log_shortest_path_cost(sim, weighted_sources, heuristic_fn_right)
        paths_reversed = _shortest_path_gen(sim, weighted_sources, set(left_destinations), adjacent_nodes_gen, reversed_distance_fn, heuristic_fn_right)
        for path in paths_reversed:
            path = algos.Path(reversed(path), path.cost)
            yield path

    def _middle_path_gen(self, path_left, path_right, sim, interaction, distance_estimator, var_map):
        if path_left[-1].carry == path_right[0].carry:
            yield None
            return
        carry_target = var_map[PostureSpecVariable.CARRY_TARGET]
        if carry_target is None:
            raise ValueError('Interaction requires a carried object in its animation but has no carry_target: {} {}', interaction, var_map)
        if isinstance(carry_target, Definition):
            return
        pickup_cost = PostureOperation.PickUpObject.get_pickup_cost(path_left[-1])
        if carry_target.is_sim:
            surface_target = carry_target.posture_state.surface_target
            if surface_target is not None:
                pickup_path = self.get_pickup_path(surface_target, interaction)
                pickup_path.cost += pickup_cost
                yield pickup_path
                return
        else:
            parent_slot = carry_target.parent_slot
            if parent_slot is not None and parent_slot.owner is not sim:
                if parent_slot.owner.is_sim:
                    return []
                surface_target = parent_slot.owner
                if not surface_target.is_surface():
                    raise ValueError('Cannot pick up an object: {} from an invalid surface: {}'.format(carry_target, surface_target))
                pickup_path = self.get_pickup_path(surface_target, interaction)
                pickup_path.cost += pickup_cost
                yield pickup_path
                return
        carry_target_inventory = carry_target.get_inventory()
        if carry_target_inventory is None or carry_target.is_in_sim_inventory():
            carry_routing_surface = carry_target.routing_surface
            if carry_routing_surface is not None and carry_routing_surface.type == routing.SurfaceType.SURFACETYPE_POOL:
                yield algos.Path([SWIM_AT_NONE, SWIM_AT_NONE_CARRY], pickup_cost)
            else:
                yield algos.Path([STAND_AT_NONE, STAND_AT_NONE_CARRY], pickup_cost)
            return
        if interaction is not None:
            obj_with_inventory = interaction.object_with_inventory
            if obj_with_inventory is not None:
                if not obj_with_inventory.can_access_for_pickup(sim):
                    return
                pickup_path = self.get_pickup_path(obj_with_inventory, interaction)
                pickup_path.cost += pickup_cost
                yield pickup_path
                return
        inv_objects = list(carry_target_inventory.owning_objects_gen())
        if not inv_objects:
            logger.warn('Attempt to plan a middle path for an inventory with no owning objects: {} on interaction: {}', carry_target_inventory, interaction, owner='bhill')
            return
        for node in path_right:
            if node.body_target or node.surface_target:
                right_target = node.body_target or node.surface_target
                break
        right_target = None

        def inv_owner_dist(owner):
            (routing_position, _) = Constraint.get_validated_routing_position(owner)
            routing_location = routing.Location(routing_position, orientation=owner.orientation, routing_surface=owner.routing_surface)
            dist = distance_estimator.estimate_distance((sim.location, routing_location))
            dist += distance_estimator.get_preferred_object_cost(owner)
            if right_target:
                (right_target_position, _) = Constraint.get_validated_routing_position(right_target)
                right_target_location = routing.Location(right_target_position, orientation=right_target.orientation, routing_surface=right_target.routing_surface)
                dist += distance_estimator.estimate_distance((routing_location, right_target_location))
            return dist

        inv_objects.sort(key=inv_owner_dist)
        for inv_object in inv_objects:
            if not inv_object.can_access_for_pickup(sim):
                pass
            else:
                pickup_path = self.get_pickup_path(inv_object, interaction)
                pickup_path.cost += pickup_cost
                yield pickup_path

    def _get_all_paths(self, sim, source, destinations, var_map, constraint, valid_edge_test, interaction=None, allow_complete=True):
        distance_estimator = DistanceEstimator(self, sim, interaction, constraint)
        segmented_paths = []
        stand_path = SegmentedPath(self, sim, source, destinations, var_map, constraint, valid_edge_test, interaction, is_complete=False, distance_estimator=distance_estimator)
        segmented_paths.append(stand_path)
        if allow_complete:
            complete = SegmentedPath(self, sim, source, destinations, var_map, constraint, valid_edge_test, interaction, is_complete=True, distance_estimator=distance_estimator)
            segmented_paths.append(complete)
        return segmented_paths

    def get_pickup_path(self, surface_target, interaction):
        cost_pickup = 0
        path_pickup = [STAND_AT_NONE]
        sequence_pickup = get_pick_up_spec_sequence(STAND_AT_NONE, surface_target)
        path_pickup.extend(sequence_pickup)
        path_pickup.append(STAND_AT_NONE_CARRY)
        if interaction is not None:
            preferred_objects = interaction.preferred_objects
            cost_pickup += postures.posture_scoring.PostureScoring.get_preferred_object_cost((surface_target,), preferred_objects)
        return algos.Path(path_pickup, cost_pickup)

    def any_template_passes_destination_test(self, templates, si, sim, node):
        if not node.body_posture._supports_carry:
            return False
        for template in templates.values():
            for (dest_spec, var_map) in template:
                if postures.posture_specs.destination_test(sim, node, (dest_spec,), var_map, None, si):
                    return True
        return False

    def get_segmented_paths(self, sim, posture_dest_list, additional_template_list, interaction, participant_type, valid_destination_test, valid_edge_test, preferences, final_constraint, included_sis):
        possible_destinations = []
        all_segmented_paths = []
        self._goal_costs.clear()
        if gsi_handlers.posture_graph_handlers.archiver.enabled:
            gsi_templates = [(ds, vm, c) for (c, value) in posture_dest_list.items() for (ds, vm) in value]
            gsi_handlers.posture_graph_handlers.add_templates_to_gsi(sim, gsi_templates)
        guaranteed_sis = list(sim.si_state.all_guaranteed_si_gen(interaction.priority, interaction.group_id))
        excluded_objects = interaction.excluded_posture_destination_objects()
        interaction_sims = set(interaction.get_participants(ParticipantType.AllSims))
        interaction_sims.discard(interaction.sim)
        relationship_bonuses = PostureScoring.build_relationship_bonuses(sim, interaction.sim_affinity_posture_scoring_data, sims_to_consider=interaction_sims)
        main_group = sim.get_main_group()
        if main_group is not None and main_group.constraint_initialized and not main_group.is_solo:
            group_constraint = main_group.get_constraint(sim)
        else:
            group_constraint = None
        found_destination_node = False
        for (constraint, templates) in posture_dest_list.items():
            destination_nodes = {}
            var_map_all = DEFAULT
            destination_specs = set()
            slot_types = set()
            for (destination_spec, var_map) in templates:
                destination_specs.add(destination_spec)
                slot = var_map.get(PostureSpecVariable.SLOT)
                if slot is not None:
                    slot_types.update(slot.slot_types)
                if var_map_all is DEFAULT:
                    var_map_all = var_map
                if gsi_handlers.posture_graph_handlers.archiver.enabled:
                    possible_destinations.append(destination_spec)
            slot_all = var_map_all.get(PostureSpecVariable.SLOT)
            if slot_all is not None:
                new_slot_manifest = slot_all.with_overrides(slot=frozenset(slot_types))
                var_map_all = frozendict(var_map_all, {PostureSpecVariable.SLOT: new_slot_manifest})
            source_spec = sim.posture_state.get_posture_spec(var_map_all)
            if source_spec is None:
                pass
            else:
                if not source_spec.body_target.is_part:
                    new_body = PostureAspectBody((source_spec.body_posture, None))
                    new_surface = PostureAspectSurface((None, None, None))
                    source_spec = source_spec.clone(body=new_body, surface=new_surface)
                if source_spec.body_posture.mobile and (source_spec.body_posture.unconstrained and source_spec.body_target is not None) and source_spec not in self._graph:
                    if services.current_zone().is_zone_shutting_down:
                        return []
                    raise AssertionError('Source spec not in the posture graph: {} for interaction: {}'.format(source_spec, interaction))
                source_node = source_spec
                if gsi_handlers.posture_graph_handlers.archiver.enabled:
                    gsi_handlers.posture_graph_handlers.add_source_or_dest(sim, (source_spec,), var_map_all, 'source', source_node)
                distance_estimator = DistanceEstimator(self, sim, interaction, constraint)
                same_mobile_body_target = source_node.body_posture.mobile
                if same_mobile_body_target:
                    if source_node.body_target is not None and source_node.body_target.is_part:
                        adjacent_source_parts = source_node.body_target.adjacent_parts_gen()
                    else:
                        adjacent_source_parts = ()
                for node in self._graph.get_matching_nodes_gen(destination_specs, slot_types, constraint=final_constraint):
                    if node.get_core_objects() & excluded_objects:
                        pass
                    elif not destination_test(sim, node, destination_specs, var_map_all, valid_destination_test, interaction):
                        pass
                    elif included_sis and node.body.target is not None and any(not node.body.target.supports_affordance(si.affordance) for si in included_sis):
                        pass
                    else:
                        if node.body.target not in adjacent_source_parts:
                            same_mobile_body_target = False
                        if same_mobile_body_target and (node.body.target is not None and node.body.target is not source_node.body_target) and interaction.is_putdown:
                            obj = node.body_target
                            if obj is not None:
                                if obj.is_part:
                                    obj = obj.part_owner
                                if not interaction.is_object_valid(obj, distance_estimator):
                                    pass
                                elif additional_template_list and not interaction.is_putdown:
                                    compatible = True
                                    for (carry_si, additional_templates) in additional_template_list.items():
                                        if carry_si not in guaranteed_sis:
                                            pass
                                        else:
                                            compatible = self.any_template_passes_destination_test(additional_templates, carry_si, sim, node)
                                            if compatible:
                                                break
                                    if not compatible:
                                        pass
                                    else:
                                        if gsi_handlers.posture_graph_handlers.archiver.enabled:
                                            gsi_handlers.posture_graph_handlers.add_source_or_dest(sim, destination_specs, var_map_all, 'destination', node)
                                        destination_nodes[node] = destination_specs
                                else:
                                    if gsi_handlers.posture_graph_handlers.archiver.enabled:
                                        gsi_handlers.posture_graph_handlers.add_source_or_dest(sim, destination_specs, var_map_all, 'destination', node)
                                    destination_nodes[node] = destination_specs
                            elif additional_template_list and not interaction.is_putdown:
                                compatible = True
                                for (carry_si, additional_templates) in additional_template_list.items():
                                    if carry_si not in guaranteed_sis:
                                        pass
                                    else:
                                        compatible = self.any_template_passes_destination_test(additional_templates, carry_si, sim, node)
                                        if compatible:
                                            break
                                if not compatible:
                                    pass
                                else:
                                    if gsi_handlers.posture_graph_handlers.archiver.enabled:
                                        gsi_handlers.posture_graph_handlers.add_source_or_dest(sim, destination_specs, var_map_all, 'destination', node)
                                    destination_nodes[node] = destination_specs
                            else:
                                if gsi_handlers.posture_graph_handlers.archiver.enabled:
                                    gsi_handlers.posture_graph_handlers.add_source_or_dest(sim, destination_specs, var_map_all, 'destination', node)
                                destination_nodes[node] = destination_specs
                        elif additional_template_list and not interaction.is_putdown:
                            compatible = True
                            for (carry_si, additional_templates) in additional_template_list.items():
                                if carry_si not in guaranteed_sis:
                                    pass
                                else:
                                    compatible = self.any_template_passes_destination_test(additional_templates, carry_si, sim, node)
                                    if compatible:
                                        break
                            if not compatible:
                                pass
                            else:
                                if gsi_handlers.posture_graph_handlers.archiver.enabled:
                                    gsi_handlers.posture_graph_handlers.add_source_or_dest(sim, destination_specs, var_map_all, 'destination', node)
                                destination_nodes[node] = destination_specs
                        else:
                            if gsi_handlers.posture_graph_handlers.archiver.enabled:
                                gsi_handlers.posture_graph_handlers.add_source_or_dest(sim, destination_specs, var_map_all, 'destination', node)
                            destination_nodes[node] = destination_specs
                if destination_nodes:
                    found_destination_node = True
                else:
                    logger.debug('No destination_nodes found for destination_specs: {}', destination_specs)
                PostureScoring.build_destination_costs(self._goal_costs, destination_nodes, sim, interaction, var_map_all, preferences, included_sis, additional_template_list, relationship_bonuses, constraint, group_constraint)
                allow_complete = not source_node.body_posture.mobile or same_mobile_body_target
                if source_node.body_target is None:
                    current_constraint = constraints.Transform(sim.transform, routing_surface=sim.routing_surface)
                    intersection = current_constraint.intersect(constraint)
                    if not intersection.valid:
                        allow_complete = False
                interaction_outfit_changes = interaction.get_tuned_outfit_changes(include_exit_changes=False)
                if allow_complete and interaction_outfit_changes:
                    for outfit_change in interaction_outfit_changes:
                        if not sim.sim_info.is_wearing_outfit(outfit_change):
                            allow_complete = False
                is_sim_carry = _is_sim_carry(interaction, sim)
                if allow_complete:
                    source_body_target = source_node.body_target
                    if is_sim_carry:
                        complete_destinations = destination_nodes
                    elif source_body_target is None:
                        complete_destinations = [dest_node for dest_node in destination_nodes if dest_node.body_target is None]
                    else:
                        if source_body_target.is_part:
                            source_body_target = source_body_target.part_owner
                        complete_destinations = [dest_node for dest_node in destination_nodes if source_body_target.is_same_object_or_part(dest_node.body_target)]
                    if not is_sim_carry:
                        for dest_node in complete_destinations:
                            outfit_change = dest_node.body.posture_type.outfit_change
                            if outfit_change:
                                entry_change_outfit = outfit_change.get_on_entry_outfit(interaction, sim_info=sim.sim_info)
                                if entry_change_outfit is not None and not sim.sim_info.is_wearing_outfit(entry_change_outfit):
                                    pass
                                else:
                                    allow_complete = True
                                    break
                            else:
                                allow_complete = True
                                break
                        allow_complete = False
                segmented_paths = self._get_all_paths(sim, source_node, destination_nodes, var_map_all, constraint, valid_edge_test, interaction=interaction, allow_complete=allow_complete)
                all_segmented_paths.extend(segmented_paths)
        if self._goal_costs:
            lowest_goal_cost = min(self._goal_costs.values())
            for (goal_node, cost) in self._goal_costs.items():
                self._goal_costs[goal_node] = cost - lowest_goal_cost
        if not all_segmented_paths:
            if not found_destination_node:
                set_transition_failure_reason(sim, TransitionFailureReasons.NO_DESTINATION_NODE, transition_controller=interaction.transition)
            else:
                set_transition_failure_reason(sim, TransitionFailureReasons.NO_PATH_FOUND, transition_controller=interaction.transition)
        return all_segmented_paths

    def handle_additional_pickups_and_putdowns(self, best_path_spec, additional_template_list, sim, can_defer_putdown=True):
        included_sis = set()
        if not (best_path_spec.transition_specs and additional_template_list):
            return included_sis
        best_transition_specs = best_path_spec.transition_specs
        final_transition_spec = best_transition_specs[-1]
        final_node = final_transition_spec.posture_spec
        final_var_map = final_transition_spec.var_map
        final_hand = final_var_map[PostureSpecVariable.HAND]
        final_spec_constraint = best_path_spec.spec_constraint
        final_carry_target = final_var_map[PostureSpecVariable.CARRY_TARGET]
        slot_manifest_entry = final_var_map.get(PostureSpecVariable.SLOT)
        additional_template_added = False
        for (carry_si, additional_templates) in additional_template_list.items():
            carry_si_carryable = carry_si.carry_target
            if carry_si.target.carryable_component is not None:
                carry_si_carryable = carry_si.target
            if carry_si_carryable is None and carry_si.target is not None and carry_si_carryable is final_carry_target:
                included_sis.add(carry_si)
                additional_template_added = True
            else:
                valid_additional_intersection = False
                for (destination_spec_additional, var_map_additional, constraint_additional) in [(ds, vm, c) for (c, value) in additional_templates.items() for (ds, vm) in value]:
                    additional_hand = var_map_additional[PostureSpecVariable.HAND]
                    if final_hand == additional_hand:
                        pass
                    elif additional_template_added:
                        pass
                    else:
                        valid_destination = destination_test(sim, final_node, (destination_spec_additional,), var_map_additional, None, carry_si)
                        valid_intersection = constraint_additional.intersect(final_spec_constraint).valid
                        if not valid_intersection:
                            pass
                        else:
                            valid_additional_intersection = True
                            if not valid_destination:
                                pass
                            else:
                                carry_target = var_map_additional[PostureSpecVariable.CARRY_TARGET]
                                container = carry_target.parent
                                if final_node[SURFACE_INDEX][SURFACE_TARGET_INDEX] is container:
                                    included_sis.add(carry_si)
                                else:
                                    additional_slot_manifest_entry = var_map_additional.get(PostureSpecVariable.SLOT)
                                    if additional_slot_manifest_entry is not None and slot_manifest_entry is not None and slot_manifest_entry.slot_types.intersection(additional_slot_manifest_entry.slot_types):
                                        pass
                                    else:
                                        if container is not sim:
                                            insertion_index = 0
                                            fallback_insertion_index_and_spec = None
                                            original_spec = best_transition_specs[0].posture_spec
                                            if original_spec[SURFACE_INDEX][SURFACE_TARGET_INDEX] is container:
                                                fallback_insertion_index_and_spec = InsertionIndexAndSpec(insertion_index, original_spec)
                                            for (prev_transition_spec, transition_spec) in zip(best_transition_specs, best_transition_specs[1:]):
                                                insertion_index += 1
                                                if transition_spec.sequence_id != prev_transition_spec.sequence_id:
                                                    pass
                                                else:
                                                    spec = transition_spec.posture_spec
                                                    if spec[SURFACE_INDEX][SURFACE_TARGET_INDEX] is container:
                                                        fallback_insertion_index_and_spec = InsertionIndexAndSpec(insertion_index, spec)
                                                    if fallback_insertion_index_and_spec is None and prev_transition_spec.posture_spec[CARRY_INDEX][CARRY_TARGET_INDEX] is None and spec[CARRY_INDEX][CARRY_TARGET_INDEX] is not None:
                                                        if spec[SURFACE_INDEX][SURFACE_TARGET_INDEX] is not container:
                                                            pass
                                                        else:
                                                            break
                                            if fallback_insertion_index_and_spec is not None:
                                                insertion_index = fallback_insertion_index_and_spec.index
                                                spec = fallback_insertion_index_and_spec.spec
                                                pick_up_sequence = get_pick_up_spec_sequence(spec, container, body_target=spec[BODY_INDEX][BODY_TARGET_INDEX])
                                                slot_var_map = {PostureSpecVariable.SLOT: SlotManifestEntry(carry_target, container, carry_target.parent_slot)}
                                                var_map_additional_updated = frozendict(var_map_additional, slot_var_map)
                                                new_specs = []
                                                for pick_up_spec in pick_up_sequence:
                                                    new_specs.append(TransitionSpec(best_path_spec, pick_up_spec, var_map_additional_updated, sequence_id=SequenceId.PICKUP))
                                                best_path_spec.insert_transition_specs_at_index(insertion_index, new_specs)
                                                final_surface_target = final_node.surface.target if final_node.surface is not None else None
                                                if PostureSpecVariable.SLOT in var_map_additional:
                                                    _slot_manifest_entry = var_map_additional[PostureSpecVariable.SLOT]
                                                    overrides = {}
                                                    if isinstance(_slot_manifest_entry.target, PostureSpecVariable):
                                                        overrides['target'] = final_surface_target
                                                    interaction_target = final_var_map[PostureSpecVariable.INTERACTION_TARGET]
                                                    if interaction_target is not None:
                                                        relative_position = interaction_target.position
                                                    else:
                                                        relative_position = final_surface_target.position
                                                    chosen_slot = self._get_best_slot(final_surface_target, _slot_manifest_entry.slot_types, carry_target, relative_position)
                                                    if chosen_slot is None:
                                                        pass
                                                    else:
                                                        overrides['slot'] = chosen_slot
                                                        _slot_manifest_entry = _slot_manifest_entry.with_overrides(**overrides)
                                                        slot_var_map = {PostureSpecVariable.SLOT: _slot_manifest_entry}
                                                        var_map_additional = frozendict(var_map_additional, slot_var_map)
                                                        if additional_slot_manifest_entry is not None:
                                                            insertion_index = 0
                                                            fallback_insertion_index_and_spec = None
                                                            original_spec = best_transition_specs[0].posture_spec
                                                            if original_spec[SURFACE_INDEX][SURFACE_TARGET_INDEX] is slot_manifest_entry.actor.parent:
                                                                fallback_insertion_index_and_spec = InsertionIndexAndSpec(insertion_index, original_spec)
                                                            for (prev_transition_spec, transition_spec) in zip(best_transition_specs, best_transition_specs[1:]):
                                                                insertion_index += 1
                                                                if transition_spec.sequence_id != prev_transition_spec.sequence_id:
                                                                    pass
                                                                else:
                                                                    spec = transition_spec.posture_spec
                                                                    if spec[SURFACE_INDEX][SURFACE_TARGET_INDEX] is slot_manifest_entry.actor.parent:
                                                                        fallback_insertion_index_and_spec = InsertionIndexAndSpec(insertion_index, spec)
                                                                    if fallback_insertion_index_and_spec is None and prev_transition_spec.posture_spec[CARRY_INDEX][CARRY_TARGET_INDEX] is not None and spec[CARRY_INDEX][CARRY_TARGET_INDEX] is None:
                                                                        break
                                                            if fallback_insertion_index_and_spec is not None:
                                                                insertion_index = fallback_insertion_index_and_spec.index
                                                                spec = fallback_insertion_index_and_spec.spec
                                                                put_down_sequence = get_put_down_spec_sequence(spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX], spec[SURFACE_INDEX][SURFACE_TARGET_INDEX], body_target=spec[BODY_INDEX][BODY_TARGET_INDEX])
                                                                new_specs = []
                                                                for put_down_spec in put_down_sequence:
                                                                    new_specs.append(TransitionSpec(best_path_spec, put_down_spec, var_map_additional, sequence_id=SequenceId.PUTDOWN))
                                                                best_path_spec.insert_transition_specs_at_index(insertion_index + 1, new_specs)
                                                                included_sis.add(carry_si)
                                                                additional_template_added = True
                                                                break
                                                        included_sis.add(carry_si)
                                                        additional_template_added = True
                                                        break
                                                if final_surface_target is not None and additional_slot_manifest_entry is not None:
                                                    insertion_index = 0
                                                    fallback_insertion_index_and_spec = None
                                                    original_spec = best_transition_specs[0].posture_spec
                                                    if original_spec[SURFACE_INDEX][SURFACE_TARGET_INDEX] is slot_manifest_entry.actor.parent:
                                                        fallback_insertion_index_and_spec = InsertionIndexAndSpec(insertion_index, original_spec)
                                                    for (prev_transition_spec, transition_spec) in zip(best_transition_specs, best_transition_specs[1:]):
                                                        insertion_index += 1
                                                        if transition_spec.sequence_id != prev_transition_spec.sequence_id:
                                                            pass
                                                        else:
                                                            spec = transition_spec.posture_spec
                                                            if spec[SURFACE_INDEX][SURFACE_TARGET_INDEX] is slot_manifest_entry.actor.parent:
                                                                fallback_insertion_index_and_spec = InsertionIndexAndSpec(insertion_index, spec)
                                                            if fallback_insertion_index_and_spec is None and prev_transition_spec.posture_spec[CARRY_INDEX][CARRY_TARGET_INDEX] is not None and spec[CARRY_INDEX][CARRY_TARGET_INDEX] is None:
                                                                break
                                                    if fallback_insertion_index_and_spec is not None:
                                                        insertion_index = fallback_insertion_index_and_spec.index
                                                        spec = fallback_insertion_index_and_spec.spec
                                                        put_down_sequence = get_put_down_spec_sequence(spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX], spec[SURFACE_INDEX][SURFACE_TARGET_INDEX], body_target=spec[BODY_INDEX][BODY_TARGET_INDEX])
                                                        new_specs = []
                                                        for put_down_spec in put_down_sequence:
                                                            new_specs.append(TransitionSpec(best_path_spec, put_down_spec, var_map_additional, sequence_id=SequenceId.PUTDOWN))
                                                        best_path_spec.insert_transition_specs_at_index(insertion_index + 1, new_specs)
                                                        included_sis.add(carry_si)
                                                        additional_template_added = True
                                                        break
                                                included_sis.add(carry_si)
                                                additional_template_added = True
                                                break
                                        final_surface_target = final_node.surface.target if final_node.surface is not None else None
                                        if PostureSpecVariable.SLOT in var_map_additional:
                                            _slot_manifest_entry = var_map_additional[PostureSpecVariable.SLOT]
                                            overrides = {}
                                            if isinstance(_slot_manifest_entry.target, PostureSpecVariable):
                                                overrides['target'] = final_surface_target
                                            interaction_target = final_var_map[PostureSpecVariable.INTERACTION_TARGET]
                                            if interaction_target is not None:
                                                relative_position = interaction_target.position
                                            else:
                                                relative_position = final_surface_target.position
                                            chosen_slot = self._get_best_slot(final_surface_target, _slot_manifest_entry.slot_types, carry_target, relative_position)
                                            if chosen_slot is None:
                                                pass
                                            else:
                                                overrides['slot'] = chosen_slot
                                                _slot_manifest_entry = _slot_manifest_entry.with_overrides(**overrides)
                                                slot_var_map = {PostureSpecVariable.SLOT: _slot_manifest_entry}
                                                var_map_additional = frozendict(var_map_additional, slot_var_map)
                                                if additional_slot_manifest_entry is not None:
                                                    insertion_index = 0
                                                    fallback_insertion_index_and_spec = None
                                                    original_spec = best_transition_specs[0].posture_spec
                                                    if original_spec[SURFACE_INDEX][SURFACE_TARGET_INDEX] is slot_manifest_entry.actor.parent:
                                                        fallback_insertion_index_and_spec = InsertionIndexAndSpec(insertion_index, original_spec)
                                                    for (prev_transition_spec, transition_spec) in zip(best_transition_specs, best_transition_specs[1:]):
                                                        insertion_index += 1
                                                        if transition_spec.sequence_id != prev_transition_spec.sequence_id:
                                                            pass
                                                        else:
                                                            spec = transition_spec.posture_spec
                                                            if spec[SURFACE_INDEX][SURFACE_TARGET_INDEX] is slot_manifest_entry.actor.parent:
                                                                fallback_insertion_index_and_spec = InsertionIndexAndSpec(insertion_index, spec)
                                                            if fallback_insertion_index_and_spec is None and prev_transition_spec.posture_spec[CARRY_INDEX][CARRY_TARGET_INDEX] is not None and spec[CARRY_INDEX][CARRY_TARGET_INDEX] is None:
                                                                break
                                                    if fallback_insertion_index_and_spec is not None:
                                                        insertion_index = fallback_insertion_index_and_spec.index
                                                        spec = fallback_insertion_index_and_spec.spec
                                                        put_down_sequence = get_put_down_spec_sequence(spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX], spec[SURFACE_INDEX][SURFACE_TARGET_INDEX], body_target=spec[BODY_INDEX][BODY_TARGET_INDEX])
                                                        new_specs = []
                                                        for put_down_spec in put_down_sequence:
                                                            new_specs.append(TransitionSpec(best_path_spec, put_down_spec, var_map_additional, sequence_id=SequenceId.PUTDOWN))
                                                        best_path_spec.insert_transition_specs_at_index(insertion_index + 1, new_specs)
                                                        included_sis.add(carry_si)
                                                        additional_template_added = True
                                                        break
                                                included_sis.add(carry_si)
                                                additional_template_added = True
                                                break
                                        if final_surface_target is not None and additional_slot_manifest_entry is not None:
                                            insertion_index = 0
                                            fallback_insertion_index_and_spec = None
                                            original_spec = best_transition_specs[0].posture_spec
                                            if original_spec[SURFACE_INDEX][SURFACE_TARGET_INDEX] is slot_manifest_entry.actor.parent:
                                                fallback_insertion_index_and_spec = InsertionIndexAndSpec(insertion_index, original_spec)
                                            for (prev_transition_spec, transition_spec) in zip(best_transition_specs, best_transition_specs[1:]):
                                                insertion_index += 1
                                                if transition_spec.sequence_id != prev_transition_spec.sequence_id:
                                                    pass
                                                else:
                                                    spec = transition_spec.posture_spec
                                                    if spec[SURFACE_INDEX][SURFACE_TARGET_INDEX] is slot_manifest_entry.actor.parent:
                                                        fallback_insertion_index_and_spec = InsertionIndexAndSpec(insertion_index, spec)
                                                    if fallback_insertion_index_and_spec is None and prev_transition_spec.posture_spec[CARRY_INDEX][CARRY_TARGET_INDEX] is not None and spec[CARRY_INDEX][CARRY_TARGET_INDEX] is None:
                                                        break
                                            if fallback_insertion_index_and_spec is not None:
                                                insertion_index = fallback_insertion_index_and_spec.index
                                                spec = fallback_insertion_index_and_spec.spec
                                                put_down_sequence = get_put_down_spec_sequence(spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX], spec[SURFACE_INDEX][SURFACE_TARGET_INDEX], body_target=spec[BODY_INDEX][BODY_TARGET_INDEX])
                                                new_specs = []
                                                for put_down_spec in put_down_sequence:
                                                    new_specs.append(TransitionSpec(best_path_spec, put_down_spec, var_map_additional, sequence_id=SequenceId.PUTDOWN))
                                                best_path_spec.insert_transition_specs_at_index(insertion_index + 1, new_specs)
                                                included_sis.add(carry_si)
                                                additional_template_added = True
                                                break
                                        included_sis.add(carry_si)
                                        additional_template_added = True
                                        break
                if not valid_additional_intersection:
                    if can_defer_putdown and carry_si_carryable.carryable_component.defer_putdown:
                        sim.transition_controller.has_deferred_putdown = True
                    else:
                        carry_si.cancel(FinishingType.TRANSITION_FAILURE, cancel_reason_msg='Posture Graph. No valid intersections for additional constraint.')
        return included_sis

    @staticmethod
    def is_valid_complete_path(sim, path, interaction):
        for posture_spec in path:
            target = posture_spec[BODY_INDEX][BODY_TARGET_INDEX]
            if target is interaction.target:
                reservation_handler = interaction.get_interaction_reservation_handler(sim=sim)
                if not reservation_handler is None:
                    if reservation_handler.may_reserve():
                        pass
                    else:
                        (can_remove, _, _) = can_remove_blocking_sims(sim, interaction, (target,))
                        if can_remove:
                            pass
                        elif target.usable_by_transition_controller(sim.queue.transition_controller):
                            pass
                        else:
                            return False
            else:
                reservation_handler = interaction.get_interaction_reservation_handler(sim=sim, target=target)
                if not reservation_handler is None:
                    if reservation_handler.may_reserve():
                        pass
                    else:
                        (can_remove, _, _) = can_remove_blocking_sims(sim, interaction, (target,))
                        if can_remove:
                            pass
                        elif target.usable_by_transition_controller(sim.queue.transition_controller):
                            pass
                        else:
                            return False
            (can_remove, _, _) = can_remove_blocking_sims(sim, interaction, (target,))
            if can_remove:
                pass
            elif target.usable_by_transition_controller(sim.queue.transition_controller):
                pass
            else:
                return False
        return True

    def get_sim_position_routing_data(self, sim):
        if sim.parent is not None and (sim.parent.is_sim or sim.posture_state.body.is_vehicle):
            return self.get_sim_position_routing_data(sim.parent)
        sim_position_constraint = interactions.constraints.Transform(sim.intended_transform, routing_surface=sim.intended_routing_surface, debug_name='SimCurrentPosition')
        return (sim_position_constraint, None, None)

    @staticmethod
    def append_handles(sim, handle_dict, invalid_handle_dict, invalid_los_dict, routing_data, target_path, var_map, dest_spec, cur_path_id, final_constraint, entry=True, path_type=PathType.LEFT, goal_height_limit=None, perform_los_check=True):
        (routing_constraint, locked_params, target) = routing_data
        if routing_constraint is None:
            return
        carry_target = var_map.get(PostureSpecVariable.CARRY_TARGET)
        for_carryable = carry_target is not None
        (reference_pt, top_level_parent) = Constraint.get_los_reference_point(target, is_carry_target=target is carry_target)
        if target is carry_target:
            goal_height_limit = None
            if top_level_parent is not sim:
                (reference_pt, top_level_parent) = (None, None)
        if not (path_type == PathType.RIGHT and perform_los_check):
            reference_pt = None
        blocking_obj_id = None
        if sim.routing_master is not None and sim.routing_master.get_routing_slave_data_count(FormationRoutingType.FOLLOW):
            target_reference_override = sim.routing_master
            goal_height_limit = FormationTuning.GOAL_HEIGHT_LIMIT
        else:
            target_reference_override = None
        for sub_constraint in routing_constraint:
            if not sub_constraint.valid:
                pass
            else:
                if sub_constraint.routing_surface is not None:
                    routing_surface = sub_constraint.routing_surface
                elif target is not None:
                    routing_surface = target.routing_surface
                else:
                    routing_surface = None
                connectivity_handles = sub_constraint.get_connectivity_handles(sim=sim, routing_surface_override=routing_surface, locked_params=locked_params, los_reference_point=reference_pt, entry=entry, target=target)
                for connectivity_handle in connectivity_handles:
                    connectivity_handle.path = target_path
                    connectivity_handle.var_map = var_map
                    existing_data = handle_dict.get(connectivity_handle)
                    if existing_data is not None and target_path.cost >= existing_data[1]:
                        pass
                    else:
                        if connectivity_handle.los_reference_point is None or test_point_in_compound_polygon(connectivity_handle.los_reference_point, connectivity_handle.geometry.polygon):
                            single_goal_only = True
                        else:
                            single_goal_only = False
                        for_source = path_type == PathType.LEFT and len(target_path) == 1
                        routing_goals = connectivity_handle.get_goals(relative_object=target, for_source=for_source, single_goal_only=single_goal_only, for_carryable=for_carryable, goal_height_limit=goal_height_limit, target_reference_override=target_reference_override, perform_los_check=perform_los_check)
                        if not routing_goals:
                            if gsi_handlers.posture_graph_handlers.archiver.enabled:
                                gsi_handlers.posture_graph_handlers.log_transition_handle(sim, connectivity_handle, connectivity_handle.polygons, target_path, 'no goals generated', path_type)
                                yield_to_irq()
                                valid_goals = []
                                invalid_goals = []
                                invalid_los_goals = []
                                ignore_los_for_vehicle = sim.posture.is_vehicle and sim.posture.target is target
                                for goal in routing_goals:
                                    if single_goal_only or not (goal.requires_los_check and target is not None and (target.is_sim or ignore_los_for_vehicle)):
                                        if top_level_parent is not target and not top_level_parent.is_sim:
                                            ignored_objects = (top_level_parent,)
                                        else:
                                            ignored_objects = ()
                                        (result, blocking_obj_id) = target.check_line_of_sight(goal.location.transform, verbose=True, for_carryable=for_carryable, ignored_objects=ignored_objects)
                                        if result == routing.RAYCAST_HIT_TYPE_IMPASSABLE:
                                            invalid_goals.append(goal)
                                        elif result == routing.RAYCAST_HIT_TYPE_LOS_IMPASSABLE:
                                            invalid_los_goals.append(goal)
                                        else:
                                            goal.path_id = cur_path_id
                                            valid_goals.append(goal)
                                    else:
                                        goal.path_id = cur_path_id
                                        valid_goals.append(goal)
                                if gsi_handlers.posture_graph_handlers.archiver.enabled and (invalid_goals or invalid_los_goals):
                                    gsi_handlers.posture_graph_handlers.log_transition_handle(sim, connectivity_handle, connectivity_handle.polygons, target_path, 'LOS Failure', path_type)
                                if invalid_goals:
                                    invalid_handle_dict[connectivity_handle] = (target_path, target_path.cost, var_map, dest_spec, invalid_goals, routing_constraint, final_constraint)
                                if invalid_los_goals:
                                    invalid_los_dict[connectivity_handle] = (target_path, target_path.cost, var_map, dest_spec, invalid_los_goals, routing_constraint, final_constraint)
                                if not valid_goals:
                                    pass
                                else:
                                    if gsi_handlers.posture_graph_handlers.archiver.enabled:
                                        gsi_handlers.posture_graph_handlers.log_transition_handle(sim, connectivity_handle, connectivity_handle.polygons, target_path, True, path_type)
                                    handle_dict[connectivity_handle] = (target_path, target_path.cost, var_map, dest_spec, valid_goals, routing_constraint, final_constraint)
                        else:
                            yield_to_irq()
                            valid_goals = []
                            invalid_goals = []
                            invalid_los_goals = []
                            ignore_los_for_vehicle = sim.posture.is_vehicle and sim.posture.target is target
                            for goal in routing_goals:
                                if single_goal_only or not (goal.requires_los_check and target is not None and (target.is_sim or ignore_los_for_vehicle)):
                                    if top_level_parent is not target and not top_level_parent.is_sim:
                                        ignored_objects = (top_level_parent,)
                                    else:
                                        ignored_objects = ()
                                    (result, blocking_obj_id) = target.check_line_of_sight(goal.location.transform, verbose=True, for_carryable=for_carryable, ignored_objects=ignored_objects)
                                    if result == routing.RAYCAST_HIT_TYPE_IMPASSABLE:
                                        invalid_goals.append(goal)
                                    elif result == routing.RAYCAST_HIT_TYPE_LOS_IMPASSABLE:
                                        invalid_los_goals.append(goal)
                                    else:
                                        goal.path_id = cur_path_id
                                        valid_goals.append(goal)
                                else:
                                    goal.path_id = cur_path_id
                                    valid_goals.append(goal)
                            if gsi_handlers.posture_graph_handlers.archiver.enabled and (invalid_goals or invalid_los_goals):
                                gsi_handlers.posture_graph_handlers.log_transition_handle(sim, connectivity_handle, connectivity_handle.polygons, target_path, 'LOS Failure', path_type)
                            if invalid_goals:
                                invalid_handle_dict[connectivity_handle] = (target_path, target_path.cost, var_map, dest_spec, invalid_goals, routing_constraint, final_constraint)
                            if invalid_los_goals:
                                invalid_los_dict[connectivity_handle] = (target_path, target_path.cost, var_map, dest_spec, invalid_los_goals, routing_constraint, final_constraint)
                            if not valid_goals:
                                pass
                            else:
                                if gsi_handlers.posture_graph_handlers.archiver.enabled:
                                    gsi_handlers.posture_graph_handlers.log_transition_handle(sim, connectivity_handle, connectivity_handle.polygons, target_path, True, path_type)
                                handle_dict[connectivity_handle] = (target_path, target_path.cost, var_map, dest_spec, valid_goals, routing_constraint, final_constraint)
                if gsi_handlers.posture_graph_handlers.archiver.enabled and (connectivity_handles or sub_constraint.geometry is not None):
                    gsi_handlers.posture_graph_handlers.log_transition_handle(sim, None, sub_constraint.geometry, target_path, True, path_type)
        return blocking_obj_id or None

    @staticmethod
    def copy_handles(sim, destination_handles, path, var_map):
        existing_data = destination_handles.get(DEFAULT)
        if existing_data is not None:
            existing_cost = existing_data[1]
            if path.cost >= existing_cost:
                return
        destination_spec = path.segmented_path.destination_specs.get(path[-1])
        destination_handles[DEFAULT] = (path, path.cost, var_map, destination_spec, [], Anywhere(), Anywhere())

    def _get_resolved_var_map(self, path, var_map):
        final_spec = path[-1]
        target = final_spec[BODY_INDEX][BODY_TARGET_INDEX]
        surface_target = final_spec[SURFACE_INDEX][SURFACE_TARGET_INDEX]
        updates = {}
        if target is not None:
            original_target = var_map.get(PostureSpecVariable.INTERACTION_TARGET)
            if original_target == PostureSpecVariable.BODY_TARGET_FILTERED:
                original_target = target
            if original_target.id == target.id:
                updates[PostureSpecVariable.INTERACTION_TARGET] = target
            original_carry_target = var_map.get(PostureSpecVariable.CARRY_TARGET)
            if original_carry_target.id == target.id:
                updates[PostureSpecVariable.CARRY_TARGET] = target
        if surface_target is not None:
            slot_manifest_entry = var_map.get(PostureSpecVariable.SLOT)
            if isinstance(slot_manifest_entry.target, PostureSpecVariable) or slot_manifest_entry.target.id == surface_target.id:
                slot_manifest_entry = SlotManifestEntry(slot_manifest_entry.actor, surface_target, slot_manifest_entry.slot)
                updates[PostureSpecVariable.SLOT] = slot_manifest_entry
        return frozendict(var_map, updates)

    def _generate_left_handles(self, sim, interaction, participant_type, left_path, var_map, destination_spec, final_constraint, unique_id, sim_position_routing_data):
        left_handles = {}
        invalid = {}
        invalid_los = {}
        blocking_obj_ids = []
        if not left_path[0][BODY_INDEX][BODY_POSTURE_TYPE_INDEX].use_containment_slot_for_exit:
            blocking_obj_id = self.append_handles(sim, left_handles, invalid, invalid_los, sim_position_routing_data, left_path, var_map, destination_spec, unique_id, final_constraint, path_type=PathType.LEFT)
            if blocking_obj_id is not None:
                blocking_obj_ids.append(blocking_obj_id)
        else:
            (exit_spec, _, _) = self.find_exit_posture_spec(sim, left_path, var_map)
            transition_posture_name = left_path[-1].body_posture.name
            if exit_spec == left_path[0] and sim.posture.is_puppet:
                with create_puppet_postures(sim):
                    (use_previous_position, routing_data) = self._get_locations_from_posture(sim, exit_spec, var_map, participant_type=participant_type, transition_posture_name=transition_posture_name)
            else:
                (use_previous_position, routing_data) = self._get_locations_from_posture(sim, exit_spec, var_map, mobile_posture_spec=left_path[-1], participant_type=participant_type, transition_posture_name=transition_posture_name, left_most_spec=left_path[0])
            if use_previous_position:
                routing_data = sim_position_routing_data
            blocking_obj_id = self.append_handles(sim, left_handles, invalid, invalid_los, routing_data, left_path, var_map, destination_spec, unique_id, final_constraint, entry=False, path_type=PathType.LEFT)
            if blocking_obj_id is not None:
                blocking_obj_ids.append(blocking_obj_id)
        return (left_handles, invalid, invalid_los, blocking_obj_ids)

    def _generate_right_handles(self, sim, interaction, participant_type, right_path, var_map, destination_spec, final_constraint, unique_id, animation_resolver_fn):
        right_handles = {}
        invalid = {}
        invalid_los = {}
        blocking_obj_ids = []
        first_spec = right_path[0]
        if not (first_spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile and (first_spec[BODY_INDEX][BODY_TARGET_INDEX] is None or first_spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].unconstrained)):
            (entry_spec, constrained_edge, _) = self.find_entry_posture_spec(sim, right_path, var_map)
            final_spec = right_path[-1]
            relevant_interaction = interaction if entry_spec is final_spec else None
            right_var_map = self._get_resolved_var_map(right_path, right_path.segmented_path.var_map)
            right_path.segmented_path.var_map_resolved = right_var_map
            transition_posture_name = first_spec.body_posture.name
            (use_previous_pos, routing_data) = self._get_locations_from_posture(sim, entry_spec, right_var_map, interaction=relevant_interaction, mobile_posture_spec=first_spec, participant_type=participant_type, constrained_edge=constrained_edge, animation_resolver_fn=animation_resolver_fn, final_constraint=final_constraint, transition_posture_name=transition_posture_name)
            if use_previous_pos:
                self.copy_handles(sim, right_handles, right_path, right_var_map)
            elif routing_data[0].valid:
                perform_los_check = interaction.should_perform_routing_los_check
                blocking_obj_id = self.append_handles(sim, right_handles, invalid, invalid_los, routing_data, right_path, right_var_map, destination_spec, unique_id, final_constraint, path_type=PathType.RIGHT, goal_height_limit=interaction.goal_height_limit, perform_los_check=perform_los_check)
                if blocking_obj_id is not None:
                    blocking_obj_ids.append(blocking_obj_id)
        elif first_spec.body_target is not None and first_spec.body_target.is_sim:
            right_var_map = self._get_resolved_var_map(right_path, right_path.segmented_path.var_map)
            right_path.segmented_path.var_map_resolved = right_var_map
            self.copy_handles(sim, right_handles, right_path, right_var_map)
        return (right_handles, invalid, invalid_los, blocking_obj_ids)

    def _generate_middle_handles(self, sim, interaction, participant_type, middle_path, var_map, destination_spec, final_constraint, unique_id, animation_resolver_fn):
        middle_handles = {}
        invalid = {}
        invalid_los = {}
        blocking_obj_ids = []
        (entry_spec, constrained_edge, carry_spec) = self.find_entry_posture_spec(sim, middle_path, var_map)
        carry_target = var_map[PostureSpecVariable.CARRY_TARGET]
        if constrained_edge is None:
            if carry_target is not None and carry_target.is_in_sim_inventory():
                self.copy_handles(sim, middle_handles, middle_path, var_map)
            else:
                raise PostureGraphMiddlePathError('\n                   Have a middle path to pick up an object that is not in the\n                   inventory and we cannot generate a constrained_edge:\n                    \n                   carry target: {}\n                   interaction: {}\n                   final constraint: {}\n                   dest spec: {}\n                   entry spec: {}\n                   sim location: {}\n                   carry target location: {}\n                   '.format(carry_target, interaction, final_constraint, destination_spec, entry_spec, sim.location, carry_target.location if carry_target else 'NO CARRY TARGET'))
        else:
            carry_transition_constraint = constrained_edge.get_constraint(sim, carry_spec, var_map)
            if carry_target.is_sim:
                _animation_resolver_fn = animation_resolver_fn

                def animation_resolver_fn(animation_participant, *args, **kwargs):
                    if animation_participant == AnimationParticipant.ACTOR:
                        return sim
                    if animation_participant == AnimationParticipant.CARRY_TARGET:
                        return carry_target
                    if animation_participant in (AnimationParticipant.SURFACE, AnimationParticipant.TARGET, PostureSpecVariable.INTERACTION_TARGET):
                        return carry_target.posture_state.body.target
                    return _animation_resolver_fn(animation_participant, *args, **kwargs)

            if carry_target is not None and carry_transition_constraint is not None:
                carry_transition_constraints = []
                for carry_transition_sub_constraint in carry_transition_constraint:
                    if carry_target.is_sim:
                        interaction.transition.add_on_target_location_changed_callback(carry_target)
                        if carry_transition_sub_constraint.posture_state_spec is not None:
                            carry_body_target = carry_transition_sub_constraint.posture_state_spec.body_target
                            if carry_body_target is not None:
                                body_aspect = PostureAspectBody((carry_spec.body.posture_type, carry_body_target))
                                carry_spec = carry_spec.clone(body=body_aspect)
                    target_posture_state = postures.posture_state.PostureState(sim, None, carry_spec, var_map, invalid_expected=True)
                    interaction.transition.add_relevant_object(target_posture_state.body_target)
                    carry_transition_sub_constraint = carry_transition_sub_constraint.apply_posture_state(target_posture_state, animation_resolver_fn)
                    carry_transition_constraints.append(carry_transition_sub_constraint)
                carry_transition_constraint = create_constraint_set(carry_transition_constraints)
            if carry_transition_constraint is not None:
                constraint_has_geometry = any(constraint.geometry is not None for constraint in carry_transition_constraint)
                if not constraint_has_geometry:
                    posture_graph_service = services.current_zone().posture_graph_service
                    posture_object = posture_graph_service.get_compatible_mobile_posture_target(sim)
                    if posture_object is not None:
                        edge_constraint = posture_object.get_edge_constraint(sim=sim)
                        carry_transition_constraint = carry_transition_constraint.intersect(edge_constraint)
                        constraint_has_geometry = True
                carry_spec_surface_spec = carry_spec[SURFACE_INDEX]
                if carry_spec_surface_spec is not None:
                    relative_object = carry_spec_surface_spec[SURFACE_TARGET_INDEX]
                else:
                    relative_object = None
                if relative_object is None:
                    relative_object = carry_spec[BODY_INDEX][BODY_TARGET_INDEX]
                if relative_object is None:
                    relative_object = entry_spec[CARRY_INDEX][CARRY_TARGET_INDEX]
                    if isinstance(relative_object, PostureSpecVariable):
                        relative_object = var_map.get(relative_object)
                if constraint_has_geometry:
                    carry_transition_constraint = carry_transition_constraint.generate_single_surface_constraints()
                    blocking_obj_id = self.append_handles(sim, middle_handles, invalid, invalid_los, (carry_transition_constraint, None, relative_object), middle_path, var_map, destination_spec, unique_id, final_constraint, path_type=PathType.MIDDLE_LEFT)
                    if blocking_obj_id is not None:
                        blocking_obj_ids.append(blocking_obj_id)
                else:
                    self.copy_handles(sim, middle_handles, middle_path, var_map)
        return (middle_handles, invalid, invalid_los, blocking_obj_ids)

    def _get_segmented_path_connectivity_handles(self, sim, segmented_path, interaction, participant_type, animation_resolver_fn, sim_position_routing_data):
        blocking_obj_ids = []
        searched = {PathType.RIGHT: set(), PathType.LEFT: set()}
        middle_handles = {}
        invalid_middles = {}
        invalid_los_middles = {}
        destination_handles = {}
        invalid_destinations = {}
        invalid_los_destinations = {}
        source_handles = {}
        invalid_sources = {}
        invalid_los_sources = {}
        for path_left in segmented_path.generate_left_paths():
            final_left_node = path_left[-1]
            if final_left_node in searched[PathType.LEFT]:
                pass
            else:
                (source_handles, invalid_sources, invalid_los_sources, blockers) = self._generate_left_handles(sim, interaction, participant_type, path_left, segmented_path.var_map, None, segmented_path.constraint, id(segmented_path), sim_position_routing_data)
                blocking_obj_ids += blockers
                if not source_handles:
                    pass
                else:
                    searched[PathType.LEFT].add(final_left_node)
                    for path_right in segmented_path.generate_right_paths(sim, path_left):
                        (entry_node, _, _) = self.find_entry_posture_spec(sim, path_right, segmented_path.var_map)
                        if entry_node is not None and entry_node.body_target in searched[PathType.RIGHT]:
                            pass
                        else:
                            final_right_node = path_right[-1]
                            destination_spec = segmented_path.destination_specs[final_right_node]
                            (destination_handles, invalid_destinations, invalid_los_destinations, blockers) = self._generate_right_handles(sim, interaction, participant_type, path_right, segmented_path.var_map, destination_spec, segmented_path.constraint, id(segmented_path), animation_resolver_fn)
                            blocking_obj_ids += blockers
                            if not destination_handles:
                                pass
                            else:
                                final_body_target = final_right_node.body_target
                                final_body_posture = final_right_node.body_posture
                                if final_body_target is not None and final_body_posture.is_vehicle and final_body_posture is not final_left_node.body_posture:
                                    posture = postures.create_posture(final_body_posture, sim, final_body_target, is_throwaway=True)
                                    slot_constraint = posture.slot_constraint_simple
                                    if slot_constraint is not None:
                                        geometry_constraint = segmented_path.constraint.generate_geometry_only_constraint()
                                        if not slot_constraint.intersect(geometry_constraint).valid:
                                            pass
                                        else:
                                            if entry_node is not None:
                                                searched[PathType.RIGHT].add(entry_node.body_target)
                                            for path_middle in segmented_path.generate_middle_paths(path_left, path_right):
                                                if path_middle is None:
                                                    return (source_handles, {}, destination_handles, invalid_sources, {}, invalid_destinations, invalid_los_sources, {}, invalid_los_destinations, blocking_obj_ids)
                                                (middle_handles, invalid_middles, invalid_los_middles, blockers) = self._generate_middle_handles(sim, interaction, participant_type, path_middle, segmented_path.var_map_resolved, destination_spec, segmented_path.constraint, id(segmented_path), animation_resolver_fn)
                                                blocking_obj_ids += blockers
                                                if middle_handles:
                                                    return (source_handles, middle_handles, destination_handles, invalid_sources, invalid_middles, invalid_destinations, invalid_los_sources, invalid_los_middles, invalid_los_destinations, blocking_obj_ids)
                                            if all(dest in searched[PathType.RIGHT] for dest in segmented_path.left_destinations) or len(searched[PathType.RIGHT]) >= MAX_RIGHT_PATHS:
                                                break
                                    else:
                                        if entry_node is not None:
                                            searched[PathType.RIGHT].add(entry_node.body_target)
                                        for path_middle in segmented_path.generate_middle_paths(path_left, path_right):
                                            if path_middle is None:
                                                return (source_handles, {}, destination_handles, invalid_sources, {}, invalid_destinations, invalid_los_sources, {}, invalid_los_destinations, blocking_obj_ids)
                                            (middle_handles, invalid_middles, invalid_los_middles, blockers) = self._generate_middle_handles(sim, interaction, participant_type, path_middle, segmented_path.var_map_resolved, destination_spec, segmented_path.constraint, id(segmented_path), animation_resolver_fn)
                                            blocking_obj_ids += blockers
                                            if middle_handles:
                                                return (source_handles, middle_handles, destination_handles, invalid_sources, invalid_middles, invalid_destinations, invalid_los_sources, invalid_los_middles, invalid_los_destinations, blocking_obj_ids)
                                        if all(dest in searched[PathType.RIGHT] for dest in segmented_path.left_destinations) or len(searched[PathType.RIGHT]) >= MAX_RIGHT_PATHS:
                                            break
                                else:
                                    if entry_node is not None:
                                        searched[PathType.RIGHT].add(entry_node.body_target)
                                    for path_middle in segmented_path.generate_middle_paths(path_left, path_right):
                                        if path_middle is None:
                                            return (source_handles, {}, destination_handles, invalid_sources, {}, invalid_destinations, invalid_los_sources, {}, invalid_los_destinations, blocking_obj_ids)
                                        (middle_handles, invalid_middles, invalid_los_middles, blockers) = self._generate_middle_handles(sim, interaction, participant_type, path_middle, segmented_path.var_map_resolved, destination_spec, segmented_path.constraint, id(segmented_path), animation_resolver_fn)
                                        blocking_obj_ids += blockers
                                        if middle_handles:
                                            return (source_handles, middle_handles, destination_handles, invalid_sources, invalid_middles, invalid_destinations, invalid_los_sources, invalid_los_middles, invalid_los_destinations, blocking_obj_ids)
                                    if all(dest in searched[PathType.RIGHT] for dest in segmented_path.left_destinations) or len(searched[PathType.RIGHT]) >= MAX_RIGHT_PATHS:
                                        break
        return (source_handles, {}, {}, invalid_sources, invalid_middles, invalid_destinations, invalid_los_sources, invalid_los_middles, invalid_los_destinations, blocking_obj_ids)

    def generate_connectivity_handles(self, sim, segmented_paths, interaction, participant_type, animation_resolver_fn):
        if len(segmented_paths) == 0:
            return NO_CONNECTIVITY
        source_destination_sets = collections.OrderedDict()
        source_middle_sets = collections.OrderedDict()
        middle_destination_sets = collections.OrderedDict()
        sim_position_routing_data = self.get_sim_position_routing_data(sim)
        best_complete_path = EMPTY_PATH_SPEC
        for segmented_path in segmented_paths:
            if not segmented_path.is_complete:
                pass
            else:
                for left_path in segmented_path.generate_left_paths():
                    for right_path in segmented_path.generate_right_paths(sim, left_path):
                        complete_path = left_path + right_path
                        if not self.is_valid_complete_path(sim, complete_path, interaction):
                            pass
                        else:
                            if best_complete_path.cost <= complete_path.cost:
                                break
                            final_node = complete_path[-1]
                            if best_complete_path is not EMPTY_PATH_SPEC and interaction.privacy is not None and len(complete_path) == 1:
                                complete_path.append(final_node)
                            destination_spec = segmented_path.destination_specs[final_node]
                            var_map = self._get_resolved_var_map(complete_path, segmented_path.var_map)
                            constraint = segmented_path.constraint
                            if len(complete_path) == 1:
                                transform_constraint = None
                                if not sim.posture.mobile:
                                    transform_constraint = sim.posture.slot_constraint
                                if transform_constraint is None:
                                    transform_constraint = interactions.constraints.Transform(sim.transform, routing_surface=sim.routing_surface)
                                final_constraint = constraint.intersect(transform_constraint)
                            else:
                                (_, routing_data) = self._get_locations_from_posture(sim, complete_path[-1], var_map, interaction=interaction, participant_type=participant_type, animation_resolver_fn=animation_resolver_fn, final_constraint=constraint)
                                final_constraint = routing_data[0]
                            if final_constraint is not None and not final_constraint.valid:
                                pass
                            else:
                                if final_constraint is None:
                                    final_constraint = constraint
                                best_complete_path = PathSpec(complete_path, complete_path.cost, var_map, destination_spec, final_constraint, constraint, allow_tentative=True)
                                self._generate_surface_and_slot_targets(best_complete_path, None, sim.routing_location, objects_to_ignore=DEFAULT)
                                break
                    if best_complete_path is not EMPTY_PATH_SPEC:
                        break
        blocking_obj_ids = []
        for segmented_path in segmented_paths:
            if segmented_path.is_complete:
                pass
            else:
                try:
                    handles = self._get_segmented_path_connectivity_handles(sim, segmented_path, interaction, participant_type, animation_resolver_fn, sim_position_routing_data)
                except PostureGraphError:
                    return NO_CONNECTIVITY
                (source_handles, middle_handles, destination_handles, invalid_sources, invalid_middles, invalid_destinations, invalid_los_sources, invalid_los_middles, invalid_los_destinations, blockers) = handles
                blocking_obj_ids += blockers
                if middle_handles:
                    value = (source_handles, middle_handles, {}, {}, invalid_middles, invalid_los_middles)
                    source_middle_sets[segmented_path] = value
                    value = [None, destination_handles, invalid_middles, invalid_los_middles, invalid_destinations, invalid_los_destinations]
                    middle_destination_sets[segmented_path] = value
                else:
                    if DEFAULT in destination_handles:
                        default_values = {source_handle.clone(): destination_handles[DEFAULT] for source_handle in source_handles}
                        for (dest_handle, (dest_path, _, _, _, _, _, _)) in default_values.items():
                            dest_handle.path = dest_path
                        del destination_handles[DEFAULT]
                        destination_handles.update(default_values)
                    value = (source_handles, destination_handles, {}, {}, invalid_destinations, invalid_los_destinations)
                    source_destination_sets[segmented_path] = value
        if not (best_complete_path is EMPTY_PATH_SPEC and (source_destination_sets or source_middle_sets and middle_destination_sets)):
            if blocking_obj_ids:
                set_transition_failure_reason(sim, TransitionFailureReasons.BLOCKING_OBJECT, target_id=blocking_obj_ids[0], transition_controller=interaction.transition)
            else:
                set_transition_failure_reason(sim, TransitionFailureReasons.NO_VALID_INTERSECTION, transition_controller=interaction.transition)
        return Connectivity(best_complete_path, source_destination_sets, source_middle_sets, middle_destination_sets)

    def find_best_path_pair(self, interaction, sim, connectivity, timeline):
        (best_complete_path, source_destination_sets, source_middle_sets, middle_destination_sets) = connectivity
        (success, best_non_complete_path) = yield from self._find_best_path_pair(interaction, sim, source_destination_sets, source_middle_sets, middle_destination_sets, timeline)
        if best_complete_path is EMPTY_PATH_SPEC and success == False:
            return (success, best_non_complete_path)
        best_non_complete_path = best_non_complete_path.get_carry_sim_merged_path_spec()
        best_non_complete_path = best_non_complete_path.get_stand_to_carry_sim_direct_path_spec()
        if best_complete_path is EMPTY_PATH_SPEC:
            return (success, best_non_complete_path)
        if best_non_complete_path is EMPTY_PATH_SPEC:
            return (True, best_complete_path)
        force_complete = False
        if interaction.is_putdown and sim in (interaction.target, interaction.carry_target):
            force_complete = True
        else:
            for node in best_complete_path.path:
                if node.body_target.is_sim:
                    for other_node in best_non_complete_path.path[1:]:
                        if node == other_node:
                            force_complete = True
                            break
                if node.body_target is not None and force_complete:
                    break
        if success and (force_complete or best_complete_path.cost <= best_non_complete_path.total_cost):
            best_non_complete_path.cleanup_path_spec(sim)
            return (True, best_complete_path)
        return (success, best_non_complete_path)

    def _find_best_path_pair(self, interaction, sim, source_destination_sets, source_middle_sets, middle_destination_sets, timeline):
        source_dest_success = False
        source_dest_path_spec = EMPTY_PATH_SPEC
        source_dest_cost = sims4.math.MAX_FLOAT
        middle_success = False
        middle_path_spec = EMPTY_PATH_SPEC
        middle_cost = sims4.math.MAX_FLOAT
        if source_destination_sets:
            (source_dest_success, source_dest_path_spec, _) = yield from self.get_best_path_between_handles(interaction, sim, source_destination_sets, timeline)
            source_dest_cost = source_dest_path_spec.total_cost
        if middle_destination_sets:
            (middle_success, middle_path_spec, selected_goal) = yield from self.get_best_path_between_handles(interaction, sim, source_middle_sets, timeline, path_type=PathType.MIDDLE_LEFT)
            if middle_path_spec.is_failure_path:
                if source_dest_success:
                    return (source_dest_success, source_dest_path_spec)
                return (middle_success, middle_path_spec)
            if middle_success:
                geometry = create_transform_geometry(selected_goal.location.transform)
                middle_handle = selected_goal.connectivity_handle.clone(routing_surface_override=selected_goal.routing_surface_id, geometry=geometry)
                middle_handle.path = middle_path = algos.Path(middle_path_spec.path[-1:])
                middle_path.segmented_path = selected_goal.connectivity_handle.path.segmented_path
                middle_handle.var_map = middle_path.segmented_path.var_map_resolved
                selected_goal.connectivity_handle = middle_handle
                middle_handle_set = {middle_handle: (middle_path, 0, middle_path_spec.var_map, None, [selected_goal], None, None)}
                for middle_dest_set in middle_destination_sets.values():
                    middle_dest_set[0] = middle_handle_set
                (middle_success, best_right_path_spec, _) = yield from self.get_best_path_between_handles(interaction, sim, middle_destination_sets, timeline, path_type=PathType.MIDDLE_RIGHT)
                if middle_success:
                    middle_path_spec = middle_path_spec.combine(best_right_path_spec)
                    middle_cost = middle_path_spec.total_cost
        if source_dest_success == middle_success:
            if source_dest_cost <= middle_cost:
                result_success = source_dest_success
                result_path_spec = source_dest_path_spec
            else:
                result_success = middle_success
                result_path_spec = middle_path_spec
        elif source_dest_success:
            result_success = source_dest_success
            result_path_spec = source_dest_path_spec
        else:
            result_success = middle_success
            result_path_spec = middle_path_spec
        return (result_success, result_path_spec)

    def _get_best_slot(self, slot_target, slot_types, obj, location, objects_to_ignore=DEFAULT):
        runtime_slots = tuple(slot_target.get_runtime_slots_gen(slot_types=slot_types))
        if not runtime_slots:
            return
        chosen_slot = None
        closest_distance = None
        for runtime_slot in runtime_slots:
            if runtime_slot.is_valid_for_placement(obj=obj, objects_to_ignore=objects_to_ignore):
                transform = runtime_slot.transform
                slot_routing_location = routing.Location(transform.translation, transform.orientation, runtime_slot.routing_surface)
                distance = (location - slot_routing_location.position).magnitude_2d_squared()
                if not closest_distance is None:
                    if distance < closest_distance:
                        chosen_slot = runtime_slot
                        closest_distance = distance
                chosen_slot = runtime_slot
                closest_distance = distance
        return chosen_slot

    def _generate_surface_and_slot_targets(self, path_spec_right, path_spec_left, final_sim_routing_location, objects_to_ignore):
        slot_var = path_spec_right.var_map.get(PostureSpecVariable.SLOT)
        if slot_var is None:
            return True
        slot_target = slot_var.target
        if isinstance(slot_target, PostureSpecVariable):
            return False
        chosen_slot = self._get_best_slot(slot_target, slot_var.slot_types, slot_var.actor, final_sim_routing_location.position, objects_to_ignore)
        if chosen_slot is None:
            return False
        path_spec_right._final_constraint = path_spec_right.final_constraint.generate_constraint_with_slot_info(slot_var.actor, slot_target, chosen_slot)
        path_spec_right._spec_constraint = path_spec_right.spec_constraint.generate_constraint_with_slot_info(slot_var.actor, slot_target, chosen_slot)

        def get_frozen_manifest_entry():
            for constraint in path_spec_right.spec_constraint:
                if constraint.posture_state_spec is not None:
                    for manifest_entry in constraint.posture_state_spec.slot_manifest:
                        return manifest_entry
            raise AssertionError('Spec constraint with no manifest entries: {}'.format(path_spec_right.spec_constraint))

        frozen_manifest_entry = get_frozen_manifest_entry()

        def replace_var_map_for_path_spec(path_spec):
            for spec in path_spec.transition_specs:
                if PostureSpecVariable.SLOT in spec.var_map:
                    new_var_map = {}
                    new_var_map[PostureSpecVariable.SLOT] = frozen_manifest_entry
                    spec.var_map = frozendict(spec.var_map, new_var_map)

        replace_var_map_for_path_spec(path_spec_right)
        if path_spec_left is not None:
            replace_var_map_for_path_spec(path_spec_left)
        return True

    def _valid_vehicle_dest_handle(self, dest, cost, in_vehicle_posture):
        if not sims4.math.almost_equal(cost, 0.0):
            return False
        if len(dest.path) < 1:
            return in_vehicle_posture
        next_posture = dest.path[0].body_posture
        if next_posture is None:
            return in_vehicle_posture
        if not in_vehicle_posture:
            return next_posture.is_vehicle
        return next_posture.is_vehicle or not next_posture.mobile

    def get_best_path_between_handles(self, interaction, sim, source_destination_sets, timeline, path_type=None):
        non_suppressed_source_goals = []
        non_suppressed_goals = []
        suppressed_source_goals = []
        suppressed_goals = []
        for_carryable = interaction.carry_target is not None
        carry_object_at_pool = False
        if interaction.carry_target.routing_surface.type == routing.SurfaceType.SURFACETYPE_POOL:
            carry_object_at_pool = True
        sim_surface_type = sim.location.routing_surface.type if for_carryable and interaction.carry_target.routing_surface is not None and sim.location.routing_surface is not None else None
        target_reference_override = None
        interaction_goal_height_limit = interaction.goal_height_limit
        if sim.routing_master.get_routing_slave_data_count(FormationRoutingType.FOLLOW):
            target_reference_override = sim.routing_master
            interaction_goal_height_limit = FormationTuning.GOAL_HEIGHT_LIMIT
        for (source_handles, _, _, _, _, _) in source_destination_sets.values():
            for source_handle in source_handles:
                if source_handle is DEFAULT:
                    raise AssertionError
                path_cost = source_handles[source_handle][1]
                source_goals = source_handle.get_goals(relative_object=source_handle.target, for_carryable=for_carryable, for_source=True)
                same_interaction_source_target = True
                if interaction.target.id != source_handle.target.id:
                    same_interaction_source_target = False
                for source_goal in source_goals:
                    source_is_valid = True
                    if path_type != PathType.MIDDLE_RIGHT and (same_interaction_source_target and (sim_surface_type is not None and (sim_surface_type != routing.SurfaceType.SURFACETYPE_POOL and source_goal.routing_surface_id.type != routing.SurfaceType.SURFACETYPE_POOL))) and sim_surface_type != source_goal.routing_surface_id.type:
                        pass
                    else:
                        if not source_handle.target.is_sim:
                            if routing.test_point_placement_in_navmesh(source_goal.location.routing_surface, source_goal.location.transform.translation):
                                (result, _) = source_handle.target.check_line_of_sight(source_goal.location.transform, verbose=True, for_carryable=for_carryable)
                                if result != routing.RAYCAST_HIT_TYPE_NONE:
                                    source_is_valid = False
                            else:
                                source_is_valid = False
                        source_goal.path_cost = path_cost
                        if source_goal.requires_los_check and source_handle.target is not None and source_is_valid:
                            non_suppressed_source_goals.append(source_goal)
                        else:
                            suppressed_source_goals.append(source_goal)
        routing_context = sim.routing_context
        routing_agent = sim
        current_posture_target = sim.posture.target
        in_vehicle = False if sim.routing_master is not None and current_posture_target is None else current_posture_target.vehicle_component is not None
        in_vehicle_posture = sim.posture.is_vehicle
        force_vehicle_route = False
        vehicle_dest_handles = []
        vehicle = None if not in_vehicle else current_posture_target
        if vehicle.vehicle_component is not None:
            vehicle_pathplan_context = vehicle.routing_component.pathplan_context
            connectivity = None
            vehicle_source_goals = non_suppressed_source_goals
            source_goal = non_suppressed_source_goals[0] if non_suppressed_source_goals else None
            if source_goal is None:
                vehicle_source_goals = suppressed_source_goals
                source_goal = suppressed_source_goals[0] if suppressed_source_goals else None
            if source_goal is not None:
                dest_handles = []
                for (_, destination_handles, _, _, _, _) in source_destination_sets.values():
                    dest_handles.extend([dest_handle for dest_handle in destination_handles.keys() if dest_handle is not DEFAULT])
                if dest_handles:
                    connectivity = routing.test_connectivity_batch((source_goal.connectivity_handle,), dest_handles, routing_context=vehicle_pathplan_context, compute_cost=True)
            if connectivity is not None:
                vehicle_dest_handles = {dest for (_, dest, cost) in connectivity if self._valid_vehicle_dest_handle(dest, cost, in_vehicle_posture)}
                if vehicle_dest_handles:
                    force_vehicle_route = True
                    routing_agent = vehicle
                    routing_context = vehicle_pathplan_context
                    for goal in vehicle_source_goals:
                        goal.connectivity_handle = goal.connectivity_handle.clone(sim=vehicle)
        middle_path_pickup = vehicle is not None and path_type is not None and path_type == PathType.MIDDLE_LEFT
        for (_, destination_handles, _, _, _, _) in source_destination_sets.values():
            for (destination_handle, (right_path, path_cost, var_map, dest_spec, _, _, _)) in destination_handles.items():
                additional_dest_handles = []
                if destination_handle is DEFAULT:
                    for (source_handles, *_) in source_destination_sets.values():
                        for source_handle in source_handles:
                            destination_handle = source_handle.clone()
                            destination_handle.path = right_path
                            additional_dest_handles.append(destination_handle)
                elif force_vehicle_route:
                    if destination_handle in vehicle_dest_handles:
                        destination_handle = destination_handle.clone(sim=routing_agent)
                        additional_dest_handles = [destination_handle]
                else:
                    additional_dest_handles = [destination_handle]
                for dest_handle in additional_dest_handles:
                    height_limit = interaction_goal_height_limit
                    if interaction.carry_target is dest_handle.target:
                        height_limit = None
                    dest_goals = dest_handle.get_goals(relative_object=dest_handle.target, for_carryable=for_carryable, goal_height_limit=height_limit, target_reference_override=target_reference_override)
                    slope_restricted = target_reference_override is None and dest_handle.target is not None and dest_handle.constraint.restricted_on_slope
                    for dest_goal in dest_goals:
                        if middle_path_pickup and carry_object_at_pool and dest_goal.routing_surface_id.type != routing.SurfaceType.SURFACETYPE_POOL:
                            pass
                        else:
                            dest_is_valid = True
                            dest_goal.path_cost = path_cost
                            if slope_restricted and dest_goal.routing_surface_id.type == routing.SurfaceType.SURFACETYPE_WORLD and dest_goal.position.y != routing_constants.INVALID_TERRAIN_HEIGHT:
                                positional_target = dest_handle.target.get_parenting_root()
                                target_position = positional_target.part_owner.position if positional_target.is_part else positional_target.position
                                height_difference = abs(target_position.y - dest_goal.position.y)
                                if height_difference > PostureTuning.CONSTRAINT_HEIGHT_TOLERANCE:
                                    set_transition_failure_reason(sim, TransitionFailureReasons.GOAL_ON_SLOPE)
                                    dest_is_valid = False
                                else:
                                    if not (in_vehicle and current_posture_target is dest_handle.target):
                                        if dest_handle.target is not None and dest_handle.target.parent is not None and not dest_handle.target.parent.is_sim:
                                            ignored_objects = (dest_handle.target.parent,)
                                        else:
                                            ignored_objects = ()
                                        if dest_handle.target.children:
                                            ignored_objects += tuple(dest_handle.target.children)
                                        (result, blocking_obj_id) = dest_handle.target.check_line_of_sight(dest_goal.location.transform, verbose=True, for_carryable=for_carryable, ignored_objects=ignored_objects)
                                        if dest_handle.target is not None and result == routing.RAYCAST_HIT_TYPE_IMPASSABLE and blocking_obj_id == 0:
                                            pass
                                        elif result != routing.RAYCAST_HIT_TYPE_NONE:
                                            set_transition_failure_reason(sim, TransitionFailureReasons.BLOCKING_OBJECT, target_id=blocking_obj_id)
                                            dest_is_valid = False
                                    if dest_goal.requires_los_check and dest_handle.target is not None and (dest_handle.target.is_sim or dest_is_valid):
                                        non_suppressed_goals.append(dest_goal)
                                    else:
                                        suppressed_goals.append(dest_goal)
                            else:
                                if not (in_vehicle and current_posture_target is dest_handle.target):
                                    if dest_handle.target is not None and dest_handle.target.parent is not None and not dest_handle.target.parent.is_sim:
                                        ignored_objects = (dest_handle.target.parent,)
                                    else:
                                        ignored_objects = ()
                                    if dest_handle.target.children:
                                        ignored_objects += tuple(dest_handle.target.children)
                                    (result, blocking_obj_id) = dest_handle.target.check_line_of_sight(dest_goal.location.transform, verbose=True, for_carryable=for_carryable, ignored_objects=ignored_objects)
                                    if dest_handle.target is not None and result == routing.RAYCAST_HIT_TYPE_IMPASSABLE and blocking_obj_id == 0:
                                        pass
                                    elif result != routing.RAYCAST_HIT_TYPE_NONE:
                                        set_transition_failure_reason(sim, TransitionFailureReasons.BLOCKING_OBJECT, target_id=blocking_obj_id)
                                        dest_is_valid = False
                                if dest_goal.requires_los_check and dest_handle.target is not None and (dest_handle.target.is_sim or dest_is_valid):
                                    non_suppressed_goals.append(dest_goal)
                                else:
                                    suppressed_goals.append(dest_goal)
        if not non_suppressed_source_goals:
            non_suppressed_source_goals = suppressed_source_goals
        all_source_goals = non_suppressed_source_goals
        all_dest_goals = non_suppressed_goals or suppressed_goals
        if not (all_source_goals and all_dest_goals):
            failure_path = yield from self._get_failure_path_spec_gen(timeline, sim, source_destination_sets, interaction=interaction, failed_path_type=path_type)
            return (False, failure_path, None)
        for goal in itertools.chain(all_source_goals, all_dest_goals):
            goal.cost += goal.path_cost
        if gsi_handlers.posture_graph_handlers.archiver.enabled:
            for source_goal in all_source_goals:
                gsi_handlers.posture_graph_handlers.log_possible_goal(sim, source_goal.connectivity_handle.path, source_goal, source_goal.cost, 'Source', id(source_destination_sets))
            for dest_goal in all_dest_goals:
                gsi_handlers.posture_graph_handlers.log_possible_goal(sim, dest_goal.connectivity_handle.path, dest_goal, dest_goal.cost, 'Dest', id(source_destination_sets))
        self.normalize_goal_costs(all_source_goals)
        self.normalize_goal_costs(all_dest_goals)
        route = routing.Route(all_source_goals[0].location, all_dest_goals, additional_origins=all_source_goals, routing_context=routing_context)
        is_failure_path = all_dest_goals is suppressed_goals
        plan_primitive = interactions.utils.routing.PlanRoute(route, routing_agent, is_failure_route=is_failure_path, interaction=interaction)
        result = yield from element_utils.run_child(timeline, elements.MustRunElement(plan_primitive))
        if not result:
            raise RuntimeError('Unknown error when trying to run PlanRoute.run()')
        if is_failure_path and plan_primitive.path.nodes and plan_primitive.path.nodes.plan_failure_object_id:
            failure_obj_id = plan_primitive.path.nodes.plan_failure_object_id
            set_transition_failure_reason(sim, TransitionFailureReasons.BLOCKING_OBJECT, target_id=failure_obj_id)
        if not ((is_failure_path or plan_primitive.path.nodes.plan_success) and plan_primitive.path.nodes):
            failure_path = yield from self._get_failure_path_spec_gen(timeline, sim, source_destination_sets, failed_path_type=path_type)
            return (False, failure_path, None)
        origin = plan_primitive.path.selected_start
        origin_path = origin.connectivity_handle.path
        dest = plan_primitive.path.selected_goal
        dest.location = plan_primitive.path.final_location
        dest_path = dest.connectivity_handle.path
        set_transition_destinations(sim, all_source_goals, all_dest_goals, origin, dest, preserve=True, draw_both_sets=True)
        destination_spec = origin_path.segmented_path.destination_specs.get(dest_path[-1])
        left_path_spec = PathSpec(origin_path, origin.path_cost, origin.connectivity_handle.var_map, None, origin.connectivity_handle.constraint, origin_path.segmented_path.constraint, is_failure_path=is_failure_path)
        o_locked_params = origin.slot_params if origin.has_slot_params else frozendict()
        left_path_spec.attach_route_and_params(None, o_locked_params, None, reverse=True)
        selected_dest_transform = sims4.math.Transform(sims4.math.Vector3(*dest.location.position), sims4.math.Quaternion(*dest.location.orientation))
        if isinstance(dest, SlotGoal) and not dest_path[-1][BODY_INDEX][BODY_POSTURE_TYPE_INDEX].mobile:
            selected_dest_containment_transform = dest.containment_transform
        else:
            selected_dest_containment_transform = selected_dest_transform
        selected_dest_constraint = interactions.constraints.Transform(selected_dest_containment_transform, routing_surface=dest.routing_surface_id)
        constraint = dest.connectivity_handle.constraint
        d_route_constraint = constraint.apply(selected_dest_constraint)
        if d_route_constraint.multi_surface:
            d_route_constraint = d_route_constraint.get_single_surface_version(dest.routing_surface_id)
        if not d_route_constraint.valid:
            d_route_constraint = constraint
        right_path_spec = PathSpec(dest_path, dest.path_cost, dest_path.segmented_path.var_map_resolved, destination_spec, d_route_constraint, dest_path.segmented_path.constraint, is_failure_path=is_failure_path)
        if dest_path.segmented_path.constraint is not None:
            if interaction.carry_target is not None:
                objects_to_ignore = (interaction.carry_target,)
            else:
                objects_to_ignore = DEFAULT
            if not self._generate_surface_and_slot_targets(right_path_spec, left_path_spec, dest.location, objects_to_ignore):
                return (False, EMPTY_PATH_SPEC, None)
        d_locked_params = dest.slot_params if dest.has_slot_params else frozendict()
        cur_path = plan_primitive.path
        while cur_path.next_path is not None:
            portal_obj = cur_path.portal_obj
            portal_id = cur_path.portal_id
            if not left_path_spec.create_route_nodes(cur_path, portal_obj=portal_obj, portal_id=portal_id):
                failure_path = yield from self._get_failure_path_spec_gen(timeline, sim, source_destination_sets)
                return (False, failure_path, None)
            portal_obj.set_portal_cost_override(portal_id, routing.PORTAL_PLAN_LOCK, sim=sim)
            cur_path = cur_path.next_path
            dest = cur_path.selected_goal
            dest.location = cur_path.final_location
            cur_path.add_destination_to_quad_tree()
        if left_path_spec._path[-1].posture_spec != right_path_spec._path[0].posture_spec:
            right_first_spec = TransitionSpec(right_path_spec, left_path_spec._path[-1].posture_spec, right_path_spec._path[0].var_map, portal_obj=right_path_spec._path[0].portal_obj, portal_id=right_path_spec._path[0].portal_id)
            if right_first_spec.portal_obj is not None:
                right_path_spec._path.insert(0, right_first_spec)
            else:
                right_path_spec._path[0] = right_first_spec
            right_first_spec.set_path(cur_path, d_route_constraint)
            right_first_spec.set_locked_params(d_locked_params)
        else:
            right_path_spec.attach_route_and_params(cur_path, d_locked_params, d_route_constraint)
        path_spec = left_path_spec.combine(right_path_spec)
        return (True, path_spec, dest)

    def normalize_goal_costs(self, all_goals):
        min_cost = sims4.math.MAX_UINT16
        for goal in all_goals:
            if goal.cost < min_cost:
                min_cost = goal.cost
        if min_cost == 0:
            return
        for goal in all_goals:
            goal.cost -= min_cost

    def _get_failure_path_spec_gen(self, timeline, sim, source_destination_sets, interaction=None, failed_path_type=None):
        all_sources = {}
        all_destinations = {}
        all_invalid_sources = {}
        all_invalid_los_sources = {}
        all_invalid_destinations = {}
        all_invalid_los_destinations = {}
        for (source_handles, destination_handles, invalid_sources, invalid_los_sources, invalid_destinations, invalid_los_destinations) in source_destination_sets.values():
            all_sources.update(source_handles)
            all_destinations.update(destination_handles)
            all_invalid_sources.update(invalid_sources)
            all_invalid_los_sources.update(invalid_los_sources)
            all_invalid_destinations.update(invalid_destinations)
            all_invalid_los_destinations.update(invalid_los_destinations)
        set_transition_failure_reason(sim, TransitionFailureReasons.PATH_PLAN_FAILED)
        failure_sources = all_sources or (all_invalid_sources or all_invalid_los_sources)
        if not failure_sources:
            return EMPTY_PATH_SPEC
        best_left_data = None
        best_left_cost = sims4.math.MAX_UINT32
        for (source_handle, (_, path_cost, _, _, _, _, _)) in failure_sources.items():
            if path_cost < best_left_cost:
                best_left_cost = path_cost
                best_left_data = failure_sources[source_handle]
                best_left_goal = best_left_data[4][0]
        fail_left_path_spec = PathSpec(best_left_data[0], best_left_data[1], best_left_data[2], best_left_data[3], best_left_data[5], best_left_data[6], is_failure_path=True, failed_path_type=failed_path_type)
        if best_left_goal is not None and best_left_goal.has_slot_params and best_left_goal.slot_params:
            fail_left_path_spec.attach_route_and_params(None, best_left_goal.slot_params, None, reverse=True)
        failure_destinations = all_destinations or (all_invalid_destinations or all_invalid_los_destinations)
        if not failure_destinations:
            return EMPTY_PATH_SPEC
        all_destination_goals = []
        for (_, _, _, _, dest_goals, _, _) in failure_destinations.values():
            all_destination_goals.extend(dest_goals)
        if all_destination_goals:
            route = routing.Route(best_left_goal.location, all_destination_goals, routing_context=sim.routing_context)
            plan_element = interactions.utils.routing.PlanRoute(route, sim, interaction=interaction)
            result = yield from element_utils.run_child(timeline, plan_element)
            if not result:
                raise RuntimeError('Failed to generate a failure path.')
            if plan_element.path.nodes:
                if len(plan_element.path.nodes) > 1:
                    first_node = plan_element.path.nodes[0]
                    (min_water_depth, max_water_depth) = OceanTuning.make_depth_bounds_safe_for_surface_and_sim(first_node.routing_surface_id, sim)
                    for node in list(plan_element.path.nodes)[1:]:
                        depth = terrain.get_water_depth(node.position[0], node.position[2], node.routing_surface_id.secondary_id)
                        if min_water_depth is not None and depth < min_water_depth:
                            return EMPTY_PATH_SPEC
                        if max_water_depth is not None and max_water_depth < depth:
                            return EMPTY_PATH_SPEC
                fail_left_path_spec.create_route_nodes(plan_element.path)
                destinations = {goal.connectivity_handle.path[-1] for goal in all_destination_goals}
                if len(destinations) > 1:
                    logger.warn('Too many destinations: {}', destinations, trigger_breakpoint=True)
                fail_left_path_spec.destination_spec = next(iter(destinations))
                return fail_left_path_spec
        return EMPTY_PATH_SPEC

    def handle_teleporting_path(self, segmented_paths):
        best_left_path = None
        best_cost = None
        for segmented_path in segmented_paths:
            for left_path in segmented_path.generate_left_paths():
                cost = left_path.cost
                if best_left_path is None or cost < best_cost:
                    best_left_path = left_path
                    best_cost = cost
                    if left_path[-1] in segmented_path.destination_specs:
                        dest_spec = segmented_path.destination_specs[left_path[-1]]
                    else:
                        dest_spec = left_path[-1]
                    var_map = segmented_path.var_map_resolved
                else:
                    break
        if best_left_path is None:
            raise ValueError('No left paths found for teleporting path.')
        return PathSpec(best_left_path, best_left_path.cost, var_map, dest_spec, None, None, path_as_posture_specs=True)

    def update_sim_node_caches(self, sim):
        if sim in self._graph.cached_sim_nodes:
            del self._graph.cached_sim_nodes[sim]
        zone = services.current_zone()
        if zone is None:
            return
        active_household = services.active_household()
        if active_household is None:
            return
        if zone.is_zone_shutting_down:
            self._graph.proxy_sim = None
            return
        from_init = self._graph.proxy_sim is None
        if from_init or self._graph.proxy_sim.sim_proxied is sim:
            for instanced_sim in active_household.instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS):
                if instanced_sim.sim_info.is_young_adult_or_older and instanced_sim is not sim:
                    self.update_generic_sim_carry_node(instanced_sim, from_init=from_init)
                    return
            sim_info_manager = services.sim_info_manager()
            for instanced_sim in sim_info_manager.instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS):
                if instanced_sim.sim_info.is_young_adult_or_older and instanced_sim is not sim:
                    self.update_generic_sim_carry_node(instanced_sim, from_init=from_init)
                    return
            self._graph.proxy_sim = None

    def _find_first_constrained_edge(self, sim, path, var_map, reverse=False):
        if not path:
            return (None, None, None)
        if reverse:
            sequence = reversed(path)
        else:
            sequence = path
        for posture_spec in sequence:
            if not posture_spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].unconstrained:
                return (posture_spec, None, None)
        if len(path) > 1:
            sequence = zip(path, path[1:])
            if reverse:
                sequence = reversed(list(sequence))
            for (spec_a, spec_b) in sequence:
                edge_info = self.get_edge(spec_a, spec_b)
                if edge_info is not None:
                    for op in edge_info.operations:
                        constraint = op.get_constraint(sim, spec_a, var_map)
                        if constraint is not None and constraint is not ANYWHERE:
                            return (posture_spec, op, spec_a)
        return (posture_spec, None, None)

    def find_entry_posture_spec(self, sim, path, var_map):
        return self._find_first_constrained_edge(sim, path, var_map)

    def find_exit_posture_spec(self, sim, path, var_map):
        return self._find_first_constrained_edge(sim, path, var_map, reverse=True)

    def _get_locations_from_posture(self, sim, posture_spec, var_map, interaction=None, participant_type=None, constrained_edge=None, mobile_posture_spec=None, animation_resolver_fn=None, final_constraint=None, transition_posture_name='stand', left_most_spec=None):
        body_target = posture_spec[BODY_INDEX][BODY_TARGET_INDEX]
        body_posture_type = posture_spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]
        body_unconstrained = body_posture_type.unconstrained
        should_add_vehicle_slot_constraint = mobile_posture_spec is None or posture_spec != mobile_posture_spec
        should_add_vehicle_slot_constraint |= left_most_spec is not None and left_most_spec != posture_spec
        if interaction is not None and interaction.transition is not None:
            interaction.transition.add_relevant_object(body_target)
            interaction.transition.add_relevant_object(interaction.target)
        body_posture = postures.create_posture(body_posture_type, sim, body_target, is_throwaway=True)
        if body_posture.unconstrained or body_posture.is_vehicle and should_add_vehicle_slot_constraint:
            constraint_intersection = body_posture.slot_constraint
            if constraint_intersection is None:
                return (True, (None, None, body_target))
            if not isinstance(final_constraint, RequiredSlotSingle):
                constraint_geometry_only = final_constraint.generate_geometry_only_constraint()
                constraint_intersection = constraint_intersection.intersect(constraint_geometry_only)
        else:
            if interaction is None:
                return (True, (None, None, body_target))
            target_posture_state = postures.posture_state.PostureState(sim, None, posture_spec, var_map, invalid_expected=True, body_state_spec_only=True, is_throwaway=True)
            if any(constraint.posture_state_spec.is_filtered_target() for constraint in final_constraint if constraint.posture_state_spec is not None):
                base_object = body_target
            else:
                base_object = None
            target = interaction.target
            with interaction.override_var_map(sim, var_map):
                interaction_constraint = interaction.apply_posture_state_and_interaction_to_constraint(target_posture_state, final_constraint, sim=sim, target=base_object or target, participant_type=participant_type, base_object=base_object)
                target_posture_state.add_constraint(self, interaction_constraint)
            constraint_intersection = target_posture_state.constraint_intersection
        if constraint_intersection.valid:
            edge_constraint = constrained_edge.get_constraint(sim, posture_spec, var_map)
            edge_constraint_resolved = edge_constraint.apply_posture_state(target_posture_state, animation_resolver_fn)
            edge_constraint_resolved_geometry_only = edge_constraint_resolved.generate_geometry_only_constraint()
            constraint_intersection = constraint_intersection.intersect(edge_constraint_resolved_geometry_only)
        if not (body_unconstrained and (animation_resolver_fn is not None and constrained_edge is not None) and constraint_intersection.valid):
            return (False, (constraint_intersection.generate_single_surface_constraints(), None, body_target))
        for constraint in constraint_intersection:
            if constraint.geometry is not None:
                break
        return (True, (None, None, body_target))
        constraint_intersection = constraint_intersection.generate_single_surface_constraints()
        locked_params = frozendict()
        if body_target is not None:
            target_name = posture_spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX].get_target_name(sim=sim, target=body_target)
            if target_name is not None:
                anim_overrides = body_target.get_anim_overrides(target_name)
                if anim_overrides is not None:
                    locked_params += anim_overrides.params
        routing_target = None
        if body_target is not None:
            routing_target = body_target
        elif interaction.target is not None:
            if posture_spec.requires_carry_target_in_hand or not posture_spec.requires_carry_target_in_slot:
                routing_target = interaction.target
            elif interaction.target.parent is not sim:
                routing_target = interaction.target
        if interaction is not None and interaction.transition is not None:
            interaction.transition.add_relevant_object(routing_target)
        locked_params += sim.get_sim_locked_params()
        locked_params += body_posture.get_slot_offset_locked_params()
        posture_locked_params = locked_params + {'transitionPosture': transition_posture_name}
        return (False, (constraint_intersection, posture_locked_params, routing_target))

    def get_compatible_mobile_posture_target(self, sim):
        posture_object = None
        compatible_postures_and_targets = self.get_compatible_mobile_postures_and_targets(sim)
        if compatible_postures_and_targets:
            posture_type = sim.posture_state.body.posture_type
            for (target, compatible_postures) in compatible_postures_and_targets.items():
                if not posture_type.is_vehicle:
                    if posture_type in compatible_postures:
                        posture_object = target
                        break
                posture_object = target
                break
            (posture_object, _) = next(iter(compatible_postures_and_targets.items()))
        return posture_object

    def get_compatible_mobile_postures_and_targets(self, sim):
        mobile_postures = {}
        found_objects = self._query_quadtree_for_mobile_posture_objects(sim, test_footprint=True)
        for found_obj in found_objects:
            mobile_posture_types = found_obj.provided_mobile_posture_types
            if found_obj.has_posture_portals():
                (posture_entry, _) = found_obj.get_nearest_posture_change(sim)
                if posture_entry is not None and posture_entry.body.posture_type in mobile_posture_types:
                    mobile_postures[found_obj] = (posture_entry.body.posture_type,)
                    mobile_postures[found_obj] = mobile_posture_types
            else:
                mobile_postures[found_obj] = mobile_posture_types
        return mobile_postures

    def _query_quadtree_for_mobile_posture_objects(self, sim, test_footprint=False):
        if self._mobile_posture_objects_quadtree is None:
            return []
        pathplan_context = sim.get_routing_context()
        quadtree_polygon = pathplan_context.get_quadtree_polygon()
        if not isinstance(quadtree_polygon, QtCircle):
            (lower_bound, upper_bound) = quadtree_polygon.bounds()
            quadtree_polygon = sims4.geometry.QtRect(sims4.math.Vector2(lower_bound.x, lower_bound.z), sims4.math.Vector2(upper_bound.x, upper_bound.z))
        query = sims4.geometry.SpatialQuery(quadtree_polygon, [self._mobile_posture_objects_quadtree])
        found_objs = query.run()
        found_objs = [posture_obj for posture_obj in found_objs if posture_obj.level == sim.level]
        special_obj = None
        if sim.in_pool:
            special_obj = pool_utils.get_pool_by_block_id(sim.block_id)
        elif sim.routing_surface.type == SurfaceType.SURFACETYPE_POOL:
            special_obj = services.terrain_service.ocean_object()
        if not test_footprint:
            if special_obj is not None:
                found_objs.append(special_obj)
            return found_objs
        mobile_posture_objects = []
        sim_pos = sim.position
        for mobile_obj in found_objs:
            polygon = mobile_obj.get_polygon_from_footprint_name_hashes(PLACEMENT_FOOTPRINT_HASH_SET)
            if not polygon is None:
                if not test_point_in_compound_polygon(sim_pos, polygon):
                    pass
                else:
                    mobile_posture_objects.append(mobile_obj)
        if special_obj is not None:
            mobile_posture_objects.append(special_obj)
        return mobile_posture_objects

    def add_object_to_mobile_posture_quadtree(self, obj):
        if not is_object_mobile_posture_compatible(obj):
            return
        location = sims4.math.Vector2(obj.position.x, obj.position.z)
        if obj.is_in_inventory() and location == TunableVector2.DEFAULT_ZERO:
            return
        if self._mobile_posture_objects_quadtree is None:
            self._mobile_posture_objects_quadtree = sims4.geometry.QuadTree()
        polygon = obj.get_polygon_from_footprint_name_hashes(PLACEMENT_FOOTPRINT_HASH_SET)
        if polygon is None:
            return
        (lower_bound, upper_bound) = polygon.bounds()
        bounding_box = sims4.geometry.QtRect(sims4.math.Vector2(lower_bound.x, lower_bound.z), sims4.math.Vector2(upper_bound.x, upper_bound.z))
        self._mobile_posture_objects_quadtree.insert(obj, bounding_box)

    def remove_object_from_mobile_posture_quadtree(self, obj):
        if self._mobile_posture_objects_quadtree is None:
            return
        self._mobile_posture_objects_quadtree.remove(obj)

    def _query_mobile_posture_objects_for_reset(self, posture_obj=None, test_footprint=False):
        sims = set()
        for sim in services.sim_info_manager().instanced_sims_gen():
            if not sim.is_on_active_lot():
                pass
            else:
                found_objs = tuple(self._query_quadtree_for_mobile_posture_objects(sim, test_footprint=test_footprint))
                if posture_obj is not None and posture_obj not in found_objs:
                    pass
                elif found_objs:
                    sims.add(sim)
        return sims

    def mobile_posture_object_location_changed(self, obj, *_, **__):
        zone = services.current_zone()
        if zone.is_zone_loading:
            return
        before_sims = self._query_mobile_posture_objects_for_reset(obj)
        self.remove_object_from_mobile_posture_quadtree(obj)
        self.add_object_to_mobile_posture_quadtree(obj)
        after_sims = self._query_mobile_posture_objects_for_reset(obj, test_footprint=True)
        affected_sims = before_sims.difference(after_sims) | after_sims
        services.get_reset_and_delete_service().trigger_batch_reset(tuple(sim for sim in affected_sims), ResetReason.RESET_EXPECTED, obj, 'Mobile posture object moved.')

    def _can_transition_between_nodes(self, source_spec, destination_spec):
        if self.get_edge(source_spec, destination_spec, return_none_on_failure=True) is None:
            return False
        return True

    def get_edge(self, spec_a, spec_b, return_none_on_failure=False):
        try:
            (edge_info, _) = self._get_edge_info(spec_a, spec_b)
            if edge_info is None:
                if spec_a[BODY_INDEX][BODY_POSTURE_TYPE_INDEX] != spec_b[BODY_INDEX][BODY_POSTURE_TYPE_INDEX] or spec_a[CARRY_INDEX] != spec_b[CARRY_INDEX]:
                    if not return_none_on_failure:
                        raise KeyError('Edge not found in posture graph: [{:s}] -> [{:s}]'.format(spec_a, spec_b))
                    return
                else:
                    return EdgeInfo((), None, 0)
            return edge_info
        except:
            pass

    def print_summary(self, _print=logger.always):
        num_nodes = len(self._graph)
        num_edges = len(self._edge_info)
        object_totals = collections.defaultdict(collections.Counter)
        for (node, node_data) in self._graph.items():
            objects = {o for o in (node.body_target, node.surface_target) if o is not None}
            if objects:
                for obj in objects:
                    object_totals[obj.definition]['nodes'] += 1
                    object_totals[obj.definition]['edges'] += len(node_data.successors)
            else:
                object_totals['Untargeted']['nodes'] += 1
                object_totals['Untargeted']['edges'] += len(node_data.successors)
        unique_objects = collections.defaultdict(set)
        for node in self._graph:
            objects = {o for o in (node.body_target, node.surface_target) if o is not None}
            for obj in objects:
                unique_objects[obj.definition].add(obj.id)
                object_totals[obj.definition]['parts'] = len(obj.part_owner.parts or (1,)) if obj.is_part else 1
        for (definition, instances) in unique_objects.items():
            object_totals[definition]['instances'] = len(instances)
        object_totals['Untargeted']['instances'] = 1
        _print('Posture Graph Summary\n====================================================\nTotal node count = {}\nTotal edge count = {}\n\nObjects:\n===================================================\n'.format(num_nodes, num_edges))
        for (definition, data) in sorted(list(object_totals.items()), reverse=True, key=lambda x: x[1]['nodes']):
            if hasattr(definition, 'name'):
                if definition.name is None:
                    def_display = definition.id
                else:
                    def_display = definition.name
            else:
                def_display = definition
            line = '{:<42} : {instances:>5} instances   {nodes:>5} nodes   {edges:>5} edges'.format(def_display, **data)
            line += '   {:>3} parts/instance   {:>5.4} nodes/instance   {:>5.4} edges/instance'.format(data['parts'], data['nodes']/data['instances'], data['edges']/data['instances'])
            _print(line)

    def get_nodes_and_edges(self):
        return (len(self._graph), len(self._edge_info))

    def export(self, filename='posture_graph'):
        graph = self._graph
        edge_info = self._edge_info
        attribute_indexes = {}
        w = xml.etree.ElementTree.TreeBuilder()
        w.start('gexf', {'xmlns': 'http://www.gexf.net/1.2draft', 'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance', 'xsi:schemaLocation': 'http://www.gexf.net/1.2draft/gexf.xsd', 'version': '1.2'})
        w.start('meta', {})
        w.start('creator', {})
        w.data('Electronic Arts')
        w.end('creator')
        w.start('description', {})
        w.data('Tuning topology')
        w.end('description')
        w.end('meta')
        w.start('graph', {'defaultedgetype': 'directed', 'mode': 'static'})
        TYPE_MAPPING = {float: 'float', int: 'float', str: 'string'}
        w.start('attributes', {'class': 'node'})
        attribute_index = 0
        for (attribute_name, attribute_type) in PostureSpec._attribute_definitions:
            attribute_indexes[attribute_name] = str(attribute_index)
            w.start('attribute', {'id': str(attribute_index), 'title': attribute_name.strip('_').title().replace('_', ' '), 'type': TYPE_MAPPING[attribute_type]})
            w.end('attribute')
            attribute_index += 1
        w.end('attributes')
        nodes = set()
        edge_nodes = set()
        w.start('nodes', {})
        for node in sorted(graph.nodes, key=repr):
            nodes.add(hash(node))
            w.start('node', {'id': str(hash(node)), 'label': str(node)})
            w.start('attvalues', {})
            for (attribute_name, attribute_type) in PostureSpec._attribute_definitions:
                attr_value = getattr(node, attribute_name)
                w.start('attvalue', {'for': attribute_indexes[attribute_name], 'value': str(attr_value)})
                w.end('attvalue')
            w.end('attvalues')
            w.end('node')
        w.end('nodes')
        w.start('edges', {})
        edge_id = 0
        for node in sorted(graph.nodes, key=repr):
            for connected_node in sorted(graph.get_successors(node), key=repr):
                edge_nodes.add(hash(node))
                edge_nodes.add(hash(connected_node))
                w.start('edge', {'id': str(edge_id), 'label': ', '.join(str(operation) for operation in edge_info[(node, connected_node)].operations), 'source': str(hash(node)), 'target': str(hash(connected_node))})
                w.end('edge')
                edge_id += 1
        w.end('edges')
        w.end('graph')
        w.end('gexf')
        tree = w.close()

        def indent(elem, level=0):
            i = '\n' + level*'  '
            if len(elem):
                if not (elem.text and elem.text.strip()):
                    elem.text = i + '  '
                if not (elem.tail and elem.tail.strip()):
                    elem.tail = i
                for elem in elem:
                    indent(elem, level + 1)
                if not (elem.tail and elem.tail.strip()):
                    elem.tail = i
            elif not (elem.tail and elem.tail.strip()):
                elem.tail = i

        indent(tree)
        from os.path import expanduser
        path = expanduser('~')
        file = open('{}\\Desktop\\{}.gexf'.format(path, filename), 'wb')
        file.write(xml.etree.ElementTree.tostring(tree))
        file.close()
        print('DONE!')
