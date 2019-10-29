from _math import Quaternion, Vector3import _resourcemanimport collectionsimport itertoolsimport mathimport weakreffrom animation import get_throwaway_animation_contextfrom animation.animation_overrides_tuning import RequiredSlotOverridefrom animation.animation_utils import StubActorfrom animation.asm import Asm, do_params_matchfrom animation.posture_manifest import PostureManifest, AnimationParticipant, SlotManifest, SlotManifestEntry, MATCH_ANY, PostureManifestEntry, UPPER_BODY, FULL_BODY, MATCH_NONE, PostureManifestOverrideValue, _get_posture_type_for_posture_name, FrozenSlotManifestfrom constraints.constraint_functions import ConstraintGoalGenerationFunctionIdealRadiusfrom interactions import ParticipantTypefrom interactions.liability import SharedLiabilityfrom interactions.utils.object_definition_or_tags import ObjectDefinitonsOrTagsVariantfrom objects.components.types import PORTAL_COMPONENTfrom objects.doors.door_selection import DoorSelectFrontDoor, DoorSelectParticipantApartmentDoorfrom objects.pools import pool_utilsfrom objects.slots import RuntimeSlotfrom placement import find_good_location, ItemTypefrom postures import PostureTrackfrom postures.posture_errors import PostureGraphBoundaryConditionErrorfrom postures.posture_specs import PostureSpec, PostureSpecVariable, PostureAspectSurfacefrom postures.posture_state_spec import create_body_posture_state_specfrom routing import SurfaceType, SurfaceIdentifierfrom routing.portals import PY_OBJ_DATA, SURFACE_POLYGON, SURFACE_OBJ_IDfrom sims.sim_info_types import SimInfoSpawnerTags, SpeciesExtendedfrom sims4.collections import frozendictfrom sims4.log import StackVarfrom sims4.repr_utils import standard_reprfrom sims4.tuning.geometric import TunableVector3from sims4.tuning.tunable import Tunable, TunableTuple, TunableAngle, TunableEnumEntry, TunableVariant, TunableRange, TunableSingletonFactory, TunableList, OptionalTunable, TunableReference, HasTunableSingletonFactory, TunableSet, AutoFactoryInit, TunableEnumWithFilter, TunableEnumSetfrom sims4.utils import ImmutableType, InternMixin, constpropertyfrom singletons import DEFAULT, SingletonType, UNSETfrom tag import Tagfrom terrain import get_water_depth, is_terrain_tag_at_position, get_water_depth_at_locationfrom world.ocean_tuning import OceanTuningfrom world.spawn_point_enums import SpawnPointRequestReasonfrom world.terrain_enums import TerrainTagimport animationimport animation.animation_utilsimport api_configimport build_buyimport cachesimport enumimport interactions.utils.routingimport objects.slotsimport placementimport postures.posture_state_specimport routingimport servicesimport sims.sim_info_typesimport sims4.geometryimport sims4.logimport sims4.mathimport sims4.resourceslogger = sims4.log.Logger('Constraints')with sims4.reload.protected(globals()):
    _global_stub_actors = {}

    def _create_stub_actor(animation_participant, **kwargs):
        return StubActor(int(animation_participant), debug_name=str(animation_participant), **kwargs)

    GLOBAL_STUB_ACTOR = _create_stub_actor(AnimationParticipant.ACTOR)
    for species in SpeciesExtended:
        if not species == SpeciesExtended.HUMAN:
            if species == SpeciesExtended.INVALID:
                pass
            else:
                _global_stub_actors[species] = _create_stub_actor(AnimationParticipant.ACTOR, species=species)

    def get_global_stub_actor(species):
        if species == SpeciesExtended.HUMAN:
            return GLOBAL_STUB_ACTOR
        return _global_stub_actors[species]

    GLOBAL_STUB_TARGET = _create_stub_actor(AnimationParticipant.TARGET)
    GLOBAL_STUB_CARRY_TARGET = _create_stub_actor(AnimationParticipant.CARRY_TARGET)
    GLOBAL_STUB_CREATE_TARGET = _create_stub_actor(AnimationParticipant.CREATE_TARGET)
    GLOBAL_STUB_SURFACE = _create_stub_actor(AnimationParticipant.SURFACE)
    GLOBAL_STUB_CONTAINER = _create_stub_actor(AnimationParticipant.CONTAINER)
    GLOBAL_STUB_BASE_OBJECT = _create_stub_actor(AnimationParticipant.BASE_OBJECT)
    del _create_stub_actorTRACK_CONSTRAINT_FRAGMENTS = False
class AnnotatedInt(int):
    pass

class ZoneConstraintMixin:

    def create_zone_constraint(self, *args, **kwargs):
        raise NotImplementedError

    def create_constraint(self, *args, **kwargs):
        if services.current_zone() is None:
            return ANYWHERE
        else:
            return self.create_zone_constraint(*args, **kwargs)

class IntersectPreference(enum.Int, export=False):
    UNIVERSAL = 0
    CONSTRAINT_SET = 1
    JIG = 2
    GEOMETRIC_PLUS = 3
    REQUIREDSLOT = 4
    GEOMETRIC = 5

class CostFunctionBase:

    def constraint_cost(self, position, orientation, routing_surface):
        return 0.0

class ConstraintCostLineDist(CostFunctionBase):

    def __init__(self, a, b, slope, safe_width=0):
        self.a = a
        self.b = b
        self.slope = slope
        self.safe_dist = safe_width/2
        self.delta = b - a
        self.cross = sims4.math.vector_cross_2d(a, b)
        self.length = self.delta.magnitude()

    def constraint_cost(self, position, orientation, routing_surface):
        dist = abs(sims4.math.vector_cross_2d(position, self.delta) - self.cross)/self.length
        dist = max(0, dist - self.safe_dist)
        return dist*self.slope

class ConstraintCostCircleDist(CostFunctionBase):

    def __init__(self, center, radius, slope, safe_width=0):
        self.center = center
        self.radius = radius
        self.slope = slope
        self.safe_dist = safe_width/2

    def constraint_cost(self, position, orientation, routing_surface):
        delta = position - self.center
        delta.y = 0.0
        dist = abs(delta.magnitude() - self.radius)
        dist = max(0, dist - self.safe_dist)
        return dist*self.slope

class ConstraintCostArcLength(CostFunctionBase):

    def __init__(self, center, point, slope, safe_angle=0):
        self.center = center
        self.point = point
        self.slope = slope
        self.safe_angular_dist = safe_angle/2
        forward = point - center
        flattened = sims4.math.Vector3(forward.x, 0, forward.z)
        self.forward = sims4.math.vector_normalize(flattened)

    def constraint_cost(self, position, orientation, routing_surface):
        delta = position - self.center
        delta.y = 0.0
        radius = delta.magnitude()
        if radius < sims4.math.EPSILON:
            return 0.0
        norm_delta = delta/radius
        dot = (self.forward*norm_delta).magnitude()
        if dot < 0:
            m = (self.forward + norm_delta).magnitude()
            angle = math.pi - 2.0*math.asin(min(m/2.0, 1.0))
        else:
            m = (self.forward - norm_delta).magnitude()
            angle = 2.0*math.asin(min(m/2.0, 1.0))
        angle = max(0, angle - self.safe_angular_dist)
        dist = angle*radius
        return dist*self.slope

def _get_score_cache_key_fn(constraint, position, orientation):
    return (constraint.geometry, constraint._routing_surface, frozenset(constraint._scoring_functions), position, orientation.x, orientation.y, orientation.z, orientation.w)

def _is_routing_surface_valid_cache_key(constraint, routing_surface):
    if routing_surface.type == routing.SurfaceType.SURFACETYPE_POOL:
        return (id(constraint), routing_surface)
    return (constraint.multi_surface, constraint.routing_surface, routing_surface)

