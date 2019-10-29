import enumfrom singletons import SingletonTypefrom services import posture_managerfrom sims4.tuning.dynamic_enum import DynamicEnum
class AllPosturesType(SingletonType):
    pass
ALL_POSTURES = AllPosturesType()
class PostureTrack(enum.IntFlags):
    BODY = ...
    LEFT = ...
    RIGHT = ...

    @staticmethod
    def is_body(track):
        return track == PostureTrack.BODY

    @staticmethod
    def is_carry(track):
        return track == PostureTrack.RIGHT or track == PostureTrack.LEFT

class PostureTrackGroup(enum.IntFlags):
    BODY = PostureTrack.BODY
    CARRY = PostureTrack.LEFT | PostureTrack.RIGHT

class PostureEvent(enum.Int, export=False):
    TRANSITION_START = 0
    TRANSITION_FAIL = 1
    TRANSITION_COMPLETE = 2
    POSTURE_CHANGED = 3

class PostureTransitionTargetPreferenceTag(DynamicEnum):
    INVALID = -1

class DerailReason(enum.Int, export=False):
    NOT_DERAILED = 0
    TRANSITION_FAILED = 1
    DISPLACE = 2
    PREEMPTED = 3
    PROCESS_QUEUE = 4
    TARGET_RESET = 5
    NAVMESH_UPDATED = 6
    PRIVACY_ENGAGED = 7
    WAIT_FOR_BLOCKING_SIMS = 8
    CONSTRAINTS_CHANGED = 9
    NAVMESH_UPDATED_BY_BUILD = 10
    MUST_EXIT_MOBILE_POSTURE_OBJECT = 11
    WAIT_TO_BE_PUT_DOWN = 12
    WAIT_FOR_FORMATION_SLAVE = 13
    MASTER_SIM_ROUTING = 14
    WAIT_FOR_CARRY_TARGET = 15
MOVING_DERAILS = (DerailReason.CONSTRAINTS_CHANGED, DerailReason.MUST_EXIT_MOBILE_POSTURE_OBJECT, DerailReason.MASTER_SIM_ROUTING)
def create_posture(posture_type, sim, target, track=PostureTrack.BODY, **kwargs):
    if isinstance(posture_type, str):
        posture_type = posture_manager().get(posture_type)
    return posture_type(sim, target, track, **kwargs)

def are_carry_compatible(posture_tuple, carry_state) -> bool:
    from animation.posture_manifest import Hand
    allow_hands = set(posture_tuple.free_hands)
    if posture_tuple.carry_hand is not None:
        if posture_tuple.carry_hand == Hand.LEFT and not carry_state[0]:
            return False
        if posture_tuple.carry_hand == Hand.RIGHT and not carry_state[1]:
            return False
        allow_hands.add(posture_tuple.carry_hand)
    if carry_state[0] and Hand.LEFT not in allow_hands:
        return False
    elif carry_state[1] and Hand.RIGHT not in allow_hands:
        return False
    return True

def get_best_supported_posture(provided_postures, supported_postures, carry_state, allow_all=False, ignore_carry=True):
    if not (provided_postures and supported_postures):
        return
    if provided_postures is ALL_POSTURES:
        if supported_postures is ALL_POSTURES:
            if allow_all:
                return ALL_POSTURES
            raise ValueError('Both the provided and supported postures are ALL_POSTURES in get_best_supported_posture')
        compatible_postures = supported_postures
    elif supported_postures is ALL_POSTURES:
        compatible_postures = provided_postures
    else:
        compatible_postures = provided_postures.intersection(supported_postures)
    if compatible_postures:
        for entry in sorted(compatible_postures, reverse=True):
            if ignore_carry or not are_carry_compatible(entry, carry_state):
                pass
            else:
                return entry

def get_posture_types_supported_by_manifest(supported_posture_manifest):
    supported_posture_types = set()
    for posture_type in posture_manager().types.values():
        provided_posture_manifest = posture_type.get_provided_postures()
        if get_best_supported_posture(provided_posture_manifest, supported_posture_manifest, (False, False), ignore_carry=True) is not None:
            supported_posture_types.add(posture_type)
    return supported_posture_types
