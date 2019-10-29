import enumINVALID_TERRAIN_HEIGHT = -100.0
class TransitionFailureReasons(enum.Int, export=False):
    UNKNOWN = 0
    NO_DESTINATION_NODE = 1
    NO_PATH_FOUND = 2
    NO_VALID_INTERSECTION = 3
    NO_GOALS_GENERATED = 4
    BUILD_BUY = 5
    BLOCKING_OBJECT = 6
    RESERVATION = 7
    NO_CONNECTIVITY_TO_GOALS = 8
    PATH_PLAN_FAILED = 9
    GOAL_ON_SLOPE = 10
