import enum
class RewardDestination(enum.Int):
    SIM = 0
    HOUSEHOLD = 1
    MAILBOX = 2

class RewardType(enum.Int, export=False):
    MONEY = 0
    OBJECT_DEFINITION = 1
    TRAIT = 2
    CAS_PART = 3
    BUILD_BUY_OBJECT = 4
    BUILD_BUY_MAGAZINE_COLLECTION = 5
    DISPLAY_TEXT = 6
    ADDITIONAL_EMPLOYEE_SLOT = 7
    ADDITIONAL_BUSINESS_CUSTOMER_COUNT = 8
    ADDITIONAL_BUSINESS_MARKUP = 9
    SET_CLUB_GATHERING_VIBE = 10
    BUCKS = 11
    BUFF = 12
    WHIM_BUCKS = 13
