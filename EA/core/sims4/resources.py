from _resourceman import *import _resourcemanimport ioimport osimport protocolbuffersfrom caches import cachedimport enumimport sims4.callback_utilsimport sims4.hash_utilimport sims4.loglogger = sims4.log.Logger('Resources', default_owner='manus')INVALID_KEY = Key(0, 0, 0)localwork = frozenset(list_local(key=None, include_packed=False)[0])localwork_no_groupid = frozenset([Key(x.type, x.instance) for x in localwork])INSTANCE_TUNING_DEFINITIONS = []TYPE_RES_DICT = {}sims4.callback_utils.add_callbacks(sims4.callback_utils.CallbackEvent.TUNING_CODE_RELOAD, purge_cache)
def cache_localwork():
    global localwork, localwork_no_groupid
    localwork = frozenset(list_local(key=None, include_packed=False)[0])
    localwork_no_groupid = frozenset([Key(x.type, x.instance) for x in localwork])

class InstanceTuningDefinition:

    def __init__(self, type_name, type_name_plural=None, file_extension=None, resource_type=None, manager_name=None, use_guid_for_ref=True, base_game_only=False, require_reference=False):
        if type_name_plural is None:
            type_name_plural = type_name + 's'
        if file_extension is None:
            file_extension = type_name
        if resource_type is None:
            resource_type = sims4.hash_util.hash32(file_extension)
        if manager_name is None:
            manager_name = type_name + '_manager'
        self.type_name = type_name
        self.TYPE_NAME = type_name.upper()
        self.TypeNames = type_name_plural.title().replace('_', '')
        self.file_extension = file_extension
        self.resource_type = resource_type
        self.manager_name = manager_name
        self.use_guid_for_ref = use_guid_for_ref
        self.base_game_only = base_game_only
        self.require_reference = require_reference

    @property
    def TYPE_ENUM_VALUE(self):
        return getattr(Types, self.TYPE_NAME)

