from _math import Vector3from animation import animation_constantsfrom element_utils import build_elementfrom interactions import ParticipantTypefrom interactions.base.super_interaction import SuperInteractionfrom interactions.constraints import TunableCircle, Nowhere, ANYWHERE, WaterDepthIntervalConstraint, WaterDepthIntervalsfrom interactions.social.social_super_interaction import SocialSuperInteractionfrom interactions.utils.routing import PlanRoute, FollowPathfrom objects.pools.pool_utils import POOL_LANDING_SURFACEfrom placement import FGLSearchFlagsDefault, FGLSearchFlagfrom routing import SurfaceType, SurfaceIdentifierfrom server.pick_info import PickTypefrom sims4.log import Loggerfrom sims4.math import TWO_PI, vector_dot_2d, vector_normalize_2dfrom sims4.tuning.tunable import TunableRange, Tunable, TunableInterval, TunableAngle, OptionalTunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom singletons import DEFAULTfrom socials.jigs.jig_type_explicit import SocialJigExplicitfrom socials.jigs.jig_utils import JigPositioningfrom terrain import get_water_depth, get_water_depth_at_locationfrom world.ocean_tuning import OceanTuningimport element_utilsimport interactionsimport routingimport servicesimport sims4.geometryimport sims4.mathlogger = Logger('DistancePlacementMixin')
class DistancePlacementMixin:
    INSTANCE_TUNABLES = {'facing_radius': TunableRange(description='\n            Facing constraint radius that will be used for the Sim looking \n            at the target position where the object will be placed.\n            ', tunable_type=int, default=1, minimum=1, tuning_group=GroupNames.CONSTRAINTS), 'facing_range': TunableAngle(description='\n            The max angle offset (in radians), the Sim can face away from the\n            object.\n            ', default=sims4.math.PI/8), 'placement_distance': TunableInterval(description='\n           Distance in meters where the object will be placed.\n           ', tunable_type=float, default_lower=0, default_upper=10, minimum=0, tuning_group=GroupNames.CONSTRAINTS), 'raytest_radius': TunableAngle(description='\n            Radius of the ray test check that will be used to validate if the\n            Sim can see the target position where the object will be placed.\n            ', default=0.1, minimum=0.1, tuning_group=GroupNames.CONSTRAINTS), 'raytest_offset': TunableInterval(description="\n           Offset in meters from the ground from where the raytest should start\n           and stop.\n           i.e. If you're testing if the Sim should see the target position \n           from its eye level, you may want a value around the 1.7 (for an \n           adult).\n           ", tunable_type=float, default_lower=1.5, default_upper=1.5, minimum=0, tuning_group=GroupNames.CONSTRAINTS), 'thrown_object_actor_name': Tunable(description='\n            Offset in meters from the ground from where the raytest should \n            end.\n            ', tunable_type=str, default='carryObject', tuning_group=GroupNames.ANIMATION), 'bounce_jig': SocialJigExplicit.TunableFactory(description="\n            The jig to use for the object's bounce, where actor b is the\n            object's final resting position, and actor a is where the initial\n            bounce occurs, relative to the final position.\n            \n            The actor offsets will setup the distance of the bounce. If the\n            offsets are both 0, then there will be no bounce. The offset for\n            actor a will determine where the first bounce occurs.\n            ", tuning_group=GroupNames.CONSTRAINTS), 'minimum_requirement_jig': OptionalTunable(description='\n            If enabled, we will use a jig to guarantee that we find a place to\n            throw the ball from. From there, we find the furthest throw.\n            ', tunable=SocialJigExplicit.TunableFactory(description="\n                The jig to use so we can find a good place to start our throw\n                from. Doesn't really matter which actor A and B are, as long as\n                there is enough distance between them for a throw. After we\n                place this jig, we FGL from that location to find the longest\n                throw possible.\n                "), tuning_group=GroupNames.CONSTRAINTS)}
    CONSTRAINT_RADIUS_BUFFER = 0.1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._starting_location = None
        self._distance_placement_transform = None
        self._bounce_transform = None
        self._routing_surface = None

    @flexmethod
    def _get_distance_placement_constraint(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        inst_or_cls = inst if inst is not None else cls
        if inst is None or participant_type != ParticipantType.Actor:
            return ANYWHERE
        constraint = ANYWHERE
        if inst._distance_placement_transform is None or inst._bounce_transform is None:
            return Nowhere("Distance Placement couldn't find a good location for the carry target.")
        if inst_or_cls._starting_location is not None:
            constraint = constraint.intersect(interactions.constraints.Position(inst_or_cls._starting_location.transform.translation, routing_surface=inst_or_cls._starting_location.routing_surface))
        else:
            constraint = constraint.intersect(interactions.constraints.Circle(inst_or_cls._distance_placement_transform.translation, inst_or_cls.placement_distance.upper_bound + DistancePlacementMixin.CONSTRAINT_RADIUS_BUFFER, inst_or_cls.sim.routing_surface, los_reference_point=DEFAULT))
        constraint = constraint.intersect(interactions.constraints.Facing(facing_range=inst_or_cls.facing_range, target_position=inst_or_cls._bounce_transform.translation))
        if constraint.valid:
            return constraint
        return Nowhere("Distance Placement couldn't find a good location for the carry target.")

    def _update_water_depth_requirements(self, sim_a, sim_b, interval, **kwargs):
        min_water_depth = kwargs['min_water_depth'] if 'min_water_depth' in kwargs else None
        max_water_depth = kwargs['max_water_depth'] if 'max_water_depth' in kwargs else None
        constraint_a = WaterDepthIntervalConstraint.create_water_depth_interval_constraint(sim_a, interval)
        constraint_b = WaterDepthIntervalConstraint.create_water_depth_interval_constraint(sim_b, interval)

        def safe_min(*args):
            ret = None
            for x in args:
                if ret is None:
                    ret = x
                elif x is not None:
                    ret = min(ret, x)
            return ret

        def safe_max(*args):
            ret = None
            for x in args:
                if ret is None:
                    ret = x
                elif x is not None:
                    ret = min(ret, x)
            return ret

        if interval == WaterDepthIntervals.SWIM:
            min_water_depth = safe_min(min_water_depth, constraint_a.get_min_water_depth(), constraint_b.get_min_water_depth())
            max_water_depth = safe_max(max_water_depth, constraint_a.get_max_water_depth(), constraint_b.get_max_water_depth())
        else:
            min_water_depth = safe_max(min_water_depth, constraint_a.get_min_water_depth(), constraint_b.get_min_water_depth())
            max_water_depth = safe_min(max_water_depth, constraint_a.get_max_water_depth(), constraint_b.get_max_water_depth())
        kwargs['min_water_depth'] = min_water_depth
        kwargs['max_water_depth'] = max_water_depth
        return kwargs

    def find_starting_location(self):
        if self.carry_target is not None and self.minimum_requirement_jig is not None:
            fgl_flags = FGLSearchFlag.STAY_IN_CONNECTED_CONNECTIVITY_GROUP | FGLSearchFlag.SHOULD_TEST_ROUTING | FGLSearchFlag.CALCULATE_RESULT_TERRAIN_HEIGHTS | FGLSearchFlag.DONE_ON_MAX_RESULTS
            check_on_lot = self.sim.is_on_active_lot()
            if check_on_lot:
                fgl_flags = fgl_flags | FGLSearchFlag.STAY_IN_LOT
            fgl_kwargs = {'ignored_object_ids': {sim.id for sim in self.required_sims()}, 'positioning_type': JigPositioning.RelativeToSimA}
            loc_a = self.sim.location.duplicate()
            fgl_kwargs.update({'search_flags': fgl_flags})
            loc_b = loc_a.duplicate()
            lot = services.current_zone().lot

            def find_a_starting_location():
                for (transform_a, transform_b, routing_surface, _) in self.minimum_requirement_jig.get_transforms_gen(self.sim, self.carry_target, actor_loc=loc_a, target_loc=loc_b, fgl_kwargs=fgl_kwargs):
                    if check_on_lot and lot.is_position_on_lot(transform_a.translation):
                        if not lot.is_position_on_lot(transform_b.translation):
                            pass
                        else:
                            return sims4.math.Location(transform_a, routing_surface)
                    else:
                        return
                return

            use_pool_surface = loc_a.routing_surface.type == SurfaceType.SURFACETYPE_POOL or 0 < get_water_depth_at_location(loc_a)
            if use_pool_surface:
                interval = WaterDepthIntervals.SWIM
                if loc_a.routing_surface.type != SurfaceType.SURFACETYPE_POOL:
                    self._routing_surface = SurfaceIdentifier(loc_a.routing_surface.primary_id, loc_a.routing_surface.secondary_id, SurfaceType.SURFACETYPE_POOL)
                    loc_a = loc_a.clone(routing_surface=self._routing_surface)
            else:
                interval = WaterDepthIntervals.WALK
            fgl_kwargs = self._update_water_depth_requirements(self.sim, self.target, interval, **fgl_kwargs)
            start_loc = find_a_starting_location()
            if start_loc is not None:
                return start_loc
        return self.sim.location.duplicate()

    def setup_final_transforms(self, start_location, **fgl_kwargs):
        loc_b = start_location.clone(routing_surface=DEFAULT if self._routing_surface is None else self._routing_surface)
        for (transform_a, transform_b, _, _) in self.bounce_jig.get_transforms_gen(self.sim, self.carry_target, actor_loc=start_location, target_loc=loc_b, fgl_kwargs=fgl_kwargs):
            self._distance_placement_transform = transform_a
            self._bounce_transform = transform_b
            break

    def _entered_pipeline(self):
        if self.carry_target is not None:
            fgl_flags = FGLSearchFlag.STAY_IN_CURRENT_BLOCK | FGLSearchFlag.STAY_IN_SAME_CONNECTIVITY_GROUP | FGLSearchFlag.SHOULD_TEST_ROUTING | FGLSearchFlag.CALCULATE_RESULT_TERRAIN_HEIGHTS | FGLSearchFlag.DONE_ON_MAX_RESULTS | FGLSearchFlag.SHOULD_RAYTEST
            fgl_kwargs = {'raytest_radius': self.raytest_radius, 'raytest_start_offset': self.raytest_offset.lower_bound, 'raytest_end_offset': self.raytest_offset.upper_bound, 'ignored_object_ids': {sim.id for sim in self.required_sims()}, 'positioning_type': JigPositioning.RelativeToSimA}
            pick = self.context.pick
            if pick is not None and pick.routing_surface.type == SurfaceType.SURFACETYPE_POOL:
                swim_constraint = WaterDepthIntervalConstraint.create_water_depth_interval_constraint(self.target, WaterDepthIntervals.SWIM)
                pick_location = sims4.math.Location(sims4.math.Transform(pick.location), pick.routing_surface)
                if swim_constraint.is_location_water_depth_valid(pick_location):
                    loc_a = pick_location
                    self._routing_surface = pick.routing_surface
                else:
                    self._routing_surface = SurfaceIdentifier(pick.routing_surface.primary_id, pick.routing_surface.secondary_id, SurfaceType.SURFACETYPE_WORLD)
                    loc_a = pick_location.clone(routing_surface=self._routing_surface)
                fgl_kwargs.update({'search_flags': fgl_flags, 'restrictions': (sims4.geometry.RelativeFacingRange(self.sim.position, 0),)})
                self.setup_final_transforms(loc_a, **fgl_kwargs)
            else:
                self._starting_location = self.find_starting_location()
                if self._starting_location is not None:
                    check_on_lot = self.sim.is_on_active_lot()
                    if check_on_lot:
                        fgl_flags = fgl_flags | FGLSearchFlag.STAY_IN_LOT
                    loc_a = self._starting_location
                    fgl_flags |= FGLSearchFlag.SPIRAL_INWARDS
                    fgl_kwargs.update({'max_distance': self.placement_distance.upper_bound, 'min_distance': self.placement_distance.lower_bound, 'restrictions': (sims4.geometry.RelativeFacingRange(loc_a.transform.translation, 0),), 'search_flags': fgl_flags})
                    self.setup_final_transforms(loc_a, **fgl_kwargs)
        return super()._entered_pipeline()

    def setup_asm_default(self, asm, *args, **kwargs):
        if self._distance_placement_transform is None:
            return False
        if self.carry_target is None:
            return False
        result = super().setup_asm_default(asm, *args, **kwargs)
        if not result:
            return result
        if not asm.set_actor_parameter(self.thrown_object_actor_name, self.carry_target, animation_constants.ASM_TARGET_TRANSLATION, self._distance_placement_transform.translation):
            return False
        if not asm.set_actor_parameter(self.thrown_object_actor_name, self.carry_target, animation_constants.ASM_TARGET_ORIENTATION, self._distance_placement_transform.orientation):
            return False
        throw_distance = (self._distance_placement_transform.translation - self.sim.position).magnitude_2d()
        bounce_distance = (self._distance_placement_transform.translation - self._bounce_transform.translation).magnitude_2d()
        asm.set_actor_parameter(self.thrown_object_actor_name, self.carry_target, 'ThrowDistance', throw_distance)
        asm.set_actor_parameter(self.thrown_object_actor_name, self.carry_target, 'BounceDistance', bounce_distance)
        if self._routing_surface is not None and self._routing_surface.type == routing.SurfaceType.SURFACETYPE_POOL:
            asm.set_actor_parameter(self.thrown_object_actor_name, self.carry_target, 'LandingSurface', POOL_LANDING_SURFACE)
        return True

    def _exited_pipeline(self, *args, **kwargs):
        if self._routing_surface is not None:
            self.carry_target.location = self.carry_target.location.clone(routing_surface=self._routing_surface)
        return super()._exited_pipeline(*args, **kwargs)

class DistancePlacementSuperInteraction(DistancePlacementMixin, SuperInteraction):

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        inst_or_cls = inst if inst is not None else cls
        yield from super(SuperInteraction, inst_or_cls)._constraint_gen(sim, target, participant_type=participant_type)
        placement_constraint = inst_or_cls._get_distance_placement_constraint(sim, target, participant_type=participant_type)
        yield placement_constraint

class FetchObjectSocialSuperInteraction(DistancePlacementMixin, SocialSuperInteraction):
    MAX_FETCH_RADIUS = 3
    INSTANCE_TUNABLES = {'fetch_constraint': TunableCircle(description='\n            The circle constraint for other Sims in the social group to route\n            near the placement location.\n            ', radius=MAX_FETCH_RADIUS, tuning_group=GroupNames.CONSTRAINTS), 'throw_xevent_id': Tunable(description='\n            An xevent id for when the carry target is thrown from an animation.\n            ', tunable_type=int, default=0, tuning_group=GroupNames.ANIMATION)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._plan_primitives = []
        self._follow_path_elements = []

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        inst_or_cls = inst if inst is not None else cls
        yield from super(SuperInteraction, inst_or_cls)._constraint_gen(sim, target, participant_type=participant_type)
        if inst is not None and participant_type == ParticipantType.TargetSim:
            starting_location = inst._starting_location if inst._starting_location is not None else sim.location
            constraint = interactions.constraints.Circle(starting_location.transform.translation, inst.social_group.max_radius, starting_location.routing_surface)
            constraint = constraint.intersect(interactions.constraints.Facing(target_position=starting_location.transform.translation))
            yield constraint
        placement_constraint = inst_or_cls._get_distance_placement_constraint(sim, target, participant_type=participant_type)
        yield placement_constraint

    def distribute_fetch_route(self, *args, **kwargs):
        for plan_primitive in self._plan_primitives:
            if FollowPath.should_follow_path(plan_primitive.sim, plan_primitive.path):
                follow_path_element = FollowPath(plan_primitive.sim, plan_primitive.path)
                self._follow_path_elements.append(follow_path_element)
                follow_path_element.distribute_path_asynchronously()

    def build_basic_content(self, *args, **kwargs):
        self.store_event_handler(self.distribute_fetch_route, handler_id=self.throw_xevent_id)
        sequence = super().build_basic_content(*args, **kwargs)

        def plan_fetch_paths(timeline):
            for target_sim in self.get_participants(ParticipantType.TargetSim | ParticipantType.Listeners):
                fetch_constraint = self.fetch_constraint.create_constraint(target_sim, target_position=self._distance_placement_transform.translation, routing_surface=self._routing_surface if self._routing_surface is not None else DEFAULT)
                facing = interactions.constraints.Facing(target_position=self._distance_placement_transform.translation, inner_radius=self.facing_radius)
                fetch_constraint = fetch_constraint.intersect(facing)
                if not fetch_constraint.valid:
                    pass
                else:
                    goals = []
                    handles = fetch_constraint.get_connectivity_handles(target_sim)
                    for handle in handles:
                        goals.extend(handle.get_goals())
                    if not goals:
                        pass
                    else:
                        route = routing.Route(target_sim.routing_location, goals, routing_context=target_sim.routing_context)
                        plan_primitive = PlanRoute(route, target_sim, interaction=self)
                        result = yield from element_utils.run_child(timeline, plan_primitive)
                        if result and plan_primitive.path.nodes and plan_primitive.path.nodes.plan_success:
                            if plan_primitive.path.portal_obj is not None:
                                logger.error('Need sub interaction to route {} due to portal on path'.format(target_sim))
                            else:
                                self._plan_primitives.append(plan_primitive)
            yield from element_utils.run_child(timeline, sequence)

        return build_element(plan_fetch_paths)
