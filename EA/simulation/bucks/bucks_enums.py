from sims4.tuning.dynamic_enum import DynamicEnumLockedimport enum
class BucksType(DynamicEnumLocked, partitioned=True):
    INVALID = 0

class BucksTrackerType(enum.Int):
    HOUSEHOLD = 0
    CLUB = 1
    SIM = 2
