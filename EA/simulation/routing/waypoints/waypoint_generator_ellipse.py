import mathfrom interactions.constraints import SmallAreaConstraintfrom routing.waypoints.waypoint_generator import _WaypointGeneratorBasefrom sims4.tuning.geometric import TunableVector3from sims4.tuning.tunable import TunableAngle, TunableIntervalimport servicesimport sims4.math
class _WaypointGeneratorEllipse(_WaypointGeneratorBase):
    FACTORY_TUNABLES = {'x_radius_interval': TunableInterval(description='\n            The min and max radius of the x axis. Make the interval 0 to\n            get rid of variance.\n            ', tunable_type=float, default_lower=1.0, default_upper=1.0, minimum=1.0), 'z_radius_interval': TunableInterval(description='\n            The min and max radius of the z axis. Make the interval 0 to\n            get rid of variance.\n            ', tunable_type=float, default_lower=1.0, default_upper=1.0, minimum=1.0), 'offset': TunableVector3(description="\n            The offset of the ellipse relative to the target's position.\n            ", default=TunableVector3.DEFAULT_ZERO), 'orientation': TunableAngle(description="\n            The orientation of the ellipse relative to the target's\n            orientation. The major axis is X if the angle is 0. If the angle is\n            90 degrees, then the major axis is Z.\n            ", default=0)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ellipse_transform = sims4.math.Transform(self.offset, sims4.math.angle_to_yaw_quaternion(self.orientation))
        self.ellipse_transform = sims4.math.Transform.concatenate(ellipse_transform, self._target.transform)
        self.start_angle = self.get_start_angle()
        self._start_constraint = None
        self._waypoint_constraints = []

    def transform_point(self, point):
        return self.ellipse_transform.transform_point(point)

    def get_start_angle(self):
        sim_vec = self._context.sim.intended_position - self.ellipse_transform.translation
        return sims4.math.vector3_angle(sims4.math.vector_normalize_2d(sim_vec))

    def get_random_ellipse_point_at_angle(self, theta):
        a = self.x_radius_interval.random_float()
        b = self.z_radius_interval.random_float()
        x = a*math.sin(theta)
        z = b*math.cos(theta)
        y = services.terrain_service.terrain_object().get_height_at(x, z)
        return self.transform_point(sims4.math.Vector3(x, y, z))

    def get_ellipse_point_constraint(self, theta):
        position = self.get_random_ellipse_point_at_angle(theta)
        geometry = sims4.geometry.RestrictedPolygon(sims4.geometry.CompoundPolygon(sims4.geometry.Polygon((position,))), ())
        return SmallAreaConstraint(geometry=geometry, debug_name='EllipsePoint', routing_surface=self._routing_surface)

    def get_start_constraint(self):
        if self._start_constraint is None:
            self._start_constraint = self.get_ellipse_point_constraint(self.start_angle)
            self._start_constraint = self._start_constraint.intersect(self.get_water_constraint())
        return self._start_constraint

    def get_waypoint_constraints_gen(self, routing_agent, waypoint_count):
        if not self._waypoint_constraints:
            delta_theta = sims4.math.TWO_PI/waypoint_count
            theta = self.start_angle
            for _ in range(waypoint_count):
                waypoint_constraint = self.get_ellipse_point_constraint(theta)
                self._waypoint_constraints.append(waypoint_constraint)
                theta += delta_theta
            self._waypoint_constraints = self.apply_water_constraint(self._waypoint_constraints)
        yield from self._waypoint_constraints
