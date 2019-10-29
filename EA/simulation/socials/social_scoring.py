import mathimport randomimport weakreffrom build_buy import is_location_outsidefrom interactions.constraints import CostFunctionBasefrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableRange, TunableTuple, Tunable, OptionalTunableimport sims4.mathimport socials.geometryimport terrain
class SocialGroupCostFunction(CostFunctionBase):

    def __init__(self, group, sim):
        self._group_ref = weakref.ref(group)
        self._sim = sim

    def constraint_cost(self, position, orientation, routing_surface):
        group = self._group_ref()
        if group is None:
            return 0.0
        geometry = group.geometry
        if geometry and len(geometry) == 1 and self._sim in geometry:
            ideal_position = group.position
            effective_distance = (position - ideal_position).magnitude_2d()*2.0
            score = socials.geometry.SocialGeometry.GROUP_DISTANCE_CURVE.get(effective_distance)
            return -score
        (base_focus, base_field) = socials.geometry._get_social_geometry_for_sim(self._sim)
        transform = sims4.math.Transform(position, orientation)
        multiplier = socials.geometry.score_transform(transform, self._sim, geometry, group.group_radius, base_focus, base_field)
        offset = multiplier*socials.geometry.SocialGeometry.SCORE_STRENGTH_MULTIPLIER
        if sims4.math.vector3_almost_equal_2d(position, self._sim.position, epsilon=0.01):
            offset += socials.geometry.SocialGeometry.SCORE_OFFSET_FOR_CURRENT_POSITION
        return -offset

class PetGroupCostFunction(HasTunableFactory, AutoFactoryInit, CostFunctionBase):
    FACTORY_TUNABLES = {'maximum_distance': TunableRange(description='\n            Any distance to another Sim over this amount scores zero.\n            ', tunable_type=float, default=1.0, minimum=0), 'minimum_distance': TunableRange(description='\n            Any distance to another Sim under this amount scores zero.\n            ', tunable_type=float, default=1.5, minimum=0), 'required_distance': TunableRange(description='\n            Any position that requires the Sim to move less than this amount\n            scores zero. This encourages Sims to move.\n            ', tunable_type=float, default=0.75, minimum=0)}
    SIDE_ARC_START = math.cos(sims4.math.PI/4)
    SIDE_ARC_END = math.cos(sims4.math.PI*3/4)

    def __init__(self, sim, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim = sim
        self._target_ref = target.ref()

    def constraint_cost(self, position, orientation, routing_surface):
        target = self._target_ref()
        if target is None:
            return 0.0
        distance_to_position = (position - self._sim.position).magnitude()
        if distance_to_position < self.required_distance:
            return 0.0
        vector_to_pos = position - target.position
        distance_to_sim = vector_to_pos.magnitude()
        if distance_to_sim <= self.minimum_distance or distance_to_sim > self.maximum_distance:
            return 0.0
        else:
            unit_vector_to_sim = vector_to_pos/distance_to_sim
            fwd = target.transform.orientation.transform_vector(sims4.math.Vector3.Z_AXIS())
            angle = sims4.math.vector_dot(fwd, unit_vector_to_sim)
            if angle <= PetGroupCostFunction.SIDE_ARC_START and angle >= PetGroupCostFunction.SIDE_ARC_END:
                return -3.0
        return 0.0

class ThrowingGroupCostFunction(HasTunableFactory, AutoFactoryInit, CostFunctionBase):
    FACTORY_TUNABLES = {'maximum_distance': TunableRange(description='\n            Any distance to another Sim over this amount will be penalized.\n            ', tunable_type=float, default=10.0, minimum=0), 'minimum_distance': TunableRange(description='\n            Any distance to another Sim under this amount will be penalized.\n            ', tunable_type=float, default=3.0, minimum=0), 'adjustment_distance': TunableRange(description='\n            Any position that requires the Sim to be at a distance less than\n            this value will be penalized.\n            ', tunable_type=float, default=5.0, minimum=0), 'location_tests': TunableTuple(description='\n            Tests to run on the goal location to validate if it should be\n            discouraged when using this social group.\n            ', validate_snowmask=OptionalTunable(description='\n                If enabled goals that do not match the snowmask value will\n                be discouraged.  This is used for winter to guarantee cases\n                like snowball fight the Sims readjust and move around in places\n                where there is snow.\n                ', tunable=Tunable(description='\n                    Value snowmask should be greater than to pass this test.\n                    ', tunable_type=float, default=0.5)), validate_is_outside=OptionalTunable(description='\n                If enabled goals that do not match the outside condition will\n                be discouraged.\n                ', tunable=Tunable(description='\n                    If True goals outside will be encouraged, if false only\n                    goals on the inside will be encouraged.\n                    ', tunable_type=bool, default=False)))}
    INVALID_GOAL_SCORE = 20

    def __init__(self, sim, target, force_readjust, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim = sim
        self._target_ref = target.ref()
        self._force_readjust = force_readjust

    def _score_location(self, position):
        if self.location_tests.validate_snowmask is not None and terrain.get_snowmask_value(position) > self.location_tests.validate_snowmask:
            return ThrowingGroupCostFunction.INVALID_GOAL_SCORE
        elif self.location_tests.validate_is_outside is not None and self.location_tests.validate_is_outside != is_location_outside(self._sim.zone_id, position, self._sim.level):
            return ThrowingGroupCostFunction.INVALID_GOAL_SCORE
        return 0.0

    def constraint_cost(self, position, orientation, routing_surface):
        target = self._target_ref()
        if target is None:
            return 0.0
        constraint_cost = 0.0
        if self._sim.get_main_group() is None or self._sim.get_main_group().anchor is None:
            return constraint_cost
        vector_to_pos = position - target.intended_position
        distance_to_sim = vector_to_pos.magnitude()
        if distance_to_sim <= self.minimum_distance:
            return ThrowingGroupCostFunction.INVALID_GOAL_SCORE
        constraint_cost += self._score_location(position)
        vector_to_anchor = position - self._sim.get_main_group().anchor.position
        distance_to_anchor = vector_to_anchor.magnitude_squared()
        constraint_cost = -distance_to_anchor
        distance_to_position = (position - self._sim.intended_position).magnitude()
        if distance_to_position < self.adjustment_distance:
            constraint_cost += ThrowingGroupCostFunction.INVALID_GOAL_SCORE
        return constraint_cost
