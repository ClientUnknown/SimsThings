import enum
class PeriodicStatisticBehavior(enum.Int):
    APPLY_AT_START_ONLY = ...
    RETEST_ON_INTERVAL = ...
    APPLY_AT_INTERVAL_ONLY = ...

class CommodityTrackerSimulationLevel(enum.Int, export=False):
    REGULAR_SIMULATION = ...
    LOW_LEVEL_SIMULATION = ...

class StatisticLockAction(enum.Int):
    DO_NOT_CHANGE_VALUE = 0
    USE_MIN_VALUE_TUNING = 1
    USE_MAX_VALUE_TUNING = 2
    USE_BEST_VALUE_TUNING = 3