class Constraint(ImmutableType, InternMixin):
    DEFAULT_FACING_RANGE = TunableAngle(sims4.math.PI/2, description='The size of the angle-range that sims should use when determining facing constraints.')
    INTERSECT_PREFERENCE = IntersectPreference.GEOMETRIC
    ROUTE_GOAL_COUNT_FOR_SCORING_FUNC = Tunable(int, 40, description='The number of points to sample when routing to a simple constraint that can be scored natively.')
    MINIMUM_VALID_AREA = TunableRange(float, 2, minimum=0, description='The minimum area, in square meters, of the polygon for constraints to be considered valid (unless they have allow_small_intersections set).')
    IGNORE_OUTER_PENALTY_THRESHOLD = 0.8
    WALL_OBJECT_FORWARD_MOD = 0.15
    __slots__ = ('_hash',)

    @property
    def _debug_name(self):
        return ''

    def __init__(self, geometry=None, routing_surface=None, scoring_functions=(), goal_functions=(), posture_state_spec=None, age=None, debug_name='', allow_small_intersections=DEFAULT, flush_planner=False, allow_geometry_intersections=True, los_reference_point=DEFAULT, ignore_outer_penalty_threshold=IGNORE_OUTER_PENALTY_THRESHOLD, cost=0, objects_to_ignore=None, create_jig_fn=None, multi_surface=False, enables_height_scoring=False, terrain_tags=None, min_water_depth=None, max_water_depth=None):
        self._geometry = geometry
        self._routing_surface = routing_surface
        self._posture_state_spec = posture_state_spec
        self._age = age
        if allow_small_intersections is DEFAULT:
            allow_small_intersections = True if geometry is not None else False
        self._allow_small_intersections = allow_small_intersections
        self._flush_planner = flush_planner
        self._scoring_functions = scoring_functions
        self._goal_functions = goal_functions
        self._allow_geometry_intersections = allow_geometry_intersections
        self._los_reference_point = los_reference_point
        self._ignore_outer_penalty_threshold = ignore_outer_penalty_threshold
        self._cost = cost
        self._objects_to_ignore = None if objects_to_ignore is None else frozenset(objects_to_ignore)
        self._create_jig_fn = create_jig_fn
        self._terrain_tags = terrain_tags
        self._min_water_depth = min_water_depth
        self._max_water_depth = max_water_depth
        if not multi_surface:
            if self._routing_surface is None:
                multi_surface = True
        elif self._geometry.polygon is not None:
            area = self._geometry.polygon.area()
            if area < self.MINIMUM_VALID_AREA:
                multi_surface = False
        self._multi_surface = multi_surface
        self._enables_height_scoring = enables_height_scoring
        if routing_surface is None and geometry is not None and geometry.polygon is not None:
            logger.callstack('Trying to create a constraint with geometry that has no routing surface.\n                                \n   Geometry: {}\n   Posture Spec: {}\n   Debug Name: {}\n   Create Jig: {}\n                                \n   Multi-Surface: {}"\n    {},\n                                ', geometry, posture_state_spec, debug_name, create_jig_fn, multi_surface, StackVar(('interaction', 'sim', 'target')), level=sims4.log.LEVEL_ERROR)

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = h = hash(frozenset(self.__dict__.items()))
            return h

    def __eq__(self, other):
        if other is self:
            return True
        return other.__class__ == self.__class__ and (other.__hash__() == self.__hash__() and other.__dict__ == self.__dict__)

    def _copy(self, debug_name='', **overrides):
        inst = self.__class__.__new__(self.__class__)
        inst.__dict__.update(self.__dict__, **overrides)
        return inst

    def __repr__(self):
        return 'Constraint(...)'
        if self._geometry is not None:
            args.append('geometry')
        if self._posture_state_spec is not None:
            args.append(str(self._posture_state_spec))
        if self._terrain_tags is not None:
            args.append(str(self._terrain_tags))
        if self._min_water_depth is not None and self._min_water_depth >= 0.0 or self._max_water_depth is not None and self._max_water_depth >= 0.0:
            args.append('depth')
        return standard_repr(self, *args)

    @staticmethod
    def get_validated_routing_position(obj):
        top_level_parent = obj
        while top_level_parent.parent is not None:
            top_level_parent = top_level_parent.parent
        offset_position = obj.position
        if top_level_parent.wall_or_fence_placement:
            offset_position += top_level_parent.forward*Constraint.WALL_OBJECT_FORWARD_MOD
        return (offset_position, top_level_parent)

    @staticmethod
    def get_los_reference_point(target, is_carry_target=False):
        if target is None:
            return (None, None)
        if target.disable_los_reference_point:
            return (None, None)
        if target.is_in_inventory():
            return (None, None)
        if target.is_sim and not is_carry_target:
            return (None, None)
        return Constraint.get_validated_routing_position(target)

    @property
    def geometry(self):
        return self._geometry

    @property
    def _sim(self):
        pass

    @constproperty
    def restricted_on_slope():
        return False

    def get_geometry_for_point(self, pos):
        if self._geometry is not None and self._geometry.contains_point(pos):
            return self._geometry

    def get_geometry_text(self, indent_string):
        return '{}\n'.format(self._geometry)

    def generate_single_surface_constraints(self):
        constraints = []
        for constraint in self:
            if not constraint.routing_surface is None:
                if constraint.routing_surface.type == routing.SurfaceType.SURFACETYPE_UNKNOWN:
                    pass
                elif not constraint.multi_surface:
                    constraints.append(constraint)
                else:
                    world_routing_surface = constraint.get_world_routing_surface()
                    constraints.append(constraint.get_single_surface_version(world_routing_surface))
                    objects_to_ignore = constraint._objects_to_ignore
                    (obj_surface, obj_surface_data) = constraint._get_object_routing_surface_and_data(early_out=False)
                    compound_polygon = constraint._geometry.polygon if constraint._geometry is not None and constraint._geometry.polygon is not None else None
                    for (obj_id, obj_polygon) in obj_surface_data.items():
                        temp_objects_to_ignore = objects_to_ignore | {obj_id} if objects_to_ignore else {obj_id}
                        temp_objects_to_ignore = frozenset(temp_objects_to_ignore)
                        geometry = sims4.geometry.RestrictedPolygon(obj_polygon, ())
                        if compound_polygon is not None:
                            intersect_polygon = compound_polygon.intersect(geometry.polygon)
                            geometry = sims4.geometry.RestrictedPolygon(intersect_polygon, constraint._geometry.restrictions)
                        constraints.append(constraint.get_single_surface_version(obj_surface, _geometry=geometry, _objects_to_ignore=temp_objects_to_ignore))
                    if constraint.geometry is not None and constraint.geometry.polygon is not None and constraint.supports_swim:
                        pool_routing_surface = constraint._get_pool_routing_surface()
                        if pool_routing_surface is not None:
                            constraints.append(constraint.get_single_surface_version(pool_routing_surface))
        return create_constraint_set(constraints)

    def get_provided_points_for_goals(self):
        points = []
        for goal_fn in self._goal_functions:
            points.extend(goal_fn())
        return tuple(points)

    def generate_geometry_only_constraint(self):
        constraints = [Constraint(geometry=constraint.geometry, scoring_functions=constraint._scoring_functions, goal_functions=constraint._goal_functions, allow_small_intersections=constraint._allow_small_intersections, routing_surface=constraint.routing_surface, allow_geometry_intersections=constraint._allow_geometry_intersections, cost=constraint.cost, objects_to_ignore=constraint._objects_to_ignore, multi_surface=constraint.multi_surface, enables_height_scoring=constraint.enables_height_scoring, min_water_depth=constraint.get_min_water_depth(), max_water_depth=constraint.get_max_water_depth()) for constraint in self if constraint.geometry is not None]
        if not constraints:
            return Anywhere()
        return create_constraint_set(constraints)

    def generate_alternate_geometry_constraint(self, alternate_geometry):
        constraints = self._copy(_geometry=alternate_geometry)
        if not constraints:
            return Anywhere()
        return create_constraint_set(constraints)

    def generate_alternate_water_depth_constraint(self, min_water_depth, max_water_depth):
        constraints = self._copy(_min_water_depth=min_water_depth, _max_water_depth=max_water_depth)
        if not constraints:
            return Anywhere()
        return create_constraint_set(constraints)

    def generate_forbid_small_intersections_constraint(self):
        return self._copy(_allow_small_intersections=False)

    def generate_constraint_with_cost(self, cost):
        return self._copy(_cost=cost)

    def generate_constraint_with_posture_spec(self, posture_state_spec):
        return self._copy(_posture_state_spec=posture_state_spec)

    def generate_constraint_with_slot_info(self, actor, slot_target, chosen_slot):
        if self.posture_state_spec is None:
            return self
        (posture_manifest, slot_manifest, body_target) = self.posture_state_spec
        new_slot_manifest = SlotManifest()
        for manifest_entry in slot_manifest:
            if manifest_entry.actor == actor:
                overrides = {}
                if not isinstance(manifest_entry.target, RuntimeSlot):
                    overrides['target'] = slot_target
                if not isinstance(manifest_entry.slot, RuntimeSlot):
                    overrides['slot'] = chosen_slot
                manifest_entry = manifest_entry.with_overrides(**overrides)
            new_slot_manifest.add(manifest_entry)
        posture_state_spec = postures.posture_state_spec.PostureStateSpec(posture_manifest, new_slot_manifest, body_target)
        return self._copy(_posture_state_spec=posture_state_spec)

    def generate_posture_only_constraint(self):
        posture_constraints = []
        for constraint in self:
            if constraint == Anywhere():
                posture_constraints.append(constraint)
            elif constraint.posture_state_spec is None:
                pass
            else:
                posture_constraints.append(Constraint(posture_state_spec=constraint.posture_state_spec))
        if not posture_constraints:
            return Anywhere()
        return create_constraint_set(posture_constraints)

    def generate_body_posture_only_constraint(self):
        body_posture_constraints = []
        for constraint in self:
            if constraint == Anywhere():
                body_posture_constraints.append(constraint)
            elif constraint.posture_state_spec is None:
                pass
            else:
                override = PostureManifestOverrideValue(MATCH_ANY, MATCH_ANY, None)
                posture_manifest_entries = []
                for posture_manifest_entry in constraint.posture_state_spec.posture_manifest:
                    new_manifest_entries = posture_manifest_entry.get_entries_with_override(override)
                    posture_manifest_entries.extend(new_manifest_entries)
                posture_manifest_new = PostureManifest(posture_manifest_entries)
                posture_state_spec_simplified = postures.posture_state_spec.create_body_posture_state_spec(posture_manifest_new, body_target=constraint.posture_state_spec.body_target)
                body_posture_constraints.append(Constraint(posture_state_spec=posture_state_spec_simplified))
        if not body_posture_constraints:
            return Anywhere()
        return create_constraint_set(body_posture_constraints)

    def generate_constraint_with_new_geometry(self, geometry, routing_surface=None):
        return self._copy(_geometry=geometry, _scoring_functions=(), _goal_functions=(), _routing_surface=routing_surface if routing_surface is not None else self.routing_surface)

    @property
    def supports_swim(self):
        (early_out, _) = self.intersect_posture_spec(animation.posture_manifest_constants.SWIM_AT_NONE_CONSTRAINT)
        return early_out is None

    def supports_mobile_posture(self, mobile_posture):
        (early_out, _) = self.intersect_posture_spec(mobile_posture.get_mobile_at_none_constraint())
        return early_out is None

    @property
    def routing_surface(self):
        return self._routing_surface

    @property
    def posture_state_spec(self):
        return self._posture_state_spec

    @property
    def age(self):
        return self._age

    @property
    def create_jig_fn(self):
        return self._create_jig_fn

    @property
    def multi_surface(self):
        return self._multi_surface

    @property
    def enables_height_scoring(self):
        return self._enables_height_scoring

    def get_multi_surface_version(self):
        if self.multi_surface:
            return self
        return self._copy(_multi_surface=True)

    def get_single_surface_version(self, surface, **overrides):
        if not self.multi_surface:
            if self.routing_surface != surface:
                raise ValueError('Surface {} passed into get_single_surface_version of constraint {} with surface {}'.format(surface, self, self.routing_surface), owner='tastle')
            return self._copy(**overrides)
        return self._copy(_multi_surface=False, _routing_surface=surface, **overrides)

    def get_object_routing_surface(self):
        zone_id = services.current_zone_id()
        return routing.SurfaceIdentifier(zone_id or 0, self.routing_surface.secondary_id, routing.SurfaceType.SURFACETYPE_OBJECT)

    def get_world_routing_surface(self, force_world=False):
        if force_world or self.multi_surface and self.routing_surface is not None and self.routing_surface.type in routing.object_routing_surfaces:
            zone_id = services.current_zone_id()
            return routing.SurfaceIdentifier(zone_id or 0, self.routing_surface.secondary_id, routing.SurfaceType.SURFACETYPE_WORLD)
        return self.routing_surface

    def _get_bounding_box_polygon(self):
        return self.polygons

    @caches.cached
    def _get_bounding_boxes_2D(self):
        bounding_boxes = []
        for compound_polygon in self._get_bounding_box_polygon():
            min_x = max_x = min_z = max_z = None
            for polygon in compound_polygon:
                (lower_bound, upper_bound) = polygon.bounds()
                min_x = min(lower_bound.x, min_x) if min_x is not None else lower_bound.x
                max_x = max(upper_bound.x, max_x) if max_x is not None else upper_bound.x
                min_z = min(lower_bound.z, min_z) if min_z is not None else lower_bound.z
                max_z = max(upper_bound.z, max_z) if max_z is not None else upper_bound.z
            bounding_boxes.append(sims4.geometry.QtRect(sims4.math.Vector2(min_x, min_z), sims4.math.Vector2(max_x, max_z)))
        return bounding_boxes

    @caches.cached
    def is_location_water_depth_valid(self, location):
        min_water_depth = self.get_min_water_depth()
        max_water_depth = self.get_max_water_depth()
        if min_water_depth is None and max_water_depth is None:
            return True
        depth = get_water_depth_at_location(location)
        if min_water_depth is not None and depth < min_water_depth:
            return False
        elif max_water_depth is not None and max_water_depth < depth:
            return False
        return True

    @caches.cached
    def is_location_terrain_tags_valid(self, location):
        terrain_tags = self.get_terrain_tags()
        if terrain_tags is None:
            return True
        return is_terrain_tag_at_position(location.position.x, location.position.z, terrain_tags, level=location.routing_surface.secondary_id)

    @caches.cached(key=_is_routing_surface_valid_cache_key)
    def is_routing_surface_valid(self, routing_surface):
        if self.routing_surface is None:
            return False
        if self.routing_surface.type == routing.SurfaceType.SURFACETYPE_UNKNOWN:
            return False
        if not self.multi_surface:
            return routing_surface == self.routing_surface
        if routing_surface.type == routing.SurfaceType.SURFACETYPE_WORLD:
            _routing_surface = self.get_world_routing_surface()
            return routing_surface == _routing_surface
        if routing_surface.type == routing.SurfaceType.SURFACETYPE_OBJECT:
            _routing_surface = self.get_object_routing_surface()
            return routing_surface == _routing_surface
        elif routing_surface.type == routing.SurfaceType.SURFACETYPE_POOL:
            _routing_surface = self._get_pool_routing_surface()
            return routing_surface == _routing_surface
        return False

    def get_all_valid_routing_surfaces(self, ignore_posture_compatibility=False, empty_set_for_invalid=False, force_multi_surface=False):
        if self.routing_surface is None:
            return {None}
        if self.routing_surface.type == routing.SurfaceType.SURFACETYPE_UNKNOWN:
            if empty_set_for_invalid:
                return set()
            return {None}
        if force_multi_surface or not self.multi_surface:
            return {self.routing_surface}
        world_routing_surface = self.get_world_routing_surface()
        self_surfaces = {world_routing_surface}
        (obj_surface, _) = self._get_object_routing_surface_and_data()
        if obj_surface is not None:
            self_surfaces.add(obj_surface)
        if ignore_posture_compatibility or not self.supports_swim:
            return self_surfaces
        if self.geometry is None or self.geometry.polygon is None:
            return self_surfaces
        pool_routing_surface = self._get_pool_routing_surface()
        if pool_routing_surface is not None:
            self_surfaces.add(pool_routing_surface)
        return self_surfaces

    def _get_object_routing_surface_and_data(self, early_out=True):
        object_surface_data = {}
        object_default_surface = self.get_object_routing_surface()
        world_routing_surface = self.get_world_routing_surface()
        for bounding_box in self._get_bounding_boxes_2D():
            object_surfaces = services.sim_quadtree().query(bounds=bounding_box, surface_id=world_routing_surface, filter=ItemType.ROUTABLE_OBJECT_SURFACE, flags=sims4.geometry.ObjectQuadTreeQueryFlag.IGNORE_SURFACE_TYPE)
            object_surface_data.update({object_data[PY_OBJ_DATA][SURFACE_OBJ_ID]: object_data[PY_OBJ_DATA][SURFACE_POLYGON] for object_data in object_surfaces})
            if object_surface_data and early_out:
                break
        if not object_surface_data:
            return (None, {})
        return (object_default_surface, object_surface_data)

    def _get_pool_routing_surface(self):
        zone_id = services.current_zone_id()
        polygon = self.geometry.polygon
        level_id = self.routing_surface.secondary_id
        for pool in pool_utils.get_main_pool_objects_gen():
            pool_routing_surface = pool.provided_routing_surface
            pool_level_id = pool_routing_surface.secondary_id
            if pool_level_id == level_id and build_buy.is_location_pool(zone_id, pool.position, pool_level_id):
                if pool.bounding_polygon is None:
                    logger.error('Pool {} does not have a bounding polygon. Location: {}', pool, pool._location)
                else:
                    pool_polygon = sims4.geometry.CompoundPolygon(pool.bounding_polygon)
                    if polygon.intersects(pool_polygon):
                        return pool_routing_surface
        if level_id == 0 and services.terrain_service.ocean_object() is not None and any(get_water_depth(vertex.x, vertex.z) > sims4.math.EPSILON for poly in polygon for vertex in poly):
            return SurfaceIdentifier(zone_id, 0, SurfaceType.SURFACETYPE_POOL)

    @property
    def polygons(self):
        if hasattr(self.geometry, 'polygon') and self.geometry.polygon is not None:
            return (self.geometry.polygon,)
        return ()

    @property
    def average_position(self):
        positions = []
        for compound_polygon in self.polygons:
            for polygon in compound_polygon:
                positions.extend(polygon)
        if not positions:
            return
        return sum(positions, sims4.math.Vector3.ZERO())/len(positions)

    @property
    def routing_positions(self):
        positions = []
        for compound_polygon in self.polygons:
            for polygon in compound_polygon:
                positions.extend(polygon)
                positions.append(sum(polygon, sims4.math.Vector3.ZERO())/len(polygon))
        return positions

    def single_point(self):
        point = None
        routing_surface = None
        for constraint in self:
            if constraint.geometry is None:
                return (None, None)
            if len(constraint.geometry.polygon) != 1:
                return (None, None)
            if len(constraint.geometry.polygon[0]) != 1:
                return (None, None)
            test_point = constraint.geometry.polygon[0][0]
            test_routing_surface = constraint.routing_surface
            if point is not None and sims4.math.vector3_almost_equal_2d(point, test_point) and test_routing_surface != routing_surface:
                return (None, None)
            point = test_point
            routing_surface = test_routing_surface
        return (point, routing_surface)

    def area(self):
        if self._geometry is not None and self._geometry.polygon is not None:
            return abs(self._geometry.polygon.area())

    @property
    def cost(self):
        return self._cost

    def __iter__(self):
        yield self

    def get_posture_specs(self, resolver=None, interaction=None):
        posture_state_spec = self._posture_state_spec
        if posture_state_spec is not None:
            if resolver is not None:
                posture_state_spec = posture_state_spec.get_concrete_version(resolver)
            return [(spec, var_map, self) for (spec, var_map) in posture_state_spec.get_posture_specs_gen(interaction=interaction)]
        else:
            return [(PostureSpec((None, None, None)), frozendict(), self)]

    def get_connectivity_handles(self, *args, los_reference_point=None, entry=True, **kwargs):
        if not (self.geometry and self.geometry.polygon):
            return ()
        kwargs['geometry'] = self.geometry
        los_reference_point = los_reference_point if self._los_reference_point is DEFAULT else self._los_reference_point
        connectivity_handle = routing.connectivity.RoutingHandle(*args, constraint=self, los_reference_point=los_reference_point, **kwargs)
        return (connectivity_handle,)

    @caches.cached(maxsize=None, key=_get_score_cache_key_fn)
    def constraint_cost(self, position, orientation):
        routing_surface = self._routing_surface
        return sum(scoring_fn.constraint_cost(position, orientation, routing_surface) for scoring_fn in self._scoring_functions)

    def get_terrain_tags(self):
        if not hasattr(self, '_terrain_tags'):
            return
        return self._terrain_tags

    def get_min_water_depth(self):
        return self._min_water_depth

    def get_max_water_depth(self):
        return self._max_water_depth

    def apply(self, other_constraint):
        intersection = self.intersect(other_constraint)
        if intersection.valid:
            return self
        return intersection

    @caches.cached(maxsize=None)
    def intersect(self, other_constraint):
        if self == other_constraint:
            return self
        if not other_constraint.valid:
            return other_constraint
        if self.INTERSECT_PREFERENCE <= other_constraint.INTERSECT_PREFERENCE:
            result = self._intersect(other_constraint)
        else:
            result = other_constraint._intersect(self)
        return result

    def tested_intersect(self, other_constraint, test_constraint):
        if self == other_constraint:
            return self
        else:
            test_intersect = self.intersect(test_constraint)
            if test_intersect.valid:
                return self.intersect(other_constraint)
        return self

    def _merge_delta_constraint(self, other_constraint):
        if self == other_constraint:
            return self
        return Nowhere('Constraints cannot be merged, {} : {}', self, other_constraint)

    def merge_delta_constraint(self, other_constraint):
        if self.INTERSECT_PREFERENCE <= other_constraint.INTERSECT_PREFERENCE:
            result = self._merge_delta_constraint(other_constraint)
        else:
            result = other_constraint._merge_delta_constraint(self)
        return result

    @staticmethod
    def _combine_debug_names(value0, value1):
        if not value1:
            return value0
        if not value0:
            return value1
        src = str(value0) + '&' + str(value1)
        if len(src) < 100:
            return src
        return src[:100] + '...'

    def intersect_posture_spec(self, other):
        if other._posture_state_spec in (None, self._posture_state_spec):
            return (None, self._posture_state_spec)
        if self._posture_state_spec is None:
            return (None, other._posture_state_spec)
        posture_state_spec = self._posture_state_spec.intersection(other._posture_state_spec)
        if not posture_state_spec:
            return (Nowhere('Posture State Spec intersection failed, A: {}, B: {}', self._posture_state_spec, other._posture_state_spec), None)
        if posture_state_spec.slot_manifest:
            for manifest_entry in posture_state_spec.posture_manifest:
                if manifest_entry.surface == MATCH_NONE:
                    return (Nowhere('posture_state_spec has a slot manifest, but the manifest does not allow a surface, State Spec: {}. Slot Manifest: {}', posture_state_spec, posture_state_spec.slot_manifest), None)
        return (None, posture_state_spec)

    def _intersect_kwargs(self, other):
        allow_geometry_intersections = self._allow_geometry_intersections and other._allow_geometry_intersections
        if allow_geometry_intersections or other._geometry is not None or self._geometry is not None:
            return (Nowhere('Geometry intersection failed. Geometry is locked for constraints: {} and {}', self, other), None)
        if other._geometry in (None, self._geometry):
            geometry = self._geometry
        elif self._geometry is None:
            geometry = other._geometry
        else:
            geometry = self._geometry.intersect(other._geometry)
            if not geometry:
                return (Nowhere('Geometry intersection failed, A: {}, B: {}', self._geometry, other._geometry), None)
        (result, posture_state_spec) = self.intersect_posture_spec(other)
        if isinstance(result, Nowhere):
            return (result, None)
        if self.age is not None and other.age is not None and self.age != other.age:
            return (Nowhere('Constraints have mismatched ages, A: {}, B: {}', self, other), None)
        age = self.age or other.age
        min_water_depth = self.get_min_water_depth()
        if min_water_depth is None:
            min_water_depth = other.get_min_water_depth()
        else:
            other_min_water_depth = other.get_min_water_depth()
            if other_min_water_depth is not None:
                min_water_depth = max(min_water_depth, other_min_water_depth)
        max_water_depth = self.get_max_water_depth()
        if max_water_depth is None:
            max_water_depth = other.get_max_water_depth()
        else:
            other_max_water_depth = other.get_max_water_depth()
            if other_max_water_depth is not None:
                max_water_depth = min(max_water_depth, other_max_water_depth)
        if min_water_depth is not None and max_water_depth is not None and max_water_depth < min_water_depth:
            return (Nowhere('Water Depth null range, A: ({}, {}), B: ({}, {})', self.get_min_water_depth(), self.get_max_water_depth(), other.get_min_water_depth(), other.get_max_water_depth()), None)
        terrain_tags = self.get_terrain_tags()
        if terrain_tags is None:
            terrain_tags = other.get_terrain_tags()
        else:
            other_terrain_tags = other.get_terrain_tags()
            if other_terrain_tags is not None:
                terrain_tags = list(set(terrain_tags).intersection(other_terrain_tags))
            if terrain_tags is not None and len(terrain_tags) == 0:
                return (Nowhere('Terrain Tags null range, A: {}, B: {}', self.get_terrain_tags(), other.get_terrain_tags()), None)
        scoring_functions = self._scoring_functions + other._scoring_functions
        scoring_functions = tuple(set(scoring_functions))
        goal_functions = getattr(self, '_goal_functions', ()) + getattr(other, '_goal_functions', ())
        goal_functions = tuple(set(goal_functions))
        allow_small_intersections = self._allow_small_intersections or other._allow_small_intersections
        if self._los_reference_point and other._los_reference_point and self._los_reference_point != other._los_reference_point:
            logger.error('\n            Trying to intersect two constraints that both have an LoS Reference Point\n                Constraint A: {}\n                Constraint B: {}\n                LoS Ref A: {}\n                LoS Ref B: {}\n            ', self, other, self._los_reference_point, other._los_reference_point)
        if self._los_reference_point is DEFAULT:
            los_reference_point = other._los_reference_point
        else:
            los_reference_point = self._los_reference_point
        outer_penalty_threshold = min(self._ignore_outer_penalty_threshold, other._ignore_outer_penalty_threshold)
        cost = max(self._cost, other._cost)
        objects_to_ignore = self._objects_to_ignore
        if objects_to_ignore is None:
            objects_to_ignore = other._objects_to_ignore
        elif other._objects_to_ignore is not None:
            objects_to_ignore = objects_to_ignore | other._objects_to_ignore
        create_jig_fn = self._create_jig_fn or other._create_jig_fn
        flush_planner = self._flush_planner or other._flush_planner
        if self.multi_surface and other.multi_surface:
            multi_surface = True
        else:
            multi_surface = False
        enables_height_scoring = self.enables_height_scoring or other.enables_height_scoring
        self_surfaces = self.get_all_valid_routing_surfaces()
        other_surfaces = other.get_all_valid_routing_surfaces()
        if self.routing_surface is None or other.routing_surface is None:
            routing_surface = self.routing_surface or other.routing_surface
            all_surfaces = self_surfaces if None not in self_surfaces else other_surfaces
        else:
            if not self_surfaces.intersection(other_surfaces):
                return (Nowhere('Surface Intersection Failure'), None)
            if multi_surface:
                routing_surface = self.routing_surface
                all_surfaces = self_surfaces
            elif self.multi_surface:
                routing_surface = other.routing_surface
                all_surfaces = other_surfaces
            else:
                routing_surface = self.routing_surface
                all_surfaces = self_surfaces
        all_surfaces -= {None}
        if all_surfaces and posture_state_spec is not None and any(posture_manifest.compatible_posture_types for posture_manifest in posture_state_spec.supported_postures):
            all_surface_types = {surface.type for surface in all_surfaces}
            for posture_manifest in posture_state_spec.supported_postures:
                if any((surface_type in all_surface_types for surface_type in posture.surface_types) for posture in posture_manifest.compatible_posture_types):
                    break
            return (Nowhere('Posture State Spec: {} does not support any valid surfaces: {}', posture_state_spec, tuple(all_surfaces)), None)
        kwargs = {'_geometry': geometry, '_routing_surface': routing_surface, '_scoring_functions': scoring_functions, '_goal_functions': goal_functions, '_posture_state_spec': posture_state_spec, '_age': age, '_allow_small_intersections': allow_small_intersections, '_allow_geometry_intersections': allow_geometry_intersections, '_los_reference_point': los_reference_point, '_cost': cost, '_objects_to_ignore': objects_to_ignore, '_flush_planner': flush_planner, '_ignore_outer_penalty_threshold': outer_penalty_threshold, '_create_jig_fn': create_jig_fn, '_multi_surface': multi_surface, '_enables_height_scoring': enables_height_scoring, '_terrain_tags': terrain_tags, '_min_water_depth': min_water_depth, '_max_water_depth': max_water_depth}
        return (None, kwargs)

    def _intersect(self, other_constraint):
        (early_out, overrides) = self._intersect_kwargs(other_constraint)
        if early_out is not None:
            return early_out
        return self._copy(**overrides)

    @property
    def locked_params(self):
        pass

    @property
    def valid(self):
        if self._geometry is None:
            return True
        if self._geometry.polygon is None:
            return True
        elif self._geometry.polygon:
            if not self._allow_small_intersections:
                area = self._geometry.polygon.area()
                if area < self.MINIMUM_VALID_AREA:
                    return False
                else:
                    return True
            else:
                return True
        return True
        return False

    @property
    def tentative(self):
        return False

    def _get_posture_state_constraint(self, posture_state, target_resolver):
        if self.tentative and posture_state is not None:
            raise AssertionError('Tentative constraints must provide an implementation of apply_posture_state().')
        if self.age is not None:
            participant = AnimationParticipant.ACTOR
            actor = target_resolver(participant, participant)
            if actor is not None and self.age != actor.age.age_for_animation_cache:
                return Nowhere('Constraint Age does not match actor. Constraint: {}, Actor: {}', self, actor)
        if posture_state is None:
            return Anywhere()
        posture_state_constraint = posture_state.posture_constraint
        return posture_state_constraint

    def apply_posture_state(self, posture_state, target_resolver, **_):
        if self._posture_state_spec is None:
            self_constraint = self
        else:
            posture_state_spec = self._posture_state_spec.get_concrete_version(target_resolver, posture_state=posture_state)
            self_constraint = self._copy(_posture_state_spec=posture_state_spec)
        posture_state_constraint = self._get_posture_state_constraint(posture_state, target_resolver)
        intersection = self_constraint.intersect(posture_state_constraint)
        return intersection

    def remove_constraints_with_unset_postures(self):
        return self

    def get_holster_version(self):
        if self._posture_state_spec is None:
            return self
        posture_state_spec = self._posture_state_spec.get_holster_version()
        self_constraint = self._copy(_posture_state_spec=posture_state_spec)
        return self_constraint

    def create_concrete_version(self, interaction):
        return self

    def add_slot_constraints_if_possible(self, sim):
        new_constraints = [sub_constraint for sub_constraint in self]
        for sub_constraint in self:
            if sub_constraint.posture_state_spec is None:
                pass
            else:
                body_target = sub_constraint.posture_state_spec.body_target
                if not body_target is None:
                    if isinstance(body_target, PostureSpecVariable):
                        pass
                    else:
                        posture_type = None
                        is_specific = None
                        for posture_manifest_entry in sub_constraint.posture_state_spec.posture_manifest:
                            if posture_manifest_entry.posture_type_specific:
                                is_specific = True
                                posture_type_entry = posture_manifest_entry.posture_type_specific
                            else:
                                is_specific = False
                                posture_type_entry = posture_manifest_entry.posture_type_family
                            if posture_type is not None and posture_type is not posture_type_entry:
                                raise RuntimeError('Mismatched posture types within a single posture state spec! [maxr]')
                            posture_type = posture_type_entry
                        if posture_type is None or not posture_type.unconstrained:
                            if posture_type.mobile:
                                pass
                            else:
                                new_constraints.remove(sub_constraint)
                                if body_target.parts:
                                    targets = (part for part in body_target.parts if part.supports_posture_type(posture_type, is_specific=is_specific))
                                else:
                                    targets = (body_target,)
                                slot_constraints = []
                                for target in targets:
                                    target_body_posture = postures.create_posture(posture_type, sim, target, is_throwaway=True)
                                    resolver = {body_target: target}.get
                                    posture_state_spec = sub_constraint.posture_state_spec.get_concrete_version(resolver)
                                    if posture_state_spec.body_target is not sub_constraint.posture_state_spec.body_target:
                                        for entry in posture_state_spec.posture_manifest:
                                            if entry.surface_target is not None and entry.surface_target.parts is not None and posture_state_spec.body_target.parent in entry.surface_target.parts:
                                                surface_resolver = {entry.surface_target: posture_state_spec.body_target.parent}.get
                                                posture_state_spec = posture_state_spec.get_concrete_version(surface_resolver)
                                    slot_constraint = target_body_posture.build_slot_constraint(posture_state_spec=posture_state_spec)
                                    slot_constraints.append(slot_constraint)
                                slot_constraint_set = create_constraint_set(slot_constraints)
                                new_constraint = sub_constraint.intersect(slot_constraint_set)
                                new_constraints.append(new_constraint)
        constraint = create_constraint_set(new_constraints)
        return constraint

    def get_target_object_filters(self):
        filter_set = set()
        for entry in self.posture_state_spec.posture_manifest:
            if entry.target_object_filter is not MATCH_ANY:
                filter_set.add(entry.target_object_filter)
        return filter_set

    def estimate_distance_cache_key(self):
        return self

class _SingletonConstraint(SingletonType, Constraint):

    def __init__(self, *args, **kwargs):
        return super().__init__()

    def _copy(self, *args, **kwargs):
        return self

