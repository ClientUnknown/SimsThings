from animation.arb import Arbfrom animation.arb_element import distribute_arb_elementfrom animation.posture_manifest import MATCH_NONEfrom event_testing.resolver import SingleObjectResolver, SingleSimResolverfrom event_testing.results import TestResultfrom interactions import ParticipantTypefrom interactions.utils.animation_reference import TunableAnimationReferencefrom interactions.utils.routing import FollowPathfrom postures import are_carry_compatiblefrom routing.route_events.route_event_mixins import RouteEventDataBasefrom sims4.math import MAX_INT32from sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, OptionalTunable, TunableRange, TunableEnumEntryimport sims4.loglogger = sims4.log.Logger('RouteEvents', default_owner='rmccord')
class RouteEventTypeAnimation(RouteEventDataBase, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'animation_element': TunableAnimationReference(description='\n            The animation that Sims play during the Route Event.\n            ', callback=None, class_restrictions=()), '_duration_override': OptionalTunable(description="\n            If enabled, we override the must run duration we expect this route\n            event to take. We do this for animations that will freeze the\n            locomotion so that we don't actually take time away from the rest of\n            the path where other route events could play.\n            ", tunable=TunableRange(description='\n                The duration we want this route event to have. This modifies how\n                much of the route time this event will take up to play the\n                animation. For route events that freeze locomotion, you might\n                want to set this to a very low value. Bear in mind that high\n                values are less likely to be scheduled for shorter routes.\n                ', tunable_type=float, default=0.1, minimum=0.1)), 'target_participant': OptionalTunable(description='\n            The target of the animation based on the resolver of the actor\n            playing the route event.\n            ', tunable=TunableEnumEntry(description='\n                The participant related to the actor that plays the route event.\n                ', tunable_type=ParticipantType, default=ParticipantType.ObjectChildren))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.arb = None
        self._duration_total = MAX_INT32
        self._duration_must_run = MAX_INT32
        self._duration_repeat = MAX_INT32

    @classmethod
    def test(cls, actor, event_data_tuning, ignore_carry=False):
        if actor is None:
            return TestResult(False, 'Route Event Actor is None.')
        if actor.is_sim:
            postures = event_data_tuning.animation_element.get_supported_postures()
            sim_posture_state = actor.posture_state
            provided_postures = sim_posture_state.body.get_provided_postures(surface_target=MATCH_NONE)
            supported_postures = provided_postures.intersection(postures)
            if not supported_postures:
                return TestResult(False, 'Animation Route Event does not support {} for {}.', actor.posture_state, actor)
            if not ignore_carry:
                carry_state = sim_posture_state.get_carry_state()
                if not any(are_carry_compatible(entry, carry_state) for entry in supported_postures):
                    return TestResult(False, 'Animation Route Event does not support {} for {}.', actor.posture_state, actor)
        return TestResult.TRUE

    @property
    def duration_override(self):
        if self._duration_override is not None:
            return self._duration_override
        return self._duration_must_run

    def get_target(self, actor):
        if self.target_participant is None:
            return
        else:
            if actor.is_sim:
                resolver = SingleSimResolver(actor.sim_info)
            else:
                resolver = SingleObjectResolver(actor)
            targets = resolver.get_participants(self.target_participant)
            if targets:
                return next(iter(targets))

    def prepare(self, actor, setup_asm_override=None):

        def restart_asm(asm):
            asm.set_current_state('entry')
            return True

        target = self.get_target(actor)
        routing_component = actor.routing_component
        if actor.is_sim:
            route_interaction = routing_component.route_interaction
            if route_interaction is None:
                logger.error('Route Interaction was None for {}', actor)
                return
            route_event_animation = self.animation_element(route_interaction, setup_asm_additional=restart_asm if setup_asm_override is None else setup_asm_override, enable_auto_exit=False)
            asm = route_event_animation.get_asm()
            if asm is not None and target is not None and not asm.set_actor(route_event_animation.target_name, target):
                logger.error('Route Event {} Failed to setup target.', self)
                return
            if asm is None:
                logger.warn('Unable to get a valid Route Event ASM ({}) for {}.', route_event_animation, actor)
                return
            route_event_animation.overrides.override_asm(asm)
        else:
            route_event_animation = self.animation_element(actor, target=target, setup_asm_func=restart_asm if setup_asm_override is None else setup_asm_override)
            animation_context = routing_component.animation_context
            asm = route_event_animation.get_asm(animation_context=animation_context)
            if asm is None:
                logger.warn('Unable to get a valid Route Event ASM ({}) for {}.', route_event_animation, actor)
                return
        self.arb = Arb()
        route_event_animation.append_to_arb(asm, self.arb)
        route_event_animation.append_exit_to_arb(asm, self.arb)
        if self.arb is None:
            logger.error('Unable to create arb for Route Event: {}', self)
            return
        (self._duration_total, self._duration_must_run, self._duration_repeat) = self.arb.get_timing()

    def is_valid_for_scheduling(self, actor, path):
        if self.arb is None or self.arb.empty:
            return False
        return True

    def execute(self, actor, **kwargs):
        if actor.primitives:
            for primitive in tuple(actor.primitives):
                if isinstance(primitive, FollowPath):
                    primitive.set_animation_sleep_end(self._duration_must_run)
                    return

    def process(self, actor):
        if self.arb is not None:
            distribute_arb_element(self.arb, master=actor, immediate=True)
