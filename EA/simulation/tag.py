import functoolsfrom sims4.tuning.dynamic_enum import DynamicEnumLockedfrom sims4.tuning.tunable import TunableSet, TunableEnumEntry, TunableEnumWithFilterfrom sims4.tuning.tunable_base import ExportModesimport singletonsPORTAL_DISALLOWANCE_PREFIX = ('PortalDisallowance',)INTERACTION_PREFIX = ('interaction',)SPAWN_PREFIX = ('Spawn',)
class Tag(DynamicEnumLocked, export_modes=(ExportModes.ClientBinary, ExportModes.ServerXML), display_sorted=True, partitioned=True):
    INVALID = 0

class TagCategory(DynamicEnumLocked, export_modes=(ExportModes.ClientBinary, ExportModes.ServerXML)):
    INVALID = 0

class TunableTag(TunableEnumWithFilter):

    def __init__(self, description='A tag.', filter_prefixes=singletons.EMPTY_SET, pack_safe=True, **kwargs):
        super().__init__(tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), pack_safe=pack_safe, filter_prefixes=filter_prefixes, **kwargs)

class TunableTags(TunableSet):

    def __init__(self, filter_prefixes=None, pack_safe=True, minlength=None, maxlength=None, **kwargs):
        if filter_prefixes is None:
            tunable_fn = TunableEnumEntry
        else:
            tunable_fn = functools.partial(TunableEnumWithFilter, filter_prefixes=filter_prefixes)
        super().__init__(tunable_fn(tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), pack_safe=pack_safe, **kwargs), minlength=minlength, maxlength=maxlength)
