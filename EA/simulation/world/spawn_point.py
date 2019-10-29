from sims4.tuning.tunable import TunableEnumEntryfrom tag import Tagfrom world.spawn_point_enums import SpawnPointPriority, SpawnPointRequestReasonimport enumimport id_generatorimport placementimport routingimport servicesimport sims4.loglogger = sims4.log.Logger('Spawn Points', default_owner='rmccord')
class SpawnPointOption(enum.Int):
    SPAWN_ANY_POINT_WITH_CONSTRAINT_TAGS = 0
    SPAWN_SAME_POINT = 1
    SPAWN_ANY_POINT_WITH_SAVED_TAGS = 2
    SPAWN_DIFFERENT_POINT_WITH_SAVED_TAGS = 3

class SpawnPoint:
    ARRIVAL_SPAWN_POINT_TAG = TunableEnumEntry(description='\n        The Tag associated with Spawn Points at the front of the lot.\n        ', tunable_type=Tag, default=Tag.INVALID)
    VISITOR_ARRIVAL_SPAWN_POINT_TAG = TunableEnumEntry(description='\n        The Tag associated with Spawn Points nearby the lot for visitors.\n        ', tunable_type=Tag, default=Tag.INVALID)

    def __init__(self, lot_id, zone_id, spawn_point_id=None, routing_surface=None):
        self.lot_id = lot_id
        if routing_surface is None:
            routing_surface = routing.SurfaceIdentifier(zone_id, 0, routing.SurfaceType.SURFACETYPE_WORLD)
        self._routing_surface = routing_surface
        if spawn_point_id is None:
            self._spawn_point_id = id_generator.generate_object_id()
        else:
            self._spawn_point_id = spawn_point_id
        self.attractor_point_ids = set()

    def __str__(self):
        return 'Name:{:20} Lot:{:15} Center:{:45} Tags:{}'.format(self.get_name(), self.lot_id, str(self.get_approximate_center()), self.get_tags())

    def on_add(self):
        self._add_goal_suppression_region()
        self.attractor_point_ids = services.object_manager().create_spawn_point_attractor(self)

    def on_remove(self):
        self._remove_goal_suppression_region()
        for attractor_point_id in self.attractor_point_ids:
            services.object_manager().destroy_dynamic_attractor_object(attractor_point_id)

    @property
    def spawn_point_id(self):
        return self._spawn_point_id

    @property
    def obj_def_guid(self):
        pass

    def get_approximate_transform(self):
        raise NotImplementedError

    @property
    def routing_surface(self):
        return self._routing_surface

    @property
    def spawn_point_priority(self):
        return SpawnPointPriority.DEFAULT

    def get_tags(self):
        raise NotImplementedError

    def has_tag(self, tag):
        if tag is not None:
            return tag in self.get_tags()
        else:
            return False

    def is_valid(self, sim_info=None, spawn_point_request_reason=SpawnPointRequestReason.DEFAULT):
        return True

    def get_approximate_center(self):
        raise NotImplementedError

    def get_name(self):
        raise NotImplementedError

    def next_spawn_spot(self):
        raise NotImplementedError

    def validate_connectivity(self, dest_handles):
        raise NotImplementedError

    def get_valid_and_invalid_positions(self):
        raise NotImplementedError

    def get_position_constraints(self, generalize=False):
        raise NotImplementedError

    def get_footprint_polygon(self):
        pass

    def _add_goal_suppression_region(self):
        footprint_polygon = self.get_footprint_polygon()
        if footprint_polygon is None:
            return
        services.sim_quadtree().insert(self, self.spawn_point_id, placement.ItemType.ROUTE_GOAL_PENALIZER, footprint_polygon, self.routing_surface, False, 0)

    def _remove_goal_suppression_region(self):
        services.sim_quadtree().remove(self.spawn_point_id, placement.ItemType.ROUTE_GOAL_PENALIZER, 0)
