import enumfrom sims4.tuning.dynamic_enum import DynamicEnum
class WalkStyleRunAllowedFlags(enum.IntFlags):
    RUN_ALLOWED_INDOORS = 1
    RUN_ALLOWED_OUTDOORS = 2

class WalkstyleBehaviorOverridePriority(DynamicEnum):
    DEFAULT = 0

class WalkStylePriority(DynamicEnum):
    INVALID = 0
    COMBO = 1
