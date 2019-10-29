from interactions import ParticipantTypefrom interactions.liability import Liabilityfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumEntryMISSING_PET_LIABILITY = 'MissingPetLiability'
class MissingPetLiability(Liability, HasTunableFactory, AutoFactoryInit):
    LIABILITY_TOKEN = MISSING_PET_LIABILITY
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant of the interaction that is going missing.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor)}

    def __init__(self, interaction, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._interaction = interaction

    def should_transfer(self, continuation):
        return False

    def on_run(self):
        participant = self._interaction.get_participant(self.participant)
        participant.sim_info.household.missing_pet_tracker.run_away_succeeded(participant.sim_info)

    def release(self):
        participant = self._interaction.get_participant(self.participant)
        participant.sim_info.household.missing_pet_tracker.run_away_interaction_released(participant.sim_info)
