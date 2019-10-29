from buffs.tunable import TunableBuffReferencefrom interactions.interaction_finisher import FinishingTypefrom interactions.liability import SharedLiabilityfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, OptionalTunable
class GameChallengeLiability(HasTunableFactory, AutoFactoryInit, SharedLiability):
    LIABILITY_TOKEN = 'GameChallengeLiability'
    FACTORY_TUNABLES = {'challenge_buff': TunableBuffReference(description='\n            The buff assigned to challenging Sims for the duration of the\n            challenge.\n            '), 'forfeit_buff': OptionalTunable(description='\n            If enabled, specify a buff awarded to Sims that forfeit the\n            challenge.\n            ', tunable=TunableBuffReference(description='\n                The buff to award to Sims that forfeit the challenge.\n                '))}

    def __init__(self, interaction, *args, game=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._interaction = interaction
        self._game = game

    @property
    def _sim(self):
        return self._interaction.sim

    def _get_linked_sims(self):
        return {liability._sim for liability in self._shared_liability_refs}

    def create_new_liability(self, interaction):
        liability = super().create_new_liability(interaction, interaction, game=self._game, challenge_buff=self.challenge_buff, forfeit_buff=self.forfeit_buff)
        self._game = None
        return liability

    def on_game_started(self, game):
        self._sim.add_buff_from_op(self.challenge_buff.buff_type, buff_reason=self.challenge_buff.buff_reason)
        self._game = game
        linked_sims = self._get_linked_sims()
        if len(linked_sims) <= 1:
            self._interaction.cancel(FinishingType.NATURAL, cancel_reason_msg='Challenge ended due to Sims forfeiting')
            return
        for sim in linked_sims:
            game.add_challenger(sim)

    def release(self, *args, **kwargs):
        if self._game is not None:
            self._game.remove_challenger(self._sim)
            self._sim.remove_buff_by_type(self.challenge_buff.buff_type)
            if not self._game.game_has_ended:
                if self.forfeit_buff is not None:
                    self._sim.add_buff_from_op(self.forfeit_buff.buff_type, buff_reason=self.forfeit_buff.buff_reason)
                if len(self._game.challenge_sims) <= 1:
                    for liability in self._shared_liability_refs:
                        liability._interaction.cancel(FinishingType.NATURAL, cancel_reason_msg='Challenge ended due to Sims forfeiting')
        return super().release(*args, **kwargs)

    def shared_release(self):
        pass
