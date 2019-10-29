import enum
class ResetReason(enum.Int, export=False):
    NONE = ...
    RESET_EXPECTED = ...
    RESET_ON_ERROR = ...
    BEING_DESTROYED = ...

class ItemLocation(enum.Int):
    INVALID_LOCATION = 0
    ON_LOT = 1
    SIM_INVENTORY = 2
    HOUSEHOLD_INVENTORY = 3
    OBJECT_INVENTORY = 4
    FROM_WORLD_FILE = 5
    FROM_OPEN_STREET = 6
    FROM_CONDITIONAL_LAYER = 7

class PersistenceType(enum.Int):
    FULL = 0
    BUILDBUY = 1
    NONE = 2

class ObjectClaimStatus(enum.Int, export=False):
    UNCLAIMED = 0
    CLAIMED = 1
