import enum
class InteractionQueuePreparationStatus(enum.Int, export=False):
    FAILURE = 0
    SUCCESS = 1
    NEEDS_DERAIL = 2
    PUSHED_REPLACEMENT = 3
