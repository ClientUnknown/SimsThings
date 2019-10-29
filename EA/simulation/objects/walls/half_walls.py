from objects.game_object import GameObjectfrom sims4.utils import constpropertyimport routing
class HalfWall(GameObject):
    LOCATION_OFFSET = 0.25

    def __init__(self, definition, **kwargs):
        super().__init__(definition, **kwargs)
        self._cached_locations_for_posture = None
        self._cached_position_and_routing_surface_for_posture = None

    @property
    def _use_locations_for_posture_for_connect_to_sim_test(self):
        return True

    @constproperty
    def is_valid_for_height_checks():
        return False

    def _compute_locations_for_posture(self):
        return (routing.Location(self.position + self.forward*self.LOCATION_OFFSET, self.orientation, self.routing_surface), routing.Location(self.position - self.forward*self.LOCATION_OFFSET, self.orientation, self.routing_surface))

    def _get_cached_locations_for_posture(self, node):
        return self._cached_locations_for_posture

    def _cache_and_return_locations_for_posture(self, node):
        self.get_locations_for_posture = self._get_cached_locations_for_posture
        self._cached_locations_for_posture = self._compute_locations_for_posture()
        return self._cached_locations_for_posture

    def _compute_position_and_routing_surface_for_posture(self):
        return ((self.position + self.forward*self.LOCATION_OFFSET, self.routing_surface), (self.position - self.forward*self.LOCATION_OFFSET, self.routing_surface))

    def _get_cached_position_and_routing_surface_for_posture(self, node):
        return self._cached_position_and_routing_surface_for_posture

    def _cache_and_return_position_and_routing_surface_for_posture(self, node):
        self.get_position_and_routing_surface_for_posture = self._get_cached_position_and_routing_surface_for_posture
        self._cached_position_and_routing_surface_for_posture = self._compute_position_and_routing_surface_for_posture()
        return self._cached_position_and_routing_surface_for_posture

    def mark_get_locations_for_posture_needs_update(self):
        self.get_locations_for_posture = self._cache_and_return_locations_for_posture
        self.get_position_and_routing_surface_for_posture = self._cache_and_return_position_and_routing_surface_for_posture
