from sims4.tuning.tunable import TunableEnumEntryfrom tag import Tagimport enum
class GameObjectProperty(enum.Int):
    CATALOG_PRICE = 0
    MODIFIED_PRICE = 1
    RARITY = 2
    GENRE = 3
    FISH_FRESHNESS = 4
    RECIPE_NAME = 5
    RECIPE_DESCRIPTION = 6
    OBJ_TYPE_REL_ID = 7

class GameObjectTuning:
    WALL_OBJ_LOS_TUNING_FLAG = TunableEnumEntry(description='\n        Tag that lets us know if this wall object needs a LOS test. \n        Currently it only works on wall grounded objects, but we can add y \n        position test later down the road. \n        ', tunable_type=Tag, default=Tag.INVALID)
