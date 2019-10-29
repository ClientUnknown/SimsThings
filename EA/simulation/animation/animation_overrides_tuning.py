import animation.posture_manifestimport servicesimport sims4.resourcesfrom animation.posture_manifest import PostureManifestOverrideKey, PostureManifestOverrideValuefrom collections import namedtuplefrom sims4.tuning.tunable import TunableMapping, TunableVariant, Tunable, TunableSingletonFactory, TunableReferencefrom sims4.tuning.tunable_base import SourceQueries
class TunableParameterMapping(TunableMapping):

    def __init__(self, **kwargs):
        super().__init__(key_name='name', value_type=TunableVariant(default='string', boolean=Tunable(bool, False), string=Tunable(str, 'value'), integral=Tunable(int, 0)), **kwargs)

class TunablePostureManifestCellValue(TunableVariant):
    __slots__ = ()

    def __init__(self, allow_none, string_name, string_default=None, asm_source=None, source_query=None):
        if asm_source is not None:
            asm_source = '../' + asm_source
        else:
            source_query = None
        locked_args = {'match_none': animation.posture_manifest.MATCH_NONE, 'match_any': animation.posture_manifest.MATCH_ANY}
        default = 'match_any'
        kwargs = {string_name: Tunable(str, string_default, source_location=asm_source, source_query=source_query)}
        if allow_none:
            locked_args['leave_unchanged'] = None
            default = 'leave_unchanged'
        super().__init__(default=default, locked_args=locked_args, **kwargs)

class TunablePostureManifestOverrideKey(TunableSingletonFactory):
    FACTORY_TYPE = PostureManifestOverrideKey

    def __init__(self, asm_source=None):
        if asm_source is not None:
            asm_source = '../' + asm_source
            source_query = SourceQueries.ASMActorSim
        else:
            source_query = None
        super().__init__(actor=TunablePostureManifestCellValue(False, 'actor_name', asm_source=asm_source, source_query=source_query), specific=TunablePostureManifestCellValue(False, 'posture_name', 'stand'), family=TunablePostureManifestCellValue(False, 'posture_name', 'stand'), level=TunablePostureManifestCellValue(False, 'overlay_level', 'FullBody'))

class TunablePostureManifestOverrideValue(TunableSingletonFactory):
    FACTORY_TYPE = PostureManifestOverrideValue

    def __init__(self, asm_source=None):
        if asm_source is not None:
            asm_source = '../' + asm_source
            source_query = SourceQueries.ASMActorObject
        else:
            source_query = None
        super().__init__(left=TunablePostureManifestCellValue(True, 'actor_name', asm_source=asm_source, source_query=source_query), right=TunablePostureManifestCellValue(True, 'actor_name', asm_source=asm_source, source_query=source_query), surface=TunablePostureManifestCellValue(True, 'actor_name', 'surface', asm_source=asm_source, source_query=source_query))
RequiredSlotOverride = namedtuple('RequiredSlotOverride', ('actor_name', 'parent_name', 'slot_type'))
class TunableRequiredSlotOverride(TunableSingletonFactory):
    __slots__ = ()
    FACTORY_TYPE = RequiredSlotOverride

    def __init__(self, asm_source=None):
        if asm_source is not None:
            source_query = SourceQueries.ASMActorObject
        else:
            source_query = None
        super().__init__(actor_name=Tunable(str, None, source_location=asm_source, source_query=source_query), parent_name=Tunable(str, 'surface', source_location=asm_source, source_query=source_query), slot_type=TunableReference(services.get_instance_manager(sims4.resources.Types.SLOT_TYPE)))
