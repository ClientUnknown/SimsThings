from interactions.liability import Liability
class AdoptionLiability(Liability):
    LIABILITY_TOKEN = 'AdoptionLiability'

    def __init__(self, household, sim_ids, **kwargs):
        super().__init__(**kwargs)
        self._household = household
        self._sim_ids = sim_ids

    def on_add(self, interaction):
        for sim_id in self._sim_ids:
            self._household.add_adopting_sim(sim_id)

    def release(self):
        for sim_id in self._sim_ids:
            self._household.remove_adopting_sim(sim_id)
