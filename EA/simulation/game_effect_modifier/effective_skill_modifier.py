from game_effect_modifier.base_game_effect_modifier import BaseGameEffectModifierfrom game_effect_modifier.game_effect_type import GameEffectTypefrom sims4.tuning.tunable import HasTunableSingletonFactory, TunableVariant, TunableEnumEntry, Tunablefrom statistics.skill import Skillimport tag
class EffectiveSkillModifier(HasTunableSingletonFactory, BaseGameEffectModifier):
    FACTORY_TUNABLES = {'description': '\n        The modifier to change the effective skill or skill_tag tuned in the\n        modifier key The value of the modifier can be negative..\n        ', 'modifier_key': TunableVariant(description='\n            ', skill_type=Skill.TunableReference(description='\n                            What skill to apply the modifier on.', pack_safe=True), skill_tag=TunableEnumEntry(description='\n                            What skill tag to apply the modifier on.', tunable_type=tag.Tag, default=tag.Tag.INVALID)), 'modifier_value': Tunable(description='\n            The value to change the effective skill. Can be negative.', tunable_type=int, default=0)}

    def __init__(self, modifier_key, modifier_value, **kwargs):
        super().__init__(GameEffectType.EFFECTIVE_SKILL_MODIFIER)
        self.modifier_key = modifier_key
        self.modifier_value = modifier_value

    def can_modify(self, skill):
        if self.modifier_key is skill.skill_type:
            return True
        return self.modifier_key in skill.tags

    def get_modifier_value(self, skill):
        if self.can_modify(skill):
            return self.modifier_value
        return 0
