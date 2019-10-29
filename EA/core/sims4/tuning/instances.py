import sims4.hash_utilimport sims4.loglogger = sims4.log.Logger('Tuning')INSTANCE_TUNABLES = 'INSTANCE_TUNABLES'REMOVE_INSTANCE_TUNABLES = 'REMOVE_INSTANCE_TUNABLES'TUNING_FILE_MODULE_NAME = 'sims4.tuning.class.instances'BASE_GAME_ONLY_ATTR = 'base_game_only'
class TunedInstanceMetaclass(type):

    def __new__(cls, name, bases, *args, **kwargs):
        if 'manager' in kwargs:
            manager = kwargs.pop('manager')
        else:
            for base in bases:
                if isinstance(base, TunedInstanceMetaclass):
                    manager = base.tuning_manager
                    break
            manager = None
        if 'custom_module_name' in kwargs:
            cls.__module__ = kwargs.pop('custom_module_name')
        if BASE_GAME_ONLY_ATTR in kwargs:
            cls.base_game_only = kwargs.pop(BASE_GAME_ONLY_ATTR)
        tuned_instance = super().__new__(cls, name, bases, *args, **kwargs)
        tuned_instance.tuning_manager = manager
        if cls.__module__ != TUNING_FILE_MODULE_NAME:
            manager.register_class_template(tuned_instance)
        for (name, tunable) in tuned_instance.get_tunables(ignore_tuned_instance_metaclass_subclasses=True).items():
            setattr(tuned_instance, name, tunable.default)
        tuned_instance.reloadable = True
        return tuned_instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

    def get_parents(cls):
        parents = cls.mro()
        for (i, c) in enumerate(parents[1:], 1):
            if isinstance(c, TunedInstanceMetaclass):
                parents = parents[:i]
                break
        return parents

    def get_tunables(cls, ignore_tuned_instance_metaclass_subclasses=False):
        tuning = {}
        if ignore_tuned_instance_metaclass_subclasses:
            parents = cls.get_parents()
        else:
            parents = cls.mro()
        for base_cls in reversed(parents):
            cls_vars = vars(base_cls)
            if REMOVE_INSTANCE_TUNABLES in cls_vars:
                remove_instance_tunables = cls_vars[REMOVE_INSTANCE_TUNABLES]
                for key in remove_instance_tunables:
                    if key in tuning:
                        del tuning[key]
            if INSTANCE_TUNABLES in cls_vars:
                instance_tunables = cls_vars[INSTANCE_TUNABLES]
                tuning.update(instance_tunables)
        return tuning

    def get_invalid_removals(cls):
        tuning = None
        parents = cls.mro()
        valid_remove = set()
        missing_remove = set()
        for base_cls in reversed(parents):
            cls_vars = vars(base_cls)
            if REMOVE_INSTANCE_TUNABLES in cls_vars:
                remove_instance_tunables = cls_vars[REMOVE_INSTANCE_TUNABLES]
                for key in remove_instance_tunables:
                    if key in tuning:
                        del tuning[key]
                        valid_remove.add(key)
                    elif tuning is not None:
                        missing_remove.add(key)
            if INSTANCE_TUNABLES in cls_vars:
                instance_tunables = cls_vars[INSTANCE_TUNABLES]
                if tuning is None:
                    tuning = {}
                tuning.update(instance_tunables)
        return missing_remove - valid_remove

    def get_removed_tunable_names(cls):
        removed_tuning = []
        for base_cls in cls.get_parents():
            cls_vars = vars(base_cls)
            if isinstance(base_cls, TunedInstanceMetaclass) and base_cls is not cls:
                return removed_tuning
            if REMOVE_INSTANCE_TUNABLES in cls_vars:
                remove_instance_tunables = cls_vars[REMOVE_INSTANCE_TUNABLES]
                for key in remove_instance_tunables:
                    removed_tuning.append(key)
        return removed_tuning

    def get_base_game_only(cls):
        base_game_only = getattr(cls, BASE_GAME_ONLY_ATTR, None)
        if base_game_only is None:
            base_game_only = cls.tuning_manager.base_game_only
        return base_game_only

    def add_tunable_to_instance(cls, tunable_name, tunable):
        cls_vars = vars(cls)
        if INSTANCE_TUNABLES in cls_vars:
            cls_vars[INSTANCE_TUNABLES][tunable_name] = tunable
        else:
            setattr(cls, INSTANCE_TUNABLES, {tunable_name: tunable})
        setattr(cls, tunable_name, tunable.default)

    def generate_tuned_type(cls, name, *args, **kwargs):
        tuning_class_instance = type(cls)(name, (cls,), {}, custom_module_name=TUNING_FILE_MODULE_NAME)
        return tuning_class_instance

class HashedTunedInstanceMetaclass(TunedInstanceMetaclass):

    def generate_tuned_type(cls, name, *args, **kwargs):
        inst = super().generate_tuned_type(name, *args, **kwargs)
        inst.guid = sims4.hash_util.hash32(name)
        if not hasattr(inst, 'guid64'):
            inst.guid64 = sims4.hash_util.hash64(name)
        return inst

def lock_instance_tunables(cls, **kwargs):
    for (key, value) in kwargs.items():
        setattr(cls, key, value)
    remove_tunables = set(cls.__dict__.get(REMOVE_INSTANCE_TUNABLES, ()))
    remove_tunables.update(kwargs.keys())
    setattr(cls, REMOVE_INSTANCE_TUNABLES, remove_tunables)

def prohibits_instantiation(cls):
    return vars(cls).get('INSTANCE_SUBCLASSES_ONLY', False)
