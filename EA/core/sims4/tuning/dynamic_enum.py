import contextlibfrom sims4.common import Pack, is_available_packfrom sims4.tuning.tunable import TunableEnumItem, TunableListimport enumimport sims4.loglogger = sims4.log.Logger('Enum')global_locked_enums_maps = {}
def validate_locked_enum_id(enum_map_class, enum_id, enum_object, invalid_id=None):
    if enum_map_class is None or enum_id is None or enum_object is None:
        return False
    locked_enums = {}
    class_name = enum_map_class.__name__
    if class_name in global_locked_enums_maps:
        locked_enums = global_locked_enums_maps[class_name]
    if enum_id == invalid_id:
        logger.error('{} {} must have an unique id assigned.', class_name, enum_object.__name__, owner='cjiang')
        return False
    for (exist_id, exist_object) in locked_enums.items():
        if exist_id == enum_id and exist_object != enum_object:
            logger.error('{} {} is trying to assign an id({}) which is already used by {}.', class_name, enum_object.__name__, enum_id, exist_object.__name__, owner='cjiang')
            return False
    locked_enums[enum_id] = enum_object
    global_locked_enums_maps[class_name] = locked_enums
    return True

def _get_pack_from_enum_value(enum_value):
    if enum_value < 8192:
        return Pack.BASE_GAME
    return Pack((enum_value - 8192)//2048 + 1)

class TunableDynamicEnumElements(TunableList):

    def __init__(self, finalize, description='The list of elements in the dynamic enumeration.', **kwargs):
        super().__init__(TunableEnumItem(), description=description, unique_entries=True, **kwargs)
        self._finalize = finalize
        self.needs_deferring = False

    def load_etree_node(self, source=None, **kwargs):
        value = super().load_etree_node(source=source, **kwargs)
        self._finalize(*value)

class DynamicEnumMetaclass(enum.Metaclass):

    def __new__(cls, classname, bases, class_dict, export_modes=(), dynamic_entry_owner=None, dynamic_max_length=None, dynamic_offset=None, **kwargs):
        enum_type = super().__new__(cls, classname, bases, class_dict, offset=dynamic_offset, **kwargs)
        with enum_type.make_mutable():
            if dynamic_entry_owner is None:
                enum_type._elements = TunableDynamicEnumElements(enum_type.finalize, export_modes=export_modes, maxlength=dynamic_max_length)
            enum_type._dynamic_entry_owner = dynamic_entry_owner
        return enum_type

    def finalize(cls, *tuned_elements):
        with cls.make_mutable():
            if not hasattr(cls, '_static_index'):
                cls._static_index = len(cls) - 1
            index = cls._static_index + 1
            items = tuple(cls.items())
            for (item_name, item_value) in items[index:]:
                delattr(cls, item_name)
                del cls.name_to_value[item_name]
                del cls.value_to_name[item_value]
            for element in tuned_elements:
                enum_name = element.enum_name
                raw_value = element.enum_value
                if cls.partitioned and not (cls.locked or is_available_pack(_get_pack_from_enum_value(raw_value))):
                    pass
                else:
                    cls._add_new_enum_value(enum_name, raw_value)

class DynamicEnum(enum.Int, metaclass=DynamicEnumMetaclass):
    pass

class DynamicEnumLocked(DynamicEnum, locked=True):
    pass

class DynamicEnumFlags(enum.IntFlags, metaclass=DynamicEnumMetaclass):
    pass
