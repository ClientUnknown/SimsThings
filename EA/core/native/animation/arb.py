from _animation import TRACK_NORMALfrom _math import Transformfrom collections import namedtupleimport _mathimport api_configimport enum_get_next_tag_id = None_get_current_tag_set = None
def set_tag_functions(get_id, get_set):
    global _get_next_tag_id, _get_current_tag_set
    _get_next_tag_id = get_id
    _get_current_tag_set = get_set

class BlockOnAnimationTag:
    __slots__ = ['tag']

    def __init__(self):
        self.tag = _get_next_tag_id()

    def __enter__(self):
        _get_current_tag_set().add(self.tag)
        return self.tag

    def __exit__(self, exc_type, exc_val, exc_tb):
        _get_current_tag_set().remove(self.tag)
        return False

def params_repr(params):
    l = []
    for (key, value) in params.items():
        if isinstance(key, tuple):
            key = key[1] + ':' + key[0]
        l.append('{}={}'.format(key, value))
    l.sort()
    l = ', '.join(l)
    l = '[' + l + ']'
    return l

class ClipEventType(enum.Int, export=False):
    Invalid = 0
    Parent = 1
    Unparent = 2
    Sound = 3
    Script = 4
    Effect = 5
    Visibility = 6
    FootPlant = 7
    CreateProp = 8
    DestroyProp = 9
    StopEffect = 10
    BlockTransition = 11
    Snap = 12
    Reaction = 13
    DoubleModifierSound = 14
    DspInterval = 15
    MaterialState = 16
    GeometryState = 17
    FocusCompatability = 18
    SuppressLipSync = 19
    Censor = 20
    ServerSoundStart = 21
    ServerSoundStop = 22
    EnableFacialOverlay = 23
    FadeObject = 24
    AdvanceFlipBook = 3433208315
    TimelineScript = 3466999690
    ClientLocationCapture = 4151022839
    ClientLocationRestore = 271806351

def event_types_match(a, b):
    if a == b:
        return True
    elif (a == ClipEventType.Script or a == ClipEventType.TimelineScript) and (b == ClipEventType.Script or b == ClipEventType.TimelineScript):
        return True
    return False

class ArbEventData:
    __slots__ = ['event_type', 'event_id', 'event_data', 'actors']
    _no_actors = ()

    def __init__(self, event_type, event_id, event_data, actors=None):
        self.event_type = event_type
        self.event_id = event_id
        self.event_data = event_data
        self.actors = actors or self._no_actors

class _ArbEventHandler:
    __slots__ = ['callback', 'event_type', 'event_id']

    def __init__(self, callback, event_type, event_id):
        self.callback = callback
        self.event_type = event_type
        self.event_id = event_id
try:
    from _animation import ArbBase, EVENT_TIME_FROM_END, EVENT_TIME_FROM_START
    from _animation import CENSOREVENT_STATE_OFF, CENSOREVENT_STATE_TORSO, CENSOREVENT_STATE_TORSOPELVIS, CENSOREVENT_STATE_PELVIS, CENSOREVENT_STATE_FULLBODY, CENSOREVENT_STATE_RHAND, CENSOREVENT_STATE_LHAND, CENSOREVENT_STATE_TODDLERPELVIS
except:
    CENSOREVENT_STATE_OFF = 0
    CENSOREVENT_STATE_TORSO = 1
    CENSOREVENT_STATE_TORSOPELVIS = 2
    CENSOREVENT_STATE_PELVIS = 3
    CENSOREVENT_STATE_FULLBODY = 4
    CENSOREVENT_STATE_RHAND = 5
    CENSOREVENT_STATE_LHAND = 6
    CENSOREVENT_STATE_TODDLERPELVIS = 7

    class ArbBase:

        def schedule(self, actor_id, controller, priority=10000, blend_in=-1.0, blend_out=-1.0):
            pass

        def _actors(self):
            return []

        def _events(self):
            return []

        def _get_boundary_conditions(self, actor_id):
            pass

        def _begin_synchronized_group(self):
            pass

        def _end_synchronized_group(self):
            pass

        def get_estimated_duration(self):
            return 1.0

        def _get_timing(self):
            return (1.0, 1.0, 0.0)

        def is_valid(self):
            return True

        def _add_custom_event(self, actor_id, base_time, time_in_secs, event_id, allow_create_stub=False):
            return True

        def _ends_in_looping_content(self, actor_id, min_track_id):
            return False

class _ArbSyncGroup:

    def __init__(self, arb):
        self.arb = arb

    def __enter__(self):
        if self.arb._in_sync_group:
            raise NotImplementedError('Starting a sync-group within another sync-group.  Nesting is not supported.')
        self.arb._begin_synchronized_group()
        self.arb._in_sync_group = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.arb._in_sync_group:
            raise RuntimeError('Ending a sync-group while not within a sync-group.')
        self.arb._end_synchronized_group()
        self.arb._in_sync_group = False
        return False

class _EventHandlerRecord(namedtuple('__EventHandlerRecord', ('clip_name', 'event_type', 'event_id', 'callbacks', 'event_data', 'tag', 'errors'))):
    __slots__ = ()
RequiredSlot = namedtuple('RequiredSlot', ('actor_id', 'target_id', 'joint_hash'))
class BoundaryConditionInfo(namedtuple('_BoundaryConditionInfo', ('asm_name', 'params', 'actor_name', 'from_state', 'to_state'))):

    def __str__(self):
        params = params_repr(self.params)
        return '{0.asm_name}: actor {0.actor_name} from {0.from_state} to {0.to_state} with parameters {1}'.format(self, params)
