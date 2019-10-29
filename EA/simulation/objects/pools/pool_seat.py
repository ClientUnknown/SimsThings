from _animation import get_joint_transform_from_rigfrom _math import Transformfrom animation.arb_element import ArbElementfrom build_buy import get_block_idfrom objects.game_object import GameObjectfrom routing import RAYCAST_HIT_TYPE_NONEfrom sims4.utils import constpropertyfrom singletons import UNSETimport cachesimport postures.posture_graphimport servicesimport sims4.mathSWIM_POSTURE_NAME = 'swim'
class PoolSeat(GameObject):

    def __init__(self, *args, pool=None, **kwargs):
        self._data = None
        self._joint_transform = None
        self._children_cache = None
        self._adjacent_parts = UNSET
        self.overlapping_parts = []
        self.part_owner = pool
        self._cached_locations_for_posture_world = None
        self._cached_locations_for_posture_pool = None
        self._cached_position_and_routing_surface_for_posture_world = None
        self._cached_position_and_routing_surface_for_posture_pool = None
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return '<part {} on {}>'.format(self.part_group_index, self.part_owner)

    def __str__(self):
        return '{}[{}]'.format(self.part_owner, self.part_group_index)

    @property
    def adjacent_parts(self):
        return self._adjacent_parts

    @adjacent_parts.setter
    def adjacent_parts(self, new_value):
        if self._adjacent_parts != new_value:
            self._adjacent_parts = new_value
            if any(part._adjacent_parts is UNSET for part in self.part_owner.parts):
                return
            posture_graph_service = services.current_zone().posture_graph_service
            with posture_graph_service.object_moving(self.part_owner):
                pass

    @property
    def part_owner(self):
        return self._part_owner

    @part_owner.setter
    def part_owner(self, value):
        self._part_owner = value
        if value is None:
            self.part_group_index = 0
        else:
            value._parts.append(self)
            self.part_group_index = value._parts.index(self)

    @constproperty
    def is_part():
        return True

    @property
    def part_definition(self):
        pass

    @property
    def disable_sim_aop_forwarding(self):
        return True

    @property
    def disable_child_aop_forwarding(self):
        return True

    @property
    def forward_direction_for_picking(self):
        return sims4.math.Vector3.Z_AXIS()

    @property
    def is_base_part(self):
        return True

    @property
    def subroot_index(self):
        pass

    @property
    def part_suffix(self):
        pass

    @property
    def transform(self):
        if self._joint_transform is None:
            try:
                self._joint_transform = get_joint_transform_from_rig(self.rig, ArbElement._BASE_ROOT_STRING)
            except KeyError:
                raise KeyError('Unable to find joint {} on {}'.format(ArbElement._BASE_ROOT_STRING, self))
        return Transform.concatenate(self._joint_transform, self._location.world_transform)

    @transform.setter
    def transform(self, transform):
        self.move_to(transform=transform)

    @property
    def can_reset(self):
        return True

    @property
    def block_id(self):
        return get_block_id(self.zone_id, self._location.transform.translation + self.forward, self.portal_exit_routing_surface.secondary_id - 1)

    @caches.cached(maxsize=20)
    def check_line_of_sight(self, *args, verbose=False, **kwargs):
        if verbose:
            return (RAYCAST_HIT_TYPE_NONE, [])
        return RAYCAST_HIT_TYPE_NONE

    def adjacent_parts_gen(self):
        if self.adjacent_parts:
            yield from self.adjacent_parts

    def has_adjacent_part(self, sim):
        if not self.adjacent_parts:
            return False
        return any(part.may_reserve(sim) for part in self.adjacent_parts)

    def get_overlapping_parts(self):
        return self.overlapping_parts[:]

    def is_mirrored(self, part=None):
        if part is None:
            return False
        offset = part.position - self.position
        return sims4.math.vector_cross_2d(self.forward, offset) < 0

    def supports_posture_spec(self, posture_spec, interaction=None, sim=None):
        if interaction is not None and interaction.is_super:
            affordance = interaction.affordance
            if affordance.requires_target_support and not self.supports_affordance(affordance):
                return False
        if not self.supported_posture_types:
            return True
        if posture_spec.body is None:
            return False
        for supported_posture_info in self.supported_posture_types:
            if posture_spec.body_posture is supported_posture_info.posture_type:
                return True
        return False

    def get_bounding_box(self):
        p = self.transform.translation
        p = sims4.math.Vector2(p.x, p.z)
        return sims4.geometry.QtRect(p + sims4.math.Vector2(-0.5, -0.5), p + sims4.math.Vector2(0.5, 0.5))

    def get_surface_override_for_posture(self, source_posture_name):
        (_, pool_location) = self.get_single_portal_locations()
        if source_posture_name == SWIM_POSTURE_NAME:
            if pool_location is not None:
                return pool_location.routing_surface
            else:
                return

    def _compute_locations_for_posture(self):
        (world_location, pool_location) = self.get_single_portal_locations()
        if world_location is None or pool_location is None:
            return ((), ())
        return ((world_location,), (pool_location,))

    def _get_cached_locations_for_posture(self, node):
        if node == postures.posture_graph.SWIM_AT_NONE:
            return self._cached_locations_for_posture_pool
        return self._cached_locations_for_posture_world

    def _cache_and_return_locations_for_posture(self, node):
        self.get_locations_for_posture = self._get_cached_locations_for_posture
        (self._cached_locations_for_posture_world, self._cached_locations_for_posture_pool) = self._compute_locations_for_posture()
        return self.get_locations_for_posture(node)

    def _compute_position_and_routing_surface_for_posture(self):
        (world_location, pool_location) = self.get_single_portal_locations()
        if world_location is None or pool_location is None:
            return ((), ())
        return (((world_location.position, world_location.routing_surface),), ((pool_location.position, pool_location.routing_surface),))

    def _get_cached_position_and_routing_surface_for_posture(self, node):
        if node == postures.posture_graph.SWIM_AT_NONE:
            return self._cached_position_and_routing_surface_for_posture_pool
        return self._cached_position_and_routing_surface_for_posture_world

    def _cache_and_return_position_and_routing_surface_for_posture(self, node):
        self.get_position_and_routing_surface_for_posture = self._get_cached_position_and_routing_surface_for_posture
        (self._cached_position_and_routing_surface_for_posture_world, self._cached_position_and_routing_surface_for_posture_pool) = self._compute_position_and_routing_surface_for_posture()
        return self.get_position_and_routing_surface_for_posture(node)

    def mark_get_locations_for_posture_needs_update(self):
        self.get_locations_for_posture = self._cache_and_return_locations_for_posture
        self.get_position_and_routing_surface_for_posture = self._cache_and_return_position_and_routing_surface_for_posture

    def on_owner_location_changed(self):
        self.mark_get_locations_for_posture_needs_update()

    def on_proxied_object_removed(self):
        pass
