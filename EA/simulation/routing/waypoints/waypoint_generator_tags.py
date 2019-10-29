import operatorfrom interactions.constraints import Circlefrom routing.waypoints.waypoint_generator import _WaypointGeneratorBasefrom sims4.tuning.geometric import TunableDistanceSquaredfrom sims4.tuning.tunable import TunableRange, TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, OptionalTunable, Tunablefrom tag import TunableTagsimport services
class _WaypointObjectDefaultStrategy(HasTunableSingletonFactory, AutoFactoryInit):

    def get_waypoint_objects(self, obj_list):
        return obj_list

class _WaypointObjectSortedDistanceStrategy(HasTunableSingletonFactory, AutoFactoryInit):

    def get_waypoint_objects(self, obj_list):
        sorted_list = sorted(obj_list, key=operator.attrgetter('position.x'))
        return sorted_list

class _WaypointGeneratorMultipleObjectByTag(_WaypointGeneratorBase):
    FACTORY_TUNABLES = {'object_max_distance': TunableDistanceSquared(description='\n            The maximum distance to check for an object as the next target\n            of our waypoint interaction.\n            ', default=5), 'constrain_radius': TunableRange(description='\n            The radius of the circle that will be generated around the objects\n            where the waypoints will be generated.\n            ', tunable_type=float, default=5, minimum=0), 'object_tags': TunableTags(description='\n            Find all of the objects based on these tags.\n            ', filter_prefixes=('func',)), 'object_search_strategy': TunableVariant(description='\n            Search strategies to find and soft the possible objects where the\n            waypoints will be generated.\n            ', default_waypoints=_WaypointObjectDefaultStrategy.TunableFactory(), sorted_by_distance=_WaypointObjectSortedDistanceStrategy.TunableFactory(), default='default_waypoints'), 'placement_restriction': OptionalTunable(description='\n            If enabled the objects where the waypoints will be generated will\n            be restricted to either the inside of outside.\n            ', tunable=Tunable(description='\n                If checked objects will be restricted to the inside the \n                house, otherwise only objects outside will be considered.\n                ', tunable_type=bool, default=True), enabled_name='inside_only', disabled_name='no_restrictions')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim = self._context.sim
        self._valid_objects = []
        for obj in services.object_manager().get_objects_matching_tags(self.object_tags, match_any=True):
            if self.placement_restriction is not None and self.placement_restriction == obj.is_outside:
                pass
            else:
                distance_from_sim = obj.position - self._sim.position
                if distance_from_sim.magnitude_squared() <= self.object_max_distance and obj.is_connected(self._sim):
                    self._valid_objects.append(obj)
        self._valid_objects = self.object_search_strategy.get_waypoint_objects(self._valid_objects)
        if not self._valid_objects:
            self._start_constraint = Circle(self._sim.position, self.constrain_radius, routing_surface=self._sim.routing_surface, los_reference_point=None)
            return
        starting_object = self._valid_objects.pop(0)
        self._start_constraint = Circle(starting_object.position, self.constrain_radius, routing_surface=self._sim.routing_surface, los_reference_point=None)
        self._start_constraint = self._start_constraint.intersect(self.get_water_constraint())

    def get_start_constraint(self):
        return self._start_constraint

    def get_waypoint_constraints_gen(self, routing_agent, waypoint_count):
        water_constraint = self.get_water_constraint()
        for _ in range(waypoint_count - 1):
            if not self._valid_objects:
                return
            obj = self._valid_objects.pop(0)
            next_constraint_circle = Circle(obj.position, self.constrain_radius, los_reference_point=None, routing_surface=obj.routing_surface)
            next_constraint_circle = next_constraint_circle.intersect(water_constraint)
            yield next_constraint_circle
