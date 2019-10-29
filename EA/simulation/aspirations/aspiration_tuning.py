from aspirations.aspiration_types import AspriationTypefrom event_testing import objective_tuningfrom event_testing.milestone import Milestonefrom event_testing.resolver import SingleSimResolver, GlobalResolverfrom interactions.utils.display_mixin import get_display_mixinfrom interactions.utils.loot import LootActionsfrom traits.traits import Traitfrom sims import genealogy_trackerfrom sims4.tuning.instances import HashedTunedInstanceMetaclass, lock_instance_tunablesfrom sims4.tuning.tunable import TunableEnumEntry, TunableSet, OptionalTunable, TunableReferencefrom sims4.tuning.tunable_base import GroupNames, SourceQueriesfrom sims4.utils import classproperty, constpropertyfrom singletons import DEFAULTfrom ui.ui_dialog import UiDialogResponsefrom ui.ui_dialog_notification import UiDialogNotificationimport enumimport server.online_testsimport servicesimport sims4.localizationimport sims4.logimport sims4.tuning.tunableimport ui.screen_slamlogger = sims4.log.Logger('AspirationTuning')
class AspirationBasic(Milestone, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION)):
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'do_not_register_events_on_load': sims4.tuning.tunable.Tunable(description='\n            If checked we will not register these events on load.\n            \n            This should be checked for all aspirations that are part of an\n            aspiration track.\n            ', tunable_type=bool, default=False), 'screen_slam': OptionalTunable(description='\n            Which screen slam to show when this aspiration is complete.\n            Localization Tokens: Sim - {0.SimFirstName}, Milestone Name - \n            {1.String}, Aspiration Track Name - {2.String}\n            ', tunable=ui.screen_slam.TunableScreenSlamSnippet(), tuning_group=GroupNames.UI)}

    @classmethod
    def handle_event(cls, sim_info, event, resolver):
        if sim_info is not None and sim_info.aspiration_tracker is not None:
            sim_info.aspiration_tracker.handle_event(cls, event, resolver)

    @constproperty
    def aspiration_type():
        return AspriationType.BASIC

    @classmethod
    def register_callbacks(cls):
        tests = [objective.objective_test for objective in cls.objectives]
        services.get_event_manager().register_tests(cls, tests)

    @classmethod
    def setup_aspiration(cls, event_data_tracker):
        for objective in cls.objectives:
            objective.setup_objective(event_data_tracker, cls)

    @classmethod
    def cleanup_aspiration(cls, event_data_tracker):
        for objective in cls.objectives:
            objective.cleanup_objective(event_data_tracker, cls)

    @classmethod
    def unregister_callbacks(cls):
        tests = [objective.objective_test for objective in cls.objectives]
        services.get_event_manager().unregister_tests(cls, tests)

    @classmethod
    def apply_on_complete_loot_actions(cls, sim_info):
        pass

    @constproperty
    def update_on_load():
        return True

