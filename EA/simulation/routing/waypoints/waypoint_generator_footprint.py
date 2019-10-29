import mathfrom interactions.constraints import SmallAreaConstraint, Constraint, Anywherefrom postures import posture_graphfrom routing.waypoints.waypoint_generator import _WaypointGeneratorBasefrom sims4.tuning.tunable import TunableRange, Tunableimport sims4.math
class _WaypointGeneratorFootprint(_WaypointGeneratorBase):
    FACTORY_TUNABLES = {'corner_radius': TunableRange(description='\n            The min and max radius of the corner. This determines how tight the\n            corners are.\n            ', tunable_type=float, default=1.0, minimum=0), 'offset_size': Tunable(description='\n            The offset of the footprint. positive means we enlarge the\n            footprint, negative means we shrink it.\n            ', tunable_type=float, default=0.0)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._waypoint_constraints = []

    def get_constraint_for_waypoint(self, x, z):
        position = self._target.transform.transform_point(sims4.math.Vector3(x, 0, z))
        geometry = sims4.geometry.RestrictedPolygon(sims4.geometry.CompoundPolygon(sims4.geometry.Polygon((position,))), ())
        return SmallAreaConstraint(geometry=geometry, debug_name='RoundedRectanglePoint', routing_surface=self._routing_surface)

    def get_rounded_corner_constraint(self, corner, theta):
        r = self.corner_radius
        x = r*math.sin(theta) + corner.x
        z = r*math.cos(theta) + corner.z
        return self.get_constraint_for_waypoint(x, z)

    def get_start_constraint(self):
        constraint = self.get_water_constraint()
        sim = self._context.sim
        supported_postures = self._target.provided_mobile_posture_types
        if self._target.footprint_polygon.contains(sim.position) and sim.posture.posture_type in supported_postures and sim.level == self._target.level:
            return constraint
        transform = self._target.transform
        corners = [transform.transform_point(sims4.math.Vector3(corner.x, 0, corner.z)) for corner in self.get_corners()]
        corners.reverse()
        geometry = sims4.geometry.RestrictedPolygon(sims4.geometry.CompoundPolygon(sims4.geometry.Polygon(corners)), ())
        return constraint.intersect(Constraint(geometry=geometry, debug_name='FootprintConstraint', routing_surface=self._routing_surface))

    def get_corners(self, radius=0):
        (corner_2, corner_0) = self._target.get_fooptrint_polygon_bounds()
        if corner_2 is None or corner_0 is None:
            return ()
        corner_1 = sims4.math.Vector3(corner_0.x, 0, corner_2.z)
        corner_3 = sims4.math.Vector3(corner_2.x, 0, corner_0.z)
        offset = self.offset_size - radius
        corner_0 += sims4.math.Vector3(offset, 0, offset)
        corner_1 += sims4.math.Vector3(offset, 0, -offset)
        corner_2 += sims4.math.Vector3(-offset, 0, -offset)
        corner_3 += sims4.math.Vector3(-offset, 0, offset)
        return (corner_0, corner_1, corner_2, corner_3)

    def get_waypoint_constraints_gen(self, routing_agent, waypoint_count):
        if not self._waypoint_constraints:
            quad_waypoint_count = waypoint_count + waypoint_count % 4
            corner_waypoint_count = int(quad_waypoint_count/4)
            corner_region_count = corner_waypoint_count - 1
            if not corner_region_count:
                self._waypoint_constraints = [self.get_constraint_for_waypoint(corner.x, corner.z) for corner in self.get_corners()]
            else:
                corners = self.get_corners(radius=self.corner_radius)
                delta_theta = sims4.math.TWO_PI/(4*corner_region_count)
                theta = delta_theta
                for corner in corners:
                    theta -= delta_theta
                    for _ in range(corner_waypoint_count):
                        waypoint_constraint = self.get_rounded_corner_constraint(corner, theta)
                        self._waypoint_constraints.append(waypoint_constraint)
                        theta += delta_theta
            corner_num = 0
            min_dist = sims4.math.MAX_FLOAT
            intended_position = self._context.sim.intended_position
            i_constraint = 0
            for waypoint_constraint in self._waypoint_constraints:
                dist = (waypoint_constraint.geometry.polygon.centroid() - intended_position).magnitude_squared()
                if dist < min_dist:
                    corner_num = i_constraint
                    min_dist = dist
                i_constraint += 1
            corner_num = len(self._waypoint_constraints) - corner_num - 1
            self._waypoint_constraints = self._waypoint_constraints[-corner_num:] + self._waypoint_constraints[:-corner_num]
            self._waypoint_constraints = self.apply_water_constraint(self._waypoint_constraints)
        yield from self._waypoint_constraints
