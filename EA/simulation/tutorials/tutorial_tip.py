from autonomy.autonomy_request import AutonomyDistanceEstimationBehavior, AutonomyPostureBehaviorfrom buffs.tunable import TunableBuffReferencefrom distributor.system import Distributorfrom drama_scheduler.drama_node_types import DramaNodeTypefrom event_testing.resolver import DoubleSimResolverfrom interactions import priorityfrom interactions.aop import AffordanceObjectPairfrom interactions.context import InteractionContext, InteractionBucketTypefrom sims4.localization import TunableLocalizedStringFactory, TunableLocalizedStringfrom sims4.tuning.tunable import TunableList, TunableReference, TunableTuple, Tunable, TunableEnumEntry, TunableSet, OptionalTunable, TunableRange, TunableResourceKey, TunableVariant, TunablePercent, TunableHouseDescription, TunablePackSafeReference, TunableEnumSetfrom sims4.tuning.tunable_base import ExportModesfrom tunable_time import TunableTimeOfDayfrom snippets import TunableAffordanceFilterSnippetfrom ui.ui_tuning import TunableUiMessageimport autonomyimport distributor.opsimport enumimport event_testingimport servicesimport sims4.localizationimport sims4.resourcesimport sims4.tuning.instancesimport tutorials.tutorial
class TutorialTipGameState(enum.Int):
    GAMESTATE_NONE = 0
    LIVE_MODE = 270579719
    BUILD_BUY = 2919482169
    CAS = 983016380
    NEIGHBORHOOD_VIEW = 3640749201
    GALLERY = 1
    TRAVEL = 238138433

