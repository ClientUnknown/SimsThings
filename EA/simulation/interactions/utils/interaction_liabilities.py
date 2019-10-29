from _collections import defaultdictfrom _weakrefset import WeakSetfrom weakref import WeakKeyDictionaryimport weakreffrom interactions.interaction_finisher import FinishingTypefrom interactions.liability import Liability, ReplaceableLiabilityfrom postures import PostureEventfrom sims4.utils import setdefault_callableimport servicesimport sims4.loglogger = sims4.log.Logger('Liability', default_owner='rmccord')ANIMATION_CONTEXT_LIABILITY = 'AnimationContext'
class AnimationContextLiability(Liability):

    def __init__(self, animation_context, **kwargs):
        super().__init__(**kwargs)
        self._animation_context = animation_context
        self._animation_context.add_ref(ANIMATION_CONTEXT_LIABILITY)
        self._event_handle = None
        self._interaction = None
        self.cached_asm_keys = defaultdict(set)

    @property
    def animation_context(self):
        return self._animation_context

    def unregister_handles(self, interaction):
        if self._event_handle is not None:
            self._event_handle.release()
            self._event_handle = None

    def setup_props(self, interaction):
        previous_interaction = self._interaction
        self._interaction = interaction
        if self._interaction is None:
            if self._event_handle is not None:
                self._event_handle.release()
                self._event_handle = None
            return
        if previous_interaction != interaction:
            if self._event_handle is not None:
                self._event_handle.release()
            self._event_handle = self._animation_context.register_custom_event_handler(self._hide_other_held_props, interaction.sim, 0, optional=True)

    def _hide_other_held_props(self, _):
        self._event_handle = None
        for sim in self._interaction.required_sims():
            for si in sim.si_state:
                if si is not self._interaction.super_interaction and not si.preserve_held_props_during_other_si:
                    si.animation_context.set_all_prop_visibility(False, held_only=True)

    def transfer(self, interaction):
        if self._animation_context is not None:
            logger.debug('TRANSFER: {} -> {}', self.animation_context, interaction)
            self.animation_context.reset_for_new_interaction()

    def release(self):
        if self._animation_context is not None:
            self._animation_context.release_ref(ANIMATION_CONTEXT_LIABILITY)
            logger.debug('RELEASE : {}', self.animation_context)
            self._animation_context = None

    def gsi_text(self):
        return '{}::context_id:{}'.format(type(self).__name__, self._animation_context.request_id)
PRIVACY_LIABILITY = 'PrivacyLiability'
class PrivacyLiability(Liability):

    def __init__(self, interaction, target=None, **kwargs):
        super().__init__(**kwargs)
        self._privacy = interaction.privacy.privacy_snippet(interaction=interaction)
        try:
            if not self._privacy.build_privacy(target=target):
                self._privacy.remove_privacy()
        except:
            if self._privacy:
                self._privacy.remove_privacy()
            raise

    @property
    def privacy(self):
        return self._privacy

    def should_transfer(self, continuation):
        return False

    def release(self):
        self._privacy.remove_privacy()

    def on_reset(self):
        self._privacy.remove_privacy()
