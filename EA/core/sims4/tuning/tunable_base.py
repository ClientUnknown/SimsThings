import inspectimport sysimport sims4.logimport sims4.reloadimport sims4.resourceslogger = sims4.log.Logger('Tuning')DELETEDMARKER = object()with sims4.reload.protected(globals()):
    TDESC_FRAG_DICT_GLOBAL = {}
    DISABLE_FRAG_DUP_NAME_CHECK = False
    CLEANDOC_DICT = {}
    DISPLAYNAME_DICT = {}
class Tags:
    Module = 'Module'
    Class = 'Class'
    Instance = 'Instance'
    Tunable = 'Tunable'
    List = 'TunableList'
    Variant = 'TunableVariant'
    Tuple = 'TunableTuple'
    Enum = 'TunableEnum'
    EnumItem = 'EnumItem'
    Deleted = 'Deleted'
    TdescFragTag = 'TdescFragTag'

class LoadingTags:
    Module = 'M'
    Class = 'C'
    Instance = 'I'
    Tunable = 'T'
    List = 'L'
    Variant = 'V'
    Tuple = 'U'
    Enum = 'E'

class GroupNames:
    GENERAL = 'General'
    ANIMATION = 'Animation'
    APPEARANCE = 'Appearance'
    AUDIO = 'Audio'
    AUTONOMY = 'Autonomy'
    AVAILABILITY = 'Availability'
    BUSINESS = 'Business'
    CAREER = 'Career'
    CARRY = 'Carry'
    CAS = 'CAS'
    CLOTHING_CHANGE = 'Clothing Change'
    CLUBS = 'Clubs'
    COMPONENTS = 'Components'
    CONSTRAINTS = 'Constraints'
    CORE = '~Core~'
    CREATE_CARRYABLE = 'Carry Creation'
    CURRENCY = 'Currency'
    CUSTOMER = 'Customer'
    DEATH = 'Death'
    DECAY = 'Decay'
    DEPRECATED = 'XXX Deprecated'
    EMPLOYEES = 'Employees'
    FISHING = 'Fishing'
    GHOSTS = 'Ghosts'
    GOALS = 'Goals'
    LOOT = 'Loot'
    MIXER = 'Mixer'
    MULTIPLIERS = 'Multipliers'
    OFF_LOT = 'Off-Lot'
    ON_CREATION = 'On Creation'
    OUTFITS = 'Outfits'
    PARTICIPANT = 'Participant'
    PERSISTENCE = 'Persistence'
    PICKERTUNING = 'Picker Tuning'
    POSTURE = 'Posture'
    PRICE = 'Price'
    PUDDLES = 'Puddles'
    RELATIONSHIP = 'Relationship'
    REWARDS = 'Rewards'
    ROLES = 'Roles'
    ROUTING = 'Routing'
    SCORING = 'Scoring'
    SIM_FILTER = 'Sim Filter'
    SITUATION = 'Situation'
    SPECIAL_CASES = 'Special Cases'
    TELEMETRY = 'Telemetry'
    TIME = 'Time'
    TRIGGERS = 'Triggers'
    SOCIALS = 'Socials'
    SIM_AUTO_INVITE = 'Sim Auto Invite'
    STATE = 'State'
    TAG = 'Tag'
    TESTS = 'Tests'
    TRAVEL = 'Travel'
    UI = 'UI'
    VENUES = 'Venues'
    GIG = 'Gig'

class RateDescriptions:
    PER_SIM_MINUTE = 'per Sim minute'
    PER_SIM_HOUR = 'per Sim hour'

class FilterTag:
    DEFAULT = 0
    EXPERT_MODE = 1

class LoadingAttributes:
    Name = 'n'
    Class = 'c'
    VariantType = 't'
    InstanceModule = 'm'
    InstanceClass = 'c'
    InstanceType = 'i'
    EnumValue = 'ev'
    Path = 'p'

