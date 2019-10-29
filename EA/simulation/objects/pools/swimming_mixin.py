import routing
class SwimmingMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._provided_routing_surface = None
        self._world_routing_surface = None

    def is_routing_surface_overlapped_at_position(self, _):
        return False

    @property
    def provided_routing_surface(self):
        return self._provided_routing_surface

    @property
    def world_routing_surface(self):
        return self._world_routing_surface

    def _build_routing_surfaces(self):
        self._provided_routing_surface = routing.SurfaceIdentifier(self.zone_id, self._location.world_routing_surface.secondary_id, routing.SurfaceType.SURFACETYPE_POOL)
        self._world_routing_surface = routing.SurfaceIdentifier(self.zone_id, self._location.world_routing_surface.secondary_id, routing.SurfaceType.SURFACETYPE_WORLD)
