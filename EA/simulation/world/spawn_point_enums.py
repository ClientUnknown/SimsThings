from sims4.tuning.dynamic_enum import DynamicEnumimport enum
class SpawnPointPriority(DynamicEnum):
    DEFAULT = 0

class SpawnPointRequestReason(enum.Int):
    DEFAULT = 0
    SPAWN = 1
    LEAVE = 2
