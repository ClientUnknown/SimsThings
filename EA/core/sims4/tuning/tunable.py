from _sims4_collections import frozendictfrom re import templateimport collectionsimport inspectimport randomimport typesfrom sims4.repr_utils import standard_reprfrom sims4.tuning.instances import TunedInstanceMetaclassfrom sims4.tuning.merged_tuning_manager import MergedTuningAttr, get_manager, UnavailablePackSafeResourceErrorfrom sims4.tuning.tunable_base import Attributes, TunableBase, tunable_type_mapping, TunableTypeNotSupportedError, BoolWrapper, Tags, RESERVED_KWARGS, get_default_display_name, MalformedTuningSchemaError, LoadingTags, LoadingAttributesfrom sims4.tuning.tunable_errors import TunableMinimumLengthErrorfrom sims4.utils import classpropertyfrom singletons import EMPTY_SET, UNSET, DEFAULTimport enumimport pathsimport sims4.colorimport sims4.logimport sims4.mathimport sims4.resourcesimport sims4.tuning.instance_managerimport sims4.tuning.instanceslogger = sims4.log.Logger('Tuning', default_owner='cjiang')with sims4.reload.protected(globals()):
    _locked_args_singletons = {}class_scan_cache = {}
def clear_class_scan_cache():
    global class_scan_cache
    class_scan_cache = {}

