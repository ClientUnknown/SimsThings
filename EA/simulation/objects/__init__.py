import collectionsimport copyfrom objects.visibility.visibility_enums import VisibilityFlagsfrom sims4.repr_utils import standard_reprfrom sims4.tuning.tunable import Tunable, TunableRange, TunableSingletonFactory, OptionalTunable, TunableFactory, TunableResourceKey, TunableReference, TunableSimMinute, TunableTuple, AutoFactoryInit, HasTunableSingletonFactory, TunableVariant, TunableEnumFlags, TunableListfrom singletons import DEFAULTimport enumimport servicesimport sims4.hash_utilimport sims4.logimport sims4.mathlogger = sims4.log.Logger('Objects', default_owner='pingebretson')
class HiddenReasonFlag(enum.IntFlags, export=False):
    NONE = 0
    NOT_INITIALIZED = 1
    RABBIT_HOLE = 2
    REPLACEMENT = 4
ALL_HIDDEN_REASONS = HiddenReasonFlag.NOT_INITIALIZED | HiddenReasonFlag.RABBIT_HOLE | HiddenReasonFlag.REPLACEMENTALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED = ALL_HIDDEN_REASONS & ~HiddenReasonFlag.NOT_INITIALIZED
class VisibilityState:
    __slots__ = ('visibility', 'inherits', 'enable_drop_shadow')

    def __init__(self, visibility=True, inherits=None, enable_drop_shadow=False):
        self.visibility = visibility
        self.inherits = inherits
        self.enable_drop_shadow = enable_drop_shadow

    def __repr__(self):
        return standard_repr(self, self.visibility, inherits=self.inherits, enable_drop_shadow=self.enable_drop_shadow)

class MaterialState:
    __slots__ = ('state_name_hash', 'opacity', 'transition', 'debug_state_name')

    def __init__(self, state_name, opacity=1.0, transition=0.0):
        if state_name is None:
            self.state_name_hash = 0
        else:
            self.state_name_hash = sims4.hash_util.hash32(state_name)
        self.opacity = sims4.math.clamp(0.0, opacity, 1.0)
        self.transition = transition
        self.debug_state_name = state_name

    def __repr__(self):
        return standard_repr(self, self.debug_state_name, hex(self.state_name_hash), opacity=self.opacity, transition=self.transition)

class PaintingState(collections.namedtuple('_PaintingState', ('texture_id', 'reveal_level', 'use_overlay', 'effect', 'stage_texture_id', 'overlay_texture_id', 'reveal_texture_id'))):
    REVEAL_LEVEL_MIN = 0
    REVEAL_LEVEL_MAX = 5

    @staticmethod
    def from_key(texture_key:sims4.resources.Key, *args, **kwargs):
        texture_id = texture_key.instance
        return PaintingState(texture_id, *args, **kwargs)

    @staticmethod
    def from_name(texture_name:str, *args, **kwargs):
        texture_id = sims4.hash_util.hash64(texture_name)
        return PaintingState(texture_id, *args, **kwargs)

    def __new__(cls, texture_id:int, reveal_level:int=0, use_overlay:bool=False, effect:int=sims4.math.MAX_UINT32, stage_texture_id=None, overlay_texture_id=None, reveal_texture_id=None):
        if reveal_level < cls.REVEAL_LEVEL_MIN or reveal_level > cls.REVEAL_LEVEL_MAX:
            raise ValueError('reveal_level ({}) is out of range [{} - {}].'.format(reveal_level, cls.REVEAL_LEVEL_MIN, cls.REVEAL_LEVEL_MAX))
        if not isinstance(texture_id, int):
            raise TypeError('texture_id must be an integer.')
        return super().__new__(cls, texture_id, reveal_level, use_overlay, effect, stage_texture_id, overlay_texture_id, reveal_texture_id)

    @property
    def texture_name(self):
        pass

    @property
    def is_initial(self):
        return self.reveal_level == self.REVEAL_LEVEL_MIN

    @property
    def is_final(self):
        return self.reveal_level == self.REVEAL_LEVEL_MAX

    def get_at_level(self, reveal_level):
        return self._replace(reveal_level=reveal_level)

    def get_with_effect(self, effect):
        return self._replace(effect=effect)

    def set_painting_texture_id(self, texture_id):
        return self._replace(texture_id=texture_id)

    def set_stage_texture_id(self, stage_texture_id):
        return self._replace(stage_texture_id=stage_texture_id)

    def set_overlay_texture_id(self, overlay_texture_id):
        return self._replace(overlay_texture_id=overlay_texture_id)

    def set_reveal_texture_id(self, reveal_texture_id):
        return self._replace(reveal_texture_id=reveal_texture_id)

    def __repr__(self):
        return standard_repr(self, self.texture_name or self.texture_id, self.reveal_level, self.use_overlay, self.effect)

