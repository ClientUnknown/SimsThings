from sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, OptionalTunable, TunableRange, Tunableimport sims4.reloadfrom interactions.constraints import ANYWHERE, Constraintfrom postures.base_postures import MobilePosturefrom postures.posture_graph import get_mobile_posture_constraintfrom world.ocean_tuning import OceanTuningimport routingDEBUGVIS_WAYPOINT_LAYER_NAME = 'waypoints'with sims4.reload.protected(globals()):
    enable_waypoint_visualization = False
class WaypointContext:

    def __init__(self, obj):
        self._obj = obj

    @property
    def pick(self):
        pass

    @property
    def sim(self):
        return self._obj

class _WaypointGeneratorBase(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'mobile_posture_override': OptionalTunable(description='\n            If enabled, the mobile posture specified would require the sim to\n            be in this posture to begin the route. This allows us to make the\n            Sim Swim or Ice Skate instead of walk/run.\n            ', tunable=MobilePosture.TunableReference(description='\n                The mobile posture we want to use.\n                ')), '_loops': TunableRange(description='\n            The number of loops we want to perform per route.\n            ', tunable_type=int, default=1, minimum=1), 'use_provided_routing_surface': Tunable(description="\n            If enabled, we will use the target's provided routing surface if it\n            has one.\n            ", tunable_type=bool, default=False)}

    def __init__(self, context, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._context = context
        self._target = target if target is not None else context.sim
        provided_routing_surface = self._target.provided_routing_surface
        if provided_routing_surface is not None and self.use_provided_routing_surface:
            self._routing_surface = provided_routing_surface
        else:
            self._routing_surface = self._target.routing_location.routing_surface
        self._water_constraint = dict()

    @property
    def loops(self):
        return self._loops

    def get_water_constraint(self, min_water_depth=None, max_water_depth=None):
        water_constraint_key = (min_water_depth, max_water_depth)
        if water_constraint_key in self._water_constraint:
            return self._water_constraint[water_constraint_key]
        if self._context.sim is not None:
            (min_water_depth, max_water_depth) = OceanTuning.make_depth_bounds_safe_for_surface_and_sim(self._routing_surface, self._context.sim, min_water_depth, max_water_depth)
        if self._target is not self._context.sim:
            (min_water_depth, max_water_depth) = OceanTuning.make_depth_bounds_safe_for_surface_and_sim(self._routing_surface, self._target, min_water_depth, max_water_depth)
        if self._target is not None and min_water_depth is None and max_water_depth is None:
            constraint = ANYWHERE
        else:
            constraint = Constraint(min_water_depth=min_water_depth, max_water_depth=max_water_depth)
        self._water_constraint[water_constraint_key] = constraint
        return constraint

    def apply_water_constraint(self, constraint_list):
        if not constraint_list:
            return constraint_list
        water_constraint = self.get_water_constraint()
        if water_constraint is not ANYWHERE:
            orig_list = constraint_list
            constraint_list = []
            for orig_constraint in orig_list:
                constraint_list.append(orig_constraint.intersect(water_constraint))
        return constraint_list

    def get_start_constraint(self):
        raise NotImplementedError

    def clean_up(self):
        pass

    def get_waypoint_constraints_gen(self, routing_agent, waypoint_count):
        raise NotImplementedError

    def get_posture_constraint(self):
        return get_mobile_posture_constraint(posture=self.mobile_posture_override, target=self._target)

    @property
    def is_for_vehicle(self):
        return self.mobile_posture_override is not None and self.mobile_posture_override.is_vehicle