class _TunableHasPackSafeMixin:
    __slots__ = ()

    def __init__(self, *args, pack_safe=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.pack_safe = pack_safe

    def export_desc(self, *args, **kwargs):
        export_dict = super().export_desc(*args, **kwargs)
        if self.pack_safe:
            export_dict[Attributes.PackSafe] = True
        return export_dict

class Tunable(TunableBase):
    __slots__ = ('_type', '_default', '_raw_default', '_source_location', '_source_query', '_source_sub_query', '_convert_defined_values')

    def __init__(self, tunable_type, default, *, source_location=None, source_query=None, source_sub_query=None, convert_defined_values=True, needs_tuning=DEFAULT, allow_empty=False, **kwargs):
        self._type = tunable_type_mapping.get(tunable_type)
        if needs_tuning is DEFAULT:
            needs_tuning = self._type is int or self._type is float
        super().__init__(needs_tuning=needs_tuning, **kwargs)
        self.cache_key = (self._type, default)
        if self._type is None:
            if isinstance(tunable_type, enum.Metaclass):
                self._type = tunable_type
            else:
                raise TunableTypeNotSupportedError(tunable_type)
        self._convert_defined_values = convert_defined_values
        self._raw_default = default
        try:
            if self._convert_defined_values:
                self._default = self._convert_to_value(default)
            else:
                self._default = self._type(default) if default is not None else None
                self._raw_default = self._convert_from_value(default)
        except:
            logger.error('Unable to convert default {}', default)
        self._source_location = '../' + source_location if source_location else None
        self._source_query = source_query
        self._source_sub_query = source_sub_query

    def __repr__(self):
        classname = type(self).__name__
        if hasattr(self, '_type'):
            typename = self._type.__name__
            if len(typename) > 1:
                typename = '{}{}'.format(typename[0].capitalize(), typename[1:])
            typename = typename.replace('Wrapper', '')
            classname = '{}{}'.format(classname, typename)
        name = getattr(self, 'name', None)
        r = '<{}'.format(classname)
        sep = ': '
        if type(self) is Tunable and name:
            r = '{}{}{}'.format(r, sep, name)
            sep = '='
        r = '{}>'.format(r)
        return r

    def get_exported_type_name(self):
        if hasattr(self._type, 'EXPORT_STRING'):
            return self._type.EXPORT_STRING
        return self._type.__name__

    def export_desc(self):
        export_dict = super().export_desc()
        export_dict[Attributes.Type] = self.get_exported_type_name()
        export_dict[Attributes.Default] = self._export_default(self._raw_default)
        if self._source_location is not None:
            export_dict[Attributes.SourceLocation] = self._source_location
        export_dict[Attributes.SourceQuery] = self._source_query
        if self._source_sub_query is not None:
            export_dict[Attributes.SourceSubQuery] = self._source_sub_query
        if self._source_query is not None and self._allow_empty:
            if self._type is str:
                export_dict[Attributes.AllowNone] = self._allow_empty
            else:
                logger.error('allow_empty is only allowed for tunable strings.')
        return export_dict

    def load_etree_node(self, node=None, source=None, expect_error=False):
        if node is None:
            return self.default
        if node.text is None:
            if self.default is None and self._type in (int, float, BoolWrapper):
                name = node.get(LoadingAttributes.Name, '<UNKNOWN ITEM>')
                logger.error('{}.{}: {} is loading a value of None.', source, name, self._type)
            return self.default
        try:
            content = node.text
            if not expect_error:
                value = self._convert_to_value(content)
            else:
                value = self._convert_to_value(content)
        except (ValueError, TypeError, KeyError):
            if getattr(self, 'pack_safe', False):
                raise UnavailablePackSafeResourceError
            name = node.get(LoadingAttributes.Name, '<UNKNOWN ITEM>')
            logger_with_no_owner = sims4.log.Logger('Tuning')
            logger_with_no_owner.error('Error while parsing tuning in {0}', source)
            logger_with_no_owner.error('{0} has an invalid value for {3} specified: {1}. Setting to default value {2}', name, content, self.default, self._type)
            return self.default
        return value

    def _convert_to_value(self, content):
        if content is None:
            return
        return self._type(content)

    def _convert_from_value(self, content):
        return content

def _to_tunable(t, default=None, **kwargs):
    if isinstance(t, TunableBase):
        return t
    tunable_factory = Tunable
    if isinstance(t, enum.Metaclass):
        if default is None:
            default = t(0)
        if issubclass(t, enum.IntFlags):
            tunable_factory = TunableEnumFlags
        else:
            tunable_factory = TunableEnumEntry
    return tunable_factory(t, default, **kwargs)

class TunableTuple(TunableBase):
    TAGNAME = Tags.Tuple
    LOADING_TAG_NAME = LoadingTags.Tuple
    INCLUDE_UNTUNED_VALUES = True
    NO_LOCKED_ARGS = frozendict()
    __slots__ = ('locked_args', 'tunable_items', '_default', 'export_class_name', '_value_class')

    def __init__(self, *args, locked_args=None, _suppress_default_gen=False, export_class_name=None, subclass_args=None, **kwargs):
        tunable_items = {}
        remaining_kwargs = {}
        locked_args = locked_args or {}
        for (k, v) in kwargs.items():
            if k in RESERVED_KWARGS:
                if isinstance(v, TunableBase):
                    logger.error('TunableTuple {} is using key {} in RESERVED_KWARGS.', self, k)
                remaining_kwargs[k] = v
            elif k not in locked_args:
                tunable_items[k] = _to_tunable(v)
        keys = [k for k in kwargs if k not in RESERVED_KWARGS]
        if subclass_args is not None:
            keys = [k for k in keys if k not in subclass_args]
        if locked_args is not None:
            keys = list(set(keys) | set(locked_args))
        self._value_class = sims4.collections.make_immutable_slots_class(keys)
        super().__init__(*args, **remaining_kwargs)
        self.tunable_items = tunable_items
        if locked_args:
            locked_args = frozendict(locked_args)
            if locked_args in _locked_args_singletons:
                locked_args = _locked_args_singletons[locked_args]
            else:
                _locked_args_singletons[locked_args] = locked_args
        else:
            locked_args = self.NO_LOCKED_ARGS
        self.locked_args = locked_args
        if not _suppress_default_gen:
            default = {}
            for (name, template) in tunable_items.items():
                template = tunable_items[name]
                if not self._has_callback:
                    self._has_callback |= template._has_callback
                default[name] = template.default
            self._default = self._create_dict(default, locked_args)
        else:
            for template in tunable_items.values():
                if not self._has_callback:
                    self._has_callback |= template._has_callback
        self.cache_key = id(self)
        self.export_class_name = export_class_name
        self.needs_deferring = True

    def _create_dict(self, items, locked_args):
        values = dict(items)
        if locked_args:
            values.update(locked_args)
        return self._value_class(values)

    def load_etree_node(self, node=None, source=None, **kwargs):
        value = {}
        tuned = set()
        mtg = get_manager()
        if node is not None:
            for child_node in node:
                name = child_node.get(LoadingAttributes.Name)
                if name in self.tunable_items:
                    template = self.tunable_items.get(name)
                    if child_node.tag == MergedTuningAttr.Reference:
                        ref_index = child_node.get(MergedTuningAttr.Index)
                        tuplevalue = mtg.get_tunable(ref_index, template, source)
                    else:
                        current_tunable_tag = template.LOADING_TAG_NAME
                        if current_tunable_tag == Tags.TdescFragTag:
                            current_tunable_tag = template.FRAG_TAG_NAME
                        if current_tunable_tag != child_node.tag:
                            tunable_name = node.get(LoadingAttributes.Name, '<Unnamed>')
                            logger.error("Incorrectly matched tuning types found in tuning for {0} in {1}. Expected '{2}', got '{3}'", tunable_name, source, current_tunable_tag, child_node.tag)
                            logger.error('ATTRS 2: {}', node.items())
                        tuplevalue = template.load_etree_node(node=child_node, source=source)
                    value[name] = tuplevalue
                    tuned.add(name)
                else:
                    logger.error('Error in {0}, parsing a {1} tag', source, self.TAGNAME)
                    if name in self.locked_args:
                        logger.error("The tag name '{0}' is locked for this tunable and should be removed from the tuning file.", name)
                    else:
                        logger.error("The tag name '{0}' was unexpected.  Valid tags: {1}", name, ', '.join(self.tunable_items.keys()))
        if self.INCLUDE_UNTUNED_VALUES:
            leftovers = set(self.tunable_items.keys()) - tuned
            for name in leftovers:
                template = self.tunable_items[name]
                tuplevalue = template.default
                value[name] = tuplevalue
        constructed_value = self._create_dict(value, self.locked_args)
        return constructed_value

    def invoke_callback(self, instance_class, tunable_name, source, value):
        if not self._has_callback:
            return
        if self.callback is not None:
            self.callback(instance_class, tunable_name, source, **dict(value))
        if value is not DEFAULT:
            for (name, tuple_value) in value.items():
                template = self.tunable_items.get(name)
                if template is not None:
                    template.invoke_callback(instance_class, name, source, tuple_value)

    def invoke_verify_tunable_callback(self, instance_class, tunable_name, source, value):
        if not self._has_verify_tunable_callback:
            return
        if self.verify_tunable_callback is not None:
            self.verify_tunable_callback(instance_class, tunable_name, source, **dict(value))
        if value is not DEFAULT:
            for (name, tuple_value) in value.items():
                template = self.tunable_items.get(name)
                if template is not None:
                    template.invoke_verify_tunable_callback(instance_class, name, source, tuple_value)

    @property
    def export_class(self):
        if self.export_class_name is not None:
            return self.export_class_name
        return self.__class__.__name__

    def export_desc(self):
        export_dict = super().export_desc()
        if self.is_exporting_to_client:
            pass
        for (name, val) in self.tunable_items.items():
            self.add_member_desc(export_dict, name, val)
        return export_dict

    @staticmethod
    def add_member_desc(export_dict, name, val):
        sub_dict = val.export_desc()
        sub_dict[Attributes.Name] = name
        if val._display_name is not None:
            sub_dict[Attributes.DisplayName] = val._display_name
        else:
            sub_dict[Attributes.DisplayName] = get_default_display_name(name)
        if val.TAGNAME in export_dict.keys():
            export_dict[val.TAGNAME].append(sub_dict)
        else:
            export_dict[val.TAGNAME] = [sub_dict]

def function_has_only_optional_arguments(fn):
    full_arg_spec = inspect.getfullargspec(fn)
    if len(full_arg_spec.args) == len(full_arg_spec.defaults or ()) and len(full_arg_spec.kwonlyargs) == len(full_arg_spec.kwonlydefaults or ()):
        return True
    return False

class TunableFactory(TunableTuple):
    FACTORY_TYPE = None
    __slots__ = ()

    class TunableFactoryWrapper:
        __slots__ = ('_tuned_values', '_name', 'factory')

        def __init__(self, tuned_values, name, factory):
            self._tuned_values = tuned_values
            self._name = name
            self.factory = factory

        def __call__(self, *args, **kwargs):
            total_kwargs = dict(self._tuned_values, **kwargs)
            try:
                return self.factory(*args, **total_kwargs)
            except:
                logger.error('Error invoking {}:', self)
                raise

        @property
        def _factory_name(self):
            return self.factory.__name__

        def __repr__(self):
            return '{}Wrapper.{}'.format(self._name, self._factory_name)

        def __getattr__(self, name):
            try:
                return getattr(self._tuned_values, name)
            except AttributeError:
                raise AttributeError('{} does not have an attribute named {}'.format(self, name))

        def __eq__(self, other):
            if not isinstance(other, TunableFactory.TunableFactoryWrapper):
                return False
            if not self.factory == other.factory:
                return False
            if not super().__eq__(other):
                return False
            elif not self._tuned_values == other._tuned_values:
                return False
            return True

        def __hash__(self):
            return hash(self._tuned_values)

    def _create_dict(self, items, locked_args):
        new_dict = super()._create_dict(items, locked_args)
        tunable_type = type(self)
        factory = self.FACTORY_TYPE
        if factory is None:
            raise NotImplementedError('{} does not specify FACTORY_TYPE.'.format(tunable_type))
        if isinstance(factory, types.MethodType) and factory.__self__ is self:
            factory_args = inspect.getfullargspec(factory).args
            if factory_args and factory_args[0] == 'self':
                raise TypeError("{}.FACTORY_TYPE is an instance method.  Suggestion: remove the self argument and make '{}' a @staticmethod.".format(tunable_type.__name__, factory.__name__))
            raise TypeError('{}.FACTORY_TYPE is a module method.  Suggestion: use FACTORY_TYPE = staticmethod({}).'.format(tunable_type.__name__, factory.__name__))
        result = TunableFactory.TunableFactoryWrapper(new_dict, tunable_type.__name__, factory)
        return result

    def invoke_callback(self, instance_class, tunable_name, source, value):
        if not self._has_callback:
            return
        if self.callback is not None:
            self.callback(instance_class, tunable_name, source, **dict(value._tuned_values))
        for (name, tuple_value) in value._tuned_values.items():
            template = self.tunable_items.get(name)
            if template is not None:
                template.invoke_callback(instance_class, name, source, tuple_value)

    def invoke_verify_tunable_callback(self, instance_class, tunable_name, source, value):
        if not self._has_verify_tunable_callback:
            return
        if self.verify_tunable_callback is not None:
            self.verify_tunable_callback(instance_class, tunable_name, source, **dict(value._tuned_values))
        for (name, tuple_value) in value._tuned_values.items():
            template = self.tunable_items.get(name)
            if template is not None:
                template.invoke_verify_tunable_callback(instance_class, name, source, tuple_value)

    @staticmethod
    def _process_factory_tunables(factory_type, factory_tunables):
        pass

    @staticmethod
    def factory_option(fn):
        fn._factory_option = True
        return fn

    AUTO_FACTORY_TYPE_NAME_PATTERN = 'Tunable{}'

    @staticmethod
    def _invoke_callable_tunable(fn, name, all_extra_kwargs, default=UNSET):
        if name not in all_extra_kwargs:
            if function_has_only_optional_arguments(fn):
                return fn()
            if default is not UNSET:
                return default
            return fn()
        value = all_extra_kwargs.pop(name)
        if isinstance(value, tuple):
            return fn(*value)
        if isinstance(value, dict):
            return fn(**value)
        return fn(value)

    @classmethod
    def create_auto_factory(cls, factory_type, auto_factory_type_name=None, **extra_kwargs):

        class auto_factory(cls):
            __slots__ = ()
            FACTORY_TYPE = factory_type

            def __init__(self, *args, **kwargs):
                all_extra_kwargs = {}
                all_extra_kwargs.update(extra_kwargs)
                all_extra_kwargs.update(kwargs)
                factory_tunables = {'description': self.FACTORY_TYPE.__doc__}
                is_auto_init = False
                callable_tunables = {}
                mro_getter = getattr(self.FACTORY_TYPE, 'mro', None)
                if mro_getter is not None:
                    parents = mro_getter()
                    is_auto_init = AutoFactoryInit in parents
                    for src_cls in reversed(parents):
                        if src_cls in class_scan_cache:
                            (callable_updates, factory_updates) = class_scan_cache[src_cls]
                            callable_tunables.update(callable_updates)
                            factory_tunables.update(factory_updates)
                        else:
                            class_callable_tunables = {}
                            class_factory_tunables = {}
                            if 'FACTORY_TUNABLES' in vars(src_cls):
                                tunables = src_cls.FACTORY_TUNABLES
                                for (name, value) in tunables.items():
                                    if callable(value):
                                        class_callable_tunables[name] = value
                                    else:
                                        class_factory_tunables[name] = value
                            for (name, value) in vars(src_cls).items():
                                if getattr(value, '_factory_option', False):
                                    class_callable_tunables[name] = value
                            class_scan_cache[src_cls] = (class_callable_tunables, class_factory_tunables)
                            callable_tunables.update(class_callable_tunables)
                            factory_tunables.update(class_factory_tunables)
                updates = {}
                for (name, fn) in callable_tunables.items():
                    new_tunables = cls._invoke_callable_tunable(fn, name, all_extra_kwargs, {})
                    if isinstance(new_tunables, dict):
                        updates.update(new_tunables)
                    else:
                        updates[name] = new_tunables
                factory_tunables.update(updates)
                cls._process_factory_tunables(factory_type, factory_tunables)
                if is_auto_init:
                    factory_type.AUTO_INIT_KWARGS = set(factory_tunables) - RESERVED_KWARGS
                    if updates:
                        if factory_type.AUTO_INIT_OPTIONAL_KWARGS is None:
                            factory_type.AUTO_INIT_OPTIONAL_KWARGS = set()
                        factory_type.AUTO_INIT_OPTIONAL_KWARGS.update(updates)
                factory_tunables.update(all_extra_kwargs)
                super().__init__(*args, **factory_tunables)

        if auto_factory_type_name is None:
            auto_factory_type_name = cls.AUTO_FACTORY_TYPE_NAME_PATTERN.format(factory_type.__name__)
        auto_factory.__name__ = auto_factory_type_name
        return auto_factory

class HasTunableFactory:

    @classproperty
    def TunableFactory(cls):
        if '_AUTO_FACTORY' not in vars(cls):
            cls._AUTO_FACTORY = TunableFactory.create_auto_factory(cls)
        return cls._AUTO_FACTORY

class TunableSingletonFactory(TunableFactory):
    __slots__ = ('_origin_value_map',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._default = self.default()
        self._origin_value_map = None

    def load_etree_node(self, **kwargs):
        value = super().load_etree_node(**kwargs)
        if value is not None:
            constructed_value = value()
            if self._has_callback:
                if self._origin_value_map is None:
                    self._origin_value_map = {}
                self._origin_value_map[id(constructed_value)] = value
            return constructed_value

    def invoke_callback(self, instance_class, tunable_name, source, value):
        if not self._has_callback:
            return
        if self.callback is not None:
            self.callback(instance_class, tunable_name, source, value)
        if self._origin_value_map is not None:
            original_value = self._origin_value_map.get(id(value))
            if original_value is not None:
                for (name, tuple_value) in original_value._tuned_values.items():
                    template = self.tunable_items.get(name)
                    if template is not None:
                        template.invoke_callback(instance_class, name, source, tuple_value)

    def invoke_verify_tunable_callback(self, instance_class, tunable_name, source, value):
        if not self._has_verify_tunable_callback:
            return
        if self.verify_tunable_callback is not None:
            self.verify_tunable_callback(instance_class, tunable_name, source, value)
        if self._origin_value_map is not None:
            original_value = self._origin_value_map.get(id(value))
            if original_value is not None:
                for (name, tuple_value) in original_value._tuned_values.items():
                    template = self.tunable_items.get(name)
                    if template is not None:
                        template.invoke_verify_tunable_callback(instance_class, name, source, tuple_value)

class HasTunableSingletonFactory:
    __slots__ = ()

    @classproperty
    def TunableFactory(cls):
        if '_AUTO_SINGLETON_FACTORY' not in vars(cls):
            cls._AUTO_SINGLETON_FACTORY = TunableSingletonFactory.create_auto_factory(cls)
        return cls._AUTO_SINGLETON_FACTORY

class AutoFactoryInit:
    AUTO_INIT_KWARGS = None
    AUTO_INIT_OPTIONAL_KWARGS = None
    AUTO_INIT_IGNORE_VALUE = 'AUTO_INIT_IGNORE_VALUE'
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        names = set()
        if self.AUTO_INIT_KWARGS is None:
            names.update(kwargs)
        if self.AUTO_INIT_KWARGS:
            names.update(self.AUTO_INIT_KWARGS)
        if self.AUTO_INIT_OPTIONAL_KWARGS:
            names.update(self.AUTO_INIT_OPTIONAL_KWARGS)
        for name in names:
            if name in kwargs:
                value = kwargs.pop(name)
                if value != self.AUTO_INIT_IGNORE_VALUE:
                    try:
                        setattr(self, name, value)
                    except AttributeError:
                        logger.error("Can't set attribute {}.{} to {}.".format(type(self).__name__, name, value))
        try:
            super().__init__(*args, **kwargs)
        except TypeError:
            raise

    def __repr__(self):
        if not self.AUTO_INIT_KWARGS:
            return super().__repr__()
        kwargs = {}
        for name in self.AUTO_INIT_KWARGS:
            if hasattr(self, name):
                kwargs[name] = getattr(self, name)
        return standard_repr(self, **kwargs)

class TunableReferenceFactory(TunableFactory):
    AUTO_FACTORY_TYPE_NAME_PATTERN = 'Tunable{}Reference'
    __slots__ = ()

    class TunableReferenceFactoryWrapper(TunableFactory.TunableFactoryWrapper):
        __slots__ = ()

        def __getattr__(self, name):
            try:
                return getattr(self._tuned_values, name)
            except AttributeError:
                pass
            return getattr(self.factory, name)

        def __call__(self, *args, **kwargs):
            total_kwargs = dict(self._tuned_values, **kwargs)
            try:
                return self.factory(*args, **total_kwargs)
            except:
                logger.error('Error invoking {}:', self)
                raise

        @property
        def _factory_name(self):
            if self.factory is None:
                return 'None'
            return self.factory.__name__

    def __init__(self, manager, class_restrictions=(), reload_dependent=False, allow_none=False, pack_safe=False, **kwargs):
        super().__init__(factory=TunableReference(manager, class_restrictions, reload_dependent=reload_dependent, allow_none=allow_none, pack_safe=pack_safe), subclass_args=('factory',), **kwargs)
        if self.default.factory is None:
            self._default = None
        self.cache_key = '{}_{}'.format(manager.TYPE, id(self))

    def load_etree_node(self, **kwargs):
        value = super().load_etree_node(**kwargs)
        if value is not None and value.factory is not None:
            return value

    def _create_dict(self, items, locked_args):
        factory = items.pop('factory')
        new_dict = super(TunableFactory, self)._create_dict(items, locked_args)
        tunable_type = type(self)
        result = TunableReferenceFactory.TunableReferenceFactoryWrapper(new_dict, tunable_type.__name__, factory)
        return result

    def invoke_callback(self, instance_class, tunable_name, source, value):
        if not self._has_callback:
            return
        if value is not None:
            if self.callback is not None:
                self.callback(instance_class, tunable_name, source, factory=value.factory, **dict(value._tuned_values))
            for (name, tuple_value) in value._tuned_values.items():
                template = self.tunable_items.get(name)
                if template is not None:
                    template.invoke_callback(instance_class, name, source, tuple_value)

    def invoke_verify_tunable_callback(self, instance_class, tunable_name, source, value):
        if not self._has_verify_tunable_callback:
            return
        if value is not None:
            if self.verify_tunable_callback is not None:
                self.verify_tunable_callback(instance_class, tunable_name, source, factory=value.factory, **dict(value._tuned_values))
            for (name, tuple_value) in value._tuned_values.items():
                template = self.tunable_items.get(name)
                if template is not None:
                    template.invoke_verify_tunable_callback(instance_class, name, source, tuple_value)

    @staticmethod
    def _process_factory_tunables(factory_type, factory_tunables):
        if not issubclass(factory_type, AutoFactoryInit):
            return
        instance_tunables = TunedInstanceMetaclass.get_tunables(factory_type)
        for (name, tunable) in dict(factory_tunables).items():
            if tunable is None:
                pass
            elif name in instance_tunables:
                tunable = OptionalTunable(disabled_name='use_default', disabled_value=AutoFactoryInit.AUTO_INIT_IGNORE_VALUE, enabled_name='override', tunable=tunable)
                factory_tunables[name] = tunable

class TunableVariant(TunableTuple):
    TAGNAME = Tags.Variant
    LOADING_TAG_NAME = LoadingTags.Variant
    VARIANTNONE = 'None'
    VARIANTNULLTAG = Tags.Tunable
    VARIANTNULLCLASS = 'TunableExistance'
    VARIANTDEFAULTNONE = 'none'
    VARIANTDEFAULT_LOCKED_ARGS = frozendict({VARIANTDEFAULTNONE: None})
    __slots__ = ('_variant', '_variant_default', '_variant_map')

    def __init__(self, default=None, *args, locked_args=None, **kwargs):
        if not default:
            if locked_args:
                locked_args[self.VARIANTDEFAULTNONE] = None
            else:
                locked_args = self.VARIANTDEFAULT_LOCKED_ARGS
        super().__init__(*args, locked_args=locked_args, _suppress_default_gen=True, **kwargs)
        self._variant_map = None
        if default:
            self._variant_default = default
            try:
                if default in self.locked_args:
                    self._default = self.locked_args[default]
                else:
                    self._default = self.tunable_items[self._variant_default].default
            except:
                logger.exception('Error while attempting to set a default.')
        else:
            self._default = None
            self._variant_default = self.VARIANTDEFAULTNONE

    def export_desc(self):
        export_dict = super().export_desc()
        export_dict[Attributes.VariantType] = self.VARIANTNONE
        if self._variant_default:
            export_dict[Attributes.Default] = self._export_default(self._variant_default)
        for name in self.locked_args.keys():
            sub_dict = {Attributes.Class: self.VARIANTNULLCLASS, Attributes.DisplayName: get_default_display_name(name), Attributes.Name: name}
            if self.VARIANTNULLTAG in export_dict.keys():
                export_dict[self.VARIANTNULLTAG].append(sub_dict)
            else:
                export_dict[self.VARIANTNULLTAG] = [sub_dict]
        return export_dict

    def load_etree_node(self, node=None, source=None, **kwargs):
        if node is None:
            return self.default
        value = None
        mtg = get_manager()
        variant = node.get(LoadingAttributes.VariantType, self._variant_default)
        if variant is not None:
            if variant in self.locked_args:
                value = self.locked_args[variant]
            else:
                value = None
                template = self.tunable_items.get(variant)
                if template is None:
                    logger.error('Variant is set to a type that does not exist: {} in {}.'.format(variant, source))
                    return self._variant_default
                node_children = list(node)
                if node_children:
                    child_node = node_children[0]
                    name = child_node.get(LoadingAttributes.Name)
                    if child_node.tag == MergedTuningAttr.Reference:
                        ref_index = child_node.get(MergedTuningAttr.Index)
                        value = mtg.get_tunable(ref_index, template, source)
                    else:
                        current_tunable_tag = template.LOADING_TAG_NAME
                        if current_tunable_tag == Tags.TdescFragTag:
                            current_tunable_tag = template.FRAG_TAG_NAME
                        if current_tunable_tag != child_node.tag:
                            tunable_name = node.get(LoadingAttributes.Name, '<Unnamed>')
                            logger.error("Incorrectly matched tuning types found in tuning for {0} in {1}. Expected '{2}', got '{3}'".format(tunable_name, source, current_tunable_tag, child_node.tag))
                            logger.error('ATTRS 3: {}'.format(child_node.items()))
                else:
                    child_node = None
                if value is None:
                    value = template.load_etree_node(node=child_node, source=source)
                if template._has_callback:
                    if self._variant_map is None:
                        self._variant_map = {}
                    self._variant_map[id(value)] = variant
        return value

    def __getitem__(self, name):
        raise RuntimeError('__getitem__ is not valid on an untuned TunableVariant')

    def invoke_callback(self, instance_class, tunable_name, source, value):
        if not self._has_callback:
            return
        if self.callback is not None:
            self.callback(instance_class, tunable_name, source, **dict(value))
        if value is not None and self._variant_map is not None:
            variant = self._variant_map.get(id(value))
            if variant is not None:
                template = self.tunable_items.get(variant)
                if template is not None:
                    template.invoke_callback(instance_class, variant, source, value)

    def invoke_verify_tunable_callback(self, instance_class, tunable_name, source, value):
        if not self._has_verify_tunable_callback:
            return
        if self.verify_tunable_callback is not None:
            self.verify_tunable_callback(instance_class, tunable_name, source, **dict(value))
        if value is not None and self._variant_map is not None:
            variant = self._variant_map.get(id(value))
            if variant is not None:
                template = self.tunable_items.get(variant)
                if template is not None:
                    template.invoke_verify_tunable_callback(instance_class, variant, source, value)

class OptionalTunable(TunableVariant):
    __slots__ = ('export_class_name',)

    def __init__(self, tunable, enabled_by_default=False, disabled_value=None, disabled_name='disabled', enabled_name='enabled', **kwargs):
        default = enabled_name if enabled_by_default else disabled_name
        kwargs.setdefault('description', getattr(tunable, 'description', None))
        kwargs[disabled_name] = disabled_value
        kwargs[enabled_name] = tunable
        super().__init__(locked_args={disabled_name: disabled_value}, default=default, **kwargs)

class TunableRange(Tunable):
    __slots__ = ('_raw_min', '_raw_max', 'min', 'max')

    def __init__(self, tunable_type, default, minimum=None, maximum=None, **kwargs):
        super().__init__(tunable_type, default, **kwargs)
        if self._convert_defined_values:
            self._raw_min = minimum
            self._raw_max = maximum
        else:
            self._raw_min = self._convert_from_value(minimum)
            self._raw_max = self._convert_from_value(maximum)
        self.min = minimum
        self.max = maximum

    def load_etree_node(self, node=None, source=None, **kwargs):
        value = super().load_etree_node(node=node, source=source, **kwargs)
        if self._convert_defined_values:
            converted_min = self._convert_to_value(self.min)
            converted_max = self._convert_to_value(self.max)
        else:
            converted_min = self.min
            converted_max = self.max
        name = '<UNKNOWN ITEM>'
        logger_with_no_owner = sims4.log.Logger('Tuning')
        if node is not None:
            name = node.get(LoadingAttributes.Name, name)
        if converted_min is not None and value < converted_min:
            logger_with_no_owner.error('Error while parsing tuning in {0}', source)
            logger_with_no_owner.error('{0} tuned below min ({1}).  Setting to min {2}', name, value, converted_min)
            value = converted_min
        elif value > converted_max:
            logger_with_no_owner.error('Error while parsing tuning in {0}', source)
            logger_with_no_owner.error('{0} tuned above max ({1}).  Setting to max {2}', name, value, converted_max)
            value = converted_max
        return value

    def export_desc(self):
        export_dict = super().export_desc()
        export_dict[Attributes.Min] = str(self._raw_min)
        export_dict[Attributes.Max] = str(self._raw_max)
        return export_dict

class _TunableCollection(TunableBase):
    __slots__ = ('_template', '_default', 'minlength')

    def __init__(self, tunable, description=None, minlength=None, maxlength=None, source_location=None, source_query=None, allow_none=False, **kwargs):
        super().__init__(description=description, **kwargs)
        if source_location:
            source_location = '../' + source_location
        self._template = _to_tunable(tunable, source_location=source_location, source_query=source_query)
        self._has_callback |= self._template._has_callback
        self.minlength = minlength
        if isinstance(tunable, TunableBase):
            self.cache_key = tunable.cache_key
        else:
            self.cache_key = tunable
        self.needs_deferring = True

    def _get_collection_types(self):
        raise NotImplementedError

    def load_etree_node(self, node=None, source=None, **kwargs):
        (collection_type, collection_fn, final_type, is_final_node) = self._get_collection_types()
        if is_final_node(node):
            return self.default
        mtg = get_manager()
        tunable_instance = self._template
        tunable_name = node.get(LoadingAttributes.Name, '<Unnamed>')
        tunable_collection = collection_type()
        element_index = 0
        for child_node in node:
            element_index += 1
            value = None
            try:
                if child_node.tag == MergedTuningAttr.Reference:
                    ref_index = child_node.get(MergedTuningAttr.Index)
                    value = mtg.get_tunable(ref_index, tunable_instance, source)
                else:
                    current_tunable_tag = tunable_instance.LOADING_TAG_NAME
                    if current_tunable_tag == Tags.TdescFragTag:
                        current_tunable_tag = tunable_instance.FRAG_TAG_NAME
                    if current_tunable_tag != child_node.tag:
                        logger.error("Incorrectly matched tuning types found in tuning for {0} in {1}. Expected '{2}', got '{3}'", tunable_name, source, current_tunable_tag, child_node.tag)
                        logger.error('ATTRS: {}'.format(child_node.items()))
                    value = tunable_instance.load_etree_node(node=child_node, source=source)
                if False and (self.allow_none or value is None):
                    logger.error('None entry found in tunable list in {}.\nName: {}\nIndex: {}\nContent:{}', source, tunable_name, element_index, child_node)
                else:
                    collection_fn(tunable_collection, value)
            except UnavailablePackSafeResourceError:
                continue
            except TunableMinimumLengthError:
                continue
            except:
                logger.exception('Error while parsing tuning in {0}:', source)
                logger.error('Failed to load element for {0} (index {1}): {2}. Skipping.', tunable_name, element_index, child_node)
        if self.minlength is not None and len(tunable_collection) < self.minlength:
            logger.info('Collection {} in {} has fewer than the minimum number of entries.', source, tunable_name)
            raise TunableMinimumLengthError
        return final_type(tunable_collection)

    def export_desc(self):
        result = super().export_desc()
        content_export_desc = self._template.export_desc()
        content_tag = self._template.TAGNAME
        result[content_tag] = content_export_desc
        if self.minlength is not None:
            result[Attributes.Min] = self.minlength
        if self.maxlength is not None:
            result[Attributes.Max] = self.maxlength
        return result

    def invoke_callback(self, instance_class, tunable_name, source, value):
        if not self._has_callback:
            return
        super().invoke_callback(instance_class, tunable_name, source, value)
        if value is not None:
            for tuned_value in value:
                self._template.invoke_callback(instance_class, tunable_name, source, tuned_value)

    def invoke_verify_tunable_callback(self, instance_class, tunable_name, source, value):
        if not self._has_verify_tunable_callback:
            return
        super().invoke_verify_tunable_callback(instance_class, tunable_name, source, value)
        if value is not None:
            for tuned_value in value:
                self._template.invoke_verify_tunable_callback(instance_class, tunable_name, source, tuned_value)

class TunableList(_TunableCollection):
    __slots__ = ('unique_entries', 'set_default_as_first_entry')
    TAGNAME = Tags.List
    LOADING_TAG_NAME = LoadingTags.List
    DEFAULT_LIST = tuple()

    def __init__(self, tunable, unique_entries=False, set_default_as_first_entry=False, **kwargs):
        super().__init__(tunable, **kwargs)
        if set_default_as_first_entry:
            self._default = (self._template.default,)
        else:
            self._default = self.DEFAULT_LIST
        self.unique_entries = unique_entries
        if isinstance(tunable, TunableBase):
            self.cache_key = tunable.cache_key
        else:
            self.cache_key = tunable

    def _get_collection_types(self):
        return (list, list.append, tuple, self._is_final_node)

    def _is_final_node(self, node):
        if node is None:
            return True
        return len(node) == 0

    def export_desc(self):
        result = super().export_desc()
        if self.unique_entries:
            result[Attributes.UniqueEntries] = 'true'
        return result

class TunableSet(_TunableCollection):
    TAGNAME = Tags.List
    LOADING_TAG_NAME = LoadingTags.List
    DEFAULT_LIST = EMPTY_SET

    def __init__(self, tunable, **kwargs):
        super().__init__(tunable, **kwargs)
        self._default = self.DEFAULT_LIST
        self.cache_key = '{}_{}'.format('TunableSet', self.cache_key)

    def _get_collection_types(self):
        return (set, set.add, frozenset, lambda n: n is None)

    def export_desc(self):
        export_dict = super().export_desc()
        export_dict[Attributes.UniqueEntries] = 'true'
        return export_dict

class TunableMapping(TunableList):
    DEFAULT_MAPPING = frozendict()
    __slots__ = ('_tunable_value', '_key_name', '_value_name', '_tuple_name', '_key_type')

    def __init__(self, key_type=str, value_type=str, key_value_type=None, key_name='key', value_name='value', tuple_name=None, **kwargs):
        if key_value_type is not None:
            if hasattr(key_value_type, 'get_tunable_mapping_info'):
                (key_name, value_name) = key_value_type.get_tunable_mapping_info()
        else:

            def key_value_type(**kwargs):
                tuple_def = {value_name: _to_tunable(value_type), key_name: _to_tunable(key_type)}
                kwargs.update(tuple_def)
                return TunableTuple(**kwargs)

        tunable_type = key_value_type()
        self._key_name = key_name
        self._value_name = value_name
        self._tuple_name = tuple_name
        self._key_type = key_type
        super().__init__(tunable_type, **kwargs)
        self._default = TunableMapping.DEFAULT_MAPPING

    def _process_dict_value(self, value, tunable_name, source):
        if value is not None:
            if len(value) == 0:
                return TunableMapping.DEFAULT_MAPPING
            key_name = self._key_name
            value_name = self._value_name
            if False and self.allow_none:
                dict_items = {getattr(item, key_name): getattr(item, value_name) for item in value}
            else:
                dict_items = {getattr(item, key_name): getattr(item, value_name) for item in value if getattr(item, key_name) is not None and getattr(item, value_name) is not None}
            value = frozendict(dict_items)
        return value

    def load_etree_node(self, node=None, source=None, **kwargs):
        value = super().load_etree_node(node=node, source=source, **kwargs)
        tunable_name = node.get(LoadingAttributes.Name, '<UNKNOWN ITEM>')
        return self._process_dict_value(value, tunable_name, source)

    def invoke_callback(self, instance_class, tunable_name, source, value):
        if not self._has_callback:
            return
        if self.callback is not None:
            self.callback(instance_class, tunable_name, source, value)
        if value is not None:
            for (k, v) in value.items():
                tuned_value = {}
                tuned_value['key'] = k
                tuned_value['value'] = v
                self._template.invoke_callback(instance_class, tunable_name, source, tuned_value)

    def invoke_verify_tunable_callback(self, instance_class, tunable_name, source, value):
        if not self._has_verify_tunable_callback:
            return
        if self.verify_tunable_callback is not None:
            self.verify_tunable_callback(instance_class, tunable_name, source, value)
        if value is not None:
            for (k, v) in value.items():
                tuned_value = {}
                tuned_value['key'] = k
                tuned_value['value'] = v
                self._template.invoke_verify_tunable_callback(instance_class, tunable_name, source, tuned_value)

    def export_desc(self):
        export_dict = super().export_desc()
        export_dict[Attributes.MappingKey] = self._key_name
        export_dict[Attributes.MappingValue] = self._value_name
        if self.is_exporting_to_client:
            pass
        if self._tuple_name is not None:
            export_dict[Attributes.MappingClass] = self._tuple_name
        return export_dict

class TunableEnumEntry(_TunableHasPackSafeMixin, Tunable):
    TAGNAME = Tags.Enum
    LOADING_TAG_NAME = LoadingTags.Enum
    __slots__ = ('pack_safe', 'cache_key', 'invalid_enums', 'binary_type')

    def __init__(self, tunable_type, *args, invalid_enums=(), binary_type=None, **kwargs):
        if not isinstance(tunable_type, enum.Metaclass):
            raise MalformedTuningSchemaError('Must provide an Enum type to TunableEnumEntry')
        super().__init__(tunable_type, *args, **kwargs)
        self.cache_key = 'TunableEnumEntry_{}_{}'.format(tunable_type.cache_key, self.default)
        self.invalid_enums = invalid_enums
        self.binary_type = binary_type

    def _export_default(self, value):
        if isinstance(value, self._type):
            return value.name
        return super()._export_default(value)

    def export_desc(self):
        export_dict = super().export_desc()
        export_dict[Attributes.Type] = self.get_exported_type_name()
        if self.invalid_enums:
            export_dict[Attributes.InvalidEnumEntries] = ','.join(self._export_default(e) for e in self.invalid_enums)
        if self.binary_type is not None:
            export_dict[Attributes.EnumBinaryExportType] = self.binary_type
        fully_qualified_class_str = self._type.get_export_path()
        export_dict[Attributes.StaticEnumEntries] = fully_qualified_class_str
        if hasattr(self._type, '_elements'):
            export_dict[Attributes.DynamicEnumEntries] = '{0}._elements'.format(fully_qualified_class_str)
        elif hasattr(self._type, '_dynamic_entry_owner'):
            export_dict[Attributes.DynamicEnumEntries] = '{0}._elements'.format(self._type._dynamic_entry_owner.get_export_path())
        return export_dict

    def _convert_to_value(self, content):
        if content is None:
            return
        if hasattr(self._type, '_dynamic_entry_owner') and self._type._dynamic_entry_owner is not None:
            return self._type._dynamic_entry_owner(content)
        return self._type(content)

class TunableEnumWithFilter(TunableEnumEntry):
    __slots__ = ('_filter',)

    def __init__(self, tunable_type, filter_prefixes, *args, **kwargs):
        super().__init__(tunable_type, *args, **kwargs)
        self._filter = '|'.join(filter_prefixes)

    def export_desc(self):
        export_dict = super().export_desc()
        export_dict[Attributes.DynamicEntriesPrefixFilter] = self._filter
        return export_dict

class TunableEnumSet(TunableSet):
    __slots__ = ('_enum_type', 'allow_empty_set')

    def __init__(self, enum_type, enum_default=None, invalid_enums=(), default_enum_list=frozenset(), allow_empty_set=False, pack_safe=False, **kwargs):
        if enum_default is None:
            single_default = enum_type.names[0]
        else:
            single_default = enum_default
        super().__init__(TunableEnumEntry(enum_type, default=single_default, invalid_enums=invalid_enums, pack_safe=pack_safe), **kwargs)
        self._enum_type = enum_type
        self.allow_empty_set = allow_empty_set
        self._default = default_enum_list

    def export_desc(self):
        export_dict = super().export_desc()
        if self._default:
            export_dict[Attributes.Default] = self._export_default(self.default)
        return export_dict

    def _export_default(self, value):
        return ','.join(e.name for e in value)

    def load_etree_node(self, node=None, source=None, **kwargs):
        value = super().load_etree_node(node=node, source=source, **kwargs)
        if self.allow_empty_set or len(value) <= 0:
            name = '<UNKNOWN ITEM>'
            if node is not None:
                name = node.get(LoadingAttributes.Name, name)
            logger.error('Error parsing enum set for {}: No enums specified for {}', source, name)
        return value

class TunableEnumFlags(TunableSet):
    __slots__ = ('default_enum_list', 'allow_no_flags', '_enum_type')

    def __init__(self, enum_type, default=None, allow_no_flags=False, invalid_enums=(), **kwargs):
        if default is None:
            default = enum_type(0)
            default_enum_list = self.DEFAULT_LIST
        else:
            default_enum_list = enum_type.list_values_from_flags(default)
        single_default = enum_type.names[0]
        super().__init__(TunableEnumEntry(enum_type, default=single_default, invalid_enums=invalid_enums), **kwargs)
        self._enum_type = enum_type
        self.allow_no_flags = allow_no_flags
        self._default = default
        self.default_enum_list = default_enum_list

    def export_desc(self):
        export_dict = super().export_desc()
        if self.default_enum_list:
            export_dict[Attributes.Default] = self._export_default(self.default_enum_list)
        return export_dict

    def _export_default(self, value):
        return ','.join(e.name for e in value)

    def _process_flag_value(self, value, attrs, source):
        if value is self.default:
            return value
        flags = self._enum_type(0)
        for flag in value:
            if flags is None:
                flags = flag
            else:
                flags |= flag
        if self.allow_no_flags or flags == 0:
            name = '<UNKNOWN ITEM>'
            if attrs is not None:
                attr_dict = dict(attrs)
                name = attr_dict.get(LoadingAttributes.Name, name)
            logger.error('Error parsing enum flags for {}: No flags specified for {}', source, name)
        return flags

    def load_etree_node(self, node=None, source=None, **kwargs):
        value = TunableSet.load_etree_node(self, node=node, source=source, **kwargs)
        attrs = None
        if node is not None:
            attrs = node.items()
        return self._process_flag_value(value, attrs, source)

    def invoke_callback(self, instance_class, tunable_name, source, value):
        if self.callback is not None:
            self.callback(instance_class, tunable_name, source, value)

    def invoke_verify_tunable_callback(self, instance_class, tunable_name, source, value):
        if self.verify_tunable_callback is not None:
            self.verify_tunable_callback(instance_class, tunable_name, source, value)
EnumItem = collections.namedtuple('EnumItem', ('enum_name', 'enum_value'))
class TunableEnumItem(Tunable):
    __slots__ = ()

    def __init__(self):
        super().__init__(str, default=None)
        self.cache_key = 'EnumItem'

    def load_etree_node(self, node=None, source=None, **kwargs):
        enum_name = super().load_etree_node(node=node, source=source, **kwargs)
        enum_value = int(node.get(LoadingAttributes.EnumValue))
        return EnumItem(enum_name=enum_name, enum_value=enum_value)

class TunableReference(_TunableHasPackSafeMixin, Tunable):
    __slots__ = ('pack_safe', '_manager', '_class_restrictions', '_reload_dependent', 'cache_key', 'needs_deferring', '_allow_none')

    def __init__(self, manager, class_restrictions=(), reload_dependent=False, allow_none=False, **kwargs):
        callback = None
        super().__init__(str, None, callback=callback, **kwargs)
        self._manager = manager
        self._reload_dependent = reload_dependent
        self._allow_none = allow_none
        if isinstance(class_restrictions, tuple):
            self._class_restrictions = class_restrictions
        else:
            self._class_restrictions = (class_restrictions,)
        self.cache_key = manager.TYPE
        self.needs_deferring = True

    def invoke_callback(self, instance_class, tunable_name, source, value):
        if sims4.core_services.defer_tuning_references:
            logger.error("Attempting to load a reference that isn't deferred from module tuning.")
            logger.error('Source = {}, Tunable Name = {}', source, tunable_name)
        if self._reload_dependent and self.callback is not None:
            self.callback(instance_class, tunable_name, source, value)

    def invoke_verify_tunable_callback(self, instance_class, tunable_name, source, value):
        if sims4.core_services.defer_tuning_references:
            logger.error("Attempting to load a reference that isn't deferred from module tuning.")
            logger.error('Source = {}, Tunable Name = {}', source, tunable_name)
        if self._reload_dependent and self.verify_tunable_callback is not None:
            self.verify_tunable_callback(instance_class, tunable_name, source, value)

    @staticmethod
    def _callback(instance_class, tunable_name, source, value):
        pass

    @property
    def export_class(self):
        return 'TunableReference'

    def export_desc(self):
        export_dict = super().export_desc()
        export_dict[Attributes.Type] = sims4.resources.extensions[self._manager.TYPE]
        export_dict[Attributes.AllowNone] = self._allow_none
        if self._class_restrictions:

            def get_class_name(c):
                if isinstance(c, str):
                    return c
                else:
                    return c.__name__

            export_dict[Attributes.ReferenceRestriction] = ','.join(get_class_name(c) for c in self._class_restrictions)
        del export_dict[Attributes.Default]
        return export_dict

    def load_etree_node(self, node=None, source=None, **kwargs):
        if sims4.core_services.defer_tuning_references:
            logger.callstack('Attempting to load a tunable reference before services have been started. Please mark this tunable as deferred. source: {}'.format(source), sims4.log.LEVEL_ERROR)
            value = None
        elif node is None:
            value = None
        elif node.text is None:
            value = None
        else:
            reference_name = node.text
            error = None
            try:
                value = self._manager.get(reference_name, pack_safe=self.pack_safe, get_fallback_definition_id=False)
                if self._class_restrictions and value is not None:
                    value_mro_set = set([cls.__name__ for cls in value.mro()])
                    for c in self._class_restrictions:
                        if isinstance(c, str):
                            if c in value_mro_set:
                                break
                                if issubclass(value, c):
                                    break
                        elif issubclass(value, c):
                            break
                    raise ValueError('TunableReference is set to a value that is not allowed by its class restriction.')
            except UnavailablePackSafeResourceError as e:
                raise e
            except KeyError as e:
                if self._manager.TYPE == sims4.resources.Types.OBJECT:
                    value = self.default
                else:
                    error = str(e)
            except Exception as e:
                logger.exception('Caught exception loading reference. RefName: {} Manager: {}.\n {}'.format(reference_name, self._manager, e))
                error = str(e)
            if error is not None:
                name = '<UNKNOWN ITEM>'
                if node is not None:
                    name = node.get(LoadingAttributes.Name, name)
                logger.error('Error while parsing tuning in {}: {}', source, error)
                logger.error('{} has an invalid value for a tunable reference specified: {}. Setting to default value {}'.format(name, reference_name, self.default))
                value = self.default
        return value

class TunablePackSafeReference(TunableReference):
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, pack_safe=True, **kwargs)
        self.cache_key = '{}_{}'.format('TunablePackSafeReference', self._manager.TYPE.name)

    def load_etree_node(self, *args, **kwargs):
        try:
            return super().load_etree_node(*args, **kwargs)
        except UnavailablePackSafeResourceError:
            return self.default

class HasTunableReference:

    @classmethod
    def _get_tunable_reference(cls, reference_type, *args, class_restrictions=DEFAULT, **kwargs):
        if class_restrictions is DEFAULT:
            class_restrictions = () if vars(cls).get('INSTANCE_SUBCLASSES_ONLY', False) else (cls,)
        return reference_type(*args, manager=cls.tuning_manager, class_restrictions=class_restrictions, **kwargs)

    @classmethod
    def TunableReference(cls, *args, **kwargs):
        return cls._get_tunable_reference(TunableReference, *args, **kwargs)

    @classmethod
    def TunablePackSafeReference(cls, *args, **kwargs):
        return cls._get_tunable_reference(TunablePackSafeReference, *args, **kwargs)

class HasDependentTunableReference:

    @classmethod
    def _get_tunable_reference(cls, reference_type, *args, class_restrictions=DEFAULT, **kwargs):
        if class_restrictions is DEFAULT:
            class_restrictions = () if vars(cls).get('INSTANCE_SUBCLASSES_ONLY', False) else (cls,)
        return reference_type(*args, manager=cls.tuning_manager, class_restrictions=class_restrictions, reload_dependent=True, **kwargs)

    @classmethod
    def TunableReference(cls, *args, **kwargs):
        return cls._get_tunable_reference(TunableReference, *args, **kwargs)

    @classmethod
    def TunablePackSafeReference(cls, *args, **kwargs):
        return cls._get_tunable_reference(TunablePackSafeReference, *args, **kwargs)

class HasTunableReferenceFactory(AutoFactoryInit):
    __slots__ = ()

    @classproperty
    def TunableReferenceFactory(cls, **extra_kwargs):
        if '_AUTO_REFERENCE_FACTORY' not in vars(cls):
            cls._AUTO_REFERENCE_FACTORY = TunableReferenceFactory.create_auto_factory(cls, manager=cls.tuning_manager, class_restrictions=(cls,), **extra_kwargs)
        return cls._AUTO_REFERENCE_FACTORY

class TunableResourceKeyReferenceBase(_TunableHasPackSafeMixin, Tunable):
    __slots__ = ('pack_safe', 'cache_key')

    def __init__(self, default=None, **kwargs):
        super().__init__(str, default, **kwargs)
        self.cache_key = self.definition_name

    @property
    def definition_name(self):
        raise NotImplementedError

    @property
    def resource_type(self):
        raise NotImplementedError

    @property
    def export_class(self):
        return 'TunableReference'

    def _does_resource_key_exist(self, value):
        if self.resource_type is not None:
            key = sims4.resources.get_resource_key(value, self.resource_type)
            return sims4.resources.does_key_exist(key)
        return True

    def export_desc(self):
        export_dict = super().export_desc()
        export_dict[Attributes.Type] = self.definition_name
        if self._raw_default is None:
            del export_dict[Attributes.Default]
        return export_dict

    def load_etree_node(self, node=None, source=None, **kwargs):
        if node is None:
            return self.default
        if node.text is None:
            if self.default is None and self._type in (int, float, BoolWrapper):
                name = '<UNKNOWN ITEM>'
                name = node.get(LoadingAttributes.Name, name)
                logger.error('{}.{}: {} is loading a value of None.'.format(source, name, self._type))
            return self.default
        content = node.text
        reference_name = str(content)
        error = None
        try:
            value = int(reference_name, 0)
        except Exception as e:
            logger.exception('Caught exception loading {}:'.format(self.definition_name))
            error = str(e)
        if error is not None:
            name = '<UNKNOWN ITEM>'
            name = node.get(LoadingAttributes.Name, name)
            logger.error('Error while parsing tuning in {}: {}'.format(source, error))
            logger.error('{0} has an invalid value for a tunable resource key reference specified: {1}. Setting to default value {2}'.format(name, content, self.default))
            value = self.default
        elif self.pack_safe and not self._does_resource_key_exist(value):
            raise UnavailablePackSafeResourceError
        return value

class TunableCasPart(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'caspart'

    @property
    def resource_type(self):
        return sims4.resources.Types.CASPART

class TunableHouseDescription(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'housedescription'

    @property
    def resource_type(self):
        return sims4.resources.Types.HOUSEHOLD_DESCRIPTION

class TunableEntitlement(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'genericmtx'

    @property
    def resource_type(self):
        pass

class TunableSkinTone(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'skintone'

    @property
    def resource_type(self):
        return sims4.resources.Types.SKINTONE

class TunableRegionDescription(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'regiondescription'

    @property
    def resource_type(self):
        return sims4.resources.Types.REGION_DESCRIPTION

class TunableWorldDescription(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'worlddescription'

    @property
    def resource_type(self):
        return sims4.resources.Types.WORLD_DESCRIPTION

class TunableLotDescription(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'lotdescription'

    @property
    def resource_type(self):
        return sims4.resources.Types.LOT_DESCRIPTION

class TunablePackSafeLotDescription(TunableLotDescription):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, pack_safe=True, **kwargs)
        self.cache_key = '{}_{}'.format('TunablePackSafeLotDescription', self.definition_name)

    def load_etree_node(self, *args, **kwargs):
        try:
            return super().load_etree_node(*args, **kwargs)
        except UnavailablePackSafeResourceError:
            return self.default

class TunableBlock(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'block'

    @property
    def resource_type(self):
        return sims4.resources.Types.BLOCK

class TunableWallPattern(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'wallpattern'

    @property
    def resource_type(self):
        return sims4.resources.Types.WALL_PATTERN

class TunableRailing(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'railing'

    @property
    def resource_type(self):
        return sims4.resources.Types.RAILING

class TunableCeilingRail(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'ceilingrail'

    @property
    def resource_type(self):
        return sims4.resources.Types.CEILING_RAILING

class TunableFloorPattern(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'floorpattern'

    @property
    def resource_type(self):
        return sims4.resources.Types.FLOOR_PATTERN

class TunableFloorTrim(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'floortrim'

    @property
    def resource_type(self):
        return sims4.resources.Types.FLOOR_TRIM

class TunableRoofTrim(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'rooftrim'

    @property
    def resource_type(self):
        return sims4.resources.Types.ROOF_TRIM

class TunablePoolTrim(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'pooltrim'

    @property
    def resource_type(self):
        return sims4.resources.Types.POOL_TRIM

class TunableHalfWallTrim(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'halfwalltrim'

    @property
    def resource_type(self):
        return sims4.resources.Types.HALFWALL_TRIM

class TunableRoofPattern(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'roofpattern'

    @property
    def resource_type(self):
        return sims4.resources.Types.ROOF_PATTERN

class TunableRoof(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'roof'

    @property
    def resource_type(self):
        return sims4.resources.Types.ROOF

class TunableFence(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'fence'

    @property
    def resource_type(self):
        return sims4.resources.Types.FENCE

class TunableHalfWall(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'halfwall'

    @property
    def resource_type(self):
        return sims4.resources.Types.Wall

class TunableStairs(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'stair'

    @property
    def resource_type(self):
        return sims4.resources.Types.STAIRS

class TunableStyle(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'style'

    @property
    def resource_type(self):
        return sims4.resources.Types.STYLE

class TunableFrieze(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'frieze'

    @property
    def resource_type(self):
        return sims4.resources.Types.FRIEZE

class TunableMTXBundle(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'mtxbundle'

    @property
    def resource_type(self):
        return sims4.resources.Types.MTX_BUNDLE

class TunableDecoTrim(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'decotrim'

    @property
    def resource_type(self):
        return sims4.resources.Types.DECOTRIM

class TunableMagazineCollection(TunableResourceKeyReferenceBase):
    __slots__ = ()

    @property
    def definition_name(self):
        return 'magazinecollection'

    @property
    def resource_type(self):
        return sims4.resources.Types.MAGAZINECOLLECTION

class TunableAngle(TunableRange):
    __slots__ = ()

    def __init__(self, default, minimum=0, maximum=sims4.math.TWO_PI, convert_defined_values=False, **kwargs):
        super().__init__(float, default, minimum=minimum, maximum=maximum, convert_defined_values=convert_defined_values, **kwargs)
        self.cache_key = 'TunableAngle_{}'.format(default)

    def _convert_to_value(self, content):
        if content is None:
            return
        return sims4.math.deg_to_rad(self._type(content))

    def _convert_from_value(self, value):
        if value is None:
            return
        return sims4.math.rad_to_deg(value)

class TunableResourceKey(_TunableHasPackSafeMixin, Tunable):
    __slots__ = ('pack_safe', 'resource_types', '_allow_none')

    def __init__(self, default=None, resource_types=(), allow_none=False, **kwargs):
        super().__init__(sims4.resources.Key, default, **kwargs)
        self.resource_types = resource_types
        self._allow_none = allow_none
        self.cache_key = 'TunableResourceKey'

    def export_desc(self):
        export_dict = super().export_desc()
        export_dict[Attributes.ResourceTypes] = ','.join(map(hex, self.resource_types))
        if self._allow_none:
            export_dict[Attributes.AllowNone] = self._allow_none
        return export_dict

    def load_etree_node(self, *args, **kwargs):
        value = super().load_etree_node(*args, **kwargs)
        if self.pack_safe and self.validate_pack_safe and not sims4.resources.does_key_exist(value):
            raise UnavailablePackSafeResourceError
        return value

    @property
    def validate_pack_safe(self):
        return True

class TunableInteractionAsmResourceKey(TunableResourceKey):

    def __init__(self, default=None, allow_none=False, **kwargs):
        super().__init__(default=default, resource_types=[sims4.resources.Types.STATEMACHINE], allow_none=allow_none, **kwargs)

class TunablePackSafeResourceKey(TunableResourceKey):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, pack_safe=True, **kwargs)

    def load_etree_node(self, *args, **kwargs):
        try:
            return super().load_etree_node(*args, **kwargs)
        except UnavailablePackSafeResourceError:
            return

class TunablePercent(TunableRange):
    __slots__ = ()

    def __init__(self, default, minimum=0, maximum=100, needs_tuning=False, **kwargs):
        super().__init__(float, default, minimum=minimum, maximum=maximum, needs_tuning=needs_tuning, **kwargs)
        self.cache_key = 'TunablePercent_{}'.format(default)

    def _convert_to_value(self, content):
        if content is None:
            return
        return self._type(content)/100

class Tunable100ConvertRange(TunablePercent):

    def __init__(self, default, minimum=None, maximum=None, needs_tuning=False, **kwargs):
        super().__init__(default, minimum=minimum, maximum=maximum, needs_tuning=needs_tuning, **kwargs)

class TunableRate(Tunable):
    __slots__ = ('_rate_description',)

    def __init__(self, *args, rate_description, **kwargs):
        self._rate_description = rate_description
        super().__init__(*args, **kwargs)

    def export_desc(self):
        export_dict = super().export_desc()
        export_dict[Attributes.RateDescription] = self._rate_description
        return export_dict

class TunableOperator(TunableEnumEntry):
    __slots__ = ()

    def __init__(self, default, tunable_type=sims4.math.Operator, **kwargs):
        super().__init__(tunable_type, default, **kwargs)
        if default is not None:
            self._default = default.function
        else:
            self._default = None
        self.cache_key = 'TunableOperator_{}'.format(tunable_type.cache_key)

    def load_etree_node(self, **kwargs):
        value = super().load_etree_node(**kwargs)
        constructed_value = value.function
        return constructed_value

class TunableThreshold(TunableTuple):
    __slots__ = ()
    DEFAULT_THRESHOLD = sims4.math.Threshold(0, sims4.math.Operator.GREATER_OR_EQUAL.function)

    def __init__(self, description='Value/comparison pair used to define a Threshold.', value=None, default=None, **kwargs):
        if value is None:
            value = Tunable(float, 0, description='The value of a threshold.')
        super().__init__(value=value, comparison=TunableOperator(sims4.math.Operator.GREATER_OR_EQUAL, description='The comparison to perform against the value.'), description=description, **kwargs)
        self._default = TunableThreshold.DEFAULT_THRESHOLD if default is None else default

    def _process_threshold_value(self, value, source):
        try:
            threshold = sims4.math.Threshold()
            threshold.value = value.value
            threshold.comparison = value.comparison
            constructed_value = threshold
        except BaseException as e:
            logger.error('Error while parsing tuning in {0}: {1}', source, e)
            logger.error('Invalid tuning for TunableThreshold. Using defaults.')
            constructed_value = sims4.math.Threshold()
        return constructed_value

    def load_etree_node(self, node=None, source=None, **kwargs):
        value = super().load_etree_node(node=node, source=source, **kwargs)
        return self._process_threshold_value(value, source)

    def invoke_callback(self, instance_class, tunable_name, source, value):
        if self.callback is not None:
            self.callback(instance_class, tunable_name, source, value)

    def invoke_verify_tunable_callback(self, instance_class, tunable_name, source, value):
        if self.verify_tunable_callback is not None:
            self.verify_tunable_callback(instance_class, tunable_name, source, value)
_TunedInterval = collections.namedtuple('_TunedInterval', ['lower_bound', 'upper_bound'])
class TunedInterval(_TunedInterval):
    __slots__ = ()

    def __contains__(self, value):
        return self.lower_bound <= value <= self.upper_bound

    def random_float(self, seed=None):
        r = random.Random(seed)
        return r.uniform(self.lower_bound, self.upper_bound)

    def random_int(self, seed=None):
        r = random.Random(seed)
        return r.randint(self.lower_bound, self.upper_bound)

    def value_at(self, percent):
        range = self.upper_bound - self.lower_bound
        value = range*percent
        return max(min(self.lower_bound + value, self.upper_bound), self.lower_bound)

class TunableInterval(TunableSingletonFactory):
    __slots__ = ()
    FACTORY_TYPE = TunedInterval

    def __init__(self, tunable_type, default_lower, default_upper, minimum=None, maximum=None, description='A tunable interval between lower_bound and upper_bound.', **kwargs):
        if not issubclass(tunable_type, TunableBase):
            super().__init__(lower_bound=TunableRange(tunable_type, default=default_lower, minimum=minimum, description='The lower bound of the interval.'), upper_bound=TunableRange(tunable_type, default=default_upper, maximum=maximum, description='The upper bound of the interval.'), description=description, **kwargs)
        else:
            super().__init__(lower_bound=tunable_type(default=default_lower, minimum=minimum, description='The lower bound of the interval.'), upper_bound=tunable_type(default=default_upper, maximum=maximum, description='The upper bound of the interval.'), description=description, **kwargs)

    def load_etree_node(self, source=None, **kwargs):
        value = super().load_etree_node(source=source, **kwargs)
        if value.lower_bound is not None and value.upper_bound is not None and value.lower_bound > value.upper_bound:
            logger.error('Error in tunable interval: {0} > {1}, in instance {2}', value.lower_bound, value.upper_bound, source)
        return value

class TunedIntervalLiteral:

    def __init__(self, value):
        self.lower_bound = value

    @property
    def upper_bound(self):
        return self.lower_bound

    def random_float(self, *_, **__):
        return float(self.lower_bound)

    def random_int(self, *_, **__):
        return int(self.lower_bound)

class TunableIntervalLiteral(TunableSingletonFactory):
    __slots__ = ()
    FACTORY_TYPE = TunedIntervalLiteral

    def __init__(self, tunable_type, default, minimum=None, maximum=None, description='A literal value that is to be used as the lower \n                 and upper bound of an interval. This allows both literal and \n                 range interval tunings in the same TunableVariant without \n                 having to manually set the lower and upper bounds to the same\n                 value.', **kwargs):
        if not issubclass(tunable_type, TunableBase):
            super().__init__(value=TunableRange(tunable_type, minimum=minimum, maximum=maximum, default=default, description='The upper and lower bounds.'), description=description, **kwargs)
        else:
            super().__init__(value=tunable_type(minimum=minimum, maximum=maximum, default=default, description='The upper and lower bounds'), description=description, **kwargs)

class TunableLiteralOrRandomValue(TunableVariant):
    __slots__ = ()

    def __init__(self, tunable_type=int, default=10, minimum=0, maximum=None, description='A literal value or a random number within the specified range.', **kwargs):
        super().__init__(literal=TunableIntervalLiteral(tunable_type=tunable_type, default=default, minimum=minimum, maximum=maximum), random_in_range=TunableInterval(tunable_type, default, default, minimum=minimum, maximum=maximum), default='literal', description=description)

class TunableColor(TunableVariant):
    __slots__ = ()

    class TunableColorRGBA(TunableSingletonFactory):
        __slots__ = ()
        FACTORY_TYPE = staticmethod(sims4.color.from_rgba_as_int)

        def __init__(self, description='A color.', **kwargs):
            super().__init__(r=TunableRange(int, 255, 0, 255, description='red value (0-255)'), g=TunableRange(int, 255, 0, 255, description='green value (0-255)'), b=TunableRange(int, 255, 0, 255, description='blue value (0-255)'), a=TunableRange(int, 255, 0, 255, description='alpha value (0-255) (0 is transparent, 255 is opaque)'), description=description, **kwargs)

    class TunableColorHex(TunableSingletonFactory):
        __slots__ = ()

        @staticmethod
        def _factory(hex_code):
            if hex_code.startswith('#'):
                hex_code = hex_code[1:]
            value = int(hex_code, 16)
            if len(hex_code) <= 6:
                value = 4278190080 | value
            return sims4.color.ColorARGB32(value)

        FACTORY_TYPE = _factory

        def __init__(self, description='A color.', **kwargs):
            super().__init__(hex_code=Tunable(str, '#FFFFFFFF', description="An ARGB color in hex, same as one would use in HTML. A leading '0x' or '#' is allowed but not required. You can omit the alpha, in which case opaque is assumed."), description=description, **kwargs)

    def __init__(self, description='A color.', **kwargs):
        super().__init__(rgb=TunableColor.TunableColorRGBA(), hex=TunableColor.TunableColorHex(), name=TunableEnumEntry(sims4.color.Color, sims4.color.Color.WHITE), description=description, **kwargs)

class TunableSimMinute(TunableRange):
    __slots__ = ()

    def __init__(self, default, **kwargs):
        super().__init__(float, default, **kwargs)

class TunableRealSecond(TunableRange):
    __slots__ = ()

    def __init__(self, default, **kwargs):
        super().__init__(float, default, **kwargs)
