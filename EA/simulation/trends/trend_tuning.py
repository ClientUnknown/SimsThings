from sims4.localization import TunableLocalizedStringfrom sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import TunableTuple, TunableEnumEntry, TunableList, TunableMapping, TunableReferencefrom tag import TunableTagfrom tunable_time import TunableTimeSpanimport services
class TrendType(DynamicEnum):
    INVALID = 0

class TrendTuning:
    TREND_DATA = TunableList(description='\n        A list of data about trends.\n        ', tunable=TunableTuple(description='\n            The data about this trend.\n            ', trend_tag=TunableTag(description='\n                The tag for this trend.\n                ', filter_prefixes=('func_trend',)), trend_type=TunableEnumEntry(description='\n                The type of this trend.\n                ', tunable_type=TrendType, default=TrendType.INVALID, invalid_enums=(TrendType.INVALID,)), trend_name=TunableLocalizedString(description='\n                The name for this trend. This will show up in a bulleted\n                list when a player researches current trends.\n                ')))
    TREND_REFRESH_COOLDOWN = TunableTimeSpan(description='\n        The amount of time it takes before trends refresh.\n        ', default_days=2)
    TREND_TIME_REMAINING_DESCRIPTION = TunableMapping(description='\n        A mapping of thresholds, in Sim Hours, to descriptions used when\n        describing the amount of time remaining in the study trends\n        notification.\n        ', key_name='sim_hours', key_type=int, value_name='description_string', value_type=TunableLocalizedString())
    TODDLER_CHILD_TREND = TunableTag(description='\n        The tag we use to indicate Toddler or Child trends.\n        ', filter_prefixes=('func_trend',))
    CELEBRITY_TREND = TunableTag(description='\n        The tag we use to indicate Celebrity Trends.\n        ', filter_prefixes=('func_trend',))
    TRENDLESS_VIDEO_DEFINITION = TunableReference(description='\n        The object definition to use if a Sim records a trendless video.\n        ', manager=services.definition_manager(), pack_safe=True)
