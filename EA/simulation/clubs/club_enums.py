from sims4.tuning.dynamic_enum import DynamicEnumimport enum
class ClubRuleEncouragementStatus(enum.Int):
    ENCOURAGED = 0
    DISCOURAGED = 1
    NO_EFFECT = 2

class ClubHangoutSetting(enum.Int, export=False):
    HANGOUT_NONE = 0
    HANGOUT_VENUE = 1
    HANGOUT_LOT = 2

class ClubGatheringKeys:
    ASSOCIATED_CLUB_ID = 'associated_club_id'
    DISBAND_TICKS = 'disband_ticks'
    GATHERING_BUFF = 'gathering_buff'
    GATHERING_VIBE = 'gathering_vibe'
    START_SOURCE = 'start_source'
    HOUSEHOLD_ID_OVERRIDE = 'household_id_override'

class ClubGatheringStartSource(enum.Int, export=False):
    DEFAULT = 0
    APPLY_FOR_INVITE = 1

class ClubOutfitSetting(enum.Int):
    NO_OUTFIT = 0
    STYLE = 1
    COLOR = 2
    OVERRIDE = 3

class ClubGatheringVibe(DynamicEnum):
    NO_VIBE = 0