class TutorialTipUiElement(enum.Int):
    UI_INVALID = 0
    GLOBAL_ESCAPE_MENU = 1
    GLOBAL_ESCAPE_MENU_BUTTON = 2
    GLOBAL_HELP_BUTTON = 3
    CAS_PERSONALITYPANEL = 100
    CAS_ASPIRATIONS = 101
    CAS_TRAITS = 102
    CAS_SIM_HEAD = 103
    CAS_SIM_BODY = 104
    CAS_OUTFIT_BUTTON = 105
    CAS_RELATIONSHIP_BUTTON = 106
    CAS_RANDOM_BUTTON = 107
    CAS_GENETICS_BUTTON = 108
    CAS_TATTOOS_BUTTON = 109
    CAS_SKIN_COLOR_MENU = 110
    CAS_GALLERY_SAVE_BUTTON = 111
    CAS_FEATURED_LOOKS_BUTTON = 112
    CAS_DETAILED_EDIT_BUTTON = 113
    CAS_PLUMBOB_BUTTON = 114
    CAS_NAME_PANEL = 115
    CAS_PRIMARY_ASPIRATION_BUTTON = 116
    CAS_ASPIRATION_GROUP_BUTTON = 117
    CAS_ASPIRATION_TRACK_BUTTON = 118
    CAS_TRAIT_GRID_BUTTON = 119
    CAS_BONUS_TRAIT_ICON = 120
    CAS_TRAIT_CATEGORY_BUTTON = 121
    CAS_OUTFIT_TYPE_BUTTON = 122
    CAS_MENU_BODY_BUTTON = 123
    CAS_MENU_FACES_BUTTON = 124
    CAS_MULTIPLE_SIMS = 125
    CAS_SKIN_DETAILS_BUTTON = 126
    CAS_GALLERY_BUTTON = 127
    CAS_GALLERY_RANDOMIZE_BUTTON = 128
    CAS_GP_MENU_CYCLE = 150
    CAS_GP_HELP_CONTROL_LAYOUT = 151
    CAS_GP_BODY_MANIPULATION = 152
    NHV_SET_HOME = 200
    NHV_WORLD_SELECT = 201
    NHV_CURRENT_LOT = 202
    NHV_OCCUPANTS = 203
    NHV_PLAY_BUTTON = 204
    NHV_MORE_BUTTON = 205
    NHV_BUILD_BUTTON = 206
    NHV_EVICT_BUTTON = 207
    NHV_MOVE_HOUSEHOLD_BUTTON = 208
    NHV_CHANGE_LOT_TYPE_BUTTON = 209
    NHV_EMPTY_LOT = 210
    NHV_MOVE_NEW_HOUSEHOLD_BUTTON = 211
    NHV_OASIS_SPRINGS_MAP = 212
    NHV_WILLOW_CREEK_SELECT = 213
    NHV_HOUSEHOLD_MANAGEMENT = 214
    NHV_EMPTY_LOT_OASIS = 215
    NHV_STARTER_WILLOW = 216
    NHV_EMPTY_LOT_MOVE_IN = 217
    NHV_CONFIRM_BUTTON = 218
    NHV_FTUE_TRAVEL_LOT = 219
    LIVE_WALL_BUTTON = 300
    LIVE_SIM_SELECTOR = 301
    LIVE_CURRENT_SIM_PORTRAIT = 302
    LIVE_TIME_CONTROLS = 303
    LIVE_INTERACTION_QUEUE = 304
    LIVE_BUILD_BUTTON = 305
    LIVE_EMOTION = 306
    LIVE_BUFF = 307
    LIVE_MOTIVE_PANEL_BUTTON = 308
    LIVE_EMOTIONAL_WHIM = 309
    LIVE_SKILL_PANEL_BUTTON = 310
    LIVE_SIMOLEON_WALLET = 311
    LIVE_CAREER_PANEL_BUTTON = 312
    LIVE_GET_JOB_BUTTON = 313
    LIVE_CAREER_GOALS = 314
    LIVE_EVENTS_UI = 315
    LIVE_EVENT_GOALS_UI = 316
    LIVE_REL_INSPECTOR = 317
    LIVE_SIM_IN_REL_INSPECTOR = 318
    LIVE_RELATIONSHIP_PANEL_BUTTON = 319
    LIVE_ASPIRATION_PANEL_BUTTON = 320
    LIVE_ASPIRATION_ICON = 321
    LIVE_SATISFACTION_STORE_BUTTON = 322
    LIVE_CHANGE_ASPIRATION_BUTTON = 323
    LIVE_SUMMARY_PANEL_BUTTON = 324
    LIVE_TRAIT_IN_PANEL = 325
    LIVE_INVENTORY_PANEL_BUTTON = 326
    LIVE_ITEM_IN_PANEL = 327
    LIVE_SKILL_LIST = 328
    LIVE_FLOOR_BUTTON = 329
    LIVE_CAREER_ADVANCEMENT = 330
    LIVE_PHONE_BUTTON = 331
    LIVE_NOTIFICATION_WALL_BUTTON = 352
    LIVE_MANAGE_WORLDS_BUTTON = 353
    LIVE_CALENDAR_BUTTON = 354
    LIVE_CLUB_PANEL_BUTTON = 355
    LIVE_VENUE_PANEL_BUTTON = 356
    LIVE_CAMERA_ADVANCED_BUTTON = 357
    LIVE_HOUSEHOLD_SIM_1 = 358
    LIVE_HOUSEHOLD_SIM_2 = 359
    LIVE_HOUSEHOLD_SIM_1_GO_HOME = 360
    LIVE_HOUSEHOLD_SIM_2_GO_HOME = 361
    LIVE_SIM_PICKER_UI = 362
    LIVE_TIME_SPEED3_CONTROL = 363
    LIVE_CLUB_MANAGER = 332
    LIVE_CLUB_MANAGER_LIST = 333
    LIVE_CLUB_PANEL = 334
    LIVE_CLUB_PANEL_CLUB_PICKER = 335
    LIVE_CLUB_PANEL_CONDUCT_RULES = 336
    LIVE_CLUB_PANEL_REWARDS = 337
    LIVE_CLUB_PANEL_START_GATHERING = 338
    LIVE_CLUB_DETAILS_PANEL = 339
    LIVE_CLUB_DETAILS_IDENTITY = 340
    LIVE_CLUB_DETAILS_ADMISSION_RULES = 341
    LIVE_CLUB_DETAILS_CLUB_MEMBERS = 342
    LIVE_CLUB_DETAILS_CONDUCT_RULES = 343
    LIVE_CLUB_ADMISSIONS_PANEL = 344
    LIVE_CLUB_ADMISSIONS_CREATION = 345
    LIVE_CLUB_ADMISSIONS_DETAILS = 346
    LIVE_CLUB_ADMISSIONS_QUALIFIERS = 347
    LIVE_CLUB_CONDUCT_PANEL = 348
    LIVE_CLUB_CONDUCT_ENCOURAGED = 349
    LIVE_CLUB_CONDUCT_ACTION = 350
    LIVE_CLUB_MANAGER_CREATE_CLUB = 351
    BB_BUILD_SORT = 400
    BB_OBJECTS_BY_ROOM = 401
    BB_OBJECTS_BY_FUNCTION = 402
    BB_SEARCH_BAR = 403
    BB_FAMILY_INVENTORY = 404
    BB_CAMERA = 405
    BB_EYEDROPPER = 406
    BB_SLEDGEHAMMER = 407
    BB_DESIGN_TOOL = 408
    BB_UNDO_REDO = 409
    BB_SHARE_LOT = 410
    BB_GALLERY_BUTTON = 411
    BB_MAGALOG_CATEGORY = 412
    BB_MAGALOG_ITEM = 413
    BB_EMPTY_ROOM = 414
    BB_NAVIGATION_HOUSE = 415
    BB_STAIRS = 416
    BB_DOOR = 417
    BB_PRODUCT_CATALOG_ITEM = 418
    BB_CAMERA_FLOOR = 419
    BB_MAGALOG_BUTTON = 420
    BB_BEDBATH_DROPDOWN = 421
    BB_BULLDOZE = 422
    BB_LOTNAME = 423
    BB_FOUNDATION_BUTTON = 424
    BB_MAGALOG_FURNISHED_ROOMS = 425
    BB_LOT_INFO = 426
    BB_PRODUCT_CATALOG_STAIRS = 427
    BB_POOL_TOOL = 428
    BB_POOL_OBJECTS = 429
    BB_GP_NOT_GALLERY_UI = 430
    GAL_GALLERY_UI = 500
    GAL_HOME_TAB = 501
    GAL_FEED_SECTION = 502
    GAL_HASHTAG_SECTION = 503
    GAL_SPOTLIGHT_SECTION = 504
    GAL_COMMUNITY_TAB = 505
    GAL_LIBRARY_TAB = 506
    GAL_FILTER_HEADER = 507
    GAL_FILTERS_PANEL = 508
    GAL_SEARCH_WIDGET = 509
    GAL_THUMBNAILS_WIDGET = 510
    GAL_INFO_PANEL = 511
    GAL_COMMENTS = 512
    GAL_SAVE_BUTTON = 513
    GAL_APPLY_BUTTON = 514
    GAL_PLAYER_PROFILE = 515
    MTX_PACK_BROWSER = 600
    MTX_PACK_BROWSER_NCAS = 601

