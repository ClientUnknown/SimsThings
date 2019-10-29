from interactions import ParticipantTypefrom interactions.liability import Liabilityfrom sims4.tuning.tunable import HasTunableFactory
class CraftingStationLiability(Liability, HasTunableFactory):
    LIABILITY_TOKEN = 'CraftingStation'

    def __init__(self, interaction, **kwargs):
        super().__init__(**kwargs)
        self._obj = interaction.get_participant(ParticipantType.Object)
        self._removed_from_cache = False

    def on_run(self):
        if self._removed_from_cache:
            return
        if self._obj is None:
            return
        self._obj.remove_from_crafting_cache()
        self._removed_from_cache = True

    def release(self):
        if not self._removed_from_cache:
            return
        if self._obj is None:
            return
        self._obj.add_to_crafting_cache()
