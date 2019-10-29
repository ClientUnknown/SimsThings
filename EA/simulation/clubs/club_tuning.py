import weakreffrom broadcasters.broadcaster import Broadcasterfrom broadcasters.broadcaster_effect import BroadcasterEffectLootfrom broadcasters.broadcaster_utils import BroadcasterClockTypefrom bucks.bucks_enums import BucksTypefrom buffs.tunable import TunableBuffReferencefrom careers.career_tuning import Careerfrom clubs import UnavailableClubCriteriaErrorfrom clubs.club_enums import ClubRuleEncouragementStatus, ClubHangoutSetting, ClubOutfitSettingfrom clubs.club_sim_picker_dialog import UiClubSimPickerfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.results import TestResultfrom fame.fame_tuning import FameTunablesfrom filters.tunable import DynamicSimFilterfrom interactions import ParticipantTypefrom interactions.base import super_interactionfrom interactions.base.super_interaction import SuperInteractionfrom interactions.social.social_mixer_interaction import SocialMixerInteractionfrom interactions.social.social_super_interaction import SocialSuperInteractionfrom interactions.utils.loot import LootActionsfrom interactions.utils.tunable_icon import TunableIcon, TunableIconAllPacksfrom objects.terrain import TravelSuperInteractionfrom scheduler import WeeklySchedulefrom server.pick_info import PickTypefrom sims.aging.aging_tuning import AgingTuningfrom sims.sim_info_types import Age, Speciesfrom sims4.localization import TunableLocalizedString, TunableLocalizedStringFactoryVariantfrom sims4.tuning.dynamic_enum import DynamicEnumLockedfrom sims4.tuning.instances import TunedInstanceMetaclass, lock_instance_tunablesfrom sims4.tuning.tunable import Tunable, TunableRange, TunableSet, TunableReference, TunableMapping, TunableEnumEntry, TunableTuple, TunableInterval, HasTunableFactory, AutoFactoryInit, TunableEnumSet, TunableVariant, OptionalTunable, TunablePackSafeReference, TunablePackSafeResourceKey, TunableSimMinute, TunableList, HasTunableSingletonFactory, TunableLotDescriptionfrom sims4.tuning.tunable_base import GroupNames, ExportModesfrom sims4.utils import flexmethodfrom singletons import DEFAULTfrom snippets import TunableAffordanceListReferencefrom statistics.skill import Skillfrom tag import Tagfrom traits.traits import Traitfrom ui.ui_dialog import UiDialogOkCancel, UiDialogOkfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetfrom world.lot import get_lot_id_from_instance_idimport bucksimport enumimport event_testingimport servicesimport sims4.logimport snippetslogger = sims4.log.Logger('Clubs', default_owner='tastle')CRITERIA_CLUB_MEMBERS = 'club_members'CRITERIA_NON_MEMBERS = 'non_members'MAX_CLUB_RULES = 10MAX_MEMBERSHIP_CRITERIA = 5
class ClubInteractionGroupCategory(enum.Int):
    OTHER = 0
    SOCIAL = 1
    SKILL = 2
    OBJECT = 3
    ART_AND_MUSIC = 4
    FOOD_AND_DRINK = 5
    FUN_AND_GAMES = 6
    HOBBIES = 7
    HOME_ACTIVITIES = 8
    KID_ACTIVITIES = 9
    MISCHIEF_AND_MAYHEM = 10
    OUTDOOR = 11

class HouseholdValueCategory(enum.Int):
    POOR = 0
    AVERAGE = 1
    RICH = 2

class MaritalStatus(enum.Int):
    MARRIED = 0
    UNMARRIED = 1

class FameRank(DynamicEnumLocked):
    FAME_RANK_1 = 1
    FAME_RANK_2 = 2
    FAME_RANK_3 = 3
    FAME_RANK_4 = 4
    FAME_RANK_5 = 5

class ClubCriteriaCategory(enum.Int, export=False):
    SKILL = 0
    TRAIT = 1
    RELATIONSHIP = 2
    CAREER = 3
    HOUSEHOLD_VALUE = 4
    AGE = 5
    CLUB_MEMBERSHIP = 6
    FAME_RANK = 7

