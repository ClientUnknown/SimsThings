from sims4.tuning.tunable import TunableMapping, Tunable, TunableInterval, TunableReference, AutoFactoryInit, HasTunableSingletonFactory, TunableEnumEntryfrom sims4.tuning.tunable_base import SourceQueriesfrom statistics.statistic_categories import StatisticCategoryimport services
class TunableStatAsmParam(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'level_ranges': TunableMapping(description='\n            The value mapping of the stat range to stat value or user value. If\n            use_user_value is True, the range should be user value, otherwise\n            stat value.\n            ', key_type=Tunable(description="\n                The asm parameter for Sim's stat level.\n                ", tunable_type=str, default=None, source_query=SourceQueries.SwingEnumNamePattern.format('statLevel')), value_type=TunableInterval(description='\n                Stat value fall into the range (inclusive).\n                ', tunable_type=float, default_lower=1, default_upper=1)), 'asm_param_name': Tunable(description='\n            The asm param name.\n            ', tunable_type=str, default='statLevel'), 'use_user_value': Tunable(description='\n            Whether use the user value or stat value to decide the asm_param.\n            ', tunable_type=bool, default=True), 'use_effective_skill_level': Tunable(description='\n            If true, the effective skill level of the Sim will be used for \n            the asm_param.\n            ', tunable_type=bool, default=True), 'always_apply': Tunable(description='\n            If checked, this parameter is always applied on any ASM involving the\n            owning Sim.\n            ', tunable_type=bool, default=False)}

    def get_asm_param(self, stat):
        stat_value = stat.get_user_value() if self.use_user_value else stat.get_value()
        if self.use_effective_skill_level:
            stat_value = stat.tracker.owner.get_effective_skill_level(stat)
        asm_param_value = None
        for (range_key, stat_range) in self.level_ranges.items():
            if stat_value >= stat_range.lower_bound and stat_value <= stat_range.upper_bound:
                asm_param_value = range_key
                break
        return (self.asm_param_name, asm_param_value)

class CommodityDecayModifierMapping(TunableMapping):

    def __init__(self, description=''):
        (super().__init__(description=description, key_type=TunableReference(services.statistic_manager(), class_restrictions=('Commodity', 'RankedStatistic'), description='\n                    The stat the modifier will apply to.\n                    ', pack_safe=True), value_type=Tunable(float, 0, description='Multiply statistic decay by this value.')),)

    @property
    def export_class(self):
        return 'TunableMapping'

class StatisticCategoryModifierMapping(TunableMapping):

    def __init__(self, description=''):
        super().__init__(description=description, key_type=TunableEnumEntry(description='\n                The category of statistics to add the modifier to.\n                ', tunable_type=StatisticCategory, default=StatisticCategory.INVALID), value_type=Tunable(description='\n                The value to multiply by the decay of the statistic by.\n                ', tunable_type=float, default=1.0))