class Anywhere(_SingletonConstraint):
    INTERSECT_PREFERENCE = IntersectPreference.UNIVERSAL

    def apply_posture_state(self, *args, **kwargs):
        return self

    def _intersect_kwargs(self, other):
        raise RuntimeError()

    def intersect(self, other_constraint):
        return other_constraint

    def _intersect(self, other_constraint):
        return other_constraint

    def get_holster_version(self):
        return self

    @property
    def valid(self):
        return True

    @property
    def multi_surface(self):
        return True
ANYWHERE = Anywhere()
class _Nowhere(Constraint):
    INTERSECT_PREFERENCE = IntersectPreference.UNIVERSAL

    def __eq__(self, other):
        return type(self) == type(other)

    def __hash__(self):
        return hash(type(self))

    def _copy(self, *args, **kwargs):
        return self

    def __repr__(self):
        return 'Nowhere()'

    def intersect(self, other_constraint):
        return self

    def _intersect(self, other_constraint):
        return self

    def apply_posture_state(self, *args, **kwargs):
        return self

    def get_holster_version(self):
        return self

    @property
    def valid(self):
        return False

class Nowhere(SingletonType, _Nowhere):

    def __init__(self, debug_str, *debug_args):
        super().__init__()

class ResolvePostureContext(ImmutableType, InternMixin):

    def __init__(self, posture_manifest_entry, create_target_name, asm_key, state_name, actor_name, target_name, carry_target_name, override_manifests, required_slots, initial_state, base_object_name):
        self._posture_manifest_entry = posture_manifest_entry
        self._create_target_name = create_target_name
        self._asm_key = asm_key
        self._state_name = state_name
        self._actor_name = actor_name
        self._target_name = target_name
        self._carry_target_name = carry_target_name
        self._override_manifests = override_manifests
        self._required_slots = tuple(required_slots)
        self._initial_state = initial_state
        self._base_object_name = base_object_name

    def __repr__(self):
        return standard_repr(self, **self.__dict__)

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['_required_slots']
        del state['_asm_key']
        required_slots_list = []
        for required_slot in self._required_slots:
            slot_tuple = (required_slot.actor_name, required_slot.parent_name, required_slot.slot_type.__name__)
            required_slots_list.append(slot_tuple)
        state['custom_require_slots'] = required_slots_list
        state['custom_asm_key'] = (self._asm_key.type, self._asm_key.instance, self._asm_key.group)
        return state

    def __setstate__(self, state):
        required_slots = state['custom_require_slots']
        del state['custom_require_slots']
        asm_key = state['custom_asm_key']
        del state['custom_asm_key']
        slot_list = []
        instance_manager = services.get_instance_manager(sims4.resources.Types.SLOT_TYPE)
        for (slot_actor_name, parent_name, slot_type_name) in required_slots:
            slot_type = None
            for tuning_file in instance_manager.types.values():
                if slot_type_name == tuning_file.__name__:
                    slot_type = tuning_file
                    break
            slot_list.append(RequiredSlotOverride(slot_actor_name, parent_name, slot_type))
        self.__dict__.update(state)
        self._required_slots = tuple(slot_list)
        self._asm_key = _resourceman.Key(*asm_key)

    def resolve(self, somewhere, posture_state, target_resolver, invalid_expected=False, posture_state_spec=None, affordance=None, base_object=None):
        actor = target_resolver(AnimationParticipant.ACTOR)
        if actor is not None and somewhere.age is not None and somewhere.age != actor.age.age_for_animation_cache:
            return Nowhere('ResolvePostureContext.resolve, Constraint age does not match actor age. Constraint: {}, Actor: {}', self, actor)
        if posture_state is None and posture_state_spec is None:
            return somewhere
        if posture_state is not None:
            if type(posture_state.body) != self._posture_manifest_entry.posture_type_specific:
                posture_type_family = self._posture_manifest_entry.posture_type_family
                if posture_type_family is None or not posture_state.body.is_same_posture_or_family(posture_type_family):
                    return Nowhere('ResolvePostureContext.resolve, Constraint postures do not match and are not in the same family. Posture state: {}, Constraint: {}', posture_state, self)
        elif posture_state_spec.body_target is None or isinstance(posture_state_spec.body_target, PostureSpecVariable):
            return somewhere
        surface_target = None
        if posture_state is not None:
            surface_target = posture_state.surface_target
            body = posture_state.body
        else:
            for entry in posture_state_spec.posture_manifest:
                posture_type = entry.posture_type_specific or entry.posture_type_family
                surface_target = entry.surface_target
                if surface_target is not None:
                    break
            if isinstance(surface_target, PostureSpecVariable):
                return somewhere
            else:
                body = DEFAULT
                if surface_target is None:
                    posture_specs = somewhere.get_posture_specs(None)
                    for (posture_spec_template, _, _) in posture_specs:
                        if posture_spec_template._at_surface:
                            if posture_state is not None:
                                return Nowhere('ResolvePostureContext.resolve, Posture State must have a surface to fulfill this constraint, Posture State: {}, Constraint: {}', posture_state, somewhere)
                            return somewhere
        if surface_target is None:
            posture_specs = somewhere.get_posture_specs(None)
            for (posture_spec_template, _, _) in posture_specs:
                if posture_spec_template._at_surface:
                    if posture_state is not None:
                        return Nowhere('ResolvePostureContext.resolve, Posture State must have a surface to fulfill this constraint, Posture State: {}, Constraint: {}', posture_state, somewhere)
                    return somewhere
        if posture_state_spec.body_target == PostureSpecVariable.BODY_TARGET_FILTERED:
            if posture_state.body_target is None:
                return somewhere
            target = posture_state.body_target
        else:
            target = target_resolver(AnimationParticipant.TARGET)
        if target is None and posture_state is None:
            return somewhere
        if self._create_target_name is not None:
            carry_target = GLOBAL_STUB_CREATE_TARGET
        elif self._carry_target_name is not None:
            carry_target = target_resolver(AnimationParticipant.CARRY_TARGET) or target
        else:
            carry_target = None
        targets = ()
        if target is not None:
            if not target.parts:
                targets = (target,)
            else:
                targets = (part for part in target.parts if affordance is None or part.supports_affordance(affordance))
        constraints = []
        for target_or_part in targets:
            if body is DEFAULT:
                body_target = posture_state_spec.body_target
                if body_target is not None and body_target.is_same_object_or_part(target_or_part):
                    body_posture = postures.create_posture(posture_type, actor, target_or_part, is_throwaway=True)
                    bodies = (body_posture,)
                else:
                    if body_target is None or not body_target.parts:
                        body_targets = (body_target,)
                    else:
                        body_targets = body_target.parts
                    bodies = []
                    for body_target in body_targets:
                        body_posture = postures.create_posture(posture_type, actor, body_target, is_throwaway=True)
                        bodies.append(body_posture)
            else:
                bodies = (body,)
            final_posture_state_spec = posture_state_spec if posture_state_spec is not None else somewhere.posture_state_spec
            if target_or_part.is_same_object_or_part(surface_target):
                surface_target = target_or_part
            for body_posture in bodies:
                constraint = RequiredSlot.create_required_slot_set(actor, target_or_part, carry_target, self._asm_key, self._state_name, self._actor_name, self._target_name, self._carry_target_name, self._create_target_name, self._override_manifests, self._required_slots, body_posture, surface_target, final_posture_state_spec, initial_state_name=self._initial_state, age=somewhere.age, invalid_expected=invalid_expected, base_object=base_object, base_object_name=self._base_object_name)
                if constraint.valid or posture_state is None:
                    return somewhere
                constraints.append(constraint)
        if constraints or not invalid_expected:
            logger.error("Tentative constraint resolution failure:\n            This is not expected and indicates a disagreement between\n            the information we have from Swing and tuning and what we\n            encountered when actually running the game, perhaps one of\n            the following:\n              * The ASM uses parameterized animation (string parameters determine\n                animation names) and the different possible Maya files\n                don't all have exactly the same namespaces and\n                constraints.\n              * One or more actors aren't set to valid objects.\n            ASM: {}".format(sims4.resources.get_debug_name(self._asm_key)))
        return create_constraint_set(constraints)

def get_constraints_excluding_unset_specific_postures(constraint_list):
    constraints = []
    for constraint in constraint_list:
        if constraint.posture_state_spec is None:
            constraints.append(constraint)
        else:
            valid_constraint = True
            for manifest_entry in constraint.posture_state_spec.posture_manifest:
                entry_posture_str = manifest_entry.specific
                if entry_posture_str is None:
                    pass
                else:
                    entry_posture = _get_posture_type_for_posture_name(entry_posture_str)
                    if entry_posture is UNSET:
                        valid_constraint = False
                        break
            if valid_constraint:
                constraints.append(constraint)
    return constraints

class TentativeIntersection(Constraint):
    INTERSECT_PREFERENCE = IntersectPreference.GEOMETRIC_PLUS

    def __init__(self, constraints, **kwargs):
        super().__init__(**kwargs)
        self_constraints = []
        for other_constraint in constraints:
            if isinstance(other_constraint, type(self)):
                self_constraints.extend(other_constraint._constraints)
            else:
                self_constraints.append(other_constraint)
        self._constraints = frozenset(self_constraints)

    def _copy(self, *args, _constraints=DEFAULT, **kwargs):
        if _constraints is DEFAULT:
            _constraints = frozenset(c._copy() for c in self._constraints)
        return super()._copy(*args, _constraints=_constraints, **kwargs)

    def _intersect(self, other_constraint):
        (early_out, kwargs) = self._intersect_kwargs(other_constraint)
        if early_out is not None:
            return early_out
        constraints = set(self._constraints)
        constraints.add(other_constraint)
        return self._copy(_constraints=frozenset(constraints), **kwargs)

    def _merge_delta_constraint(self, other_constraint):
        return self._intersect(other_constraint)

    def create_concrete_version(self, *args, **kwargs):
        return TentativeIntersection((constraint.create_concrete_version(*args, **kwargs) for constraint in self._constraints), debug_name=self._debug_name)

    @property
    def valid(self):
        for constraint in self._constraints:
            if not constraint.valid:
                return False
        return True

    @property
    def tentative(self):
        return True

    def apply_posture_state(self, *args, **kwargs):
        intersection = Anywhere()
        for other_constraint in self._constraints:
            other_constraint = other_constraint.apply_posture_state(*args, **kwargs)
            intersection = intersection.intersect(other_constraint)
        return intersection

    def remove_constraints_with_unset_postures(self):
        constraints = get_constraints_excluding_unset_specific_postures(self._constraints)
        return self._copy(_constraints=frozenset(constraints))

    def get_holster_version(self):
        constraints = []
        for constraint in self._constraints:
            constraints.append(constraint.get_holster_version())
        if self._posture_state_spec is None:
            holster_version = self._copy(_constraints=frozenset(constraints))
        else:
            holster_version = self._copy(_constraints=frozenset(constraints), _posture_state_spec=self._posture_state_spec.get_holster_version())
        return holster_version

    def estimate_distance_cache_key(self):
        return frozenset(constraint.estimate_distance_cache_key() for constraint in self._constraints)

class Somewhere(Constraint):
    INTERSECT_PREFERENCE = IntersectPreference.GEOMETRIC_PLUS

    def __init__(self, apply_posture_context, **kwargs):
        super().__init__(**kwargs)
        self._apply_posture_context = apply_posture_context
        if not isinstance(apply_posture_context, ResolvePostureContext):
            logger.warn('Non class init of somewhere')

    def _intersect(self, other_constraint):
        (early_out, kwargs) = self._intersect_kwargs(other_constraint)
        if early_out is not None:
            return early_out
        return TentativeIntersection((self, other_constraint))._copy(**kwargs)

    def _merge_delta_constraint(self, other_constraint):
        return self._intersect(other_constraint)

    @property
    def valid(self):
        return True

    @property
    def tentative(self):
        return True

    def apply_posture_state(self, posture_state, target_resolver, **kwargs):
        if self._posture_state_spec is not None:
            posture_state_spec = self._posture_state_spec.get_concrete_version(target_resolver)
        else:
            posture_state_spec = None
        result = self._apply_posture_context.resolve(self, posture_state, target_resolver, posture_state_spec=posture_state_spec, **kwargs)
        if result is self:
            return super().apply_posture_state(posture_state, target_resolver, **kwargs)
        return result.apply_posture_state(posture_state, target_resolver, **kwargs)

def create_constraint_set(constraint_list, invalid_constraints=None, debug_name=''):
    if not constraint_list:
        if invalid_constraints:
            invalid_constraints_set = frozenset(invalid_constraints)
            if len(invalid_constraints_set) == 1:
                return invalid_constraints[0]
            return _ConstraintSet(invalid_constraints_set, debug_name=debug_name)
        return Nowhere('create_constraint_set called with no constraints in list.')
    flattened_constraints = []
    for constraint in constraint_list:
        flattened_constraints.extend(constraint)
    if len(flattened_constraints) == 1:
        return flattened_constraints[0]
    similar_constraints = collections.defaultdict(list)
    for constraint in flattened_constraints:
        similar_constraints[frozendict(vars(constraint), _cost=0)].append(constraint)
    if len(similar_constraints) == 1:
        (_, constraints) = similar_constraints.popitem()
        return min(constraints, key=lambda c: c._cost)
    constraint_set = frozenset({min(constraints, key=lambda c: c._cost) for constraints in similar_constraints.values()})
    if len(constraint_set) == 1:
        return next(iter(constraint_set))
    return _ConstraintSet(constraint_set, debug_name=debug_name)

class _ConstraintSet(Constraint):
    INTERSECT_PREFERENCE = IntersectPreference.CONSTRAINT_SET
    _allow_geometry_intersections = True

    def __init__(self, constraints:frozenset, debug_name=''):
        if not isinstance(constraints, frozenset):
            raise TypeError('constraints must be in a frozenset')
        if len(constraints) <= 1:
            raise ValueError('There must be more than 1 constraint in a _ConstraintSet')
        self._constraints = constraints

    def _copy(self, **overrides):
        return create_constraint_set((constraint._copy(**overrides) for constraint in self._constraints), debug_name=self._debug_name)

    def __iter__(self):
        return iter(self._constraints)

    def __len__(self):
        return len(self._constraints)

    def apply(self, other_constraint):
        valid_constraints = []
        for constraint in self._constraints:
            applied_constraint = constraint.apply(other_constraint)
            if applied_constraint.valid:
                valid_constraints.append(applied_constraint)
        return create_constraint_set(valid_constraints)

    def get_geometry_for_point(self, pos):
        for constraint in self._constraints:
            geometry = constraint.get_geometry_for_point(pos)
            if geometry is not None:
                return geometry

    def get_geometry_text(self, indent_string):
        return_string = 'Set: \n'
        for constraint in self._constraints:
            return_string += '{}{}'.format(indent_string, constraint.get_geometry_text(indent_string + '    '))
        return_string += '{}EndSet\n'.format(indent_string)
        return return_string

    def get_multi_surface_version(self):
        for constraint in self:
            if not constraint.multi_surface:
                return self._copy(_multi_surface=True)
        return self

    def generate_forbid_small_intersections_constraint(self):
        return create_constraint_set([constraint.generate_forbid_small_intersections_constraint() for constraint in self._constraints])

    def get_single_surface_version(self, surface, **overrides):
        raise NotImplementedError

    def area(self):
        raise NotImplementedError()

    @property
    def cost(self):
        return min(constraint.cost for constraint in self._constraints)

    @property
    def create_jig_fn(self, *args, **kwargs):

        def create_all_jigs(*args, **kwargs):
            for constraint in self._constraints:
                fn = constraint.create_jig_fn
                if fn is not None:
                    fn(*args, **kwargs)

        return create_all_jigs

    @property
    def supports_swim(self):
        return any(sub_constraint.supports_swim for sub_constraint in self._constraints)

    def supports_mobile_posture(self, mobile_posture):
        return any(sub_constraint.supports_mobile_posture(mobile_posture) for sub_constraint in self._constraints)

    @property
    def average_position(self):
        count = 0
        total_position = sims4.math.Vector3.ZERO()
        for constraint in self:
            average_position = constraint.average_position
            if average_position is not None:
                count += 1
                total_position += average_position
        if count == 0:
            return
        return total_position/count

    @property
    def routing_positions(self):
        return sum((sub_constraint.routing_positions for sub_constraint in self), [])

    def constraint_cost(self, position, orientation):
        return min(constraint.constraint_cost(position, orientation) for constraint in self)

    def get_terrain_tags(self):
        total_terrain_tags = set()
        for constraint in self:
            constraint_terrain_tags = constraint.get_terrain_tags()
            if constraint_terrain_tags is None:
                return
            else:
                total_terrain_tags.union(constraint_terrain_tags)
                if total_terrain_tags:
                    return list(total_terrain_tags)
        if total_terrain_tags:
            return list(total_terrain_tags)

    def get_min_water_depth(self):
        current_value = sims4.math.MAX_FLOAT
        updated_value = False
        for constraint in self:
            constaint_value = constraint.get_min_water_depth()
            if constaint_value is None:
                return
            else:
                current_value = min(current_value, constaint_value)
                updated_value = True
                if updated_value:
                    return current_value
        if updated_value:
            return current_value

    def get_max_water_depth(self):
        current_value = -sims4.math.MAX_FLOAT
        updated_value = False
        for constraint in self:
            constaint_value = constraint.get_max_water_depth()
            if constaint_value is None:
                return
            else:
                current_value = max(current_value, constaint_value)
                updated_value = True
                if updated_value:
                    return current_value
        if updated_value:
            return current_value

    def get_posture_specs(self, resolver=None, interaction=None):
        posture_state_specs_to_constraints = collections.defaultdict(list)
        for constraint in self:
            if constraint.posture_state_spec is not None:
                key_carries = set()
                key_surfaces = set()
                key_surface_type = None
                for manifest_entry in constraint.posture_state_spec.posture_manifest:
                    entry_posture_str = manifest_entry.specific or manifest_entry.family
                    if entry_posture_str:
                        entry_posture = _get_posture_type_for_posture_name(entry_posture_str)
                        if entry_posture:
                            key_surface_type = tuple(sorted(entry_posture.surface_types))
                    if manifest_entry.carry_target is not None:
                        key_carries.add(manifest_entry.carry_target)
                    if manifest_entry.surface_target is not None:
                        key_surfaces.add(manifest_entry.surface_target)
                if constraint.posture_state_spec.slot_manifest:
                    for slot_manifest_entry in constraint.posture_state_spec.slot_manifest:
                        key_surfaces.add((slot_manifest_entry.actor, slot_manifest_entry.target))
                key_carries = frozenset(key_carries)
                key_surfaces = frozenset(key_surfaces)
                key = (key_carries, key_surfaces, key_surface_type)
            else:
                key = None
            posture_state_specs_to_constraints[key].append(constraint)
        results = set()
        for similar_constraints in posture_state_specs_to_constraints.values():
            similar_constraint_set = create_constraint_set(similar_constraints)
            for similar_constraint in similar_constraints:
                for (posture_spec, var_map, _) in similar_constraint.get_posture_specs(resolver, interaction=interaction):
                    results.add((posture_spec, var_map, similar_constraint_set))
        return list(results)

    def get_connectivity_handles(self, *args, **kwargs):
        return [handle for constraint in self._constraints for handle in constraint.get_connectivity_handles(*args, **kwargs)]

    def tested_intersect(self, other_constraint, test_constraint):
        valid_constraints = []
        invalid_constraints = []
        for self_sub_constraint in self:
            tested_intersect = self_sub_constraint.intersect(test_constraint)
            if tested_intersect.valid:
                for other_sub_constraint in other_constraint:
                    intersection = other_sub_constraint.intersect(self_sub_constraint)
                    if intersection.valid:
                        valid_constraints.append(intersection)
            elif self_sub_constraint.valid:
                valid_constraints.append(self_sub_constraint)
        return create_constraint_set(valid_constraints, invalid_constraints=invalid_constraints, debug_name=self._debug_name)

    def _intersect(self, other_constraint):
        valid_constraints = []
        invalid_constraints = []
        for (self_sub_constraint, other_sub_constraint) in itertools.product(self, other_constraint):
            intersection = other_sub_constraint.intersect(self_sub_constraint)
            if intersection.valid:
                valid_constraints.append(intersection)
        return create_constraint_set(valid_constraints, invalid_constraints=invalid_constraints, debug_name=self._debug_name)

    def _merge_delta_constraint(self, other_constraint):
        valid_constraints = [constraint._copy() for constraint in self._constraints]
        for constraint in other_constraint:
            constraint = constraint._copy()
            for self_constraint in valid_constraints:
                merged_constraint = constraint.merge_delta_constraint(self_constraint)
                if merged_constraint.valid:
                    if merged_constraint != constraint:
                        valid_constraints.remove(self_constraint)
                        valid_constraints.append(merged_constraint)
                    break
            valid_constraints.append(constraint)
        return create_constraint_set(valid_constraints, debug_name=self._debug_name)

    def get_holster_version(self):
        holster_constraints = []
        for constraint in self._constraints:
            holster_constraint = constraint.get_holster_version()
            holster_constraints.append(holster_constraint)
        return create_constraint_set(holster_constraints, debug_name=self._debug_name)

    def generate_constraint_with_slot_info(self, actor, slot_target, chosen_slot):
        return create_constraint_set((constraint.generate_constraint_with_slot_info(actor, slot_target, chosen_slot) for constraint in self._constraints), debug_name=self._debug_name)

    @property
    def tentative(self):
        return any(constraint.tentative for constraint in self._constraints)

    def apply_posture_state(self, *args, **kwargs):
        valid_constraints = []
        invalid_constraints = []
        for constraint in self._constraints:
            new_constraint = constraint.apply_posture_state(*args, **kwargs)
            if new_constraint.valid:
                valid_constraints.append(new_constraint)
        return create_constraint_set(valid_constraints, invalid_constraints=invalid_constraints, debug_name=self._debug_name)

    def remove_constraints_with_unset_postures(self):
        constraints = get_constraints_excluding_unset_specific_postures(self._constraints)
        return create_constraint_set(constraints, debug_name=self._debug_name)

    def create_concrete_version(self, *args, **kwargs):
        return create_constraint_set((constraint.create_concrete_version(*args, **kwargs) for constraint in self._constraints), debug_name=self._debug_name)

    @property
    def locked_params(self):
        return {}

    @property
    def valid(self):
        for constraint in self._constraints:
            if constraint.valid:
                return True
        return False

    def __repr__(self):
        return 'ConstraintSet(...)'

    def get_target_object_filters(self):
        filter_set = set()
        for constraint in self:
            filter_set |= constraint.get_target_object_filters()
        return filter_set

    def estimate_distance_cache_key(self):
        return frozenset(constraint.estimate_distance_cache_key() for constraint in self)