class ClubInteractionMixin:

    def __init__(self, *args, associated_club=None, **kwargs):
        super().__init__(*args, associated_club=associated_club, **kwargs)
        self.associated_club = associated_club

    @flexmethod
    def test(cls, inst, associated_club=DEFAULT, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        club_service = services.get_club_service()
        if club_service is None:
            return TestResult(False, 'There is no Club Service')
        associated_club = getattr(inst, 'associated_club', None) if associated_club is DEFAULT else associated_club
        if associated_club is None:
            return TestResult(False, 'No associated Club provided')
        if club_service.get_club_by_id(associated_club.club_id) is None:
            return TestResult(False, '{} has been deleted', associated_club)
        return super(__class__, inst_or_cls).test(associated_club=associated_club, **kwargs)

    @flexmethod
    def get_participants(cls, inst, participant_type:ParticipantType, sim=DEFAULT, target=DEFAULT, **interaction_parameters) -> tuple:
        inst_or_cls = inst if inst is not None else cls
        result = super(__class__, inst_or_cls).get_participants(participant_type, sim=sim, target=target, **interaction_parameters)
        result = set(result)
        if participant_type & ParticipantType.AssociatedClub and inst is not None:
            result.add(inst.associated_club)
        if participant_type & ParticipantType.AssociatedClubMembers and inst is not None:
            result.update(inst.associated_club.members)
        if participant_type & ParticipantType.AssociatedClubLeader and inst is not None:
            result.add(inst.associated_club.leader)
        if participant_type & ParticipantType.AssociatedClubGatheringMembers and inst is not None:
            club_service = services.get_club_service()
            if club_service is not None:
                gathering = club_service.clubs_to_gatherings_map.get(inst.associated_club)
                if gathering is not None:
                    result.update(gathering.all_sims_in_situation_gen())
        return tuple(result)

class ClubSuperInteraction(ClubInteractionMixin, SuperInteraction):
    ASSOCIATED_PICK_TYPE = PickType.PICK_SIM
lock_instance_tunables(ClubSuperInteraction, _saveable=None)
class ClubSocialSuperInteraction(ClubSuperInteraction, SocialSuperInteraction):

    def get_source_social_kwargs(self):
        kwargs = super().get_source_social_kwargs()
        kwargs['associated_club'] = self.associated_club
        return kwargs

class ClubTravelHereWithGatheringSuperInteraction(ClubSuperInteraction, TravelSuperInteraction):
    ASSOCIATED_PICK_TYPE = PickType.PICK_TERRAIN

    @classmethod
    def _test(cls, target, context, **kwargs):
        return cls.travel_pick_info_test(target, context, **kwargs)

    def _run_interaction_gen(self, timeline):
        to_zone_id = self.context.pick.get_zone_id_from_pick_location()
        if to_zone_id is None:
            logger.error('Could not resolve lot id: {} into a valid zone id when traveling to adjacent lot.', self.context.pick.lot_id, owner='rmccord')
            return
        if services.get_persistence_service().is_save_locked():
            return
        club_service = services.get_club_service()
        situation_manager = services.get_zone_situation_manager()
        gathering = club_service.clubs_to_gatherings_map.get(self.associated_club)
        if gathering is not None:
            situation_manager.travel_existing_situation(gathering, to_zone_id)

class ClubSocialMixerInteraction(ClubInteractionMixin, SocialMixerInteraction):
    ASSOCIATED_PICK_TYPE = PickType.PICK_SIM

    @classmethod
    def get_base_content_set_score(cls, associated_club=None, **kwargs):
        base_score = super().get_base_content_set_score(**kwargs)
        if associated_club.get_gathering() is not None:
            base_score += ClubTunables.FRONT_PAGE_SCORE_BONUS_FOR_CLUB_MIXERS
        return base_score

    @property
    def super_interaction(self):
        return super(SocialMixerInteraction, self).super_interaction

    @super_interaction.setter
    def super_interaction(self, value):
        super(SocialMixerInteraction, self.__class__).super_interaction.fset(self, value)
        if self.associated_club is None:
            self.associated_club = value.associated_club
        elif value.associated_club is None:
            value.associated_club = self.associated_club

class BroadcasterEffectClubRule(BroadcasterEffectLoot):

    def apply_broadcaster_effect(self, broadcaster, affected_object):
        if not affected_object.is_sim:
            return
        club_service = services.get_club_service()
        interaction = broadcaster.interaction
        sim_info = interaction.sim.sim_info
        (encouragement, rules) = club_service.get_interaction_encouragement_status_and_rules_for_sim_info(sim_info, interaction.aop)
        if encouragement == ClubRuleEncouragementStatus.DISCOURAGED:
            affected_sim_clubs = club_service.get_clubs_for_sim_info(affected_object.sim_info)
            if affected_sim_clubs and any(rule.club in affected_sim_clubs for rule in rules):
                super()._apply_broadcaster_effect(broadcaster, affected_object)

class BroadcasterClubRule(Broadcaster):
    REMOVE_INSTANCE_TUNABLES = ('effects',)
    INSTANCE_TUNABLES = {'negative_effect': BroadcasterEffectClubRule.TunableFactory(description='\n            A broadcaster effect to run on Sims who witness a Sim running a\n            discouraged Club Rule.\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.effects = (self.negative_effect,)
lock_instance_tunables(BroadcasterClubRule, clock_type=BroadcasterClockType.GAME_TIME)
class ClubTunables:
    MINIMUM_CRITERIA_SKILL_LEVEL = Tunable(description='\n        Club rules and club membership criteria can specify specific skills\n        that Sims must have in order for those things to apply to them. This\n        tunable defines the minimum required skill level for those skills.\n        ', tunable_type=int, default=3)
    CLUB_MEMBER_SIM_FILTER = DynamicSimFilter.TunablePackSafeReference(description='\n        A reference to a DynamicSimFilter that will be used to find club\n        members. A list of additional filterTerms will be passed in when this\n        is instanced depending on club admission criteria.\n        ')
    CLUB_MEMBER_LOOT = LootActions.TunableReference(description='\n        Loot that is awarded when a Sim joins a Club, between the new member and\n        all existing members.\n        ', pack_safe=True)
    CLUB_ENCOURAGEMENT_AD_DATA = Tunable(description='\n        The default value that club rule encouragement static commodities will\n        advertise at.\n        ', tunable_type=int, default=64)
    CLUB_DISCOURAGEMENT_AD_DATA = Tunable(description='\n        The default value that club rule discouragement static commodities will\n        advertise at.\n        ', tunable_type=int, default=0)
    CLUB_ENCOURAGEMENT_MULTIPLIER = TunableRange(description="\n        The multiplier to apply to an interaction's final autonomy score in the\n        case that a club rule encourages that action. This tunable has the\n        responsibility of making sure Sims will not run encouraged interactions\n        100% of the time with no chance of normal things like solving motives,\n        even if those actions are not encouraged.\n        ", tunable_type=float, default=1.25, minimum=0)
    CLUB_ENCOURAGEMENT_SUBACTION_MULTIPLIER = TunableRange(description="\n        The multiplier to apply to a mixer interaction's final subaction\n        autonomy score in the case that it is encouraged by a club rule.\n        ", tunable_type=float, default=100, minimum=1)
    CLUB_DISCOURAGEMENT_MULTIPLIER = TunableRange(description="\n        The multiplier to apply to an interaction's final autonomy score in the\n        case that a club rule discourages that action. This tunable has the\n        responsibility of making sure Sims will still solve for motives and not\n        die, even if those actions are discouraged.\n        ", tunable_type=float, default=0.5, minimum=0)
    CLUB_SEEDS_SECONDARY = TunableSet(description='\n        A set of ClubSeeds that will be used to create new Clubs when there are\n        fewer than the minimum number left in the world.\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.CLUB_SEED), pack_safe=True))
    MINIMUM_REQUIRED_CLUBS = TunableRange(description='\n        The minimum number of Clubs that must exist in the world at all times.\n        If we ever drop below this number, we will add new Clubs from the\n        CLUB_SEEDS_SECONDARY list to get us back up to the minimum.\n        ', tunable_type=int, minimum=1, default=5)
    DEFAULT_MEMBER_CAP = TunableRange(description='\n        The default maximum number of Sims that can be in a single Club. This\n        cap can be increased with Club Perk unlocks.\n        ', tunable_type=int, default=4, minimum=1)
    CLUB_RELATIONSHIP_SCORE_MULTIPLIER = TunableRange(description='\n        A multiplier to apply to the relationship score for an interaction\n        between two club members.\n        ', tunable_type=int, default=2, minimum=1)
    CLUB_RULE_BROADCASTER = BroadcasterClubRule.TunablePackSafeReference(description='\n        A reference to the broadcaster triggered as part of a basic extra on\n        all interactions affected by Club Rules.\n        ')
    CLUB_SUPER_INTERACTIONS = TunableSet(description='\n        A set of SuperInteractions that the Club System should provide to Sims.\n        ', tunable=ClubSuperInteraction.TunableReference(pack_safe=True))
    CLUB_PHONE_SUPER_INTERACTIONS = TunableSet(description='\n        A set of SuperInteractions that the Club System should provide to Sims\n        through their phone.\n        ', tunable=ClubSuperInteraction.TunableReference(pack_safe=True))
    CLUB_ICONS = TunableSet(description='\n        A set of icons available for use with Clubs.\n        \n        Consumed by UI when populating icon options for club modification.\n        ', tunable=TunableIcon(pack_safe=True), tuning_group=GroupNames.UI, export_modes=(ExportModes.ClientBinary,))
    CLUB_TRAITS = TunableSet(description='\n        A set of traits available for use with club rules and admission\n        criteria.\n        \n        Consumed by UI when populating options for club modification.\n        ', tunable=Trait.TunableReference(pack_safe=True), tuning_group=GroupNames.UI)
    CLUB_DISPLAY_INFO_TRAIT_TOOLTIP_NAME = TunableMapping(description='\n        A mapping of traits to their desired name in the tooltip. This is useful\n        if the text needs to differ, e.g. "Teen" -> Be Mean to Teens.\n        ', key_type=Trait.TunableReference(description='\n            The trait whose display name needs to be different in tooltips.\n            ', pack_safe=True), value_type=TunableLocalizedString(description='\n            The tooltip name of the specified trait.\n            '))
    CLUB_DISPLAY_INFO_MARITAL_STATUS = TunableMapping(description='\n        Tunable Mapping from MaritalStatus enums to their associated display\n        names and icons.\n        ', key_type=TunableEnumEntry(description='\n            A MaritalStatus enum entry.\n            ', tunable_type=MaritalStatus, default=MaritalStatus.MARRIED), value_type=TunableTuple(name=TunableLocalizedString(description='\n                The name to associate with this enum entry.\n                '), icon=TunableIcon(description='\n                The icon to associate with this enum entry.\n                ')))
    CLUB_DISPLAY_INFO_HOUSEHOLD_VALUE = TunableMapping(description='\n        Tunable Mapping from HouseholdValueCategory enums to their associated\n        display names and icons.\n        ', key_type=TunableEnumEntry(description='\n            A HouseholdValueCategory enum entry.\n            ', tunable_type=HouseholdValueCategory, default=HouseholdValueCategory.AVERAGE), value_type=TunableTuple(name=TunableLocalizedString(description='\n                The name to associate with this enum entry.\n                '), icon=TunableIcon(description='\n                The icon to associate with this enum entry.\n                ')))
    CLUB_DISPLAY_INFO_FAME_RANK = TunableMapping(description='\n        Tunable mapping from FameRank enums to their associated display names\n        and icons.\n        ', key_type=TunableEnumEntry(description='\n            A FameRank enum entry.\n            ', tunable_type=FameRank, default=FameRank.FAME_RANK_1), value_type=TunableTuple(name=TunableLocalizedString(description='\n                The name to associate with this enum entry.\n                '), icon=TunableIcon(description='\n                The icon to associate with this enum entry.\n                ')))
    CLUB_COLOR_MAP = TunableMapping(description='\n        A mapping from CAS tags to LocalizedStrings representing available club\n        colors.\n        ', key_type=TunableEnumEntry(description='\n            A color tag that can be associated with Club uniforms.\n            ', tunable_type=Tag, default=Tag.INVALID, pack_safe=True), value_type=TunableTuple(color_name=TunableLocalizedString(description='\n                The name of the tag shown to users.\n                '), color_value=Tunable(description="\n                The color's actual value.\n                ", tunable_type=str, default='ffffffff'), export_class_name='ColorDataTuple'), tuple_name='TunableColorData', export_modes=ExportModes.All)
    CLUB_STYLE_MAP = TunableMapping(description='\n        A mapping from CAS tags to LocalizedStrings representing available club\n        styles.\n        ', key_type=TunableEnumEntry(description='\n            A color tag that can be associated with Club uniforms.\n            ', tunable_type=Tag, default=Tag.INVALID, pack_safe=True), value_type=TunableTuple(style_name=TunableLocalizedString(description='\n                The name of the tag shown to users.\n                '), export_class_name='StyleDataTuple'), tuple_name='TunableStyleData', export_modes=ExportModes.All)
    HOUSEHOLD_VALUE_MAP = TunableMapping(description='\n        A mapping from HouseholdValueCategory to an actual wealth interval.\n        ', key_type=TunableEnumEntry(description='\n            A HouseholdValueCategory to be associated with a wealth interval.\n            ', tunable_type=HouseholdValueCategory, default=HouseholdValueCategory.AVERAGE), value_type=TunableInterval(description='\n            A wealth interval that qualifies a Sim for the associated\n            HouseholdValueCategory.\n            ', tunable_type=int, default_lower=0, default_upper=1000, minimum=0))
    MARRIAGE_REL_BIT = TunableReference(description='\n        A reference to the marriage relationship bit for use with ClubCriteria.\n        ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), pack_safe=True)
    MAX_CLUBS_PER_SIM = TunableRange(description='\n        The maximum number of Clubs a single Sim can be a member of at one\n        time.\n        ', tunable_type=int, minimum=1, default=3)
    DEFAULT_CLUB_GATHERING_SITUATION = TunableReference(description='\n        A reference to the default situation for Club Gatherings.\n        \n        Used for cheat commands.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), class_restrictions=('ClubGatheringSituation',), pack_safe=True)
    CLUB_MEMBER_CAPACITY_INCREASES = TunableMapping(description='\n        A mapping from Bucks Perk to the Cap Increase that perk rewards.\n        \n        These benefits are additive.\n        ', key_type=TunableReference(description='\n            The perk that rewards the club with an increase in the number of\n            members it is allowed to have.\n            ', manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK), pack_safe=True), value_type=Tunable(description='\n            The amount to increase the member cap of the club.\n            ', tunable_type=int, default=1))
    NEW_RELATIONSHIP_MODS = TunableMapping(description="\n        A mapping of perk to a set of tests and a loot.\n        \n        If a new relationship is added while a Sim is in a club gathering and \n        all of the tests pass the loot will be applied to the relationship.\n        \n        NOTE: This loot will be applied using a DoubleSimResolver where Actor\n        is the Sim in the club and Target is the Sim they are meeting. If \n        you don't want the bonus to be applied to relationships where both Sims\n        are in the same group you should add a test for that. Also you might \n        not have access to many of the participant types you do for interaction\n        tests.\n        ", key_type=TunableReference(description='\n            The Perk that must be unlocked in order to potentially apply the \n            new relationship mods.\n            ', manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK), pack_safe=True), value_type=TunableTuple(description='\n            A tuple of Global Test Set to Loot.\n            \n            If all of the tests in the test set pass then the loot will be \n            applied.\n            ', test_set=event_testing.tests.TunableGlobalTestSet(description='\n                A Set of tests that all must pass in order for the \n                corresponding loot to be applied.\n                '), loot=TunableReference(description='\n                A reference to a loot that will be applied if all of the tests\n                in the tests set pass.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True), export_class_name='RelationshipModTuple'), tuple_name='TunableRelationshipMod')
    CLUB_BUCKS_REWARDS_MULTIPLIER = TunableTuple(description='\n        A combination of trait reference and multiplier.\n        \n        When a Sim receiving the Club Bucks has the tuned trait then they will\n        get the tuned multiplier applied to the amound of reward they receive.\n        ', trait=TunableReference(description='\n            The trait required to receiver the multiplier bonus to the club \n            bucks the Sim receives.\n            ', manager=services.trait_manager(), pack_safe=True), multiplier=Tunable(description='\n            The multiplier to apply to the amount of club bucks a club member \n            receives if they have the appropriate trait.\n            ', tunable_type=float, default=1.0))
    BUFFS_NOT_IN_ANY_CLUB = TunableSet(description='\n        The buffs that are applied to a Sim that is not a member of any club.\n        ', tunable=TunableBuffReference(pack_safe=True))
    CLUB_GATHERING_AUTO_START_GROUP_SIZE = TunableRange(description='\n        The required number of Sims in a social group necessary to auto-start a\n        gathering. The most common Club among those Sims will determine the type\n        of gathering to start.\n        ', tunable_type=int, minimum=1, default=3)
    CLUB_GATHERING_TRAVEL_AUTO_START_GROUP_SIZE = TunableRange(description='\n        The required number of Sims that traveled to auto-start a\n        gathering. The most common Club among those Sims will determine the type\n        of gathering to start.\n        ', tunable_type=int, minimum=1, default=3)
    CLUB_GATHERING_AUTO_START_COOLDOWN = TunableSimMinute(description='\n        The span of time since the ending of a gathering during which the same\n        gathering will not be automatically started by the game.\n        ', default=60)
    CLUB_ADD_MEMBER_PICKER_DIALOG = UiClubSimPicker.TunableFactory(description='\n        The picker dialog to show when adding Sims to a club.\n        ', locked_args={'max_selectable': None})
    CLUB_ADD_MEMBER_FILTER = TunablePackSafeReference(description='\n        The filter to use when adding Sims to a club, relative to the active\n        Sim.\n        ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER))
    CLUB_ADD_MEMBER_CAP = TunableRange(description='\n        The maximum number of Sims allowed in the picker to add members to a\n        Club. Sims matching CLUB_ADD_MEMBER_FILTER are always prioritized\n        against Sims not matching the filter.\n        ', tunable_type=int, default=27, minimum=1)
    CLUB_GATHERING_AUTO_START_SCHEDULES = TunableList(description="\n        A list of weekly schedules. Each Club is randomly assigned a weekly\n        schedule. While this is never surfaced to the player, the system uses\n        this to determine if a Club is available for auto-started gatherings.\n        This ensures that Clubs aren't constantly gathered at venues.\n        ", tunable=WeeklySchedule.TunableFactory(), minlength=1)
    CLUB_BUCKS_ENCOURAGED_REWARDS_TIMER_START = TunableSimMinute(description="\n        This is the initial amount of time, in Sim minutes, to wait when a Sim runs an \n        encouraged interaction before rewarding the Sim's clubs with reward\n        bucks for the interaction. \n        \n        It is possible for this to reward club bucks to multiple clubs at the \n        same time.\n        ", default=10)
    CLUB_BUCKS_ENCOURAGED_REWARDS_TIMER_REPEATING = TunableSimMinute(description="\n        This is the repeating amount of time, in Sim minutes, to wait before awarding more\n        club bucks to the Sim's clubs for doing an encouraged interaction.\n        \n        It is possible for this to reward club bucks to multiple clubs at the \n        same time.\n        ", default=10)
    CLUB_BUCKS_TYPE = TunableEnumEntry(description='\n        This is the enum entry for the type of bucks that clubs reward. This\n        should always be set to ClubBucks.\n        ', tunable_type=BucksType, default=bucks.bucks_enums.BucksType.INVALID, pack_safe=True)
    CLUB_NOTIFICATION_CREATE = TunableUiDialogNotificationSnippet(description='\n        The notification to show when a Club is created by the player.\n        ', pack_safe=True)
    CLUB_NOTIFICATION_JOIN = TunableUiDialogNotificationSnippet(description='\n        The notification to show when a selectable Sim joins a Club.\n        ', pack_safe=True)
    CLUB_NOTIFICATION_INVALID = TunableUiDialogNotificationSnippet(description='\n        The notification to show when a selectable Sim is removed from a Club\n        because they no longer match the criteria, e.g. they have Aged Up,\n        Married, etc...\n        ', pack_safe=True)
    CLUB_GATHERING_DIALOG = UiDialogOkCancel.TunableFactory(description='\n        A dialog that is shown to invite a player-controlled Sim to a Club\n        gathering.\n        \n        The dialog is provided with several additional tokens:\n         * The name of the Club\n         * The name of the lot the gathering is at\n         * Text specific to the venue type.\n         * Text specific to the type of invite (join, drama node, \n           request for invitation)\n        ')
    CLUB_GATHERING_DIALOG_TEXT_JOIN = TunableLocalizedStringFactoryVariant(description='\n        Text that is provided as a token to CLUB_GATHERING_DIALOG when the Sim\n        in question has just joined the Club and is being invited to a\n        gathering.\n        ')
    CLUB_GATHERING_DIALOG_TEXT_DRAMA_NODE = TunableLocalizedStringFactoryVariant(description='\n        Text that is provided as a token to CLUB_GATHERING_DIALOG when the Sim\n        in question is being invited to a gathering as part of a scheduled drama\n        node.\n        ')
    CLUB_GATHERING_DIALOG_TEXT_REQUEST_INVITE = TunableLocalizedStringFactoryVariant(description='\n        Text that is provided as a token to CLUB_GATHERING_DIALOG when the Sim\n        in question has requested an invitation to a closed Club and is being\n        invited to a gathering.\n        ')
    CLUB_GATHERING_DIALOG_REQUEST_INVITE_NO_LOT = UiDialogOkCancel.TunableFactory(description='\n        A dialog that is shown when a player-controlled Sim requests an invite\n        to a Club, but that Club has no available hangout spot. If the player\n        Sim is home, they are asked whether or not it would be acceptable to\n        start the gathering at the home lot.\n        \n        The dialog is provided with additional tokens:\n         * The name of the Club\n        ')
    CLUB_GATHERING_DIALOG_REQUEST_INVITE_NO_LOT_NOT_HOME = UiDialogOk.TunableFactory(description='\n        A dialog that is shown when a player-controlled Sim requests an invite\n        to a Club, but that Club has no available hangout spot and the player\n        Sim is not home (where they would usually offer to meet).\n        \n        The dialog is provided with additional tokens:\n         * The name of the Club\n        ')
    CLUB_GATHERING_DIALOG_REQUEST_INVITE_ACTIVE_SIM = TunableUiDialogNotificationSnippet(description='\n        A notification that is shown to a player-controlled Sim that has\n        requested a Club invite to a Club which has another active Sim as a\n        member.\n        ', pack_safe=True)
    CLUB_GATHERING_DIALOG_REQUEST_INVITE_CURRENT_LOT = TunableUiDialogNotificationSnippet(description='\n        A notification that is shown to a player-controlled Sim that has\n        requested a Club invite to a Club that is currently gathering on the\n        active lot.\n        ', pack_safe=True)
    CLUB_GATHERING_DIALOG_REQUEST_INVITE_UNAVAILABLE = UiDialogOk.TunableFactory(description='\n        A dialog that is shown to a player-controlled Sim that has requested a\n        Club invite but is unable to travel due to region incompatibility.\n        \n        The dialog is provided with additional tokens:\n         * The name of the Club\n        ')
    CLUB_GATHERING_START_DIALOG = UiDialogOk.TunableFactory(description='\n        A dialog that shows up when a Club gathering starts because the player\n        Sim has requested an Invite.\n        ')
    CLUB_GATHERING_START_SELECT_LOCATION_DIALOG = UiDialogOkCancel.TunableFactory(description='\n        A dialog that shows up when the player starts a gathering. The "OK"\n        button travels the player to the Club\'s preferred hangout spot. The\n        "Cancel" button starts the gathering in the current location.\n        ')
    CLUB_GATHERING_START_RESIDENTIAL_INVALID_DIALOG = UiDialogOk.TunableFactory(description='\n        A dialog that shows up when the player starts a gathering on an invalid\n        residential lot via the UI.\n        ')
    CLUB_GATHERING_START_INVALID_DIALOG = UiDialogOk.TunableFactory(description='\n        A dialog that shows up when the player starts a gathering on an invalid\n        lot via the UI.\n        ')
    DEFAULT_MANNEQUIN_DATA = TunableTuple(description='\n        References to each of the default mannequin sim infos to use for\n        club CAS.\n        ', male_adult=TunablePackSafeResourceKey(description='\n            Default mannequin sim info for male adult club CAS.\n            ', resource_types=(sims4.resources.Types.SIMINFO,)), female_adult=TunablePackSafeResourceKey(description='\n            Default mannequin sim info for female adult club CAS.\n            ', resource_types=(sims4.resources.Types.SIMINFO,)), male_child=TunablePackSafeResourceKey(description='\n            Default mannequin sim info for male child club CAS.\n            ', resource_types=(sims4.resources.Types.SIMINFO,)), female_child=TunablePackSafeResourceKey(description='\n            Default mannequin sim info for female child club CAS.\n            ', resource_types=(sims4.resources.Types.SIMINFO,)))
    MINUTES_BETWEEN_CLUB_GATHERING_PULSES = Tunable(description='\n        This is the amount of time, in Sim minutes, that pass between when we \n        increase the amount of time a Sim has spent in a Club Gathering.\n        \n        Ex: If this is set to 10 minutes then once every 10 minutes after a \n        club gathering starts the amount of time that a Sim has spent in a \n        gathering will be increased by the amount of time since we last\n        increased their value.\n        ', tunable_type=int, default=10)
    PIE_MENU_INTERACTION_ENCOURAGED_ICON = TunableIconAllPacks(description='\n        The Icon to display in the pie menu if an interaction is encouraged.\n        ')
    PIE_MENU_INTERACTION_DISCOURAGED_ICON = TunableIconAllPacks(description='\n        The Icon to display in the pie menu if an interaction is discouraged.\n        ')
    FRONT_PAGE_SCORE_BONUS_FOR_ENCOURAGED_MIXER = Tunable(description='\n        The bonus added to the score of a mixer interaction when figuring out\n        which mixers end up in the social front page.\n        ', tunable_type=int, default=100)
    FRONT_PAGE_SCORE_BONUS_FOR_CLUB_MIXERS = Tunable(description='\n        The bonus added to the front page score of a Club mixer interaction when\n        its associated Club is currently gathering.\n        ', tunable_type=int, default=100)
    INITIAL_AMOUNT_OF_CLUB_BUCKS = Tunable(description='\n        The amount of club bucks that a new club starts with.\n        ', tunable_type=int, default=100)
    DEFAULT_USER_CLUB_PERKS = TunableList(description='\n        The perks to unlock by default for non seeded clubs (user created clubs)\n        ', tunable=TunableReference(description='\n            The reference to the perk to unlock.\n            ', manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK), pack_safe=True))
    PROHIBIT_CLUB_OUTFIT_BUFFS = TunableList(description='\n        A list of buffs that a Sim can have to prevent them from changing into\n        their club outfit when a club situation starts.\n        ', tunable=TunableReference(description='\n            The Buff that will prevent a sim from changing into their club\n            outfit when a club situation starts.\n            ', manager=services.get_instance_manager(sims4.resources.Types.BUFF), pack_safe=True))

class ClubRuleCriteriaBase(HasTunableFactory, AutoFactoryInit):

    def __init__(self, *args, criteria_infos=None, criteria_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._club = None
        self.criteria_id = criteria_id

    @classmethod
    def test(self):
        return True

    @classmethod
    def is_multi_select(self):
        return False

    @classmethod
    def populate_possibilities(cls, criteria_proto):
        criteria_proto.multi_select = cls.is_multi_select()

    def register_club(self, club):
        pass

    def test_sim_info(self, sim_info):
        raise NotImplementedError

    def save(self, club_criteria):
        club_criteria.category = self.CATEGORY
        club_criteria.multi_select = self.is_multi_select()

class ClubRuleCriteriaMultiSelect(ClubRuleCriteriaBase):

    @classmethod
    def is_multi_select(self):
        return True

class ClubRuleCriteriaSkill(ClubRuleCriteriaMultiSelect):
    CATEGORY = ClubCriteriaCategory.SKILL
    FACTORY_TUNABLES = {'skills': TunableList(description='\n            In order to pass this criteria, the target Sim must have one of\n            these skills with a skill level of at least the value specified in\n            MINIMUM_CRITERIA_SKILL_LEVEL.\n            ', tunable=Skill.TunableReference(pack_safe=True), unique_entries=True, minlength=1)}

    def __init__(self, *args, skills=(), criteria_infos=None, **kwargs):
        super().__init__(*args, skills=skills, **kwargs)
        if criteria_infos is not None:
            self.skills = []
            skill_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
            for criteria_info in criteria_infos:
                skill = skill_manager.get(criteria_info.resource_value.instance)
                if skill is not None:
                    self.skills.append(skill)
            if not self.skills:
                raise UnavailableClubCriteriaError

    @classmethod
    def _populate_criteria_info(cls, criteria_info, skill):
        criteria_info.name = skill.stat_name
        criteria_info.icon = sims4.resources.get_protobuff_for_key(skill.icon)
        skill_proto = sims4.resources.get_protobuff_for_key(skill.resource_key)
        criteria_info.resource_value = skill_proto

    @classmethod
    def populate_possibilities(cls, criteria_proto):
        skill_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
        for skill in skill_manager.get_ordered_types(only_subclasses_of=Skill):
            if skill.hidden:
                pass
            elif not any(age >= Age.CHILD for age in skill.ages):
                pass
            else:
                with ProtocolBufferRollback(criteria_proto.criteria_infos) as criteria_info:
                    cls._populate_criteria_info(criteria_info, skill)
        return super().populate_possibilities(criteria_proto)

    def save(self, club_criteria):
        for skill in self.skills:
            with ProtocolBufferRollback(club_criteria.criteria_infos) as criteria_info:
                self._populate_criteria_info(criteria_info, skill)
        return super().save(club_criteria)

    def test_sim_info(self, sim_info):
        for skill_type in self.skills:
            skill_or_skill_type = sim_info.get_stat_instance(skill_type) or skill_type
            skill_level = skill_or_skill_type.get_user_value()
            if skill_level >= ClubTunables.MINIMUM_CRITERIA_SKILL_LEVEL:
                return True
        return False

class ClubRuleCriteriaTrait(ClubRuleCriteriaMultiSelect):
    CATEGORY = ClubCriteriaCategory.TRAIT
    FACTORY_TUNABLES = {'traits': TunableList(description='\n            In order to pass this criteria, the target Sim must have one of\n            these Traits.\n            ', tunable=Trait.TunableReference(pack_safe=True), unique_entries=True, minlength=1)}

    def __init__(self, *args, traits=(), criteria_infos=None, **kwargs):
        super().__init__(*args, traits=traits, **kwargs)
        if criteria_infos is not None:
            self.traits = []
            trait_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
            for criteria_info in criteria_infos:
                trait = trait_manager.get(criteria_info.resource_value.instance)
                if trait is not None:
                    self.traits.append(trait)
            if not self.traits:
                raise UnavailableClubCriteriaError

    @classmethod
    def _populate_criteria_info(cls, criteria_info, trait):
        criteria_info.name = trait.display_name_gender_neutral
        if trait in ClubTunables.CLUB_DISPLAY_INFO_TRAIT_TOOLTIP_NAME:
            criteria_info.tooltip_name = ClubTunables.CLUB_DISPLAY_INFO_TRAIT_TOOLTIP_NAME[trait]
        criteria_info.icon = sims4.resources.get_protobuff_for_key(trait.icon)
        trait_proto = sims4.resources.get_protobuff_for_key(trait.resource_key)
        criteria_info.resource_value = trait_proto

    @classmethod
    def populate_possibilities(cls, criteria_proto):
        for trait in ClubTunables.CLUB_TRAITS:
            with ProtocolBufferRollback(criteria_proto.criteria_infos) as criteria_info:
                cls._populate_criteria_info(criteria_info, trait)
        return super().populate_possibilities(criteria_proto)

    def save(self, club_criteria):
        for trait in self.traits:
            with ProtocolBufferRollback(club_criteria.criteria_infos) as criteria_info:
                self._populate_criteria_info(criteria_info, trait)
        return super().save(club_criteria)

    def test_sim_info(self, sim_info):
        return any(sim_info.has_trait(trait) for trait in self.traits)

class ClubRuleCriteriaRelationship(ClubRuleCriteriaBase):
    CATEGORY = ClubCriteriaCategory.RELATIONSHIP
    FACTORY_TUNABLES = {'marital_status': TunableEnumEntry(description='\n            Marital status a Sim must have in order to pass this criteria.\n            ', tunable_type=MaritalStatus, default=MaritalStatus.MARRIED)}

    def __init__(self, *args, marital_status=None, criteria_infos=None, **kwargs):
        super().__init__(*args, marital_status=marital_status, **kwargs)
        if criteria_infos is not None:
            self.marital_status = criteria_infos[0].enum_value

    @classmethod
    def _populate_criteria_info(cls, criteria_info, marital_status):
        possibility_space = ClubTunables.CLUB_DISPLAY_INFO_MARITAL_STATUS.get(marital_status)
        if possibility_space is None:
            return
        criteria_info.name = possibility_space.name
        criteria_info.icon = sims4.resources.get_protobuff_for_key(possibility_space.icon)
        criteria_info.enum_value = marital_status

    @classmethod
    def populate_possibilities(cls, criteria_proto):
        for marital_status in MaritalStatus:
            with ProtocolBufferRollback(criteria_proto.criteria_infos) as criteria_info:
                cls._populate_criteria_info(criteria_info, marital_status)
        return super().populate_possibilities(criteria_proto)

    def save(self, club_criteria):
        with ProtocolBufferRollback(club_criteria.criteria_infos) as criteria_info:
            self._populate_criteria_info(criteria_info, self.marital_status)
        return super().save(club_criteria)

    def test_sim_info(self, sim_info):
        is_married = sim_info.spouse_sim_id is not None
        if self.marital_status == MaritalStatus.MARRIED:
            return is_married
        elif self.marital_status == MaritalStatus.UNMARRIED:
            return not is_married

class ClubRuleCriteriaCareer(ClubRuleCriteriaMultiSelect):
    CATEGORY = ClubCriteriaCategory.CAREER
    FACTORY_TUNABLES = {'careers': TunableList(description='\n            In order to pass this criteria, the target Sim must have one of\n            these Careers.\n            ', tunable=Career.TunableReference(pack_safe=True), unique_entries=True, minlength=1)}

    def __init__(self, *args, careers=(), criteria_infos=None, **kwargs):
        super().__init__(*args, careers=careers, **kwargs)
        if criteria_infos is not None:
            self.careers = []
            career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
            for criteria_info in criteria_infos:
                career = career_manager.get(criteria_info.resource_value.instance)
                if career is not None:
                    self.careers.append(career)
            if not self.careers:
                raise UnavailableClubCriteriaError

    @classmethod
    def _populate_criteria_info(cls, criteria_info, career):
        criteria_info.name = career.start_track.career_name_gender_neutral
        criteria_info.icon = sims4.resources.get_protobuff_for_key(career.start_track.icon)
        career_proto = sims4.resources.get_protobuff_for_key(career.resource_key)
        criteria_info.resource_value = career_proto

    @classmethod
    def populate_possibilities(cls, criteria_proto):
        career_service = services.get_career_service()
        for career in career_service.get_career_list():
            if not career.available_for_club_criteria:
                pass
            else:
                with ProtocolBufferRollback(criteria_proto.criteria_infos) as criteria_info:
                    cls._populate_criteria_info(criteria_info, career)
        return super().populate_possibilities(criteria_proto)

    def save(self, club_criteria):
        for career in self.careers:
            with ProtocolBufferRollback(club_criteria.criteria_infos) as criteria_info:
                self._populate_criteria_info(criteria_info, career)
        return super().save(club_criteria)

    def test_sim_info(self, sim_info):
        if any(career.guid64 in sim_info.careers for career in self.careers):
            return True
        extra_careers = []
        for sim_career_uid in sim_info.careers:
            sim_career = sim_info.career_tracker.get_career_by_uid(sim_career_uid)
            if sim_career is not None and sim_career.current_level_tuning.ageup_branch_career is not None:
                extra_career = sim_career.current_level_tuning.ageup_branch_career(sim_info)
                extra_careers.append(extra_career.guid64)
        return any(career.guid64 in extra_careers for career in self.careers)

class ClubRuleCriteriaHouseholdValue(ClubRuleCriteriaBase):
    CATEGORY = ClubCriteriaCategory.HOUSEHOLD_VALUE
    FACTORY_TUNABLES = {'household_value': TunableEnumEntry(description="\n            In order to pass this criteria, the target sim must have a\n            household value in this enum value's associated interval.\n            ", tunable_type=HouseholdValueCategory, default=HouseholdValueCategory.AVERAGE)}

    def __init__(self, *args, household_value=None, criteria_infos=None, **kwargs):
        super().__init__(*args, household_value=household_value, **kwargs)
        if criteria_infos is not None:
            self.household_value = criteria_infos[0].enum_value

    @classmethod
    def _populate_criteria_info(cls, criteria_info, household_value):
        possibility_space = ClubTunables.CLUB_DISPLAY_INFO_HOUSEHOLD_VALUE.get(household_value)
        if possibility_space is None:
            return
        criteria_info.name = possibility_space.name
        criteria_info.icon = sims4.resources.get_protobuff_for_key(possibility_space.icon)
        criteria_info.enum_value = household_value

    @classmethod
    def populate_possibilities(cls, criteria_proto):
        for household_value in HouseholdValueCategory:
            with ProtocolBufferRollback(criteria_proto.criteria_infos) as criteria_info:
                cls._populate_criteria_info(criteria_info, household_value)
        return super().populate_possibilities(criteria_proto)

    def save(self, club_criteria):
        with ProtocolBufferRollback(club_criteria.criteria_infos) as criteria_info:
            self._populate_criteria_info(criteria_info, self.household_value)
        return super().save(club_criteria)

    def test_sim_info(self, sim_info):
        interval = ClubTunables.HOUSEHOLD_VALUE_MAP[self.household_value]
        return interval.lower_bound <= sim_info.household.household_net_worth() <= interval.upper_bound

class ClubRuleCriteriaAge(ClubRuleCriteriaMultiSelect):
    CATEGORY = ClubCriteriaCategory.AGE
    FACTORY_TUNABLES = {'ages': TunableEnumSet(description='\n            In order to pass this criteria, the target Sim must be one of the\n            specified ages.\n            ', enum_type=Age, enum_default=Age.ADULT)}

    def __init__(self, *args, ages=None, criteria_infos=None, **kwargs):
        super().__init__(*args, ages=ages, **kwargs)
        if criteria_infos is not None:
            self.ages = set(criteria_info.enum_value for criteria_info in criteria_infos)

    @classmethod
    def _populate_criteria_info(cls, criteria_info, age):
        aging_data = AgingTuning.get_aging_data(Species.HUMAN)
        age_transition_data = aging_data.get_age_transition_data(age)
        age_trait = age_transition_data.age_trait
        if age_trait is None:
            return
        criteria_info.name = age_trait.display_name_gender_neutral
        if age_trait in ClubTunables.CLUB_DISPLAY_INFO_TRAIT_TOOLTIP_NAME:
            criteria_info.tooltip_name = ClubTunables.CLUB_DISPLAY_INFO_TRAIT_TOOLTIP_NAME[age_trait]
        criteria_info.icon = sims4.resources.get_protobuff_for_key(age_trait.icon)
        criteria_info.enum_value = age

    @classmethod
    def populate_possibilities(cls, criteria_proto):
        for age in Age:
            if age <= Age.TODDLER:
                pass
            else:
                with ProtocolBufferRollback(criteria_proto.criteria_infos) as criteria_info:
                    cls._populate_criteria_info(criteria_info, age)
        return super().populate_possibilities(criteria_proto)

    def save(self, club_criteria):
        for age in self.ages:
            with ProtocolBufferRollback(club_criteria.criteria_infos) as criteria_info:
                self._populate_criteria_info(criteria_info, age)
        return super().save(club_criteria)

    def test_sim_info(self, sim_info):
        return sim_info.age in self.ages

class ClubRuleCriteriaClubMembership(ClubRuleCriteriaMultiSelect):
    CATEGORY = ClubCriteriaCategory.CLUB_MEMBERSHIP
    FACTORY_TUNABLES = {'required_club_seeds': TunableSet(description='\n            In order to pass this criteria, the target Sim must be a member of\n            one the specified Clubs.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.CLUB_SEED), pack_safe=True))}

    def __init__(self, *args, required_club_seeds=(), criteria_infos=None, **kwargs):
        super().__init__(*args, required_club_seeds=required_club_seeds, **kwargs)
        self._required_club_ids = []
        if criteria_infos is not None:
            for criteria_info in criteria_infos:
                self._required_club_ids.append(criteria_info.resource_id)
        else:
            club_service = services.get_club_service()
            for required_club_seed in self.required_club_seeds:
                required_club = club_service.get_club_by_seed(required_club_seed)
                if required_club is not None:
                    self._required_club_ids.append(required_club.club_id)

    @classmethod
    def _populate_criteria_info(cls, criteria_info, club):
        criteria_info.name = club.name
        criteria_info.icon = sims4.resources.get_protobuff_for_key(club.icon)
        criteria_info.resource_id = club.club_id

    @classmethod
    def populate_possibilities(cls, criteria_proto):
        club_service = services.get_club_service()
        if club_service is None:
            logger.error('No Club Service exists.')
            return
        for club in club_service.clubs:
            with ProtocolBufferRollback(criteria_proto.criteria_infos) as criteria_info:
                cls._populate_criteria_info(criteria_info, club)
        return super().populate_possibilities(criteria_proto)

    def save(self, club_criteria):
        club_service = services.get_club_service()
        if not self._required_club_ids:
            for required_club_seed in self.required_club_seeds:
                required_club = club_service.get_club_by_seed(required_club_seed)
                if required_club is not None:
                    self._required_club_ids.append(required_club.club_id)
        for required_club in self._required_club_ids:
            required_club = club_service.get_club_by_id(required_club)
            if required_club is not None:
                with ProtocolBufferRollback(club_criteria.criteria_infos) as criteria_info:
                    self._populate_criteria_info(criteria_info, required_club)
        return super().save(club_criteria)

    def register_club(self, club):
        self._club = weakref.ref(club)

    def test_sim_info(self, sim_info):
        club = self._club()
        if club is None:
            logger.error('Attempting to test ClubRule {} with Sim {}, but the associated Club no longer exists.', self, sim_info)
            return False
        club_service = services.get_club_service()
        if club_service is None:
            logger.error("Attempting to test a ClubRule {} with Sim {}, but the ClubService isn't loaded.", self, sim_info)
            return False
        for required_club_id in self._required_club_ids:
            club = club_service.get_club_by_id(required_club_id)
            if club is not None and sim_info in club.members:
                return True
        return False

class ClubRuleCriteriaFameRank(ClubRuleCriteriaMultiSelect):
    CATEGORY = ClubCriteriaCategory.FAME_RANK
    FACTORY_TUNABLES = {'fame_rank_requirements': TunableEnumSet(description='\n            In order to pass this criteria, the Sim must have a fame rank\n            that has been selected.\n            ', enum_type=FameRank, enum_default=FameRank.FAME_RANK_1)}

    def __init__(self, *args, fame_rank_requirements=None, criteria_infos=None, **kwargs):
        super().__init__(*args, fame_rank_requirements=fame_rank_requirements, **kwargs)
        if criteria_infos is not None:
            self.fame_rank_requirements = set(criteria_info.enum_value for criteria_info in criteria_infos)

    @classmethod
    def test(cls):
        return FameTunables.FAME_RANKED_STATISTIC is not None

    @classmethod
    def _populate_criteria_info(cls, criteria_info, fame_rank):
        possibility_space = ClubTunables.CLUB_DISPLAY_INFO_FAME_RANK.get(fame_rank)
        if possibility_space is None:
            return
        criteria_info.name = possibility_space.name
        criteria_info.icon = sims4.resources.get_protobuff_for_key(possibility_space.icon)
        criteria_info.enum_value = fame_rank

    @classmethod
    def populate_possibilities(cls, criteria_proto):
        for fame_rank in FameRank:
            with ProtocolBufferRollback(criteria_proto.criteria_infos) as criteria_info:
                cls._populate_criteria_info(criteria_info, fame_rank)
        return super().populate_possibilities(criteria_proto)

    def save(self, club_criteria):
        for rank in self.fame_rank_requirements:
            with ProtocolBufferRollback(club_criteria.criteria_infos) as criteria_info:
                self._populate_criteria_info(criteria_info, rank)
        return super().save(club_criteria)

    def test_sim_info(self, sim_info):
        fame_stat = sim_info.commodity_tracker.get_statistic(FameTunables.FAME_RANKED_STATISTIC)
        if fame_stat is None:
            return False
        fame_rank = fame_stat.rank_level
        return fame_rank in self.fame_rank_requirements
CATEGORY_TO_CRITERIA_MAPPING = {ClubCriteriaCategory.FAME_RANK: ClubRuleCriteriaFameRank, ClubCriteriaCategory.CLUB_MEMBERSHIP: ClubRuleCriteriaClubMembership, ClubCriteriaCategory.AGE: ClubRuleCriteriaAge, ClubCriteriaCategory.HOUSEHOLD_VALUE: ClubRuleCriteriaHouseholdValue, ClubCriteriaCategory.CAREER: ClubRuleCriteriaCareer, ClubCriteriaCategory.RELATIONSHIP: ClubRuleCriteriaRelationship, ClubCriteriaCategory.TRAIT: ClubRuleCriteriaTrait, ClubCriteriaCategory.SKILL: ClubRuleCriteriaSkill}
class TunableClubAdmissionCriteriaVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, skill=ClubRuleCriteriaSkill.TunableFactory(), trait=ClubRuleCriteriaTrait.TunableFactory(), relationship=ClubRuleCriteriaRelationship.TunableFactory(), career=ClubRuleCriteriaCareer.TunableFactory(), household_value=ClubRuleCriteriaHouseholdValue.TunableFactory(), age=ClubRuleCriteriaAge.TunableFactory(), fame_rank=ClubRuleCriteriaFameRank.TunableFactory(), default='skill', **kwargs)

class TunableClubRuleCriteriaVariant(TunableClubAdmissionCriteriaVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, club_membership=ClubRuleCriteriaClubMembership.TunableFactory(), **kwargs)

class ClubInteractionGroup(metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.CLUB_INTERACTION_GROUP)):
    INSTANCE_TUNABLES = {'name': TunableLocalizedString(description='\n            The name for this interaction group.\n            ', tuning_group=GroupNames.UI, export_modes=(ExportModes.ClientBinary,)), 'tooltip_template': TunableLocalizedString(description='\n            A template for the compound string representation of an encouraged\n            Club rule for this interaction group.\n            \n            e.g. Flirt with {1.String} -> Flirt with Adults\n            ', tuning_group=GroupNames.UI, export_modes=(ExportModes.ClientBinary,)), 'tooltip_template_negative': TunableLocalizedString(description="\n            A template for the compound string representation of a discouraged\n            Club rule for this interaction group.\n            \n            e.g. Don't Use Alien Powers on {0.String} -> Don't Use Alien Powers\n            on Teenagers\n            ", tuning_group=GroupNames.UI, export_modes=(ExportModes.ClientBinary,)), 'category': TunableEnumEntry(description='\n            The category this interaction group should be associated with when\n            shown in the UI.\n            ', tunable_type=ClubInteractionGroupCategory, default=ClubInteractionGroupCategory.OTHER, export_modes=(ExportModes.ClientBinary,)), 'affordances': TunableSet(description='\n            A set of affordances associated with this interaction group.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True)), 'affordance_lists': TunableSet(description=',\n            A set of affordance lists associated with this interaction group.\n            ', tunable=TunableAffordanceListReference(pack_safe=True)), 'child_safe': Tunable(description='\n            If checked, this interaction group can be associated with children\n            when building ClubRules. If unchecked, we will disallow this.\n            ', tunable_type=bool, default=True, export_modes=(ExportModes.ClientBinary,)), 'teen_safe': Tunable(description='\n            If checked, this interaction group can be associated with teens when\n            building ClubRules. If unchecked, we will disallow this.\n            ', tunable_type=bool, default=True, export_modes=(ExportModes.ClientBinary,)), 'club_bucks_reward': Tunable(description='\n            The number of Club Bucks to reward a Sim following a rule that \n            encourages this InteractionGroup whenever the timer goes off.  The \n            tuning for how often the timer goes off can be found in ClubTunables.\n            ', tunable_type=int, default=1), 'is_targeted': Tunable(description='\n            If checked, this interaction group contains interactions that\n            target other Sims. If unchecked, this interaction group contains\n            interactions that do not target other Sims.\n            ', tunable_type=bool, default=True, export_modes=(ExportModes.ClientBinary,)), 'category_icon': TunableIcon(description='\n            The icon associated with this Interaction Group.\n            ', allow_none=True, export_modes=(ExportModes.ClientBinary,))}

    def __iter__(self):
        all_items = set(affordance for affordance in self.affordances)
        for affordance_list in self.affordance_lists:
            all_items.update(set(affordance for affordance in affordance_list))
        yield from all_items

class ClubRule(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'action': TunableReference(description='\n            The ClubInteractionGroup that this rule applies to.\n            ', manager=services.get_instance_manager(sims4.resources.Types.CLUB_INTERACTION_GROUP), display_name='1. Action'), 'with_whom': OptionalTunable(tunable=TunableClubRuleCriteriaVariant(description='\n                If specified, this rule will only apply to cases where the\n                actions set in "1_action" are targeting a Sim that matches\n                these criteria.\n                '), display_name='2. With Whom'), 'restriction': TunableVariant(description='\n            Whether this rule encourages or discourages its action.\n            ', locked_args={'Encouraged': ClubRuleEncouragementStatus.ENCOURAGED, 'Discouraged': ClubRuleEncouragementStatus.DISCOURAGED}, default='Encouraged', display_name='3. Restriction')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.club = None
        if self.with_whom is not None:
            self.with_whom = self.with_whom()

    @property
    def is_encouraged(self):
        return self.restriction == ClubRuleEncouragementStatus.ENCOURAGED

    def register_club(self, club):
        self.club = club
        if self.with_whom is not None:
            self.with_whom.register_club(club)
(_, TunableClubRuleSnippet) = snippets.define_snippet('ClubRule', ClubRule.TunableFactory())
class ClubSeed(metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.CLUB_SEED)):

    class _ClubHangoutNone(HasTunableSingletonFactory, AutoFactoryInit):

        def get_hangout_data(self):
            return (ClubHangoutSetting.HANGOUT_NONE, None, 0)

    class _ClubHangoutVenue(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'venue_type': TunableReference(manager=services.get_instance_manager(sims4.resources.Types.VENUE))}

        def get_hangout_data(self):
            return (ClubHangoutSetting.HANGOUT_VENUE, self.venue_type, 0)

    class _ClubHangoutLot(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'lot': TunableLotDescription()}

        def get_hangout_data(self):
            lot_id = get_lot_id_from_instance_id(self.lot)
            zone_id = services.get_persistence_service().resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
            return (ClubHangoutSetting.HANGOUT_LOT, None, zone_id)

    INSTANCE_TUNABLES = {'name': TunableLocalizedString(description="\n            This Club's display name.\n            ", tuning_group=GroupNames.UI, export_modes=ExportModes.All), 'icon': TunableIcon(tuning_group=GroupNames.UI), 'club_description': TunableLocalizedString(description="\n            This Club's description.\n            ", tuning_group=GroupNames.UI, export_modes=ExportModes.All), 'initial_number_of_memebers': TunableInterval(description='\n            An interval specifying the maximum and minimum initial number of\n            members, including the Club leader, this club will be created with.\n            \n            Maximum number of initial members corresponds to the maximum number\n            of members allowed in a club.\n            ', tunable_type=int, default_lower=8, default_upper=10, minimum=1, maximum=10), 'hangout': TunableVariant(description='\n            Specify where this Club regularly hangs out.\n            ', no_hangout=_ClubHangoutNone.TunableFactory(), venue=_ClubHangoutVenue.TunableFactory(), lot=_ClubHangoutLot.TunableFactory(), default='no_hangout'), 'membership_criteria': TunableSet(description='\n            A set of criteria that all club members must pass to be admitted to\n            and remain a member of this club.\n            ', tunable=TunableClubAdmissionCriteriaVariant(), maxlength=MAX_MEMBERSHIP_CRITERIA), 'club_rules': TunableSet(description='\n            A set of rules that all club members must adhere to.\n            ', tunable=TunableClubRuleSnippet(pack_safe=True), maxlength=MAX_CLUB_RULES), 'invite_only': Tunable(description="\n            If checked, this Club is invite-only and Sims cannot join unless\n            they're invited to. If unchecked, Sims can join this Club without\n            being asked.\n            ", tunable_type=bool, default=False), 'unlocked_rewards': TunableSet(description="\n            A set of ClubRewards this club will have pre-unlocked when it's\n            created.\n            ", tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK), pack_safe=True)), 'associated_color': OptionalTunable(TunableEnumEntry(description='\n            The color tag associated with this Club.\n            ', tunable_type=Tag, default=Tag.INVALID, pack_safe=True, tuning_group=GroupNames.CLOTHING_CHANGE)), 'uniform_male_child': OptionalTunable(TunablePackSafeResourceKey(description='\n            A uniform for male children in this club.\n            ', resource_types=(sims4.resources.Types.SIMINFO,), tuning_group=GroupNames.CLOTHING_CHANGE)), 'uniform_female_child': OptionalTunable(TunablePackSafeResourceKey(description='\n            A uniform for female children in this club.\n            ', resource_types=(sims4.resources.Types.SIMINFO,), tuning_group=GroupNames.CLOTHING_CHANGE)), 'uniform_male_adult': OptionalTunable(TunablePackSafeResourceKey(description='\n            A uniform for male adult-sized Sims in this club.\n            ', resource_types=(sims4.resources.Types.SIMINFO,), tuning_group=GroupNames.CLOTHING_CHANGE)), 'uniform_female_adult': OptionalTunable(TunablePackSafeResourceKey(description='\n            A uniform for female adult-sized Sims in this club.\n            ', resource_types=(sims4.resources.Types.SIMINFO,), tuning_group=GroupNames.CLOTHING_CHANGE)), 'club_outfit_setting': TunableEnumEntry(description='\n            The Club Outfit Setting that the group is set to when it is created.\n            \n            This needs to be set properly so that when a player starts a\n            gathering the Sims will spin into the appropriate outfit. For \n            example if you want to create a pre-seeded club that has an outfit\n            that is setup in Club CAS then this should be set to OVERRIDE. If\n            instead that group is supposed to use the clubs colors then set\n            this to COLOR.\n            ', tunable_type=ClubOutfitSetting, default=ClubOutfitSetting.NO_OUTFIT, tuning_group=GroupNames.CLOTHING_CHANGE), 'associated_style': OptionalTunable(description="\n            If Enabled allows tuning the Style of the club outfit.\n            \n            You'll need to use an appropriate style Tag since Tag includes lots\n            of different things. An exmaple would be Style_Boho or Style_Country.\n            \n            The club_outfit_setting does not need to be set to STYLE in order \n            to tune this. If this is tuned and the club_outfit_setting is not\n            set to STYLE this will still show up as the default Style choice\n            for the club in the UI.\n            ", tunable=TunableEnumEntry(description='\n                The tag representation of the desired style. For instance\n                Style_Country.\n                ', tunable_type=Tag, default=Tag.INVALID, pack_safe=True, tuning_group=GroupNames.CLOTHING_CHANGE))}

    @classmethod
    def create_club(cls, leader=None, members=None, refresh_cache=True):
        club_service = services.get_club_service()
        if club_service is None:
            logger.error('Attempting to create a club {} when there is no Club Service.', cls)
            return
        if leader is not None and members is not None:
            seed_members = (leader, members)
        else:
            seed_members = None
        return club_service.create_club(club_seed=cls, seed_members=seed_members, from_load=False, refresh_cache=refresh_cache)
