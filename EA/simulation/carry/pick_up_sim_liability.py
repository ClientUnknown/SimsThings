from interactions.liability import Liability
class WaitToBePickedUpLiability(Liability):
    LIABILITY_TOKEN = 'WaitToBePickedUpLiability'

class PickUpSimLiability(Liability):
    LIABILITY_TOKEN = 'PickUpSimLiability'

    def __init__(self, original_interaction, on_finish_callback):
        super().__init__()
        self._interaction = None
        self._original_interaction = original_interaction
        self._on_finish_callback = on_finish_callback
        original_interaction.add_liability(WaitToBePickedUpLiability.LIABILITY_TOKEN, WaitToBePickedUpLiability())

    @property
    def original_interaction(self):
        return self._original_interaction

    def on_add(self, interaction):
        self._interaction = interaction

    def should_transfer(self, continuation):
        return continuation.is_putdown

    def transfer(self, interaction):
        self._interaction = interaction

    def release(self):
        if self._on_finish_callback is not None:
            self._on_finish_callback(self._interaction)
        self._original_interaction.remove_liability(WaitToBePickedUpLiability.LIABILITY_TOKEN)