class SmallAreaConstraint(Constraint):

    def __init__(self, *args, allow_small_intersections=True, **kwargs):
        super().__init__(*args, allow_small_intersections=True, **kwargs)

    def generate_forbid_small_intersections_constraint(self):
        return self

def AbsoluteFacing(angle, facing_range=None, debug_name=DEFAULT, **kwargs):
    if debug_name is DEFAULT:
        debug_name = 'AbsoluteFacing'
    if facing_range is None:
        facing_range = Constraint.DEFAULT_FACING_RANGE
    interval = sims4.geometry.interval_from_facing_angle(angle, facing_range)
    abs_facing_range = sims4.geometry.AbsoluteOrientationRange(interval)
    facing_geometry = sims4.geometry.RestrictedPolygon(None, (abs_facing_range,))
    return Constraint(debug_name=debug_name, geometry=facing_geometry, **kwargs)

def Facing(target=None, facing_range=None, inner_radius=None, target_position=DEFAULT, target_forward=DEFAULT, debug_name=DEFAULT, **kwargs):
    if debug_name is DEFAULT:
        debug_name = 'Facing'
    if target_position is DEFAULT:
        target_position = target.intended_position
    if facing_range is None:
        facing_range = Constraint.DEFAULT_FACING_RANGE
    if inner_radius is None or inner_radius <= sims4.math.EPSILON:
        relative_facing_range = sims4.geometry.RelativeFacingRange(target_position, facing_range)
    else:
        relative_facing_range = sims4.geometry.RelativeFacingWithCircle(target_position, facing_range, inner_radius)
    facing_geometry = sims4.geometry.RestrictedPolygon(None, (relative_facing_range,))
    return Constraint(debug_name=debug_name, geometry=facing_geometry, **kwargs)

class TunedFacing:

    def __init__(self, range, inner_radius, subroot_index):
        self._facing_range = range
        self._inner_radius = inner_radius
        self._subroot_index = subroot_index

    def create_constraint(self, sim, target=None, target_position=DEFAULT, **kwargs):
        if target is not None and target.is_in_inventory():
            if target.is_in_sim_inventory():
                return Anywhere()
            logger.error('Attempt to create a tuned Facing constraint on a target: {} which is in the inventory.  This will not work correctly.', target, owner='mduke')
            return Nowhere('Cannot create facing constraint for an object in an inventory: {}', target)
        if target is not None and self._subroot_index is not None:
            if target.is_part:
                target = target.part_owner
            part = target.get_part_by_index(self._subroot_index)
            if part is None:
                logger.error('Attempt to create a tuned Facing constraint on a target: {} but could not find subroot {}.', target, self._subroot_index, owner='jdimailig')
                return Nowhere('Cannot create facing constraint for subroot {}: {}', self._subroot_index, target)
            target_position = part.transform.translation
        elif target is None and target_position is DEFAULT:
            return Anywhere()
        return Facing(target, facing_range=self._facing_range, inner_radius=self._inner_radius, target_position=target_position, **kwargs)

class TunableFacing(TunableSingletonFactory):
    FACTORY_TYPE = TunedFacing

    def __init__(self, description=None, **kwargs):
        super().__init__(range=TunableAngle(description='\n                The size of the angle-range that sims should use when determining facing constraints.\n                ', default=sims4.math.PI/2), inner_radius=Tunable(description="\n                A radius around the center of the constraint that defines an area in which the Sim's facing is unrestricted.\n                ", tunable_type=float, default=0.0), subroot_index=OptionalTunable(description='\n                An optional subroot to use for facing.\n                ', tunable=Tunable(tunable_type=int, default=0)), description=description, **kwargs)

class TunedFireOrLotFacingConstraint(TunedFacing):

    def create_constraint(self, sim, target=None, routing_surface=DEFAULT, **kwargs):
        zone = services.current_zone()
        if zone is None:
            logger.error('Attempting to create Fire or Lot Facing constraint when zone is None.', owner='rmccord')
            return Nowhere('TunedFireOrLotFacingConstraint.create_constraint, zone is None')
        target_position = None
        fire_service = services.get_fire_service()
        if fire_service is not None:
            target_position = fire_service.get_fire_position()
        if target_position is None:
            active_lot = zone.lot
            if active_lot is None:
                logger.error('Attempting to create Fire or Lot Facing constraint when active lot is None.', owner='rmccord')
                return Nowhere('TunedFireOrLotFacingConstraint.create_constraint, active_lot is None')
            target_position = active_lot.center
        if routing_surface is DEFAULT:
            routing_surface = routing.SurfaceIdentifier(zone.id, 0, routing.SurfaceType.SURFACETYPE_WORLD)
        return super().create_constraint(sim, target=target, routing_surface=routing_surface, target_position=target_position, **kwargs)

class TunableFireOrLotFacingConstraint(TunableFacing):
    FACTORY_TYPE = TunedFireOrLotFacingConstraint

    def __init__(self, callback=None, **kwargs):
        super().__init__(description='\n            A tunable type for creating a constraint that faces a fire on the lot or the lot center.\n            ', **kwargs)

class TunedLineOfSight:

    def __init__(self, temporary_los, multi_surface):
        self._temporary_los = temporary_los
        self._multi_surface = multi_surface

    def create_constraint(self, sim, target, target_position=DEFAULT, **kwargs):
        if isinstance(target, StubActor):
            return Anywhere()
        if target is None:
            logger.warn('Attempting to create a LineOfSight constraint on a None target. This is expected if the target has been destroyed.', owner='epanero')
            return ANYWHERE
        if target.is_in_inventory():
            logger.error('Attempt to tune a LineOfSight constraint on a target {} that is in the inventory. This will not work.', target, owner='mduke')
            return Nowhere('Cannot create a line of sight constraint for an object in an inventory: {}', target)
        if target_position is DEFAULT:
            target_position = target.intended_position
            target_forward = target.intended_forward
            target_routing_surface = target.intended_routing_surface
        else:
            target_forward = target.forward
            target_routing_surface = target.routing_surface
        if not isinstance(target_routing_surface, routing.SurfaceIdentifier):
            logger.error('Target {} does not have a valid routing surface {}, type {}.', target, target_routing_surface, type(target_routing_surface), owner='tastle')
            return Nowhere('Line of sight target does not have a valid routing surface: {}', target)
        if target.lineofsight_component is None:
            if self._temporary_los is not None:
                from objects.components.line_of_sight_component import LineOfSight
                los = LineOfSight(self._temporary_los.max_line_of_sight_radius, self._temporary_los.map_divisions, self._temporary_los.simplification_ratio, self._temporary_los.boundary_epsilon, multi_surface=self._multi_surface, debug_str_data=('Tuned LOS Constraint, Target: {}', target))
                position = target_position + target_forward*self._temporary_los.facing_offset
                los.generate(position, target_routing_surface)
                return los.constraint
            logger.error('{} has no LOS and no temporary LOS was specified', target, owner='epanero')
            return Nowhere('{} has no LOS and no temporary LOS was specified', target)
        if target.is_sim and target.lineofsight_component is not None:
            target.refresh_los_constraint(target_position=target_position)
        if self._multi_surface:
            return target.lineofsight_component.multi_surface_constraint
        return target.lineofsight_component.constraint

class TunableLineOfSightData(TunableTuple):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, facing_offset=Tunable(description='\n                The LOS origin is offset from the object origin by this amount\n                (mainly to avoid intersecting walls).\n                ', tunable_type=float, default=0.1), max_line_of_sight_radius=Tunable(description='\n                The maximum possible distance from this object than an\n                interaction can reach.\n                ', tunable_type=float, default=10), map_divisions=Tunable(description='\n                The number of points around the object to check collision from.\n                More points means higher accuracy.\n                ', tunable_type=int, default=30), simplification_ratio=Tunable(description='\n                A factor determining how much to combine edges in the line of\n                sight polygon.\n                ', tunable_type=float, default=0.35), boundary_epsilon=Tunable(description='\n                The LOS origin is allowed to be outside of the boundary by this\n                amount.\n                ', tunable_type=float, default=0.01), **kwargs)

class TunableLineOfSight(TunableSingletonFactory):
    FACTORY_TYPE = TunedLineOfSight

    def __init__(self, **kwargs):
        super().__init__(temporary_los=OptionalTunable(description="\n                 If enabled, a Line of Sight component will be temporarily created\n                 when constraints are needed. This should be used if the affordance\n                 requires LOS on an object that doesn't have an LOS component (i.e. a\n                 Sim needs to see another Sim WooHoo to play the jealousy reactions\n                 but Sims don't have LoS components.)\n                 ", tunable=TunableLineOfSightData()), multi_surface=Tunable(description='\n                If enabled, this constraint will be considered for multiple surfaces.\n                \n                Example: You want a circle\n                constraint that can be both inside\n                and outside of a pool.\n                ', tunable_type=bool, default=False), **kwargs)

class TunedSpawnPoint(ZoneConstraintMixin):

    def __init__(self, tags=None, spawn_point_request_reason=False, use_lot_id=True):
        super().__init__()
        self.tags = tags
        self.spawn_point_request_reason = spawn_point_request_reason
        self.use_lot_id = use_lot_id

    def create_zone_constraint(self, sim, target=None, lot_id=None, **kwargs):
        return services.current_zone().get_spawn_points_constraint(sim_info=sim.sim_info, lot_id=lot_id if self.use_lot_id else None, sim_spawner_tags=self.tags, spawn_point_request_reason=self.spawn_point_request_reason)

class TunableSpawnPoint(TunableSingletonFactory):
    FACTORY_TYPE = TunedSpawnPoint

    def __init__(self, description='\n        A tunable type for creating Spawn Point constraints. If no Tags are\n        tuned, then the system will use whatever information is saved on the\n        sim_info. The saved info will rely on information about where the Sim\n        spawned from.\n        ', **kwargs):
        super().__init__(tags=OptionalTunable(tunable=TunableSet(tunable=TunableEnumWithFilter(tunable_type=Tag, default=Tag.INVALID, filter_prefixes=('Spawn',)), minlength=1), enabled_by_default=True, disabled_name='Use_Saved_Spawn_Point_Options', enabled_name='Spawn_Point_Tags', description=description), spawn_point_request_reason=TunableEnumEntry(description='\n                The reason why we want the spawn point. Certain spawn points are\n                only available for specific reasons, such as specific spawn\n                points for leaving or for spawning at.\n                ', tunable_type=SpawnPointRequestReason, default=SpawnPointRequestReason.DEFAULT), use_lot_id=Tunable(description='\n                If checked then we will use the current lot id to limit spawn\n                points that are linked to lots to the current lot.  Otherwise\n                we will get spawn points of the given type that are\n                potenially not linked to the current lot.\n                ', tunable_type=bool, default=True), **kwargs)

def create_animation_constraint_set(constraints, asm_name, state_name, **kwargs):
    debug_name = 'AnimationConstraint({}.{})'.format(asm_name, state_name)
    return create_constraint_set(constraints, debug_name=debug_name)

def _create_slot_manifest(boundary_condition, required_slots, resolve_actor_name_fn):
    slot_manifest = SlotManifest()
    if required_slots is None:
        for (child_name, parent_name, bone_name_hash) in boundary_condition.required_slots:
            entry = SlotManifestEntry(child_name, parent_name, bone_name_hash)
            entry = entry.apply_actor_map(resolve_actor_name_fn)
            slot_manifest.add(entry)
    else:
        for (child_name, parent_name, slot_type) in required_slots:
            entry = SlotManifestEntry(child_name, parent_name, slot_type.bone_name_hash)
            entry = entry.apply_actor_map(resolve_actor_name_fn)
            slot_manifest.add(entry)
    return slot_manifest

def _resolve_slot_and_surface_constraints(boundary_condition, animation_overrides, target, target_name, carry_target, carry_target_name, surface_target, surface_target_name, slot_manifest):
    surface = None
    slot_manifest_entry = None
    if animation_overrides is None or not animation_overrides.required_slots:
        for (child_id, parent_id, bone_name_hash) in boundary_condition.required_slots:
            if target is not None and child_id == target.id:
                target_var = PostureSpecVariable.INTERACTION_TARGET
            elif carry_target is not None and child_id == carry_target.id:
                target_var = PostureSpecVariable.CARRY_TARGET
            else:
                target_var = None
            slot_type = objects.slots.get_slot_type_for_bone_name_hash(bone_name_hash)
            if slot_type is None:
                msg = 'Could not find tuning matching a surface slot specified in Maya:'
                bone_name = animation.animation_utils.unhash_bone_name(bone_name_hash)
                if bone_name:
                    msg += " the bone named '{}' does not have a SlotType defined.".format(bone_name)
                else:
                    msg += " a bone whose name hash is '{:#x}' does not have a SlotType defined.".format(bone_name_hash)
                if api_config.native_supports_new_api('native.animation.arb.BoundaryConditionInfo'):
                    msg += ' (Clip is in ASM {})'.format(boundary_condition.debug_info)
                logger.error(msg)
            else:
                for entry in slot_manifest:
                    if slot_type in entry.slot_types:
                        slot_manifest_entry = entry
                        break
                if slot_type is not None:
                    slot_type = PostureSpecVariable.SLOT
                if target is not None and parent_id == target.id:
                    surface_var = PostureSpecVariable.INTERACTION_TARGET
                elif surface_target is not None and parent_id == surface_target.id:
                    surface_var = PostureSpecVariable.SURFACE_TARGET
                else:
                    surface_var = PostureSpecVariable.ANYTHING
                surface = PostureAspectSurface((surface_var, slot_type, target_var))
                break
    else:
        for (child_name, parent_name, slot_type) in animation_overrides.required_slots:
            if child_name == target_name:
                target_var = PostureSpecVariable.INTERACTION_TARGET
            elif child_name == carry_target_name:
                target_var = PostureSpecVariable.CARRY_TARGET
            else:
                target_var = None
            if parent_name == target_name:
                surface_var = PostureSpecVariable.INTERACTION_TARGET
            elif parent_name == surface_target_name:
                surface_var = PostureSpecVariable.SURFACE_TARGET
            else:
                surface_var = PostureSpecVariable.ANYTHING
            for entry in slot_manifest:
                if slot_type in entry.slot_types:
                    slot_manifest_entry = entry
                    break
            if slot_type is not None:
                slot_type = PostureSpecVariable.SLOT
            surface = PostureAspectSurface((surface_var, slot_type, target_var))
            break
    return (surface, slot_manifest_entry)

