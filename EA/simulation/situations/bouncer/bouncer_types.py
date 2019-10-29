import enumfrom sims4.tuning.dynamic_enum import DynamicEnum
class BouncerRequestStatus(enum.Int, export=False):
    INITIALIZED = 0
    SUBMITTED = 1
    SIM_FILTER_SERVICE = 2
    SPAWN_REQUESTED = 3
    FULFILLED = 4
    DESTROYED = 5

class BouncerRequestPriority(enum.Int):
    GAME_BREAKER = 0
    EVENT_VIP = 1
    EVENT_HOSTING = 2
    VENUE_REQUIRED = 3
    EVENT_AUTO_FILL = 4
    BACKGROUND_HIGH = 5
    BACKGROUND_MEDIUM = 6
    BACKGROUND_LOW = 7
    EVENT_DEFAULT_JOB = 8
    LEAVE = 9

class RequestSpawningOption(enum.Int):
    MUST_SPAWN = 1
    CANNOT_SPAWN = 2
    DONT_CARE = 3

class BouncerExclusivityCategory(enum.IntFlags):
    LEAVE = 2
    NORMAL = 4
    WALKBY = 8
    SERVICE = 16
    VISIT = 32
    LEAVE_NOW = 64
    UNGREETED = 128
    PRE_VISIT = 256
    WORKER = 512
    NEUTRAL = 1024
    VENUE_EMPLOYEE = 2048
    VENUE_BACKGROUND = 4096
    CLUB_GATHERING = 8192
    FESTIVAL_BACKGROUND = 16384
    FESTIVAL_GOER = 32768
    WALKBY_SNATCHER = 65536
    CAREGIVER = 131072
    FIRE = 262144
    NON_WALKBY_BACKGROUND = 524288
    VENUE_GOER = 1048576
    SQUAD = 2097152
    INFECTED = 4194304
    NEUTRAL_UNPOSSESSABLE = 8388608
    NORMAL_UNPOSSESSABLE = 16777216

class BouncerExclusivityOption(enum.Int):
    NONE = 0
    EXPECTATION_PREFERENCE = 1
    ERROR = 2
    ALREADY_ASSIGNED = 3