class Types(enum.Int, export=False):

    def _add_inst_tuning(*args, **kwargs):
        definition = InstanceTuningDefinition(*args, **kwargs)
        INSTANCE_TUNING_DEFINITIONS.append(definition)
        TYPE_RES_DICT[definition.resource_type] = definition.file_extension
        return definition.resource_type

    INVALID = 4294967295
    MODEL = 23466547
    RIG = 2393838558
    FOOTPRINT = 3548561239
    SLOT = 3540272417
    OBJECTDEFINITION = 3235601127
    OBJCATALOG = 832458525
    MAGAZINECOLLECTION = 1946487583
    GPINI = 2249506521
    PNG = 796721156
    TGA = 796721158
    STATEMACHINE = 47570707
    PROPX = 968010314
    VP6 = 929579223
    BC_CACHE = 479834948
    AC_CACHE = 3794048034
    XML = 53690476
    TRACKMASK = 53633251
    CLIP = 1797309683
    CLIP_HEADER = 3158986820
    OBJDEF = 3625704905
    SIMINFO = 39769844
    CASPART = 55242443
    SKINTONE = 55867754
    COMBINED_TUNING = 1659456824
    PLAYLIST = 1415235194
    DDS = 11720834
    WALKSTYLE = 666901909
    HOUSEHOLD_DESCRIPTION = 1923050575
    REGION_DESCRIPTION = 3596464121
    WORLD_DESCRIPTION = 2793466443
    LOT_DESCRIPTION = 26488364
    FRIEZE = 2690089244
    BLOCK = 127102176
    CEILING_RAILING = 1057772186
    FENCE = 68746794
    FLOOR_TRIM = 2227319321
    FLOOR_PATTERN = 3036111561
    POOL_TRIM = 2782919923
    ROOF = 2448276798
    ROOF_TRIM = 2956008719
    ROOF_PATTERN = 4058889606
    STAIRS = 2585840924
    RAILING = 471658999
    STYLE = 2673671952
    WALL = 2438063804
    WALL_PATTERN = 3589339425
    GENERIC_MTX = 2885921078
    TRAY_METADATA = 713711138
    HALFWALL_TRIM = 2851789917
    MTX_BUNDLE = 2377243942
    DECOTRIM = 332336850
    TUNING = _add_inst_tuning('tuning', type_name_plural='tuning', file_extension='tun', resource_type=62078431, manager_name='module_tuning_manager')
    SNIPPET = _add_inst_tuning('snippet', resource_type=2113017500, require_reference=True)
    POSTURE = _add_inst_tuning('posture', resource_type=2909789983)
    SLOT_TYPE = _add_inst_tuning('slot_type', resource_type=1772477092, use_guid_for_ref=False, base_game_only=True, require_reference=True)
    STATIC_COMMODITY = _add_inst_tuning('static_commodity', type_name_plural='static_commodities', file_extension='scommodity', resource_type=1359443523, require_reference=True)
    RELATIONSHIP_BIT = _add_inst_tuning('relationship_bit', file_extension='relbit', resource_type=151314192, require_reference=True)
    OBJECT_STATE = _add_inst_tuning('object_state', resource_type=1526890910)
    RECIPE = _add_inst_tuning('recipe', resource_type=3952605219, require_reference=True)
    GAME_RULESET = _add_inst_tuning('game_ruleset', resource_type=3779558936, require_reference=True)
    STATISTIC = _add_inst_tuning('statistic', resource_type=865846717, require_reference=True)
    MOOD = _add_inst_tuning('mood', resource_type=3128647864, require_reference=True)
    BUFF = _add_inst_tuning('buff', resource_type=1612179606, require_reference=True)
    TRAIT = _add_inst_tuning('trait', resource_type=3412057543)
    SLOT_TYPE_SET = _add_inst_tuning('slot_type_set', resource_type=1058419973, use_guid_for_ref=False, base_game_only=True)
    PIE_MENU_CATEGORY = _add_inst_tuning('pie_menu_category', type_name_plural='pie_menu_categories', resource_type=65657188, require_reference=True)
    ASPIRATION = _add_inst_tuning('aspiration', resource_type=683034229)
    ASPIRATION_CATEGORY = _add_inst_tuning('aspiration_category', type_name_plural='aspiration_categories', resource_type=3813727192, require_reference=True)
    ASPIRATION_TRACK = _add_inst_tuning('aspiration_track', resource_type=3223387309)
    OBJECTIVE = _add_inst_tuning('objective', resource_type=6899006, require_reference=True)
    TUTORIAL = _add_inst_tuning('tutorial', resource_type=3762955427)
    TUTORIAL_TIP = _add_inst_tuning('tutorial_tip', resource_type=2410930353)
    CAREER = _add_inst_tuning('career', resource_type=1939434475)
    INTERACTION = _add_inst_tuning('interaction', resource_type=3900887599, manager_name='affordance_manager', require_reference=True)
    ACHIEVEMENT = _add_inst_tuning('achievement', resource_type=2018877086)
    ACHIEVEMENT_CATEGORY = _add_inst_tuning('achievement_category', type_name_plural='achievement_categories', resource_type=609337601, require_reference=True)
    ACHIEVEMENT_COLLECTION = _add_inst_tuning('achievement_collection', resource_type=80917605)
    SERVICE_NPC = _add_inst_tuning('service_npc', resource_type=2629964386, require_reference=True)
    VENUE = _add_inst_tuning('venue', resource_type=3871070174)
    REWARD = _add_inst_tuning('reward', resource_type=1873057832, require_reference=True)
    TEST_BASED_SCORE = _add_inst_tuning('test_based_score', resource_type=1332976878, require_reference=True)
    LOT_TUNING = _add_inst_tuning('lot_tuning', resource_type=3632270694, require_reference=True)
    REGION = _add_inst_tuning('region', resource_type=1374134669, require_reference=True)
    STREET = _add_inst_tuning('street', resource_type=4142189312, require_reference=True)
    WALK_BY = _add_inst_tuning('walk_by', resource_type=1070998590, require_reference=True)
    OBJECT = _add_inst_tuning('object', manager_name='definition_manager', resource_type=3055412916, require_reference=True)
    ANIMATION = _add_inst_tuning('animation', resource_type=3994535597, require_reference=True)
    BALLOON = _add_inst_tuning('balloon', resource_type=3966406598, require_reference=True)
    ACTION = _add_inst_tuning('action', resource_type=209137191, require_reference=True)
    OBJECT_PART = _add_inst_tuning('object_part', resource_type=1900520272, require_reference=True)
    SITUATION = _add_inst_tuning('situation', resource_type=4223905515)
    SITUATION_JOB = _add_inst_tuning('situation_job', resource_type=2617738591, require_reference=True)
    SITUATION_GOAL = _add_inst_tuning('situation_goal', resource_type=1502554343, require_reference=True)
    SITUATION_GOAL_SET = _add_inst_tuning('situation_goal_set', resource_type=2649944562, require_reference=True)
    STRATEGY = _add_inst_tuning('strategy', resource_type=1646578134, require_reference=True)
    SIM_FILTER = _add_inst_tuning('sim_filter', resource_type=1846401695, require_reference=True)
    TOPIC = _add_inst_tuning('topic', resource_type=1938713686, require_reference=True)
    SIM_TEMPLATE = _add_inst_tuning('sim_template', resource_type=212125579, require_reference=True)
    SUBROOT = _add_inst_tuning('subroot', resource_type=3086978965, require_reference=True)
    SOCIAL_GROUP = _add_inst_tuning('social_group', manager_name='social_group_tuning_manager', resource_type=776446212, require_reference=True)
    TAG_SET = _add_inst_tuning('tag_set', resource_type=1228493570, require_reference=True)
    TEMPLATE_CHOOSER = _add_inst_tuning('template_chooser', resource_type=1220728301, require_reference=True)
    ZONE_DIRECTOR = _add_inst_tuning('zone_director', resource_type=4183335058, require_reference=True)
    ROLE_STATE = _add_inst_tuning('role_state', resource_type=239932923, require_reference=True)
    CAREER_LEVEL = _add_inst_tuning('career_level', resource_type=745582072, require_reference=True)
    CAREER_TRACK = _add_inst_tuning('career_track', resource_type=1221024995, require_reference=True)
    CAREER_EVENT = _add_inst_tuning('career_event', resource_type=2487354146, require_reference=True)
    BROADCASTER = _add_inst_tuning('broadcaster', resource_type=3736796019, require_reference=True)
    AWAY_ACTION = _add_inst_tuning('away_action', resource_type=2947394632, require_reference=True)
    ROYALTY = _add_inst_tuning('royalty', resource_type=938421991)
    NOTEBOOK_ENTRY = _add_inst_tuning('notebook_entry', resource_type=2567109238)
    DETECTIVE_CLUE = _add_inst_tuning('detective_clue', resource_type=1400130038)
    BUCKS_PERK = _add_inst_tuning('bucks_perk', resource_type=3963461902)
    STORY_PROGRESSION_ACTION = _add_inst_tuning('story_progression_action', file_extension='spaction', resource_type=3187939130, require_reference=True)
    CLUB_SEED = _add_inst_tuning('club_seed', resource_type=794407991, require_reference=True)
    CLUB_INTERACTION_GROUP = _add_inst_tuning('club_interaction_group', resource_type=4195351092, require_reference=True)
    DRAMA_NODE = _add_inst_tuning('drama_node', resource_type=626258997)
    ENSEMBLE = _add_inst_tuning('ensemble', resource_type=3112702240, require_reference=True)
    BUSINESS = _add_inst_tuning('business', type_name_plural='businesses', resource_type=1977092083, require_reference=True)
    OPEN_STREET_DIRECTOR = _add_inst_tuning('open_street_director', resource_type=1265622724, require_reference=True)
    ZONE_MODIFIER = _add_inst_tuning('zone_modifier', resource_type=1008568217)
    USER_INTERFACE_INFO = _add_inst_tuning('user_interface_info', resource_type=3099531875)
    CALL_TO_ACTION = _add_inst_tuning('call_to_action', type_name_plural='calls_to_action', resource_type=4114068192)
    SICKNESS = _add_inst_tuning('sickness', type_name_plural='sicknesses', resource_type=3288062174)
    BREED = _add_inst_tuning('breed', resource_type=874331941)
    CAS_MENU_ITEM = _add_inst_tuning('cas_menu_item', resource_type=213537012)
    CAS_MENU = _add_inst_tuning('cas_menu', resource_type=2472182722)
    RELATIONSHIP_LOCK = _add_inst_tuning('relationship_lock', resource_type=2922702451)
    HOUSEHOLD_MILESTONE = _add_inst_tuning('household_milestone', resource_type=963831539)
    CONDITIONAL_LAYER = _add_inst_tuning('conditional_layer', resource_type=2441338001, require_reference=True)
    SEASON = _add_inst_tuning('season', resource_type=3381515358, require_reference=True)
    HOLIDAY_DEFINITION = _add_inst_tuning('holiday_definition', resource_type=238120813, require_reference=True)
    HOLIDAY_TRADITION = _add_inst_tuning('holiday_tradition', resource_type=1070408838)
    WEATHER_EVENT = _add_inst_tuning('weather_event', resource_type=1476851130, require_reference=True)
    WEATHER_FORECAST = _add_inst_tuning('weather_forecast', resource_type=1233072753, require_reference=True)
    LOT_DECORATION = _add_inst_tuning('lot_decoration', resource_type=4264407467)
    LOT_DECORATION_PRESET = _add_inst_tuning('lot_decoration_preset', resource_type=3726571771)
    CAREER_GIG = _add_inst_tuning('career_gig', resource_type=3436908253)
    HEADLINE = _add_inst_tuning('headline', resource_type=4093714525, require_reference=True)
    RABBIT_HOLE = _add_inst_tuning('rabbit_hole', resource_type=2976568058, require_reference=True)
    NARRATIVE = _add_inst_tuning('narrative', resource_type=1047870521, require_reference=True)
    SPELL = _add_inst_tuning('spell', resource_type=523506649, require_reference=True)
    CAS_STORIES_QUESTION = _add_inst_tuning('cas_stories_question', resource_type=52718493, require_reference=True)
    CAS_STORIES_ANSWER = _add_inst_tuning('cas_stories_answer', resource_type=2163289367, require_reference=True)
    CAS_STORIES_TRAIT_CHOOSER = _add_inst_tuning('cas_stories_trait_chooser', resource_type=2376930633, require_reference=True)
    TDESC_DEBUG = _add_inst_tuning('tdesc_debug')
    TUNING_DESCRIPTION = 2519486516
    del _add_inst_tuning

