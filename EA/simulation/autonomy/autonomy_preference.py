from sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import TunableTuple, TunableEnumEntry, OptionalTunable, Tunable
class ObjectPreferenceTag(DynamicEnum):
    INVALID = -1

class TunableAutonomyPreference(TunableTuple):

    def __init__(self, is_scoring, **kwargs):
        super().__init__(tag=TunableEnumEntry(description="\n                The preference tag associated with this interaction's \n                ownership settings.\n                ", tunable_type=ObjectPreferenceTag, default=ObjectPreferenceTag.INVALID, invalid_enums=(ObjectPreferenceTag.INVALID,)), should_set=OptionalTunable(description='\n                Whether or not running this interaction sets an autonomy\n                preference for the target object.\n                ', tunable=TunableTuple(autonomous=Tunable(description='\n                        Whether or not this should be set when this interaction \n                        is running autonomously.\n                        ', tunable_type=bool, default=False)), enabled_by_default=True, disabled_value=False, disabled_name='false', enabled_name='true'), locked_args={'is_scoring': is_scoring}, **kwargs)