class Attributes:
    Name = 'name'
    DisplayName = 'display'
    Description = 'description'
    Group = 'group'
    Filter = 'filter'
    Type = 'type'
    Class = 'class'
    Default = 'default'
    PackSafe = 'pack_safe'
    AllowNone = 'allow_none'
    AllowCatalogName = 'allow_catalog_name'
    Min = 'min'
    Max = 'max'
    RateDescription = 'rate_description'
    VariantType = 'type'
    InstanceModule = 'module'
    InstanceClass = 'class'
    InstancePath = 'path'
    InstanceParents = 'parents'
    InstanceType = 'instance_type'
    InstanceSubclassesOnly = 'instance_subclasses_only'
    InstanceUseGuidForRef = 'use_guid_for_reference'
    InstanceBaseGameOnly = 'instance_base_game_only'
    InstanceRequireReference = 'instance_needs_reference'
    StaticEnumEntries = 'static_entries'
    DynamicEnumEntries = 'dynamic_entries'
    InvalidEnumEntries = 'invalid_entries'
    EnumValue = 'enum_value'
    EnumBitFlag = 'enum_bit_flag'
    EnumLocked = 'enum_locked'
    EnumOffset = 'enum_offset'
    EnumBinaryExportType = 'binary_type'
    Deprecated = 'deprecated'
    DisplaySorted = 'enum_sorted'
    Partitioned = 'enum_partitioned'
    UniqueEntries = 'unique_entries'
    ResourceTypes = 'resource_types'
    ValidationCategory = 'category'
    ValidationMethod = 'method'
    ValidationArgument = 'argument'
    ReferenceRestriction = 'restrict'
    ExportModes = 'export_modes'
    SourceLocation = 'choice_source'
    SourceQuery = 'choice_query'
    SourceSubQuery = 'choice_subquery'
    MappingKey = 'mapping_key'
    MappingValue = 'mapping_value'
    MappingClass = 'mapping_class'
    TdescFragType = 'tdescfrag'
    TdescFragClass = 'TdescFrag'
    DynamicEntriesPrefixFilter = 'dynamic_entries_prefix'
    TuningState = 'tuning_state'
    NeedsTuning = 'NeedsTuning'
    Deprecated = 'Deprecated'

class ExportModes:
    ClientBinary = 'client_binary'
    ServerBinary = 'server_binary'
    ServerXML = 'server_xml'
    All = (ClientBinary, ServerBinary, ServerXML)

class SourceQueries:
    ASMState = 'ASM:StateNames'
    ASMActorAll = 'ASM:ActorNames'
    ASMActorSim = 'ASM:ActorNames(Sim)'
    ASMActorObject = 'ASM:ActorNames(Object)'
    ASMActorProp = 'ASM:ActorNames(Prop)'
    ASMClip = 'ASM:ClipResourcesInStates({})'
    SwingEnumNamePattern = 'SwingSupport:EnumNames({})'

class SourceSubQueries:
    ClipEffectName = 'ClipResource:ClipEventActorNames(EffectEvent)'
    ClipSoundName = 'ClipResource:ClipEventActorNames(SoundEvent)'

class EnumBinaryExportType:
    EnumUint32 = 'uint32'

class TunableReadOnlyError(AttributeError):

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Attempting to write to read-only tunable - ' + self.name

class TunableAliasError(Exception):

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Attempting to alias another tunable - ' + self.name

class TunableFileReadOnlyError(Exception):

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Failed to write Tuning file - ' + self.name + ', as it is marked read-only.'

class MalformedTuningSchemaError(Exception):

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Malformed tunable specified: ' + self.name

class TunableTypeNotSupportedError(Exception):

    def __init__(self, t):
        self._type = t

    def __str__(self):
        return 'Bad type: {0}'.format(self._type)

class BoolWrapper:
    EXPORT_STRING = 'bool'

    def __new__(cls, data):
        if isinstance(data, str):
            data_lower = data.lower()
            if data_lower == 'true' or data_lower == 't':
                return True
            if data_lower == 'false' or data_lower == 'f':
                return False
            else:
                raise ValueError("Invalid string supplied to TunableBool: {0}\nExpected 'True' or 'False'.".format(data))
        else:
            return bool(data)
tunable_type_mapping = {sims4.resources.ResourceKeyWrapper: sims4.resources.ResourceKeyWrapper, sims4.resources.Key: sims4.resources.ResourceKeyWrapper, BoolWrapper: BoolWrapper, bool: BoolWrapper, str: str, float: float, int: int}
def get_default_display_name(name):
    if name is None:
        return
    if name in DISPLAYNAME_DICT:
        return DISPLAYNAME_DICT[name]
    display_name = name.replace('_', ' ').strip().title()
    DISPLAYNAME_DICT[name] = display_name
    return display_name
