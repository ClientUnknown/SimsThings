import enum
class GlobalPolicyProgressEnum(enum.Int):
    NOT_STARTED = 0
    IN_PROGRESS = 1
    COMPLETE = 2

class GlobalPolicyTokenType(enum.Int):
    NAME = 0
    PROGRESS = 1
