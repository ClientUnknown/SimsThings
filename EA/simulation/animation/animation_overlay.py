from animation.animation_element import AnimationElementfrom animation.animation_interaction import AnimationInteractionfrom animation.arb import Arbfrom animation.arb_element import distribute_arb_elementfrom event_testing.test_events import TestEventfrom interactions.aop import AffordanceObjectPairfrom interactions.context import InteractionContextfrom interactions.interaction_finisher import FinishingTypefrom interactions.priority import Priorityfrom objects.components import Component, types, componentmethodfrom postures import PostureEvent, PostureTrackfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableListimport servicesimport sims4.loglogger = sims4.log.Logger('Animation')
class AnimationOverlay(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'_overlay_animation': AnimationElement.TunableReference(description='\n            The animation element controlling the overlay.\n            ')}

    def __init__(self, sim, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim = sim
        self._sim.on_posture_event.append(self._on_posture_changed)
        self._overlay_interaction = None

    def start_overlay(self):
        aop = AffordanceObjectPair(AnimationInteraction, None, AnimationInteraction, None, hide_unrelated_held_props=False)
        context = InteractionContext(self._sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
        self._overlay_interaction = aop.interaction_factory(context).interaction

    def stop_overlay(self):
        if self._overlay_interaction is None:
            return
        self._overlay_interaction.cancel(FinishingType.RESET, 'Stopping overlay animations.')
        self._overlay_interaction.on_removed_from_queue()
        self._overlay_interaction = None

    def update_overlay(self):

        def restart_overlay_asm(asm):
            asm.set_current_state('entry')
            return True

        if self._overlay_interaction is None:
            return
        overlay_animation = self._overlay_animation(self._overlay_interaction, setup_asm_additional=restart_overlay_asm, enable_auto_exit=False)
        asm = overlay_animation.get_asm()
        if asm is None:
            logger.warn(' Unable to get a valid overlay ASM ({}) for {}.', self._overlay_animation, self._sim)
            return
        arb = Arb()
        overlay_animation.append_to_arb(asm, arb)
        distribute_arb_element(arb)

    def _on_posture_changed(self, change, dest_state, track, old_value, new_value):
        if change == PostureEvent.POSTURE_CHANGED and track == PostureTrack.BODY and self._overlay_interaction is not None:
            self._overlay_interaction.clear_animation_liability_cache()

class AnimationOverlayComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=types.ANIMATION_OVERLAY_COMPONENT):
    ANIMATION_OVERLAY_EVENTS = (TestEvent.MoodChange,)
    FACTORY_TUNABLES = {'animation_overlays': TunableList(description='\n            A list of animation overlays to play on this Sim.\n            ', tunable=AnimationOverlay.TunableFactory())}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._animation_overlays = []

    def on_add(self):
        for animation_overlay in self.animation_overlays:
            self._animation_overlays.append(animation_overlay(self.owner))
        services.get_event_manager().register(self, self.ANIMATION_OVERLAY_EVENTS)

    def on_remove(self):
        services.get_event_manager().unregister(self, self.ANIMATION_OVERLAY_EVENTS)

    def handle_event(self, sim_info, event_type, resolver):
        if self.owner.is_sim and self.owner.sim_info is not sim_info:
            return
        self.update_animation_overlays()

    @componentmethod
    def start_animation_overlays(self):
        for animation_overlay in self._animation_overlays:
            animation_overlay.start_overlay()

    @componentmethod
    def stop_animation_overlays(self):
        for animation_overlay in self._animation_overlays:
            animation_overlay.stop_overlay()

    @componentmethod
    def update_animation_overlays(self):
        for animation_overlay in self._animation_overlays:
            animation_overlay.update_overlay()
