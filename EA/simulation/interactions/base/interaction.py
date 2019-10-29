from collections import OrderedDict, namedtuple, defaultdictfrom contextlib import contextmanagerfrom weakref import WeakKeyDictionary, WeakSetimport collectionsimport copyimport functoolsimport itertoolsimport weakreffrom protocolbuffers import Sims_pb2from animation.animation_constants import InteractionAsmTypefrom animation.animation_overrides_liability import AnimationOverridesLiabilityfrom animation.animation_utils import StubActor, with_event_handlers, flush_all_animationsfrom animation.arb_element import distribute_arb_elementfrom animation.posture_manifest import PostureManifest, MATCH_ANY, MATCH_NONE, PostureManifestEntry, AnimationParticipantfrom animation.tunable_animation_overrides import TunableAnimationOverridesfrom balloon.tunable_balloon import TunableBalloonfrom buffs.tunable import RemoveBuffLiabilityfrom careers.career_event_liabilities import CareerEventTravelLiabilityfrom carry.carry_utils import create_two_handed_carry_constraint, hand_to_track, set_carry_track_param_if_needed, holster_carried_object, interact_with_carried_object, get_carried_objects_genfrom crafting.crafting_station_liability import CraftingStationLiabilityfrom date_and_time import TimeSpan, create_time_spanfrom distributor.shared_messages import IconInfoData, EMPTY_ICON_INFO_DATAfrom distributor.system import Distributorfrom element_utils import build_critical_section, build_critical_section_with_finally, build_elementfrom event_testing.resolver import DoubleSimResolverfrom event_testing.tests import TestListfrom interactions import ParticipantType, PipelineProgress, TargetType, ParticipantTypeSavedActor, ParticipantTypeSingleSim, ParticipantTypeSituationSimsfrom interactions.base.basic import TunableBasicContentSet, TunableBasicExtras, AFFORDANCE_LOADED_CALLBACK_STRfrom interactions.constraint_variants import TunableConstraintVariantfrom interactions.constraints import ANYWHERE, Nowherefrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.interaction_finisher import FinishingType, InteractionFinisherfrom interactions.item_consume import InteractionItemCostVariantfrom interactions.liability import SharedLiabilityfrom interactions.rabbit_hole import RabbitHoleLiabilityfrom interactions.utils import sim_focusfrom interactions.utils.autonomy_op_list import AutonomyAdListfrom interactions.utils.content_score_mixin import ContentScoreMixinfrom interactions.utils.display_name import TunableDisplayNameVariant, TunableDisplayNameWrapperfrom interactions.utils.forwarding import Forwardingfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom interactions.utils.interaction_liabilities import AUTONOMY_MODIFIER_LIABILITY, AutonomyModifierLiability, ANIMATION_CONTEXT_LIABILITY, AnimationContextLiability, STAND_SLOT_LIABILITY, RESERVATION_LIABILITY, UNCANCELABLE_LIABILITYfrom interactions.utils.lighting_liability import LightingLiabilityfrom interactions.utils.localization_tokens import LocalizationTokensfrom interactions.utils.outcome import TunableOutcomefrom interactions.utils.reserve import TunableReserveObjectfrom interactions.utils.route_goal_suppression_liability import RouteGoalSuppressionLiabilityfrom interactions.utils.sim_focus import TunableFocusElement, with_sim_focus, SimFocusfrom interactions.utils.statistic_element import ExitCondition, ConditionalInteractionActionfrom interactions.utils.teleport_liability import TeleportLiabilityfrom interactions.utils.temporary_state_change_liability import TemporaryStateChangeLiabilityfrom interactions.utils.tunable import TimeoutLiability, TunableStatisticAdvertisements, SaveLockLiability, TunableContinuation, CriticalPriorityLiability, GameSpeedLiability, PushAffordanceOnRouteFailLiabilityfrom interactions.utils.tunable_icon import TunableIconVariant, TunableIconfrom interactions.utils.user_cancelable_chain_liability import UserCancelableChainLiabilityfrom interactions.vehicle_liabilities import VehicleLiabilityfrom objects import ALL_HIDDEN_REASONSfrom objects.components.game.game_challenge_liability import GameChallengeLiabilityfrom objects.slots import get_surface_height_parameter_for_objectfrom pets.missing_pets_liability import MissingPetLiabilityfrom postures import ALL_POSTURESfrom postures.posture_specs import PostureSpecVariablefrom postures.proxy_posture_owner_liability import ProxyPostureOwnerLiabilityfrom restaurants.restaurant_liabilities import RestaurantDeliverFoodLiabilityfrom restaurants.restaurant_tuning import get_restaurant_zone_directorfrom sims.daycare import DaycareLiabilityfrom sims.funds import FundsSource, get_funds_for_source, FundsTuningfrom sims.household_utilities.utility_types import Utilitiesfrom sims.outfits.outfit_change import ChangeOutfitLiabilityfrom sims.sim_info_tests import GenderPreferenceTestfrom sims.template_affordance_provider.tunable_provided_template_affordance import TunableProvidedTemplateAffordancefrom sims4.callback_utils import consume_exceptions, CallableListfrom sims4.collections import frozendictfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.math import MAX_UINT64from sims4.sim_irq_service import yield_to_irqfrom sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import OptionalTunable, TunableTuple, TunableSimMinute, TunableSet, HasTunableReference, Tunable, TunableList, TunableVariant, TunableEnumEntry, TunableReference, TunableRange, TunableMapping, TunableThreshold, TunablePackSafeReferencefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classproperty, flexproperty, flexmethod, constpropertyfrom singletons import DEFAULT, EMPTY_SET, UNSETfrom situations.situation_liabilities import CreateSituationLiability, SituationSimParticipantProviderLiabilityfrom socials.social_tests import SocialContextTestfrom statistics.skill import TunableSkillLootDatafrom tag import Tagfrom teleport.teleport_type_liability import TeleportStyleLiabilityfrom ui.ui_dialog import UiDialogOkCancelfrom ui.ui_dialog_element import UiDialogElementfrom uid import unique_idfrom whims.whims_tracker import HideWhimsLiabilityimport alarmsimport animationimport animation.asmimport cachesimport clockimport distributorimport element_utilsimport enumimport event_testing.resolverimport event_testing.resultsimport event_testing.test_events as test_eventsimport event_testing.testsimport gsi_handlersimport interactions.baseimport interactions.si_stateimport interactions.utils.exit_condition_managerimport objects.components.typesimport pathsimport servicesimport simsimport sims4.logimport sims4.resourcesimport snippetsimport telemetry_helperlogger = sims4.log.Logger('Interactions')TELEMETRY_GROUP_INTERACTION = 'INTR'TELEMETRY_HOOK_INTERACTION_END = 'IEND'TELEMETRY_FIELD_INTERACTION_ID = 'intr'TELEMETRY_FIELD_INTERACTION_RUNNING_TIME = 'mins'interaction_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_INTERACTION)SIM_YIELD_INTERACTION_GET_PARTICIPANTS_MOD = 1000interaction_get_particpants_call_count = 0
class CancelablePhase(enum.Int, export=False):
    NEVER = 0
    ALWAYS = 1
    RUNNING = 2

class InteractionIntensity(DynamicEnum):
    Default = 0

class InteractionQueueVisualType(enum.Int):
    SIMPLE = 0
    PARENT = 1
    MIXER = 2
    POSTURE = 3

    @staticmethod
    def get_interaction_visual_type(visual_type):
        if visual_type == InteractionQueueVisualType.PARENT:
            return Sims_pb2.Interaction.PARENT
        if visual_type == InteractionQueueVisualType.MIXER:
            return Sims_pb2.Interaction.MIXER
        if visual_type == InteractionQueueVisualType.POSTURE:
            return Sims_pb2.Interaction.POSTURE
        return Sims_pb2.Interaction.SIMPLE

class CancelGroupInteractionType(enum.Int):
    ALL = 0
    USER_DIRECTED_ONLY = 1
ROUTING_POSTURE_INTERACTION_ID = MAX_UINT64 - 1
class InteractionFailureOptions:
    FAILURE_REASON_TESTS = TunableList(description='\n            A List in the format of (TunableTestSet, TunableAnimOverrides).\n            When an interaction fails because of its tests, we execute these\n            tests and the first one that passes determines the AnimOverrides\n            that will be used to show failure to the player.\n            ', tunable=TunableTuple(test_set=event_testing.tests.TunableTestSet(), anim_override=TunableAnimationOverrides()))
    ROUTE_FAILURE_AFFORDANCE = TunableReference(description="\n            A Tunable Reference to the Interaction that's pushed on a Sim when\n            their tests fail and they need to display failure to the user.\n            ", manager=services.affordance_manager())