def create_animation_constraint(asm_key, actor_name, target_name, carry_target_name, create_target_name, initial_state, begin_states, end_states, animation_overrides, base_object_name=None):
    constraints = []
    tentative_posture_spec_var_pairs = set()
    concrete_posture_spec_var_pairs = set()
    age_name_lower_to_enum = {age.animation_age_param: age for age in sims.sim_info_types.Age.get_ages_for_animation_cache()}
    state_name = begin_states[0] if begin_states else end_states[0]
    animation_context = get_throwaway_animation_context()
    asm = Asm(asm_key, animation_context, posture_manifest_overrides=animation_overrides.manifests)
    posture_manifest = asm.get_supported_postures_for_actor(actor_name).get_constraint_version()
    for posture_manifest_entry in posture_manifest:
        if not posture_manifest_entry.posture_types:
            logger.error('Manifest entry has no posture types: {}.{}.', asm.name, posture_manifest_entry)
        else:
            posture_type = posture_manifest_entry.posture_types[0]
            for species in posture_type.get_animation_species():
                global_stub_actor = get_global_stub_actor(species)
                actor_name_to_animation_participant_map = {}
                actor_name_to_stub_actor_map = {}

                def add_mapping(animation_participant, tuned_name, default_stub_actor):
                    if tuned_name is None:
                        return
                    if tuned_name in actor_name_to_stub_actor_map:
                        return actor_name_to_stub_actor_map[tuned_name]
                    actor_name_to_animation_participant_map[tuned_name] = animation_participant
                    actor_name_to_stub_actor_map[tuned_name] = default_stub_actor
                    return default_stub_actor

                surface_target_name = posture_manifest_entry.surface_target
                asm = Asm(asm_key, animation_context, posture_manifest_overrides=animation_overrides.manifests)
                posture = posture_type(global_stub_actor, GLOBAL_STUB_CONTAINER, PostureTrack.BODY, animation_context=animation_context)
                target = add_mapping(AnimationParticipant.TARGET, target_name, GLOBAL_STUB_TARGET)
                actor = add_mapping(AnimationParticipant.ACTOR, actor_name, global_stub_actor)
                container_target = add_mapping(AnimationParticipant.CONTAINER, posture.get_target_name(), GLOBAL_STUB_CONTAINER)
                surface_target = add_mapping(AnimationParticipant.SURFACE, surface_target_name, GLOBAL_STUB_SURFACE)
                carry_target = add_mapping(AnimationParticipant.CARRY_TARGET, carry_target_name, GLOBAL_STUB_CARRY_TARGET)
                create_target = add_mapping(AnimationParticipant.CREATE_TARGET, create_target_name, GLOBAL_STUB_CREATE_TARGET)
                base_object_target = add_mapping(AnimationParticipant.BASE_OBJECT, base_object_name, GLOBAL_STUB_BASE_OBJECT)
                last_state = begin_states[-1] if begin_states else end_states[-1]
                for (prop_name, definition_id) in asm.get_props_in_traversal(initial_state or 'entry', last_state).items():
                    prop_definition = services.definition_manager().get(definition_id, get_fallback_definition_id=False)
                    add_mapping(None, prop_name, prop_definition)
                actor = actor or global_stub_actor
                container_target = container_target or GLOBAL_STUB_CONTAINER
                base_object_target = base_object_target or GLOBAL_STUB_BASE_OBJECT
                base_object_or_container_target = base_object_target if base_object_name is not None else container_target
                if posture.multi_sim:
                    posture_actor_name = posture_type.get_actor_name(sim=actor, target=container_target)
                    if actor_name == posture_actor_name:
                        is_master = True
                    else:
                        is_master = False
                    posture = posture_type(actor, base_object_or_container_target, PostureTrack.BODY, master=is_master, animation_context=animation_context)
                    target_posture = posture_type(target or GLOBAL_STUB_TARGET, base_object_or_container_target, PostureTrack.BODY, master=not is_master, animation_context=animation_context)
                    posture.linked_posture = target_posture
                else:
                    posture = posture_type(actor, base_object_or_container_target, PostureTrack.BODY, animation_context=animation_context)
                if surface_target_name is None:
                    if posture_manifest_entry.allow_surface:
                        surface = None
                    else:
                        surface = PostureAspectSurface((None, None, None))
                else:
                    surface = PostureAspectSurface((PostureSpecVariable.SURFACE_TARGET, None, None))
                result = posture.setup_asm_interaction(asm, actor, target, actor_name, target_name, carry_target=carry_target, carry_target_name=carry_target_name, surface_target=surface_target, invalid_expected=True, base_object=base_object_target, base_object_name=base_object_name)
                if not result:
                    logger.error('Could not set up AnimationConstraint asm with stub actors: {}, {}', asm.name, result, owner='rmccord')
                else:
                    if create_target is not None:
                        asm.set_actor(create_target_name, create_target)
                    body_target_var = PostureSpecVariable.ANYTHING
                    if target_name == posture.get_target_name():
                        body_target_var = PostureSpecVariable.INTERACTION_TARGET
                    try:
                        actor.posture = posture
                        containment_slot_to_slot_data = asm.get_boundary_conditions_list(actor, state_name, from_state_name=initial_state)
                    finally:
                        actor.posture = None
                    if not (target_name is not None and containment_slot_to_slot_data):
                        bound_posture_manifest_entry = posture_manifest_entry.apply_actor_map(actor_name_to_animation_participant_map.get)
                        bound_posture_manifest_entry = bound_posture_manifest_entry.intern()
                        if animation_overrides is not None and animation_overrides.required_slots:
                            slot_manifest = _create_slot_manifest(None, animation_overrides.required_slots, actor_name_to_animation_participant_map.get)
                        else:
                            slot_manifest = SlotManifest()
                        slot_manifest = slot_manifest.intern()
                        posture_manifest = PostureManifest((bound_posture_manifest_entry,))
                        posture_manifest = posture_manifest.intern()
                        posture_state_spec = postures.posture_state_spec.PostureStateSpec(posture_manifest, slot_manifest, body_target_var)
                        entry = (bound_posture_manifest_entry, posture_state_spec, None)
                        concrete_posture_spec_var_pairs.add(entry)
                    else:
                        boundary_conditions = []
                        for (_, slot_data) in containment_slot_to_slot_data:
                            for (boundary_condition, locked_params_list) in slot_data:
                                for locked_params in locked_params_list:
                                    if locked_params is not None:
                                        age_param = None
                                        if ('age', actor_name) in locked_params:
                                            age_str = locked_params[('age', actor_name)]
                                            if age_str in age_name_lower_to_enum:
                                                age_param = age_name_lower_to_enum[age_str]
                                        boundary_conditions.append((boundary_condition, age_param))
                        for (boundary_condition, age) in boundary_conditions:
                            tentative = False
                            bc_body_target_var = body_target_var
                            if target_name is not None or surface_target is not None:
                                relative_object_name = boundary_condition.pre_condition_reference_object_name or boundary_condition.post_condition_reference_object_name
                                if relative_object_name is not None:
                                    tentative = posture_type.unconstrained
                                    if relative_object_name == target_name:
                                        bc_body_target_var = PostureSpecVariable.INTERACTION_TARGET
                            required_slots = None
                            if animation_overrides is not None:
                                required_slots = animation_overrides.required_slots
                            slot_manifest = _create_slot_manifest(boundary_condition, required_slots, actor_name_to_animation_participant_map.get)
                            slot_manifest = slot_manifest.intern()
                            (surface_from_constraint, _) = _resolve_slot_and_surface_constraints(boundary_condition, animation_overrides, target, target_name, carry_target, carry_target_name, surface_target, surface_target_name, slot_manifest)
                            surface = surface_from_constraint or surface
                            bound_posture_manifest_entry = posture_manifest_entry.apply_actor_map(actor_name_to_animation_participant_map.get)
                            bound_posture_manifest_entry = bound_posture_manifest_entry.intern()
                            posture_manifest = PostureManifest((bound_posture_manifest_entry,))
                            posture_manifest = posture_manifest.intern()
                            posture_state_spec = postures.posture_state_spec.PostureStateSpec(posture_manifest, slot_manifest, bc_body_target_var)
                            entry = (bound_posture_manifest_entry, posture_state_spec, age)
                            if tentative:
                                tentative_posture_spec_var_pairs.add(entry)
                            else:
                                concrete_posture_spec_var_pairs.add(entry)
    if tentative_posture_spec_var_pairs:
        for (posture_manifest_entry, posture_state_spec, age_param) in tentative_posture_spec_var_pairs:
            override_manifests = None
            required_slots = None
            if animation_overrides is not None:
                override_manifests = animation_overrides.manifests
                required_slots = animation_overrides.required_slots
            resolve_context = ResolvePostureContext(posture_manifest_entry, create_target_name, asm_key, state_name, actor_name, target_name, carry_target_name, override_manifests, required_slots, initial_state, base_object_name)
            debug_name = None
            constraint = Somewhere(resolve_context, debug_name=debug_name, posture_state_spec=posture_state_spec, age=age_param)
            constraints.append(constraint)
    for (posture_manifest_entry, posture_state_spec, age_param) in concrete_posture_spec_var_pairs:
        debug_name = None
        constraint = Constraint(debug_name=debug_name, posture_state_spec=posture_state_spec, age=age_param)
        constraints.append(constraint)
    if not constraints:
        return
    families = set()
    for constraint in constraints:
        for entry in constraint.posture_state_spec.posture_manifest:
            if not entry.specific:
                families.add(entry.family)
    nonredundant_constraints = []
    for constraint in constraints:
        if any(entry.family or entry.posture_type_specific.family_name not in families for entry in constraint.posture_state_spec.posture_manifest):
            nonredundant_constraints.append(constraint)
    return create_animation_constraint_set(nonredundant_constraints, asm.name, state_name)

class RequiredSlot:

    @staticmethod
    def _setup_asm(sim, target, asm, posture, *args, **kwargs):
        if posture is None:
            raise RuntimeError('Attempt to create a RequiredSlot with no posture.')
        if asm is posture.asm:
            result = posture.setup_asm_posture(asm, sim, target)
            if not result:
                logger.debug('Failed to setup posture ASM {} on posture {} for RequiredSlotSingle constraint. {}', asm, posture, result)
            return result
        result = posture.setup_asm_interaction(asm, sim, target, *args, **kwargs)
        if not result:
            logger.debug('Failed to setup interaction ASM {} with posture {} for RequiredSlotSingle constraint. {}', asm, posture, result)
        return result

    @staticmethod
    def _get_and_setup_asm_for_required_slot_set(asm_key, sim, target, actor_name, target_name, posture, posture_manifest_overrides=None, asm=None, **kwargs):
        anim_context = get_throwaway_animation_context()
        if asm is None:
            asm = Asm(asm_key, anim_context, posture_manifest_overrides=posture_manifest_overrides)
        result = RequiredSlot._setup_asm(sim, target, asm, posture, actor_name, target_name, **kwargs)
        if not result:
            logger.debug('Failed to setup ASM {} for RequiredSlotSingle constraint. {}', asm, result)
            return
        return asm

    @staticmethod
    def _build_relative_slot_data(asm, sim, target, actor_name, target_name, posture, state_name, exit_slot_start_state=None, exit_slot_end_state='exit', locked_params=frozendict(), initial_state_name=DEFAULT, base_object_name=None):
        locked_params += posture.default_animation_params
        anim_overrides_target = target.get_anim_overrides(target_name)
        if anim_overrides_target.params:
            locked_params += anim_overrides_target.params
        containment_slot_to_slot_data_entry = asm.get_boundary_conditions_list(sim, state_name, locked_params=locked_params, from_state_name=initial_state_name, posture=posture, base_object_name=base_object_name)
        if anim_overrides_target is not None and exit_slot_start_state is not None:
            containment_slot_to_slot_data_exit = asm.get_boundary_conditions_list(sim, exit_slot_end_state, locked_params=locked_params, from_state_name=exit_slot_start_state, entry=False, posture=posture, base_object_name=base_object_name)
        else:
            containment_slot_to_slot_data_exit = ()
        return (containment_slot_to_slot_data_entry, containment_slot_to_slot_data_exit)

    @staticmethod
    def _build_posture_state_spec_for_boundary_condition(boundary_condition, asm, sim, target, carry_target, surface_target, actor_name, target_name, carry_target_name, create_target_name, posture, state_name, posture_state_spec, required_slots):
        object_manager = services.object_manager()
        if posture is not None and posture.asm == asm:
            supported_postures = asm.provided_postures
        elif posture_state_spec is None:
            supported_postures = asm.get_supported_postures_for_actor(actor_name)
        else:
            supported_postures = posture_state_spec.posture_manifest
        matching_supported_postures = PostureManifest()
        body_target = posture.target if posture is not None else target
        surface_target = posture.surface_target if surface_target is DEFAULT else surface_target
        surface_target_name = None
        if posture is not None:
            for posture_manifest_entry in supported_postures:
                for body_type in posture_manifest_entry.posture_types:
                    if isinstance(posture, body_type):
                        matching_supported_postures.add(posture_manifest_entry)
                surface_target_name = posture_manifest_entry.surface_target
        actor_name_to_game_object_map = {}
        valid_relative_object_ids = set()

        def add_actor_map(name, obj, is_valid_relative_object):
            if name is None or obj is None:
                return
            actor_name_to_game_object_map[name] = obj
            if name not in actor_name_to_game_object_map and is_valid_relative_object:
                valid_relative_object_ids.add(obj.id)

        add_actor_map(target_name, target, True)
        add_actor_map(actor_name, sim, False)
        if posture is not None:
            add_actor_map(posture.get_target_name(), posture.target, True)
        add_actor_map(carry_target_name, carry_target, False)
        add_actor_map(create_target_name, AnimationParticipant.CREATE_TARGET, False)
        add_actor_map(surface_target_name, surface_target, True)
        actor_name_to_game_object_map[AnimationParticipant.ACTOR] = sim
        actor_name_to_game_object_map[AnimationParticipant.TARGET] = target
        actor_name_to_game_object_map[AnimationParticipant.CONTAINER] = posture.target
        actor_name_to_game_object_map[AnimationParticipant.CARRY_TARGET] = carry_target
        actor_name_to_game_object_map[AnimationParticipant.SURFACE] = surface_target
        actor_name_to_game_object_map[AnimationParticipant.BASE_OBJECT] = posture.target
        matching_supported_postures = matching_supported_postures.apply_actor_map(actor_name_to_game_object_map.get)
        relative_object_id = boundary_condition.get_relative_object_id(asm)
        relative_object = object_manager.get(relative_object_id)
        if relative_object is not None and relative_object.parent is sim:
            raise PostureGraphBoundaryConditionError('\n                    [bhill/maxr] ASM is trying to generate a bogus required slot\n                    constraint relative to {}: {}.{} Most likely this means the\n                    base object for this clip was set incorrectly in Maya.\n                    Contact an animator to fix this or Max R.\n                    '.format(relative_object, asm.name, state_name))
        if posture_state_spec is not None:
            slot_manifest = posture_state_spec.slot_manifest
        else:
            slot_manifest = _create_slot_manifest(boundary_condition, required_slots, actor_name_to_game_object_map.get)
        posture_state_spec = postures.posture_state_spec.PostureStateSpec(PostureManifest(matching_supported_postures), slot_manifest, body_target)
        return posture_state_spec

    @staticmethod
    def _build_required_slot_set_from_relative_data(asm, asm_key, sim, target, posture, actor_name, target_name, state_name, containment_slot_to_slot_data_entry, containment_slot_to_slot_data_exit, get_posture_state_spec_fn, age=None, invalid_expected=False):
        slot_constraints = []
        for (_, slots_to_params_entry) in containment_slot_to_slot_data_entry:
            posture_state_spec = None
            slots_to_params_entry_absolute = []
            containment_transform = None
            for (boundary_condition_entry, param_sequences_entry) in slots_to_params_entry:
                if target.is_part:
                    for param_sequence in param_sequences_entry:
                        subroot_parameter = param_sequence.get('subroot')
                        if subroot_parameter is None or subroot_parameter == target.part_suffix:
                            break
                else:
                    relative_obj_id = boundary_condition_entry.get_relative_object_id(asm)
                    if relative_obj_id is not None and target.id != relative_obj_id:
                        if not invalid_expected:
                            logger.callstack('Unexpected relative object in required slot for {}: {}', asm, boundary_condition_entry.pre_condition_reference_object_name or boundary_condition_entry.post_condition_reference_object_name, level=sims4.log.LEVEL_ERROR)
                            (routing_transform_entry, containment_transform, _, reference_joint_exit) = boundary_condition_entry.get_transforms(asm, target)
                            slots_to_params_entry_absolute.append((routing_transform_entry, reference_joint_exit, param_sequences_entry))
                            if posture_state_spec is None and get_posture_state_spec_fn is not None:
                                posture_state_spec = get_posture_state_spec_fn(boundary_condition_entry)
                    else:
                        (routing_transform_entry, containment_transform, _, reference_joint_exit) = boundary_condition_entry.get_transforms(asm, target)
                        slots_to_params_entry_absolute.append((routing_transform_entry, reference_joint_exit, param_sequences_entry))
                        if posture_state_spec is None and get_posture_state_spec_fn is not None:
                            posture_state_spec = get_posture_state_spec_fn(boundary_condition_entry)
            if containment_transform is None:
                pass
            else:
                containment_transform_exit = None
                slots_to_params_exit_absolute = []
                if containment_slot_to_slot_data_exit:
                    for (_, slots_to_params_exit) in containment_slot_to_slot_data_exit:
                        for (boundary_condition_exit, param_sequences_exit) in slots_to_params_exit:
                            if target.is_part:
                                for param_sequence in param_sequences_exit:
                                    subroot_parameter = param_sequence.get('subroot')
                                    if subroot_parameter is None or subroot_parameter == target.part_suffix:
                                        break
                            else:
                                relative_obj_id = boundary_condition_exit.get_relative_object_id(asm)
                                if relative_obj_id is not None and target.id != relative_obj_id:
                                    logger.callstack('Unexpected relative object in required slot for {}: {}', asm, boundary_condition_exit.pre_condition_reference_object_name or boundary_condition_exit.post_condition_reference_object_name, level=sims4.log.LEVEL_ERROR)
                                else:
                                    (containment_transform_exit, routing_transform_exit, reference_joint_entry, _) = boundary_condition_exit.get_transforms(asm, target)
                                    slots_to_params_exit_absolute.append((routing_transform_exit, reference_joint_entry, param_sequences_exit))
                slot_constraint = RequiredSlotSingle(sim, target, asm, asm_key, posture, actor_name, target_name, state_name, containment_transform, containment_transform_exit, tuple(slots_to_params_entry_absolute), tuple(slots_to_params_exit_absolute), posture_state_spec=posture_state_spec, asm_name=asm.name, age=age)
                slot_constraints.append(slot_constraint)
        if slot_constraints:
            return create_constraint_set(slot_constraints)
        return Anywhere()

    _required_slot_cache = {}

    @classmethod
    def clear_required_slot_cache(cls):
        cls._required_slot_cache.clear()

    @staticmethod
    def _get_cache_key(sim, species, posture_type, target, actor_name):
        params = None
        if target is not None:
            anim_overrides = target.get_anim_overrides(None)
            if anim_overrides is not None:
                params = frozendict({param_name: param_value for (param_name, param_value) in anim_overrides.params.items() if not isinstance(param_value, (Quaternion, Vector3))})
        is_mirrored = target.is_mirrored() if target is not None and target.is_part else None
        key = (posture_type, sim.age, species, is_mirrored, params, actor_name)
        return key

    @staticmethod
    def create_slot_constraint(posture, posture_state_spec=DEFAULT):
        jig_name = posture.get_animation_data()._jig_name
        if posture.unconstrained and jig_name:
            return Anywhere()
        asm_key = posture._asm_key
        sim = posture.sim
        target = posture.target
        if posture_state_spec is DEFAULT:
            posture_manifest = posture.get_provided_postures(surface_target=MATCH_ANY)
            posture_state_spec = postures.posture_state_spec.PostureStateSpec(posture_manifest, FrozenSlotManifest(), posture.target)
        key = RequiredSlot._get_cache_key(sim, sim.species, posture.posture_type, target, posture._actor_param_name)
        slots_cached = RequiredSlot._required_slot_cache.get(key)
        if slots_cached is not None:
            slots_new = []
            for slot in slots_cached:
                slot_new = slot.clone_slot_for_new_target_and_posture(posture, posture_state_spec)
                slots_new.append(slot_new)
            return create_constraint_set(slots_new)
        state_name = posture._enter_state_name
        exit_slot_start_state = posture._state_name
        actor_name = posture._actor_param_name
        target_name = posture.get_target_name()
        asm = RequiredSlot._get_and_setup_asm_for_required_slot_set(asm_key, sim, target, actor_name, target_name, posture, asm=posture.asm)
        (containment_slot_to_slot_data_entry, containment_slot_to_slot_data_exit) = RequiredSlot._build_relative_slot_data(asm, sim, target, actor_name, target_name, posture, state_name, exit_slot_start_state=exit_slot_start_state)
        if not containment_slot_to_slot_data_entry:
            if posture.unconstrained:
                return Anywhere()
            if not posture.has_mobile_entry_transition():
                if posture_state_spec is None:
                    posture_manifest = posture.get_provided_postures(surface_target=MATCH_ANY)
                    posture_state_spec = create_body_posture_state_spec(posture_manifest, body_target=target)
                return Constraint(posture_state_spec=posture_state_spec)
            return Nowhere('create_slot_constraint could not generate the entry locations for a constrained posture. ASM: {}, Sim: {}, Target: {}', asm_key, sim, target)
        create_posture_state_spec_fn = lambda *_, **__: posture_state_spec
        required_slots = RequiredSlot._build_required_slot_set_from_relative_data(asm, asm_key, sim, target, posture, actor_name, target_name, state_name, containment_slot_to_slot_data_entry, containment_slot_to_slot_data_exit, create_posture_state_spec_fn)
        if required_slots is ANYWHERE:
            required_slots = Constraint(posture_state_spec=posture_state_spec)
        else:
            RequiredSlot._required_slot_cache[key] = required_slots._copy(_posture_state_spec=None)
        return required_slots

    @staticmethod
    def create_required_slot_set(sim, target, carry_target, asm_key, state_name, actor_name, target_name, carry_target_name, create_target_name, posture_manifest_overrides, required_slots, posture, surface_target, posture_state_spec, age=None, initial_state_name=DEFAULT, invalid_expected=False, base_object=None, base_object_name=None):
        if target.carryable_component is not None:
            target = surface_target
        if carry_target is not None and (target_name is not None and (target_name != carry_target_name and surface_target is not None)) and target is None:
            raise RuntimeError('Posture transition failed due to invalid tuning: Trying to create a required slot set with no target. \n  Sim: {}\n  Asm_Key: {}\n  State Name: {}\n  Actor Name: {}\n  Target Name: {}'.format(sim, asm_key, state_name, actor_name, target_name))
        if target.is_sim:
            return Constraint(posture_state_spec=posture_state_spec)
        asm = RequiredSlot._get_and_setup_asm_for_required_slot_set(asm_key, sim, target, actor_name, target_name, posture, carry_target=carry_target, carry_target_name=carry_target_name, create_target_name=create_target_name, surface_target=surface_target, posture_manifest_overrides=posture_manifest_overrides, invalid_expected=invalid_expected, base_object=base_object, base_object_name=base_object_name)
        if asm is None:
            return Nowhere('create_required_slot_set, failed to setup ASM: {}, Sim: {}, Target: {}', asm_key, sim, target)
        posture_state_spec_target = target

        def get_posture_state_spec(boundary_condition):
            return RequiredSlot._build_posture_state_spec_for_boundary_condition(boundary_condition, asm, sim, posture_state_spec_target, carry_target, surface_target, actor_name, target_name, carry_target_name, create_target_name, posture, state_name, posture_state_spec, required_slots)

        if posture is not None:
            target = posture.target
        (route_type, route_target) = target.route_target
        (containment_slot_to_slot_data_entry, _) = RequiredSlot._build_relative_slot_data(asm, sim, target, actor_name, target_name, posture, state_name, initial_state_name=initial_state_name, base_object_name=base_object_name)
        if not (target_name is None and target is None and containment_slot_to_slot_data_entry):
            return Nowhere('create_required_slot_set, failed to build entry locations for asm, ASM: {}, Sim: {}, Target: {}', asm, sim, target)
        if surface_target is DEFAULT:
            surface_target = posture.surface_target
        actual_route_target = None
        for (_, slot_data) in containment_slot_to_slot_data_entry:
            for (boundary_condition, _) in slot_data:
                relative_object_id = boundary_condition.get_relative_object_id(asm)
                if relative_object_id and relative_object_id != target.id:
                    if posture.target is not None and posture.target.id == relative_object_id:
                        actual_route_target = posture.target
                    elif surface_target is not None and surface_target.id == relative_object_id:
                        actual_route_target = surface_target
                    elif sim.id == relative_object_id:
                        actual_route_target = sim
                    else:
                        relative_object = services.object_manager().get(relative_object_id)
                        raise RuntimeError('Unexpected relative object ID: not target, container, or surface. object_id: {} object: {} asm: {} state_name {} interaction {}', relative_object_id, relative_object, asm, state_name, StackVar(('interaction',)))
                    (route_type, route_target) = actual_route_target.route_target
                    break
        if route_type == interactions.utils.routing.RouteTargetType.PARTS:
            part_owner = actual_route_target or target
            if part_owner.is_part:
                part_owner = part_owner.part_owner
            if len(route_target) > 1:
                route_target = part_owner.get_compatible_parts(posture)
                if not route_target:
                    logger.error('No parts are compatible with {}!', posture)
            elif route_target[0] not in part_owner.get_compatible_parts(posture):
                return Nowhere('Route Target has no compatible parts for posture. Target: {}, Posture: {}', route_target[0], posture)
        elif route_type == interactions.utils.routing.RouteTargetType.OBJECT:
            route_target = (route_target,)
        else:
            raise ValueError('Unexpected routing target type {} for object {}'.format(route_type, target))
        slot_constraints = []
        for target in route_target:
            slot_constraints_part = RequiredSlot._build_required_slot_set_from_relative_data(asm, asm_key, sim, target, posture, actor_name, target_name, state_name, containment_slot_to_slot_data_entry, None, get_posture_state_spec, age=age, invalid_expected=invalid_expected)
            slot_constraints.extend(slot_constraints_part)
        if slot_constraints:
            return create_constraint_set(slot_constraints)
        return Nowhere('create_required_slot_set, failed to generate slot constraint for asm. ASM: {}', asm_key)