class Groups(enum.Int, export=False):
    INVALID = 4294967295

class CompoundTypes:
    IMAGE = [Types.PNG]
extensions = {Types.TUNING_DESCRIPTION: 'tdesc'}hot_swappable_type_ids = [Types.OBJECTDEFINITION]for definition in INSTANCE_TUNING_DEFINITIONS:
    extensions[definition.TYPE_ENUM_VALUE] = definition.file_extension
    hot_swappable_type_ids.append(definition.TYPE_ENUM_VALUE)for type_id in hot_swappable_type_ids:
    try:
        make_resource_hot_swappable(type_id)
    except RuntimeError:
        pass
def get_resource_key(potential_key, resource_type):
    if isinstance(potential_key, int):
        return Key(resource_type, potential_key)
    if isinstance(potential_key, str):
        try:
            instance_id = int(potential_key)
            return Key(resource_type, instance_id)
        except:
            file_portion = os.path.split(potential_key)[1]
            filename = os.path.splitext(file_portion)[0]
            resource_key = Key.hash64(filename, type=resource_type)
            return resource_key
    return potential_key

class ResourceKeyWrapper:
    EXPORT_STRING = 'ResourceKey'

    def __new__(cls, data):
        data_tuple = data.split(':')
        if len(data_tuple) == 2:
            return Key.hash64(data_tuple[1], type=Types(data_tuple[0]), group=0)
        if len(data_tuple) == 3:
            return Key(int(data_tuple[0], 16), int(data_tuple[2], 16), int(data_tuple[1], 16))
        raise ValueError('Invalid string passed into TunableResource. Expected Type:Instance or Type:Instance:Group.')

