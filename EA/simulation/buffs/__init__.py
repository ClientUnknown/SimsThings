import enum
class BuffPolarity(enum.Int):
    NEUTRAL = 0
    NEGATIVE = 1
    POSITIVE = 2

class Appropriateness(enum.Int, export=False):
    DONT_CARE = (0,)
    NOT_ALLOWED = (1,)
    ALLOWED = (2,)
