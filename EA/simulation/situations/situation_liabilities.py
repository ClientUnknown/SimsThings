from interactions import ParticipantTypefrom interactions.interaction_finisher import FinishingTypefrom interactions.liability import Liability, ReplaceableLiabilityfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, Tunablefrom situations.situation_sim_providers import SituationSimParticipantProviderMixinfrom situations.situation_types import SituationCallbackOptionfrom situations.tunable import TunableSituationStartimport servicesAUTO_INVITE_LIABILTIY = 'AutoInviteLiability'
class AutoInviteLiability(Liability):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._target_sim = None
        self._situation_id = None
        self._interaction = None

    def on_add(self, interaction):
        self._interaction = interaction
        self._target_sim = interaction.get_participant(ParticipantType.TargetSim)
        situation_manager = services.get_zone_situation_manager()
        self._situation_id = situation_manager.create_visit_situation(self._target_sim)
        situation_manager.bouncer._assign_instanced_sims_to_unfulfilled_requests()

    def release(self):
        if not self._target_sim.is_on_active_lot():
            situation_manager = services.get_zone_situation_manager()
            situation_manager.destroy_situation_by_id(self._situation_id)

    def should_transfer(self, continuation):
        return False

class CreateSituationLiability(Liability, HasTunableFactory, AutoFactoryInit):
    LIABILITY_TOKEN = 'CreateSituationLiability'
    FACTORY_TUNABLES = {'create_situation': TunableSituationStart(), 'cancel_interaction_on_situation_end': Tunable(description='\n            If enabled, we will cancel the interaction with this liability\n            whenever the created situation ends. Note: this will not merge well\n            with another liability that has the opposite setting.\n            ', tunable_type=bool, default=True)}

    def __init__(self, interaction, **kwargs):
        super().__init__(**kwargs)
        self._situation_ids = set()
        self._interaction = interaction

    def on_add(self, interaction):
        self._interaction = interaction

    def on_run(self):
        if not self._is_create_situation_already_running():
            self.create_situation(self._interaction.get_resolver(), situation_created_callback=self.on_situation_created)()

    def release(self):
        self._interaction = None
        self.destroy_situations()

    def transfer(self, interaction):
        self._interaction = interaction

    def should_transfer(self, continuation):
        self.validate_situations()
        if not self._situation_ids:
            return False
        return True

    def merge(self, interaction, key, new_liability):
        new_liability._situation_ids.update(self._situation_ids)
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._situation_ids:
            situation_manager.unregister_callback(situation_id, SituationCallbackOption.END_OF_SITUATION, self._situation_end_callback)
            situation_manager.register_for_callback(situation_id, SituationCallbackOption.END_OF_SITUATION, new_liability._situation_end_callback)
        return new_liability

    def _is_create_situation_already_running(self):
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._situation_ids:
            if isinstance(situation_manager.get(situation_id), self.create_situation._tuned_values.situation):
                return True
        return False

    def validate_situations(self):
        situation_manager = services.get_zone_situation_manager()
        invalid_ids = set()
        for situation_id in self._situation_ids:
            if situation_manager.get(situation_id) is None:
                invalid_ids.add(situation_id)
        self._situation_ids.difference_update(invalid_ids)

    def destroy_situations(self):
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._situation_ids:
            situation_manager.unregister_callback(situation_id, SituationCallbackOption.END_OF_SITUATION, self._situation_end_callback)
            situation_manager.destroy_situation_by_id(situation_id)

    def on_situation_created(self, situation_id):
        self._situation_ids.add(situation_id)
        situation_manager = services.get_zone_situation_manager()
        situation_manager.register_for_callback(situation_id, SituationCallbackOption.END_OF_SITUATION, self._situation_end_callback)

    def _situation_end_callback(self, situation_id, callback_option, _):
        if callback_option == SituationCallbackOption.END_OF_SITUATION:
            if self.cancel_interaction_on_situation_end and self._interaction is not None:
                self._interaction.cancel(FinishingType.SITUATIONS, 'Situation owned by liability was destroyed.')
            self._situation_ids.discard(situation_id)

class SituationSimParticipantProviderLiability(ReplaceableLiability, SituationSimParticipantProviderMixin):
    LIABILITY_TOKEN = 'SituationSimParticipantProviderLiability'

    def __init__(self, interaction=None, **__):
        super().__init__(**__)
