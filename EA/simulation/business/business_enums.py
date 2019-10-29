from sims4.tuning.dynamic_enum import DynamicEnumimport enum
class BusinessType(enum.Int):
    INVALID = 0
    RETAIL = 1
    RESTAURANT = 2
    VET = 3

class BusinessEmployeeType(DynamicEnum):
    INVALID = 0

class BusinessCustomerStarRatingBuffBuckets(DynamicEnum):
    INVALID = 0

class BusinessAdvertisingType(DynamicEnum):
    INVALID = 0

class BusinessQualityType(DynamicEnum):
    INVALID = 0