BASIC_DESC_KEY = (Attributes.Name, Attributes.DisplayName, Attributes.Description, Attributes.Class, Attributes.Filter, Attributes.Group, Attributes.ValidationCategory, Attributes.TuningState, Attributes.ExportModes)
def export_fragment_tag(self):
    export_desc = self.frag_desc()
    for key in list(export_desc.keys()):
        if key not in BASIC_DESC_KEY:
            del export_desc[key]
    return export_desc

class TdescFragMetaClass(type):

    def __new__(cls, name, *args, is_fragment=False, **kwargs):
        self_cls = super().__new__(cls, name, *args, **kwargs)
        self_cls.is_fragment = is_fragment
        if is_fragment:
            if DISABLE_FRAG_DUP_NAME_CHECK or not (name in TDESC_FRAG_DICT_GLOBAL and sims4.reload.currently_reloading):
                raise AssertionError('Frag Class with name {} already exists'.format(name))
            TDESC_FRAG_DICT_GLOBAL[name] = self_cls
            self_cls.frag_desc = self_cls.export_desc
            self_cls.FRAG_TAG_NAME = self_cls.TAGNAME
            self_cls.TAGNAME = Tags.TdescFragTag
            self_cls.export_desc = export_fragment_tag
        return self_cls

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
RESERVED_KWARGS = set(['description', 'category', 'callback', 'verify_tunable_callback', 'export_modes', 'display_name', '_display_name', 'deferred', 'needs_tuning', 'tuning_group', 'tuning_filter', 'default', 'is_fragment', 'cache_key', 'deprecated', 'locked_args', 'subclass_args', 'items', 'keys', 'values'])
class TunableBase(metaclass=TdescFragMetaClass):
    __slots__ = ('callback', 'deferred', 'needs_deferring', 'is_fragment', '_cache_key', '_has_callback')
    TAGNAME = Tags.Tunable
    LOADING_TAG_NAME = LoadingTags.Tunable
    FRAG_TAG_NAME = None

    def __init__(self, *, description=None, category=None, callback=None, verify_tunable_callback=None, export_modes=(), display_name=None, deferred=False, needs_tuning=False, tuning_group=GroupNames.GENERAL, tuning_filter=FilterTag.DEFAULT, deprecated=False):
        if isinstance(callback, staticmethod):
            callback = callback.__func__
        self.callback = callback
        self.deferred = deferred
        self.needs_deferring = False
        self.cache_key = self.TAGNAME
        self._has_callback = self.callback is not None

    def __set__(self, instance, owner):
        raise TunableReadOnlyError(str(self))

    @property
    def default(self):
        return self._default

    @property
    def display_name(self):
        return repr(self)

    @property
    def cache_key(self):
        return self._cache_key

    @cache_key.setter
    def cache_key(self, value):
        if isinstance(value, str):
            self._cache_key = sys.intern(value)
        else:
            self._cache_key = value

    @property
    def export_class(self):
        return self.__class__.__name__

    @property
    def has_callback(self):
        return self._has_callback

    @property
    def has_verify_tunable_callback(self):
        return False

    @property
    def is_exporting_to_client(self):
        return False

    def export_desc(self):
        description = self.description
        if description is not None:
            if description in CLEANDOC_DICT:
                description = CLEANDOC_DICT[description]
            else:
                description = inspect.cleandoc(description)
                CLEANDOC_DICT[self.description] = description
        export_dict = {Attributes.Deprecated: self._deprecated, Attributes.Group: self.group, Attributes.Filter: self.tuning_filter, Attributes.Class: self.export_class, Attributes.Description: description, Attributes.DisplayName: self.display_name, Attributes.Name: self.name}
        if self._category:
            export_dict[Attributes.ValidationCategory] = self._category
        if self.needs_tuning:
            export_dict[Attributes.TuningState] = Attributes.NeedsTuning
        if self.export_modes:
            export_dict[Attributes.ExportModes] = ','.join(self.export_modes)
        return export_dict

    def _export_default(self, value):
        return str(value)

    def load_etree_node(self, **kwargs):
        raise NotImplementedError('load method for a tunable is undefined.')

    def invoke_callback(self, instance_class, tunable_name, source, value):
        if self.callback is not None:
            self.callback(instance_class, tunable_name, source, value)

    def invoke_verify_tunable_callback(self, instance_class, tunable_name, source, value):
        if self.verify_tunable_callback is not None:
            self.verify_tunable_callback(instance_class, tunable_name, source, value)
