import copyfrom filters.tunable import TunableSimFilterfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableInterval, TunableVariantfrom story_progression.story_progression_agents import StoryProgressionAgentSimInfoimport services
class _StoryProgressionDemographic(HasTunableFactory, AutoFactoryInit):

    def get_demographic_clone(self):
        return copy.copy(self)

    def get_demographic_error(self):
        raise NotImplementedError

    def add_sim_info_agent(self, sim_info_agent):
        raise NotImplementedError

    def remove_sim_info_agent(self, sim_info_agent):
        raise NotImplementedError

class _StoryProgressionDemographicWithFilter(_StoryProgressionDemographic):
    FACTORY_TUNABLES = {'population_filter': TunableSimFilter.TunableReference(description='\n            The subset of Sims this action can operate on.\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for sim_info_agent in self._get_sims_from_filter():
            self._add_sim_info_agent_internal(sim_info_agent)

    def add_sim_info_agent(self, sim_info_agent):
        if self._is_valid_agent(sim_info_agent):
            self._add_sim_info_agent_internal(sim_info_agent)

    def _add_sim_info_agent_internal(self, sim_info_agent):
        raise NotImplementedError

    def remove_sim_info_agent(self, sim_info_agent):
        if self._is_valid_agent(sim_info_agent):
            self._remove_sim_info_agent_internal(sim_info_agent)

    def _remove_sim_info_agent_internal(self, sim_info_agent):
        raise NotImplementedError

    def _is_valid_agent(self, sim_info_agent):

        def get_sim_filter_gsi_name():
            return 'Request to check if {} matches filter from {}'.format(sim_info_agent, self)

        return services.sim_filter_service().does_sim_match_filter(sim_info_agent.sim_id, sim_filter=self.population_filter, gsi_source_fn=get_sim_filter_gsi_name)

    def get_sim_filter_gsi_name(self):
        return str(self)

    def _get_sims_from_filter(self):
        results = services.sim_filter_service().submit_filter(self.population_filter, None, allow_yielding=False, gsi_source_fn=self.get_sim_filter_gsi_name)
        return tuple(StoryProgressionAgentSimInfo(r.sim_info) for r in results)

class StoryProgressionDemographicEmployment(_StoryProgressionDemographicWithFilter):
    FACTORY_TUNABLES = {'employment_rate': TunableInterval(description='\n            The ideal employment rate. If the rate of employed Sims falls\n            outside of this interval, Sims will be hired/fired as necessary.\n            ', tunable_type=float, default_lower=0.6, default_upper=0.9, minimum=0, maximum=1)}

    def __init__(self, *args, **kwargs):
        self._workforce_count = 0
        self._employed_count = 0
        self._unemployed_count = 0
        super().__init__(*args, **kwargs)

    def get_demographic_error(self):
        employment_ratio = self._employed_count/self._workforce_count if self._workforce_count else 0
        if employment_ratio < self.employment_rate.lower_bound:
            return self.employment_rate.lower_bound - employment_ratio
        elif employment_ratio > self.employment_rate.upper_bound:
            return employment_ratio - self.employment_rate.upper_bound
        return 0

    def _add_sim_info_agent_internal(self, sim_info_agent):
        work_career = sim_info_agent.get_work_career()
        if work_career is None:
            self._unemployed_count += 1
        elif work_career.can_quit:
            self._employed_count += 1
        self._workforce_count += 1

    def _remove_sim_info_agent_internal(self, sim_info_agent):
        work_career = sim_info_agent.get_work_career()
        if work_career is None:
            self._unemployed_count -= 1
        elif work_career.can_quit:
            self._employed_count -= 1
        self._workforce_count -= 1

class TunableStoryProgressionDemographicVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, employment=StoryProgressionDemographicEmployment.TunableFactory(), default='employment', **kwargs)
