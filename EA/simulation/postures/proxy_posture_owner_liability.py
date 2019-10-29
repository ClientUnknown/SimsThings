from interactions.interaction_finisher import FinishingTypefrom interactions.liability import Liabilityfrom sims4.tuning.tunable import HasTunableFactory
class ProxyPostureOwnerLiability(Liability, HasTunableFactory):
    LIABILITY_TOKEN = 'ProxyPostureOwnerLiability'

    def __init__(self, interaction, **kwargs):
        super().__init__(**kwargs)
        self._interaction = interaction

    def transfer(self, interaction):
        self._interaction = interaction

    def release(self):
        sim = self._interaction.sim
        posture = sim.posture_state.body
        if self._interaction in posture.owning_interactions and (len(posture.owning_interactions) == 1 and posture.source_interaction is not None) and posture.source_interaction is not self._interaction:
            posture.source_interaction.cancel(FinishingType.SI_FINISHED, cancel_reason_msg='Posture Proxy Owner Liability Released')