class RequiredSlotSingle(SmallAreaConstraint):
    INTERSECT_PREFERENCE = IntersectPreference.REQUIREDSLOT

    def __init__(self, sim, target, asm, asm_key, posture, actor_name, target_name, state_name, containment_transform, containment_transform_exit, slots_to_params_entry, slots_to_params_exit, geometry=DEFAULT, routing_surface=DEFAULT, asm_name=None, debug_name=DEFAULT, objects_to_ignore=None, **kwargs):
        if routing_surface is DEFAULT:
            if target.routing_surface.type == routing.SurfaceType.SURFACETYPE_OBJECT:
                transform = slots_to_params_entry[0][0]
                if transform is None:
                    routing_surface = target.routing_surface
                else:
                    world_surface = routing.SurfaceIdentifier(services.current_zone_id() or 0, target.routing_surface.secondary_id, routing.SurfaceType.SURFACETYPE_WORLD)
                    bounds = sims4.geometry.QtCircle(sims4.math.Vector2(transform.translation.x, transform.translation.z), 0.05)
                    object_surfaces = services.sim_quadtree().query(bounds=bounds, surface_id=world_surface, filter=ItemType.ROUTABLE_OBJECT_SURFACE)
                    if object_surfaces:
                        routing_surface = target.routing_surface
                    else:
                        routing_surface = world_surface
            else:
                routing_surface = target.routing_surface
        geometry = create_transform_geometry(containment_transform)
        objects_to_ignore = set(objects_to_ignore or ())
        objects_to_ignore.add(target.id)
        if not (target.parent is not None and target.is_part and target.parent.is_part):
            objects_to_ignore.add(target.parent.id)
        super().__init__(geometry=geometry, routing_surface=routing_surface, debug_name=debug_name, objects_to_ignore=objects_to_ignore, **kwargs)
        self._sim_ref = sim.ref()
        self._target = target
        self._asm = asm
        self._asm_key = asm_key
        self._posture = posture
        self._actor_name = actor_name
        self._target_name = target_name
        self._state_name = state_name
        self._containment_transform = containment_transform
        self._containment_transform_exit = containment_transform_exit
        self._slots_to_params_entry = slots_to_params_entry
        self._slots_to_params_exit = slots_to_params_exit
        self._target_transform = target.transform

    @property
    def _sim(self):
        if self._sim_ref is not None:
            return self._sim_ref()

    @constproperty
    def restricted_on_slope():
        return True

    @property
    def multi_surface(self):
        if self._posture is None:
            return False
        return self._posture.is_universal and (self._target is not None and self._target.provided_routing_surface is not None)

    def _get_bounding_box_polygon(self):
        if self._posture is not None and (self._posture.is_universal and self._target is not None) and self._target.provided_routing_surface is not None:
            constraint = self.get_universal_constraint()
            return constraint.polygons
        return super()._get_bounding_box_polygon()

    def get_universal_constraint(self, reference_joint=None):
        if reference_joint is None:
            target_forward = DEFAULT
        else:
            reference_transform = self._target.get_joint_transform_for_joint(reference_joint)
            target_forward = reference_transform.orientation.transform_vector(sims4.math.Vector3.Z_AXIS())
        universal_constraint = Anywhere()
        if self._posture.universal is None:
            return universal_constraint
        for tuned_constraint in self._posture.universal.constraint:
            constraint = tuned_constraint.create_constraint(None, target=self._target, target_position=self._target.position, target_forward=target_forward)
            universal_constraint = universal_constraint.intersect(constraint)
        return universal_constraint

    def get_connectivity_handles(self, *args, locked_params=frozendict(), entry=True, routing_surface_override=None, los_reference_point=None, log_none_slots_to_params_as_error=False, **kwargs):
        if entry or not self._slots_to_params_exit:
            slots_to_params = self._slots_to_params_entry
        else:
            slots_to_params = self._slots_to_params_exit
        if slots_to_params is None:
            if False and log_none_slots_to_params_as_error:
                logger.error('RequiredSlotSingle: SlotsToParam is None for Constraint:{} Entry:{} Exit:{}', self, self._slots_to_params_entry, self._slots_to_params_exit, owner='nsavalani')
            return []
        if los_reference_point is None:
            (los_reference_point, _) = Constraint.get_los_reference_point(self._target)
        handles = []
        for (routing_transform, reference_joint, my_locked_params_list) in slots_to_params:
            for my_locked_params in my_locked_params_list:
                if not do_params_match(my_locked_params, locked_params):
                    pass
                else:
                    transition_posture = my_locked_params.get('transitionPosture')
                    _routing_surface_override = self._target.get_surface_override_for_posture(transition_posture)
                    if _routing_surface_override is not None:
                        routing_surface_override = _routing_surface_override
                    if routing_transform is not None:
                        geometry = create_transform_geometry(routing_transform)
                        connectivity_handle = routing.connectivity.SlotRoutingHandle(*args, constraint=self, geometry=geometry, locked_params=my_locked_params, routing_surface_override=routing_surface_override, los_reference_point=los_reference_point, **kwargs)
                    else:
                        universal_constraint = self.get_universal_constraint(reference_joint=reference_joint)
                        geometry = universal_constraint.geometry
                        if not entry:
                            for restriction in geometry.restrictions:
                                if isinstance(restriction, sims4.geometry.RelativeFacingRange):
                                    restriction.invert = True
                        reference_transform = None
                        if reference_joint:
                            reference_transform = self._target.get_joint_transform_for_joint(reference_joint)
                            root_transform = self.containment_transform if entry else self.containment_transform_exit
                            reference_transform = sims4.math.Transform(sims4.math.Vector3(root_transform.translation.x, reference_transform.translation.y, root_transform.translation.z), root_transform.orientation)
                        connectivity_handle = routing.connectivity.UniversalSlotRoutingHandle(*args, constraint=self, geometry=geometry, locked_params=my_locked_params, routing_surface_override=routing_surface_override, los_reference_point=los_reference_point, reference_transform=reference_transform, entry=entry, cost_functions_override=universal_constraint._scoring_functions, posture=self._posture, **kwargs)
                    handles.append(connectivity_handle)
                    break
        return handles

    def constraint_cost(self, *args, **kwargs):
        return 0.0

    @property
    def containment_transform(self):
        return self._containment_transform

    @property
    def containment_transform_exit(self):
        return self._containment_transform_exit

    @property
    def average_position(self):
        return self.containment_transform.translation

    @property
    def routing_positions(self):
        return [self.containment_transform.translation]

    def _posture_state_spec_target_resolver(self, target, default=None):
        if target == AnimationParticipant.ACTOR:
            return self._sim
        if target == AnimationParticipant.CONTAINER or target == AnimationParticipant.BASE_OBJECT:
            return self._posture.target
        elif target == AnimationParticipant.TARGET:
            return self._target
        return default

    def _intersect(self, other_constraint):
        resolved_constraint = other_constraint.apply_posture_state(None, self._posture_state_spec_target_resolver)
        if not resolved_constraint.valid:
            return Nowhere('RequiredSlotSingle._intersect, unable to apply posture state to a constraint to resolve it. Constraint: {}, Sim: {}', other_constraint, self._sim)
        (early_out, kwargs) = self._intersect_kwargs(resolved_constraint)
        if early_out is not None:
            return early_out
        if isinstance(other_constraint, RequiredSlotSingle) and not Asm.transform_almost_equal_2d(self.containment_transform, resolved_constraint.containment_transform):
            return Nowhere('Trying to intersect RequiredSlots at different transforms. A: {}, B: {}', self.containment_transform, resolved_constraint.containment_transform)
        result = self._copy(**kwargs)
        return result

    def apply_posture_state(self, posture_state, target_resolver, **kwargs):
        posture_state_constraint = self._get_posture_state_constraint(posture_state, target_resolver)
        intersection = self.intersect(posture_state_constraint)
        return intersection

    def clone_slot_for_new_target_and_posture(self, posture, posture_state_spec):
        target = posture.target
        if self._target_transform == target.transform:
            return self._copy(_sim_ref=posture.sim.ref(), _target=target, _posture=posture, _posture_state_spec=posture_state_spec)
        original_obj_inverse = sims4.math.get_difference_transform(self._target_transform, sims4.math.Transform())
        transform_between_objs = sims4.math.Transform.concatenate(original_obj_inverse, target.transform)
        containment_transform_new = sims4.math.Transform.concatenate(self._containment_transform, transform_between_objs)
        containment_transform_exit_new = sims4.math.Transform.concatenate(self._containment_transform_exit, transform_between_objs) if self._containment_transform_exit is not None else None
        slots_to_params_entry_new = []
        for (routing_transform_entry, reference_joint, param_sequences) in self._slots_to_params_entry:
            routing_transform_entry_new = sims4.math.Transform.concatenate(routing_transform_entry, transform_between_objs) if routing_transform_entry is not None else None
            slots_to_params_entry_new.append((routing_transform_entry_new, reference_joint, param_sequences))
        slots_to_params_entry_new = tuple(slots_to_params_entry_new)
        if self._slots_to_params_exit:
            slots_to_params_exit_new = []
            for (routing_transform_exit, reference_joint, param_sequences) in self._slots_to_params_exit:
                routing_transform_exit_new = sims4.math.Transform.concatenate(routing_transform_exit, transform_between_objs) if routing_transform_exit is not None else None
                slots_to_params_exit_new.append((routing_transform_exit_new, reference_joint, param_sequences))
            slots_to_params_exit_new = tuple(slots_to_params_exit_new)
        else:
            slots_to_params_exit_new = None
        geometry = create_transform_geometry(containment_transform_new)
        result = self._copy(_sim_ref=posture.sim.ref(), _target=target, _posture=posture, _containment_transform=containment_transform_new, _containment_transform_exit=containment_transform_exit_new, _slots_to_params_entry=slots_to_params_entry_new, _slots_to_params_exit=slots_to_params_exit_new, _geometry=geometry, _routing_surface=target.routing_surface, _posture_state_spec=posture_state_spec)
        return result

    def estimate_distance_cache_key(self):
        return self._copy(_actor_name=None, _asm=None, _asm_key=None, _containment_transform_exit=None, debug_name='EstimateDistanceCacheKeyCopy', _posture=None)

def Position(position, debug_name=DEFAULT, **kwargs):
    if debug_name is DEFAULT:
        debug_name = 'Position'
    position = sims4.math.vector_flatten(position)
    geometry = sims4.geometry.RestrictedPolygon(sims4.geometry.CompoundPolygon(sims4.geometry.Polygon((position,))), ())
    return SmallAreaConstraint(geometry=geometry, debug_name=debug_name, **kwargs)

class TunedPosition:

    def __init__(self, relative_position):
        self._relative_position = relative_position

    def create_constraint(self, sim, target, **kwargs):
        offset = sims4.math.Transform(self._relative_position, sims4.math.Quaternion.IDENTITY())
        transform = sims4.math.Transform.concatenate(offset, target.intended_transform)
        return Position(transform.translation, routing_surface=target.intended_routing_surface)

class TunablePosition(TunableSingletonFactory):
    FACTORY_TYPE = TunedPosition

    def __init__(self, relative_position, description='A tunable type for creating positional constraints.', **kwargs):
        super().__init__(relative_position=TunableVector3(relative_position, description='Position'), description=description, **kwargs)

def Transform(transform, debug_name=DEFAULT, **kwargs):
    if debug_name is DEFAULT:
        debug_name = 'Transform'
    transform_geometry = create_transform_geometry(transform)
    return SmallAreaConstraint(geometry=transform_geometry, debug_name=debug_name, **kwargs)

def create_transform_geometry(transform):
    if transform.orientation != sims4.math.Quaternion.ZERO():
        facing_direction = transform.transform_vector(sims4.math.FORWARD_AXIS)
        facing_angle = sims4.math.atan2(facing_direction.x, facing_direction.z)
        transform_facing_range = sims4.geometry.AbsoluteOrientationRange(sims4.geometry.interval_from_facing_angle(facing_angle, 0))
        facing_restriction = (transform_facing_range,)
    else:
        facing_restriction = ()
    return sims4.geometry.RestrictedPolygon(sims4.geometry.CompoundPolygon(sims4.geometry.Polygon((sims4.math.vector_flatten(transform.translation),))), facing_restriction)
_DEFAULT_CONE_ROTATION_OFFSET = 0_DEFAULT_CONE_RADIUS_MIN = 0.25_DEFAULT_CONE_RADIUS_MAX = 0.75_DEFAULT_CONE_IDEAL_ANGLE = 0.25_DEFAULT_CONE_VERTEX_COUNT = 8_DEFAULT_COST_WEIGHT = 2.25
def build_weighted_cone(pos, forward, min_radius, max_radius, angle, rotation_offset=_DEFAULT_CONE_ROTATION_OFFSET, ideal_radius_min=_DEFAULT_CONE_RADIUS_MIN, ideal_radius_max=_DEFAULT_CONE_RADIUS_MAX, ideal_angle=_DEFAULT_CONE_IDEAL_ANGLE, radial_cost_weight=_DEFAULT_COST_WEIGHT, angular_cost_weight=_DEFAULT_COST_WEIGHT):
    cone_polygon = sims4.geometry.generate_cone_constraint(pos, forward, min_radius, max_radius, angle, rotation_offset, _DEFAULT_CONE_VERTEX_COUNT)
    cone_polygon.normalize()
    cone_geometry = sims4.geometry.RestrictedPolygon(sims4.geometry.CompoundPolygon(cone_polygon), ())
    ideal_radius_min = min_radius + ideal_radius_min*(max_radius - min_radius)
    ideal_radius_max = min_radius + ideal_radius_max*(max_radius - min_radius)
    center = pos
    ideal_radius = (ideal_radius_min + ideal_radius_max)*0.5
    safe_radial_width = ideal_radius_max - ideal_radius_min
    safe_angle = angle*ideal_angle
    scoring_functions = ()
    if radial_cost_weight != 0:
        scoring_function_radial = ConstraintCostCircleDist(center, ideal_radius, radial_cost_weight, safe_width=safe_radial_width)
        scoring_functions += (scoring_function_radial,)
    if angular_cost_weight != 0:
        scoring_function_angular = ConstraintCostArcLength(center, center + forward, angular_cost_weight, safe_angle=safe_angle)
        scoring_functions += (scoring_function_angular,)
    return (cone_geometry, scoring_functions)

def Cone(pos, forward, min_radius, max_radius, angle, routing_surface, rotation_offset=_DEFAULT_CONE_ROTATION_OFFSET, ideal_radius_min=_DEFAULT_CONE_RADIUS_MIN, ideal_radius_max=_DEFAULT_CONE_RADIUS_MAX, ideal_angle=_DEFAULT_CONE_IDEAL_ANGLE, radial_cost_weight=_DEFAULT_COST_WEIGHT, angular_cost_weight=_DEFAULT_COST_WEIGHT, scoring_functions=(), debug_name=DEFAULT, **kwargs):
    if debug_name is DEFAULT:
        debug_name = 'Cone'
    (cone_geometry, cone_scoring_functions) = build_weighted_cone(pos, forward, min_radius, max_radius, angle, rotation_offset=rotation_offset, ideal_radius_min=ideal_radius_min, ideal_radius_max=ideal_radius_max, ideal_angle=ideal_angle, radial_cost_weight=radial_cost_weight, angular_cost_weight=angular_cost_weight)
    scoring_functions = scoring_functions + cone_scoring_functions
    return Constraint(geometry=cone_geometry, scoring_functions=scoring_functions, routing_surface=routing_surface, debug_name=debug_name, **kwargs)

class TunedCone:

    def __init__(self, min_radius, max_radius, angle, offset, ideal_radius_min, ideal_radius_max, ideal_angle, radial_cost_weight, angular_cost_weight, multi_surface, enables_height_scoring, require_los):
        self._min_radius = min_radius
        self._max_radius = max_radius
        self._angle = angle
        self._offset = offset
        self._ideal_radius_min = ideal_radius_min
        self._ideal_radius_max = ideal_radius_max
        self._ideal_angle = ideal_angle
        self._radial_cost_weight = radial_cost_weight
        self._angular_cost_weight = angular_cost_weight
        self._multi_surface = multi_surface
        self._enables_height_scoring = enables_height_scoring
        self._require_los = require_los

    def create_constraint(self, sim, target, target_position=DEFAULT, target_forward=DEFAULT, routing_surface=DEFAULT, **kwargs):
        if target is None and (target_position is DEFAULT or target_forward is DEFAULT or routing_surface is DEFAULT):
            return Nowhere('Trying to create a cone relative to None')
        if target is not None and target.is_in_inventory():
            if target.is_in_sim_inventory():
                return Anywhere()
            logger.error('Attempt to create a tuned Cone constraint on a target: {} which is in the inventory.  This will not work correctly.', target, owner='mduke')
            return Nowhere('Trying to create a cone relative to an object in an inventory: {}', target)
        if target_position is DEFAULT:
            target_position = target.intended_position
        if target_forward is DEFAULT:
            target_forward = target.intended_forward
        if routing_surface is DEFAULT:
            routing_surface = target.intended_routing_surface
        if self._angular_cost_weight != 0 and target_forward.z == 0 and target_forward.x == 0:
            logger.error('Sim: () attempt to create a tuned Cone constraint with angular cost weight on a target: {} with invalid forward vector', sim, target)
            return Nowhere('Attempt to create a tuned Cone constraint with angular cost weight on a target: {} with invalid forward vector', target)
        los_reference_point = DEFAULT if self._require_los else None
        return Cone(target_position, target_forward, self._min_radius, self._max_radius, self._angle, routing_surface, self._offset, self._ideal_radius_min, self._ideal_radius_max, self._ideal_angle, self._radial_cost_weight, self._angular_cost_weight, multi_surface=self._multi_surface, los_reference_point=los_reference_point, **kwargs)

class TunableCone(TunableSingletonFactory):
    FACTORY_TYPE = TunedCone

    def __init__(self, min_radius, max_radius, angle, description='A tunable type for creating cone constraints.', callback=None, **kwargs):
        super().__init__(min_radius=Tunable(description='\n                                            The minimum cone radius.\n                                            ', tunable_type=float, default=min_radius), max_radius=Tunable(description='\n                                            The maximum cone radius.\n                                            ', tunable_type=float, default=max_radius), angle=TunableAngle(description='\n                                            The cone angle in degrees.\n                                            ', default=angle), offset=TunableAngle(description='\n                                            An offset (rotation) in degrees.\n                                            \n                                            By default the cone will face the \n                                            forward vector of the object.  Use\n                                            an offset to rotate the cone to \n                                            face a different direction. \n                                            ', default=_DEFAULT_CONE_ROTATION_OFFSET), ideal_radius_min=TunableRange(description='\n                                            The radial lower bound of an ideal \n                                            region as a fraction of the \n                                            difference between max_radius and \n                                            min_radius.\n                                            ', tunable_type=float, default=_DEFAULT_CONE_RADIUS_MIN, minimum=0, maximum=1), ideal_radius_max=TunableRange(description='\n                                            The radial upper bound of an ideal \n                                            region as a fraction of the \n                                            difference between max_radius and \n                                            min_radius.\n                                            ', tunable_type=float, default=_DEFAULT_CONE_RADIUS_MAX, minimum=0, maximum=1), ideal_angle=TunableRange(description='\n                                            The angular extents of an ideal \n                                            region as a fraction of angle.\n                                            ', tunable_type=float, default=_DEFAULT_CONE_IDEAL_ANGLE, minimum=0, maximum=1), radial_cost_weight=TunableRange(description='\n                                            The importance of the radial cost \n                                            function.\n                                             = 0: Not used\n                                             > 1: Important on surfaces\n                                             > 2: Important on grass\n                                            ', tunable_type=float, default=_DEFAULT_COST_WEIGHT, minimum=0), angular_cost_weight=TunableRange(description='\n                                            The importance of the angular cost \n                                            function.\n                                             = 0: Not used\n                                             > 1: Important on surfaces\n                                             > 2: Important on grass\n                                            ', tunable_type=float, default=_DEFAULT_COST_WEIGHT, minimum=0), multi_surface=Tunable(description='\n                                            If enabled, this constraint will be\n                                            considered for multiple surfaces.\n                                            \n                                            Example: You want a circle\n                                            constraint that can be both inside\n                                            and outside of a pool.\n                                            ', tunable_type=bool, default=False), enables_height_scoring=Tunable(description='\n                                            If enabled, this constraint will \n                                            score goals using the height of\n                                            the surface.  The higher the goal\n                                            the cheaper it is.\n                                            ', tunable_type=bool, default=False), require_los=Tunable(description="\n                                            If checked, the Sim will require line of sight to the actor.  Positions where a Sim\n                                            can't see the actor (e.g. there's a wall in the way) won't be valid.\n                                            \n                                            NOTE: This will NOT work on a\n                                            constraint that is not used to\n                                            generate routing goals such as\n                                            broadcasters and reactions, use a\n                                            Line Of Sight Constraint instead.\n                                            This will work on constraints used\n                                            to keep Sims in an interaction.\n                                            ", tunable_type=bool, default=True), description=description, **kwargs)

