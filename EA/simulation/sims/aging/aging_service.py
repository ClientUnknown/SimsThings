from protocolbuffers import GameplaySaveData_pb2from sims.aging.aging_tuning import AgeSpeeds, AgingTuningfrom sims.sim_info_lod import SimInfoLODLevelfrom sims4.service_manager import Serviceimport enumimport game_servicesimport servicesgame_play_options_enums = GameplaySaveData_pb2.GameplayOptions
class PlayedHouseholdSimAgingOptions(enum.Int, export=False):
    DISABLED = ...
    ALL_PLAYED = ...
    ACTIVE_FAMILY_ONLY = ...

    @classmethod
    def convert_protocol_option_to_aging_option(cls, option_allow_aging):
        if option_allow_aging == game_play_options_enums.DISABLED:
            return cls.DISABLED
        if option_allow_aging == game_play_options_enums.ENABLED:
            return cls.ALL_PLAYED
        elif option_allow_aging == game_play_options_enums.FOR_ACTIVE_FAMILY:
            return cls.ACTIVE_FAMILY_ONLY

    @classmethod
    def convert_aging_option_to_protocol_option(cls, aging_option):
        if aging_option == cls.DISABLED:
            return game_play_options_enums.DISABLED
        if aging_option == cls.ALL_PLAYED:
            return game_play_options_enums.ENABLED
        elif aging_option == cls.ACTIVE_FAMILY_ONLY:
            return game_play_options_enums.FOR_ACTIVE_FAMILY

class AgingService(Service):

    def __init__(self):
        self._aging_speed = AgeSpeeds.NORMAL
        self._played_household_aging_option = PlayedHouseholdSimAgingOptions.ACTIVE_FAMILY_ONLY
        self._unplayed_aging_enabled = False

    @property
    def aging_speed(self):
        return self._aging_speed

    def set_unplayed_aging_enabled(self, enabled_option):
        self._unplayed_aging_enabled = enabled_option
        services.sim_info_manager().set_aging_enabled_on_all_sims(self.is_aging_enabled_for_sim_info)

    def set_aging_enabled(self, enabled_option):
        self._played_household_aging_option = PlayedHouseholdSimAgingOptions(enabled_option)
        services.sim_info_manager().set_aging_enabled_on_all_sims(self.is_aging_enabled_for_sim_info)

    def is_aging_enabled_for_sim_info(self, sim_info):
        if sim_info.household is None:
            return False
        if sim_info.lod == SimInfoLODLevel.MINIMUM:
            return False
        if not sim_info.is_played_sim:
            return self._unplayed_aging_enabled
        if self._played_household_aging_option == PlayedHouseholdSimAgingOptions.ACTIVE_FAMILY_ONLY:
            return not sim_info.is_npc
        return self._played_household_aging_option == PlayedHouseholdSimAgingOptions.ALL_PLAYED

    def set_aging_speed(self, speed:int):
        self._aging_speed = AgeSpeeds(speed)
        services.sim_info_manager().set_aging_speed_on_all_sims(self._aging_speed)

    def get_speed_multiple(self, age_speed:AgeSpeeds) -> float:
        return AgingTuning.AGE_SPEED_SETTING_MULTIPLIER.get(age_speed, 0)

    def save_options(self, options_proto):
        options_proto.sim_life_span = self._aging_speed
        options_proto.allow_aging = PlayedHouseholdSimAgingOptions.convert_aging_option_to_protocol_option(self._played_household_aging_option)
        options_proto.unplayed_aging_enabled = self._unplayed_aging_enabled

    def load_options(self, options_proto):
        if game_services.service_manager.is_traveling:
            return
        self._aging_speed = AgeSpeeds(options_proto.sim_life_span)
        self._played_household_aging_option = PlayedHouseholdSimAgingOptions.convert_protocol_option_to_aging_option(options_proto.allow_aging)
        self._unplayed_aging_enabled = options_proto.unplayed_aging_enabled
        services.sim_info_manager().set_aging_enabled_on_all_sims(self.is_aging_enabled_for_sim_info, update_callbacks=False)
        services.sim_info_manager().set_aging_speed_on_all_sims(self._aging_speed)
