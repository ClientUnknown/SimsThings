import enum
class SeasonType(enum.Int):
    SUMMER = 0
    FALL = 1
    WINTER = 2
    SPRING = 3

class SeasonLength(enum.Int):
    NORMAL = 0
    LONG = 1
    VERY_LONG = 2

class SeasonSegment(enum.Int):
    EARLY = 0
    MID = 1
    LATE = 2

class SeasonParameters(enum.Int):
    LEAF_ACCUMULATION = 1
    FLOWER_GROWTH = 2
    FOLIAGE_REDUCTION = 3
    FOLIAGE_COLORSHIFT = 4

class SeasonSetSource(enum.Int, export=False):
    PROGRESSION = ...
    CHEAT = ...
    LOOT = ...