class TunableStringOrDefault(OptionalTunable):

    def __init__(self, default, **kwargs):
        super().__init__(disabled_name='set_to_default_value', enabled_name='set_to_custom_value', tunable=Tunable(str, default), **kwargs)

class TunableVisibilityState(TunableSingletonFactory):
    FACTORY_TYPE = VisibilityState

    def __init__(self, description='A visibility state.', **kwargs):
        super().__init__(visibility=Tunable(description='\n                If True, the object may be visible. If False, the object will \n                not be visible.\n                ', tunable_type=bool, default=True), inherits=Tunable(description="\n                If True, this object can only be visible if its parent is \n                visible. If False, it may be visible regardless of its parent's \n                visibility.\n                ", tunable_type=bool, default=True), enable_drop_shadow=Tunable(description="\n                If True, this object's drop shadow may be visible.  If False, \n                this object's drop shadow will not be visible.\n                ", tunable_type=bool, default=True), description=description, **kwargs)

class TunableMaterialState(TunableSingletonFactory):
    FACTORY_TYPE = MaterialState

    def __init__(self, description='A material state.', **kwargs):
        super().__init__(state_name=TunableStringOrDefault('materialStateName', description='The name of the material state.'), opacity=TunableRange(float, 1, 0, 1, description='Opacity of the material from ( 0.0 == transparent ) to ( 1.0 == opaque ). Not yet supported on the client.'), transition=TunableSimMinute(0, description='Time to take when transitioning in sim minutes. Not yet supported on the client.'), description=description, **kwargs)

class TunableGeometryState(TunableStringOrDefault):
    DEFAULT_VALUE = 'geometryStateName'

    def __init__(self, **kwargs):
        super().__init__(self.DEFAULT_VALUE, **kwargs)

    def load_etree_node(self, **kwargs):
        value = super().load_etree_node(**kwargs)
        if value is self.DEFAULT_VALUE:
            return
        return value

class ModelSuiteStateIndex:

    def __init__(self, state_index, target=None):
        self._target = target
        self._state_index = state_index
        self._old_state_index = None

    def __call__(self, target):
        return ModelSuiteStateIndex(self._state_index, target)

    def start(self):
        if self._target is not None:
            self._old_state_index = self._target.state_index
            if self._old_state_index != self._state_index:
                self._target.set_object_def_state_index(self._state_index)

    def stop(self, *_, **__):
        if self._target is not None and self._old_state_index is not None and self._old_state_index != self._target.state_index:
            self._target.set_object_def_state_index(self._old_state_index)

class TunableModelSuiteStateIndex(Tunable):
    DEFAULT_VALUE = 0

    def __init__(self, **kwargs):
        super().__init__(int, 0, **kwargs)
        self.cache_key = '{}_{}'.format('TunableModelSuiteStateIndex', self.cache_key)

    def load_etree_node(self, **kwargs):
        value = super().load_etree_node(**kwargs)
        if value is None:
            value = 0
        return ModelSuiteStateIndex(value)

class TunableMaterialVariant(TunableStringOrDefault):
    pass
