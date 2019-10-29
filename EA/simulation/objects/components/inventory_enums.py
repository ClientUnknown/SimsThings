from sims4.tuning.dynamic_enum import DynamicEnumLocked, DynamicEnumimport enumimport sims4.loglogger = sims4.log.Logger('Inventory Enums')
class InventoryType(DynamicEnumLocked):
    UNDEFINED = 0
    SIM = 1
    HIDDEN = 2
    FISHBOWL = 3
    MAILBOX = 4
    FRIDGE = 5
    BOOKSHELF = 6
    TOYBOX = 7
    COMPUTER = 8
    TRASHCAN = 9
    SINK = 10
    COLLECTION_ELEMENT_SHELVE = 11
    RETAIL_FRIDGE = 12
    RETAIL_SHELF = 13
    BAKING_WARMINGRACK = 14
    AQUARIUM_STANDARD = 15
    STORAGE_CHEST = 16
    COLLECTION_SKULL_DISPLAY = 17
    CRAFT_SALES_TABLE_EP03 = 18
    CRAFT_SALES_TABLE_PAINTINGS_EP03 = 19
    SACK_GP05 = 20
    HIDINGSPOT_GP05 = 21
    PET_TOYBOX = 22
    AUTOPETFEEDER = 23
    MEDICINESTATION = 24
    VET_MEDICINE_VENDING_MACHINE = 25
    LAUNDRY_STORAGE = 26

class StackScheme(DynamicEnum):
    NONE = ...
    VARIANT_GROUP = ...
    DEFINITION = ...

class ObjectShareability(enum.Int):
    NOT_SHARED = ...
    SHARED_IF_NOT_IN_APARTMENT = ...
    SHARED = ...

class InventoryItemClaimStatus(enum.Int, export=False):
    UNCLAIMED = 0
    CLAIMED = 1