FITNESS_LIABILITY = 'FitnessLiability'
class FitnessLiability(Liability):

    def __init__(self, sim, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim

    def release(self):
        self.sim.sim_info.update_fitness_state()
OWNS_POSTURE_LIABILITY = 'OwnsPostureLiability'
class OwnsPostureLiability(ReplaceableLiability):

    def __init__(self, interaction, posture):
        self._interaction_ref = None
        self._posture_ref = weakref.ref(posture)

    def should_transfer(self, continuation):
        if continuation.involves_carry or not (self._posture_ref is not None and self._posture_ref().IS_BODY_POSTURE):
            return False
        return True

    def on_add(self, interaction):
        super().on_add(interaction)
        if self._posture is not None:
            self._interaction_ref = weakref.ref(interaction)
            self._posture.add_owning_interaction(self._interaction)

    def transfer(self, interaction):
        if self._posture is not None:
            self._posture.remove_owning_interaction(self._interaction)

    def release(self):
        if self._posture is not None:
            self._posture.remove_owning_interaction(self._interaction)

    @property
    def _posture(self):
        return self._posture_ref()

    @property
    def _interaction(self):
        return self._interaction_ref()
UNCANCELABLE_LIABILITY = 'UncanceableLiability'
class UncancelableLiability(Liability):
    pass
CANCEL_AOP_LIABILITY = 'CancelAOPLiability'
class CancelAOPLiability(Liability):

    def __init__(self, sim, interaction_cancel_replacement, interaction_to_cancel, release_callback, posture, **kwargs):
        super().__init__(**kwargs)
        self._sim_ref = weakref.ref(sim)
        self._interaction_cancel_replacement_ref = weakref.ref(interaction_cancel_replacement)
        self._interaction_to_cancel_ref = weakref.ref(interaction_to_cancel)
        self._release_callback = release_callback
        self._posture = posture
        if posture is not None:
            self._posture.add_cancel_aop(interaction_cancel_replacement)
        sim.on_posture_event.append(self._on_posture_changed)

    @property
    def interaction_to_cancel(self):
        return self._interaction_to_cancel_ref()

    def release(self):
        self._sim_ref().on_posture_event.remove(self._on_posture_changed)
        if self._release_callback is not None:
            self._release_callback(self._posture)
        sim = self._sim_ref()
        if sim is not None and (sim.posture is self._posture and (sim.posture.ownable and (self._posture.owning_interactions and len(self._posture.owning_interactions) == 1))) and self._interaction_cancel_replacement_ref() in self._posture.owning_interactions:
            if not sim.posture.unconstrained:
                sim.schedule_reset_asap(source=self._posture.target, cause="CancelAOPLiability released without changing the Sim's posture away from {}".format(self._posture))
            else:
                sim.ui_manager.update_interaction_cancel_status(self.interaction_to_cancel)

    def _on_posture_changed(self, change, dest_state, track, old_value, new_value):
        if self._posture.track == track and change == PostureEvent.POSTURE_CHANGED:
            interaction = self._interaction_cancel_replacement_ref()
            sim = self._sim_ref()
            if interaction is None or sim is None or sim.queue.transition_controller is None:
                return
            if interaction is new_value.source_interaction or interaction in new_value.owning_interactions:
                return
            transition_controller_interaction = sim.queue.transition_controller.interaction
            if transition_controller_interaction is interaction or transition_controller_interaction.sim is not interaction.sim:
                return
            interaction.cancel(FinishingType.LIABILITY, cancel_reason_msg='CancelAOPLiability. Posture changed before cancel_replacement completed.')
CANCEL_INTERACTION_ON_EXIT_LIABILITY = 'CancelInteractionsOnExitLiability'
class CancelInteractionsOnExitLiability(Liability):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._to_cancel_for_sim = WeakKeyDictionary()

    def merge(self, interaction, key, new_liability):
        if not isinstance(new_liability, CancelInteractionsOnExitLiability):
            raise TypeError('Cannot merge a CancelInteractionsOnExitLiability with a ' + type(new_liability).__name__)
        if key != CANCEL_INTERACTION_ON_EXIT_LIABILITY:
            raise ValueError('Mysterious and unexpected key: {} instead of {}'.format(key, CANCEL_INTERACTION_ON_EXIT_LIABILITY))
        old_keys = set(self._to_cancel_for_sim.keys())
        new_keys = set(new_liability._to_cancel_for_sim.keys())
        for key in old_keys & new_keys:
            new_liability._to_cancel_for_sim[key] |= self._to_cancel_for_sim[key]
        for key in old_keys - new_keys:
            new_liability._to_cancel_for_sim[key] = self._to_cancel_for_sim[key]
        return new_liability

    def release(self):
        for (sim, affordances_or_interactions) in tuple(self._to_cancel_for_sim.items()):
            for affordance_or_interaction in tuple(affordances_or_interactions):
                if affordance_or_interaction is not affordance_or_interaction.affordance:
                    interaction = affordance_or_interaction
                else:
                    interaction = sim.si_state.get_si_by_affordance(affordance_or_interaction)
                if interaction is not None:
                    if interaction.depended_on_until_running:
                        transition = interaction.transition
                        if transition is not None and transition.running:
                            pass
                        else:
                            interaction.cancel(FinishingType.LIABILITY, cancel_reason_msg='CancelInteractionsOnExitLiability released')
                    else:
                        interaction.cancel(FinishingType.LIABILITY, cancel_reason_msg='CancelInteractionsOnExitLiability released')

    def add_cancel_entry(self, sim, affordance_or_interaction):
        if sim not in self._to_cancel_for_sim:
            self._to_cancel_for_sim[sim] = WeakSet()
        self._to_cancel_for_sim[sim].add(affordance_or_interaction)

    def remove_cancel_entry(self, sim, affordance_or_interaction):
        interactions_to_cancel = self._to_cancel_for_sim.get(sim, None)
        if interactions_to_cancel is None:
            return
        if affordance_or_interaction in interactions_to_cancel:
            interactions_to_cancel.remove(affordance_or_interaction)
        if len(interactions_to_cancel) == 0:
            del self._to_cancel_for_sim[sim]

    def get_cancel_entries_for_sim(self, sim):
        return self._to_cancel_for_sim.get(sim, None)
LOCK_GUARANTEED_ON_SI_WHILE_RUNNING = 'LockGuaranteedOnSIWhileRunning'
class LockGuaranteedOnSIWhileRunning(Liability):

    def __init__(self, si_to_lock, **kwargs):
        super().__init__(**kwargs)
        self._unlock_fn = si_to_lock.lock_guaranteed()

    def release(self):
        self._unlock_fn()
STAND_SLOT_LIABILITY = 'StandSlotReservationLiability'
class StandSlotReservationLiability(ReplaceableLiability):

    def __init__(self, sim, interaction):
        self._sim = sim
        self._interaction_ref = weakref.ref(interaction)

    def should_transfer(self, continuation):
        return False

    @property
    def sim(self):
        return self._sim

    @property
    def interaction(self):
        return self._interaction_ref()

    def release(self):
        self.sim.routing_component.remove_stand_slot_reservation(self.interaction)
        self._sim = None
RESERVATION_LIABILITY = 'ReservationLiability'
class ReservationLiability(ReplaceableLiability):

    def __init__(self, reservation_handlers):
        self._reservation_handlers = reservation_handlers

    def on_reset(self):
        self.release_reservations()

    def release(self):
        self.release_reservations()

    def should_transfer(self, continuation):
        return False

    def release_reservations(self):
        for handler in self._reservation_handlers:
            handler.end_reservation()
SITUATION_LIABILITY = 'SituationLiability'
class SituationLiability(Liability):

    def __init__(self, situation, **kwargs):
        super().__init__(**kwargs)
        self._situation = situation

    def on_reset(self):
        services.get_zone_situation_manager().destroy_situation_by_id(self._situation.id)

    def release(self):
        services.get_zone_situation_manager().destroy_situation_by_id(self._situation.id)

    def should_transfer(self, continuation):
        return True
AUTONOMY_MODIFIER_LIABILITY = 'AutonomyModifierLiability'
class AutonomyModifierLiability(Liability):

    def __init__(self, interaction, **kwargs):
        super().__init__(**kwargs)
        self._sim = interaction.sim
        self._autonomy_modifier_handles = weakref.WeakKeyDictionary()
        autonomy_modifiers = interaction.target.autonomy_modifiers
        for modifier in autonomy_modifiers:
            subject = self._sim
            if modifier.subject:
                subject = interaction.get_participant(modifier.subject)
            if subject is not None:
                handle = subject.add_statistic_modifier(modifier, interaction_modifier=True)
                setdefault_callable(self._autonomy_modifier_handles, subject, list).append(handle)

    def release(self, *args, **kwargs):
        for (subject, handles) in self._autonomy_modifier_handles.items():
            for handle in handles:
                subject.remove_statistic_modifier(handle)
