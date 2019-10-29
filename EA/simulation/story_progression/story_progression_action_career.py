import randomfrom sims4.repr_utils import standard_reprfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableVariantfrom story_progression.story_progression_action_base import StoryProgressionActionfrom story_progression.story_progression_agents import StoryProgressionAgentSimInfoimport servicesimport sims4.resources
class _CareerSubaction:

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._sim_info_agent = StoryProgressionAgentSimInfo(sim_info)

    def __repr__(self):
        return standard_repr(self)

    def save(self, data):
        raise NotImplementedError

    def execute_subaction(self):
        raise NotImplementedError

class _CareerSubactionFactory(HasTunableSingletonFactory, AutoFactoryInit):

    def load(self, data):
        raise NotImplementedError

    def get_potenial_subactions_gen(self, sim_info):
        raise NotImplementedError

class _CareerSubactionJoin(_CareerSubaction):

    def __init__(self, *args, career, **kwargs):
        super().__init__(*args, **kwargs)
        self._career = career

    def __repr__(self):
        return standard_repr(self, career=self._career.__name__)

    def save(self, data):
        data.custom_guid = self._career.guid64

    def execute_subaction(self):
        user_level = random.randint(1, self._career.get_max_user_level())
        self._sim_info.career_tracker.add_career(self._career(self._sim_info), user_level_override=user_level, give_skipped_rewards=False)

    def update_demographics(self, demographics):
        sim_info_agent = self._sim_info_agent.get_agent_clone(career=self._career)
        for demographic in demographics:
            demographic.remove_sim_info_agent(self._sim_info_agent)
            demographic.add_sim_info_agent(sim_info_agent)

class _CareerSubactionFactoryJoin(_CareerSubactionFactory):

    def load(self, sim_info, data):
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        career = career_manager.get(data.custom_guid)
        if career is None:
            raise TypeError
        return _CareerSubactionJoin(sim_info, career=career)

    def get_potenial_subactions_gen(self, sim_info):
        career_service = services.get_career_service()
        for career in career_service.get_career_list():
            if career.career_story_progression.joining is not None:
                yield _CareerSubactionJoin(sim_info, career=career)

class _CareerSubactionFactoryQuit(_CareerSubactionFactory):
    pass

class _CareerSubactionFactoryFired(_CareerSubactionFactory):
    pass

class _CareerSubactionFactoryRetire(_CareerSubactionFactory):
    pass

class _CareerSubactionFactoryPromoted(_CareerSubactionFactory):
    pass

class _CareerSubactionFactoryDemoted(_CareerSubactionFactory):
    pass

class StoryProgressionActionCareer(StoryProgressionAction):
    INSTANCE_TUNABLES = {'career_subaction': TunableVariant(description='\n            The career operation to apply for this action.\n            ', join=_CareerSubactionFactoryJoin.TunableFactory(), quit=_CareerSubactionFactoryQuit.TunableFactory(), fired=_CareerSubactionFactoryFired.TunableFactory(), retire=_CareerSubactionFactoryRetire.TunableFactory(), promoted=_CareerSubactionFactoryPromoted.TunableFactory(), demoted=_CareerSubactionFactoryDemoted.TunableFactory(), default='join')}

    def __init__(self, *args, career_subaction=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._career_subaction = career_subaction

    def __repr__(self):
        return standard_repr(self, subaction=self._career_subaction)

    def load(self, data):
        super().load(data)
        self._career_subaction = self.career_subaction.load(self._sim_info, data)

    def save(self, data):
        super().save(data)
        self._career_subaction.save(data)

    @classmethod
    def get_potential_actions_gen(cls, sim_info):
        for career_subaction in cls.career_subaction.get_potenial_subactions_gen(sim_info):
            yield cls(sim_info, career_subaction=career_subaction)

    def execute_action(self):
        return self._career_subaction.execute_subaction()

    def update_demographics(self, demographics):
        self._career_subaction.update_demographics(demographics)
