from sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import TunableMapping, TunableRange
class FocusScore(DynamicEnum):
    NONE = 0

class FocusTuning:
    FOCUS_SCORE_VALUES = TunableMapping(description='\n        A mapping of focus score to their numerical representation.\n        ', key_type=FocusScore, value_type=TunableRange(description='\n            The value associated with this focus score. Sims chose what to focus\n            on based on the weighted randomization of all objects they could\n            choose to focus on.\n            ', tunable_type=float, default=1, minimum=0))
