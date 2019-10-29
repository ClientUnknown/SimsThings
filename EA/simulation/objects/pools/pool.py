from animation.posture_manifest_constants import STAND_AT_NONE_CONSTRAINT, SWIM_AT_NONE_CONSTRAINTfrom interactions.constraints import Constraintfrom objects.game_object import GameObjectfrom objects.pools.pool_utils import cached_pool_objectsfrom objects.pools.swimming_mixin import SwimmingMixinfrom routing import RAYCAST_HIT_TYPE_NONEfrom singletons import DEFAULTimport build_buyimport cachesimport objects.componentsimport routingimport sims4.geometryimport sims4.loglogger = sims4.log.Logger('Pools', default_owner='bhill')
class SwimmingPool(SwimmingMixin, GameObject):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parts = []
        self._old_footprint_component = self.remove_component(objects.components.types.FOOTPRINT_COMPONENT)
        self._bounding_polygon = None
        self._center_point = None

    @classmethod
    def _verify_tuning_callback(cls):
        super()._verify_tuning_callback()
        if cls._has_reservation_tests:
            logger.error("Interactions with object reservation tests have been tuned on the swimming pool.\nThis is not okay because it will make performance horribly bad. (For every pool seat, we have to look at every other pool seat).\nPlease remove {} from the pool's super interaction list or remove their object reservation tests.", ', '.join(str(sa) for sa in cls._super_affordances if sa.object_reservation_tests), owner='bhill')

    def on_add(self):
        super().on_add()
        cached_pool_objects.add(self)

    def on_remove(self):
        super().on_remove()
        cached_pool_objects.discard(self)

    def try_mark_as_new_object(self):
        pass

    def on_location_changed(self, old_location):
        if self._location.routing_surface.type == routing.SurfaceType.SURFACETYPE_POOL:
            self._build_routing_surfaces()
            self._create_bounding_polygon()
        super().on_location_changed(old_location)

    @property
    def remove_children_from_posture_graph_on_delete(self):
        return False

    def get_users(self, *args, **kwargs):
        return set()

    def get_edges(self):
        pool_edges = build_buy.get_pool_edges(self.zone_id)
        return pool_edges[(self.block_id, self.routing_surface.secondary_id)]

    def get_edge_constraint(self, constraint_width=1.0, inward_dir=False, return_constraint_list=False, los_reference_point=DEFAULT, sim=None):
        edges = self.get_edges()
        polygons = []
        for (start, stop) in edges:
            along = sims4.math.vector_normalize(stop - start)
            inward = sims4.math.vector3_rotate_axis_angle(along, sims4.math.PI/2, sims4.math.Vector3.Y_AXIS())
            if inward_dir:
                polygon = sims4.geometry.Polygon([start, start + constraint_width*inward, stop + constraint_width*inward, stop])
            else:
                polygon = sims4.geometry.Polygon([start, stop, stop - constraint_width*inward, start - constraint_width*inward])
            polygons.append(polygon)
        if inward_dir:
            constraint_spec = SWIM_AT_NONE_CONSTRAINT
            routing_surface = self.provided_routing_surface
        else:
            constraint_spec = STAND_AT_NONE_CONSTRAINT
            routing_surface = self.world_routing_surface
        if return_constraint_list:
            constraint_list = []
            for polygon in polygons:
                restricted_polygon = sims4.geometry.RestrictedPolygon(polygon, ())
                constraint = Constraint(routing_surface=routing_surface, geometry=restricted_polygon, los_reference_point=los_reference_point)
                constraint = constraint.intersect(constraint_spec)
                constraint_list.append(constraint)
            return constraint_list
        else:
            geometry = sims4.geometry.RestrictedPolygon(sims4.geometry.CompoundPolygon(polygons), ())
            constraint = Constraint(routing_surface=routing_surface, geometry=geometry)
            constraint = constraint.intersect(constraint_spec)
            return constraint

    def _get_bounds(self):
        edges = self.get_edges()
        return sims4.math.get_bounds_2D([edge_tuple[0] for edge_tuple in edges])

    def _create_bounding_polygon(self):
        (lower_bounds, upper_bounds) = self._get_bounds()
        ll = sims4.math.Vector3(lower_bounds[0], 0, lower_bounds[1])
        lr = sims4.math.Vector3(lower_bounds[0], 0, upper_bounds[1])
        ul = sims4.math.Vector3(upper_bounds[0], 0, lower_bounds[1])
        ur = sims4.math.Vector3(upper_bounds[0], 0, upper_bounds[1])
        self._bounding_polygon = sims4.geometry.Polygon((ul, ur, lr, ll))
        self._find_center()

    @property
    def bounding_polygon(self):
        return self._bounding_polygon

    def _find_center(self):
        bounding_points = list(self._bounding_polygon)
        upper_left = bounding_points[0]
        lower_left = bounding_points[3]
        lower_right = bounding_points[2]
        center_x = upper_left.x - (upper_left.x - lower_left.x)/2
        center_z = lower_left.z - (lower_left.z - lower_right.z)/2
        self._center_point = sims4.math.Vector2(center_x, center_z)

    @property
    def center_point(self):
        return self._center_point

    @property
    def block_id(self):
        return build_buy.get_block_id(self.zone_id, self._location.transform.translation, self.provided_routing_surface.secondary_id - 1)

    @caches.cached(maxsize=20)
    def check_line_of_sight(self, *args, verbose=False, **kwargs):
        if verbose:
            return (RAYCAST_HIT_TYPE_NONE, [])
        return RAYCAST_HIT_TYPE_NONE