@unique_id('id', 1, MAX_UINT64 - 2)
class Interaction(HasTunableReference, ContentScoreMixin, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)):
    DEBUG_NAME_FACTORY = OptionalTunable(TunableLocalizedStringFactory(description='\n                Format for displaying interaction names for interactions that\n                are debug interactions.', display_name='Debug Interaction Name Pattern'))
    SIMOLEON_DELTA_MODIFIES_AFFORDANCE_NAME = Tunable(description='\n            Enables the display of Simoleon delta information in the choices\n            menu.\n            ', tunable_type=bool, default=True)
    SIMOLEON_DELTA_MODIFIES_INTERACTION_NAME = Tunable(description='\n            Enables the display of Simoleon delta information on running\n            interactions.\n            ', tunable_type=bool, default=True)
    SIMOLEON_COST_NAME_FACTORY = OptionalTunable(TunableLocalizedStringFactory(description='\n                Format for displaying interaction names on interactions that\n                have Simoleon costs.\n                ', display_name='Simoleon Cost Interaction Name Pattern'))
    SIMOLEON_GAIN_NAME_FACTORY = OptionalTunable(TunableLocalizedStringFactory(description='\n                Format for displaying interaction names on interactions that\n                have Simoleon gains.\n                ', display_name='Simoleon Gain Interaction Name Pattern'))
    ITEM_COST_NAME_FACTORY = OptionalTunable(TunableLocalizedStringFactory(description='\n                Format for displaying item cost on the interaction name so\n                player is aware what the interaction will consume.\n                ', display_name='Item Cost Interaction Name Pattern'))
    MAX_NOWHERE_MIXERS = 20
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'display_name': TunableLocalizedStringFactory(description='\n            The localized name of this interaction.  It takes two tokens, the\n            actor (0) and target object (1) of the interaction.\n            ', allow_none=True, tuning_group=GroupNames.CORE), 'display_name_in_queue': OptionalTunable(description='\n        If enabled, the interaction has a different display name once it has\n        been selected and is visible in the queue. If disabled, its name in the\n        queue is simply whatever appeared in the Pie Menu, barring any further\n        visual overrides.\n        ', tunable=TunableLocalizedStringFactory(description="\n            The interaction's display name once it is added to the interaction\n            queue.\n            "), tuning_group=GroupNames.CORE), 'display_tooltip': OptionalTunable(description='\n            The tooltip to show on the pie menu option if this interaction\n            passes its tests.\n            ', tunable=TunableLocalizedStringFactory(), tuning_group=GroupNames.UI), 'display_name_text_tokens': LocalizationTokens.TunableFactory(description="\n            Localization tokens to be passed into 'display_name'.\n            For example, you could use a participant or you could also pass in \n            statistic and commodity values.\n            ", tuning_group=GroupNames.UI), 'display_name_overrides': TunableDisplayNameVariant(description='\n            Set name modifiers or random names.\n            ', tuning_group=GroupNames.UI), 'display_name_wrappers': OptionalTunable(description='\n            If enabled, the first wrapper within the list to pass tests will\n            be applied to the display name.\n            ', tunable=TunableDisplayNameWrapper.TunableFactory(), tuning_group=GroupNames.UI), '_icon': TunableIconVariant(description='\n            The icon to be displayed in the interaction queue.\n            ', default_participant_type=ParticipantType.Object, tuning_group=GroupNames.UI), 'pie_menu_icon': OptionalTunable(description='\n        If enabled, there will be an icon on the pie menu.\n        ', tunable=TunableIconVariant(description='\n            The icon to display in the pie menu.\n            ', tuning_group=GroupNames.UI)), 'pie_menu_priority': TunableRange(description="\n            Higher priority interactions will show up first on the pie menu.\n            Interactions with the same priority will be alphabetical. This will\n            not override the content_score for socials. Socials with a high\n            score will still show on the top-most page of the pie menu. It's\n            suggested that you start with lower numbers instead of\n            automatically tuning something to a 10 just to make it show up on\n            the first page.\n            ", tunable_type=int, default=0, minimum=0, maximum=10, tuning_group=GroupNames.UI), 'allow_autonomous': Tunable(description='\n            If checked, this interaction may be chosen by autonomy for Sims to\n            run autonomously.\n            ', tunable_type=bool, default=True, needs_tuning=True, tuning_group=GroupNames.AVAILABILITY), 'allow_user_directed': Tunable(description='\n            If checked, this interaction may appear in the pie menu and be\n            chosen by the player.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.AVAILABILITY), 'allow_from_world': Tunable(description='\n            If checked, this interaction may be started while the object is in\n            the world (as opposed to being in an inventory).\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.AVAILABILITY), 'allow_from_sim_inventory': Tunable(description="\n            If checked, this interaction may be started while the object is in\n            a Sim's inventory.\n            ", tunable_type=bool, default=False, tuning_group=GroupNames.AVAILABILITY), 'allow_from_object_inventory': Tunable(description="\n            If checked, this interaction may be started while the object is in\n            another object's inventory.\n            ", tunable_type=bool, default=False, tuning_group=GroupNames.AVAILABILITY), '_forwarding': OptionalTunable(description='\n        If enabled, this interaction will be available by clicking on the parent\n        of this object (for example, on an oven containing a backing pan) or by\n        clicking on a Sim using this object (for example, "order drink" is\n        available both on a bar and the Sim tending the bar).\n        ', disabled_name="Don't_Forward", enabled_name='Forward', tunable=Forwarding.TunableFactory(), tuning_group=GroupNames.AVAILABILITY), 'allow_from_portrait': Tunable(description='\n            If checked, this interaction may be surfaced from the portrait icon\n            of a Sim in the Relationship panel.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.AVAILABILITY), 'allow_while_save_locked': Tunable(description='\n            If checked, this interaction is allowed to run while saving is\n            currently blocked. For example, saving is locked when a Sim is in\n            the process of dying and is waiting to be reaped by the grim\n            reaper. While this is happening we do not want you to be able to\n            travel, so all travel interactions have this tunable unchecked.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.PERSISTENCE), '_cancelable_by_user': TunableVariant(description='\n            Define the ability for the player to cancel this interaction.            \n            ', require_confirmation=UiDialogOkCancel.TunableFactory(description='\n                A dialog prompting the player for confirmation as to whether or\n                not they want to cancel this interaction. The interaction will\n                cancel only if the player responds affirmatively. \n                '), locked_args={'allow_cancelation': CancelablePhase.ALWAYS, 'prohibit_cancelation': CancelablePhase.NEVER, 'only_while_running': CancelablePhase.RUNNING}, default='allow_cancelation', tuning_group=GroupNames.UI), '_must_run': Tunable(description='\n            If checked, nothing may cancel this interaction.  Not to be used\n            lightly.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.UI), 'time_overhead': TunableSimMinute(description="\n            Amount of time, in sim minutes, that autonomy believes that this\n            interaction will take to run. This value does not represent an\n            actual value of how long the interaction should run, but rather an\n            estimation of how long it will run for autonomy calculate the\n            efficiency of the interaction. Efficiency is used to model distance\n            attenuation.  If this value is high, the sim won't care as much how\n            far away it is.\n            ", default=10, minimum=1, tuning_group=GroupNames.AUTONOMY), 'visible': Tunable(description='\n            If checked, this interaction will be visible in the UI when queued\n            or running.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.UI), 'always_show_route_failure': Tunable(description="\n        If checked, this interaction will always attempt to show route failures\n        even if it's invisible.\n        ", tunable_type=bool, default=False, tuning_group=GroupNames.UI), 'simless': Tunable(description='\n            If unchecked, there must be an active Sim to run it. If checked, no\n            Sim will be available to the interaction when it runs. Debug\n            interactions are often Simless.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.AVAILABILITY), 'target_type': TunableEnumEntry(description='\n            Indicates the type of target this interaction has: a specific Sim,\n            a group, or no one.\n                                        \n            Setting this value here will determine the animation resource\n            required for interaction to run.\n                                        \n            Examples:\n             * If sim "told a joke" and you want all sims in the group to react,\n             this should be set to GROUP.\n                                        \n             * If sim poke fun at another sim, you want to set this to TARGET.\n            ', tunable_type=TargetType, default=TargetType.GROUP, tuning_group=GroupNames.ANIMATION), 'asm_actor_overrides': TunableList(description='\n            Override ASM actors with tuned participants.\n            \n            Note: This is a very seldom used override. If you think you need it\n            talk to a GPE.\n            ', tunable=TunableTuple(actor_name=Tunable(description='\n                    The name of the parameter to override in the ASM.\n                    ', tunable_type=str, default=None), actor_participant=TunableEnumEntry(description='\n                    The participant type that will be used to get the participant\n                    that will provide the override value.\n                    ', tunable_type=ParticipantType, default=ParticipantType.Object)), tuning_group=GroupNames.ANIMATION), 'debug': Tunable(description='\n            If checked, this interaction will only be available from the debug\n            pie menu.  The debug pie menu is not available in release builds and\n            only appears when shift-clicking to bring up the pie menu.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.AVAILABILITY), 'cheat': Tunable(description='\n            If checked, this interaction will only be available from the cheat\n            pie menu. The cheat pie menu is available in all builds when cheats\n            are enabled, and only appears when shift-clicking to bring up the\n            pie menu.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.AVAILABILITY), 'automation': Tunable(description='\n            If checked, this interaction will only be available from the\n            automation mode of the game. Note that this is ignored if the\n            cheat is marked as debug while the game is non-optimized.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.AVAILABILITY), '_static_commodities': TunableList(description='\n            The list of static commodities to which this affordance will\n            advertise.\n            ', tunable=TunableTuple(description='\n                A single chunk of static commodity scoring data.\n                ', static_commodity=TunableReference(description='\n                    The type of static commodity offered by this affordance.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.STATIC_COMMODITY), pack_safe=True, reload_dependent=True), desire=Tunable(description='\n                    The autonomous desire to fulfill this static commodity.\n                    This is how much of the static commodity the Sim thinks\n                    they will get.  This is, of course, a blatant lie.\n                    ', tunable_type=float, default=1)), tuning_group=GroupNames.AUTONOMY), '_affordance_key_override_for_autonomy': OptionalTunable(description='\n        If set, this string will take the place of the affordance as the key\n        used in autonomy scoring.  This will cause autonomy to see two\n        affordances as the same for the purposes of grouping.\n        \n        For example, if you have bed_sleep_single and bed_sleep_double, you can\n        override them to both be "bed_sleep".  Autonomy will see them as the\n        same affordance and will only choose one to consider when throwing the\n        weighted random at the end. It will also apply object preference,\n        treating them as the same affordance.\n        ', tunable=Tunable(tunable_type=str, default=''), tuning_group=GroupNames.AUTONOMY), 'outcome': TunableOutcome(outcome_locked_args={'cancel_si': None}, allow_route_events=True, tuning_group=GroupNames.CORE), 'skill_loot_data': TunableSkillLootData(description='\n            Loot Data for DynamicSkillLootOp. This will only be used if in the\n            loot list of the outcome there is a dynamic loot op.\n            ', tuning_group=GroupNames.STATE), 'provided_template_affordances': OptionalTunable(description='\n        If enabled, allows the Actor Sims running this interaction to provide\n        a suite of interactions that have template data.\n        ', tunable=TunableProvidedTemplateAffordance(description='\n            Sims will provide the tuned list of affordances for the\n            specified duration.\n            '), tuning_group=GroupNames.STATE), '_false_advertisements': TunableStatisticAdvertisements(description='\n            Fake advertisements make the interaction more enticing to autonomy\n            by promising things it will not deliver.\n            ', tuning_group=GroupNames.AUTONOMY), '_hidden_false_advertisements': TunableStatisticAdvertisements(description="\n            Fake advertisements that are hidden from the Sim.  These ads will\n            not be used when determining which interactions solve for a\n            commodity, but it will be used to calculate the final score.\n            \n            For example: You can tune the bubble bath to provide hygiene as\n            normal, but to also have a hidden ad for fun.  Sims will prefer a\n            bubble bath when they want to solve hygiene and their fun is low,\n            but they won't choose to take a bubble bath just to solve for fun.\n            ", tuning_group=GroupNames.AUTONOMY), '_constraints': TunableList(description='\n            A list of constraints that must be fulfilled in order to interact\n            with this object.\n            ', tunable=TunableTuple(constrained_participant=TunableEnumEntry(description='\n                    The participant tuned here will have this constraint \n                    applied to them.\n                    ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), constraints=TunableList(description='\n                    Species-based constraints. Define different constraints\n                    depending on species.\n                    ', tunable=TunableTuple(value=TunableConstraintVariant(description='\n                            A constraint that must be fulfilled in order to interact\n                            with this object.\n                            ')), minlength=1)), tuning_group=GroupNames.CORE), '_constraints_actor': TunableEnumEntry(description='\n            The Actor used to generate _constraints relative to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object, tuning_group=GroupNames.CORE), '_require_current_posture': Tunable(description="\n            If checked, the actor's current posture will be added to the\n            constraints for this interaction. This means that the Sim will not\n            consider changing posture to satisfy this interaction. This can be\n            useful for stuff like odor reactions, which shouldn't force the Sim\n            to change posture and shouldn't waste time considering every seat\n            on the lot.\n            ", tunable_type=bool, default=False, tuning_group=GroupNames.POSTURE), '_multi_surface': Tunable(description="\n        If checked, this interaction will build all of its constraints to work\n        on multiple surfaces.\n        \n        For example, watch_tv is marked as multi_surface and there is a TV on\n        the ground near a pool. Sims will be able to watch this TV while\n        standing around outside of the pool, but also while swimming in the\n        nearby pool. If watch_tv was not multi_surface, Sims would only be able\n        to stand around outside of the pool in order to watch it.\n        \n        This will only apply to routing surfaces on the same level. A pool and\n        the floor that pool is on will both satisfy this interaction's\n        constraints, but different floors or pools on different floors will\n        not.\n        ", tunable_type=bool, default=True, tuning_group=GroupNames.POSTURE), 'fade_sim_out': Tunable(description='\n            If set to True, this interaction will fade the Sim out as they approach\n            the destination constraint for this interaction.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.SPECIAL_CASES), 'tests': event_testing.tests.TunableTestSet(tuning_group=GroupNames.CORE), 'test_globals': event_testing.tests.TunableGlobalTestSet(description='\n            A set of global tests that are always run before other tests. All\n            tests must pass in order for the interaction to run.\n            ', tuning_group=GroupNames.CORE), 'test_autonomous': event_testing.tests.TunableTestSet(description='\n            A set of tests that are only run for interactions being considered \n            by autonomy.\n            ', tuning_group=GroupNames.AUTONOMY), 'basic_reserve_object': OptionalTunable(description='\n            If enabled, control which objects this interaction reserves for use.\n            If unset, this interaction will not reserve any objects for use.\n            ', tunable=TunableReserveObject(), enabled_by_default=True, tuning_group=GroupNames.STATE), 'basic_focus': TunableVariant(description='\n            Control the focus (gaze) of the actor while running this\n            interaction.\n            ', locked_args={'do_not_change_focus': None, 'disable_focus': False}, default='do_not_change_focus', tunable_focus=TunableFocusElement(), tuning_group=GroupNames.ANIMATION), 'basic_liabilities': TunableList(description="\n            Use basic_liablities to tune a list of tunable liabilities.                     \n            \n            A liability is a construct that is associated to an interaction the\n            moment it is added to the queue. This is different from\n            basic_content and basic_extras, which only affect interactions that\n            have started running.\n            \n            e.g. The 'timeout' tunable is a liability, because its behavior is\n            triggered the moment the SI is enqueued - by keeping track of how\n            long it takes for it to start running and canceling if the timeout\n            is hit.\n            ", tunable=TunableVariant(timeout=TimeoutLiability.TunableFactory(), save_lock=SaveLockLiability.TunableFactory(), teleport=TeleportLiability.TunableFactory(), lighting=LightingLiability.TunableFactory(), crafting_station=CraftingStationLiability.TunableFactory(), daycare=DaycareLiability.TunableFactory(), critical_priority=CriticalPriorityLiability.TunableFactory(), career_event_travel=CareerEventTravelLiability.TunableFactory(), game_speed=GameSpeedLiability.TunableFactory(), hide_whims=HideWhimsLiability.TunableFactory(), remove_buff=RemoveBuffLiability.TunableFactory(), push_affordance_on_route_fail=PushAffordanceOnRouteFailLiability.TunableFactory(), route_goal_suppression=RouteGoalSuppressionLiability.TunableFactory(), outfit_change=ChangeOutfitLiability.TunableFactory(), game_challenge_liability=GameChallengeLiability.TunableFactory(), restaurant_deliver_food_liability=RestaurantDeliverFoodLiability.TunableFactory(), teleport_style_liability=TeleportStyleLiability.TunableFactory(), animation_overrides=AnimationOverridesLiability.TunableFactory(), rabbit_hole=RabbitHoleLiability.TunableFactory(), user_cancelable_chain=UserCancelableChainLiability.TunableFactory(), create_situation=CreateSituationLiability.TunableFactory(), missing_pet=MissingPetLiability.TunableFactory(), proxy_posture_owner=ProxyPostureOwnerLiability.TunableFactory(), vehicles=VehicleLiability.TunableFactory(), temporary_state_change=TemporaryStateChangeLiability.TunableFactory()), tuning_group=GroupNames.STATE), 'basic_extras': TunableBasicExtras(tuning_group=GroupNames.CORE), 'basic_content': TunableBasicContentSet(description='\n            Use basic_content to define the nature of this interaction. Any\n            looping animation, autonomy, statistic gain, and any other periodic\n            change is tuned in. Also, exit conditions will be specified here.\n            \n            Depending on the type of basic_content you select, some options\n            may or may not be available.\n            \n            Please see the variant elements descriptions to determine how\n            each specific option affects the behavior of this interaction.\n            ', one_shot=True, looping_animation=True, no_content=True, default='no_content', tuning_group=GroupNames.CORE), 'confirmation_dialog': OptionalTunable(tunable=TunableTuple(dialog=UiDialogElement.TunableFactory(description='\n                    Prompts the user with an Ok Cancel Dialog. This will stop the\n                    interaction from running if the user chooses the cancel option.\n                    '), continuation_on_cancel=OptionalTunable(description='\n                    If enabled, and the dialog is not accepted, then this\n                    continuation will be pushed.\n                    ', tunable=TunableContinuation(description='\n                        The tuned continuation to push when the dialog is not\n                        accepted.\n                        '))), tuning_group=GroupNames.UI), 'intensity': TunableEnumEntry(description='\n            The intensity of response animations for this interaction. When we\n            build outcomes for the interaction, we pass this field to the\n            associated ASM.\n            ', tunable_type=InteractionIntensity, default=InteractionIntensity.Default, tuning_group=GroupNames.ANIMATION), 'category': TunablePackSafeReference(description='\n            Pie menu category. Helps declare display name, priority, icon,\n            parent, mood overrides etc.\n            ', manager=services.get_instance_manager(sims4.resources.Types.PIE_MENU_CATEGORY), allow_none=True, tuning_group=GroupNames.UI), 'category_on_forwarded': OptionalTunable(description='\n            Pie menu category when this interaction is forwarded from inventory\n            object to inventory owner.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.PIE_MENU_CATEGORY)), tuning_group=GroupNames.UI), 'posture_preferences': TunableTuple(description='\n            Options relating to posture preferences for this interaction.\n            ', prefer_surface=Tunable(description='\n                If checked, a Sim will prefer to perform this interaction at a\n                surface.\n                ', tunable_type=bool, default=False), apply_penalties=Tunable(description='\n                If checked, posture penalties will be applied when selecting a\n                posture in which to perform this interaction.\n                ', tunable_type=bool, default=False), prefer_clicked_part=Tunable(description='\n                If True, this interaction will prefer to take the Sim to the part\n                near where you clicked in world.\n                ', tunable_type=bool, default=True), require_current_constraint=Tunable(description='\n                If checked, a Sim will never violate its current geometric\n                constraints in order to find a place to run the interaction.\n                ', tunable_type=bool, default=False), posture_cost_overrides=TunableMapping(description='\n                For any posture in this mapping, its cost is overriden by the\n                specified value for the purpose of transitioning for this\n                interaction.\n                \n                For example, Sit is a generally cheap posture. However, some\n                interactions (such as Nap), would want to penalize Sit in favor\n                of something more targeted (such as the two-seated version of\n                nap).\n                ', key_type=TunableReference(manager=services.posture_manager()), value_type=Tunable(description='\n                    The cost override for the specified posture.\n                    ', tunable_type=int, default=0)), disable_all_scoring=Tunable(description="\n                When this is turned on there will be no scoring of goals at all.\n                Essentially this will make the goals rely totally on distance.\n                This should really only be used for interactions that are only\n                run as continuations. Basically if you run an interaction that\n                gets you to the exact spot you want the Sim and then you want\n                to run something else without them moving you would want to \n                enable this. It's for a very specific use case. Use with\n                caution.\n                \n                Default scoring behavior will happen when this is turned off.\n                ", tunable_type=bool, default=False), tuning_group=GroupNames.POSTURE), 'interaction_category_tags': TunableSet(description='\n            This attribute is used to tag an interaction to allow for\n            searching, testing, and categorization. An example would be using a\n            tag to selectively test certain interactions. On each of the\n            interactions you want to test together you would add the same tag,\n            then the test routine would only test interactions with that tag.\n            Interactions can have multiple tags.\n            \n            This attribute has no effect on gameplay.\n            ', tunable=TunableEnumEntry(description='\n                These tag values are used for searching, testing, and\n                categorizing interactions.\n                ', tunable_type=Tag, default=Tag.INVALID, pack_safe=True), tuning_group=GroupNames.STATE), 'utility_info': OptionalTunable(TunableList(description='\n                Tuning that specifies which utilities this interaction requires\n                to be run.\n                ', tunable=TunableEnumEntry(Utilities, None)), tuning_group=GroupNames.AVAILABILITY), 'test_incest': Tunable(description='\n            If checked, an incest check must pass for this interaction to be\n            available. This test is only valid for interactions that involve\n            two Sims.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.AVAILABILITY), 'visual_type_override': TunableEnumEntry(description='\n            Specify visual type if you want to override how this interaction\n            will appear in the interaction queue.\n            \n            Example: sitting by default will appear as posture interaction set\n            to simple if you want to make this appear as a normal interaction.\n            ', tunable_type=InteractionQueueVisualType, default=None, tuning_group=GroupNames.UI), 'visual_type_override_data': TunableTuple(description='\n            Overrides interaction queue appearance and behavior of this\n            interaction.\n            ', icon=TunableIcon(allow_none=True), tooltip_text=TunableLocalizedStringFactory(description='\n                The localized name of this interaction when it appear in the\n                running section of the interaction queue.\n                ', default=None, allow_none=True), group_tag=TunableEnumEntry(description='\n                This tag is used for Grouping interactions in the\n                running section of the interaction queue.\n                \n                Example:  Sim is running chat then queues up be_affectionate.\n                Once be_affectionate moves into the running of the section of\n                the queue be_affection will disappear since it is grouped\n                together with sim chat\n                ', tunable_type=Tag, default=Tag.INVALID), group_priority=TunableRange(description='\n                When interactions are grouped into one item in the queue, this\n                is the priority of which interaction will be the top item.\n                ', tunable_type=int, default=1, minimum=1), group_cancel_behavior=TunableEnumEntry(description='\n                Cancel all grouped interactions when one of the interaction is\n                canceled for the following behavior\n                ', tunable_type=CancelGroupInteractionType, default=CancelGroupInteractionType.USER_DIRECTED_ONLY), tuning_group=GroupNames.UI), 'item_cost': InteractionItemCostVariant(tuning_group=GroupNames.SPECIAL_CASES), 'progress_bar_enabled': TunableTuple(description='\n            Set of tuning to display the progress bar when the interaction runs\n            ', bar_enabled=Tunable(description='\n                If checked, interaction will try to show a progress bar when\n                running. Progress bar functionality also depends on the\n                interaction being tuned with proper exit condition and extras\n                that will lead it to that exit condition. e.g.  An interaction\n                with an exit condition for a statistic that reaches a threshold\n                and a tunable extra that increases that statistic as the\n                interaction runs. e.g.  Interaction with tunable time of\n                execution.\n                ', tunable_type=bool, needs_tuning=True, default=True), remember_progress=Tunable(description="\n                If checked, interaction will use the current progress of the \n                statistic from the exit conditions to display where the bar\n                should start.  \n                This is used for interactions that we don't always want to \n                start the progress bar from zero but to display they had been \n                started previously.\n                ", tunable_type=bool, default=False), force_listen_statistic=OptionalTunable(TunableTuple(description="\n                If this is enabled, the progress bar will listen to a specific\n                statistic on a subject of this interaction instead of \n                looking at the interaction's exit conditions.  This means, \n                instead of sending the UI a rate of change during the \n                interaction we will send a message whenever that statistic \n                changes.\n                ", statistic=TunableReference(description='\n                    Statistic to listen to display on the progress bar.\n                    This should not be a commodity with a decay value.\n                    The reason for this is because we will send a message to \n                    the UI for every update on this commodity and decaying \n                    commodities decay every tick, so that will just overload \n                    the number of messages we send.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), subject=TunableEnumEntry(description='\n                    Subject of interaction that the progress bar will listen \n                    for this statistic change.\n                    ', tunable_type=ParticipantType, default=ParticipantType.Actor), target_value=TunableThreshold(description='\n                    Target value of where the progress bar should lead to.\n                    '))), override_min_max_values=OptionalTunable(TunableTuple(description='\n                If this is enabled, we can override the minimum and maximum \n                value of a statistic.  \n                For example, the build rocketship \n                uses a statistic that goes from -100 to 100, but the build \n                interaction only works from 0 to 100.  So for this interaction\n                we want to override the min value to 0 so the progress bar \n                shows properly.  \n                ', statistic=TunableReference(description='\n                    Statistic to look for to override its min or max values \n                    when calculating the progress bar generation.\n                    ', manager=services.statistic_manager()), min_value=OptionalTunable(description='\n                    Override min value\n                    ', tunable=Tunable(description='\n                        Value to use as the new minimum of the specified \n                        statistic \n                        ', tunable_type=float, default=0), enabled_name='specified_min', disabled_name='use_stat_min'), max_value=OptionalTunable(description='\n                    Override max value\n                    ', tunable=Tunable(description='\n                        Value to use as the new maximum of the specified \n                        statistic \n                        ', tunable_type=float, default=0), enabled_name='specified_max', disabled_name='use_stat_max'))), blacklist_statistics=OptionalTunable(description='\n                Set statistics that should be ignored by the progress bar\n                ', tunable=TunableList(description='\n                    List of commodities the progress bar will ignore when \n                    calculating the exit condition that will cause the \n                    interaction to exit.\n                    ', tunable=TunableReference(description='\n                        Statistic to be ignored by the progress bar\n                        ', manager=services.statistic_manager())), enabled_name='specify_blacklist_statistics', disabled_name='consider_all'), interaction_exceptions=TunableTuple(description='\n                Possible exceptions to the normal progress bar rules.\n                For example, music interactions will listen to a tunable \n                time which is hand tuned to match the audio tracks, \n                ', is_music_interaction=Tunable(description='\n                    If checked, interaction will read the tunable track time of\n                    music tracks and use that time to display the progress bar.\n                    e.g.  Piano and violin interactions.\n                    ', tunable_type=bool, default=False)), tuning_group=GroupNames.UI), 'appropriateness_tags': TunableSet(description='\n            A set of tags that define appropriateness for this interaction.  If\n            an appropriateness or inappropriateness test is used for this\n            interaction then it will check the tuned appropriateness tags\n            against the ones that the role state has applied to the actor.\n            ', tunable=TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID, pack_safe=True), tuning_group=GroupNames.AUTONOMY), 'route_start_balloon': OptionalTunable(TunableTuple(description='\n                Allows for a balloon to be played over the actor at the start  \n                of this interaction transition when run autonomously.\n                ', balloon=TunableBalloon(locked_args={'balloon_delay': 0, 'balloon_delay_random_offset': 0}), also_show_user_directed=Tunable(description='\n                    If checked, this balloon also can be shown for this\n                    interaction when it is user-directed.\n                    ', tunable_type=bool, default=False)), tuning_group=GroupNames.UI), 'allowed_to_combine': Tunable(description="\n            If checked, this interaction will be allowed to combine with other\n            interactions we deem are compatible. If unchecked, it will never be\n            allowed to combine.\n            \n            If we combine multiple interactions, we attempt to solve for all\n            their constraints at once. For example, we tell the Sim to eat and\n            they decide to sit in a chair to do so. While they're routing to\n            that chair, we queue up a go-here. Because the Sim can go to that\n            new location and eat at the same time, we derail their current\n            transition and tell them to do both at once.\n            \n            By default this is set to True, but certain interactions might have\n            deceptive or abnormal constraints that could cause them to be\n            combined in unexpected ways.\n            \n            Please consult a GPE if you think you need to tune this to False.\n            ", tunable_type=bool, default=True, tuning_group=GroupNames.AVAILABILITY), 'mood_list': TunableList(description='\n        A list of possible moods this interaction may associate with.\n        ', tunable=TunableReference(description='\n            A mood associated with this interaction.\n            ', manager=services.get_instance_manager(sims4.resources.Types.MOOD)), tuning_group=GroupNames.STATE), 'ignore_animation_context_liability': Tunable(description='\n            This interaction will discard any AnimationContextLiabilities from\n            its source (if a continuation). Use this for interactions that are\n            continuations but share no ASMs or props with their continuation\n            source.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.ANIMATION), '_report_running_time': Tunable(description='    \n            If checked, this interaction will send off telemetry data whenever\n            it ends to report its running time in Sim minutes.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.TELEMETRY), 'counts_as_inside': Tunable(description='\n        If True, Sims running this interaction will be considered inside. For\n        instance, using the Observatory, while technically outside, should be\n        considered as being inside. This is used for the DayNightTracking system\n        on traits, like for Vampires.\n        ', tunable_type=bool, default=False, tuning_group=GroupNames.SPECIAL_CASES), 'counts_as_in_shade': Tunable(description='\n        If True, Sims running this interaction will be considered in the shade.\n        For instance, sims running sim_CreateCarryUmbrella will be considered\n        in the shade which will keep vampires from being considered in the sun\n        and keep them from burning up.\n        ', tunable_type=bool, default=False, tuning_group=GroupNames.SPECIAL_CASES), '_situation_participant_provider': OptionalTunable(description='\n        If enabled, this interaction and its continuations have access \n        to additional participant types as specified in the provided \n        participant type map.\n        ', tunable=SituationSimParticipantProviderLiability.TunableFactory(), tuning_group=GroupNames.SPECIAL_CASES), 'goal_height_limit': OptionalTunable(description='\n        If enabled geometric constraints will use this value to ignore goals\n        that are generated at a height difference bigger than this limit\n        compared to the height of the interaction target.\n        ', tunable=TunableRange(description='\n            Value in meters that will invalidate any goal inside the \n            constraint.\n            ', tunable_type=float, default=1, minimum=0), tuning_group=GroupNames.ROUTING), '_add_actor_sim_as_listener': Tunable(description='\n        If set, this adds the actor Sim as a listener, so it is possible\n        to run reactionlets on the interaction without the need to\n        be in a social group interaction with other Sims.\n        \n        Example: Sim examines a scarecrow object.  The scarecrow plays\n        an animation which the Sim reacts to via a reactionlet.\n        ', tunable_type=bool, default=False, tuning_group=GroupNames.SPECIAL_CASES)}
    _commodity_flags = EMPTY_SET
    _supported_postures = None
    _autonomy_ads = None
    _simoleon_delta_callbacks = None
    _sim_can_violate_privacy_callbacks = None
    _auto_constraints = None
    _auto_constraint_is_canonical = False
    _auto_constraints_history = None
    _additional_conditional_actions = None
    _additional_tests = None
    _static_commodities_set = None
    _actor_role_asm_info_map = None
    _provided_posture_type = None
    _progress_bar_goal = None
    Multiplier = namedtuple('Multiplier', ['curve', 'use_effective_skill'])
    _success_chance_multipliers = {}
    _monetary_payout_multipliers = {}
    _expressed = True
    _animation_data_actors = defaultdict(lambda : InteractionAsmType.Unknown)
    disable_transitions = False
    disable_distance_estimation_and_posture_checks = False
    _additional_static_commodities = None
    _additional_basic_extras = None
    _additional_basic_liabilities = None
    _animation_constraint_dirty = False
    _has_multi_reserve = False

    @constproperty
    def is_put_in_inventory():
        return False

    @classproperty
    def is_putdown(cls):
        return False

    @classproperty
    def is_rally_interaction(cls):
        return False

    @classproperty
    def is_autonomous_picker_interaction(cls):
        return False

    @classmethod
    def is_allowed_to_forward(cls, obj):
        if cls._forwarding is None:
            return False
        return cls._forwarding.is_allowed_to_forward(cls, obj)

    @classmethod
    def _tuning_loading_callback(cls):
        cls._commodity_flags = EMPTY_SET
        cls._supported_postures = None
        cls._autonomy_ads = None
        if cls._simoleon_delta_callbacks:
            del cls._simoleon_delta_callbacks[DEFAULT]
        if cls._sim_can_violate_privacy_callbacks:
            del cls._sim_can_violate_privacy_callbacks[DEFAULT]
        cls._auto_constraints = None
        cls._auto_constraint_is_canonical = False
        cls._auto_constraints_history = None
        cls._additional_conditional_actions = None
        cls._static_commodities_set = None

    @classmethod
    def register_tuned_animation(cls, interaction_asm_type, asm_key, actor_name, target_name, carry_target_name, create_target_name, overrides, participant_type_actor, participant_type_target):
        if cls._actor_role_asm_info_map is None:
            cls._actor_role_asm_info_map = defaultdict(list)
        if asm_key in sims4.resources.localwork_no_groupid:
            cls._animation_constraint_dirty = True
        data = cls._animation_data_actors[participant_type_actor]
        data |= interaction_asm_type
        cls._animation_data_actors[participant_type_actor] = data
        if participant_type_target & ParticipantType.AllSims:
            data_target = cls._animation_data_actors[participant_type_target]
            data_target |= interaction_asm_type
            cls._animation_data_actors[participant_type_target] = data_target
        if participant_type_target is not None and target_name == 'y':
            data = cls._animation_data_actors[ParticipantType.TargetSim]
            data |= interaction_asm_type
            cls._animation_data_actors[ParticipantType.TargetSim] = data
        list_key = (asm_key, overrides, target_name, carry_target_name, create_target_name)
        if interaction_asm_type == InteractionAsmType.Interaction or interaction_asm_type == InteractionAsmType.Outcome or interaction_asm_type == InteractionAsmType.Response:
            actor_list = cls._actor_role_asm_info_map[ParticipantType.Actor]
            actor_list.append((list_key, 'x'))
            target_list = cls._actor_role_asm_info_map[ParticipantType.TargetSim]
            target_list.append((list_key, 'y'))
        elif interaction_asm_type == InteractionAsmType.Reactionlet:
            target_list = cls._actor_role_asm_info_map[ParticipantType.TargetSim]
            target_list.append((list_key, 'x'))
            listener_list = cls._actor_role_asm_info_map[ParticipantType.Listeners]
            listener_list.append((list_key, 'x'))

    @classmethod
    def add_auto_constraint(cls, participant_type, tuned_constraint, is_canonical=False):
        if cls._multi_surface:
            tuned_constraint = tuned_constraint.get_multi_surface_version()
        if cls._auto_constraint_is_canonical and not is_canonical:
            return
        if is_canonical:
            cls._auto_constraint_is_canonical = True
        for ptype in ParticipantType:
            if ptype == participant_type:
                participant_type = ptype
        if cls._auto_constraints is None:
            cls._auto_constraints = {}
        if participant_type in cls._auto_constraints and not is_canonical:
            intersection = cls._auto_constraints[participant_type].intersect(tuned_constraint)
        else:
            intersection = tuned_constraint
        if not intersection.valid:
            logger.error('{}: Interaction is incompatible with itself: {} and {} have no intersection.', cls.__name__, cls._auto_constraints, tuned_constraint)
        cls._auto_constraints[participant_type] = intersection

    @classmethod
    def _add_autonomy_ad(cls, operation, overwrite=False):
        if operation.stat is None:
            logger.error('stat is None in statistic operation {} for {}.', operation, cls, owner='rez')
            return
        if cls._autonomy_ads is None:
            cls._autonomy_ads = {}
        ad_list = cls._autonomy_ads.get(operation.stat)
        if ad_list is None or overwrite:
            ad_list = AutonomyAdList(operation.stat)
            cls._autonomy_ads[operation.stat] = ad_list
        ad_list.add_op(operation)

    @classmethod
    def _remove_autonomy_ad(cls, operation):
        ad_list = cls._autonomy_ads.get(operation.stat)
        if ad_list is None:
            return False
        return ad_list.remove_op(operation)

    def instance_statistic_operations_gen(self):
        for op in self.aditional_instance_ops:
            yield op
        stat_op_list = self._statistic_operations_gen()
        for op in stat_op_list:
            yield op

    @classmethod
    def _statistic_operations_gen(cls):
        if cls.basic_content is None:
            return
        for op in cls.basic_content.periodic_stat_change.operations:
            yield op
        for operation_list in cls.basic_content.periodic_stat_change.operation_actions.actions:
            for (op, _) in operation_list.get_loot_ops_gen():
                yield op
        if cls.basic_content.periodic_stat_change is not None and cls.basic_content.progressive_stat_change is not None:
            for op in cls.basic_content.progressive_stat_change.additional_operations:
                yield op

    @classmethod
    def get_affordance_key_for_autonomy(cls):
        if cls._affordance_key_override_for_autonomy is not None:
            return cls._affordance_key_override_for_autonomy
        else:
            return cls.__qualname__

    @classmethod
    def register_simoleon_delta_callback(cls, callback, object_tuning_id=DEFAULT):
        if not cls._simoleon_delta_callbacks:
            cls._simoleon_delta_callbacks = defaultdict(list)
        cls._simoleon_delta_callbacks[object_tuning_id].append(callback)

    @classmethod
    def register_sim_can_violate_privacy_callback(cls, callback, object_tuning_id=DEFAULT):
        if not cls._sim_can_violate_privacy_callbacks:
            cls._sim_can_violate_privacy_callbacks = defaultdict(list)
        cls._sim_can_violate_privacy_callbacks[object_tuning_id].append(callback)

    @classmethod
    def clear_registered_callbacks_for_object_tuning_id(cls, object_tuning_id):
        if object_tuning_id in cls._sim_can_violate_privacy_callbacks:
            del cls._sim_can_violate_privacy_callbacks[object_tuning_id]
        if object_tuning_id in cls._simoleon_delta_callbacks:
            del cls._simoleon_delta_callbacks[object_tuning_id]

    @classmethod
    def add_exit_condition(cls, condition_factory_list):
        action = ExitCondition(conditions=condition_factory_list, interaction_action=ConditionalInteractionAction.EXIT_NATURALLY)
        if cls._additional_conditional_actions:
            cls._additional_conditional_actions.append(action)
        else:
            cls._additional_conditional_actions = [action]

    @classmethod
    def add_additional_test(cls, test):
        if cls._additional_tests:
            cls._additional_tests.append(test)
        else:
            cls._additional_tests = [test]

    @classmethod
    def _tuning_loaded_callback(cls):
        for op in cls._statistic_operations_gen():
            if op.advertise and op.subject == ParticipantType.Actor:
                cls._add_autonomy_ad(op)
        for op in cls._false_advertisements_gen():
            cls._add_autonomy_ad(op, overwrite=True)
        cls._update_commodity_flags()
        if cls._supported_postures is None:
            cls._supported_postures = cls._define_supported_postures()
        if not paths.SUPPORT_RELOADING_RESOURCES:
            cls._actor_role_asm_info_map = None
        for liability in cls.basic_liabilities:
            liability.factory.on_affordance_loaded_callback(cls, liability)
        for basic_extra in cls.basic_extras:
            if hasattr(basic_extra.factory, AFFORDANCE_LOADED_CALLBACK_STR):
                basic_extra.factory.on_affordance_loaded_callback(cls, basic_extra)
        if cls.outcome is not None:
            for basic_extra in cls.outcome.get_basic_extras_gen():
                if hasattr(basic_extra.factory, AFFORDANCE_LOADED_CALLBACK_STR):
                    basic_extra.factory.on_affordance_loaded_callback(cls, basic_extra)
        constraints = collections.defaultdict(list)
        for entry in cls._constraints:
            constraints[entry.constrained_participant].append(entry.constraints)
        cls._constraints = frozendict({k: tuple(v) for (k, v) in constraints.items()})
        cls._animation_constraint_dirty = cls.resource_key in sims4.resources.localwork_no_groupid

    @classmethod
    def _verify_tuning_callback(cls):
        if cls.immediate and cls.staging:
            logger.error('{} is tuned to be staging but is marked immediate, this is not allowed.  Suggestion: set basic_content to one-shot or uncheck immediate.', cls.__name__)
        if cls.outcome is not None:
            outcome_actions = cls.outcome
            outcome_actions.interaction_cls_name = cls.__name__
            outcome_actions.validate_basic_extra_tuning(cls.__name__)
        for basic_extra in cls.basic_extras:
            if isinstance(basic_extra.factory, XevtTriggeredElement):
                basic_extra.factory.validate_tuning_interaction(cls, basic_extra)
        if cls.visible:
            if cls.display_name is not None and not cls.display_name:
                logger.error('Interaction {} is visible but has no display name', cls.__name__)
            icon_participant_type = getattr(cls._icon, 'participant_type', None)
            if icon_participant_type is not None and cls.target_type == TargetType.ACTOR and icon_participant_type == ParticipantType.Object:
                logger.error("Interaction {} only targets the actor but uses participant Object's icon. Use an icon or participant Actor.", cls.__name__)
        if cls.basic_content:
            cls.basic_content.validate_tuning(cls)
        if cls.autonomy_preference is not None and cls.autonomy_preference.preference.tag is None:
            logger.error('Interaction {} has autonomy preference enabled, but no autonomy preference tag set.  Please come talk to Joshua Jacobson if you have any questions.', cls.__name__, owner='BadTuning')
        progress_bar_tuning = cls.progress_bar_enabled.force_listen_statistic
        if progress_bar_tuning is not None and progress_bar_tuning.statistic is None:
            logger.error('Progress bar forced commodity is none for interaction {}.', cls, owner='camilogarcia')

    @classmethod
    def _update_commodity_flags(cls):
        commodity_flags = set()
        if cls._autonomy_ads:
            for stat in cls._autonomy_ads:
                commodity_flags.add(stat)
        static_commodities = cls.static_commodities
        if static_commodities:
            commodity_flags.update(static_commodities)
        if commodity_flags:
            cls._commodity_flags = tuple(commodity_flags)
        object_manager = services.object_manager()
        if object_manager is not None:
            services.object_manager().clear_commodity_flags_for_objs_with_affordance((cls,))

    @classmethod
    def contains_stat(cls, stat):
        if stat is None:
            logger.warn('Pass in None stat to ask whether {} contains it.', cls.__name__)
            return False
        for op in cls._statistic_operations_gen():
            if stat is op.stat:
                return True
        return False

    def is_adjustment_interaction(self):
        return False

    @classmethod
    def add_skill_multiplier(cls, multiplier_dict, skill_type, curve, use_effective_skill):
        if cls not in multiplier_dict:
            multiplier_dict[cls] = {}
        multiplier_dict[cls][skill_type] = cls.Multiplier(curve, use_effective_skill)

    @classmethod
    def get_skill_multiplier(cls, multiplier_dict, target):
        multiplier = 1
        if cls in multiplier_dict:
            for (skill_type, modifier) in multiplier_dict[cls].items():
                skill_or_skill_type = target.get_stat_instance(skill_type) or skill_type
                if modifier.use_effective_skill:
                    value = target.Buffs.get_effective_skill_level(skill_or_skill_type)
                else:
                    value = skill_or_skill_type.get_user_value()
                multiplier *= modifier.curve.get(value)
        return multiplier

    def should_fade_sim_out(self):
        return self.fade_sim_out

    @classproperty
    def success_chance_multipliers(cls):
        return cls._success_chance_multipliers

    @classproperty
    def monetary_payout_multipliers(cls):
        return cls._monetary_payout_multipliers

    def _get_conditional_actions_for_content(self, basic_content):
        conditional_actions = []
        if basic_content is not None:
            if basic_content.conditional_actions:
                actions = snippets.flatten_snippet_list(basic_content.conditional_actions)
                conditional_actions.extend(actions)
            if self._additional_conditional_actions:
                actions = snippets.flatten_snippet_list(self._additional_conditional_actions)
                conditional_actions.extend(actions)
        return conditional_actions

    def get_conditional_actions(self):
        actions = self._get_conditional_actions_for_content(self.basic_content)
        if self.target is not None:
            target_basic_content = self.target.get_affordance_basic_content(self)
            if target_basic_content is not None:
                target_actions = self._get_conditional_actions_for_content(target_basic_content)
                actions.extend(target_actions)
        return actions

    def _get_start_as_guaranteed_for_content(self, basic_content):
        if self.sim is not None and self.sim.queue.always_start_inertial:
            return False
        if basic_content is not None:
            if self.is_user_directed:
                return not self.basic_content.start_user_directed_inertial
            else:
                return not self.basic_content.start_autonomous_inertial
        return False

    def get_start_as_guaranteed(self):
        if self._get_start_as_guaranteed_for_content(self.basic_content):
            return True
        elif self.target is not None:
            target_basic_content = self.target.get_affordance_basic_content(self)
            if self._get_start_as_guaranteed_for_content(target_basic_content):
                return True
        return False

    def __str__(self):
        return 'Interaction {} on {}; id:{}, sim:{}'.format(self.affordance, self.target, self.id, self.sim)

    def __repr__(self):
        return '<Interaction {} id:{} sim:{}>'.format(self.affordance.__name__, self.id, self.sim)

    @classproperty
    def autonomy_preference(cls):
        pass

    @classproperty
    def interaction(cls):
        return cls

    @classproperty
    def requires_target_support(cls):
        return True

    @classmethod
    def get_interaction_type(cls):
        return cls

    def get_linked_interaction_type(self):
        pass

    @classmethod
    def generate_continuation_affordance(cls, affordance):
        return affordance

    def get_target_si(self):
        return (None, True)

    @staticmethod
    def _tunable_tests_enabled():
        return True

    @flexmethod
    def get_display_tooltip(cls, inst, override=None, context=DEFAULT, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        context = inst.context if context is DEFAULT else context
        sim = inst.sim if inst is not None else context.sim
        tooltip = inst_or_cls.display_tooltip
        if override.new_display_tooltip is not None:
            tooltip = override.new_display_tooltip
        if override is not None and tooltip is not None:
            tooltip = inst_or_cls.create_localized_string(tooltip, context=context, **kwargs)
        if inst_or_cls.item_cost is not None:
            tooltip = inst_or_cls.item_cost.get_interaction_tooltip(tooltip=tooltip, sim=sim)
        return tooltip

    @flexmethod
    def skip_test_on_execute(cls, inst):
        if inst is not None:
            return inst.aop.skip_test_on_execute
        return False

    @classmethod
    def _test(cls, target, context, **interaction_parameters):
        return event_testing.results.TestResult.TRUE

    @flexmethod
    def test(cls, inst, target=DEFAULT, context=DEFAULT, super_interaction=None, skip_safe_tests=False, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        target = target if target is not DEFAULT else inst.target
        context = context if context is not DEFAULT else inst.context
        if inst_or_cls.is_super:
            for obj in inst_or_cls.get_participants(ParticipantType.All, sim=context.sim, target=target, **interaction_parameters):
                if obj.build_buy_lockout:
                    return event_testing.results.TestResult(False, 'Target object has been locked out and cannot be interacted with.')
        if inst is not None:
            if inst.interaction_parameters and interaction_parameters:
                interaction_parameters = frozendict(inst.interaction_parameters, interaction_parameters)
            else:
                interaction_parameters = inst.interaction_parameters or interaction_parameters
            if super_interaction is None:
                super_interaction = inst.super_interaction
        result = event_testing.results.TestResult.TRUE
        try:
            if cls.is_super and (cls.visible and target is None) and cls._icon is None:
                return event_testing.results.TestResult(False, 'Visible interaction has no target, which is invalid for displaying icons.')
            if context.sim is None and not cls.simless:
                return event_testing.results.TestResult(False, 'No Sim specified in context.')
            if target is not None:
                if target.is_in_inventory():
                    if target.is_in_sim_inventory():
                        if not cls.allow_from_sim_inventory:
                            return event_testing.results.TestResult(False, 'Interaction is not valid from sim inventory.')
                    elif not cls.allow_from_object_inventory:
                        return event_testing.results.TestResult(False, 'Interaction is not valid from object inventory.')
                else:
                    is_starting = interaction_parameters.get('interaction_starting', False)
                    if is_starting or not cls.allow_from_world:
                        return event_testing.results.TestResult(False, 'Interaction is not valid from the world.')
                if cls.simless or not (target.parent is not None and (target.parent.is_sim and (target.parent is not context.sim and target is not context.sim)) and (target.is_set_as_head or target.is_sim)):
                    return event_testing.results.TestResult(False, 'Target is being held by another Sim.')
            if target.is_sim:
                if not context.sim.sim_info.incest_prevention_test(target.sim_info):
                    return event_testing.results.TestResult(False, 'Not available because it violates the incest rules.')
            else:
                logger.error('Trying to test for incest with an object, not a Sim. Interaction = {}, Actor = {}, Target = {}', inst_or_cls, context.sim, target, owner='rfleig')
            if inst_or_cls is not None and (inst_or_cls.test_incest and target is not None) and inst_or_cls is not None and not inst_or_cls.debug:
                fire_service = services.get_fire_service()
                if fire_service is not None:
                    fire_interaction_test_result = fire_service.fire_interaction_test(inst_or_cls.affordance, context)
                    if not fire_interaction_test_result:
                        return fire_interaction_test_result
            instance_result = inst_or_cls._test(target, context, skip_safe_tests=skip_safe_tests, **interaction_parameters)
            if instance_result or not instance_result.tooltip:
                return instance_result
            if inst_or_cls._tunable_tests_enabled():
                search_for_tooltip = context.source == context.SOURCE_PIE_MENU
                resolver = inst_or_cls.get_resolver(target=target, context=context, super_interaction=super_interaction, search_for_tooltip=search_for_tooltip, **interaction_parameters)
                global_result = event_testing.results.TestResult.TRUE
                if context.sim.is_dying:
                    global_result = event_testing.results.TestResult(False, 'Sim [{}] is dying.', context.sim)
                if context.shift_held or inst_or_cls.is_super and (context.is_cancel_aop or context.sim is not None and global_result):
                    global_result = cls.test_globals.run_tests(resolver, skip_safe_tests, search_for_tooltip=search_for_tooltip)
                local_result = event_testing.results.TestResult.TRUE
                autonomous_result = event_testing.results.TestResult.TRUE
                target_result = event_testing.results.TestResult.TRUE
                if global_result.tooltip is not None:
                    local_result = cls.tests.run_tests(resolver, skip_safe_tests=skip_safe_tests, search_for_tooltip=search_for_tooltip)
                    if inst_or_cls._additional_tests:
                        additional_tests = TestList(inst_or_cls._additional_tests)
                        local_result = additional_tests.run_tests(resolver, skip_safe_tests=skip_safe_tests, search_for_tooltip=search_for_tooltip)
                    if target is not None:
                        tests = target.get_affordance_tests(inst_or_cls)
                        if tests is not None:
                            target_result = tests.run_tests(resolver, skip_safe_tests=skip_safe_tests, search_for_tooltip=search_for_tooltip)
                    if inst_or_cls.test_autonomous:
                        autonomous_result = cls.test_autonomous.run_tests(resolver, skip_safe_tests=skip_safe_tests, search_for_tooltip=False)
                if not ((global_result or search_for_tooltip) and target_result):
                    result = target_result
                elif not local_result:
                    result = local_result
                elif not global_result:
                    result = global_result
                else:
                    result = autonomous_result
            if not result:
                return result
            result = target_result & local_result & global_result & autonomous_result
            result &= instance_result
            if target and target.is_on_active_lot():
                household_id = services.owning_household_id_of_active_lot()
                if household_id is not None:
                    result &= services.utilities_manager(household_id).test_utility_info(cls.utility_info)
            if not (context.sim is None or context.sim.is_npc):
                for funds_source in FundsSource:
                    if funds_source == FundsSource.STATISTIC:
                        pass
                    else:
                        cost_for_source = inst_or_cls.get_simoleon_cost_for_source(funds_source, target=target, context=context, **interaction_parameters)
                        if cost_for_source > 0:
                            funds = get_funds_for_source(funds_source, sim=context.sim)
                            if not funds is None:
                                if funds.money < cost_for_source:
                                    unavailable_funds_tooltip = FundsTuning.UNAFFORDABLE_TOOLTIPS.get(funds_source)
                                    result &= event_testing.results.TestResult(False, "Sim [{}] either has no household funds manager, or doesn't have enough funds.:", context.sim, tooltip=unavailable_funds_tooltip)
                            unavailable_funds_tooltip = FundsTuning.UNAFFORDABLE_TOOLTIPS.get(funds_source)
                            result &= event_testing.results.TestResult(False, "Sim [{}] either has no household funds manager, or doesn't have enough funds.:", context.sim, tooltip=unavailable_funds_tooltip)
            if result and result and result:
                result &= inst_or_cls.item_cost.get_test_result(context.sim, inst_or_cls)
            if result and not cls.allow_while_save_locked:
                fail_reason = services.get_persistence_service().get_save_lock_tooltip()
                if fail_reason is not None:
                    error_tooltip = lambda *_, **__: fail_reason
                    return event_testing.results.TestResult(False, 'Interaction is not allowed to run while save is locked.', tooltip=error_tooltip)
            if not result:
                return result
        except Exception as e:
            logger.exception('Exception during call to test method on {0}', cls)
            return event_testing.results.TestResult(False, 'Exception: {}', e)
        if not isinstance(result, event_testing.results.TestResult):
            logger.warn("Interaction test didn't return a TestResult: {}: {}", result, cls.__name__, result)
            return event_testing.results.TestResult(result)
        return result

    @flexmethod
    def get_participant(cls, inst, participant_type=ParticipantType.Actor, **kwargs):
        inst_or_cl = inst if inst is not None else cls
        participants = inst_or_cl.get_participants(participant_type=participant_type, **kwargs)
        if not participants:
            return
        if len(participants) > 1:
            logger.warn('{} is ignoring multiple {} since a single object was expected.', inst_or_cl, participant_type)
            return
        return next(iter(participants))

    @flexmethod
    def get_participants(cls, inst, participant_type:ParticipantType, sim=DEFAULT, target=DEFAULT, carry_target=DEFAULT, listener_filtering_enabled=False, target_type=None, **interaction_parameters) -> set:
        global interaction_get_particpants_call_count
        interaction_get_particpants_call_count += 1
        if interaction_get_particpants_call_count % SIM_YIELD_INTERACTION_GET_PARTICIPANTS_MOD == 0:
            yield_to_irq()
        try:
            participant_type = int(participant_type)
        except:
            participant_type = ParticipantType.Invalid
        if inst is not None:
            if inst.interaction_parameters and interaction_parameters:
                interaction_parameters = frozendict(inst.interaction_parameters, interaction_parameters)
            else:
                interaction_parameters = inst.interaction_parameters or interaction_parameters
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls.simless:
            sim = None
        else:
            sim = inst.sim if sim is DEFAULT else sim
        target = inst.target if target is DEFAULT else target
        if participant_type == ParticipantType.Actor:
            if sim is not None:
                return (sim,)
            return ()
        elif participant_type == ParticipantType.Object:
            if target is not None:
                return (target,)
            return ()
        return ()
        if participant_type == ParticipantType.TargetSim:
            if target is not None and target.is_sim:
                return (target,)
            elif inst is not None and inst.target is not None and inst.target.is_sim:
                return (inst.target,)
            return ()
        object_manager = services.object_manager()
        inventory_manager = services.current_zone().inventory_manager
        if inst is not None:
            carry_target = inst.carry_target if carry_target is DEFAULT else carry_target
        is_all = participant_type & ParticipantType.All
        all_sims = participant_type & ParticipantType.AllSims
        if target_type is None:
            target_type = inst_or_cls.target_type
        result = set()
        if is_all:
            all_sims = True
        target_is_sim = target is not DEFAULT and (target is not None and target.is_sim)
        if all_sims or participant_type & ParticipantType.Actor:
            result.add(sim)
        if is_all or participant_type & ParticipantType.Object:
            result.add(target)
        if (is_all or participant_type & ParticipantType.ObjectParent) and target is not None and not target.is_sim:
            result.add(target.parent)
        if participant_type & ParticipantType.ObjectChildren and target is not None and not isinstance(target, PostureSpecVariable):
            if target.is_part:
                result.update(target.part_owner.children_recursive_gen())
            else:
                result.update(target.children_recursive_gen())
        if is_all or participant_type & ParticipantType.CarriedObject:
            if carry_target is not None and carry_target is not DEFAULT:
                result.add(carry_target)
            elif 'carry_target' in interaction_parameters and target is not None:
                result.add(target)
        if (all_sims or participant_type & ParticipantType.TargetSim) and target_is_sim:
            result.add(target)
        if all_sims or participant_type & ParticipantType.JoinTarget:
            join_target_ref = interaction_parameters.get('join_target_ref')
            if join_target_ref is not None:
                result.add(join_target_ref())
        if participant_type & ParticipantType.LinkedPostureSim:
            posture = sim.posture
            if posture.multi_sim:
                result.add(posture.linked_posture.sim)
        if all_sims or participant_type & ParticipantType.Listeners:
            social_group = inst.social_group if inst is not None else None
            if not (target_type & TargetType.TARGET and (target is not None and (target_is_sim and target.ignore_group_socials(excluded_group=social_group))) and listener_filtering_enabled):
                result.add(target)
            if social_group is not None:
                for other_sim in social_group:
                    if other_sim is sim:
                        pass
                    else:
                        for si in social_group.get_sis_registered_for_sim(other_sim):
                            if si.pipeline_progress >= PipelineProgress.RUNNING and not si.is_finishing:
                                break
                        if inst.acquire_listeners_as_resource or listener_filtering_enabled and other_sim.ignore_group_socials(excluded_group=social_group):
                            pass
                        elif inst._required_sims is not None and listener_filtering_enabled and other_sim not in inst._required_sims:
                            pass
                        else:
                            result.add(other_sim)
        if participant_type & ParticipantType.SocialGroup and inst is not None and inst.is_social:
            result.add(inst.social_group)
        if participant_type & ParticipantType.SocialGroupSims and inst is not None and inst.is_social:
            social_group = inst.social_group
            if social_group is not None:
                result.update(social_group)
        if participant_type & ParticipantType.InventoryObjectStack and target is not None:
            result.add(target)
            if sim is not None and target.inventoryitem_component is not None:
                stack_id = target.inventoryitem_component.get_stack_id()
                result.update(sim.inventory_component.get_stack_items(stack_id))
        if participant_type & ParticipantType.ObjectInventoryOwner and target is not None and target.is_in_inventory():
            owner = target.inventoryitem_component.last_inventory_owner
            if owner is not None:
                result.add(owner)
        if sim.posture_state is not None:
            if is_all or participant_type & ParticipantType.ActorSurface:
                result.add(sim.posture_state.surface_target)
            if participant_type & ParticipantType.ActorPostureTarget:
                result.add(sim.posture_state.body.target)
        if sim is not None and participant_type == ParticipantType.TargetSimPostureTarget:
            if target is not None and target.is_sim:
                result.add(target.posture_state.body.target)
            elif inst.target is not None and inst.target.is_sim:
                result.add(inst.target.posture_state.body.target)
        if target is not None and (target.is_sim and target.posture_state is not None) and (is_all or participant_type & ParticipantType.TargetSurface):
            result.add(target.posture_state.surface_target)
        if participant_type & ParticipantType.CreatedObject:
            if inst is not None and inst.created_target is not None:
                result.add(inst.created_target)
            elif inst.interaction_parameters:
                created_target_id = interaction_parameters.get('created_target_id')
                if created_target_id:
                    obj = object_manager.get(created_target_id) or inventory_manager.get(created_target_id)
                    if obj is not None:
                        result.add(obj)
                    else:
                        del interaction_parameters['created_target_id']
        if participant_type & ParticipantType.PickedItemId:
            picked_item_ids = interaction_parameters.get('picked_item_ids')
            if picked_item_ids is not None:
                result.update(picked_item_ids)
        if participant_type & ParticipantType.Unlockable:
            result.add(interaction_parameters.get('unlockable_name'))
        if participant_type & ParticipantType.PickedObject or participant_type & ParticipantType.StoredSimOnPickedObject:
            picked_item_ids = interaction_parameters.get('picked_item_ids')
            if picked_item_ids is not None:
                for picked_item_id in picked_item_ids:
                    obj = object_manager.get(picked_item_id)
                    if obj is None:
                        obj = inventory_manager.get(picked_item_id)
                    if participant_type & ParticipantType.StoredSimOnPickedObject:
                        stored_sim_info = obj.get_stored_sim_info()
                        if stored_sim_info is not None:
                            result.add(stored_sim_info.get_sim_instance() or stored_sim_info)
                    if obj is not None and participant_type & ParticipantType.PickedObject:
                        result.add(obj)
        if participant_type & ParticipantType.PickedSim:
            picked_item_ids = interaction_parameters.get('picked_item_ids')
            if picked_item_ids is not None:
                for picked_item_id in picked_item_ids:
                    sim_info = services.sim_info_manager().get(picked_item_id)
                    if sim_info is not None:
                        result.add(sim_info.get_sim_instance() or sim_info)
        if participant_type & ParticipantType.RoutingMaster:
            master = sim.routing_master
            if sim.get_routing_slave_data():
                master = sim
            if target.is_sim:
                master = target.routing_master
            if master is None and master is None and target is not None and master is not None:
                result.add(master)
        if participant_type & ParticipantType.RoutingSlaves:
            routing_slave_data = sim.get_routing_slave_data()
            if target.is_sim:
                routing_slave_data = target.get_routing_slave_data()
            if routing_slave_data or target is not None and routing_slave_data:
                result.update({data.slave for data in routing_slave_data})
        if participant_type & ParticipantType.StoredSim and target is not None:
            stored_sim_info = target.get_stored_sim_info()
            if stored_sim_info is not None:
                result.add(stored_sim_info.get_sim_instance() or stored_sim_info)
        if participant_type & ParticipantType.StoredSimOrNameData and target is not None:
            stored_sim_info_or_name_data = target.get_stored_sim_info_or_name_data()
            if stored_sim_info_or_name_data is not None:
                result.add(stored_sim_info_or_name_data)
        if participant_type & ParticipantType.StoredSimOnActor and sim is not None:
            stored_sim_info = sim.get_stored_sim_info()
            if stored_sim_info is not None:
                result.add(stored_sim_info.get_sim_instance() or stored_sim_info)
        if participant_type & ParticipantType.OwnerSim and target is not None:
            owner_sim_info_id = target.get_sim_owner_id()
            owner_sim_info = services.sim_info_manager().get(owner_sim_info_id)
            if owner_sim_info is not None:
                result.add(owner_sim_info.get_sim_instance() or owner_sim_info)
        if participant_type & ParticipantType.SignificantOtherActor and sim is not None:
            spouse = sim.get_significant_other_sim_info()
            if spouse is not None:
                result.add(spouse.get_sim_instance() or spouse)
        if participant_type & ParticipantType.SignificantOtherTargetSim and target is not None and target.is_sim:
            spouse = target.get_significant_other_sim_info()
            if spouse is not None:
                result.add(spouse.get_sim_instance() or spouse)
        if participant_type & ParticipantType.ActorFiance and sim is not None:
            fiance = sim.get_fiance_sim_info()
            if fiance is not None:
                result.add(fiance.get_sim_instance() or fiance)
        if participant_type & ParticipantType.TargetFiance and target is not None and target.is_sim:
            fiance = target.get_fiance_sim_info()
            if fiance is not None:
                result.add(fiance.get_sim_instance() or fiance)
        if participant_type & ParticipantType.PregnancyPartnerActor and sim is not None:
            partner = sim.sim_info.pregnancy_tracker.get_partner()
            if partner is not None:
                result.add(partner.get_sim_instance() or partner)
        if participant_type & ParticipantType.PregnancyPartnerTargetSim and target is not None and target.is_sim:
            partner = target.sim_info.pregnancy_tracker.get_partner()
            if partner is not None:
                result.add(partner.get_sim_instance() or partner)
        if participant_type & ParticipantType.Lot:
            result.update(event_testing.resolver.Resolver.get_particpants_shared(ParticipantType.Lot))
        if participant_type & ParticipantType.PickedZoneId:
            picked_zone_ids = interaction_parameters.get('picked_zone_ids')
            if picked_zone_ids is not None:
                result.update(picked_zone_ids)
        if participant_type & ParticipantType.OtherSimsInteractingWithTarget and target is not None:
            user_target = target.part_owner if target.is_part else target
            user_targets = user_target.parts if user_target.parts else (user_target,)
            other_sims = set()
            for user_target in user_targets:
                if hasattr(user_target, 'get_users'):
                    other_sims.update(user_target.get_users(sims_only=True))
            all_sims_for_removal = inst_or_cls.get_participants(ParticipantType.AllSims, sim=sim, target=target, carry_target=carry_target, **interaction_parameters)
            result.update(set(other_sims) - set(all_sims_for_removal))
        if participant_type & ParticipantType.ActiveHousehold:
            active_household_sim_infos = event_testing.resolver.Resolver.get_particpants_shared(ParticipantType.ActiveHousehold)
            if active_household_sim_infos:
                result.update(active_household_sim_infos)
        if participant_type & ParticipantType.LotOwners:
            owners = event_testing.resolver.Resolver.get_particpants_shared(ParticipantType.LotOwners)
            if owners is not None:
                result.update(owners)
        if participant_type & ParticipantType.LotOwnersOrRenters:
            owners = event_testing.resolver.Resolver.get_particpants_shared(ParticipantType.LotOwnersOrRenters)
            if owners is not None:
                result.update(owners)
        if participant_type & ParticipantType.LotOwnerSingleAndInstanced:
            owners = event_testing.resolver.Resolver.get_particpants_shared(ParticipantType.LotOwnerSingleAndInstanced)
            if owners is not None:
                result.update(owners)
        if participant_type & ParticipantType.SocialGroupAnchor and inst is not None:
            group = inst.social_group
            if group is not None:
                result.add(group.anchor)
        if participant_type & ParticipantType.AllOtherInstancedSims:
            for instanced_sim in services.sim_info_manager().instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS):
                if instanced_sim is not sim and not instanced_sim.is_dying:
                    result.add(instanced_sim)
        if participant_type & ParticipantType.CareerEventSim:
            result.update(event_testing.resolver.Resolver.get_particpants_shared(ParticipantType.CareerEventSim))
        if participant_type & ParticipantType.ActorEnsemble and sim is not None:
            ensemble = services.ensemble_service().get_most_important_ensemble_for_sim(sim)
            if ensemble:
                result.update(ensemble)
        if participant_type & ParticipantType.ActorEnsembleSansActor and sim is not None:
            ensemble = services.ensemble_service().get_most_important_ensemble_for_sim(sim)
            if ensemble:
                ensemble_sims = set(ensemble)
                ensemble_sims.discard(sim)
                result.update(ensemble_sims)
        if participant_type & ParticipantType.TargetEnsemble and target_is_sim:
            ensemble = services.ensemble_service().get_most_important_ensemble_for_sim(target)
            if ensemble:
                result.update(ensemble)
        if participant_type & ParticipantType.MissingPet and sim is not None:
            missing_pet = sim.household.missing_pet_tracker.missing_pet_info
            if missing_pet:
                result.add(missing_pet.get_sim_instance() or missing_pet)
        if participant_type & ParticipantType.ActorDiningGroupMembers and sim is not None:
            restaurant_zone_director = get_restaurant_zone_director()
            if restaurant_zone_director:
                dining_group_sims = restaurant_zone_director.get_group_sims_by_sim(sim)
                result.update(dining_group_sims)
        if participant_type & ParticipantType.TargetDiningGroupMembers:
            restaurant_zone_director = get_restaurant_zone_director()
            if restaurant_zone_director is not None and target_is_sim:
                dining_group_sims = restaurant_zone_director.get_group_sims_by_sim(target)
                result.update(dining_group_sims)
        if participant_type & ParticipantType.TableDiningGroupMembers:
            restaurant_zone_director = get_restaurant_zone_director()
            if restaurant_zone_director is not None and target is not None:
                dining_group_sims = restaurant_zone_director.get_group_sims_by_table(target.id)
                result.update(dining_group_sims)
        if participant_type & ParticipantType.LinkedObjects:
            if target.linked_object_component is None:
                logger.error("Requesting ParticipantType.LinkedObjects on target {} that doesn't have a linked Object component", target)
            result.update(target.get_linked_objects_gen())
        if participant_type & ParticipantType.TargetTeleportPortalObjectDestinations:
            if not target.has_component(objects.components.types.PORTAL_COMPONENT):
                logger.error('Trying to get the TeleportPortalObjectDestinations for a target that does not have a portal component. {}', target)
            else:
                portal_data = target.get_portal_data()
                for data in portal_data:
                    result.update(data.traversal_type.get_destination_objects())
        if participant_type & ParticipantType.ActorFeudTarget and sim is not None:
            feud_target = sim.get_feud_target()
            if feud_target is not None:
                result.add(feud_target)
        if participant_type & ParticipantType.TargetFeudTarget and target is not None and target.is_sim:
            feud_target = target.get_feud_target()
            if feud_target is not None:
                result.add(feud_target)
        if sim is not None:
            sim_info_manager = services.sim_info_manager()
            for squad_member_id in sim.squad_members:
                squad_sim_info = sim_info_manager.get(squad_member_id)
                if squad_sim_info is not None:
                    result.add(squad_sim_info)
        if target.is_sim:
            sim_info_manager = services.sim_info_manager()
            for squad_member_id in target.squad_members:
                squad_sim_info = sim_info_manager.get(squad_member_id)
                if squad_sim_info is not None:
                    result.add(squad_sim_info)
        if participant_type & ParticipantType.ActorSquadMembers and participant_type & ParticipantType.TargetSquadMembers and target is not None and participant_type & ParticipantType.StoredObjectsOnActor and sim is not None:
            actor = sim.sim_info
            c = actor.get_component(objects.components.types.STORED_OBJECT_INFO_COMPONENT)
            if c is not None:
                result.update(c.get_stored_objects())
            else:
                logger.error("Requesting ParticipantType.StoredObjectsOnActor on actor {} that doesn't have a Stored Object Info component", actor)
        if participant_type & ParticipantType.StoredObjectsOnTarget and target is not None:
            _target = target.sim_info if target.is_sim else target
            c = _target.get_component(objects.components.types.STORED_OBJECT_INFO_COMPONENT)
            if c is not None:
                result.update(c.get_stored_objects())
            else:
                logger.error("Requesting ParticipantType.StoredObjectsOnTarget on target {} that doesn't have a Stored Object Info component", _target)
        for p_type in ParticipantTypeSituationSims:
            if participant_type & p_type:
                provider = inst_or_cls.get_situation_participant_provider()
                if provider is not None:
                    return provider.get_participants(participant_type, inst_or_cls.get_resolver())
                logger.error("Requesting {} in {} that doesn't have a SituationSimParticipantProviderLiability", participant_type, provider)
        familiar_tracker_array = set()
        if participant_type & ParticipantType.Familiar and sim is not None:
            familiar_tracker = sim.sim_info.familiar_tracker
            if familiar_tracker is not None:
                familiar_tracker_array.add(familiar_tracker)
        if participant_type & ParticipantType.FamiliarOfTarget and target is not None and target_is_sim:
            familiar_tracker = target.sim_info.familiar_tracker
            if familiar_tracker is not None:
                familiar_tracker_array.add(familiar_tracker)
        for familiar_tracker in familiar_tracker_array:
            familiar = familiar_tracker.get_active_familiar()
            if familiar is not None:
                if familiar.is_sim:
                    result.add(familiar.sim_info)
                else:
                    result.add(familiar)
        for (index, p_type) in enumerate(ParticipantTypeSavedActor):
            if participant_type & p_type:
                if inst is None:
                    saved_participants = interaction_parameters.get('saved_participants')
                    if saved_participants:
                        result.add(saved_participants[index])
                else:
                    result.add(inst.get_saved_participant(index))
        result.discard(None)
        return tuple(result)

    PRIORITY_PARTICIPANT_TYPES = (ParticipantType.Actor, ParticipantType.TargetSim, ParticipantType.Listeners)
    AGGREGATE_PARTICIPANT_TYPES = (ParticipantType.All, ParticipantType.AllSims)

    @flexmethod
    def get_participant_type(cls, inst, participant, restrict_to_participant_types=None, exclude_participant_types=(), **kwargs) -> ParticipantType:
        inst_or_cls = inst if inst is not None else cls
        priority_participant_types = inst_or_cls.PRIORITY_PARTICIPANT_TYPES
        exclude_participant_types = inst_or_cls.AGGREGATE_PARTICIPANT_TYPES + exclude_participant_types
        for participant_type in priority_participant_types:
            if restrict_to_participant_types is not None and participant_type not in restrict_to_participant_types:
                pass
            elif participant_type in exclude_participant_types:
                pass
            elif participant in inst_or_cls.get_participants(participant_type, **kwargs):
                return participant_type
        for (_, participant_type) in ParticipantType.items():
            if participant_type in priority_participant_types:
                pass
            elif restrict_to_participant_types is not None and participant_type not in restrict_to_participant_types:
                pass
            elif participant_type in exclude_participant_types:
                pass
            elif participant in inst_or_cls.get_participants(participant_type, **kwargs):
                return participant_type

    def can_sim_violate_privacy(self, sim):
        if self._sim_can_violate_privacy_callbacks:
            for callback in self._sim_can_violate_privacy_callbacks[DEFAULT]:
                if callback(self, sim):
                    return True
            if self.target is not None:
                target_tuning_id = self.target.guid64
                for callback in self._sim_can_violate_privacy_callbacks[target_tuning_id]:
                    if callback(self, sim):
                        return True
        return False

    @flexmethod
    def get_simoleon_deltas_gen(cls, inst, target=DEFAULT, context=DEFAULT, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls._simoleon_delta_callbacks:
            for callback in inst_or_cls._simoleon_delta_callbacks[DEFAULT]:
                yield callback(inst_or_cls, target, context, **interaction_parameters)
            target_inst = target if target is not DEFAULT else inst.target
            if not target_inst.is_sim:
                target_tuning_id = target_inst.guid64
                if target_tuning_id in inst_or_cls._simoleon_delta_callbacks:
                    for callback in inst_or_cls._simoleon_delta_callbacks[target_tuning_id]:
                        yield callback(inst_or_cls, target_inst, context, **interaction_parameters)

    @flexmethod
    def get_simoleon_cost(cls, inst, target=DEFAULT, context=DEFAULT):
        inst_or_cls = inst if inst is not None else cls
        return -sum(amount for (amount, _) in inst_or_cls.get_simoleon_deltas_gen(target, context) if amount < 0)

    @flexmethod
    def get_simoleon_cost_for_source(cls, inst, funds_source, target=DEFAULT, context=DEFAULT, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        return -sum(amount for (amount, _funds_source) in inst_or_cls.get_simoleon_deltas_gen(target, context, **interaction_parameters) if amount < 0 and _funds_source == funds_source)

    @flexmethod
    def get_simoleon_payout(cls, inst, target=DEFAULT, context=DEFAULT):
        inst_or_cls = inst if inst is not None else cls
        return sum(amount for (amount, _) in inst_or_cls.get_simoleon_deltas_gen(target, context) if amount > 0)

    @classmethod
    def get_category_tags(cls):
        return cls.interaction_category_tags

    @flexmethod
    def get_pie_menu_category(cls, inst, from_inventory_to_owner=False, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        if from_inventory_to_owner:
            return inst_or_cls.category_on_forwarded
        return inst_or_cls.category

    @flexmethod
    def get_name_override_and_test_result(cls, inst, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls.display_name_overrides is not None:
            return inst_or_cls.display_name_overrides.get_display_name_and_result(inst_or_cls, **kwargs)
        return (None, event_testing.results.TestResult.NONE)

    @flexmethod
    def get_display_name_wrapper(cls, inst, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls.display_name_wrappers is not None:
            return inst_or_cls.display_name_wrappers.get_first_passing_wrapper(inst_or_cls, **kwargs)

    @flexmethod
    def get_name_override_tunable_and_result(cls, inst, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        (override_tunable, test_result) = inst_or_cls.get_name_override_and_test_result(**kwargs)
        if override_tunable is not None:
            return (override_tunable, test_result)
        return (None, test_result)

    @flexmethod
    def get_name(cls, inst, target=DEFAULT, context=DEFAULT, apply_name_modifiers=True, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        display_name = inst_or_cls._get_name(target=target, context=context, **interaction_parameters)
        if apply_name_modifiers:
            if inst is None and cls.SIMOLEON_DELTA_MODIFIES_AFFORDANCE_NAME or inst.SIMOLEON_DELTA_MODIFIES_INTERACTION_NAME:
                simoleon_cost = inst_or_cls.get_simoleon_cost(target=target, context=context)
                if simoleon_cost > 0 and inst_or_cls.SIMOLEON_COST_NAME_FACTORY is not None:
                    display_name = inst_or_cls.SIMOLEON_COST_NAME_FACTORY(display_name, simoleon_cost)
                elif inst_or_cls.SIMOLEON_GAIN_NAME_FACTORY is not None:
                    simoleon_payout = inst_or_cls.get_simoleon_payout(target=target, context=context)
                    if simoleon_payout > 0:
                        display_name = inst_or_cls.SIMOLEON_GAIN_NAME_FACTORY(display_name, simoleon_payout)
            if cls.ITEM_COST_NAME_FACTORY:
                display_name = cls.item_cost.get_interaction_name(cls, display_name)
            wrapper_item = inst_or_cls.get_display_name_wrapper(target=target, context=context)
            if inst is None and wrapper_item is not None:
                display_name = wrapper_item.wrapper(display_name)
            if inst_or_cls.DEBUG_NAME_FACTORY is not None:
                display_name = inst_or_cls.DEBUG_NAME_FACTORY(display_name)
        return display_name

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        if inst is not None and inst.display_name_in_queue is not None:
            display_name = inst.display_name_in_queue
        else:
            display_name = inst_or_cls.display_name
        (override_tunable, _) = inst_or_cls.get_name_override_and_test_result(target=target, context=context)
        if override_tunable.new_display_name is not None:
            display_name = override_tunable.new_display_name
        display_name = inst_or_cls.create_localized_string(display_name, target=target, context=context, **interaction_parameters)
        if context.sim is not None:
            curfew_service = services.get_curfew_service()
            if curfew_service.sim_breaking_curfew(context.sim, target, inst_or_cls):
                display_name = curfew_service.BREAK_CURFEW_WARNING(display_name)
        return display_name

    @flexmethod
    def create_localized_string(cls, inst, localized_string_factory, *tokens, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        interaction_tokens = inst_or_cls.get_localization_tokens(**kwargs)
        return localized_string_factory(*interaction_tokens + tokens)

    @flexmethod
    def get_localization_tokens(cls, inst, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        tokens = inst_or_cls.display_name_text_tokens.get_tokens(inst_or_cls.get_resolver(**interaction_parameters))
        return tokens

    @classmethod
    def visual_targets_gen(cls, target, context, **kwargs):
        yield target

    @classmethod
    def has_pie_menu_sub_interactions(cls, target, context, **kwargs):
        return False

    @classmethod
    def potential_pie_menu_sub_interactions_gen(cls, target, context, scoring_gsi_handler=None, **kwargs):
        pass

    @classmethod
    def get_score_modifier(cls, sim, target):
        if cls.content_score.test_gender_preference:
            gender_pref_test = GenderPreferenceTest(subject=ParticipantType.Actor, target_sim=ParticipantType.TargetSim, fallback_if_no_perference_is_set=False, override_target_gender_test=None, tooltip=None, ignore_reciprocal=True)
            resolver = DoubleSimResolver(sim.sim_info, target.sim_info)
            result = resolver(gender_pref_test)
            if not result:
                return cls.GENDER_PREF_CONTENT_SCORE_PENALTY
        score_modifier = cls.content_score.mood_preference.get(sim.get_mood(), 0)
        if target is None:
            return score_modifier
        sims = set(itertools.chain.from_iterable(group for group in sim.get_groups_for_sim_gen() if target in group))
        if sims:
            social_context = SocialContextTest.get_overall_short_term_context_bit(*sims)
        else:
            relationship_track = sim.relationship_tracker.get_relationship_prevailing_short_term_context_track(target.id)
            if relationship_track is not None:
                social_context = relationship_track.get_active_bit()
            else:
                social_context = None
        social_context_preference = cls.content_score.social_context_preference.get(social_context, 0)
        relationship_bit_preference = 0
        trait_preference = 0
        buff_preference = 0
        if cls.content_score.relationship_bit_preference:
            relationship_bit_preference = sum(cls.content_score.relationship_bit_preference.get(rel_bit, 0) for rel_bit in sim.relationship_tracker.get_all_bits(target_sim_id=target.id))
        if cls.content_score.trait_preference:
            trait_preference = sum(cls.content_score.trait_preference.get(trait, 0) for trait in sim.trait_tracker.equipped_traits)
        if cls.content_score.buff_preference:
            buff_preference = sum(score for (buff, score) in cls.content_score.buff_preference.items() if sim.has_buff(buff))
        if cls.content_score.buff_target_preference:
            buff_preference += sum(score for (buff, score) in cls.content_score.buff_target_preference.items() if target.has_buff(buff))
        score_modifier = score_modifier + social_context_preference + relationship_bit_preference + trait_preference + buff_preference
        return score_modifier

    @classproperty
    def is_super(cls):
        return False

    @classmethod
    def _false_advertisements_gen(cls):
        for false_add in cls._false_advertisements:
            yield false_add

    @classproperty
    def commodity_flags(cls):
        return frozenset(cls._commodity_flags)

    @classmethod
    def autonomy_ads_gen(cls, target=None, include_hidden_false_ads=False):
        for ad in target.get_affordance_false_ads(cls):
            cls._add_autonomy_ad(ad, overwrite=False)
        for ad in cls._hidden_false_advertisements:
            cls._add_autonomy_ad(ad, overwrite=False)
        if target is not None and include_hidden_false_ads and cls._autonomy_ads:
            for ad_list in cls._autonomy_ads.values():
                yield ad_list
        if include_hidden_false_ads:
            for ad in cls._hidden_false_advertisements:
                cls._remove_autonomy_ad(ad)
        if target is not None:
            for ad in target.get_affordance_false_ads(cls):
                cls._remove_autonomy_ad(ad)

    @classproperty
    def static_commodities(cls):
        static_commodities_frozen_set = frozenset([data.static_commodity for data in cls.static_commodities_data])
        return static_commodities_frozen_set

    @classproperty
    def static_commodities_data(cls):
        if cls._static_commodities_set is None:
            cls._refresh_static_commodity_cache()
        return cls._static_commodities_set

    @classmethod
    def _refresh_static_commodity_cache(cls):
        if cls._static_commodities:
            static_commodities_set = set(cls._static_commodities)
        else:
            static_commodities_set = set()
        if cls._additional_static_commodities:
            static_commodities_set.update(cls._additional_static_commodities)
        cls._static_commodities_set = frozenset(static_commodities_set)
        cls._update_commodity_flags()

    @classmethod
    def trigger_refresh_static_commodity_cache(cls):
        cls._static_commodities_set = None
        cls._refresh_static_commodity_cache()

    @classproperty
    def provided_posture_type(cls):
        pass

    @flexmethod
    def get_associated_skill(cls, inst):
        skill = None
        if inst is not None:
            skill = inst.stat_from_skill_loot_data
        elif cls.outcome is not None:
            skill = cls.outcome.associated_skill
        return skill

    @flexmethod
    def _get_skill_loot_data(cls, inst):
        if inst is not None and inst.target is not None:
            target_skill_loot_data = inst.target.get_affordance_skill_loot_data(inst)
            if target_skill_loot_data is not None:
                return target_skill_loot_data
        return cls.skill_loot_data

    @flexproperty
    def stat_from_skill_loot_data(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        skill_loot_data = inst_or_cls._get_skill_loot_data()
        return skill_loot_data.stat or inst_or_cls.skill_loot_data.stat

    @flexproperty
    def skill_effectiveness_from_skill_loot_data(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        skill_loot_data = inst_or_cls._get_skill_loot_data()
        return skill_loot_data.effectiveness or inst_or_cls.skill_loot_data.effectiveness

    @flexproperty
    def level_range_from_skill_loot_data(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        skill_loot_data = inst_or_cls._get_skill_loot_data()
        return skill_loot_data.level_range or inst_or_cls.skill_loot_data.level_range

    @classproperty
    def approximate_duration(cls):
        return cls.time_overhead

    @classmethod
    def get_supported_postures(cls, participant_type=ParticipantType.Actor):
        try:
            return cls._supported_postures[participant_type]
        except KeyError:
            if participant_type == ParticipantType.Actor:
                return PostureManifest()
            return ALL_POSTURES

    @classmethod
    def _define_supported_postures(cls):
        if not cls._actor_role_asm_info_map:
            return frozendict()
        posture_support_map = {}
        for (actor_role, asm_info) in cls._actor_role_asm_info_map.items():
            supported_postures = PostureManifest()
            for ((asm_key, overrides, target_name, carry_target_name, create_target_name), actor_name) in asm_info:
                posture_manifest_overrides = None
                if overrides is not None:
                    posture_manifest_overrides = overrides.manifests
                asm = animation.asm.create_asm(asm_key, None, posture_manifest_overrides)
                supported_postures_asm = asm.get_supported_postures_for_actor(actor_name)
                supported_postures.update(supported_postures_asm)
            if supported_postures:
                posture_support_map[actor_role] = supported_postures.frozen_copy()
        return frozendict(posture_support_map)

    @classmethod
    def filter_supported_postures(cls, supported_postures_from_asm, filter_posture_name=None, force_carry_state=None):
        if supported_postures_from_asm is ALL_POSTURES:
            return ALL_POSTURES
        if force_carry_state is None:
            force_carry_state = (None, None)
        filter_entry = PostureManifestEntry(None, filter_posture_name, filter_posture_name, MATCH_ANY, force_carry_state[0], force_carry_state[1], None)
        supported_postures = supported_postures_from_asm.intersection_single(filter_entry)
        return supported_postures

    @flexmethod
    def constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        inst_or_cls = cls if inst is None else inst
        if inst_or_cls._require_current_posture:
            yield sim.posture_state.posture_constraint_strict
        for constraint in inst_or_cls._constraint_gen(sim, target, participant_type):
            constraint = constraint.get_multi_surface_version()
            constraint = constraint.generate_forbid_small_intersections_constraint()
            yield constraint

    @classmethod
    def _constraint_gen(cls, sim, target, participant_type=ParticipantType.Actor):
        for constraints in cls._constraints.get(participant_type, ()):
            for constraint in constraints:
                yield constraint.value.create_constraint(sim, target)
        if cls._auto_constraints is not None and participant_type in cls._auto_constraints:
            yield cls._auto_constraints[participant_type]

    @flexmethod
    def get_constraint_target(cls, inst, target):
        constraint_target = target
        if inst is not None:
            constraint_target = inst.get_participant(participant_type=cls._constraints_actor)
        return constraint_target

    @flexmethod
    def constraint_intersection(cls, inst, sim=DEFAULT, target=DEFAULT, participant_type=DEFAULT, *, posture_state=DEFAULT, force_concrete=True, allow_holster=DEFAULT, invalid_expected=False):
        inst_or_cls = inst if inst is not None else cls
        target = inst.target if target is DEFAULT else target
        if participant_type is DEFAULT:
            participant_type = ParticipantType.Actor
        sim = inst_or_cls.get_participant(participant_type, target=target) if sim is DEFAULT and sim is DEFAULT else sim
        if sim is None:
            return ANYWHERE
        if posture_state is DEFAULT:
            posture_state = sim.posture_state
        if inst is not None and posture_state is not None and posture_state.body.source_interaction is inst:
            return posture_state.body_posture_state_constraint
        participant_type = inst_or_cls.get_participant_type(sim, target=target) if participant_type is DEFAULT else participant_type
        if participant_type is None:
            return Nowhere('Interaction({}) cannot find {} as a participant, target: {}', inst_or_cls, sim, target)
        add_slot_constraints_if_possible = not sim.parent_may_move
        sim_constraint_cache_key = (sim.ref, add_slot_constraints_if_possible)
        if inst is None or allow_holster is not DEFAULT:
            intersection = None
        elif False and not caches.use_constraints_cache:
            intersection = None
        else:
            if posture_state is not None:
                cached_constraint = inst._constraint_cache_final.get(posture_state)
                if cached_constraint:
                    return cached_constraint
            intersection = inst._constraint_cache.get(sim_constraint_cache_key)
        if intersection is None:
            intersection = ANYWHERE
            constraints = list(inst_or_cls.constraint_gen(sim, inst_or_cls.get_constraint_target(target), participant_type=participant_type))
            routing_master = sim.routing_master
            if routing_master is not None:
                passed_sim = sim if inst is None else DEFAULT
                actor_participant = inst_or_cls.get_participant(ParticipantType.Actor, target=target, sim=passed_sim)
                if actor_participant is not routing_master:
                    slave_data = routing_master.get_formation_data_for_slave(sim)
                    if slave_data is not None:
                        constraints.append(slave_data.get_routing_slave_constraint())
            for constraint in constraints:
                if inst is not None:
                    if force_concrete:
                        constraint = constraint.create_concrete_version(inst)
                    constraint_resolver = inst.get_constraint_resolver(None, participant_type=participant_type, force_actor=sim)
                    constraint = constraint.apply_posture_state(None, constraint_resolver, affordance=inst_or_cls.affordance)
                    if add_slot_constraints_if_possible:
                        constraint = constraint.add_slot_constraints_if_possible(sim)
                test_intersection = constraint.intersect(intersection)
                intersection = test_intersection
                if not intersection.valid:
                    break
            if allow_holster is DEFAULT:
                inst._constraint_cache[sim_constraint_cache_key] = intersection
        if not intersection.valid:
            return intersection
        final_intersection = inst_or_cls.apply_posture_state_and_interaction_to_constraint(posture_state, intersection, sim=sim, target=target, participant_type=participant_type, allow_holster=allow_holster, invalid_expected=invalid_expected)
        if inst_or_cls._multi_surface:
            final_intersection = final_intersection.get_multi_surface_version()
        if allow_holster is DEFAULT:
            inst._constraint_cache_final[posture_state] = final_intersection
        return final_intersection

    def is_guaranteed(self):
        return not self.has_active_cancel_replacement

    @classmethod
    def consumes_object(cls):
        return cls.outcome.consumes_object

    @classproperty
    def interruptible(cls):
        return False

    def should_cancel_on_si_cancel(self, interaction):
        return False

    def __init__(self, aop, context, aop_id=None, super_affordance=None, must_run=False, posture_target=None, liabilities=None, route_fail_on_transition_fail=True, name_override=None, load_data=None, depended_on_si=None, depended_on_until_running=False, anim_overrides=None, set_work_timestamp=True, saved_participants=None, **kwargs):
        self._kwargs = kwargs
        self._aop = aop
        self._liability_target_ref = None
        self.context = copy.copy(context)
        self.anim_overrides = anim_overrides
        if name_override is not None:
            self.name_override = name_override
        self._pipeline_progress = PipelineProgress.NONE
        self._constraint_cache = {}
        self._constraint_cache_final = WeakKeyDictionary()
        self._target = None
        self.set_target(aop.target)
        self.carry_track = None
        self.slot_manifest = None
        self.motive_handles = []
        self.aditional_instance_ops = []
        self._super_interaction = None
        self._run_interaction_element = None
        self._asm_states = {}
        self.locked_params = frozendict()
        if context is not None:
            self._priority = context.priority
            self._run_priority = context.run_priority if context.run_priority else context.priority
        else:
            self._priority = context.priority if context else interactions.priority.Priority.Low
            self._run_priority = context.priority
        self._active = False
        self._satisfied = not self.get_start_as_guaranteed()
        self._delay_behavior = None
        conditional_actions = self.get_conditional_actions()
        if conditional_actions:
            self._conditional_action_manager = interactions.utils.exit_condition_manager.ConditionalActionManager()
        else:
            self._conditional_action_manager = None
        self._performing = False
        self._start_time = None
        self._loaded_start_time = None
        if load_data.start_time is not None:
            self._loaded_start_time = load_data.start_time
        self._finisher = InteractionFinisher()
        self.on_pipeline_change_callbacks = CallableList()
        self._must_run_instance = must_run
        self._global_outcome_result = None
        self.outcome_display_message = None
        self._outcome_result_map = {}
        self._posture_target_ref = None
        self._interaction_event_update_alarm = None
        self._liabilities = OrderedDict()
        if load_data is not None and liabilities is not None:
            for liability in liabilities:
                self.add_liability(*liability)
        if self._situation_participant_provider is not None:
            self.add_liability(SituationSimParticipantProviderLiability.LIABILITY_TOKEN, self._situation_participant_provider(self))
        self.route_fail_on_transition_fail = route_fail_on_transition_fail
        self._required_sims = None
        self._required_sims_threading = None
        self._on_cancelled_callbacks = CallableList()
        if self.context.continuation_id:
            parent = self.sim.find_interaction_by_id(self.context.continuation_id)
            if parent is not None:
                depended_on_si = parent.depended_on_si
        if depended_on_si is None and depended_on_si is not None:
            depended_on_si.attach_interaction(self)
        self.depended_on_si = depended_on_si
        self.depended_on_until_running = depended_on_until_running
        self._progress_bar_commodity_callback = None
        self._progress_bar_displayed = False
        self.set_work_timestamp = set_work_timestamp
        self._object_create_helper = None
        self._saved_participants = [None, None, None, None] if saved_participants is None else saved_participants
        self._animation_events = []
        self.additional_destination_validity_tests = []
        self.privacy_test_cache = None
        self.carry_sim_node = None
        self._additional_instance_basic_extras = None

    def on_asm_state_changed(self, asm, state):
        if state == 'exit':
            state = 'entry'
        self._asm_states[asm] = state

    def prevents_distress(self, stat_type):
        return stat_type in self.commodity_flags

    @property
    def aop(self):
        return self._aop

    @property
    def aop_id(self):
        return self.aop.aop_id

    @property
    def sim(self):
        return self.context.sim

    @property
    def source(self):
        return self.context.source

    @property
    def is_user_directed(self):
        return self.source == InteractionContext.SOURCE_PIE_MENU or self.source == InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT

    @property
    def is_autonomous(self):
        return self.source == InteractionContext.SOURCE_AUTONOMY

    @property
    def object_with_inventory(self):
        return self._kwargs.get('object_with_inventory')

    @classproperty
    def staging(cls):
        if cls.basic_content is not None:
            return cls.basic_content.staging
        return False

    @classproperty
    def looping(cls):
        if cls.basic_content is not None:
            return cls.basic_content.sleeping
        return False

    @classproperty
    def one_shot(cls):
        basic_content = cls.basic_content
        if basic_content is not None:
            if basic_content.staging:
                return False
            elif basic_content.sleeping:
                return False
        return True

    @classproperty
    def is_basic_content_one_shot(cls):
        basic_content = cls.basic_content
        if basic_content is not None and (basic_content.staging or basic_content.sleeping):
            return False
        return True

    @property
    def consecutive_running_time_span(self):
        if self._start_time is None:
            return TimeSpan.ZERO
        return services.time_service().sim_now - self._start_time

    @property
    def target(self):
        return self._target

    @property
    def user_facing_target(self):
        return self.target

    @classproperty
    def immediate(cls):
        return False

    @contextmanager
    def override_var_map(self, sim, var_map):
        original_target = self.target
        original_carry_track = self.carry_track
        original_slot_manifest = self.slot_manifest
        self._apply_vars(*self._get_vars_from_var_map(sim, var_map))
        yield None
        self._apply_vars(original_target, original_carry_track, original_slot_manifest)

    def apply_var_map(self, sim, var_map):
        self._apply_vars(*self._get_vars_from_var_map(sim, var_map))

    def _get_vars_from_var_map(self, sim, var_map):
        target = var_map.get(PostureSpecVariable.INTERACTION_TARGET)
        hand = var_map.get(PostureSpecVariable.HAND)
        if hand is None:
            carry_track = None
        else:
            carry_track = hand_to_track(hand)
        slot_manifest = var_map.get(PostureSpecVariable.SLOT)
        return (target, carry_track, slot_manifest)

    def _apply_vars(self, target, carry_track, slot_manifest):
        self.set_target(target)
        self.carry_track = carry_track
        self.slot_manifest = slot_manifest

    def set_target(self, target):
        if self.target is target:
            return
        if self.sim is None:
            logger.error('{}: Setting the target of an interaction but self.sim is None.', self, owner='miking')
        if self.queued and self.target is not None:
            self.target.remove_interaction_reference(self)
            if self.sim is not None and self.sim.transition_controller is not None:
                self.sim.transition_controller.remove_relevant_object(self.target)
        if self.target_type & TargetType.ACTOR or self.target_type & TargetType.FILTERED_TARGET:
            target = None
        elif target is self.sim and target is not None and not self.immediate:
            logger.error('Setting the target of an {} interaction to the running Sim. This can cause errors if the Sim is reset or deleted.', self)
        if self.queued and target is not None:
            target.add_interaction_reference(self)
            if self.sim is not None and self.sim.transition_controller is not None:
                self.sim.transition_controller.add_relevant_object(target)
        self._target = target
        self.refresh_constraints()

    def get_saved_participant(self, index):
        return self._saved_participants[index]

    def set_saved_participant(self, index, obj):
        self._saved_participants[index] = obj

    def is_saved_participant(self, obj):
        return any(obj == saved_obj for saved_obj in self._saved_participants if saved_obj is not None)

    @property
    def interaction_parameters(self):
        return self._kwargs

    @property
    def continuation_id(self):
        return self.context.continuation_id

    @property
    def visual_continuation_id(self):
        return self.context.continuation_id or self.context.visual_continuation_id

    def is_continuation_by_id(self, source_id):
        return source_id is not None and self.continuation_id == source_id

    @property
    def group_id(self):
        return self.context.group_id or self.id

    def is_related_to(self, interaction):
        return self.group_id == interaction.group_id

    @classproperty
    def affordance(cls):
        return cls

    @classproperty
    def affordances(cls):
        return (cls.get_interaction_type(),)

    @property
    def super_affordance(self):
        return self._aop.super_affordance

    @property
    def si_state(self):
        if self.sim is not None:
            return self.sim.si_state

    @property
    def queue(self):
        if self.sim is not None:
            return self.sim.queue

    @property
    def visible_as_interaction(self):
        return self.visible

    @property
    def transition(self):
        pass

    @property
    def object_create_helper(self):
        return self._object_create_helper

    @object_create_helper.setter
    def object_create_helper(self, create_helper):
        self._object_create_helper = create_helper

    @property
    def carry_target(self):
        return self.context.carry_target

    @property
    def create_target(self):
        pass

    @property
    def created_target(self):
        if self.context.create_target_override is not None:
            return self.context.create_target_override
        if self.object_create_helper is None or self.object_create_helper.is_object_none:
            return
        return self.object_create_helper.object

    @property
    def disable_carry_interaction_mask(self):
        return False

    @flexmethod
    def get_icon_info(cls, inst, target=DEFAULT, context=DEFAULT):
        inst_or_cls = inst if inst is not None else cls
        resolver = inst_or_cls.get_resolver(target=target, context=context)
        icon_info = inst_or_cls._get_icon(resolver)
        if icon_info is not None:
            return icon_info
        else:
            target = inst.target if inst is not None else target
            if target is not DEFAULT and target is not None:
                return IconInfoData(icon_resource=target.icon)
        return EMPTY_ICON_INFO_DATA

    @flexmethod
    def get_pie_menu_icon_info(cls, inst, target=DEFAULT, context=DEFAULT, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls.pie_menu_icon is None:
            return
        resolver = inst_or_cls.get_resolver(target=target, context=context)
        icon_info_data = inst_or_cls.pie_menu_icon(resolver)
        return icon_info_data

    @classmethod
    def _get_icon(cls, interaction):
        return cls._icon(interaction)

    @classproperty
    def never_user_cancelable(cls):
        return cls._cancelable_by_user != CancelablePhase.NEVER or cls._must_run

    @property
    def user_cancelable(self, **kwargs):
        if self.must_run:
            return False
        return self.never_user_cancelable

    @property
    def must_run(self):
        if self._must_run or self._must_run_instance:
            return True
        return False

    @property
    def super_interaction(self):
        return self._super_interaction

    @super_interaction.setter
    def super_interaction(self, si):
        if si is self._super_interaction:
            return
        if self._super_interaction is not None:
            self._super_interaction.detach_interaction(self)
        self._super_interaction = si
        if si is not None:
            si.attach_interaction(self)

    @property
    def queued(self):
        return self.pipeline_progress >= PipelineProgress.QUEUED

    @property
    def prepared(self):
        return self.pipeline_progress >= PipelineProgress.PREPARED

    @property
    def running(self):
        return self._run_interaction_element is not None and self._run_interaction_element._child_handle is not None

    @property
    def performing(self):
        return self._performing

    @property
    def active(self):
        return self._active

    def _set_pipeline_progress(self, value):
        self._pipeline_progress = value

    @property
    def pipeline_progress(self):
        return self._pipeline_progress

    @pipeline_progress.setter
    def pipeline_progress(self, value):
        if value is not self._pipeline_progress:
            self._set_pipeline_progress(value)
            self.on_pipeline_change_callbacks(self)

    @property
    def should_reset_based_on_pipeline_progress(self):
        return self._pipeline_progress >= PipelineProgress.PRE_TRANSITIONING

    def _set_satisfied(self, value):
        self._satisfied = value

    @property
    def satisfied(self):
        return self._satisfied

    @satisfied.setter
    def satisfied(self, value):
        self._set_satisfied(value)

    def get_animation_context_liability(self):
        animation_liability = self.get_liability(ANIMATION_CONTEXT_LIABILITY)
        if animation_liability is None:
            animation_context = animation.AnimationContext()
            animation_liability = AnimationContextLiability(animation_context)
            self.add_liability(ANIMATION_CONTEXT_LIABILITY, animation_liability)
        return animation_liability

    @property
    def animation_context(self):
        animation_liability = self.get_animation_context_liability()
        return animation_liability.animation_context

    @property
    def priority(self):
        return self._priority

    @property
    def run_priority(self):
        return self._run_priority

    @priority.setter
    def priority(self, value):
        if self._priority == value:
            return
        self._priority = value
        if self.queue is not None:
            self.queue.on_element_priority_changed(self)

    @run_priority.setter
    def run_priority(self, value):
        self._run_priority = value
        if self.running:
            logger.error('Setting the run priority of an interaction that is already running, this will not actually cause the interaction to run at a different priority. {}', self)

    @classproperty
    def is_social(cls):
        return False

    @property
    def social_group(self):
        pass

    @property
    def liabilities(self):
        return reversed(tuple(self._liabilities.values()))

    @property
    def start_time(self):
        if self._loaded_start_time is not None:
            return self._loaded_start_time
        return self._start_time

    def disable_displace(self, other):
        return False

    def add_liability(self, key, liability):
        target_continuation = self._liability_target_ref() if self._liability_target_ref is not None else None
        if target_continuation is not None and liability.should_transfer(target_continuation):
            liability_target = target_continuation
        else:
            liability_target = self
        old_liability = liability_target.get_liability(key)
        if old_liability is not None:
            liability = old_liability.merge(self, key, liability)
        liability.on_add(liability_target)
        liability_target._liabilities[key] = liability

    def remove_liability(self, key):
        liability = self.get_liability(key)
        if liability is not None:
            liability.release()
            del self._liabilities[key]

    def get_liability(self, key):
        if key in self._liabilities:
            return self._liabilities[key]

    def _acquire_liabilities(self):
        parent = None
        if self.context.continuation_id:
            parent = self.sim.find_interaction_by_id(self.context.continuation_id)
        elif self.context.source_interaction_id:
            if self.context.source_interaction_sim_id is not None:
                sim = services.object_manager().get(self.context.source_interaction_sim_id)
            else:
                sim = self.sim
            if sim is not None:
                parent = sim.find_interaction_by_id(self.context.source_interaction_id)
        if parent is not None:
            if self.is_super != parent.is_super:
                return
            parent._liability_target_ref = weakref.ref(self)
            parent.release_liabilities(continuation=self)

    def release_liabilities(self, continuation=None, liabilities_to_release=()):
        exception = None
        if continuation is not None:
            source_interaction_id = continuation.context.source_interaction_id
            continuation_id = continuation.context.continuation_id
        for (key, liability) in list(self._liabilities.items()):
            if liabilities_to_release:
                if key in liabilities_to_release:
                    if continuation is not None:
                        if not (key != ANIMATION_CONTEXT_LIABILITY or continuation.ignore_animation_context_liability):
                            if source_interaction_id and isinstance(liability, SharedLiability):
                                continuation_liability = liability.create_new_liability(continuation)
                                continuation.add_liability(key, continuation_liability)
                            elif continuation_id is not None:
                                liability.transfer(continuation)
                                continuation.add_liability(key, liability)
                                del self._liabilities[key]
                    try:
                        liability.release()
                        del self._liabilities[key]
                    except BaseException as ex:
                        logger.exception('Liability {} threw exception {}', liability, ex)
                        if exception is None:
                            exception = ex
            if continuation is not None:
                if not (key != ANIMATION_CONTEXT_LIABILITY or continuation.ignore_animation_context_liability):
                    if source_interaction_id and isinstance(liability, SharedLiability):
                        continuation_liability = liability.create_new_liability(continuation)
                        continuation.add_liability(key, continuation_liability)
                    elif continuation_id is not None:
                        liability.transfer(continuation)
                        continuation.add_liability(key, liability)
                        del self._liabilities[key]
            try:
                liability.release()
                del self._liabilities[key]
            except BaseException as ex:
                logger.exception('Liability {} threw exception {}', liability, ex)
                if exception is None:
                    exception = ex
        if exception is not None:
            raise exception

    @flexmethod
    def get_situation_participant_provider(cls, inst):
        if inst is not None:
            liability = inst.get_liability(SituationSimParticipantProviderLiability.LIABILITY_TOKEN)
            if liability is not None:
                return liability
            elif cls._situation_participant_provider is not None:
                return cls._situation_participant_provider()
        elif cls._situation_participant_provider is not None:
            return cls._situation_participant_provider()

    @property
    def is_affordance_locked(self):
        return self.sim.is_affordance_locked(self.affordance)

    @classmethod
    def add_additional_static_commodity_data(cls, static_commodity_data):
        if cls._additional_static_commodities is None:
            cls._additional_static_commodities = []
        cls._additional_static_commodities.append(static_commodity_data)

    @classmethod
    def remove_additional_static_commodity_data(cls, static_commodity_data):
        cls._additional_static_commodities.remove(static_commodity_data)

    @classproperty
    def can_holster_incompatible_carries(cls):
        return True

    @classproperty
    def allow_holstering_of_owned_carries(cls):
        return False

    @classproperty
    def allow_with_unholsterable_carries(cls):
        if cls.basic_content is not None and cls.basic_content.allow_with_unholsterable_object is not None:
            return cls.basic_content.allow_with_unholsterable_object
        return not cls.is_super

    @property
    def combined_posture_preferences(self):
        return self.posture_preferences

    @property
    def combined_posture_target_preference(self):
        return self.posture_target_preferences

    @flexmethod
    def get_constraint_resolver(cls, inst, posture_state, *args, participant_type=ParticipantType.Actor, force_actor=None, **kwargs):
        if posture_state is not None:
            posture_sim = posture_state.sim
            participant_sims = inst.get_participants(participant_type)
        inst_or_cls = inst if inst is not None and inst is not None else cls

        def resolver(constraint_participant, default=None):
            result = default
            if constraint_participant == AnimationParticipant.ACTOR:
                if force_actor is not None:
                    result = force_actor
                else:
                    result = inst_or_cls.get_participant(participant_type, *args, **kwargs)
            elif constraint_participant == AnimationParticipant.TARGET or constraint_participant == PostureSpecVariable.INTERACTION_TARGET:
                if inst_or_cls.target_type == TargetType.FILTERED_TARGET and posture_state is not None:
                    result = posture_state.body_target
                else:
                    if inst_or_cls.is_social and participant_type == ParticipantType.TargetSim:
                        target_participant_type = ParticipantType.Actor
                    else:
                        target_participant_type = ParticipantType.Object
                    result = inst_or_cls.get_participant(target_participant_type, *args, **kwargs)
            elif constraint_participant == AnimationParticipant.CARRY_TARGET or constraint_participant == PostureSpecVariable.CARRY_TARGET:
                result = inst_or_cls.get_participant(ParticipantType.CarriedObject, *args, **kwargs)
            elif constraint_participant == AnimationParticipant.CREATE_TARGET:
                if inst is not None:
                    result = inst.create_target
            elif constraint_participant == AnimationParticipant.BASE_OBJECT:
                if posture_state is not None:
                    result = posture_state.body.target
                else:
                    result = PostureSpecVariable.BODY_TARGET_FILTERED
            elif constraint_participant == AnimationParticipant.CONTAINER or constraint_participant == PostureSpecVariable.CONTAINER_TARGET:
                if posture_state is not None:
                    result = posture_state.body.target
                else:
                    result = PostureSpecVariable.CONTAINER_TARGET
            elif constraint_participant in (AnimationParticipant.SURFACE, PostureSpecVariable.SURFACE_TARGET):
                if posture_state is not None:
                    result = posture_state.surface_target
                    if result is None:
                        result = MATCH_NONE
                elif default == AnimationParticipant.SURFACE:
                    result = PostureSpecVariable.SURFACE_TARGET
            return result

        return resolver

    @flexmethod
    def apply_posture_state_and_interaction_to_constraint(cls, inst, posture_state, constraint, *args, participant_type=ParticipantType.Actor, sim=DEFAULT, allow_holster=DEFAULT, invalid_expected=False, base_object=None, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        sim = sim if sim is not DEFAULT else posture_state.sim
        if posture_state is not None:
            body_target = posture_state.body_target
            if body_target is not None and body_target.is_part and not body_target.supports_posture_spec(posture_state.get_posture_spec({}), inst_or_cls):
                return Nowhere('Body Target({}) does not support PostureSpec({})', body_target, posture_state.get_posture_spec({}))
        allow_holster = inst_or_cls.can_holster_incompatible_carries and sim.is_allowed_to_holster() if allow_holster is DEFAULT else allow_holster
        if allow_holster:
            constraint = constraint.get_holster_version()
        constraint_resolver = inst_or_cls.get_constraint_resolver(posture_state, *args, participant_type=participant_type, sim=sim, **kwargs)
        result = constraint.apply_posture_state(posture_state, constraint_resolver, invalid_expected=invalid_expected, base_object=base_object)
        return result

    def log_participants_to_gsi(self):
        if gsi_handlers.interaction_archive_handlers.is_archive_enabled(self):
            for participant in self.get_participants(ParticipantType.All):
                ptype = self.get_participant_type(participant)
                gsi_handlers.interaction_archive_handlers.add_participant(self, ptype, participant)

    def get_asm(self, asm_key, actor_name, target_name, carry_target_name, setup_asm_override=DEFAULT, animation_context=DEFAULT, posture=None, use_cache=True, posture_manifest_overrides=None, **kwargs):
        if posture is None:
            posture = self.sim.posture
        if setup_asm_override is DEFAULT:
            setup_asm_override = lambda asm: self.setup_asm_default(asm, actor_name, target_name, carry_target_name, posture=posture, **kwargs)
        if animation_context is DEFAULT:
            animation_context = self.animation_context
        cache_key = (self.group_id, animation_context.request_id)
        animation_liability = self.get_animation_context_liability()
        cached_keys = animation_liability.cached_asm_keys[posture]
        cached_keys.add(cache_key)
        asm = posture.get_registered_asm(animation_context, asm_key, setup_asm_override, use_cache=use_cache, cache_key=cache_key, interaction=self, posture_manifest_overrides=posture_manifest_overrides)
        if asm is None:
            return
        current_state = self._asm_states.get(asm)
        if current_state is not None:
            asm.set_current_state(current_state)
        else:
            self._asm_states[asm] = None
        return asm

    def setup_asm_default(self, asm, actor_name, target_name, carry_target_name, posture=None, create_target_name=None, base_object_name=None):
        if posture is None:
            posture = self.sim.posture
        carry_track = self.carry_track if self.carry_track is not None else DEFAULT
        result = posture.setup_asm_interaction(asm, self.sim, self.target, actor_name, target_name, carry_target=self.carry_target, carry_target_name=carry_target_name, create_target_name=create_target_name, carry_track=carry_track, base_object_name=base_object_name)
        if not result:
            return result
        if self.target is not None:
            surface_height = get_surface_height_parameter_for_object(self.target, sim=self.sim)
            asm.set_parameter('surfaceHeight', surface_height)
        self.super_interaction.set_stat_asm_parameter(asm, actor_name, target_name, self.sim, self.target)
        self.sim.set_mood_asm_parameter(asm, actor_name)
        self.sim.set_trait_asm_parameters(asm, actor_name)
        if target_name is not None and self.target is not None and self.target.is_sim:
            self.target.set_mood_asm_parameter(asm, target_name)
            self.target.set_trait_asm_parameters(asm, target_name)
        if create_target_name is not None and asm.get_actor_definition(create_target_name) is not None and self.created_target is not None:
            result = asm.add_potentially_virtual_actor(actor_name, self.sim, create_target_name, self.created_target, target_participant=AnimationParticipant.CREATE_TARGET)
            if not result:
                return result
            set_carry_track_param_if_needed(asm, self.sim, create_target_name, self.created_target, carry_track)
        if self.locked_params:
            virtual_actor_map = {target_name: self.target} if target_name is not None else None
            asm.update_locked_params(self.locked_params, virtual_actor_map)
        if self.asm_actor_overrides:
            for override in self.asm_actor_overrides:
                override_actor_obj = self.get_participant(override.actor_participant)
                if override_actor_obj is not None:
                    asm.set_actor(override.actor_name, override_actor_obj)
        return True

    def with_listeners(self, sims, sequence):
        listeners = WeakSet(sims)
        if self._add_actor_sim_as_listener and self.sim is not None:
            listeners.add(self.sim)

        def event_handler_reactionlet(event_data):
            asm_name_default = event_data.event_data['reaction_name']
            public_state_name = event_data.event_data['public_state']
            self._trigger_reactionlets(listeners, asm_name_default, public_state_name)

        sequence = with_event_handlers(self.animation_context, event_handler_reactionlet, animation.ClipEventType.Reaction, sequence=sequence, tag='reactionlets')
        for listener in sims:
            if listener is self.sim:
                pass
            else:
                sequence = with_sim_focus(self.sim, listener, self.sim, SimFocus.LAYER_INTERACTION, sequence, score=0.999)
        return sequence

    def _trigger_reactionlets(self, listeners, asm_name_default, public_state_name):
        if self.super_interaction is None:
            return
        for listener in listeners:

            def setup_asm_listener(asm):
                return listener.posture.setup_asm_interaction(asm, listener, None, 'x', None)

            reactionlet = self.outcome.get_reactionlet(self, setup_asm_override=setup_asm_listener, sim=listener)
            if reactionlet is not None:
                asm = reactionlet.get_asm()
                if asm is None:
                    logger.error('Reactionlet {} from Interaction {} does not have an animation element tuned', reactionlet, self, owner='rmccord')
                    return
                arb = animation.arb.Arb()
                reactionlet.append_to_arb(asm, arb)
                distribute_arb_element(arb)
            else:
                asm = listener.posture.get_registered_asm(self.animation_context, asm_name_default, setup_asm_listener, interaction=self, use_cache=False)
                if asm is not None:
                    reaction_arb = animation.arb.Arb()
                    if public_state_name is None:
                        asm.request('exit', reaction_arb)
                    else:
                        asm.request(public_state_name, reaction_arb)
                    distribute_arb_element(reaction_arb)

    def refresh_constraints(self):
        self._constraint_cache.clear()
        self._constraint_cache_final.clear()

    def apply_posture_state(self, posture_state, participant_type=ParticipantType.Actor, sim=DEFAULT):
        if posture_state in self._constraint_cache_final:
            return
        intersection = self.constraint_intersection(sim=sim, participant_type=participant_type, posture_state=posture_state, force_concrete=True)
        if posture_state is not None:
            posture_state.add_constraint(self, intersection)

    def _setup_gen(self, timeline):
        if self.super_interaction is None:
            return False
        if not self.super_interaction.can_run_subinteraction(self):
            return False
        yield from self.si_state.process_gen(timeline)
        self._active = True
        return True

    def setup_gen(self, timeline):
        interaction_parameters = {}
        interaction_parameters['interaction_starting'] = True
        test_result = self.test(skip_safe_tests=self.skip_test_on_execute(), **interaction_parameters)
        if not test_result:
            return (test_result.result, test_result.reason)
        result = yield from self._setup_gen(timeline)
        return (result, None)

    @property
    def should_rally(self):
        return False

    def maybe_bring_group_along(self, **kwargs):
        pass

    def pre_process_interaction(self):
        pass

    def post_process_interaction(self):
        pass

    def _validate_posture_state(self):
        return True

    def perform_gen(self, timeline):
        if self.sim.transition_controller is not None:
            constraint = self.sim.transition_controller.get_final_constraint(self.sim)
            constraint.apply_posture_state(self.sim.posture_state, self.get_constraint_resolver(self.sim.posture_state))
            (single_point, _) = constraint.single_point()
            if single_point is None:
                self.remove_liability(STAND_SLOT_LIABILITY)
        if not self.disable_transitions:
            constraint_interaction = self.constraint_intersection()
            if constraint_interaction.tentative:
                raise AssertionError("Interaction's constraints are still tentative in perform(): {}.".format(self))
            if self.is_super or not (self.super_interaction is not None and constraint_interaction.valid):
                self.super_interaction._num_nowhere_mixers_executed_in_perform += 1
                if self.super_interaction._num_nowhere_mixers_executed_in_perform > Interaction.MAX_NOWHERE_MIXERS:
                    logger.error("SI: {} is repeatedly executing mixers with a nowhere constraint, auto completing the interaction so the game won't hang.", self.super_interaction)
                    self.super_interaction._auto_complete()
        (result, reason) = yield from self.setup_gen(timeline)
        if not result:
            self.cancel(FinishingType.FAILED_TESTS, cancel_reason_msg='Interaction failed setup on perform. {}'.format(result))
            return (result, reason)
        if self.is_finishing or not self._active:
            return (False, 'is_finishing or not active')
        if self._run_priority is not None:
            self._priority = self._run_priority
        completed = True
        consumed_exc = None
        try:
            self._performing = True
            self._start_time = services.time_service().sim_now
            if not self._pre_perform():
                return (False, 'pre_perform failed')
            self._trigger_interaction_start_event()
            self._add_club_rewards_liability()
            for liability in self._liabilities.values():
                liability.on_run()
            completed = False
            yield from self._do_perform_trigger_gen(timeline)
            completed = True
            if self.provided_posture_type is None:
                for required_sim in self.required_sims():
                    required_sim.last_affordance = self.affordance
            self._post_perform()
        except Exception as exc:
            for posture in self.sim.posture_state.aspects:
                if posture.source_interaction is self:
                    raise
            logger.exception('Exception while running interaction {0}', self)
            consumed_exc = exc
        finally:
            if not completed:
                with consume_exceptions('Interactions', 'Exception thrown while tearing down an interaction:'):
                    self.detach_conditional_actions()
                    self.kill()
            self._delay_behavior = None
            self._performing = False
            self.clear_outcome_results()
            if not self.is_super:
                self.remove_liability(AUTONOMY_MODIFIER_LIABILITY)
        return (True, None)

    def _pre_perform(self):
        if self.basic_content.sleeping:
            self._delay_behavior = element_utils.soft_sleep_forever()
        curfew_service = services.get_curfew_service()
        if self.basic_content is not None and curfew_service.sim_breaking_curfew(self.sim, self.target, self):
            curfew_service.add_broke_curfew_buff(self.sim)
        return True

    def _stop_delay_behavior(self):
        if self._delay_behavior is not None:
            self._delay_behavior.trigger_soft_stop()
            self._delay_behavior = None

    def _conditional_action_satisfied_callback(self, condition_group):
        conditional_action = condition_group.conditional_action
        action = conditional_action.interaction_action
        if action == ConditionalInteractionAction.GO_INERTIAL:
            self.satisfied = True
            self._stop_delay_behavior()
        elif action == ConditionalInteractionAction.EXIT_NATURALLY:
            if not self.is_finishing:
                self._finisher.on_pending_finishing_move(FinishingType.NATURAL, self)
            self.satisfied = True
            if self.staging:
                self.cancel(FinishingType.NATURAL, cancel_reason_msg='Conditional Action: Exit Naturally')
            self._stop_delay_behavior()
        elif action == ConditionalInteractionAction.EXIT_CANCEL:
            self.cancel(FinishingType.CONDITIONAL_EXIT, cancel_reason_msg='Conditional Action: Exit Cancel')
            self._stop_delay_behavior()
        elif action == ConditionalInteractionAction.LOWER_PRIORITY:
            self.priority = interactions.priority.Priority.Low
        if gsi_handlers.interaction_archive_handlers.is_archive_enabled(self):
            gsi_handlers.interaction_archive_handlers.add_exit_reason(self, action, condition_group)
        loot_actions = conditional_action.loot_actions
        if loot_actions:
            resolver = self.get_resolver()
            for actions in loot_actions:
                actions.apply_to_resolver(resolver)

    def refresh_conditional_actions(self):
        if self._conditional_action_manager:
            self.detach_conditional_actions()
            self.attach_conditional_actions()

    def attach_conditional_actions(self):
        if self.staging:
            self._satisfied = not self.get_start_as_guaranteed()
        conditional_actions = self.get_conditional_actions()
        if conditional_actions:
            self._conditional_action_manager.attach_conditions(self, conditional_actions, self._conditional_action_satisfied_callback, interaction=self)

    def detach_conditional_actions(self):
        if self._conditional_action_manager is not None:
            self._conditional_action_manager.detach_conditions(self, exiting=True)

    def _run_gen(self, timeline):
        result = yield from self._do_perform_gen(timeline)
        return result

    def _do_perform_trigger_gen(self, timeline):
        result = yield from self._do_perform_gen(timeline)
        return result

    def _get_behavior(self):
        self._run_interaction_element = self.build_basic_elements(sequence=self._run_interaction_gen)
        return self._run_interaction_element

    def _clean_behavior(self):
        self._run_interaction_element = None

    def _do_perform_gen(self, timeline):
        interaction_element = self._get_behavior()
        result = yield from element_utils.run_child(timeline, interaction_element)
        return result

    def register_additional_event_handlers(self, animation_context):
        if animation_context is not None:
            for (callback, handler_id) in self._animation_events:
                animation_context.register_event_handler(callback, handler_id=handler_id)
        else:
            logger.error('ASM Animation Context is None for interaction: {}. Cannot register additional event handlers.', self, owner='rmccord')
        self._animation_events.clear()

    def store_event_handler(self, callback, handler_id=None):
        self._animation_events.append((callback, handler_id))

    def build_basic_content(self, sequence=(), **kwargs):
        if self.basic_content is not None:
            sequence = self.basic_content(self, sequence=sequence, **kwargs)
            sequence = build_critical_section(sequence, self._set_last_animation_factory)
        if self.target is not None:
            target_basic_content = self.target.get_affordance_basic_content(self)
            if target_basic_content is not None:
                sequence = target_basic_content(self, sequence=sequence, **kwargs)
        return sequence

    def _build_outcome_sequence(self):
        sequence = self.outcome.build_elements(self, update_global_outcome_result=True)
        if self.target is not None:
            target_outcome = self.target.get_affordance_outcome(self)
            if target_outcome is not None:
                sequence = (sequence, target_outcome.build_elements(self))
        return sequence

    def build_outcome(self):
        return self._build_outcome_sequence()

    def build_basic_extras(self, sequence=()):
        for factory in reversed(self.basic_extras):
            sequence = factory(self, sequence=sequence)
        if self.target is not None:
            target_basic_extras = self.target.get_affordance_basic_extras(self)
            for factory in reversed(target_basic_extras):
                sequence = factory(self, sequence=sequence)
        if self._additional_basic_extras is not None:
            for factory in reversed(self._additional_basic_extras):
                sequence = factory(self, sequence=sequence)
        if self._additional_instance_basic_extras is not None:
            for factory in reversed(self._additional_instance_basic_extras):
                sequence = factory(self, sequence=sequence)
        if self.sim is not None:
            for factory in self.sim.get_actor_basic_extras_reversed_gen(self.affordance, self.get_resolver()):
                sequence = factory(self, sequence=sequence)
        if self.confirmation_dialog is not None:

            def on_response(dialog):
                if not dialog.accepted:
                    if self.confirmation_dialog.continuation_on_cancel:
                        self.push_tunable_continuation(self.confirmation_dialog.continuation_on_cancel)
                    self.cancel(FinishingType.USER_CANCEL, cancel_reason_msg='User did not confirm.')
                return dialog.accepted

            sequence = (self.confirmation_dialog.dialog(self.sim, self.get_resolver(), on_response=on_response), sequence)
        return sequence

    @classmethod
    def add_additional_basic_extra(cls, basic_extra):
        if cls._additional_basic_extras is None:
            cls._additional_basic_extras = []
        cls._additional_basic_extras.append(basic_extra)

    @classmethod
    def remove_additional_basic_extra(cls, basic_extra):
        cls._additional_basic_extras.remove(basic_extra)
        if not cls._additional_basic_extras:
            cls._additional_basic_extras = None

    @classmethod
    def add_additional_basic_liability(cls, basic_liability):
        if cls._additional_basic_liabilities is None:
            cls._additional_basic_liabilities = []
        cls._additional_basic_liabilities.append(basic_liability)

    def add_additional_instance_basic_extra(self, basic_extra):
        if self._additional_instance_basic_extras is None:
            self._additional_instance_basic_extras = []
        self._additional_instance_basic_extras.append(basic_extra)

    def get_item_cost_content(self):
        if self.item_cost.ingredients:
            return self.item_cost.consume_interaction_cost(self)

    def _decay_topics(self, e):
        if self.sim is not None:
            self.sim.decay_topics()

    def _set_last_animation_factory(self, _):
        if self.basic_content.animation_ref is not None:
            self.sim.last_animation_factory = self.basic_content.animation_ref.factory
            if self.target.parent is self.sim:
                self.target.last_animation_factory = None

    def get_keys_to_process_events(self):
        custom_keys = set(self.get_category_tags())
        custom_keys.add(self.affordance.get_interaction_type())
        associated_skill = self.get_associated_skill()
        if associated_skill is not None:
            custom_keys.update(associated_skill.tags)
        return custom_keys

    def _trigger_interaction_complete_test_event(self):
        custom_keys = self.get_keys_to_process_events()
        for participant in self.get_participants(ParticipantType.AllSims):
            if participant is not None:
                services.get_event_manager().process_event(test_events.TestEvent.InteractionComplete, sim_info=participant.sim_info, interaction=self, custom_keys=custom_keys)
        self.remove_event_auto_update()

    def _trigger_interaction_exited_pipeline_test_event(self):
        custom_keys = self.get_keys_to_process_events()
        actor = self.sim
        if actor is not None:
            services.get_event_manager().process_event(test_events.TestEvent.InteractionExitedPipeline, sim_info=actor.sim_info, interaction=self, custom_keys=custom_keys)

    def _build_pre_elements(self):
        pass

    def build_basic_elements(self, sequence=(), **kwargs):
        sequence = self.build_basic_content(sequence=sequence, **kwargs)
        sequence = (lambda _: self.send_current_progress(), sequence)
        if not self.is_basic_content_one_shot:
            sequence = build_critical_section_with_finally(lambda _: self.attach_conditional_actions(), sequence, lambda _: self.detach_conditional_actions())
        listeners = list(self.get_participants(ParticipantType.Listeners, listener_filtering_enabled=True))
        sequence = self.with_listeners(listeners, sequence)
        sequence = build_critical_section(self.get_item_cost_content(), sequence, self._decay_topics, self.build_outcome())
        sequence = self.build_basic_extras(sequence=sequence)
        if self.sim is not None:
            sequence = (lambda _: self.sim.trait_tracker.update_day_night_tracking_state(), sequence)
            if self.sim.has_component(objects.components.types.WEATHER_AWARE_COMPONENT):
                sequence = (lambda _: self.sim.weather_aware_component.on_location_changed_callback(), sequence)
        if not self.disable_transitions:
            create_target_track = self.carry_track if self.create_target is not None else None
            sequence = interact_with_carried_object(self.sim, self.carry_target or self.target, interaction=self, create_target_track=create_target_track, sequence=sequence)
            sequence = holster_carried_object(self.sim, self, self.should_unholster_carried_object, sequence=sequence)
        if self.provided_posture_type is None:
            if self.basic_focus is False:
                sequence = sim_focus.without_sim_focus(self.sim, self.sim, sequence)
            else:
                sequence = self.basic_focus(self, sequence=sequence)
        if (self.immediate or self.basic_focus is not None) and self.autonomy_preference is not None:
            should_set = self.autonomy_preference.preference.should_set
            if self.is_user_directed or should_set.autonomous:

                def set_preference(_):
                    self.sim.set_autonomy_preference(self.autonomy_preference.preference, self.target)
                    return True

                sequence = (set_preference, sequence)
        if self.target is not None and (self._provided_posture_type is None and isinstance(self.target, objects.game_object.GameObject)) and self.target.autonomy_modifiers:
            self.add_liability(AUTONOMY_MODIFIER_LIABILITY, AutonomyModifierLiability(self))
        for participant in self.get_participants(ParticipantType.All):
            sequence = participant.add_modifiers_for_interaction(self, sequence=sequence)
        reservation_handler = self.get_interaction_reservation_handler()
        if not self.get_liability(RESERVATION_LIABILITY):
            sequence = reservation_handler.do_reserve(sequence=sequence)
        if not (reservation_handler is not None and self.immediate):
            sequence = build_critical_section(sequence, flush_all_animations)
        communicable_commodities = set()
        if self.sim is not None:
            communicable_commodities |= self.sim.commodity_tracker.get_communicable_statistic_set()
        if self.target != self.sim:
            communicable_commodities |= self.target.commodity_tracker.get_communicable_statistic_set()
        for commodity in communicable_commodities:
            for tag_loot_pair in commodity.communicable_by_interaction_tag:
                if len(self.get_category_tags() & {tag_loot_pair.tag}) > 0:
                    tag_loot_pair.loot.apply_to_resolver(self.get_resolver())
                    break
        animation_liability = self.get_animation_context_liability()
        sequence = build_critical_section_with_finally(lambda _: animation_liability.setup_props(self), sequence, lambda _: animation_liability.unregister_handles(self))
        template_affordance_tracker = self.sim.sim_info.template_affordance_tracker if self.target is not None and self.sim is not None else None
        provided_template_affordances = self.provided_template_affordances
        if provided_template_affordances is not None:
            sequence = build_critical_section_with_finally(lambda _: template_affordance_tracker.on_affordance_template_start(provided_template_affordances), sequence, lambda _: template_affordance_tracker.on_affordance_template_stop(provided_template_affordances))

        def sync_element(_):
            try:
                if self.sim is None or self.immediate:
                    return
                noop = distributor.ops.SetLocation(self.sim)
                added_additional_channel = False
                for additional_sim in self.required_sims():
                    if additional_sim is self.sim:
                        pass
                    else:
                        added_additional_channel = True
                        noop.add_additional_channel(additional_sim.manager.id, additional_sim.id)
                if added_additional_channel:
                    distributor.ops.record(self.sim, noop)
            except Exception:
                logger.exception('Exception when trying to create the Sync Element at the end of {}', self, owner='maxr')

        return build_element((self._build_pre_elements(), sequence, sync_element))

    def _run_interaction_gen(self, timeline):
        if self._delay_behavior:
            result = yield from element_utils.run_child(timeline, self._delay_behavior)
            return result
        return True

    def get_continuation_aop_and_context(self, continuation, actor, insert_strategy=QueueInsertStrategy.NEXT, affordance_override=None, **kwargs):
        if actor is self.sim:
            if self.immediate:
                clone_context_fn = functools.partial(self.context.clone_from_immediate_context, self)
            elif continuation.affordance.is_super and self.super_interaction is not None:
                clone_context_fn = functools.partial(self.super_interaction.context.clone_for_continuation, self.super_interaction)
            else:
                clone_context_fn = functools.partial(self.context.clone_for_continuation, self)
        else:
            group_id = self.super_interaction.group_id if self.super_interaction is not None else None
            clone_context_fn = functools.partial(self.context.clone_for_sim, actor, group_id=group_id)
        source_interaction_id = self.super_interaction.id if self.super_interaction is not None else None
        source_interaction_sim_id = self.sim.sim_id if self.sim is not None else None
        if continuation.preserve_preferred_object:
            pick = self.context.pick
            preferred_objects = self.context.preferred_objects
        else:
            pick = None
            preferred_objects = set()
        context = clone_context_fn(insert_strategy=insert_strategy, source_interaction_id=source_interaction_id, source_interaction_sim_id=source_interaction_sim_id, pick=pick, preferred_objects=preferred_objects)
        if not continuation.affordance.involves_carry:
            context.carry_target = None
        elif continuation.carry_target is not None:
            context.carry_target = self.get_participant(continuation.carry_target)
        elif continuation.inventory_carry_target is not None:
            inventory_carry_target = continuation.inventory_carry_target
            check_type = inventory_carry_target.check_type
            for item in actor.inventory_component:
                if check_type == TunableContinuation.ITEM_DEFINITION:
                    if item.definition is inventory_carry_target.definition:
                        context.carry_target = item
                        break
                elif check_type == TunableContinuation.ITEM_TUNING_ID:
                    if item.definition.tuning_file_id == inventory_carry_target.definition.tuning_file_id:
                        context.carry_target = item
                        break
                elif check_type == TunableContinuation.TAGGED_ITEM and inventory_carry_target(item, None):
                    context.carry_target = item
                    break
        if continuation.target != ParticipantType.Invalid:
            targets = self.get_participants(continuation.target)
            target = next(iter(targets), None)
        else:
            target = None
        if target.is_sim:
            if isinstance(target, sims.sim_info.SimInfo):
                target = target.get_sim_instance()
        elif target.is_part:
            target = target.part_owner
        affordance = continuation.affordance if target is not None and affordance_override is None else affordance_override
        kwargs_copy = kwargs.copy()
        join_target_ref = self.interaction_parameters.get('join_target_ref')
        if join_target_ref is not None:
            kwargs_copy['join_target_ref'] = join_target_ref
        if 'picked_item_ids' not in kwargs_copy:
            picked_items = self.get_participants(ParticipantType.PickedItemId)
            if picked_items:
                kwargs_copy['picked_item_ids'] = picked_items
        if 'picked_zone_ids' not in kwargs_copy:
            picked_zones = self.get_participants(ParticipantType.PickedZoneId)
            if picked_zones:
                kwargs_copy['picked_zone_ids'] = picked_zones
        kwargs_copy['saved_participants'] = self._saved_participants
        if affordance.is_super:
            aop = interactions.aop.AffordanceObjectPair(affordance, target, affordance, None, picked_object=self.target, **kwargs_copy)
        else:
            if continuation.si_affordance_override is not None:
                super_affordance = continuation.si_affordance_override
                super_interaction = None
                push_super_on_prepare = True
            else:
                super_affordance = self.super_affordance
                super_interaction = self.super_interaction
                push_super_on_prepare = False
            aop = interactions.aop.AffordanceObjectPair(affordance, target, super_affordance, super_interaction, picked_object=self.target, push_super_on_prepare=push_super_on_prepare, **kwargs_copy)
        return (aop, context)

    def get_aops_and_contexts_for_tunable_continuation(self, tunable_continuation, multi_push=True, insert_strategy=QueueInsertStrategy.NEXT, actor=DEFAULT, **kwargs):
        num_success = collections.defaultdict(int)
        num_required = collections.defaultdict(int)
        aops_contexts = []
        continuations = tunable_continuation
        if insert_strategy == QueueInsertStrategy.NEXT:
            continuations = reversed(tunable_continuation)
        for continuation in continuations:
            if actor is DEFAULT:
                local_actors = self.get_participants(continuation.actor)
            else:
                local_actors = (actor,)
            for local_actor in local_actors:
                if isinstance(local_actor, sims.sim_info.SimInfo):
                    pass
                else:
                    if multi_push:
                        num_required[local_actor.id] += 1
                    else:
                        num_required[local_actor.id] = 1
                        if num_success[local_actor.id] > 0:
                            pass
                        else:
                            (aop, context) = self.get_continuation_aop_and_context(continuation, local_actor, insert_strategy=insert_strategy, **kwargs)
                            result = aop.test(context, **kwargs)
                            if result:
                                num_success[local_actor.id] += 1
                                aops_contexts.append((aop, context))
                    (aop, context) = self.get_continuation_aop_and_context(continuation, local_actor, insert_strategy=insert_strategy, **kwargs)
                    result = aop.test(context, **kwargs)
                    if result:
                        num_success[local_actor.id] += 1
                        aops_contexts.append((aop, context))
        return aops_contexts

    def push_tunable_continuation(self, tunable_continuation, multi_push=True, insert_strategy=QueueInsertStrategy.NEXT, actor=DEFAULT, **kwargs):
        num_pushed = collections.defaultdict(int)
        num_required = collections.defaultdict(int)
        continuations = tunable_continuation
        if insert_strategy == QueueInsertStrategy.NEXT:
            continuations = reversed(tunable_continuation)
        for continuation in continuations:
            if actor is DEFAULT:
                local_actors = self.get_participants(continuation.actor)
            else:
                local_actors = (actor,)
            for local_actor in local_actors:
                if isinstance(local_actor, sims.sim_info.SimInfo):
                    pass
                else:
                    if multi_push:
                        num_required[local_actor.id] += 1
                    else:
                        num_required[local_actor.id] = 1
                        if num_pushed[local_actor.id] > 0:
                            pass
                        else:
                            (aop, context) = self.get_continuation_aop_and_context(continuation, local_actor, insert_strategy=insert_strategy, interaction_name=self.get_name(), interaction_icon_info=self.get_icon_info(), **kwargs)
                            result = aop.test_and_execute(context)
                            if result:
                                num_pushed[local_actor.id] += 1
                    (aop, context) = self.get_continuation_aop_and_context(continuation, local_actor, insert_strategy=insert_strategy, interaction_name=self.get_name(), interaction_icon_info=self.get_icon_info(), **kwargs)
                    result = aop.test_and_execute(context)
                    if result:
                        num_pushed[local_actor.id] += 1
        return num_pushed == num_required

    def _post_perform(self):
        if not self.is_finishing:
            self._finisher.on_finishing_move(FinishingType.NATURAL, self)
        self._active = False
        curfew_service = services.get_curfew_service()
        if not curfew_service.sim_breaking_curfew(self.sim, self.target, self):
            curfew_service.remove_broke_curfew_buff(self.sim)

    def required_sims(self, *args, for_threading=False, **kwargs):
        cached_required_sims = self._required_sims if not for_threading else self._required_sims_threading
        if cached_required_sims is not None:
            return cached_required_sims
        else:
            return self._get_required_sims(*args, for_threading=for_threading, **kwargs)

    def get_mutexed_resources(self):
        mutexed_resources = set()

        def _can_be_mutexed_resource(obj):
            if obj is None:
                return False
            if obj.is_sim:
                return False
            elif obj.objectrouting_component is None:
                return False
            return True

        if self.target_type & TargetType.TARGET:
            obj = self.get_participant(ParticipantType.Object)
            if _can_be_mutexed_resource(obj):
                mutexed_resources.add(obj)
        return mutexed_resources

    def has_sim_in_required_sim_cache(self, sim_in_question):
        if self._required_sims is None:
            return False
        return sim_in_question in self._required_sims

    def required_resources(self):
        return set()

    def is_required_sims_locked(self):
        return isinstance(self._required_sims, frozenset)

    def refresh_and_lock_required_sims(self):
        self._required_sims = frozenset(self._get_required_sims())
        self._required_sims_threading = frozenset(self._get_required_sims(for_threading=True))

    def remove_required_sim(self, sim):
        if self._required_sims is None:
            logger.error('Trying to remove a Sim {} even though we have not yet reserved a list of required Sims.', sim)
            return
        if sim in self._required_sims:
            self._required_sims -= {sim}
            sim.queue.transition_controller = None

    def unlock_required_sims(self):
        self._required_sims = None

    def _get_required_sims(self, *args, **kwargs):
        return {self.sim}

    def notify_queue_head(self):
        pass

    def on_incompatible_in_queue(self):
        if self.context.cancel_if_incompatible_in_queue:
            self.cancel(FinishingType.INTERACTION_INCOMPATIBILITY, 'Canceled because cancel_if_incompatible_in_queue == True')

    def _trigger_interaction_start_event(self):
        if self.sim is not None:
            services.get_event_manager().process_event(test_events.TestEvent.InteractionStart, sim_info=self.sim.sim_info, interaction=self, custom_keys=self.get_keys_to_process_events())
            self.register_event_auto_update()

    def _add_club_rewards_liability(self):
        club_service = services.get_club_service()
        if club_service is None:
            return
        cr_liability = club_service.create_rewards_buck_liability(self.sim.sim_info, self)
        if cr_liability is not None:
            self.add_liability(cr_liability.LIABILITY_TOKEN, cr_liability)

    def register_event_auto_update(self):
        if self._interaction_event_update_alarm is not None:
            self.remove_event_auto_update()
        self._interaction_event_update_alarm = alarms.add_alarm(self, create_time_span(minutes=15), lambda _, sim_info=self.sim.sim_info, interaction=self, custom_keys=self.get_keys_to_process_events(): services.get_event_manager().process_event(test_events.TestEvent.InteractionUpdate, sim_info=sim_info, interaction=interaction, custom_keys=custom_keys), True)

    def remove_event_auto_update(self):
        if self._interaction_event_update_alarm is not None:
            alarms.cancel_alarm(self._interaction_event_update_alarm)
            self._interaction_event_update_alarm = None

    def _interrupt_active_work(self, kill=False, finishing_type=None):
        element = self._run_interaction_element
        if element is not None:
            if kill:
                element.trigger_hard_stop()
            else:
                element.trigger_soft_stop()
        return True

    def invalidate(self):
        if self.pipeline_progress == PipelineProgress.NONE:
            if self.transition is not None:
                self.transition.shutdown()
            if self.depended_on_si is not None:
                self.depended_on_si.detach_interaction(self)
            self._finisher.on_finishing_move(FinishingType.KILLED, self)
            self.release_liabilities()

    def kill(self):
        if self.has_been_killed:
            return False
        self._finisher.on_finishing_move(FinishingType.KILLED, self)
        self._interrupt_active_work(kill=True, finishing_type=FinishingType.KILLED)
        self._active = False
        if self.queue is not None:
            self.queue.on_interaction_canceled(self)
        return True

    def cancel(self, finishing_type, cancel_reason_msg, ignore_must_run=False, **kwargs):
        user_cancel_liability = self.get_liability(UserCancelableChainLiability.LIABILITY_TOKEN)
        if user_cancel_liability is not None and finishing_type == FinishingType.USER_CANCEL:
            user_cancel_liability.set_user_cancel_requested()
        if self.is_finishing or not (self.must_run and ignore_must_run):
            return False
        self._finisher.on_finishing_move(finishing_type, self)
        self._interrupt_active_work(finishing_type=finishing_type)
        self._active = False
        if self.queue is not None:
            self.queue.on_interaction_canceled(self)
        self._on_cancelled_callbacks(self)
        self._on_cancelled_callbacks.clear()
        return True

    def displace(self, displaced_by, **kwargs):
        return self.cancel(FinishingType.DISPLACED, **kwargs)

    def on_reset(self):
        if self._finisher.has_been_reset:
            return
        self._finisher.on_finishing_move(FinishingType.RESET, self)
        self._active = False
        for liability in list(self.liabilities):
            liability.on_reset()
        self._liabilities.clear()
        self.remove_event_auto_update()

    def cancel_user(self, cancel_reason_msg, on_response=None):

        def _send_response(response):
            if on_response is not None:
                on_response(response)

        if self.get_liability(UNCANCELABLE_LIABILITY) is not None:
            return False
        if self._cancelable_by_user == CancelablePhase.NEVER or not (self._cancelable_by_user == CancelablePhase.RUNNING and self.running):
            _send_response(False)
            return False
        if self._cancelable_by_user == CancelablePhase.ALWAYS or self._cancelable_by_user == CancelablePhase.RUNNING and self.running or not self.prepared:
            result = self.cancel(FinishingType.USER_CANCEL, cancel_reason_msg=cancel_reason_msg)
            _send_response(True)
            return result

        def on_cancel_dialog_response(dialog):
            if dialog.accepted:
                self.cancel(FinishingType.USER_CANCEL, cancel_reason_msg=cancel_reason_msg)
            else:
                self.sim.ui_manager.update_interaction_cancel_status(self)
            _send_response(dialog.accepted)

        dialog = self._cancelable_by_user(self.sim, self.get_resolver())
        dialog.show_dialog(on_response=on_cancel_dialog_response)
        return True

    def should_visualize_interaction_for_sim(self, participant_type):
        return participant_type == ParticipantType.Actor

    @classmethod
    def additional_mixers_to_cache(cls):
        return 0

    @classproperty
    def has_visible_content_sets(cls):
        return False

    def get_interaction_queue_visual_type(self):
        if self.visual_type_override is not None:
            return (InteractionQueueVisualType.get_interaction_visual_type(self.visual_type_override), self.visual_type_override_data)
        if not self.is_super:
            return (Sims_pb2.Interaction.MIXER, self.visual_type_override_data)
        if self.has_visible_content_sets:
            return (Sims_pb2.Interaction.PARENT, self.visual_type_override_data)
        sim_posture = self.sim.posture
        if sim_posture.source_interaction is self:
            return (Sims_pb2.Interaction.POSTURE, self.visual_type_override_data)
        return (Sims_pb2.Interaction.SIMPLE, self.visual_type_override_data)

    def on_added_to_queue(self, interaction_id_to_insert_after=None, notify_client=True):
        self.pipeline_progress = PipelineProgress.QUEUED
        self._entered_pipeline()
        self.sim.ui_manager.add_queued_interaction(self, interaction_id_to_insert_after=interaction_id_to_insert_after, notify_client=notify_client)
        if self.should_visualize_interaction_for_sim(ParticipantType.TargetSim):
            target_sim = self.get_participant(ParticipantType.TargetSim)
            if target_sim is not None and target_sim is not self.sim:
                target_sim.ui_manager.add_queued_interaction(self, notify_client=notify_client)
        additional_basic_liabilities = () if self._additional_basic_liabilities is None else self._additional_basic_liabilities
        for liability in itertools.chain(self.basic_liabilities, additional_basic_liabilities):
            liability = liability(self)
            self.add_liability(liability.LIABILITY_TOKEN, liability)

    def on_removed_from_queue(self):
        if self.pipeline_progress < PipelineProgress.RUNNING or self.is_super or self.pipeline_progress < PipelineProgress.EXITED:
            if self.sim is None:
                logger.error('Removing interaction {} from queue from a None Sim', self, owner='camilogarcia')
            else:
                self.sim.ui_manager.remove_queued_interaction(self)
            if self.should_visualize_interaction_for_sim(ParticipantType.TargetSim):
                target_sim = self.get_participant(ParticipantType.TargetSim)
                if target_sim is not None and target_sim is not self.sim:
                    target_sim.ui_manager.remove_queued_interaction(self)
            if not self.is_finishing:
                self.cancel(FinishingType.INTERACTION_QUEUE, 'Being removed from queue without successfully running.', ignore_must_run=True, immediate=True)
            self._exited_pipeline()

    def _entered_pipeline(self):
        self._acquire_liabilities()
        if self.target is not None:
            self.target.add_interaction_reference(self)

    def _exited_pipeline(self, *args, send_exited_events=True, **kwargs):
        if not self.is_finishing:
            logger.callstack('Exiting pipeline without having canceled an interaction: \n   {}\n   Pending Finishing Move: {}\n   PipelineProgress:{}', self, self._finisher.get_pending_finishing_move_debug_string(), self.pipeline_progress, level=sims4.log.LEVEL_WARN, owner='bhill')
            self.cancel(FinishingType.UNKNOWN, 'Exiting pipeline without canceling.', ignore_must_run=True, immediate=True)
        if self.target is not None:
            self.target.remove_interaction_reference(self)
        if gsi_handlers.interaction_archive_handlers.is_archive_enabled(self):
            gsi_handlers.interaction_archive_handlers.archive_interaction(self.sim, self, 'Complete')
        if self.pipeline_progress >= PipelineProgress.EXITED:
            logger.callstack('_exited_pipeline called twice on {}', self, level=sims4.log.LEVEL_ERROR)
            return
        completed = self.pipeline_progress >= PipelineProgress.RUNNING
        self.pipeline_progress = PipelineProgress.EXITED
        if self.is_super:
            animation_liability = self.get_liability(ANIMATION_CONTEXT_LIABILITY)
            if animation_liability is not None:
                for (posture, key_list) in animation_liability.cached_asm_keys.items():
                    for key in key_list:
                        posture.remove_from_cache(key)
                animation_liability.cached_asm_keys.clear()
        self.release_liabilities()
        for asm in self._asm_states:
            if self.on_asm_state_changed in asm.on_state_changed_events:
                asm.on_state_changed_events.remove(self.on_asm_state_changed)
        if completed:
            self._trigger_interaction_complete_test_event()
        self._object_create_helper = None
        if self.sim is not None:
            self.sim.skip_autonomy(self, False)
        if send_exited_events:
            self._trigger_interaction_exited_pipeline_test_event()
        if self._report_running_time:
            total_sim_minutes_taken = self.consecutive_running_time_span.in_minutes()
            with telemetry_helper.begin_hook(interaction_telemetry_writer, TELEMETRY_HOOK_INTERACTION_END, sim=self.sim) as hook:
                hook.write_int(TELEMETRY_FIELD_INTERACTION_ID, self.guid64)
                hook.write_int(TELEMETRY_FIELD_INTERACTION_RUNNING_TIME, total_sim_minutes_taken)
        self._saved_participants = [None, None, None, None]
        self._clean_behavior()

    def _do(self, *args):
        raise RuntimeError('Calling _do on interaction is not supported')

    def disallows_full_autonomy(self, disable_full_autonomy=DEFAULT):
        return False

    def _update_autonomy_timer(self, force_user_directed=False):
        self.sim.skip_autonomy(self, False)
        if force_user_directed or self.is_user_directed:
            self.sim.set_last_user_directed_action_time()
            if self.is_social and self.target is not None and self.target.is_sim:
                self.target.set_last_user_directed_action_time()
        elif self.source == InteractionContext.SOURCE_AUTONOMY:
            self.sim.set_last_autonomous_action_time()

    def register_on_finishing_callback(self, callback):
        self._finisher.register_callback(callback)

    def unregister_on_finishing_callback(self, callback):
        self._finisher.unregister_callback(callback)

    @classproperty
    def is_teleport_style_injection_allowed(cls):
        return False

    @constproperty
    def should_perform_routing_los_check():
        return True

    @property
    def allow_outcomes(self):
        if not self.is_super:
            return True
        if self.immediate:
            return True
        if self.is_basic_content_one_shot:
            return True
        if self.is_finishing or self._finisher.has_pending_natural_finisher:
            return True
        elif self.is_finishing_naturally:
            return True
        return False

    @property
    def is_finishing(self):
        return self._finisher.is_finishing

    @property
    def user_canceled(self):
        return self._finisher.has_been_user_canceled

    @property
    def is_finishing_naturally(self):
        return self._finisher.is_finishing_naturally

    @property
    def transition_failed(self):
        return self._finisher.transition_failed

    @property
    def will_exit(self):
        return self.is_finishing

    @property
    def was_initially_displaced(self):
        return self._finisher.was_initially_displaced

    @property
    def uncanceled(self):
        if not self._finisher.is_finishing:
            return True
        elif self._finisher.is_finishing_naturally:
            return True
        return False

    @property
    def has_active_cancel_replacement(self):
        return self.sim.queue.cancel_aop_exists_for_si(self)

    @property
    def is_cancel_aop(self):
        return self.context.is_cancel_aop

    @property
    def has_been_killed(self):
        return self._finisher.has_been_killed

    @property
    def has_been_canceled(self):
        return self._finisher.has_been_canceled

    @property
    def has_been_user_canceled(self):
        return self._finisher.has_been_user_canceled

    @property
    def has_been_reset(self):
        return self._finisher.has_been_reset

    def finisher_repr(self):
        return self._finisher.__repr__()

    @property
    def global_outcome_result(self):
        return self._global_outcome_result

    @global_outcome_result.setter
    def global_outcome_result(self, value):
        self._global_outcome_result = value

    def get_result_for_outcome(self, outcome):
        return self._outcome_result_map.get(outcome, None)

    def store_result_for_outcome(self, outcome, result):
        if result in self._outcome_result_map:
            logger.error('Overriding an existing outcome result. Outcome {}, Previous Result {}, New Result {}, Interaction {}', outcome, self._outcome_result_map[outcome], result, self, owner='tastle')
            return
        self._outcome_result_map[outcome] = result

    def clear_outcome_results(self):
        self._outcome_result_map.clear()

    def is_equivalent(self, interaction, target=DEFAULT):
        if target is DEFAULT:
            target = interaction.target
        return self.get_interaction_type() is interaction.get_interaction_type() and self.target is target

    def merge(self, other):
        if self.context.priority < other.context.priority:
            self.context.priority = interactions.priority.Priority(other.context.priority)
            self.context.source = other.context.source
        self.refresh_conditional_actions()

    def should_unholster_carried_object(self, obj):
        if obj.should_unholster():
            return obj is self.target or obj is self.carry_target
        return not self.is_super

    def cancel_incompatible_carry_interactions(self, can_defer_putdown=True, derail_actors=False):
        needs_derail = False
        if isinstance(self, interactions.base.teleport_interaction.TeleportHereInteraction):
            can_defer_putdown = False
        for (owning_interaction, carry_posture) in self.get_uncarriable_objects_gen(posture_state=None):
            if can_defer_putdown and carry_posture.target.carryable_component.defer_putdown:
                pass
            elif not owning_interaction.is_cancel_aop:
                if derail_actors or self.is_super and owning_interaction.sim is not self.sim:
                    needs_derail = True
                owning_interaction.cancel(FinishingType.INTERACTION_INCOMPATIBILITY, cancel_reason_msg='Incompatible with carry')
        if needs_derail:
            services.get_master_controller().set_timestamp_for_sim_to_now(self.sim)
            return False
        return True

    def get_uncarriable_objects_gen(self, posture_state=DEFAULT, allow_holster=DEFAULT, use_holster_compatibility=False):
        carry_target = self.carry_target or self.super_interaction.carry_target
        interaction_target = self.target
        for sim in self.required_sims():
            participant_type = self.get_participant_type(sim)
            if participant_type is None:
                pass
            else:
                if not sim.is_allowed_to_holster():
                    allow_holster = False
                else:
                    for (_, carry_posture, carry_object) in get_carried_objects_gen(sim):
                        if self.allow_with_unholsterable_carries:
                            allow_holster = True
                        else:
                            allow_holster = False
                        break
                        if carry_object.is_sim and not carry_object is not carry_target or carry_object is not interaction_target:
                            for owning_interaction in carry_posture.owning_interactions:
                                if not owning_interaction.allow_holstering_of_owned_carries:
                                    allow_holster = False
                                    break
                current_interaction_constraint = None
                current_interaction_constraint = self.constraint_intersection(sim=sim, participant_type=participant_type, posture_state=posture_state, allow_holster=allow_holster)
                posture_specs = current_interaction_constraint.get_posture_specs(interaction=self)
                for (_, var_map, _) in posture_specs:
                    var_map_carry_target = var_map.get(PostureSpecVariable.CARRY_TARGET, None)
                    if var_map_carry_target is None:
                        pass
                    else:
                        hand = var_map[PostureSpecVariable.HAND] if var_map_carry_target is carry_target else None
                        if hand is not None:
                            temp_carry_posture = carry_target.get_carry_object_posture()(sim, carry_target, hand)
                            if temp_carry_posture.is_two_handed_carry:
                                current_interaction_constraint = current_interaction_constraint.intersect(create_two_handed_carry_constraint(carry_target, hand))
                                break
                forced_tentative_interaction_constraint = UNSET
                for (carry_hand, carry_posture, carry_object) in get_carried_objects_gen(sim):
                    current_interaction_constraint = self.constraint_intersection(sim=sim, participant_type=participant_type, posture_state=posture_state, allow_holster=allow_holster)
                    if posture_state is None:
                        forced_tentative_interaction_constraint = current_interaction_constraint
                    else:
                        forced_tentative_interaction_constraint = None
                    if (not current_interaction_constraint is None or not forced_tentative_interaction_constraint == UNSET or carry_object is not carry_target) and carry_object is not interaction_target:
                        for owning_interaction in list(carry_posture.owning_interactions):
                            if not use_holster_compatibility or not carry_object.carryable_component.holster_compatibility(self.super_affordance):
                                yield (owning_interaction, carry_posture)
                            elif not self.is_super or not interactions.si_state.SIState.test_non_constraint_compatibility(self, owning_interaction, owning_interaction.target):
                                yield (owning_interaction, carry_posture)
                            else:
                                if owning_interaction.running:
                                    other_constraint = owning_interaction.constraint_intersection(posture_state=posture_state)
                                    other_constraint = other_constraint.generate_body_posture_only_constraint()
                                    other_constraint = other_constraint.intersect(create_two_handed_carry_constraint(carry_object, carry_hand))
                                    interaction_constraint = current_interaction_constraint
                                else:
                                    other_constraint = owning_interaction.constraint_intersection(posture_state=None)
                                    forced_tentative_interaction_constraint = self.constraint_intersection(sim=sim, participant_type=participant_type, posture_state=None, allow_holster=allow_holster)
                                    interaction_constraint = forced_tentative_interaction_constraint
                                if participant_type == ParticipantType.Listeners:
                                    constraint_resolver = self.get_constraint_resolver(None, participant_type=participant_type, force_actor=sim)
                                else:
                                    constraint_resolver = self.get_constraint_resolver(None, participant_type=participant_type)
                                other_constraint = other_constraint.apply_posture_state(None, constraint_resolver)
                                intersection = interaction_constraint.intersect(other_constraint)
                                if not intersection.valid:
                                    yield (owning_interaction, carry_posture)
                                else:
                                    for sub_constraint in intersection:
                                        break
                                        body_target = sub_constraint.posture_state_spec.body_target
                                        if sub_constraint.posture_state_spec is None and body_target is not None and not isinstance(body_target, PostureSpecVariable):
                                            surface = body_target.parent
                                        else:
                                            surface = None
                                        break
                                        for manifest_entry in sub_constraint.posture_state_spec.posture_manifest:
                                            if manifest_entry.surface_target is MATCH_NONE:
                                                pass
                                            else:
                                                break
                                        break
                                        for runtime_slot in surface.get_runtime_slots_gen():
                                            if not runtime_slot.is_valid_for_placement(obj=carry_object, objects_to_ignore=[carry_object]):
                                                pass
                                            else:
                                                break
                                        break
                                    yield (owning_interaction, carry_posture)

    def register_on_cancelled_callback(self, callback):
        self._on_cancelled_callbacks.append(callback)

    def send_current_progress(self, new_interaction=True):
        self.send_progress_bar_message(new_interaction=new_interaction)

    def send_progress_bar_message(self, new_interaction=True):
        if self.progress_bar_enabled.bar_enabled and (self.display_name and self.sim.is_selectable) and self.sim.valid_for_distribution:
            if self.progress_bar_enabled.force_listen_statistic:
                if self._progress_bar_commodity_callback is not None:
                    return
                progress_tuning = self.progress_bar_enabled.force_listen_statistic
                progress_target = self.get_participant(progress_tuning.subject)
                tracker = progress_target.get_tracker(progress_tuning.statistic)
                if tracker is not None and self._progress_bar_goal is None:
                    self._progress_bar_commodity_callback = tracker.add_watcher(self._progress_bar_update_statistic_callback)
                    override_value = progress_tuning.target_value.value
                    if override_value != 0:
                        _statistic = tracker.get_statistic(progress_tuning.statistic)
                        if _statistic is not None and _statistic.decay_rate != 0:
                            current_value = tracker.get_user_value(progress_tuning.statistic)
                            change_rate = (override_value - current_value)/(override_value*100)*_statistic.get_change_rate()
                            self._send_progress_bar_update_msg(0, change_rate, start_msg=True)
            elif self.progress_bar_enabled.interaction_exceptions.is_music_interaction:
                track_time = clock.interval_in_real_seconds(self._track.length).in_minutes()
                if track_time == 0:
                    logger.error('Progress bar: Tuned track time is 0 for interaction {}.', self, owner='camilogarcia')
                    return
                rate_change = 1/track_time
                self._send_progress_bar_update_msg(0, rate_change, start_msg=True)
            elif self._conditional_action_manager:
                (percent, rate_change) = self._conditional_action_manager.get_percent_rate_for_best_exit_conditions(self)
                if percent is not None:
                    if percent < 1:
                        rate_change = rate_change/(1 - percent)
                        percent = 0
                    self._send_progress_bar_update_msg(percent, rate_change, start_msg=True)

    def _progress_bar_update_statistic_callback(self, stat_type, old_value, new_value):
        if stat_type is not self.progress_bar_enabled.force_listen_statistic.statistic:
            return
        target_value = self.progress_bar_enabled.force_listen_statistic.target_value.value
        current_value = new_value
        if target_value < current_value:
            if self._progress_bar_goal is None:
                self._progress_bar_goal = current_value - target_value
            current_value = self._progress_bar_goal - new_value
        else:
            self._progress_bar_goal = target_value
        if self._progress_bar_goal == 0:
            return
        percent = current_value/self._progress_bar_goal
        self._send_progress_bar_update_msg(percent, 0, start_msg=True)

    def send_end_progress(self):
        if self._progress_bar_commodity_callback is not None:
            progress_tuning = self.progress_bar_enabled.force_listen_statistic
            progress_target = self.get_participant(progress_tuning.subject)
            if progress_target is not None:
                tracker = progress_target.get_tracker(progress_tuning.statistic)
                tracker.remove_watcher(self._progress_bar_commodity_callback)
            self._progress_bar_commodity_callback = None
        if self.user_canceled:
            return
        if self._progress_bar_displayed and self.sim.valid_for_distribution:
            self._send_progress_bar_update_msg(1, 0)

    def _send_progress_bar_update_msg(self, percent, rate_change, start_msg=False):
        if start_msg:
            self._progress_bar_displayed = True
        if self.sim is None:
            logger.error('Trying to update the progress of interaction where sim no longer exist: {}', self)
            return
        op = distributor.ops.InteractionProgressUpdate(self.sim.sim_id, percent, rate_change, self.id)
        Distributor.instance().add_op(self.sim, op)

    @property
    def acquire_listeners_as_resource(self):
        return False

    @flexmethod
    def get_resolver(cls, inst, target=DEFAULT, context=DEFAULT, super_interaction=None, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        if target == DEFAULT:
            target = inst_or_cls.target
        if context == DEFAULT:
            context = inst_or_cls.context
        return event_testing.resolver.InteractionResolver(cls, inst, target=target, context=context, super_interaction=super_interaction, **interaction_parameters)

    @flexmethod
    def get_interaction_reservation_handler(cls, inst, sim=DEFAULT, target=DEFAULT):
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls.basic_reserve_object is None:
            return
        sim = inst_or_cls.sim if sim is DEFAULT else sim
        if target is DEFAULT:
            reserve_object_fn = inst_or_cls.basic_reserve_object
        else:
            reserve_object_fn = functools.partial(inst_or_cls.basic_reserve_object, reserve_target=target)
        reservation_handler = reserve_object_fn(sim, inst)
        return reservation_handler

    @property
    def finishing_type(self):
        if self._finisher is not None:
            return self._finisher.finishing_type

    @classmethod
    def is_affordance_available(cls, context=None):
        shift_held = context.shift_held if context is not None else False
        if shift_held:
            if cls.cheat:
                return True
            if cls.debug and False:
                return True
            if cls.automation and paths.AUTOMATION_MODE:
                return True
        elif cls.debug or not cls.cheat:
            return True
        return False

    @property
    def fame_moment_active(self):
        return False
