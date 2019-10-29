from animation.tunable_animation_overrides import TunableAnimationOverridesfrom animation.animation_utils import flush_all_animationsfrom balloon.tunable_balloon import TunableBalloonfrom element_utils import build_elementfrom interactions.context import InteractionSourcefrom interactions.utils.animation_reference import TunableAnimationReferencefrom interactions.utils.routing_constants import TransitionFailureReasonsimport autonomyimport element_utilsimport services
def handle_transition_failure(sim, source_interaction_target, transition_interaction, failure_reason=None, failure_object_id=None):
    if transition_interaction.visible or not transition_interaction.always_show_route_failure:
        return
    if not transition_interaction.route_fail_on_transition_fail:
        return
    if transition_interaction.is_adjustment_interaction():
        return

    def _do_transition_failure(timeline):
        if source_interaction_target is not None:
            sim.add_lockout(source_interaction_target, autonomy.autonomy_modes.AutonomyMode.LOCKOUT_TIME)
        if transition_interaction is None:
            return
        if transition_interaction.context.source == InteractionSource.AUTONOMY:
            return
        yield from element_utils.run_child(timeline, route_failure(sim, transition_interaction, failure_reason, failure_object_id))

    return _do_transition_failure

class RouteFailureTunables:
    route_fail_animation = TunableAnimationReference(description='\n                               Route Failure Animation                     \n                               Note: Route Failure Balloons are handled specially and not tuned here. See: route_fail_overrides_object, route_fail_overrides_build\n                               ', callback=None)
    route_fail_overrides_object = TunableAnimationOverrides()
    route_fail_overrides_reservation = TunableAnimationOverrides()
    route_fail_overrides_build = TunableAnimationOverrides()
    route_fail_overrides_no_dest_node = TunableAnimationOverrides()
    route_fail_overrides_no_path_found = TunableAnimationOverrides()
    route_fail_overrides_no_valid_intersection = TunableAnimationOverrides()
    route_fail_overrides_no_goals_generated = TunableAnimationOverrides()
    route_fail_overrides_no_connectivity = TunableAnimationOverrides()
    route_fail_overrides_path_plan_fail = TunableAnimationOverrides()
    route_fail_overrides_goal_on_slope = TunableAnimationOverrides()
ROUTE_FAILURE_OVERRIDE_MAP = None
def route_failure(sim, interaction, failure_reason, failure_object_id):
    global ROUTE_FAILURE_OVERRIDE_MAP
    if not sim.should_route_fail:
        return
    overrides = None
    if failure_reason is not None:
        if ROUTE_FAILURE_OVERRIDE_MAP is None:
            ROUTE_FAILURE_OVERRIDE_MAP = {TransitionFailureReasons.GOAL_ON_SLOPE: RouteFailureTunables.route_fail_overrides_goal_on_slope, TransitionFailureReasons.PATH_PLAN_FAILED: RouteFailureTunables.route_fail_overrides_path_plan_fail, TransitionFailureReasons.NO_CONNECTIVITY_TO_GOALS: RouteFailureTunables.route_fail_overrides_no_connectivity, TransitionFailureReasons.NO_GOALS_GENERATED: RouteFailureTunables.route_fail_overrides_no_goals_generated, TransitionFailureReasons.NO_VALID_INTERSECTION: RouteFailureTunables.route_fail_overrides_no_valid_intersection, TransitionFailureReasons.NO_PATH_FOUND: RouteFailureTunables.route_fail_overrides_no_path_found, TransitionFailureReasons.NO_DESTINATION_NODE: RouteFailureTunables.route_fail_overrides_no_dest_node, TransitionFailureReasons.BUILD_BUY: RouteFailureTunables.route_fail_overrides_build, TransitionFailureReasons.RESERVATION: RouteFailureTunables.route_fail_overrides_reservation, TransitionFailureReasons.BLOCKING_OBJECT: RouteFailureTunables.route_fail_overrides_object}
        if failure_reason in ROUTE_FAILURE_OVERRIDE_MAP:
            overrides = ROUTE_FAILURE_OVERRIDE_MAP[failure_reason]()
            if failure_object_id is not None:
                fail_obj = services.object_manager().get(failure_object_id)
                if fail_obj is not None:
                    if fail_obj.blocking_balloon_overrides is not None:
                        overrides.balloons = fail_obj.blocking_balloon_overrides
                    else:
                        overrides.balloon_target_override = fail_obj
    route_fail_anim = RouteFailureTunables.route_fail_animation(sim.posture.source_interaction, overrides=overrides, sequence=())
    supported_postures = route_fail_anim.get_supported_postures()
    if supported_postures:
        return build_element((route_fail_anim, flush_all_animations))
    else:
        balloon_requests = TunableBalloon.get_balloon_requests(interaction, route_fail_anim.overrides)
        return balloon_requests
