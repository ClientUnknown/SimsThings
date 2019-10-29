from sims4.localization import TunableLocalizedString
class MemoryUid(DynamicEnumLocked, display_sorted=True):
    Invalid = 0

class TunableMemoryTuple(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(name=TunableLocalizedString(export_modes=ExportModes.All, description='Localization String for the kind of memory.'), reminisce_affordance=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions='SuperInteraction', description='The interaction that is pushed on the Sim when they Reminisce about this Memory. Should most often be from the Reminisce Prototype.'), **kwargs)

class Memory:
    MEMORIES = TunableMapping(key_type=TunableEnumEntry(MemoryUid, export_modes=ExportModes.All, default=MemoryUid.Invalid, description='The Type of Memory. Should be unique. Defined in MemoryUid.'), value_type=TunableMemoryTuple(), tuple_name='MemoryMappingTuple', export_modes=ExportModes.All)
