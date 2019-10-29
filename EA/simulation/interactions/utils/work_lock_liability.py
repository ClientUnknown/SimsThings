from interactions.liability import Liability
class WorkLockLiability(Liability):
    LIABILITY_TOKEN = 'MasterControllerLockLiability'

    def __init__(self, *args, sim, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim = sim

    def on_add(self, interaction):
        self._sim.add_work_lock(self)

    def merge(self, interaction, key, new_liability):
        self.release()
        return super().merge(interaction, key, new_liability)

    def release(self):
        self._sim.remove_work_lock(self)
