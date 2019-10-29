from collections import namedtuplefrom contextlib import contextmanagerimport collectionsimport functoolsimport inspectfrom sims4.common import is_available_pack, Packfrom sims4.repr_utils import standard_reprfrom sims4.utils import classpropertyimport enumimport sims4.logimport sims4.reloadcomponent_definition = namedtuple('component_definition', 'class_attr instance_attr')with sims4.reload.protected(globals()):
    native_component_id_to_class = {}
    native_component_names = set()
    component_name_to_classes = collections.defaultdict(dict)
    component_inames = set()
    component_definition_set = set()
    persistence_key_map = {}
    NO_FORWARD = 'NoForward'
    logger = sims4.log.Logger('Components')
def _update_wrapper(func, wrapper, note=None):
    functools.update_wrapper(wrapper, func)
    if note:
        if wrapper.__doc__:
            wrapper.__doc__ += '\n\n' + note
        else:
            wrapper.__doc__ = note

def componentmethod(func):
    func._export_component_method = True
    return func

def componentmethod_with_fallback(fallback):

    def dec(func):
        func._export_component_method = True
        func._export_component_method_fallback = fallback
        return func

    return dec

def forward_to_components(func):
    forwards = {}

    def wrapped_method(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        if result is not None:
            logger.error('Method {} (which will also be forwarded to components) returned a value, which was ignored: {}', func.__name__, result, owner='bhill')
        for comp in self.components_sorted_gen():
            comp_class = comp.__class__
            comp_func = forwards.get(comp_class, None)
            if comp_func is None:
                comp_func = getattr(comp_class, func.__name__, NO_FORWARD)
                forwards[comp_class] = comp_func
            if comp_func is not NO_FORWARD:
                comp_result = comp_func(comp, *args, **kwargs)
                if comp_result is not None:
                    logger.error('Method {} (which was forwarded to a component) returned a value, which was ignored: {}', func.__name__, comp_result, owner='bhill')

    _update_wrapper(func, wrapped_method, 'Calls to this method will automatically forward to all components.')
    return wrapped_method

def ored_forward_to_components(func):
    forwards = {}

    def wrapped_method(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        for comp in self.components_sorted_gen():
            comp_class = comp.__class__
            comp_func = forwards.get(comp_class, None)
            if comp_func is None:
                comp_func = getattr(comp_class, func.__name__, NO_FORWARD)
                forwards[comp_class] = comp_func
            if comp_func is not NO_FORWARD:
                result |= comp_func(comp, *args, **kwargs)
        return result

    _update_wrapper(func, wrapped_method, 'Calls to this method will automatically forward to all components.')
    return wrapped_method

def forward_to_components_gen(func):
    forwards = {}

    def wrapped_method(self, *args, **kwargs):
        for result in func(self, *args, **kwargs):
            yield result
        for comp in self.components:
            comp_class = comp.__class__
            comp_func = forwards.get(comp_class, None)
            comp_func = getattr(comp_class, func.__name__, NO_FORWARD)
            forwards[comp_class] = comp_func
            if not comp_func is None or comp_func is not NO_FORWARD:
                for i in comp_func(comp, *args, **kwargs):
                    yield i

    _update_wrapper(func, wrapped_method, 'Calls to this method will automatically forward to all components.')
    return wrapped_method

def call_component_func(component, func_name, *args, **kwargs):
    func = getattr(component, func_name, None)
    if func is not None:
        func(*args, **kwargs)

def get_component_priority_and_name_using_persist_id(persist_id):
    return persistence_key_map[persist_id]

class ComponentContainer:
    _component_reload_hooks = None
    _component_definitions = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._component_instances = {}

    def __getattr__(self, attr):
        if attr in component_inames:
            return
        return self.__getattribute__(attr)

    @property
    def is_social_group(self):
        return False

    @property
    def components(self):
        return self._component_instances.values()

    def components_sorted_gen(self):
        proxied_obj = getattr(self, 'proxied_obj', None)
        if proxied_obj is not None:
            yield from proxied_obj.components_sorted_gen()
            return
        for component_definition in self._component_definitions:
            yield self._component_instances[component_definition.INAME]

    @property
    def component_definitions(self):
        proxied_obj = getattr(self, 'proxied_obj', None)
        if proxied_obj is not None:
            return proxied_obj.component_definitions
        return self._component_definitions

    def has_component(self, component_definition):
        return self.get_component(component_definition) is not None

    def get_component(self, component_definition):
        return getattr(self, component_definition.instance_attr, None)

    def can_add_component(self, component_definition):
        return True

    def is_valid_pack(self, component):
        required_packs = component.required_packs
        if required_packs is not None and any(not is_available_pack(pack) for pack in required_packs):
            return False
        return True

    def add_component(self, component):
        component_def = component_definition(component.CNAME, component.INAME)
        if self.has_component(component_def):
            raise AttributeError('Component {} already exists on {}.'.format(component.INAME, self))
        if not self.can_add_component(component_def):
            return False
        if not self.is_valid_pack(component):
            return False
        if not component.is_valid_to_add():
            return False
        setattr(self, component.INAME, component)
        if self._component_instances:
            self._component_instances[component.INAME] = component
            component_definitions = list(self._component_definitions)
            component_definitions.append(type(component))
            self._component_definitions = tuple(sorted(component_definitions, key=lambda t: (-t.priority, t.INAME)))
        else:
            self._component_instances = {}
            self._component_instances[component.INAME] = component
            self._component_definitions = (type(component),)
        return True

    def remove_component(self, component_definition):
        proxied_obj = getattr(self, 'proxied_obj', None)
        if proxied_obj is not None:
            return proxied_obj.remove_component(component_definition)
        component_name = getattr(self, component_definition.instance_attr)
        del self._component_instances[component_definition.instance_attr]
        component_definitions = list(self._component_definitions)
        component_definitions.remove(type(component_name))
        self._component_definitions = tuple(sorted(component_definitions, key=lambda t: (-t.priority, t.INAME)))
        if not self._component_definitions:
            del self._component_definitions
            self._component_instances = {}
        setattr(self, component_definition.instance_attr, None)
        return component_name

    def add_dynamic_component(self, component_definition, **kwargs):
        proxied_obj = getattr(self, 'proxied_obj', None)
        if proxied_obj is not None:
            return proxied_obj.add_dynamic_component(component_definition, **kwargs)
        if not self.has_component(component_definition):
            if component_definition.instance_attr not in component_name_to_classes:
                raise ValueError('Unknown component: {}'.format(component_definition.instance_attr))
            component_classes = component_name_to_classes[component_definition.instance_attr]
            if len(component_classes) > 1:
                raise ValueError('Non-unique components cannot be added dynamically: {}'.format(component_definition.instance_attr))
            for component_class in component_classes.values():
                if not self.is_valid_pack(component_class):
                    return False
                if component_class.allow_dynamic and component_class.can_be_added_dynamically(self):
                    component = component_class(self, **kwargs)
                    if component.is_valid_to_add():
                        return self.add_component(component)
                        sims4.log.Logger('Components').info('Trying to add the {} component dynamically which is not allowed. Component not added'.format(component_definition.instance_attr))
                else:
                    sims4.log.Logger('Components').info('Trying to add the {} component dynamically which is not allowed. Component not added'.format(component_definition.instance_attr))
        return False

    def on_failed_to_load_component(self, component_definition, persistable_data):
        if self.has_component(component_definition):
            return
        if component_definition.instance_attr not in component_name_to_classes:
            logger.error('Unknown component failed to load: {}', component_definition.instance_attr)
            return
        component_classes = component_name_to_classes[component_definition.instance_attr]
        if len(component_classes) > 1:
            logger.error('Non-unique components not sure which failed load to call: {}', component_definition.instance_attr)
            return
        for component_class in component_classes.values():
            if not component_class.allow_dynamic:
                return component_class.on_failed_to_load_component(self, persistable_data)

@contextmanager
def restore_component_methods(oldobj, newobj):
    for component_definition in oldobj._component_reload_hooks.values():
        component_definition._apply_component_methods(newobj, True)
    yield None

class ComponentPriority(enum.Int, export=False):
    PRIORITY_DEFAULT = 0
    PRIORITY_RETAIL = 5
    PRIORITY_STATISTIC = 10
    PRIORITY_STATE = 20
    PRIORITY_FLOWING_PUDDLE = 25

class ComponentMetaclass(type):

    def __new__(mcs, name, bases, cls_dict, component_name=None, key=None, persistence_key=None, persistence_priority=ComponentPriority.PRIORITY_DEFAULT, use_owner=True, allow_dynamic=False, **kwargs):
        cls = super().__new__(mcs, name, bases, cls_dict, **kwargs)
        if component_name is None:
            return cls
        if key:
            native_component_id_to_class.setdefault(key, cls)
        if persistence_key:
            persistence_key_map[persistence_key] = (persistence_priority, component_name)
        cntc_key = (cls.__module__, cls.__name__)
        component_name_to_classes[component_name.class_attr].setdefault(cntc_key, cls)
        component_name_to_classes[component_name.instance_attr].setdefault(cntc_key, cls)
        component_definition_set.add(component_definition(component_name.class_attr, component_name.instance_attr))
        setattr(ComponentContainer, component_name.class_attr, None)
        cls.CNAME = component_name.class_attr
        cls.INAME = component_name.instance_attr
        cls.allow_dynamic = allow_dynamic
        cls.priority = persistence_priority
        component_inames.add(cls.INAME)
        patched_owner_classes = set()
        component_methods = {}

        def build_exported_func(func):

            def exported_func(owner, *args, **kwargs):
                comp = getattr(owner, component_name.instance_attr)
                if comp is None:
                    fallback = getattr(ComponentContainer, func.__name__)
                    return fallback(*args, **kwargs)
                return func(comp, *args, **kwargs)

            _update_wrapper(func, exported_func, 'This method is provided by {}.'.format(cls.__name__))
            return exported_func

        for (func_name, func) in inspect.getmembers(cls, lambda member: getattr(member, '_export_component_method', False)):
            if func_name in component_methods:
                logger.error('Doubled up component method: {}', func_name, owner='bhill')
            component_methods[func.__name__] = build_exported_func(func)
            fallback = getattr(func, '_export_component_method_fallback', None)
            if fallback is not None:
                setattr(ComponentContainer, func_name, staticmethod(fallback))

        def apply_component_methods(owner_cls, reload):
            if reload or owner_cls not in patched_owner_classes:
                for (name, func) in component_methods.items():
                    existing_attr = getattr(owner_cls, name, None)
                    if existing_attr == getattr(ComponentContainer, name, None):
                        setattr(owner_cls, name, func)
                if owner_cls._component_reload_hooks is None:
                    owner_cls._component_reload_hooks = {}
                    if sims4.reload._getattr_exact(owner_cls, '__reload_context__') is not None:
                        logger.warn('Class already defines a __reload_context__, component methods may not work correctly after hot.reload: {}', owner_cls)
                    setattr(owner_cls, '__reload_context__', restore_component_methods)
                owner_cls._component_reload_hooks[component_name.instance_attr] = cls
                patched_owner_classes.add(owner_cls)

        cls._apply_component_methods = staticmethod(apply_component_methods)
        return cls

    def __init__(cls, name, bases, cls_dict, *args, component_name=None, key=None, persistence_key=None, persistence_priority=ComponentPriority.PRIORITY_DEFAULT, use_owner=None, allow_dynamic=None, **kwargs):
        super().__init__(name, bases, cls_dict, *args, **kwargs)

    def __call__(cls, owner, *args, **kwargs):
        if not hasattr(cls, 'INAME'):
            raise NotImplementedError('{} cannot be instantiated because it has no component_name defined.'.format(cls.__name__))
        component = super().__call__(owner, *args, **kwargs)
        component._apply_component_methods(type(owner), False)
        return component

class Component(metaclass=ComponentMetaclass):

    def __init__(self, owner, **kwargs):
        super().__init__(**kwargs)
        self.owner = owner

    @classproperty
    def required_packs(cls):
        return (Pack.BASE_GAME,)

    def is_valid_to_add(self):
        return True

    def get_subcomponents_gen(self):
        yield self

    @classmethod
    def on_failed_to_load_component(cls, owner, persistable_data):
        pass

    @classmethod
    def can_be_added_dynamically(cls, obj):
        return True

    def save(self, persistence_master_message):
        pass

    def load(self, component_save_message):
        pass

    def __repr__(self):
        return standard_repr(self, self.owner)
