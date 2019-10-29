from interactions.constraints import Circle, Nowherefrom routing.waypoints.waypoint_generator import _WaypointGeneratorBasefrom sims4.geometry import random_uniform_points_in_compound_polygonfrom sims4.tuning.tunable import TunableRange
class _WaypointGeneratorObjectPoints(_WaypointGeneratorBase):
    FACTORY_TUNABLES = {'object_constraint_radius': TunableRange(description='\n            The radius, in meters, of the generated constraint around the \n            target object where the waypoints will be generated.\n            ', tunable_type=float, default=3, minimum=0), 'waypoint_constraint_radius': TunableRange(description='\n            The radius, in meters, for each generated waypoint inside the \n            object constraint radius for the Sim to route to.\n            ', tunable_type=float, default=1, minimum=1)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._target is None:
            self._start_constraint = Nowhere('Trying to generate a waypoint constraint without a target.')
            self._los_reference_point = None
        else:
            self._los_reference_point = self._target.position
            if self._target.is_terrain:
                self._los_reference_point = None
            self._start_constraint = Circle(self._target.position, self.object_constraint_radius, routing_surface=self._routing_surface, los_reference_point=self._los_reference_point)
            self._start_constraint = self._start_constraint.intersect(self.get_water_constraint())

    def get_start_constraint(self):
        return self._start_constraint

    def get_waypoint_constraints_gen(self, routing_agent, waypoint_count):
        polygon = self._start_constraint.geometry.polygon
        object_waypoint_constraints = []
        object_waypoint = Circle(self._target.position, self.waypoint_constraint_radius, routing_surface=self._target.routing_surface, los_reference_point=self._los_reference_point)
        object_waypoint_constraints.append(object_waypoint)
        for position in random_uniform_points_in_compound_polygon(polygon, num=waypoint_count):
            object_waypoint_constraints.append(Circle(position, self.waypoint_constraint_radius, routing_surface=self._start_constraint.routing_surface, los_reference_point=self._los_reference_point))
            object_waypoint_constraints.append(object_waypoint)
        object_waypoint_constraints = self.apply_water_constraint(object_waypoint_constraints)
        yield from object_waypoint_constraints
