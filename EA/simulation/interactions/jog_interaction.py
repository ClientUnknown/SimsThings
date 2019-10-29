from _math import Vector3import itertoolsimport randomfrom balloon.tunable_balloon import TunableBalloonfrom element_utils import do_allfrom event_testing.results import TestResultfrom interactions import TargetTypefrom interactions.base.super_interaction import SuperInteractionfrom interactions.constraints import Circle, ANYWHEREfrom interactions.utils.routing import FollowPath, PlanRoute, get_route_element_for_pathfrom routing.walkstyle.walkstyle_request import WalkStyleRequestfrom routing.waypoints.waypoint_generator_variant import TunableWaypointGeneratorVariantfrom routing.waypoints.waypoint_stitching import WaypointStitchingVariantfrom sims4 import randomfrom sims4.tuning.tunable import TunableRange, Tunable, OptionalTunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodimport element_utilsimport routingimport sims4.loglogger = sims4.log.Logger('WaypointInteraction')
class _WaypointGeneratorRallyable:

    def __init__(self, waypoint_info):
        self._original_generator = waypoint_info

    def get_start_constraint(self):
        return self._original_generator.get_start_constraint()

    def get_waypoint_constraints_gen(self, routing_agent, waypoint_count):
        yield from self._original_generator.get_waypoint_constraints_gen(routing_agent, waypoint_count)

class WaypointInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'waypoint_constraint': TunableWaypointGeneratorVariant(tuning_group=GroupNames.ROUTING), 'waypoint_count': TunableRange(description='\n            The number of waypoints to select, from spawn points in the zone, to\n            visit for a Jog prior to returning to the original location.\n            ', tunable_type=int, default=2, minimum=2, tuning_group=GroupNames.ROUTING), 'waypoint_walk_style': WalkStyleRequest.TunableFactory(description='\n            The walkstyle to use when routing between waypoints.\n            ', tuning_group=GroupNames.ROUTING), 'waypoint_stitching': WaypointStitchingVariant(tuning_group=GroupNames.ROUTING), 'waypoint_randomize_orientation': Tunable(description='\n            Make Waypoint orientation random.  Default is velocity aligned.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.ROUTING), 'waypoint_clear_locomotion_mask': Tunable(description='\n            If enabled, override the locomotion queue mask.  This mask controls\n            which Animation Requests and XEvents get blocked during locomotion.\n            By default, the mask blocks everything.  If cleared, it blocks\n            nothing.  It also lowers the animation track used by locomotion to \n            9,999 from the default of 10,000.  Use with care, ask your GPE.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.ROUTING), 'waypoint_override_agent_radius': OptionalTunable(description='\n            If enabled, use the specified value as the agent radius when\n            generating goals for the waypoints. The agent radius is restored\n            for the actual route.\n            ', tunable=TunableRange(description='\n                The value to use as the agent radius when generating goals. \n                ', tunable_type=float, minimum=0, maximum=1.0, default=0.123), tuning_group=GroupNames.ROUTING), 'waypoint_route_fail_balloon': OptionalTunable(description='\n            Tuning for balloon to show when failing to plan a aroute for this waypoint interaction. \n            ', tunable=TunableBalloon(locked_args={'balloon_delay': 0, 'balloon_delay_random_offset': 0, 'balloon_chance': 100}), tuning_group=GroupNames.ROUTING)}

    def __init__(self, aop, *args, **kwargs):
        super().__init__(aop, *args, **kwargs)
        waypoint_info = kwargs.get('waypoint_info')
        if waypoint_info is not None:
            self._waypoint_generator = _WaypointGeneratorRallyable(waypoint_info)
        else:
            if aop.target is None and self.target_type is TargetType.ACTOR:
                target = self.sim
            else:
                target = aop.target
            self._waypoint_generator = self.waypoint_constraint(self.context, target)
        self._routing_infos = None
        self._goal_size = 0.0
        self.register_on_finishing_callback(self._clean_up_waypoint_generator)

    @classmethod
    def _test(cls, target, context, **interaction_parameters):
        sim = context.sim
        routing_master = sim.routing_master
        if routing_master is not None and sim.parent is not routing_master:
            return TestResult(False, '{} cannot run Waypoint interactions because they are following {}', sim, routing_master)
        return super()._test(target, context, **interaction_parameters)

    def _get_starting_constraint(self, *args, **kwargs):
        constraint = ANYWHERE
        target = self.target
        if self._waypoint_generator.is_for_vehicle and (target is not None and target.vehicle_component is not None) and not target.is_in_inventory():
            constraint = Circle(target.position, target.vehicle_component.minimum_route_distance, routing_surface=target.routing_surface)
        else:
            constraint = self._waypoint_generator.get_start_constraint()
        posture_constraint = self._waypoint_generator.get_posture_constraint()
        if posture_constraint is not None:
            constraint = constraint.intersect(posture_constraint)
        return constraint

    @flexmethod
    def _constraint_gen(cls, inst, *args, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        if inst is not None:
            constraint = inst._get_starting_constraint(*args, **kwargs)
            yield constraint
        yield from super(__class__, inst_or_cls)._constraint_gen(*args, **kwargs)

    def cancel(self, *args, **kwargs):
        for sim_primitive in list(self.sim.primitives):
            if isinstance(sim_primitive, FollowPath):
                sim_primitive.detach()
        return super().cancel(*args, **kwargs)

    def _clean_up_waypoint_generator(self, _):
        self._waypoint_generator.clean_up()

    def _get_goals_for_constraint(self, constraint, routing_agent):
        goals = []
        handles = constraint.get_connectivity_handles(routing_agent)
        for handle in handles:
            goals.extend(handle.get_goals(always_reject_invalid_goals=True))
        return goals

    def _show_route_fail_balloon(self):
        balloon_tuning = self.waypoint_route_fail_balloon
        if balloon_tuning is None:
            return
        if not self.is_user_directed:
            return
        balloon_requests = balloon_tuning(self)
        if balloon_requests:
            chosen_balloon = random.random.choice(balloon_requests)
            if chosen_balloon is not None:
                chosen_balloon.distribute()

    def _run_interaction_gen(self, timeline):
        all_sims = self.required_sims()
        if not all_sims:
            return
        self._routing_infos = []
        routing_agent = self.sim
        for sim in all_sims:
            routing_context = sim.routing_context
            routing_agent = sim
            vehicle = None if not sim.posture.is_vehicle else sim.parent
            if vehicle.vehicle_component is not None:
                routing_agent = vehicle
                routing_context = vehicle.routing_component.pathplan_context
            self._routing_infos.append((routing_agent, routing_context))
        waypoints = []
        default_agent_radius = None
        if routing_agent.routing_component is not None:
            default_agent_radius = routing_agent.routing_component._pathplan_context.agent_radius
            routing_agent.routing_component._pathplan_context.agent_radius = self.waypoint_override_agent_radius
        try:
            for constraint in self._waypoint_generator.get_waypoint_constraints_gen(routing_agent, self.waypoint_count):
                goals = self._get_goals_for_constraint(constraint, routing_agent)
                if not goals:
                    pass
                else:
                    if self.waypoint_randomize_orientation:
                        for goal in goals:
                            goal.orientation = sims4.math.angle_to_yaw_quaternion(random.uniform(0.0, sims4.math.TWO_PI))
                    waypoints.append(goals)
        finally:
            if default_agent_radius is not None:
                routing_agent.routing_component._pathplan_context.agent_radius = default_agent_radius
        if not (self.waypoint_override_agent_radius is not None and waypoints):
            return False
        self._goal_size = max(info[0].routing_component.get_routing_context().agent_goal_radius for info in self._routing_infos)
        self._goal_size *= self._goal_size
        if self.staging:
            for route_waypoints in itertools.cycle(self.waypoint_stitching(waypoints, self._waypoint_generator.loops)):
                result = yield from self._do_route_to_constraint_gen(route_waypoints, timeline)
                if not result:
                    return result
        else:
            for route_waypoints in self.waypoint_stitching(waypoints, self._waypoint_generator.loops):
                result = yield from self._do_route_to_constraint_gen(route_waypoints, timeline)
            return result
        return True

    def _do_route_to_constraint_gen(self, waypoints, timeline):
        if self.is_finishing:
            return False
        plan_primitives = []
        for (i, routing_info) in enumerate(self._routing_infos):
            routing_agent = routing_info[0]
            routing_context = routing_info[1]
            route = routing.Route(routing_agent.routing_location, waypoints[-1], waypoints=waypoints[:-1], routing_context=routing_context)
            plan_primitive = PlanRoute(route, routing_agent, interaction=self)
            result = yield from element_utils.run_child(timeline, plan_primitive)
            if not result:
                self._show_route_fail_balloon()
                return False
            if not (plan_primitive.path.nodes and plan_primitive.path.nodes.plan_success):
                self._show_route_fail_balloon()
                return False
            plan_primitive.path.blended_orientation = self.waypoint_randomize_orientation
            plan_primitives.append(plan_primitive)
            if i == len(self._routing_infos) - 1:
                pass
            else:
                for node in plan_primitive.path.nodes:
                    position = Vector3(*node.position)
                    for goal in itertools.chain.from_iterable(waypoints):
                        if goal.routing_surface_id != node.routing_surface_id:
                            pass
                        else:
                            dist_sq = (Vector3(*goal.position) - position).magnitude_2d_squared()
                            if dist_sq < self._goal_size:
                                goal.cost = routing.get_default_obstacle_cost()
        route_primitives = []
        track_override = None
        mask_override = None
        if self.waypoint_clear_locomotion_mask:
            mask_override = 0
            track_override = 9999
        for plan_primitive in plan_primitives:
            sequence = get_route_element_for_path(plan_primitive.sim, plan_primitive.path, interaction=self, force_follow_path=True, track_override=track_override, mask_override=mask_override)
            walkstyle_request = self.waypoint_walk_style(plan_primitive.sim)
            sequence = walkstyle_request(sequence=sequence)
            route_primitives.append(sequence)
        result = yield from element_utils.run_child(timeline, do_all(*route_primitives))
        return result

    @classmethod
    def get_rallyable_aops_gen(cls, target, context, **kwargs):
        key = 'waypoint_info'
        if key not in kwargs:
            waypoint_generator = cls.waypoint_constraint(context, target)
            kwargs[key] = waypoint_generator
        yield from super().get_rallyable_aops_gen(target, context, rally_constraint=waypoint_generator.get_start_constraint(), **kwargs)
