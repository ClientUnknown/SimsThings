from sims.aging.aging_data import AgingDatafrom sims.sim_info_types import Speciesfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, Tunable, TunableSimMinutefrom sims4.tuning.tunable_base import EnumBinaryExportTypeimport enum
class AgeSpeeds(enum.Int):
    FAST = 0
    NORMAL = 1
    SLOW = 2

class AgingTuning:
    AGING_DATA = TunableMapping(description='\n        On a per-species level, define all age-related data.\n        ', key_type=TunableEnumEntry(description='\n            The species this aging data applies to.\n            ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,), binary_type=EnumBinaryExportType.EnumUint32), value_type=AgingData.TunableFactory(), tuple_name='AgingDataMapping')
    AGING_SAVE_LOCK_TOOLTIP = TunableLocalizedStringFactory(description='\n        The tooltip to show in situations where save-lock during Age Up is\n        necessary, i.e. when babies or non-NPC Sims age up.\n        \n        This tooltip is provided one token: the Sim that is aging up.\n        ')
    AGE_SPEED_SETTING_MULTIPLIER = TunableMapping(description='\n        A mapping between age speeds and the multiplier that those speeds\n        correspond to.\n        ', key_type=TunableEnumEntry(description='\n            The age speed that will be mapped to its multiplier.\n            ', tunable_type=AgeSpeeds, default=AgeSpeeds.NORMAL), value_type=Tunable(description="\n            The multiplier by which to adjust the lifespan based on user age\n            speed settings. Setting this to 2 for 'Slow' speed will double the\n            Sim's age play time in that setting.\n            ", tunable_type=float, default=1))
    AGE_PROGRESS_UPDATE_TIME = Tunable(description='\n        The update rate, in Sim Days, of age progression in the UI.\n        ', tunable_type=float, default=0.2)
    AGE_SUPPRESSION_ALARM_TIME = TunableSimMinute(description='\n        Amount of time in sim seconds to suppress aging.\n        ', default=5, minimum=1)

    @classmethod
    def get_aging_data(cls, species):
        return cls.AGING_DATA[species]
