from sims4.tuning.tunable import Tunablefrom statistics.skill import Skillfrom traits.sim_info_fixup_action import _SimInfoFixupAction
class _SimInfoSkillFixupAction(_SimInfoFixupAction):
    FACTORY_TUNABLES = {'skill': Skill.TunableReference(description='\n            The skill which will be assigned to the sim_info.\n            '), 'initial_level': Tunable(description='\n            The initial level at which to assign the skill.\n            ', tunable_type=int, default=1)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, sim_info):
        sim_info.commodity_tracker.set_user_value(self.skill, self.initial_level)