api_config.register_native_support('native.animation.arb.BoundaryConditionInfo')
class BoundaryCondition:
    __slots__ = ('pre_condition_transform', 'post_condition_transform', 'pre_condition_reference_object_id', 'post_condition_reference_object_id', 'pre_condition_reference_joint_name_hash', 'post_condition_reference_joint_name_hash', 'required_slots', 'debug_info')

    def __init__(self, pre_condition_reference_object_id, pre_condition_transform, pre_condition_reference_joint_name_hash, post_condition_reference_object_id, post_condition_transform, post_condition_reference_joint_name_hash, required_slots):
        self.pre_condition_reference_object_id = pre_condition_reference_object_id
        self.pre_condition_transform = pre_condition_transform
        self.post_condition_reference_object_id = post_condition_reference_object_id
        self.post_condition_transform = post_condition_transform
        self.pre_condition_reference_joint_name_hash = pre_condition_reference_joint_name_hash
        self.post_condition_reference_joint_name_hash = post_condition_reference_joint_name_hash
        self.required_slots = required_slots
        self.debug_info = None

    def __repr__(self):
        pre_condition_reference_object_id = 'None'
        post_condition_reference_object_id = 'None'
        if self.pre_condition_reference_object_id is not None:
            pre_condition_reference_object_id = '0x{:x}'.format(self.pre_condition_reference_object_id)
        if self.post_condition_reference_object_id is not None:
            post_condition_reference_object_id = '0x{:x}'.format(self.post_condition_reference_object_id)
        return '<BoundaryCondition {} {} {} {}>'.format(pre_condition_reference_object_id, self.pre_condition_transform if self.pre_condition_transform is not None else 'Indeterminate', post_condition_reference_object_id, self.post_condition_transform if self.post_condition_transform is not None else 'Indeterminate')

class NativeArb(ArbBase):

    def __init__(self):
        self._in_sync_group = False
        self._handlers = []
        self.unhandled_event_records = []

    def get_boundary_conditions(self, actor):
        boundaries = self._get_boundary_conditions(actor.id)
        if not boundaries:
            return
        (pre_condition_reference_object_id, pre_condition_reference_joing_name_hash, pre_condition_surface_object_id, pre_condition_surface_joint_name_hash, pre_condition_surface_child_id, pre_condition_transform, post_condition_reference_object_id, post_condition_reference_joint_name_hash, post_condition_transform) = boundaries
        if pre_condition_surface_object_id == 0 or pre_condition_surface_child_id == 0:
            required_slots = ()
        else:
            required_slots = ((pre_condition_surface_child_id, pre_condition_surface_object_id, pre_condition_surface_joint_name_hash),)
        return BoundaryCondition(pre_condition_reference_object_id, pre_condition_transform, pre_condition_reference_joing_name_hash, post_condition_reference_object_id, post_condition_transform, post_condition_reference_joint_name_hash, required_slots)

    def add_custom_event(self, actor_id, time_in_secs, event_id):
        if time_in_secs >= 0:
            base_time = EVENT_TIME_FROM_START
        else:
            base_time = EVENT_TIME_FROM_END
        return self._add_custom_event(actor_id, base_time, abs(time_in_secs), event_id, False)

    def ends_in_looping_content(self, actor_id, min_track_id=TRACK_NORMAL):
        return self._ends_in_looping_content(actor_id, min_track_id)

    def synchronized(self):
        return _ArbSyncGroup(self)

    def register_event_handler(self, handler_method, handler_type=None, handler_id=None):
        self._handlers.append(_ArbEventHandler(handler_method, handler_type, handler_id))

    def handle_events(self, events=None, event_context=None):
        if events is None:
            events = self._events()
        event_records = []
        actors = self._actors()
        events = tuple(sorted(events, key=lambda e: e[0] != ClipEventType.ClientLocationCapture))
        handlers_to_delete = []
        for (event_type, event_id, event_data) in events:
            applicable_handlers = [handler for handler in self._handlers if (handler.event_type is None or event_types_match(handler.event_type, event_type)) and (handler.event_id == event_id or handler.event_id is None)]
            if applicable_handlers:
                with BlockOnAnimationTag() as tag:
                    errors = []
                    clip_name = event_data.get('clip_name', 'unknown clip')
                    callback_strings = [str(handler.callback) for handler in applicable_handlers]
                    event_records.append(_EventHandlerRecord(clip_name, event_type, event_id, callback_strings, event_data, tag, errors))
                    data = ArbEventData(event_type, event_id, event_data, actors)
                    for handler in applicable_handlers:
                        result = 'Exception raised.'
                        if event_context is not None:
                            with event_context:
                                result = handler.callback(data)
                        else:
                            result = handler.callback(data)
                        handlers_to_delete.append(handler)
                        if not isinstance(result, str):
                            if not result:
                                errors.append(result)
                        errors.append(result)
        for handler in handlers_to_delete:
            if handler in self._handlers:
                self._handlers.remove(handler)
        return event_records

    def get_timing(self):
        return self._get_timing()

    def append(self, arb, safe_mode=True, force_sync=False):
        if self._append(arb, safe_mode=safe_mode, force_sync=force_sync):
            self._handlers.extend(arb._handlers)
            return True
        return False
