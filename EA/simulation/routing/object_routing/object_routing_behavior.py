from sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, OptionalTunable, TunableList, TunableVariant, TunableSet, Tunablefrom animation.animation_utils import flush_all_animationsfrom animation.object_animation import ObjectAnimationElementfrom element_utils import build_elementfrom elements import SubclassableGeneratorElementfrom event_testing.resolver import SingleObjectResolverfrom interactions.utils.loot import LootActionsfrom interactions.utils.routing import PlanRoute, FollowPathfrom routing.object_routing.object_route_variants import ObjectRoutingBehaviorFromWaypointGenerator, ObjectRoutingBehaviorFromRoutingSlotConstraint, ObjectRouteFromRoutingFormation, ObjectRouteFromFGLfrom routing.object_routing.object_routing_behavior_actions import ObjectRoutingBehaviorActionDestroyObjects, ObjectRoutingBehaviorActionAnimationfrom routing.walkstyle.walkstyle_request import WalkStyleRequestimport element_utilsimport services
class ObjectRoutingBehavior(HasTunableReference, SubclassableGeneratorElement, metaclass=HashedTunedInstanceMetaclass, manager=services.snippet_manager()):
    INSTANCE_TUNABLES = {'route': TunableVariant(description='\n            Define how this object routes when this behavior is active.\n            ', from_waypoints=ObjectRoutingBehaviorFromWaypointGenerator.TunableFactory(), from_slot_constraint=ObjectRoutingBehaviorFromRoutingSlotConstraint.TunableFactory(), from_routing_formation=ObjectRouteFromRoutingFormation.TunableFactory(), from_fgl=ObjectRouteFromFGL.TunableFactory(), default='from_waypoints'), 'pre_route_animation': OptionalTunable(description='\n            If enabled, the routing object will play this animation before any\n            route planning/following happens.\n            ', tunable=ObjectAnimationElement.TunableReference()), 'actions': TunableList(description='\n            A list of things the routing object can do once they have reached a\n            routing destination.\n            ', tunable=TunableVariant(play_animation=ObjectRoutingBehaviorActionAnimation.TunableFactory(), destroy_objects=ObjectRoutingBehaviorActionDestroyObjects.TunableFactory(), default='play_animation')), 'completion_loot': TunableSet(description='\n            Upon completion, this loot is applied to the routing object. This\n            loot is not executed if the behavior was canceled.\n            ', tunable=LootActions.TunableReference()), 'walkstyle_override': OptionalTunable(description='\n            If enabled, we will override the default walkstyle for any routes\n            in this routing behavior.\n            ', tunable=WalkStyleRequest.TunableFactory(description='\n                The walkstyle request we want to make.\n                ')), 'clear_locomotion_mask': Tunable(description='\n            If enabled, override the locomotion queue mask.  This mask controls\n            which Animation Requests and XEvents get blocked during locomotion.\n            By default, the mask blocks everything.  If cleared, it blocks\n            nothing.  It also lowers the animation track used by locomotion to \n            9,999 from the default of 10,000.  Use with care, ask your GPE.\n            ', tunable_type=bool, default=False)}

    def __init__(self, obj, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._obj = obj
        self._route_data = self.route(obj)
        self._canceled = False
        self._element = None

    def _do_single_route_gen(self, timeline, route):
        if not route:
            yield from self._route_data.do_route_fail_gen(timeline)
            return True
        self._element = plan_primitive = PlanRoute(route, self._obj)
        result = yield from element_utils.run_child(timeline, plan_primitive)
        if not result:
            return result
        nodes = plan_primitive.path.nodes
        if not (nodes and nodes.plan_success):
            yield from self._route_data.do_route_fail_gen(timeline)
            return True
        if self._canceled:
            return False
        plan_primitive.path.blended_orientation = self._route_data.get_randomize_orientation()
        mask_override = None
        track_override = None
        if self.clear_locomotion_mask:
            mask_override = 0
            track_override = 9999
        self._element = follow_path_element = FollowPath(self._obj, plan_primitive.path, track_override=track_override, mask_override=mask_override)
        result = yield from element_utils.run_child(timeline, follow_path_element)
        if not result:
            return result
        if self._canceled:
            return False
        for action in self.actions:
            result = yield from action.run_action_gen(timeline, self._obj, self._route_data.get_target())
            if not result:
                return result
        return True

    def _run_gen(self, timeline):
        if self.pre_route_animation is not None:
            animation_element = self.pre_route_animation(self._obj)
            self._element = build_element((animation_element, flush_all_animations))
            result = yield from element_utils.run_child(timeline, self._element)
            if not result:
                return result

        def do_routes(timeline):
            result = False
            for route in self._route_data.get_routes_gen():
                result = yield from self._do_single_route_gen(timeline, route)
                if not result:
                    break
            if not result:
                yield from element_utils.run_child(timeline, element_utils.sleep_until_next_tick_element())
            return result

        if self.walkstyle_override is None:
            yield from do_routes(timeline)
        else:
            walkstyle_request = self.walkstyle_override(self._obj)
            yield from element_utils.run_child(timeline, walkstyle_request(sequence=do_routes))
        resolver = SingleObjectResolver(self._obj)
        for loot_action in self.completion_loot:
            loot_action.apply_to_resolver(resolver)
        return True

    def _soft_stop(self):
        self._canceled = True
        if self._element is not None:
            self._element.trigger_soft_stop()
        return super()._soft_stop()
