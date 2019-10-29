from sims4.tuning.dynamic_enum import DynamicEnumimport enum
class TeleportStyle(DynamicEnum, partitioned=True):
    NONE = 0

class TeleportStyleSource(enum.Int, export=False):
    TUNED_LIABILITY = 0
    TELEPORT_STYLE_SUPER_INTERACTION = 1