class Circle(Constraint):
    NUM_SIDES = Tunable(int, 8, description='The number of polygon sides to use when approximating a circle constraint.')

    def __init__(self, center, radius, routing_surface, ideal_radius=None, ideal_radius_width=0, radial_cost_weight=_DEFAULT_COST_WEIGHT, target_forward=None, **kwargs):
        circle_geometry = sims4.geometry.RestrictedPolygon(sims4.geometry.CompoundPolygon(sims4.geometry.generate_circle_constraint(self.NUM_SIDES, center, radius)), ())
        self._center = center
        self._radius = radius
        self._radius_sq = radius*radius
        if ideal_radius is not None and radial_cost_weight > 0:
            scoring_function = ConstraintCostCircleDist(self._center, ideal_radius, radial_cost_weight)
            scoring_functions = (scoring_function,)
            goal_function = ConstraintGoalGenerationFunctionIdealRadius(self._center, ideal_radius)
            goal_functions = (goal_function,)
        else:
            scoring_functions = ()
            goal_functions = ()
        super().__init__(geometry=circle_geometry, routing_surface=routing_surface, scoring_functions=scoring_functions, goal_functions=goal_functions, **kwargs)

class TunedCircle:

    def __init__(self, radius, ideal_radius, ideal_radius_width, require_los, radial_cost_weight, multi_surface, enables_height_scoring):
        self.radius = radius
        self.ideal_radius = ideal_radius
        self.ideal_radius_width = ideal_radius_width
        self._require_los = require_los
        self._radial_cost_weight = radial_cost_weight
        self._multi_surface = multi_surface
        self._enables_height_scoring = enables_height_scoring

    def create_constraint(self, sim, target=None, target_position=DEFAULT, routing_surface=DEFAULT, **kwargs):
        if target is not None and target.is_in_inventory():
            if target.is_in_sim_inventory():
                return Anywhere()
            logger.error('Attempt to create a tuned Circle constraint on a target: {} which is in the inventory.  This will not work correctly.', target, owner='mduke')
            return Nowhere('Trying to create a circle constraint relative to an object in an inventory: {}', target)
        if target is None:
            target = sim
        if target_position is DEFAULT:
            target_position = target.intended_position
        if routing_surface is DEFAULT:
            routing_surface = target.intended_routing_surface
        los_reference_point = DEFAULT if self._require_los else None
        return Circle(target_position, self.radius, routing_surface, ideal_radius=self.ideal_radius, ideal_radius_width=self.ideal_radius_width, radial_cost_weight=self._radial_cost_weight, los_reference_point=los_reference_point, multi_surface=self._multi_surface, enables_height_scoring=self._enables_height_scoring, **kwargs)

class TunableCircle(TunableSingletonFactory):
    FACTORY_TYPE = TunedCircle

    def __init__(self, radius, description='A tunable type for creating Circle constraints.', callback=None, **kwargs):
        super().__init__(radius=Tunable(float, radius, description='Circle radius'), ideal_radius=Tunable(description='\n                                            Ideal distance for this circle constraint, points \n                                            closer to the ideal distance will score higher.\n                                            ', tunable_type=float, default=None), ideal_radius_width=Tunable(description='\n                                            This creates a band around the ideal_radius that also\n                                            costs 0 instead of rising in cost. ex: If you\n                                            have a circle of radius 5, with an ideal_radius of 2.5, and a\n                                            ideal_radius_width of 0.5, all goals in the radius 2 to radius 3 range\n                                            will score optimially.\n                                            ', tunable_type=float, default=0), require_los=Tunable(description="\n                                            If checked, the Sim will require line of sight to the actor.  Positions where a Sim\n                                            can't see the actor (e.g. there's a wall in the way) won't be valid.\n                                            \n                                            NOTE: This will NOT work on a\n                                            constraint that is not used to\n                                            generate routing goals such as\n                                            broadcasters and reactions, use a\n                                            Line Of Sight Constraint instead.\n                                            This will work on constraints used\n                                            to keep Sims in an interaction.\n                                            ", tunable_type=bool, default=True), radial_cost_weight=TunableRange(description='\n                                            The importance of the radial cost function.\n                                             = 0: Not used\n                                             > 1: Important on surfaces\n                                             > 2: Important on grass\n                                            ', tunable_type=float, default=_DEFAULT_COST_WEIGHT, minimum=0), multi_surface=Tunable(description='\n                                            If enabled, this constraint will be considered for multiple surfaces.\n                                            \n                                            Example: You want a circle\n                                            constraint that can be both inside\n                                            and outside of a pool.\n                                            ', tunable_type=bool, default=False), enables_height_scoring=Tunable(description='\n                                            If enabled, this constraint will \n                                            score goals using the height of\n                                            the surface.  The higher the goal\n                                            the cheaper it is.\n                                            ', tunable_type=bool, default=False), description=description, **kwargs)

class CurrentPosition(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'radius': TunableRange(description='\n            The maximum radius around the center point.\n            ', tunable_type=float, minimum=0, default=1), 'ignore_on_object_routing_surface': Tunable(description="\n            If checked, we will ignore this constraint on the object routing\n            surface. This should be used when we are only tuning this constraint\n            for performance reasons in order to be compatible with stair \n            landings or other object routing surface areas that are not in the\n            sim quadtree- which don't support geometric constraints.\n            ", tunable_type=bool, default=True)}

    def create_constraint(self, sim, target, **kwargs):
        if self.ignore_on_object_routing_surface and sim.intended_routing_surface is not None and sim.intended_routing_surface.type == SurfaceType.SURFACETYPE_OBJECT:
            return ANYWHERE
        return Circle(sim.intended_position, self.radius, sim.intended_routing_surface, **kwargs)

class TunedWelcomeConstraint:

    def __init__(self, radius, ideal_radius, find_front_door):
        self._radius = radius
        self._ideal_radius = ideal_radius
        self._find_front_door = find_front_door

    def create_constraint(self, sim, target=None, routing_surface=DEFAULT, **kwargs):
        zone = services.current_zone()
        if zone is None:
            logger.error('Attempting to create welcome constraint when zone is None.', owner='jjacobson')
            return Nowhere('TunedWelcomeConstraint.create_constraint, zone is None')
        active_lot = zone.lot
        if active_lot is None:
            logger.error('Attempting to create welcome constraint when active lot is None.', owner='jjacobson')
            return Nowhere('TunedWelcomeConstraint.create_constraint, active_lot is None')
        front_door = services.get_door_service().get_front_door() if self._find_front_door else None
        if front_door is not None:
            position = front_door.position
            routing_surface = front_door.routing_surface
        else:
            spawn_point = zone.get_spawn_point(lot_id=active_lot.lot_id, sim_spawner_tags=SimInfoSpawnerTags.SIM_SPAWNER_TAGS)
            position = spawn_point.get_approximate_center()
            routing_surface = routing.SurfaceIdentifier(zone.id, 0, routing.SurfaceType.SURFACETYPE_WORLD)
        return Circle(position, self._radius, routing_surface=routing_surface, ideal_radius=self._ideal_radius)

class TunableWelcomeConstraint(TunableSingletonFactory):
    FACTORY_TYPE = TunedWelcomeConstraint

    def __init__(self, radius, description='A tunable type for creating circle constraints to an object that has the Welcome component', callback=None, **kwargs):
        super().__init__(radius=Tunable(float, radius, description='Circle radius'), ideal_radius=Tunable(float, None, description='ideal distance for this front door constraint, points closer to the ideal distance will score higher.'), find_front_door=Tunable(bool, True, description='\n                            If True the constraint will try and locate the front door on the lot\n                            and use that location before using the spawn points. If False\n                            the spawn points will always be used. The tuning for the spawn\n                            tags is in sim_info_types.tuning.\n                            '), description=description, **kwargs)

class FrontDoorOption(enum.Int):
    OUTSIDE_FRONT_DOOR = 0
    INSIDE_FRONT_DOOR = 1

class TunedFrontDoorConstraint(ZoneConstraintMixin):

    def __init__(self, ideal_radius, line_of_sight, front_door_position_option, door_select_option, fallback_to_anywhere_on_lot):
        super().__init__()
        self._ideal_radius = ideal_radius
        self._line_of_sight = line_of_sight
        self._front_door_position_option = front_door_position_option
        self._door_select_option = door_select_option
        self._fallback_to_anywhere_on_lot = fallback_to_anywhere_on_lot

    def create_zone_constraint(self, sim, target=None, routing_surface=DEFAULT, **kwargs):
        front_door = self._door_select_option.get_door(sim, target=target)
        if front_door is not None:
            (front_position, back_position) = front_door.get_door_positions()
            if self._front_door_position_option == FrontDoorOption.OUTSIDE_FRONT_DOOR:
                position = front_position
            else:
                position = back_position
            routing_surface = front_door.routing_surface
        else:
            if self._fallback_to_anywhere_on_lot:
                edge_constraints = []
                world_routing_surface = routing.SurfaceIdentifier(services.current_zone_id(), 0, routing.SurfaceType.SURFACETYPE_WORLD)
                edge_polygons = services.active_lot().get_edge_polygons()
                for polygon in edge_polygons:
                    geometry = sims4.geometry.RestrictedPolygon(sims4.geometry.CompoundPolygon((polygon,)), [])
                    edge_constraints.append(Constraint(geometry=geometry, routing_surface=world_routing_surface))
                return create_constraint_set(edge_constraints, debug_name='LotEdgeConstraints')
            return Nowhere('Front Door Constraint: Could not find a door for this constraint.')
        los_factory = self._line_of_sight()
        los_factory.generate(position, routing_surface)
        los_constraint = los_factory.constraint
        circle_constraint = Circle(position, self._line_of_sight.max_line_of_sight_radius, routing_surface=routing_surface, ideal_radius=self._ideal_radius)
        return circle_constraint.intersect(los_constraint)

class TunableFrontDoorConstraint(TunableSingletonFactory):
    FACTORY_TYPE = TunedFrontDoorConstraint

    def __init__(self, description='A tunable type for creating a constraint inside or outside the front door', callback=None, **kwargs):
        from objects.components.line_of_sight_component import TunableLineOfSightFactory
        super().__init__(ideal_radius=Tunable(description='\n                            ideal distance for this front door constraint, \n                            points closer to the ideal distance will score higher.\n                            ', tunable_type=float, default=2), line_of_sight=TunableLineOfSightFactory(description='\n                            Tuning to generate a light of sight constraint\n                            either inside or outside the front door in\n                            order to get the sims to move there.\n                            '), front_door_position_option=TunableEnumEntry(description='\n                             The option of whether to use the inside or outside\n                             side of the front door in order to generate the\n                             constraint.\n                             ', tunable_type=FrontDoorOption, default=FrontDoorOption.OUTSIDE_FRONT_DOOR), door_select_option=TunableVariant(description='\n                             The option to select which door we actually want\n                             to use for this constraint. Since apartment doors\n                             are on lot and considered front doors of their\n                             respective zones, we can acquire them using this\n                             option.\n                             \n                             Note: In any case, if we cannot find an\n                             appropriate door for the option, we will return a\n                             Nowhere constraint.\n                             ', default='front_door', front_door=DoorSelectFrontDoor.TunableFactory(), participant_apartment_door=DoorSelectParticipantApartmentDoor.TunableFactory()), fallback_to_anywhere_on_lot=Tunable(description='\n                             If enabled and we do not have a front door, the\n                             constraint will be a polygon of anywhere on lot.\n                             ', tunable_type=bool, default=False), description=description, **kwargs)

class PostureConstraintFactory(HasTunableSingletonFactory, AutoFactoryInit):

    @staticmethod
    def on_tunable_loaded_callback(instance_class, tunable_name, source, value):
        posture_manifest = PostureManifest()
        for tuning in value.posture_manifest_tuning:
            posture_manifest_entry = value._create_manifest_entry(AnimationParticipant.ACTOR, tuning.posture_type, tuning.compatibility, tuning.carry_left, tuning.carry_right, tuning.surface, tuning.target_object_filter)
            posture_manifest.add(posture_manifest_entry)
        posture_manifest = posture_manifest.intern()
        body_target = value.body_target_tuning
        if value.slot_manifest_tuning:
            constraints = []
            for tuning in value.slot_manifest_tuning:
                slot_manifest = SlotManifest()
                slot_manifest_entry = SlotManifestEntry(tuning.child, tuning.parent, tuning.slot)
                slot_manifest.add(slot_manifest_entry)
                posture_state_spec = postures.posture_state_spec.PostureStateSpec(posture_manifest, slot_manifest, body_target)
                constraint = Constraint(posture_state_spec=posture_state_spec, debug_name='TunablePostureConstraint')
                constraints.append(constraint)
            value._constraint = create_constraint_set(constraints)
        else:
            posture_state_spec = postures.posture_state_spec.PostureStateSpec(posture_manifest, SlotManifest(), body_target)
            value._constraint = Constraint(posture_state_spec=posture_state_spec, debug_name='TunablePostureConstraint')

    FACTORY_TUNABLES = {'posture_manifest_tuning': TunableList(description='A list of posture manifests this interaction should support.', tunable=TunableTuple(description='A posture manifests this interaction should support.', posture_type=OptionalTunable(TunableReference(services.get_instance_manager(sims4.resources.Types.POSTURE), description='The posture required by this constraint', pack_safe=True)), compatibility=TunableVariant(default='Any', locked_args={'Any': MATCH_ANY, 'UpperBody': UPPER_BODY, 'FullBody': FULL_BODY}, description='posture level. upper body, full body or any'), carry_left=TunableVariant(default='Any', actor=TunableEnumEntry(AnimationParticipant, AnimationParticipant.CARRY_TARGET), locked_args={'Any': MATCH_ANY, 'None': MATCH_NONE}, description='tuning for requirements for carry left. either any, none, or animation participant'), carry_right=TunableVariant(default='Any', actor=TunableEnumEntry(AnimationParticipant, AnimationParticipant.CARRY_TARGET), locked_args={'Any': MATCH_ANY, 'None': MATCH_NONE}, description='tuning for requirements for carry right. either any, none, or animation participant'), surface=TunableVariant(default='Any', actor=TunableEnumEntry(AnimationParticipant, AnimationParticipant.SURFACE), locked_args={'Any': MATCH_ANY, 'None': MATCH_NONE}, description='tuning for requirements for surface. either any, none, or animation participant'), target_object_filter=OptionalTunable(ObjectDefinitonsOrTagsVariant()))), 'slot_manifest_tuning': TunableList(description="\n                    A list of slot requirements that will be OR'd together \n                    for this interaction.  \n                    ", tunable=TunableTuple(description='A slot requirement for this interaction.  Adding a slot manifest will require the specified relationship between actors to exist before the interaction runs.  If the child object is carryable, the transition system will attempt to have the Sim move the child object into the correct type of slot.', child=TunableVariant(default='participant', participant=TunableEnumEntry(AnimationParticipant, AnimationParticipant.TARGET, description='If this is CREATE_TARGET, the transition system will find an empty slot of the specified type in which the object being created by the interaction will fit.'), definition=TunableReference(description='\n                            If used, the transition system will find an empty slot of the specified type in which an object of this definition can fit.\n                            ', manager=services.definition_manager())), parent=TunableEnumEntry(AnimationParticipant, AnimationParticipant.SURFACE), slot=TunableReference(services.get_instance_manager(sims4.resources.Types.SLOT_TYPE)))), 'body_target_tuning': TunableEnumEntry(description='The body target of the posture.', tunable_type=PostureSpecVariable, default=PostureSpecVariable.ANYTHING), 'callback': on_tunable_loaded_callback}

    def __init__(self, *args, **kwargs):
        self._constraint = None
        super().__init__(*args, **kwargs)

    def _create_manifest_entry(self, actor, posture_type, compatibility, carry_left, carry_right, surface, target_object_filter):
        posture_name = MATCH_ANY
        posture_family_name = MATCH_ANY
        if posture_type is not None:
            posture_name = posture_type.name
            posture_family_name = posture_type.family_name
        return PostureManifestEntry(actor, posture_name, posture_family_name, compatibility, carry_left, carry_right, surface, target_object_filter=target_object_filter)

    def create_constraint(self, *_, **__):
        return self._constraint

class WaterDepthIntervals(enum.Int):
    WALK = 0
    WET = 1
    WADE = 2
    SWIM = 3

class ObjectJigConstraint(SmallAreaConstraint, HasTunableSingletonFactory):
    INTERSECT_PREFERENCE = IntersectPreference.JIG
    JIG_CONSTRAINT_LIABILITY = 'JigConstraintLiability'

    class JigConstraintLiability(SharedLiability):

        def __init__(self, jig, constraint=None, ignore_sim=None, should_transfer=True, **kwargs):
            super().__init__(**kwargs)
            self.jig = jig
            self.constraint = constraint
            self._should_transfer = should_transfer
            if ignore_sim is not None:
                self._ignore_sim_ref = weakref.ref(ignore_sim)
                ignore_sim.routing_context.ignore_footprint_contour(self.jig.routing_context.object_footprint_id)
            else:
                self._ignore_sim_ref = None

        def should_transfer(self, continuation):
            return self._should_transfer

        def release(self, *args, **kwargs):
            if self.sim is not None:
                self.sim.routing_context.remove_footprint_contour_override(self.jig.routing_context.object_footprint_id)
            super().release(*args, **kwargs)

        def shared_release(self):
            self.jig.schedule_destroy_asap(source=self, cause='Destroying Jig in ObjectJigConstraint.')

        @property
        def sim(self):
            if self._ignore_sim_ref is not None:
                return self._ignore_sim_ref()

        def create_new_liability(self, interaction, *args, **kwargs):
            return super().create_new_liability(interaction, self.jig, *args, constraint=self.constraint, ignore_sim=self.sim, **kwargs)

    def __init__(self, jig_definition, stay_outside=False, is_soft_constraint=False, face_participant=None, sim=None, target=None, ignore_sim=True, object_id=None, should_transfer_liability=True, stay_on_world=False, use_intended_location=True, model_suite_state_index=None, jig_model_suite_state_index=None, force_pool_surface_water_depth=None, **kwargs):
        super().__init__(**kwargs)
        self._jig_definition = jig_definition
        self._ignore_sim = ignore_sim
        self._stay_outside = stay_outside
        self._is_soft_constraint = is_soft_constraint
        self._object_id = object_id
        self._face_participant = face_participant
        self._should_transfer_liability = should_transfer_liability
        self._stay_on_world = stay_on_world
        self._use_intended_location = use_intended_location
        self._model_suite_state_index = model_suite_state_index
        if jig_model_suite_state_index is None and self._object_id is None and self._model_suite_state_index is not None:
            self._jig_model_suite_state_index = self._model_suite_state_index
        elif jig_model_suite_state_index is None:
            self._jig_model_suite_state_index = 0
        else:
            self._jig_model_suite_state_index = jig_model_suite_state_index
        self._force_pool_surface_water_depth = force_pool_surface_water_depth

    def _intersect(self, other_constraint):
        (early_out, kwargs) = self._intersect_kwargs(other_constraint)
        if early_out is not None:
            return early_out
        return TentativeIntersection((self, other_constraint))._copy(**kwargs)

    def create_concrete_version(self, interaction):
        sim = interaction.sim
        if sim.in_pool:
            sim_pool = pool_utils.get_pool_by_block_id(sim.block_id)
            fallback_routing_surface = sim_pool.world_routing_surface
        elif sim.routing_surface.type != SurfaceType.SURFACETYPE_WORLD:
            fallback_routing_surface = SurfaceIdentifier(sim.routing_surface.primary_id, sim.routing_surface.secondary_id, SurfaceType.SURFACETYPE_WORLD)
        else:
            fallback_routing_surface = None
        participant_to_face = None
        facing_radius = None
        if self._face_participant is not None:
            participant_to_face = interaction.get_participant(self._face_participant.participant_to_face)
            facing_radius = self._face_participant.radius
        fgl_context = interactions.utils.routing.get_fgl_context_for_jig_definition(self._jig_definition, sim, ignore_sim=self._ignore_sim, fallback_routing_surface=fallback_routing_surface, stay_outside=self._stay_outside, object_id=self._object_id, participant_to_face=participant_to_face, facing_radius=facing_radius, stay_on_world=self._stay_on_world, use_intended_location=self._use_intended_location, model_suite_state_index=self._model_suite_state_index, force_pool_surface_water_depth=self._force_pool_surface_water_depth, min_water_depth=self._min_water_depth, max_water_depth=self._max_water_depth)
        chosen_routing_surface = fgl_context.search_strategy.start_routing_surface
        (translation, orientation) = find_good_location(fgl_context)
        if translation is None or orientation is None:
            logger.warn('Failed to find a good location for {}', interaction, owner='bhill')
            if self._is_soft_constraint:
                return ANYWHERE
            return Nowhere('ObjectJigConstraint.create_concrete_version, FGL failed to place the object jig. Interaction: {}', interaction)
        transform = sims4.math.Transform(translation, orientation)

        def create_jig_object(*_, **__):
            liability = interaction.get_liability(self.JIG_CONSTRAINT_LIABILITY)
            if liability is not None:
                if liability.jig.definition is not self._jig_definition:
                    logger.error('Interaction {} is tuned to have multiple jig constraints, which is not allowed.', interaction)
                if liability.constraint.tentative:
                    raise AssertionError("Liability should not have a tentative constraint, it's set just below this to a concrete constraint. [bhill]")
            else:
                from objects.jigs import Jig
                cls_override = self._jig_definition.cls
                if not issubclass(cls_override, Jig):
                    cls_override = Jig
                jig_object = objects.system.create_object(self._jig_definition, cls_override=cls_override, obj_state=self._jig_model_suite_state_index)
                jig_object.opacity = 0
                jig_object.move_to(translation=translation, orientation=orientation, routing_surface=chosen_routing_surface)
                liability = JigConstraint.JigConstraintLiability(jig_object, constraint=concrete_constraint, ignore_sim=sim, should_transfer=self._should_transfer_liability)
                interaction.add_liability(self.JIG_CONSTRAINT_LIABILITY, liability)

        concrete_constraint = self._get_concrete_constraint(transform, chosen_routing_surface, create_jig_object)
        return concrete_constraint

    def _get_concrete_constraint(self, transform, routing_surface, create_jig_fn):
        object_slots = self._jig_definition.get_slots_resource(self._jig_model_suite_state_index)
        slot_transform = object_slots.get_slot_transform_by_index(sims4.ObjectSlots.SLOT_ROUTING, 0)
        transform = sims4.math.Transform.concatenate(transform, slot_transform)
        return Transform(transform, routing_surface=routing_surface, create_jig_fn=create_jig_fn)

    @property
    def tentative(self):
        return True

