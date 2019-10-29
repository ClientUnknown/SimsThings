from element_utils import build_critical_section_with_finally, build_elementfrom interactions import ParticipantType, ParticipantTypeSinglefrom interactions.liability import Liabilityfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom interactions.utils.loot_basic_op import BaseLootOperationfrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.tunable import TunableEnumEntry, OptionalTunable, TunableTuple, Tunable, HasTunableSingletonFactory, TunableVariant, AutoFactoryInitfrom sims4.tuning.tunable_hash import TunableStringHash32from tunable_utils.tunable_object_generator import TunableObjectGeneratorVariantfrom vfx import PlayEffect
class _VisualEffectLifetimeOneShot(HasTunableSingletonFactory):

    def start_visual_effect(self, vfx):
        vfx.start_one_shot()

    def get_visual_effect_sequence(self, vfx_element, sequence):
        return sequence

class _VisualEffectLifetimeInteraction(HasTunableSingletonFactory):

    def start_visual_effect(self, vfx):
        vfx.start()

    def get_visual_effect_sequence(self, vfx_element, sequence):
        return build_critical_section_with_finally(sequence, vfx_element._stop_vfx)

class _VisualEffectLifetimeContinuationLiability(Liability):
    LIABILITY_TOKEN = '_VisualEffectLifetimeContinuationLiability'

    def __init__(self, vfx_element, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._vfx_element = vfx_element

    def release(self):
        self._vfx_element._stop_vfx()

class _VisualEffectLifetimeContinuation(HasTunableSingletonFactory):

    def start_visual_effect(self, vfx):
        vfx.start()

    def get_visual_effect_sequence(self, vfx_element, sequence):

        def attach_liability(_):
            liability = _VisualEffectLifetimeContinuationLiability(vfx_element)
            vfx_element.interaction.add_liability(liability.LIABILITY_TOKEN, liability)

        return build_element((attach_liability, sequence))

class _VisualEffectLifetimeAnimationEvent(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'event': Tunable(description='\n            The event triggering the VFX stop.\n            ', tunable_type=int, default=100)}

    def start_visual_effect(self, vfx):
        vfx.start()

    def get_visual_effect_sequence(self, vfx_element, sequence):
        got_callback = False

        def callback(*_, **__):
            nonlocal got_callback
            if got_callback:
                return
            got_callback = True
            vfx_element._stop_vfx()

        vfx_element.interaction.store_event_handler(callback, handler_id=self.event)
        return build_critical_section_with_finally(sequence, callback)

class PlayVisualEffectMixin:
    FACTORY_TUNABLES = {'vfx': PlayEffect.TunableFactory(description='\n            The effect to play.\n            '), 'vfx_target': OptionalTunable(description='\n            If enabled, the visual effect is set to target a specific joint on\n            another object or Sim.\n            ', tunable=TunableTuple(participant=TunableEnumEntry(description='\n                    The participant this visual effect targets.\n                    ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.TargetSim), joint_name=TunableStringHash32(description='\n                    The name of the slot this effect is targeted to.\n                    ', default='_FX_')))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _start_vfx(self, participant, target_participant):
        vfx_params = {}
        if target_participant is not None:
            vfx_params['target_actor_id'] = target_participant.id
            vfx_params['target_joint_name_hash'] = self.vfx_target.joint_name
        running_vfx = self.vfx(participant, **vfx_params)
        self.vfx_lifetime.start_visual_effect(running_vfx)
        return running_vfx

class PlayVisualEffectElement(XevtTriggeredElement, PlayVisualEffectMixin):
    FACTORY_TUNABLES = {'participant': TunableObjectGeneratorVariant(description='\n            The object or objects to play the effect on.\n            ', participant_default=ParticipantType.Object), 'vfx_lifetime': TunableVariant(description='\n            Define how the lifetime of this visual effect is managed.\n            ', interaction=_VisualEffectLifetimeInteraction.TunableFactory(), continuation=_VisualEffectLifetimeContinuation.TunableFactory(), one_shot=_VisualEffectLifetimeOneShot.TunableFactory(), animation_event=_VisualEffectLifetimeAnimationEvent.TunableFactory(), default='one_shot')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._running_vfx = None

    def _stop_vfx(self, *_, **__):
        if self._running_vfx is not None:
            for vfx in self._running_vfx:
                vfx.stop()

    def _do_behavior(self):
        if self._running_vfx is not None:
            return
        self._running_vfx = []
        target_participant = None
        if self.vfx_target is not None:
            target_participant = self.interaction.get_participant(self.vfx_target.participant)
            if target_participant is None:
                return
        from sims.sim_info import SimInfo
        resolver = self.interaction.get_resolver()
        for participant in self.participant.get_objects(resolver):
            if isinstance(participant, SimInfo):
                participant = participant.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            vfx = self._start_vfx(participant, target_participant)
            self._running_vfx.append(vfx)

    def _build_outer_elements(self, sequence):
        sequence = super()._build_outer_elements(sequence)
        return self.vfx_lifetime.get_visual_effect_sequence(self, sequence)

class PlayVisualEffectLootOp(BaseLootOperation, PlayVisualEffectMixin):

    def __init__(self, vfx, vfx_target, **kwargs):
        super().__init__(**kwargs)
        self.vfx = vfx
        self.vfx_target = vfx_target
        self.vfx_lifetime = _VisualEffectLifetimeOneShot()

    def _apply_to_subject_and_target(self, subject, target, resolver):
        target_participant = None
        if self.vfx_target is not None:
            target_participant = resolver.get_participant(self.vfx_target.participant)
            if target_participant is None:
                return
        from sims.sim_info import SimInfo
        if isinstance(subject, SimInfo):
            subject = subject.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        self._start_vfx(subject, target_participant)