class TutorialTipGroupRequirementType(enum.Int):
    ANY = 0
    ALL = 1

class TutorialTipDisplayOption(enum.Int):
    STANDARD = 0
    GAME_MODE = 1
    ARROW_INDICATOR = 2

class TutorialTipActorOption(enum.Int):
    ACTIVE_SIM = 0
    PLAYER_SIM = 1
    HOUSEMATE_SIM = 2

class TutorialTipTestSpecificityOption(enum.Int):
    UNSPECIFIED = 0
    ACTIVE_SIM = 1
    PLAYER_SIM = 2
    HOUSEMATE_SIM = 3

class TutorialMode(enum.Int):
    DISABLED = 0
    STANDARD = 1
    FTUE = 2

class TutorialTipSubtitleDisplayLocation(enum.Int):
    TOP = 0
    BOTTOM = 1
GROUP_NAME_DISPLAY_CRITERIA = 'Display Criteria'GROUP_NAME_ACTIONS = 'Tip Actions'GROUP_NAME_SATISFY = 'Satisfy Criteria'
class TutorialTipTuning:
    FTUE_TUNABLES = TunableTuple(description='\n        Tunables relating to the FTUE tutorial mode.\n        ', start_house_description=TunableHouseDescription(description='\n            A reference to the HouseDescription resource to load into in FTUE\n            '), ftue_aspiration_category=TunablePackSafeReference(description='\n            A reference to an aspiration category which is used in cas for the ftue flow\n            ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION_CATEGORY)), disable_ui_elements=TunableList(description='\n            Disable one or more UI elements during a phase of the tutorial, denoted by\n            the starting and ending tips.\n            ', tunable=TunableTuple(description='\n                Defines a set of UI elements to be disabled during a range of tips.\n                ', start_tip=TunablePackSafeReference(description='\n                    When this tip becomes active or is satisfied, the target elements\n                    will become disabled.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.TUTORIAL_TIP)), end_tip=TunablePackSafeReference(description='\n                    When this tip becomes active or is satisfied, the target elements\n                    will become re-enabled.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.TUTORIAL_TIP)), reason=TunableLocalizedString(description='\n                    The reason the element has been disabled, usually displayed as a tooltip.\n                    '), elements=TunableEnumSet(description='\n                    List of UI elements to disable.  Note that not all elements can be disabled.\n                    ', enum_type=TutorialTipUiElement), export_class_name='TutorialTipDisableUiElements')), export_modes=(ExportModes.ClientBinary,), export_class_name='FtueDataTuple')

class TunableTutorialTipDisplay(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(cancelable=Tunable(description='\n                If this tutorial tip can be canceled.\n                ', tunable_type=bool, default=True), text=TunableLocalizedStringFactory(description="\n                The text for this tip.\n                Token {0} is the active sim. i.e. {0.SimFirstName}\n                Token {1.String} is a 'wildcard' string to be used for things\n                like aspiration names or buff names during the tutorial.\n                Not used when display type is INDICATOR_ARROW.\n                ", allow_none=True), action_text=TunableLocalizedStringFactory(description="\n                The action the user must make for this tip to satisfy.\n                Token {0} is the active sim. i.e. {0.SimFirstName}\n                Token {1.String} is a 'wildcard' string to be used for things\n                like aspiration names or buff names during the tutorial.\n                ", allow_none=True), timeout=TunableRange(description='\n                How long, in seconds, until this tutorial tip times out.\n                ', tunable_type=int, default=1, minimum=1), ui_element=TunableEnumEntry(description='\n                The UI element associated with this tutorial tip.\n                ', tunable_type=TutorialTipUiElement, default=TutorialTipUiElement.UI_INVALID), is_modal=Tunable(description='\n                Enable if this tip should be modal.\n                Disable, if not.\n                ', tunable_type=bool, default=False), icon=TunableResourceKey(description='\n                The icon to be displayed in a modal tutorial tip.\n                If Is Modal is disabled, this field can be ignored.\n                ', resource_types=sims4.resources.CompoundTypes.IMAGE, default=None, allow_none=True), icon_console=TunableResourceKey(description='\n                The icon to be displayed in a modal tutorial tip on console.\n                If unset, will fall back to Icon.\n                If Is Modal is disabled, this field can be ignored.\n                ', resource_types=sims4.resources.CompoundTypes.IMAGE, default=None, allow_none=True, display_name='Icon (Console)', export_modes=ExportModes.ClientBinary), title=TunableLocalizedString(description='\n                The title of this tutorial tip.\n                Not used when display type is INDICATOR_ARROW.\n                ', allow_none=True), pagination_label=TunableLocalizedString(description='\n                The label of what page this tutorial tip is in within the\n                tutorial tip group.\n                Not used when display type is INDICATOR_ARROW.\n                ', allow_none=True), display_type_option=TunableEnumEntry(description='\n                The display type of this tutorial tip.\n                ', tunable_type=TutorialTipDisplayOption, default=TutorialTipDisplayOption.STANDARD), **kwargs)

class TutorialTipGroup(metaclass=sims4.tuning.instances.HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.TUTORIAL_TIP)):
    INSTANCE_TUNABLES = {'tips': TunableList(description='\n            The tips that are associated with this tip group.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.TUTORIAL_TIP), class_restrictions='TutorialTip', export_modes=ExportModes.ClientBinary)), 'group_requirement': TunableEnumEntry(description='\n            The requirement for completing this tip group. ANY means any of the\n            tips in this group need to be completed for the group to be\n            considered complete. ALL means all of the tips in this group need\n            to be completed for the group to be considered complete.\n            ', tunable_type=TutorialTipGroupRequirementType, default=TutorialTipGroupRequirementType.ALL, export_modes=ExportModes.ClientBinary)}

    def __init__(self):
        raise NotImplementedError

class TunableTutorialTipUiMessage(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(ui_message_cmn=OptionalTunable(description='\n                Sends a message to the UI for a tutorial tip.\n                ', display_name='UI Message Common', tunable=TunableUiMessage(), tuning_group=GROUP_NAME_ACTIONS, export_modes=ExportModes.ClientBinary), ui_message_ps4=OptionalTunable(description='\n                If set, overrides the ui_message_cmn to be specific to the PS4 platform\n                ', display_name='UI Message PS4 override', tunable=TunableUiMessage(), tuning_group=GROUP_NAME_ACTIONS, export_modes=ExportModes.ClientBinary), ui_message_xb1=OptionalTunable(description='\n                If set, overrides the ui_message_cmn to be specific to the XB1 platform\n                ', display_name='UI Message XboxOne override', tunable=TunableUiMessage(), tuning_group=GROUP_NAME_ACTIONS, export_modes=ExportModes.ClientBinary), **kwargs)

class TutorialTip(metaclass=sims4.tuning.instances.HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.TUTORIAL_TIP)):
    INSTANCE_TUNABLES = {'required_tip_groups': TunableList(description='\n            The Tip Groups that must be complete for this tip to be valid.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.TUTORIAL_TIP), class_restrictions='TutorialTipGroup'), tuning_group=GROUP_NAME_DISPLAY_CRITERIA, export_modes=ExportModes.ClientBinary), 'required_ui_list': TunableList(description='\n            The UI elements that are required to be present in order for this\n            tutorial tip to be valid.\n            ', tunable=TunableEnumEntry(tunable_type=TutorialTipUiElement, default=TutorialTipUiElement.UI_INVALID), tuning_group=GROUP_NAME_DISPLAY_CRITERIA, export_modes=ExportModes.ClientBinary), 'required_ui_hidden_list': TunableList(description='\n            The UI elements that are required to NOT be present in order for this\n            tutorial tip to be valid.\n            ', tunable=TunableEnumEntry(tunable_type=TutorialTipUiElement, default=TutorialTipUiElement.UI_INVALID), tuning_group=GROUP_NAME_DISPLAY_CRITERIA, export_modes=ExportModes.ClientBinary), 'required_game_state': TunableEnumEntry(description='\n            The state the game must be in for this tutorial tip to be valid.\n            ', tunable_type=TutorialTipGameState, default=TutorialTipGameState.GAMESTATE_NONE, tuning_group=GROUP_NAME_DISPLAY_CRITERIA, export_modes=ExportModes.ClientBinary), 'required_tips_not_satisfied': TunableList(description='\n            This is a list of tips that must be un-satisfied in order for this\n            tip to activate. If any tip in this list is satisfied, this tip will\n            not activate.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.TUTORIAL_TIP), class_restrictions='TutorialTip'), tuning_group=GROUP_NAME_DISPLAY_CRITERIA, export_modes=ExportModes.ClientBinary), 'platform_filter': TunableEnumEntry(description='\n            The platforms on which this tutorial tip is shown.\n            ', tunable_type=tutorials.tutorial.TutorialPlatformFilter, default=tutorials.tutorial.TutorialPlatformFilter.ALL_PLATFORMS, tuning_group=GROUP_NAME_DISPLAY_CRITERIA, export_modes=ExportModes.ClientBinary), 'required_tutorial_mode': TunableEnumEntry(description='\n            What mode this tutorial tip should be restricted to.\n            STANDARD allows this tip to be in the original / standard tutorial mode.\n            FTUE allows this tip to be in the FTUE tutorial mode.\n            DISABLED means this tip is valid in any mode.\n            ', tunable_type=TutorialMode, default=TutorialMode.STANDARD, tuning_group=GROUP_NAME_DISPLAY_CRITERIA, export_modes=ExportModes.ClientBinary), 'display': TunableTutorialTipDisplay(description='\n            This display information for this tutorial tip.\n            ', tuning_group=GROUP_NAME_ACTIONS, export_modes=ExportModes.ClientBinary), 'display_narration': OptionalTunable(description='\n            Optionally play narration voice-over and display subtitles.\n            ', tunable=TunableTuple(voiceover_audio=TunableResourceKey(description='\n                    Narration audio to play.\n                    ', default=None, allow_none=True, resource_types=(sims4.resources.Types.PROPX,)), voiceover_audio_ps4=TunableResourceKey(description='\n                    Narration audio to play specific to PS4.\n                    ', default=None, allow_none=True, resource_types=(sims4.resources.Types.PROPX,)), voiceover_audio_xb1=TunableResourceKey(description='\n                    Narration audio to play specific to XB1.\n                    ', default=None, allow_none=True, resource_types=(sims4.resources.Types.PROPX,)), subtitle_text=TunableLocalizedString(description='\n                    Subtitles to display while audio narration is playing.\n                    '), subtitle_display_location=TunableVariant(description='\n                    What area on the screen the subtitles should appear.\n                    Top    - Use the generic top-of-screen position.\n                    Bottom - Use the generic bottom-of-screen position.\n                    Custom - Specify a custom position in terms of % vertically.\n                    ', location=TunableEnumEntry(description='\n                        Semantic location (UX-defined) for where the subtitles should appear.\n                        ', tunable_type=TutorialTipSubtitleDisplayLocation, default=TutorialTipSubtitleDisplayLocation.BOTTOM), custom=TunablePercent(description='\n                        Vertical position for the subtitles, expressed as a\n                        percentage of the height of the screen.\n                        ', default=90), default='location'), satisfy_when_voiceover_finished=Tunable(description='\n                    If set, the tutorial tip will be marked as satisfied when the\n                    voiceover completes or is interrupted.\n                    ', tunable_type=bool, default=False), delay_satisfaction_until_voiceover_finished=Tunable(description='\n                    If set, the tutorial tip will not be marked satisfied until after\n                    the voiceover completes, preventing the voiceover from being\n                    interrupted by external satisfaction.\n                    ', tunable_type=bool, default=False), keep_subtitle_visible_until_satisfaction=Tunable(description='\n                    If set, the subtitle will remain visible until the tutorial tip is\n                    marked as satisfied, even though the voiceover may have finished.\n                    ', tunable_type=bool, default=False), export_class_name='TutorialTipNarrationDisplay'), tuning_group=GROUP_NAME_ACTIONS, export_modes=ExportModes.ClientBinary), 'activation_ui_message': TunableTutorialTipUiMessage(description='\n            Sends a message to the UI when this tip is activated.\n            ', tuning_group=GROUP_NAME_ACTIONS, export_modes=ExportModes.ClientBinary), 'deactivation_ui_message': TunableTutorialTipUiMessage(description='\n            Sends a message to the UI when this tip is deactivated.\n            ', tuning_group=GROUP_NAME_ACTIONS, export_modes=ExportModes.ClientBinary), 'buffs': TunableList(description='\n            Buffs that will be applied at the start of this tutorial tip.\n            ', tunable=TunableBuffReference(), tuning_group=GROUP_NAME_ACTIONS), 'buffs_removed_on_deactivate': Tunable(description='\n            If enabled, this tip will remove those buffs on deactivate.\n            ', tunable_type=bool, default=False, tuning_group=GROUP_NAME_ACTIONS), 'commodities_to_solve': TunableSet(description="\n            A set of commodities we will attempt to solve. This will result in\n            the Sim's interaction queue being filled with various interactions.\n            ", tunable=TunableReference(services.statistic_manager()), tuning_group=GROUP_NAME_ACTIONS), 'gameplay_loots': OptionalTunable(description='\n            Loots that will be given at the start of this tip.\n            Actor is is the sim specified by Sim Actor.\n            Target is the sim specified by Sim Target.\n            ', tunable=TunableList(tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), tuning_group=GROUP_NAME_ACTIONS), 'restricted_affordances': OptionalTunable(description='\n            If enabled, use the filter to determine which affordances are allowed.\n            ', tunable=TunableTuple(visible_affordances=TunableAffordanceFilterSnippet(description='\n                    The filter of affordances that are visible.\n                    '), tooltip=OptionalTunable(description='\n                    Tooltip when interaction is disabled by tutorial restrictions\n                    If not specified, will use the default in the tutorial service\n                    tuning.\n                    ', tunable=sims4.localization.TunableLocalizedStringFactory()), enabled_affordances=TunableAffordanceFilterSnippet(description='\n                    The filter of visible affordances that are enabled.\n                    ')), tuning_group=GROUP_NAME_ACTIONS), 'call_to_actions': OptionalTunable(description='\n            Call to actions that should persist for the duration of this tip.\n            ', tunable=TunableList(tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.CALL_TO_ACTION), pack_safe=True)), tuning_group=GROUP_NAME_ACTIONS), 'end_drama_node': Tunable(description='\n            If enabled, this tip will end the tutorial drama node.\n            ', tunable_type=bool, default=False, tuning_group=GROUP_NAME_ACTIONS), 'sim_actor': TunableEnumEntry(description="\n            The entity who will be the actor sim for loot, and will\n            receive the items that aren't specified via loots.\n            \n            If there is no Tutorial Drama Node active, actor will be active\n            sim\n            ", tunable_type=TutorialTipActorOption, default=TutorialTipActorOption.ACTIVE_SIM, tuning_group=GROUP_NAME_ACTIONS), 'sim_target': TunableEnumEntry(description='\n            The entity who will be the target sim for loot\n            \n            If there is no Tutorial Drama Node active, target sim will be active\n            sim.\n            ', tunable_type=TutorialTipActorOption, default=TutorialTipActorOption.ACTIVE_SIM, tuning_group=GROUP_NAME_ACTIONS), 'add_target_to_actor_household': Tunable(description='\n            If enabled, target sim will be added to active sim household.\n            ', tunable_type=bool, default=False, tuning_group=GROUP_NAME_ACTIONS), 'make_housemate_unselectable': Tunable(description='\n            If enabled, housemate will be unselectable for the duration of the\n            tooltip.\n            ', tunable_type=bool, default=False, tuning_group=GROUP_NAME_ACTIONS), 'timeout_satisfies': Tunable(description='\n            If enabled, this tip is satisfied when the timeout is reached.\n            If disabled, this tip will not satisfy when the timeout is reached.\n            ', tunable_type=bool, default=False, tuning_group=GROUP_NAME_SATISFY, export_modes=ExportModes.ClientBinary), 'gameplay_test': OptionalTunable(description='\n            Tests that, if passed, will satisfy this tutorial tip.\n            Only one test needs to pass to satisfy. These are intended for tips\n            where the satisfy message should be tested and sent at a later time.\n            ', tunable=tutorials.tutorial.TunableTutorialTestVariant(), tuning_group=GROUP_NAME_SATISFY, export_modes=ExportModes.All), 'sim_tested': TunableEnumEntry(description='\n            The entity who must fulfill the test events.\n            \n            If there is no Tutorial Drama Node, player sim and housemate sim will be active\n            sim.\n            ', tunable_type=TutorialTipTestSpecificityOption, default=TutorialTipTestSpecificityOption.UNSPECIFIED, tuning_group=GROUP_NAME_SATISFY), 'time_of_day': OptionalTunable(description='\n            If specified, tutorialtip will be satisfied once the time passes \n            the specified time.\n            ', tunable=TunableTimeOfDay(), tuning_group=GROUP_NAME_SATISFY), 'gameplay_immediate_test': OptionalTunable(description='\n            Tests that, if passed, will satisfy this tutorial tip.\n            Only one test needs to pass to satisfy. These are intended for tips\n            where the satisfy message should be tested and sent back immediately.\n            ', tunable=tutorials.tutorial.TunableTutorialTestVariant(), tuning_group=GROUP_NAME_SATISFY, export_modes=ExportModes.All), 'satisfy_on_active_sim_change': Tunable(description='\n            If enabled, this tip is satisfied when the active sim changes\n            ', tunable_type=bool, default=False, tuning_group=GROUP_NAME_SATISFY, export_modes=ExportModes.All), 'satisfy_on_activate': Tunable(description="\n            If enabled, this tip is satisfied immediately when all of it's\n            preconditions have been met.\n            ", tunable_type=bool, default=False, tuning_group=GROUP_NAME_SATISFY, export_modes=ExportModes.ClientBinary), 'tutorial_group_to_complete_on_skip': TunableReference(description='\n            The tutorial group who will have all tutorial tips within it\n            completed when the button to skip all is pressed from this tip.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TUTORIAL_TIP), class_restrictions='TutorialTipGroup', export_modes=ExportModes.ClientBinary)}

    def __init__(self):
        raise NotImplementedError

    @classmethod
    def activate(cls):
        tutorial_service = services.get_tutorial_service()
        client = services.client_manager().get_first_client()
        actor_sim_info = client.active_sim.sim_info
        target_sim_info = actor_sim_info
        housemate_sim_info = None
        tutorial_drama_node = None
        drama_scheduler = services.drama_scheduler_service()
        if drama_scheduler is not None:
            drama_nodes = drama_scheduler.get_running_nodes_by_drama_node_type(DramaNodeType.TUTORIAL)
            if drama_nodes:
                tutorial_drama_node = drama_nodes[0]
                housemate_sim_info = tutorial_drama_node.get_housemate_sim_info()
                player_sim_info = tutorial_drama_node.get_player_sim_info()
                if cls.sim_actor == TutorialTipActorOption.PLAYER_SIM:
                    actor_sim_info = player_sim_info
                elif cls.sim_actor == TutorialTipActorOption.HOUSEMATE_SIM:
                    actor_sim_info = housemate_sim_info
                if cls.sim_target == TutorialTipActorOption.PLAYER_SIM:
                    target_sim_info = player_sim_info
                elif cls.sim_target == TutorialTipActorOption.HOUSEMATE_SIM:
                    target_sim_info = housemate_sim_info
        if cls.gameplay_immediate_test is not None:
            resolver = event_testing.resolver.SingleSimResolver(actor_sim_info)
            if resolver(cls.gameplay_immediate_test):
                cls.satisfy()
            else:
                return
        for buff_ref in cls.buffs:
            actor_sim_info.add_buff_from_op(buff_ref.buff_type, buff_reason=buff_ref.buff_reason)
        if cls.gameplay_test is not None:
            services.get_event_manager().register_tests(cls, [cls.gameplay_test])
        if cls.satisfy_on_active_sim_change:
            client = services.client_manager().get_first_client()
            if client is not None:
                client.register_active_sim_changed(cls._on_active_sim_change)
        if cls.commodities_to_solve:
            actor_sim = actor_sim_info.get_sim_instance()
            if actor_sim is not None:
                context = InteractionContext(actor_sim, InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT, priority.Priority.High, bucket=InteractionBucketType.DEFAULT)
                for commodity in cls.commodities_to_solve:
                    if not actor_sim.queue.can_queue_visible_interaction():
                        break
                    autonomy_request = autonomy.autonomy_request.AutonomyRequest(actor_sim, autonomy_mode=autonomy.autonomy_modes.FullAutonomy, commodity_list=(commodity,), context=context, consider_scores_of_zero=True, posture_behavior=AutonomyPostureBehavior.IGNORE_SI_STATE, distance_estimation_behavior=AutonomyDistanceEstimationBehavior.ALLOW_UNREACHABLE_LOCATIONS, allow_opportunity_cost=False, autonomy_mode_label_override='Tutorial')
                    selected_interaction = services.autonomy_service().find_best_action(autonomy_request)
                    AffordanceObjectPair.execute_interaction(selected_interaction)
        if cls.gameplay_loots:
            resolver = DoubleSimResolver(actor_sim_info, target_sim_info)
            for loot_action in cls.gameplay_loots:
                loot_action.apply_to_resolver(resolver)
        if cls.restricted_affordances is not None and tutorial_service is not None:
            tutorial_service.set_restricted_affordances(cls.restricted_affordances.visible_affordances, cls.restricted_affordances.tooltip, cls.restricted_affordances.enabled_affordances)
        if cls.call_to_actions is not None:
            call_to_action_service = services.call_to_action_service()
            for call_to_action_fact in cls.call_to_actions:
                call_to_action_service.begin(call_to_action_fact, None)
        if cls.add_target_to_actor_household:
            household_manager = services.household_manager()
            household_manager.switch_sim_household(target_sim_info)
        if cls.make_housemate_unselectable and tutorial_service is not None:
            tutorial_service.set_unselectable_sim(housemate_sim_info)
        if cls.end_drama_node and tutorial_drama_node is not None:
            tutorial_drama_node.end()
        if cls.time_of_day is not None and tutorial_service is not None:
            tutorial_service.add_tutorial_alarm(cls, lambda _: cls.satisfy(), cls.time_of_day)

    @classmethod
    def _on_active_sim_change(cls, old_sim, new_sim):
        cls.satisfy()

    @classmethod
    def handle_event(cls, sim_info, event, resolver):
        if cls.gameplay_test is not None and resolver(cls.gameplay_test):
            if cls.sim_tested != TutorialTipTestSpecificityOption.UNSPECIFIED:
                client = services.client_manager().get_first_client()
                test_sim_info = client.active_sim.sim_info
                drama_scheduler = services.drama_scheduler_service()
                if drama_scheduler is not None:
                    drama_nodes = drama_scheduler.get_running_nodes_by_drama_node_type(DramaNodeType.TUTORIAL)
                    if drama_nodes:
                        drama_node = drama_nodes[0]
                        if cls.sim_tested == TutorialTipTestSpecificityOption.PLAYER_SIM:
                            test_sim_info = drama_node.get_player_sim_info()
                        elif cls.sim_tested == TutorialTipTestSpecificityOption.HOUSEMATE_SIM:
                            test_sim_info = drama_node.get_housemate_sim_info()
                if test_sim_info is not sim_info:
                    return
            cls.satisfy()

    @classmethod
    def satisfy(cls):
        op = distributor.ops.SetTutorialTipSatisfy(cls.guid64)
        distributor_instance = Distributor.instance()
        distributor_instance.add_op_with_no_owner(op)

    @classmethod
    def deactivate(cls):
        tutorial_service = services.get_tutorial_service()
        client = services.client_manager().get_first_client()
        if cls.gameplay_test is not None:
            services.get_event_manager().unregister_tests(cls, (cls.gameplay_test,))
        if cls.satisfy_on_active_sim_change and client is not None:
            client.unregister_active_sim_changed(cls._on_active_sim_change)
        if cls.restricted_affordances is not None and tutorial_service is not None:
            tutorial_service.clear_restricted_affordances()
        if cls.call_to_actions is not None:
            call_to_action_service = services.call_to_action_service()
            for call_to_action_fact in cls.call_to_actions:
                call_to_action_service.end(call_to_action_fact)
        if cls.buffs_removed_on_deactivate:
            actor_sim_info = None
            if client is not None:
                actor_sim_info = client.active_sim.sim_info
            drama_scheduler = services.drama_scheduler_service()
            if drama_scheduler is not None:
                drama_nodes = drama_scheduler.get_running_nodes_by_drama_node_type(DramaNodeType.TUTORIAL)
                if drama_nodes:
                    tutorial_drama_node = drama_nodes[0]
                    if cls.sim_actor == TutorialTipActorOption.PLAYER_SIM:
                        actor_sim_info = tutorial_drama_node.get_player_sim_info()
                    elif cls.sim_actor == TutorialTipActorOption.HOUSEMATE_SIM:
                        actor_sim_info = tutorial_drama_node.get_housemate_sim_info()
            if actor_sim_info is not None:
                for buff_ref in cls.buffs:
                    actor_sim_info.remove_buff_by_type(buff_ref.buff_type)
        if cls.time_of_day is not None and tutorial_service is not None:
            tutorial_service.remove_tutorial_alarm(cls)
        if cls.make_housemate_unselectable and tutorial_service is not None:
            tutorial_service.set_unselectable_sim(None)
