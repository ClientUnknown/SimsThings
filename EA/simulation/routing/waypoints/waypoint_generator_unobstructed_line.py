from protocolbuffers.Math_pb2 import Quaternionfrom interactions.constraints import Anywhere, SmallAreaConstraintfrom routing import FootprintTypefrom routing.waypoints.waypoint_generator import _WaypointGeneratorBasefrom sims4.geometry import build_rectangle_from_two_points_and_radius, PolygonFootprintfrom sims4.tuning.tunable import TunableRange, TunableTuple, OptionalTunable, Tunable, TunableAngleimport placementimport routingimport sims4.geometrylogger = sims4.log.Logger('_WaypointGeneratorUnobstructedLine', default_owner='rrodgers')
class _WaypointGeneratorUnobstructedLine(_WaypointGeneratorBase):
    FACTORY_TUNABLES = {'line_length': TunableRange(description='\n            The radius, in meters, of the generated constraint around the \n            target object where the waypoints will be generated.\n            ', tunable_type=float, default=3, minimum=0), 'fgl_parameters': TunableTuple(description='\n            Arguments that will affect the FGL.\n            ', min_water_depth=OptionalTunable(description='\n                (float) If provided, each vertex of the line polygon along with its centroid will\n                be tested to determine whether the ocean water at the test location is at least this deep.\n                0 indicates that all water placement is valid. To allow land placement, leave untuned.\n                ', tunable=TunableRange(description='\n                    Value of the min water depth allowed.\n                    ', minimum=0, tunable_type=float, default=0)), max_water_depth=OptionalTunable(description='\n                (float) If provided, each vertex of the line polygon along with its centroid will\n                be tested to determine whether the ocean water at the test location is at most this deep.\n                To disallow water placement, set to 0.\n                ', tunable=TunableRange(description='\n                    Value of the max water depth allowed.\n                    ', tunable_type=float, minimum=0, maximum=1000.0, default=1000.0)))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._footprint = None

    def get_start_constraint(self):
        return self.get_water_constraint(self.fgl_parameters.min_water_depth, self.fgl_parameters.max_water_depth)

    def clean_up(self):
        if self._footprint is None:
            return
        self._target.routing_context.remove_footprint_contour_override(self._footprint.footprint_id)
        self._footprint = None

    def get_waypoint_constraints_gen(self, routing_agent, waypoint_count):
        line_length_offset = sims4.math.Vector3(0, 0, self.line_length)
        object_radius = routing_agent.routing_component.object_radius
        start = routing_agent.position
        initial_orientation = sims4.random.random_orientation()
        end = initial_orientation.transform_vector(line_length_offset) + start
        polygon = build_rectangle_from_two_points_and_radius(start, end, object_radius)
        starting_location_for_sample = placement.create_starting_location(position=start, routing_surface=self._routing_surface)
        water_constraint = self.get_water_constraint(self.fgl_parameters.min_water_depth, self.fgl_parameters.max_water_depth)
        fgl_context = placement.FindGoodLocationContext(starting_location_for_sample, object_polygons=(polygon,), ignored_object_ids=[routing_agent.id, self._context.sim.sim_id], max_distance=0, min_water_depth=water_constraint.get_min_water_depth(), max_water_depth=water_constraint.get_max_water_depth())
        (_, orientation) = placement.find_good_location(fgl_context)
        if orientation is None:
            return
        final_orientation = sims4.math.Quaternion.concatenate(orientation, initial_orientation)
        oriented_line_offset = final_orientation.transform_vector(line_length_offset)
        waypoint_constraints = []
        for waypoint_index in range(0, waypoint_count):
            percent_down_line = waypoint_index/(waypoint_count - 1)
            goal_positon = oriented_line_offset*percent_down_line + start
            geometry = sims4.geometry.RestrictedPolygon(sims4.geometry.CompoundPolygon(sims4.geometry.Polygon((goal_positon,))), ())
            constraint = SmallAreaConstraint(geometry=geometry, routing_surface=self._routing_surface, min_water_depth=water_constraint.get_min_water_depth(), max_water_depth=water_constraint.get_max_water_depth())
            waypoint_constraints.append(constraint)
        end = oriented_line_offset + start
        polygon = build_rectangle_from_two_points_and_radius(start, end, object_radius)
        self._footprint = PolygonFootprint(polygon, routing_surface=self._routing_surface, cost=routing.get_default_discouragement_cost(), footprint_type=FootprintType.FOOTPRINT_TYPE_OBJECT, enabled=True)
        routing_agent.routing_component.pathplan_context.ignore_footprint_contour(self._footprint.footprint_id)
        yield from waypoint_constraints