class Aspiration(AspirationBasic):
    INSTANCE_TUNABLES = {'display_name': sims4.localization.TunableLocalizedString(description='\n            Display name for this aspiration\n            ', allow_none=True, export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'descriptive_text': sims4.localization.TunableLocalizedString(description='\n            Description for this aspiration\n            ', allow_none=True, export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'is_child_aspiration': sims4.tuning.tunable.Tunable(description='\n            If checked then this aspiration can only be completed by a child\n            Sim and will not be considered complete even if all of the\n            Objectives are complete as a non-child.\n            ', tunable_type=bool, default=False, export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.SPECIAL_CASES), 'reward': sims4.tuning.tunable.TunableReference(description='\n            The reward given when this Aspiration is completed.\n            ', manager=services.get_instance_manager(sims4.resources.Types.REWARD), allow_none=True, tuning_group=GroupNames.REWARDS), 'on_complete_loot_actions': sims4.tuning.tunable.TunableList(description='\n           List of loots operations that will be awarded when this aspiration\n           completes.\n           ', tunable=LootActions.TunableReference(), tuning_group=GroupNames.REWARDS)}

    @constproperty
    def aspiration_type():
        return AspriationType.FULL_ASPIRATION

    @classmethod
    def _verify_tuning_callback(cls):
        for objective in cls.objectives:
            pass
        logger.debug('Loading asset: {0}', cls)

    @classmethod
    def apply_on_complete_loot_actions(cls, sim_info):
        resolver = SingleSimResolver(sim_info)
        for loot_action in cls.on_complete_loot_actions:
            loot_action.apply_to_resolver(resolver)

class AspirationSimInfoPanel(AspirationBasic):
    INSTANCE_TUNABLES = {'display_name': sims4.localization.TunableLocalizedString(description='\n            Display name for this aspiration.\n            ', allow_none=True, export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'descriptive_text': sims4.localization.TunableLocalizedString(description='\n            Description for this aspiration.\n            ', allow_none=True, export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'category': sims4.tuning.tunable.TunableReference(description='\n            The category that this Sim Info Panel Aspiration goes into within\n            the Sim Info Panel.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION_CATEGORY), export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI)}

    @constproperty
    def aspiration_type():
        return AspriationType.SIM_INFO_PANEL

    @classmethod
    def _verify_tuning_callback(cls):
        for objective in cls.objectives:
            pass
lock_instance_tunables(AspirationSimInfoPanel, do_not_register_events_on_load=False)
class AspirationNotification(AspirationBasic):
    INSTANCE_TUNABLES = {'objectives': sims4.tuning.tunable.TunableList(description='\n            A list of all of the Objectives that will be tracked in order for\n            this Milestone to be completed.  Using the Objective Completion Type\n            we will determine the action number of Objectives that need to be\n            completed.\n            ', tunable=sims4.tuning.tunable.TunableReference(description='\n                An Objective that is one of the requirements for this Milestone\n                to be completed.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECTIVE)), tuning_group=GroupNames.CORE), 'notification': UiDialogNotification.TunableFactory(description='\n            A TNS that will appear when this Aspiration is completed.\n            ', tuning_group=GroupNames.UI)}

    @constproperty
    def aspiration_type():
        return AspriationType.NOTIFICATION
lock_instance_tunables(AspirationNotification, do_not_register_events_on_load=False)AspirationCareerDisplayMixin = get_display_mixin(use_string_tokens=True, has_description=True, has_icon=True, has_tooltip=True)
class AspirationCareer(AspirationCareerDisplayMixin, AspirationBasic):

    def reward(self, *args, **kwargs):
        pass

    @constproperty
    def aspiration_type():
        return AspriationType.CAREER

    @classmethod
    def _verify_tuning_callback(cls):
        for objective in cls.objectives:
            pass
lock_instance_tunables(AspirationCareer, do_not_register_events_on_load=True)
class AspirationAssignment(AspirationBasic):

    def reward(self, *args, **kwargs):
        pass

    @classmethod
    def satisfy_assignment(cls, sim_info):
        current_career = sim_info.career_tracker.get_on_assignment_career()
        if current_career is None:
            return
        if cls not in current_career.active_assignments:
            return
        current_career.handle_assignment_loot()

    @classmethod
    def send_assignment_update(cls, sim_info):
        current_career = sim_info.career_tracker.get_on_assignment_career()
        if current_career is None:
            return
        if cls not in current_career.active_assignments:
            return
        current_career.resend_at_work_info()
        current_career.send_assignment_update()

    @constproperty
    def aspiration_type():
        return AspriationType.ASSIGNMENT

    @classmethod
    def _verify_tuning_callback(cls):
        for objective in cls.objectives:
            pass
lock_instance_tunables(AspirationAssignment, do_not_register_events_on_load=True)
class AspirationGig(AspirationBasic):

    def reward(self, *args, **kwargs):
        pass

    @classmethod
    def satisfy_assignment(cls, sim_info):
        for career in sim_info.career_tracker:
            career.gig_aspiration_completed(cls)

    @classmethod
    def send_assignment_update(cls, sim_info):
        pass

    @constproperty
    def aspiration_type():
        return AspriationType.GIG

    @classmethod
    def _verify_tuning_callback(cls):
        for objective in cls.objectives:
            pass
lock_instance_tunables(AspirationGig, do_not_register_events_on_load=True)
class AspirationFamilialTrigger(AspirationBasic):
    INSTANCE_TUNABLES = {'objectives': sims4.tuning.tunable.TunableList(description='\n            A list of all of the Objectives that will be tracked in order for\n            this Milestone to be completed.  Using the Objective Completion Type\n            we will determine the action number of Objectives that need to be\n            completed.\n            ', tunable=sims4.tuning.tunable.TunableReference(description='\n                An Objective that is one of the requirements for this Milestone\n                to be completed.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECTIVE)), tuning_group=GroupNames.CORE), 'target_family_relationships': TunableSet(description='\n            The genetic relationships that will be notified when this\n            Aspiration is completed.\n            ', tunable=TunableEnumEntry(description='\n                A genetic relationship that will be notified when this\n                Aspiraiton is completed.\n                ', tunable_type=genealogy_tracker.FamilyRelationshipIndex, default=genealogy_tracker.FamilyRelationshipIndex.FATHER), tuning_group=GroupNames.CORE)}

    @constproperty
    def aspiration_type():
        return AspriationType.FAMILIAL

    @classmethod
    def _verify_tuning_callback(cls):
        for objective in cls.objectives:
            pass
lock_instance_tunables(AspirationFamilialTrigger, do_not_register_events_on_load=False)
class AspirationCategory(metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION_CATEGORY)):
    INSTANCE_TUNABLES = {'display_text': sims4.localization.TunableLocalizedString(description="\n            The Aspiration Category's name within the UI.\n            ", export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'ui_sort_order': sims4.tuning.tunable.Tunable(description='\n            Order in which this category is sorted against other categories in\n            the UI.  If two categories share the same sort order, undefined\n            behavior will ensue.\n            ', tunable_type=int, default=0, export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'icon': sims4.tuning.tunable.TunableResourceKey(description='\n            The icon to be displayed in the panel view.\n            ', default=None, resource_types=sims4.resources.CompoundTypes.IMAGE, allow_none=True, export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'is_sim_info_panel': sims4.tuning.tunable.Tunable(description='\n            If checked then this Category will be marked for the Sim Info panel\n            rather than for the Aspiration panel.\n            ', tunable_type=bool, default=False, export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'used_by_packs': sims4.tuning.tunable.TunableEnumSet(description='\n            Optional set of packs which utilize this category.  Used for\n            excluding categories from the UI if their tuning resides in base\n            game. (It is preferred to place category tuning in the appropriate\n            pack, if possible.)\n            ', enum_type=sims4.common.Pack, enum_default=sims4.common.Pack.BASE_GAME, export_modes=sims4.tuning.tunable_base.ExportModes.ClientBinary, tuning_group=GroupNames.UI)}

class AspirationTrackLevels(enum.Int):
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4
    LEVEL_5 = 5
    LEVEL_6 = 6
TRACK_LEVEL_MAX = 6
class TunableHiddenTrackTestVariant(sims4.tuning.tunable.TunableVariant):

    def __init__(self, description='A tunable test supporting hidden aspiration testing', **kwargs):
        super().__init__(is_live_event_active=server.online_tests.IsLiveEventActive.TunableFactory(), description=description, **kwargs)

class AspirationTrack(metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION_TRACK)):
    INSTANCE_TUNABLES = {'display_text': sims4.localization.TunableLocalizedString(description="\n            The Aspiration Track's name.\n            ", export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'description_text': sims4.localization.TunableLocalizedString(description="\n            The Aspiration Track's description.\n            ", export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'icon': sims4.tuning.tunable.TunableResourceKey(description="\n            The Aspiration Track's icon.\n            ", default=None, resource_types=sims4.resources.CompoundTypes.IMAGE, export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'icon_high_res': sims4.tuning.tunable.TunableResourceKey(description="\n            The icon to be displayed in aspiration track selection.\n            The Aspiration Track's icon for display when selecting a track.\n            ", default=None, resource_types=sims4.resources.CompoundTypes.IMAGE, allow_none=True, export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'category': sims4.tuning.tunable.TunableReference(description='\n            The Aspiration Category that this Aspiration Track is a part of.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION_CATEGORY), export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'primary_trait': sims4.tuning.tunable.TunableReference(description='\n            A trait that is given to Sims if this is the Aspiration Track that\n            was selected for the Sim when they exited CAS for the first time or\n            is the initial Aspiration Track selected when the Sim ages up from\n            a child. \n            ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), export_modes=sims4.tuning.tunable_base.ExportModes.All, allow_none=True, tuning_group=GroupNames.CORE), 'aspirations': sims4.tuning.tunable.TunableMapping(description='\n            A mapping between the Aspiration Track Level and the Aspiration\n            to be completed.  The Aspirations will need to be completed in\n            order and upon the final one being complete will have this\n            Aspiration Track be considered complete.\n            ', key_type=TunableEnumEntry(description='\n                The Level within the Aspiration Track that this Aspiration\n                lives.\n                ', tunable_type=AspirationTrackLevels, default=AspirationTrackLevels.LEVEL_1), value_type=sims4.tuning.tunable.TunableReference(description='\n                The Aspiration within the track that is associated with this\n                level.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='Aspiration', reload_dependent=True), tuple_name='AspirationsMappingTuple', minlength=1, export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.CORE), 'reward': sims4.tuning.tunable.TunableReference(description='\n            The rewards that are given when a Sim completes this Aspiration\n            Track.\n            ', manager=services.get_instance_manager(sims4.resources.Types.REWARD), export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.REWARDS), 'notification': UiDialogNotification.TunableFactory(description='\n            A TNS that will be displayed with the Aspiration Track is\n            completed.\n            ', locked_args={'text_tokens': DEFAULT, 'icon': None, 'primary_icon_response': UiDialogResponse(text=None, ui_request=UiDialogResponse.UiDialogUiRequest.SHOW_ASPIRATION_SELECTOR), 'secondary_icon': None}, tuning_group=GroupNames.UI), 'mood_asm_param': sims4.tuning.tunable.Tunable(description="\n            The asm parameter for Sim's mood for use with CAS ASM state\n            machine, driven by selection of this AspirationTrack, i.e. when a\n            player selects the a romantic aspiration track, the Flirty ASM is\n            given to the state machine to play. The name tuned here must match\n            the animation state name parameter expected in Swing.\n            ", tunable_type=str, default=None, source_query=SourceQueries.SwingEnumNamePattern.format('mood'), export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'is_hidden_unlockable': sims4.tuning.tunable.Tunable(description='\n            If True, this track will be initially hidden until unlocked\n            during gameplay.\n            Note: It will never be able to be selected in CAS, even\n            if it has been unlocked.\n            ', tunable_type=bool, default=False, export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.UI), 'override_traits': sims4.tuning.tunable.TunableSet(description='\n            Traits that are applied to the sim when they select this\n            aspiration. Overrides any traits that are on the sim when the\n            aspiration is selected. This is used for FTUE aspirations.\n            ', tunable=Trait.TunableReference(pack_safe=True), export_modes=sims4.tuning.tunable_base.ExportModes.All, tuning_group=GroupNames.SPECIAL_CASES), 'whim_set': OptionalTunable(description='\n            If enabled then this Aspiration Track will give a Whim Set when it\n            is active.\n            ', tunable=TunableReference(description='\n                A Whim Set that is active when this Aspiration Track is active.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions=('ObjectivelessWhimSet',)), tuning_group=GroupNames.CORE), 'is_hidden_unlocked_tests': sims4.tuning.tunable.TunableList(description='\n            All tests must pass for this track to remain\n            unlocked on load.  This does NOT unlock it.\n            \n            Uses GlobalResolver\n            ', tunable=TunableHiddenTrackTestVariant(), tuning_group=GroupNames.SPECIAL_CASES)}
    _sorted_aspirations = None

    @classmethod
    def get_aspirations(cls):
        return cls._sorted_aspirations

    @classmethod
    def get_next_aspriation(cls, current_aspiration):
        next_aspiration_level = None
        current_aspiration_guid = current_aspiration.guid64
        for (level, track_aspiration) in cls.aspirations.items():
            if track_aspiration.guid64 == current_aspiration_guid:
                next_aspiration_level = int(level) + 1
                break
        if next_aspiration_level in cls.aspirations:
            return cls.aspirations[next_aspiration_level]

    @classmethod
    def is_available(cls):
        if not cls.is_hidden_unlockable:
            return True
        resolver = GlobalResolver()
        for test in cls.is_hidden_unlocked_tests:
            if not resolver(test):
                return False
        return True

    @classproperty
    def is_child_aspiration_track(cls):
        return cls._sorted_aspirations[0][1].is_child_aspiration

    @classmethod
    def _tuning_loaded_callback(cls):
        cls._sorted_aspirations = tuple(sorted(cls.aspirations.items()))

    @classmethod
    def _verify_tuning_callback(cls):
        aspiration_list = cls.aspirations.values()
        aspiration_set = set(aspiration_list)
        if len(aspiration_set) != len(aspiration_list):
            logger.error('{} Aspiration Track has repeating aspiration values in the aspiration map.', cls, owner='ddriscoll')