class ResourceLoader:

    def __init__(self, resource_key, resource_type=None):
        self.filename = resource_key
        if isinstance(resource_key, (str, int)):
            if resource_type is None:
                raise ValueError('Resource loader requires a resource_type when provided with a string: {}'.format(resource_key))
            resource_key = sims4.resources.get_resource_key(resource_key, resource_type)
        self.resource_key = resource_key

    def load(self, silent_fail=True):
        resource = self.load_raw(silent_fail=silent_fail)
        return self.cook(resource)

    def load_raw(self, silent_fail=True):
        resource = None
        try:
            resource = sims4.resources.load(self.resource_key)
            return resource
        except KeyError:
            if not silent_fail:
                log_name = self.filename
                logger.exception("File not found: '{}'", log_name)
            return

    def cook(self, resource):
        if not resource:
            return
        return io.BytesIO(bytes(resource))

def get_debug_name(key, table_type=None):
    logger.error('Attempting to get a debug name in a non-debug build.')
    return ''

def get_all_resources_of_type(type_id:Types):
    return sims4.resources.list(type=type_id)

def get_protobuff_for_key(key):
    if key is None:
        return
    resource_key = protocolbuffers.ResourceKey_pb2.ResourceKey()
    resource_key.type = key.type
    resource_key.group = key.group
    resource_key.instance = key.instance
    return resource_key

def get_key_from_protobuff(key_proto):
    if key_proto is None:
        return
    return Key(key_proto.type, key_proto.instance, key_proto.group)

@cached
def _get_resource_list(group, _type):
    return sims4.resources.list(group=group, type=_type)

def does_key_exist(key):
    key = sims4.resources.get_normalized_key(key)
    resource_list = _get_resource_list(key.group, key.type)
    return key in resource_list
