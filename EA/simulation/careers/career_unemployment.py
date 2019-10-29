from careers.career_mixins import CareerKnowledgeMixinfrom sims4.tuning.tunable import TunableReferenceimport servicesimport sims4.resources
class CareerUnemployment(CareerKnowledgeMixin):
    CAREER_TRACK_UNEMPLOYED = TunableReference(description='\n        A career track for unemployed Sims.\n        ', manager=services.get_instance_manager(sims4.resources.Types.CAREER_TRACK))
    CAREER_TRACK_STAY_AT_HOME = TunableReference(description="\n        A career track for Sims that don't have a job but stay at home to take\n        care of children.\n        ", manager=services.get_instance_manager(sims4.resources.Types.CAREER_TRACK))

    def __init__(self, sim_info):
        self._sim_info = sim_info

    @property
    def current_track_tuning(self):
        if self._sim_info.household is None:
            return self.CAREER_TRACK_UNEMPLOYED
        if any(household_sim.is_teen_or_younger and self._sim_info.sim_id in household_sim.genealogy.get_parent_sim_ids_gen() for household_sim in self._sim_info.household):
            return self.CAREER_TRACK_STAY_AT_HOME
        return self.CAREER_TRACK_UNEMPLOYED

    @classmethod
    def get_career_text_tokens(cls):
        return (None, None, None)
