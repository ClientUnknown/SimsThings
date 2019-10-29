from careers.career_enums import CareerCategoryfrom singletons import DEFAULT
class StoryProgressionAgentSimInfo:

    def __init__(self, sim_info, career=DEFAULT):
        self._sim_info = sim_info
        self._career = career

    @property
    def sim_id(self):
        return self._sim_info.sim_id

    def get_agent_clone(self, **kwargs):
        return StoryProgressionAgentSimInfo(self._sim_info, **kwargs)

    def get_work_career(self):
        if self._career is not DEFAULT:
            return self._career
        return self._sim_info.career_tracker.get_career_by_category(CareerCategory.Work)
