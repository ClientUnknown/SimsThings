from interactions.liability import Liability
class AutonomousGetComfortableLiability(Liability):
    LIABILITY_TOKEN = 'AutonomousGetComfortable'

    def __init__(self, sim, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim = sim

    def release(self):
        self._sim.push_get_comfortable_interaction()
