from animation.animation_utils import flush_all_animationsfrom animation.arb_element import distribute_arb_elementfrom animation.posture_manifest import Handfrom element_utils import build_critical_section, build_critical_section_with_finallyfrom elements import ParentElementfrom postures.posture_specs import get_origin_spec, PostureSpecVariablefrom postures.transition import PostureTransitionfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableReference, TunableEnumEntryimport animation.arbimport element_utilsimport routingimport servicesimport sims4.loglogger = sims4.log.Logger('SetPosture', default_owner='tingyul')
class SetPosture(ParentElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'posture_type': TunableReference(description='\n            Posture to set.\n            ', manager=services.posture_manager()), 'surface_type': TunableEnumEntry(routing.SurfaceType, description='\n            The surface type the posture requires. For example, swim should set\n            this to SURFACETYPE_POOL.\n            ', default=routing.SurfaceType.SURFACETYPE_WORLD)}

    def __init__(self, interaction, *args, sequence=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.interaction = interaction
        self.sequence = sequence
        self._event_handler_handle = None
        self._xevt_triggered = False
        self._previous_posture_state = None

    def _run(self, timeline):
        sequence = build_critical_section(build_critical_section_with_finally(self._register_set_posture_xevt, self.sequence, self._release_set_posture_xevt), self._start_posture_gen)
        return timeline.run_child(sequence)

    def _register_set_posture_xevt(self, element):
        self._event_handler_handle = self.interaction.animation_context.register_event_handler(self._set_posture, handler_id=PostureTransition.IDLE_TRANSITION_XEVT)

    def _release_set_posture_xevt(self, element):
        self._event_handler_handle.release()
        self._event_handler_handle = None

    def _set_posture(self, *args, **kwargs):
        self._xevt_triggered = True
        from postures.posture_state import PostureState
        sim = self.interaction.sim
        self._previous_posture_state = sim.posture_state
        origin_posture_spec = get_origin_spec(self.posture_type)
        sim.posture_state = PostureState(sim, None, origin_posture_spec, {PostureSpecVariable.HAND: (Hand.LEFT,)})
        sim.posture_state.body.source_interaction = sim.create_default_si()
        idle_arb = animation.arb.Arb()
        sim.posture.append_transition_to_arb(idle_arb, None)
        sim.posture.append_idle_to_arb(idle_arb)
        distribute_arb_element(idle_arb, master=sim)

    def _start_posture_gen(self, timeline):
        if not self._xevt_triggered:
            if self.interaction.has_been_canceled:
                return
            logger.error('{} is missing a 750 xevt in its animation. Set Posture basic extra requires it to work correctly. Without it, Sim will likely pop between posture idles.', self.interaction)
            self._set_posture()
        sim = self.interaction.sim
        target = self.interaction.target if self.interaction.target is not None else sim
        routing_surface = routing.SurfaceIdentifier(target.zone_id, target.level, self.surface_type)
        sim.move_to(routing_surface=routing_surface)
        self.interaction.satisfied = True
        yield from element_utils.run_child(timeline, (sim.posture.get_idle_behavior(), flush_all_animations))
        yield from sim.posture_state.kickstart_gen(timeline, routing_surface)
        for aspect in self._previous_posture_state.aspects:
            yield from element_utils.run_child(timeline, aspect.end())
