from sims4.tuning.dynamic_enum import DynamicEnumimport enum
class AwarenessChannel(DynamicEnum, dynamic_max_length=10, dynamic_offset=1000):
    PROXIMITY = 0
    AUDIO_VOLUME = 1

    def get_type_name(self):
        return str(self).split('.')[-1].lower()

class AwarenessChannelEvaluationType(enum.Int):
    PEAK = 0
    AVERAGE = 1
    SUM = 2
