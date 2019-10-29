from sims4.tuning.dynamic_enum import DynamicEnum, DynamicEnumLockedfrom weather.weather_enums import WeatherEffectType, CloudTypeimport enum
class NarrativeGroup(DynamicEnum, partitioned=True):
    INVALID = 0

class NarrativeEvent(DynamicEnum, partitioned=True):
    INVALID = 0

class NarrativeProgressionEvent(DynamicEnumLocked, partitioned=True):
    INVALID = 0

class NarrativeSituationShiftType(DynamicEnum, partitioned=True):
    INVALID = 0

class NarrativeEnvironmentParams(enum.Int):
    StrangerVille_Act = WeatherEffectType.STRANGERVILLE_ACT
    StrangerVille_Strange_Skybox = CloudType.STRANGE
    StrangerVille_VeryStrange_Skybox = CloudType.VERY_STRANGE