class JigConstraint(ObjectJigConstraint):
    FACTORY_TUNABLES = {'jig': TunableReference(description='\n            The jig defining the constraint.\n            ', manager=services.definition_manager()), 'is_soft_constraint': Tunable(description='\n            If checked, then this constraint is merely a suggestion for the Sim.\n            Should FGL succeed and a good location is found for the jig, the Sim\n            will have to route to it in order to run the interaction. However,\n            should the jig be unable to be placed, then this constraint is\n            ignored and the Sim will be able to run the interaction from\n            wherever.\n            \n            If unchecked, then if the jig cannot be placed, a Nowhere constraint\n            is generated and the Sim will be unable to perform the interaction.\n            ', tunable_type=bool, default=False), 'stay_outside': Tunable(description='\n            Whether the jig can only be placed outside.\n            ', tunable_type=bool, default=False), 'face_participant': OptionalTunable(description='\n            If enabled, allows you to tune a participant and a radius around\n            the participant that the jig will face when placed. Keep in mind,\n            this does limit the possibilities for jig placement.\n            ', tunable=TunableTuple(description='\n                The participant to face and radius around that participant to\n                place the jig.\n                ', participant_to_face=TunableEnumEntry(description='\n                    The participant of the interaciton the jig should face when placed.\n                    ', tunable_type=ParticipantType, default=ParticipantType.Object), radius=Tunable(description='\n                    The valid radius around the provided participant where the\n                    jig should be placed.\n                    ', tunable_type=float, default=0))), 'stay_on_world': Tunable(description='\n            Jig placement will only consider positions on the world surface.\n            ', tunable_type=bool, default=False), 'use_intended_location': Tunable(description='\n            The jig constraint will be placed at the intended location if \n            checked.  Useful to disable for TeleportStyleInteractions which\n            want to place the jig somewhere near the Sim rather than where\n            they are going.\n            ', tunable_type=bool, default=True), 'model_suite_state_index': TunableRange(description='\n            For object definitions that use a suite of models (each w/ its own\n            model, rig, slots, slot resources, and footprint), switch the index\n            used in the suite.  For jigs, this changes the footprint used.\n            Counters are an example of objects that use a suite of models.\n            ', tunable_type=int, default=0, minimum=0)}

    def __init__(self, jig, is_soft_constraint, stay_outside, face_participant, stay_on_world, model_suite_state_index, use_intended_location, sim=None, target=None, **kwargs):
        super().__init__(jig, stay_outside=stay_outside, is_soft_constraint=is_soft_constraint, face_participant=face_participant, stay_on_world=stay_on_world, jig_model_suite_state_index=model_suite_state_index, use_intended_location=use_intended_location, **kwargs)

    def create_constraint(self, *args, **kwargs):
        return JigConstraint(self._jig_definition, self._is_soft_constraint, self._stay_outside, self._face_participant, self._stay_on_world, self._model_suite_state_index, self._use_intended_location, *args, **kwargs)

class ObjectPlacementConstraint(ObjectJigConstraint):
    FACTORY_TUNABLES = {'description': '\n            A constraint defined by a location on a specific jig object,\n            which will be placed when the constraint is bound and will\n            live for the duration of the interaction owning the constraint.\n            ', 'use_intended_location': Tunable(description='\n            If enabled, we will use the intended location of the relative\n            object when placing this object. That means we use their intended\n            location to start the FGL search from, and the routing surface to\n            start with.\n            ', tunable_type=bool, default=True), 'model_suite_state_index': TunableRange(description='\n            For object definitions that use a suite of models (each w/ its own\n            model, rig, slots, slot resources, and footprint), switch the index\n            used in the suite.  For jigs, this changes the footprint used.\n            For object definitions that use a suite of models\n            ', tunable_type=int, default=0, minimum=0), 'force_pool_surface_water_depth': OptionalTunable(description='\n            (float) If provided, and the starting point for the FGL is not already on\n            the pool (or ocean) surface, water depths greater than this value\n            will force the use of the pool routing surface.\n            ', tunable=TunableTuple(description='\n                Settings for forced use of pool routing surface.\n                ', water_depth=Tunable(description='\n                    Value of the min water depth allowed.\n                    ', tunable_type=float, default=-1.0), model_suite_state_index=OptionalTunable(description='\n                    For object definitions that use a suite of models (each w/ its own\n                    model, rig, slots, slot resources, and footprint), switch the index\n                    used in the suite.  For jigs, this changes the footprint used.\n                    For object definitions that use a suite of models\n                    ', tunable=TunableRange(description='\n                        Index to use.\n                        ', tunable_type=int, default=0, minimum=0)))), 'min_water_depth': OptionalTunable(description='\n            (float) If provided, minimum water depth where the object can be placed\n            ', tunable=Tunable(description='\n                Value of the min water depth allowed.\n                ', tunable_type=float, default=0.0)), 'max_water_depth': OptionalTunable(description='\n            (float) If provided, maximum water depth where the object can be placed\n            ', tunable=Tunable(description='\n                Value of the max water depth allowed.\n                ', tunable_type=float, default=0.0))}

    def __init__(self, use_intended_location, jig_definition=None, model_suite_state_index=0, force_pool_surface_water_depth=None, min_water_depth=None, max_water_depth=None, sim=None, target=None, object_id=None, **kwargs):
        if target is not None:
            jig_definition = target.definition if jig_definition is None else jig_definition
            object_id = target.id if object_id is None else object_id
            jig_model_suite_state_index = model_suite_state_index
        else:
            jig_model_suite_state_index = None
        super().__init__(jig_definition, object_id=object_id, should_transfer_liability=False, use_intended_location=use_intended_location, model_suite_state_index=model_suite_state_index, jig_model_suite_state_index=jig_model_suite_state_index, force_pool_surface_water_depth=force_pool_surface_water_depth, min_water_depth=min_water_depth, max_water_depth=max_water_depth, **kwargs)

    def create_constraint(self, *args, **kwargs):
        return ObjectPlacementConstraint(self._use_intended_location, self._jig_definition, self._model_suite_state_index, self._force_pool_surface_water_depth, self._min_water_depth, self._max_water_depth, *args, ignore_sim=False, object_id=self._object_id, **kwargs)

    def _get_concrete_constraint(self, transform, routing_surface, create_jig_fn):
        footprint = self._jig_definition.get_footprint(0 if self._jig_model_suite_state_index is None else self._jig_model_suite_state_index)
        compound_polygon = placement.get_placement_footprint_compound_polygon(transform.translation, transform.orientation, routing_surface, footprint)
        radius = compound_polygon.radius()
        circle = Circle(transform.translation, radius + 0.5, routing_surface, ideal_radius=radius, allow_small_intersections=True, create_jig_fn=create_jig_fn)
        return circle.intersect(Facing(target_position=transform.translation))

class RelativeCircleConstraint(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'minimum_radius': OptionalTunable(description='\n            If enabled, the generated constraint will have a radius no smaller\n            than the specified amount.\n            ', tunable=TunableRange(description="\n                The constraint's minimum radius.\n                ", tunable_type=float, minimum=0, default=1)), 'maximum_radius': OptionalTunable(description='\n            If enabled, the generated constraint will have a radius no larger\n            that the specified amount.\n            ', tunable=TunableRange(description="\n                The constraint's maximum radius.\n                ", tunable_type=float, minimum=0, default=1)), 'relative_radius': TunableRange(description="\n            The constraint's radius relative to the size of the object. This is\n            a simple multiplier applied to the area generated by the object's\n            footprint\n            ", tunable_type=float, minimum=1, default=1), 'relative_ideal_radius': OptionalTunable(description="\n            If enabled, specify an ideal radius relative to the constraint's\n            radius. \n            ", tunable=TunableTuple(description='\n                Ideal radius data.\n                ', radius=TunableRange(description="\n                    The constraint's relative ideal radius. A value of 1 would\n                    mean the ideal location is on the outskirt of the\n                    constraint; values towards 0 approach the constraint's\n                    center.\n                    ", tunable_type=float, minimum=0, maximum=1, default=1), width=Tunable(description='\n                    This creates a band around the ideal_radius that also scores\n                    to 1 instead of starting to fall off to 0 in scoring. ex: If\n                    you have a circle of radius 5, with an ideal_radius of 2.5,\n                    and a ideal_radius_width of 0.5, any goals in the radius 2\n                    to radius 3 range will all score optimially.\n                    ', tunable_type=float, default=0))), 'multi_surface': Tunable(description='\n            If enabled, this constraint will be considered for multiple surfaces.\n            \n            Example: You want a circle\n            constraint that can be both inside\n            and outside of a pool.\n            ', tunable_type=bool, default=False), 'enables_height_scoring': Tunable(description='\n            If enabled, this constraint will score goals using the height of\n            the surface.  The higher the goal the cheaper it is.\n            ', tunable_type=bool, default=False)}

    def create_constraint(self, sim, target, **kwargs):
        footprint = target.definition.get_footprint() if target is not None and target.definition is not None else None
        if footprint is not None:
            compound_polygon = placement.get_placement_footprint_compound_polygon(target.position, target.orientation, target.routing_surface, footprint)
            if compound_polygon:
                radius = compound_polygon.radius()*self.relative_radius
                if self.minimum_radius is not None:
                    radius = max(self.minimum_radius, radius)
                if self.maximum_radius is not None:
                    radius = min(self.maximum_radius, radius)
                ideal_radius = None if self.relative_ideal_radius is None else radius*self.relative_ideal_radius.radius
                ideal_radius_width = 0 if self.relative_ideal_radius is None else self.relative_ideal_radius.width
                return Circle(compound_polygon.centroid(), radius, target.routing_surface, ideal_radius=ideal_radius, ideal_radius_width=ideal_radius_width, multi_surface=self.multi_surface, enables_height_scoring=self.enables_height_scoring)
        logger.warn('Object {} does not support relative circle constraints, possibly because it has no footprint. Using Anywhere instead.', target, owner='epanero')
        return Anywhere()

class WaterDepthConstraint(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'min_water_depth': OptionalTunable(description='\n            (float) If provided, each vertex of the test polygon along with its centroid will\n            be tested to determine whether the ocean water at the test location is at least this deep.\n            Values <= 0 indicate placement on land is valid.\n            ', tunable=Tunable(description='\n                Value of the min water depth allowed.\n                ', tunable_type=float, default=-1.0)), 'max_water_depth': OptionalTunable(description='\n            (float) If provided, each vertex of the test polygon along with its centroid will\n            be tested to determine whether the ocean water at the test location is at most this deep.\n            Values <= 0 indicate placement in ocean is invalid.\n            ', tunable=Tunable(description='\n                Value of the max water depth allowed.\n                ', tunable_type=float, default=1000.0))}

    def create_constraint(self, *args, **kwargs):
        if self.min_water_depth is None and self.max_water_depth is None:
            return ANYWHERE
        if self.min_water_depth is not None and self.max_water_depth is not None and self.max_water_depth < self.min_water_depth:
            return Nowhere()
        return Constraint(min_water_depth=self.min_water_depth, max_water_depth=self.max_water_depth)

class WaterDepthIntervalConstraint(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'interval': TunableEnumEntry(description="\n            Test if a Sim should be walking, wading or swimming based on the water\n            height offset at a target location and the Sim's wading interval data.\n            ", tunable_type=WaterDepthIntervals, default=WaterDepthIntervals.WALK)}

    @staticmethod
    def create_water_depth_interval_constraint(sim, interval):
        wading_interval = OceanTuning.get_actor_wading_interval(sim) if sim is not None else None
        min_water_depth = None
        max_water_depth = None
        if wading_interval is None:
            max_water_depth = 0
        elif interval == WaterDepthIntervals.WALK:
            max_water_depth = wading_interval.lower_bound
        elif interval == WaterDepthIntervals.WET:
            min_water_depth = 0
            max_water_depth = wading_interval.lower_bound
        elif interval == WaterDepthIntervals.WADE:
            min_water_depth = wading_interval.lower_bound
            max_water_depth = wading_interval.upper_bound
        elif interval == WaterDepthIntervals.SWIM:
            min_water_depth = wading_interval.upper_bound
        return Constraint(min_water_depth=min_water_depth, max_water_depth=max_water_depth)

    def create_constraint(self, sim, target, **kwargs):
        return WaterDepthIntervalConstraint.create_water_depth_interval_constraint(sim, self.interval)

class TerrainMaterialConstraint(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'terrain_tags': OptionalTunable(description='\n            If enabled, a set of allowed terrain tags. At least one tag must\n            match the terrain under each vertex of the footprint of the supplied\n            object.\n            ', tunable=TunableEnumSet(enum_type=TerrainTag, enum_default=TerrainTag.INVALID, invalid_enums=(TerrainTag.INVALID,)))}

    def create_constraint(self, *args, **kwargs):
        return Constraint(terrain_tags=self.terrain_tags)

class OceanStartLocationConstraint(TunedCircle):

    def __init__(self, interval, radius, ideal_radius, ideal_radius_width, require_los, radial_cost_weight, multi_surface, enables_height_scoring):
        super().__init__(radius, ideal_radius, ideal_radius_width, require_los, radial_cost_weight, multi_surface, enables_height_scoring)
        self._interval = interval

    @staticmethod
    def create_simple_constraint(interval, radius, sim, target=None, target_position=DEFAULT, routing_surface=DEFAULT, relative_offset_vector=DEFAULT, **kwargs):
        if not (target is None or target.is_in_inventory() or target.is_sim):
            target = sim
        ocean = services.terrain_service.ocean_object()
        if ocean is not None and target is not None and target.is_sim:
            if target_position is DEFAULT:
                target_position = target.intended_position
            extended_species = sim.extended_species
            age = sim.age
            starting_location = ocean.get_nearest_constraint_start_location(extended_species, age, target_position, interval)
            if starting_location is not None:
                starting_transform = starting_location.transform
                starting_position = starting_transform.translation
                if relative_offset_vector is not None:
                    offset_vector = starting_transform.transform_vector(relative_offset_vector)
                    starting_position = starting_transform.translation + offset_vector
                if relative_offset_vector is not DEFAULT and routing_surface is DEFAULT:
                    routing_surface = starting_location.routing_surface
                return Circle(starting_position, radius, routing_surface, **kwargs)
        return Nowhere('OceanStartLocationConstraint needs a Sim and an Ocean, cannot use {} with ocean {}', sim, ocean)

    def create_constraint(self, sim, target=None, target_position=DEFAULT, routing_surface=DEFAULT, relative_offset=DEFAULT, **kwargs):
        if not (target is None or target.is_in_inventory() or target.is_sim):
            target = sim
        los_reference_point = DEFAULT if self._require_los else None
        return OceanStartLocationConstraint.create_simple_constraint(self._interval, self.radius, target, target_position=target_position, routing_surface=routing_surface, ideal_radius=self.ideal_radius, ideal_radius_width=self.ideal_radius_width, radial_cost_weight=self._radial_cost_weight, los_reference_point=los_reference_point, multi_surface=self._multi_surface, enables_height_scoring=self._enables_height_scoring, **kwargs)

class TunableOceanStartLocationConstraint(TunableCircle):
    FACTORY_TYPE = OceanStartLocationConstraint

    def __init__(self, radius, description='A tunable type for creating Circle constraints at the nearest Ocean location.', callback=None, **kwargs):
        super().__init__(radius, interval=TunableEnumEntry(description="\n                Select the depth for the Sim based on the water\n                height offset at a target location and the Sim's wading interval data.\n                ", tunable_type=WaterDepthIntervals, default=WaterDepthIntervals.WET), description=description, **kwargs)

class PortalConstraint(HasTunableSingletonFactory, AutoFactoryInit):
    PORTAL_DIRECTION_THERE = 0
    PORTAL_DIRECTION_BACK = 1
    PORTAL_LOCATION_ENTRY = 0
    PORTAL_LOCATION_EXIT = 1
    FACTORY_TUNABLES = {'portal_type': TunableReference(description='\n            A reference to the type of portal to use for the constraint.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('PortalData',)), 'portal_direction': TunableVariant(description='\n            Choose between the There and Back of the portal. This will not work\n            properly if the portal is missing a Back and Back is specified here.\n            ', locked_args={'there': PORTAL_DIRECTION_THERE, 'back': PORTAL_DIRECTION_BACK}, default='there'), 'portal_location': TunableVariant(description='\n            Choose between the entry and exit of a portal direction.\n            ', locked_args={'entry': PORTAL_LOCATION_ENTRY, 'exit': PORTAL_LOCATION_EXIT}, default='entry'), 'sub_constraint': OptionalTunable(description='\n            If enabled, specify a specific type of constraint to create at the\n            location of the portal.\n            \n            If disabled then the constraint will just be a location constraint\n            at the location of the portal.\n            ', tunable=TunableVariant(description='\n                The types of constraints that can be created at the location\n                of the portal.\n                ', circle=TunableCircle(description='\n                    A circle constraint that is created at the location of the\n                    portal.\n                    ', radius=3), cone=TunableCone(description='\n                    A cone constraint that is created at the location of the \n                    portal.\n                    ', min_radius=0, max_radius=1, angle=sims4.math.PI), default='circle'))}

    def _build_location_constraint(self, location):
        return Position(location.position, routing_surface=location.routing_surface)

    def _build_sub_constraint(self, sim, target, location):
        return self.sub_constraint.create_constraint(sim, target=target, target_position=location.position, routing_surface=location.routing_surface)

    def create_constraint(self, sim, target=None, **kwargs):
        if target is None:
            return Nowhere('Trying to create a portal constraint without specifying the portal object.')
        portal_component = target.get_component(PORTAL_COMPONENT)
        if portal_component is None:
            return Nowhere("Trying to create a portal constraint using {} which doesn't have a portal component.".format(target))
        location = portal_component.get_portal_location_by_type(self.portal_type, self.portal_direction, self.portal_location)
        if location is None:
            return Nowhere('Unable to find a matching portal location as tuned on object {} with type {}'.format(target, self.portal_type))
        if self.sub_constraint is None:
            return self._build_location_constraint(location)
        return self._build_sub_constraint(sim, target, location)
