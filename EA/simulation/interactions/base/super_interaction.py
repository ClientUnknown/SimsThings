from _sims4_collections import frozendictfrom _weakrefset import WeakSetfrom contextlib import contextmanagerimport itertoolsimport operatorimport weakreffrom animation.animation_constants import InteractionAsmTypefrom animation.animation_utils import flush_all_animationsfrom animation.posture_manifest_constants import STAND_NO_SURFACE_CONSTRAINT, STAND_OR_SIT_CONSTRAINTfrom autonomy.autonomy_modes import FullAutonomyfrom autonomy.autonomy_preference import TunableAutonomyPreferencefrom autonomy.autonomy_util import AutonomyAffordanceTimesfrom autonomy.content_sets import ContentSet, generate_content_setfrom autonomy.parameterized_autonomy_request_info import ParameterizedAutonomyRequestInfofrom distributor.shared_messages import IconInfoDatafrom element_utils import build_element, build_critical_section, build_critical_section_with_finallyfrom event_testing.resolver import SingleSimResolverfrom event_testing.results import TestResultfrom event_testing.test_utils import get_disallowed_agesfrom interactions import ParticipantType, PipelineProgress, TargetType, ParticipantTypeSim, ParticipantTypeSingleSimfrom interactions.aop import AffordanceObjectPairfrom interactions.base.basic import TunableBasicContentSetfrom interactions.base.interaction import Interaction, CancelGroupInteractionTypefrom interactions.base.interaction_constants import InteractionQueuePreparationStatusfrom interactions.choices import ChoiceMenufrom interactions.constraints import Anywhere, create_constraint_set, PostureConstraintFactoryfrom interactions.constraint_variants import TunableGeometricConstraintVariantfrom interactions.context import InteractionContext, InteractionBucketType, QueueInsertStrategy, InteractionSourcefrom interactions.interaction_finisher import FinishingTypefrom interactions.privacy import TunablePrivacySnippetfrom interactions.si_state import SIStatefrom interactions.utils.animation_reference import TunableAnimationReferencefrom interactions.utils.interaction_liabilities import CancelInteractionsOnExitLiability, CANCEL_INTERACTION_ON_EXIT_LIABILITY, OWNS_POSTURE_LIABILITY, OwnsPostureLiability, CANCEL_AOP_LIABILITY, CancelAOPLiabilityfrom interactions.utils.line_utils import LineUtilsfrom interactions.utils.tested_variant import TunableTestedVariantfrom interactions.utils.tunable_icon import TunableIconVariantfrom interactions.utils.tunable_provided_affordances import TunableProvidedAffordancesfrom interactions.utils.user_cancelable_chain_liability import UserCancelableChainLiabilityfrom interactions.vehicle_liabilities import VehicleLiabilityfrom objects.components.autonomy import TunableParameterizedAutonomyfrom objects.components.line_of_sight_component import TunableLineOfSightFactoryfrom objects.components.types import WAITING_LINE_COMPONENTfrom objects.definition import Definitionfrom objects.object_enums import ResetReasonfrom postures import PostureTrack, posture_graph, PostureTransitionTargetPreferenceTag, DerailReasonfrom postures.posture_graph import TransitionSequenceStagefrom postures.posture_scoring import TunableSimAffinityPostureScoringDatafrom postures.posture_specs import PostureOperation, PostureSpecVariablefrom postures.proxy_posture_owner_liability import ProxyPostureOwnerLiabilityfrom primitives.staged import StageControllerElementfrom reservation.reservation_result import ReservationResultfrom routing.route_enums import RouteEventTypefrom routing.route_events.route_event import RouteEventfrom routing.route_events.route_event_provider import RouteEventProviderMixinfrom routing.walkstyle.walkstyle_request import WalkStyleRequestfrom scheduling import HardStopErrorfrom sims.outfits.outfit_change import TunableOutfitChange, InteractionOnRouteOutfitChangefrom sims.outfits.outfit_enums import OutfitChangeReason, DefaultOutfitPriorityfrom sims.sim_info_types import Speciesfrom sims4.collections import enumdictfrom sims4.localization import TunableLocalizedString, TunableLocalizedStringFactoryfrom sims4.resources import Typesfrom sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.geometric import TunableVector2, TunablePolygon, TunableVector3, TunableWeightedUtilityCurveAndWeightfrom sims4.tuning.tunable import Tunable, TunableList, TunableReference, TunableTuple, OptionalTunable, TunableEnumEntry, TunableVariant, TunableSet, TunableMapping, TunableAngle, HasTunableSingletonFactory, AutoFactoryInit, TunableEnumSet, TunableSimMinutefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethod, classproperty, flexpropertyfrom singletons import DEFAULTfrom snippets import TunableAffordanceFilterSnippet, define_snippet, ANIMATION_ACTOR_MAPfrom statistics.statistic_conditions import StatisticConditionfrom tag import Tagfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport autonomy.autonomy_requestimport cachesimport element_utilsimport elementsimport enumimport event_testing.test_events as test_eventsimport event_testing.tests as testsimport gsi_handlers.interaction_archive_handlersimport interactions.priorityimport posturesimport servicesimport sims4.logimport situationslogger = sims4.log.Logger('Interactions')LOCK_ENTERING_SI = 'enter_si'
class LifetimeState(enum.Int, export=False):
    INITIAL = 0
    RUNNING = 1
    PENDING_COMPLETE = 2
    CANCELED = 3
    EXITED = 4

class RallyableTag(DynamicEnum):
    NONE = 0

class RallySource(enum.Int):
    SOCIAL_GROUP = ...
    ENSEMBLE = ...

class AnimationActorMap(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'target_override': OptionalTunable(description="\n            If specified, we will attempt to set this interaction's target to\n            the actor that matches the ParticipantType specified here.\n            ", tunable=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.Object)), 'carry_target': OptionalTunable(description='\n            This must be specified for any interaction that involves carrying\n            an object. The ParticipantType specified here will be used to find\n            the participant in this interaction to set to the carry_target.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.Object))}
(TunableAnimationActorMapReference, TunableAnimationActorMapSnippet) = define_snippet(ANIMATION_ACTOR_MAP, AnimationActorMap.TunableFactory())
class SuperInteraction(RouteEventProviderMixin, Interaction, StageControllerElement):
    MULTIPLAYER_REJECTED_TOOLTIP = TunableLocalizedString(description='\n            Grayed out Pie Menu Text on sim has already been rejected by other\n            player.\n            ')
    DEFAULT_POSTURE_TARGET_PREFERENCES = TunableMapping(description='\n            A tunable mapping of posture tags to a goal score bonus in meters.\n            This is used to make some objects more attractive than others for\n            the purposes of posture preference scoring.  That means that higher\n            numbers are good; the Sim will go x meters out of their way to use\n            these objects, where x is the amount tuned.\n            \n            For example, if one object has a score of 3 and another object has\n            a score of 0, the object that scores 0 will need to be more than 3\n            meters closer than the object that scores 3 for the Sim to choose\n            it.\n            \n            Example: Let\'s say you want to make couches more desirable for\n            watching TV.  To do this, you would create a new tag in\n            PostureTransitionTargetPreferenceTag (found in Tuning->postures)\n            called "ComfortableSeating".  Then you would tag all appropriate\n            objects with that tag by adding it to PosturePreferenceTagList on\n            the object.  Next, you would come in here and add a new item with a\n            key of that tag and a value of 10 or so, which is about the size of\n            the constraint to watch TV. Thus they will tend to use couches in\n            the TV cone at the expense of other factors. One example downside\n            of this is they will be less inclined to consider how centered they\n            are in the TV cone and what direction the sofa is facing.\n            ', key_type=TunableEnumEntry(PostureTransitionTargetPreferenceTag, PostureTransitionTargetPreferenceTag.INVALID), value_type=Tunable(float, 0))
    INSTANCE_TUNABLES = {'waiting_line': OptionalTunable(description='\n            Enable a waiting line for sims wanting to use this object. \n            ', tunable=TunableTuple(waiting_line_interaction=TunableReference(description='\n                    An affordance for waiting in-line.\n                    ', manager=services.affordance_manager()), waiting_line_key=Tunable(description='\n                    A key for distinguishing different lines on the same target.\n                    ', tunable_type=str, default='default_key'), line_cone=interactions.constraints.TunableCone(min_radius=0, max_radius=1, angle=sims4.math.PI, description='\n                    A cone describing how subsequent sims line\n                    up. A cone position at the intended position of the sim in\n                    front of us in the line. This constraint will ensure an\n                    organic looking line. *Note: do not alter the position of\n                    the cone.\n                    '), line_head_position=TunableVector2(description='\n                    The Sim at the head of the line will stand in a cone positioned at this point relative to the object.\n                    ', default=sims4.math.Vector2.ZERO(), x_axis_name='x', y_axis_name='z'), line_head_angle=TunableAngle(description="\n                    The Sim at the head of the line will stand facing this angle, relative to the target's orientation.\n                    ", default=sims4.math.PI), line_head_los_constraint=TunableLineOfSightFactory(description="\n                    The Line of Sight constraint for a sim standing at line's head and viewing the interaction target.\n                    "), route_nearby_radius=Tunable(description='\n                    The radius of a circle constraint that forces the sim to\n                    route-near the line-head or the last sim in line before actually entering the line.\n                    ', tunable_type=float, default=4), autonomous_waiting_line_prefence_curve=OptionalTunable(description='\n                    Tune how autonomy scores interactions with waiting lines.\n                    ', tunable=TunableWeightedUtilityCurveAndWeight(description='\n                        A curve that maps the number of sims in a waiting line\n                        for this interaction to an autonomy score multiplier\n                        for this interaction.\n                        ')), line_origin_override=OptionalTunable(description='\n                    If enabled the origin of the line will be built around the \n                    subroot specified instead of the root of the object.\n                    ', tunable=Tunable(description='\n                        Integer value of the subroot index.\n                        ', tunable_type=int, default=0), enabled_name='specify_subroot', disabled_name='use_object_root'), allow_line_on_same_target=Tunable(description='\n                    If checked the interaction will consider using the same\n                    target to go in line again.  This is for cases like the \n                    slippy slide where the sim will queue up again after \n                    using the object.\n                    ', tunable_type=bool, default=False)), tuning_group=GroupNames.SPECIAL_CASES), 'maximum_time_to_wait_for_other_sims': TunableSimMinute(description='\n            The number of Sim minutes to wait for other Sims in a multi-Sim\n            interaction before giving up and canceling the interaction.\n            ', default=8, tuning_group=GroupNames.SPECIAL_CASES), '_transition_constraints': OptionalTunable(description='\n            If enabled, constraints that will be used for generating the\n            transition to this interaction.  I.e. if you want a sim drinking coffee\n            to drink the coffee wherever the coffee happens to be, you would\n            put in a circle constraint with the object being the constraint actor.\n            If a player later decides to drink someplace else, (or later autonomy requires\n            moving elsewhere) the sim would still be able to do so while continuing\n            to drink.\n            \n            This creates an entry in a constraint set for each\n            target object/list of constraints\n            \n            This is primarily intended as a performance optimization.\n            ', tunable=TunableMapping(description='\n                A mapping of participants to constraints that must be \n                fulfilled in order to interact with this object.\n                ', key_type=TunableEnumEntry(description='\n                        The participant tuned here will have this constraint \n                        applied to them\n                        ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), value_type=TunableList(description='\n                    List of constraint data.\n                    ', tunable=TunableTuple(autonomous_only=Tunable(description="\n                            If checked these constraints will\n                            only be applied if the interaction isn't user\n                            directed.\n                            ", tunable_type=bool, default=False), test_constraint=OptionalTunable(description='\n                            If enabled, specifies a posture constraint that the standard\n                            constraint must be compatible with for these constraints\n                            to be applied.  i.e. if you only want the constraints\n                            to be applied to elements of the normal constraint set\n                            that are sitting, you would specify a sitting constraint here.\n                            ', tunable=PostureConstraintFactory.TunableFactory()), constraint_infos=TunableList(description='\n                            Specifies the constraints and target of the constraint to apply.\n                            ', tunable=TunableTuple(constraints=TunableList(tunable=TunableGeometricConstraintVariant(description='\n                                        A constraint that must be fulfilled in order to interact\n                                        with this object.\n                                        '), minlength=1), constraint_target=TunableVariant(description='\n                                    The object used to generate constraints relative to.\n                                    ', participant_based=TunableTuple(participant=TunableEnumEntry(description='\n                                            The participant used to generate _constraints relative to.\n                                            If the object is in inventory, the containing\n                                            object(s) will be used. (all potential objects if\n                                            inventory is shared)\n                                            ', tunable_type=ParticipantType, default=ParticipantType.Object), locked_args={'is_participant': True}), tag_based=TunableTuple(tags=TunableSet(description='\n                                            The tag for objects used to generate _constraints relative to.\n                                            ', tunable=TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), pack_safe=True), minlength=1), locked_args={'is_participant': False}), default='participant_based')))))), tuning_group=GroupNames.CORE), 'super_affordance_compatibility': TunableAffordanceFilterSnippet(description="\n                The filter of SuperInteractions that will be allowed to run at\n                the same time as this interaction, if possible. By default,\n                include all interactions which means compatibility will be\n                determined by posture requirements. When needed, add specific\n                interactions to the blacklist when they don't make sense to\n                multitask with this or the gameplay is not desired. When\n                creating an interaction that should generally not multitask,\n                like motive failure, switch variant to exclude_all.\n                \n                Note: Some interactions will not be exempted from exclude all.\n                This is because those interactions are specifically tuned to\n                'ignore exclude all compatibility'. If you would like to exclude\n                one of those interactions, it must be explicitly added to the\n                exception items list under exclude all or the blacklist under\n                allow all.\n                ", tuning_group=GroupNames.AVAILABILITY), 'ignore_exclude_all_compatibility': Tunable(description='\n            If checked, this affordance will not be excluded by compatibility if\n            it is not on the exclude list. WARNING. Please consult a GPE before\n            checking this.\n            ', tunable_type=bool, default=False), 'super_affordance_klobberers': OptionalTunable(description=" \n                The filter of SuperInteractions that this interaction can\n                clobber even if they are still guaranteed. Use this for\n                interactions where we commonly want to transition to another\n                interaction without waiting, for example bed_BeIntimate needs\n                to cancel sim_chat to run, but we don't want to wait for\n                sim_chat to go inertial. Remember that this should generally\n                default to exclude_all and you want to call out the\n                interactions that can be clobbered in the whitelist of\n                exclude_all; interactions that pass the filter will be\n                clobbered.\n                ", tunable=TunableAffordanceFilterSnippet(), tuning_group=GroupNames.AVAILABILITY), '_super_affordance_can_share_target': Tunable(bool, False, description='\n                By default, SuperInteractions with the same target are\n                considered incompatible. Check this to enable compatibility\n                with other SIs that target the same object, such as for Tend\n                Bar and Make Drink.', tuning_group=GroupNames.AVAILABILITY), '_preserve_held_props': TunableTuple(description='\n            Define how props are preserved for this interaction. Normally, props\n            from one SI are hidden whenever mixers from another SI are run.\n            Also, props are hidden whenever a Sim routes.\n            \n            Use this tuning to override this behavior such that props are never\n            hidden in either or both of those cases.\n            \n            NOTE: Double check with your animator that this is correct. This is\n            normally not required in regular circumstances.\n            ', preserve_during_other_si=Tunable(description='\n                If checked, props held as part of this SI are not hidden when a\n                mixer from a different SI runs.\n                ', tunable_type=bool, default=False), preserve_during_route=Tunable(description='\n                If checked, props held as part of this SI are not hidden when\n                the Sim routes.\n                ', tunable_type=bool, default=False), tuning_group=GroupNames.ANIMATION), 'animation_stat': OptionalTunable(description='\n                If enabled, specify a statistic to drive the animation content\n                for this interaction.\n                ', tunable=TunableTuple(description='\n                    Which stat to use and whether or not to get the stat level\n                    from the actor or the target.\n                    ', stat=TunableTestedVariant(description='\n                        Specify the single stat to use, or a suite of tests\n                        to decide which stat to drive the animation content.\n                        ', tunable_type=TunableReference(description="\n                            The statistic used to drive the animation content for this\n                            interaction. The stat defines tiers that the animators use\n                            to determine which specific clips to play within an ASM\n                            state. Most often, this stat is a skill.\n                        \n                            e.g. Play Violin interaction This interaction would\n                            probably tune the Violin skill as its animation state,\n                            since animators would want to play more failure clips as\n                            well as not play high skill clips if the Sim is on the\n                            lower end of the skill.\n                         \n                            To control what the exact ranges are, use the\n                            'stat_asm_param' field on a statistic's instance tuning.\n                            ", manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), is_noncallable_type=True), use_actor_skill=Tunable(description='\n                        If this is checked then the actor in the interaction\n                        will be used when getting the skill for the asm. If\n                        this is not checked and the target is a Sim then the\n                        targets skill will be used. If this is checked and\n                        the target is not a Sim then no skill will be used.\n                        ', tunable_type=bool, default=True)), tuning_group=GroupNames.ANIMATION), '_provided_posture_type': TunableReference(description="\n                Posture tuning must be hooked up via an interaction that\n                provides that posture. Setting this tunable on an SI will cause\n                it to provide the specified posture and will create the\n                appropriate nodes in the posture graph.\n                \n                IMPORTANT: Only one interaction can provide a given posture\n                type on a single object, otherwise there will be problems with\n                the graph! Supported Posture Type Filter is for removing\n                supported entries from that posture's manifest and is seldom\n                used.\n                ", manager=services.get_instance_manager(sims4.resources.Types.POSTURE), category='asm', tuning_group=GroupNames.POSTURE, allow_none=True), '_provided_posture_type_species': TunableEnumEntry(description='\n                Species this generic posture provided is associated with. You need\n                a generic posture provider per species.\n                ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,), tuning_group=GroupNames.POSTURE), 'supported_posture_type_filter': TunableList(TunableTuple(description='\n                    A list of filters to apply to the postures supported by \n                    this affordance.\n                    ', participant_type=TunableEnumEntry(description='\n                        The participant to which to apply this filter.\n                        ', tunable_type=ParticipantType, default=ParticipantType.Actor), posture_type=TunableReference(description='\n                        The posture being filtered.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.POSTURE)), force_carry_state=TunableList(description='\n                        A carry state to force on the supported postures.\n                        The list must either be empty or have exactly three\n                        elements corresponding to carry right, left, and\n                        both.\n                        ', tunable=Tunable(bool, True), maxlength=3)), tuning_group=GroupNames.POSTURE), 'posture_target_preference': OptionalTunable(TunableMapping(description='\n                    A tunable mapping of posture tags to a goal score bonus in\n                    meters.  This is used to make some objects more attractive\n                    than others for the purposes of posture preference scoring.\n                    That means that higher numbers are good; the Sim will go x\n                    meters out of their way to use these objects, where x is\n                    the amount tuned.\n                    \n                    For example, if one object has a score of 3 and another\n                    object has a score of 0, the object that scores 0 will need\n                    to be more than 3 meters closer than the object that scores\n                    3 for the Sim to choose it.\n                    \n                    Example: Let\'s say you want to make couches more desirable\n                    for watching TV.  To do this, you would create a new tag in\n                    PostureTransitionTargetPreferenceTag (found in\n                    Tuning->postures) called "ComfortableSeating".  Then you\n                    would tag all appropriate objects with that tag by adding\n                    it to PosturePreferenceTagList on the object.  Next, you\n                    would come in here and add a new item with a key of that\n                    tag and a value of 10 or so, which is about the size of the\n                    constraint to watch TV. Thus they will tend to use couches\n                    in the TV cone at the expense of other factors. One example\n                    downside of this is they will be less inclined to consider\n                    how centered they are in the TV cone and what direction the\n                    sofa is facing.\n                    ', key_type=TunableEnumEntry(PostureTransitionTargetPreferenceTag, PostureTransitionTargetPreferenceTag.INVALID), value_type=Tunable(float, 0)), tuning_group=GroupNames.POSTURE), 'posture_surface_slotted_object_preference': OptionalTunable(description='\n            When enabled allows you to specify a bonus to using a particular\n            surface based on the presences of an object in a particular slot\n            of the surface.\n            ', tunable=TunableMapping(description="\n                A tunable mapping of SlotType to goal score bonus. SlotType is \n                the slot that must have at least one child attached to it in \n                order to get the goal score bonus. This is used to make\n                certain surfaces more appealing than others for the purposes of\n                posture preference scoring. This means that higher numbers are \n                good; the Sim will go x meters out of their way to use these\n                objects, where x is the amound tuned.\n                \n                For example, if one surface has a score of 3 and another surface\n                has a score of 0, the surface that scores 0 will need to be more\n                than 3 meters closer than the surface that scores 3 for the Sim\n                to choose that surface.\n                \n                Example: Let's say that a sim is going to eat something. When\n                they look for a surface to eat on you want a surface with a \n                placemat setting to be more desirable. To do this you would\n                create a new entry in this mapping of SlotType slot_placematDrawing\n                with a score of 20 or so. With this tuning, if there is a \n                surface within 20 meters or so that has a placemat parented to\n                the slot_placematDrawing slot the Sim will prefer to use that\n                surface instead of the closest, most convenient, surface.\n                ", key_type=TunableReference(description='\n                    This is a reference to the slot that must have at least\n                    one child in order for the bonus to be applied to the\n                    goal scoring.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE)), value_type=Tunable(description='\n                    This is the goal score bonus that is applied if the\n                    corresponding slot has at least one child parented to it.\n                    ', tunable_type=float, default=0)), tuning_group=GroupNames.POSTURE), 'sim_affinity_posture_scoring_data': OptionalTunable(description='\n                Tunable preferences for doing this interaction nearby other\n                Sims, for example eating together or watching TV on the same\n                sofa.', tunable=TunableSimAffinityPostureScoringData(), tuning_group=GroupNames.POSTURE), 'score_additional_sims_for_in_use': OptionalTunable(description='\n                Some interactions use the transition sequence to choose\n                which object to use for the posture target.\n                \n                When this happens, the initiating Sim will choose the posture\n                target and can check against the reservations that he/she can \n                make.  \n                \n                If it is a multi-Sim interaction that requires each Sim \n                to reserve a specific part, this can cause issues where\n                the target Sim may attempt to use a part that is already\n                occupied.\n                \n                Enable this only for special cases where we also want to do \n                scoring for other Sims in the interaction for additional\n                parts when the posture target is decided.\n                \n                For example, Hospital Exam bed uses an interaction to pick\n                which exam bed to admit a patient to, and uses the transition \n                sequence to pick the bed. When choosing the bed, we need\n                to ensure that we check if TargetSim can reserve the\n                Patient_Seated part in addition to the part that the doctor\n                will stand at.\n                ', tunable=TunableMapping(description='\n                    A mapping of participant to part we want to check\n                    for the ability for the participant to reserve.\n                    ', key_type=TunableEnumEntry(description='\n                        The Sim we want to check a reservation for.\n                        ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.TargetSim, invalid_enums=(ParticipantType.Invalid, ParticipantTypeSingleSim.Actor)), value_type=TunableReference(description='\n                        The part we want to check for Sim reservation.\n                        ', manager=services.get_instance_manager(Types.OBJECT_PART)), minlength=1), tuning_group=GroupNames.POSTURE), 'force_autonomy_on_inertia': Tunable(description='\n                Whether we should force a full autonomy ping when this\n                interaction enters the inertial phase.\n                ', tunable_type=bool, default=False, tuning_group=GroupNames.AUTONOMY), 'force_exit_on_inertia': Tunable(description='\n                This tuning field is deprecated. Use the EXIT_NATURALLY\n                conditional action on exit conditions to force Sims to exit an\n                interaction once a condition is reached.\n                ', tunable_type=bool, default=False, tuning_group=GroupNames.DEPRECATED), 'pre_add_autonomy_commodities': TunableList(description="\n                List, in order, of parameterized autonomy requests to run prior \n                to adding this interaction to the Sim's SI State.\n                ", tunable=TunableParameterizedAutonomy(), tuning_group=GroupNames.AUTONOMY), 'pre_run_autonomy_commodities': TunableList(description="\n                List, in order, of parameterized autonomy requests to run prior\n                to running this interaction but after it has been added to the\n                Sim's SI state.", tunable=TunableParameterizedAutonomy(), tuning_group=GroupNames.AUTONOMY), 'post_guaranteed_autonomy_commodities': TunableList(description='\n                List, on order, of parameterized autonomy requests to run when\n                this interaction goes inertial.\n                ', tunable=TunableParameterizedAutonomy(), tuning_group=GroupNames.AUTONOMY), 'post_run_autonomy_commodities': TunableTuple(description='\n                Grouping of requests and fallback behavior that can happen\n                after running this interaction.\n                ', requests=TunableList(description='\n                    List, in order, of parameterized autonomy requests to run\n                    after running this interaction.\n                    ', tunable=TunableParameterizedAutonomy()), fallback_notification=OptionalTunable(description='\n                    If set, this notification will be displayed if there is no \n                    parametrized autonomy request pushed at the end of this\n                    interaction.\n                    ', tunable=TunableUiDialogNotificationSnippet()), tuning_group=GroupNames.AUTONOMY), 'opportunity_cost_multiplier': Tunable(description='\n                This will be multiplied with the calculated opportunity cost of\n                an SI when determining the cost of leaving this SI.\n                ', tunable_type=float, default=1, tuning_group=GroupNames.AUTONOMY), 'ignore_autonomy_rules_if_user_directed': Tunable(description='\n                If enabled, the transition sequence will consider objects the\n                user picked even if Sims in the interaction have conflicting\n                autonomy rules. This only works on NPCs with invalid autonomy\n                rules that are apart of a user directed interaction.\n                ', tunable_type=bool, default=False, tuning_group=GroupNames.AUTONOMY), 'apply_autonomous_posture_change_cost': Tunable(description="\n                There are two places where a cost for changing postures is\n                applied. \n                \n                1) When there is a guaranteed SI in the sim's SI state, we test\n                out all interactions that require a posture change. \n                \n                2) Even when all interactions are inertial, we still apply a\n                penalty for changing postures.\n                \n                If this tunable is set to True, both of these conditions are\n                applied.  If it's False, neither condition is applied and the\n                Sim will effectively ignore the posture changes with regards to\n                autonomy.  Note that the posture system will still score\n                normally.\n                ", tunable_type=bool, default=True, tuning_group=GroupNames.AUTONOMY), 'attention_cost': Tunable(description="\n                The attention cost of this interaction.  This models the fact\n                that humans are notoriously bad at multi-tasking.  For example,\n                if you are really hungry but socially satisfied, then talking\n                while eating is not necessarily the correct choice.\n                \n                More specifically, the total attention cost of all SI's are\n                summed up.  This is used as the X value for the attention\n                utility curve and a normalized value is returned.  This value\n                is multiplied to the autonomy score to get the final score.\n                When considering a new action, the Sim will look at the score\n                for their current state and subtract the target score.  If this\n                value is less than or equal to 0, the choice will be discarded.\n                ", tunable_type=float, default=1, tuning_group=GroupNames.AUTONOMY), 'duplicate_affordance_group': TunableEnumEntry(description='\n                Autonomy will only consider a limited number of affordances\n                that share this tag.  Each autonomy loop, it will gather all of\n                those aops, then score a random set of them (this number is\n                tuned in autonomy.autonomy_modes.NUMBER_OF_DUPLICATE_AFFORDANCE\n                _TAGS_TO_SCORE).\n                \n                All affordances that are tagged with INVALID will be scored.  \n                ', tunable_type=Tag, default=Tag.INVALID, tuning_group=GroupNames.AUTONOMY), 'autonomy_can_overwrite_similar_affordance': Tunable(description="\n                If True, autonomy will consider this affordance even if it's\n                already running.\n                ", tunable_type=bool, default=False, needs_tuning=True, tuning_group=GroupNames.AUTONOMY), 'subaction_selection_weight': Tunable(description='\n                The weight for selecting subactions from this super affordance.\n                A higher weight means the Sim will tend to run mixers provided\n                by this SI more often.\n                ', tunable_type=float, default=1, tuning_group=GroupNames.AUTONOMY), 'scoring_priority': TunableEnumEntry(description='\n                The priority bucket that this interaction will be scored in.\n                For example, if you have three interactions that all advertise\n                to the same commodity but want to guarantee that one is ALWAYS\n                chosen over the others, you can tune this value to HIGH.\n                Likewise, if you want to guarantee that one or more\n                interactions are only chosen if nothing else is available, set\n                this to LOW.\n                \n                It\'s important to note two things:\n\n                1) Autonomy is commodity-based.  That means it will always\n                choose a valid SI from a higher scoring commodity rather than a\n                lower scoring commodity.  This tunable is only used for\n                bucketing SI\'s within a single commodity loop.  That means it\'s\n                possible for a LOW priority SI to be chosen over a HIGH\n                priority SI.  This will happen when the LOW priority SI\'s\n                commodity out scores the other SI\'s commodity.\n                \n                2) Under the covers, this is just a sort.  There is not special\n                meaning for these values; each one just maps to an integer\n                which is used to sort the list of scored SI\'s into buckets.  We\n                choose an SI from the highest priority bucket.\n                       \n                The classic example of this tech is autonomous eating.  A Sim\n                should always choose to eat food that is already prepared\n                rather than make new food.  Furthermore, a sim should always\n                choose to resume cooking food that he started rather than eat\n                food sitting out. This is accomplished by setting the resume\n                interactions to HIGH priority and the "make new food"\n                interactions to LOW priority.  Eating existing food, getting\n                food from the inventory, grabbing a plate, etc. can all remain\n                NORMAL.\n                ', tunable_type=autonomy.autonomy_interaction_priority.AutonomyInteractionPriority, default=autonomy.autonomy_interaction_priority.AutonomyInteractionPriority.INVALID, needs_tuning=True, tuning_group=GroupNames.AUTONOMY), 'basic_content': TunableBasicContentSet(description='\n                The main animation and periodic stat changes for the\n                interaction.\n                ', one_shot=True, flexible_length=True, default='flexible_length', tuning_group=GroupNames.CORE), 'relationship_scoring': Tunable(description=' \n                When True, factor the relationship and party size into the\n                autonomy scoring for this interaction.\n                ', tunable_type=bool, default=False, tuning_group=GroupNames.AUTONOMY), '_party_size_weight_tuning': TunableList(description='\n                A list of Vector2 points that define the utility curve.\n                ', tunable=TunableVector2(sims4.math.Vector2(0, 0), description='Point on a Curve'), tuning_group=GroupNames.AUTONOMY), 'joinable': TunableList(description="\n                Joinable interactions for this super-interaction. A joinable\n                interaction X means that when Sim A is running X, Sim A \n                clicking on Sim B yields 'Ask to Join: X', whereas if Sim B is \n                running X, Sim A clicking on Sim B yields 'Join: X'. If both \n                cases are true, both options are yielded. If neither case is \n                true, X is yielded.\n                ", tunable=TunableTuple(join_affordance=TunableVariant(description='\n                        You can tune join to use a specific affordance, or to\n                        search for an affordance which provides a tuned\n                        commodity.\n                        ', affordance=TunableTuple(locked_args={'is_affordance': True}, value=OptionalTunable(description='\n                                The affordance that is pushed on the joining\n                                sim.\n                                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), disabled_name='this', enabled_name='custom')), commodity_search=TunableTuple(locked_args={'is_affordance': False}, value=TunableTuple(commodity=TunableReference(description='\n                                    Commodity searched for when finding a\n                                    potential join affordance.\n                                    ', manager=services.get_instance_manager(sims4.resources.Types.STATIC_COMMODITY)), radius=Tunable(description='\n                                    Max radial distance an object which\n                                    satisfies the tuned commodity can be from\n                                    the sim being joined.\n                                    ', tunable_type=int, default=5))), default='affordance'), join_target=TunableEnumEntry(description='\n                         This is the participant in the interaction being\n                         joined that should be target of new join\n                         interaction.\n                         ', tunable_type=ParticipantType, default=ParticipantType.Object), join_available=OptionalTunable(TunableTuple(description='\n                             Whether or not Join is available.\n                             ', loc_custom_join_name=OptionalTunable(TunableLocalizedStringFactory(description='\n                                     Use a specified string for the Join\n                                     interaction instead of the standard join\n                                     text.\n                                     ')))), invite_available=OptionalTunable(TunableTuple(description='\n                            Whether or not Ask to Join is available.', loc_custom_invite_name=OptionalTunable(TunableLocalizedStringFactory(description='\n                                    Use a specified string for the Invite\n                                    interaction instead of the standard invite\n                                    text.\n                                    ')))), link_joinable=Tunable(description="\n                        If true, the joining Sim's interaction will be\n                        cancelled if the joined Sim cancels or exits their\n                        interaction.\n                        ", tunable_type=bool, default=False)), tuning_group=GroupNames.STATE), 'rallyable': TunableList(description='\n                Interactions in this list will be generated in the Pie Menu\n                when the Sim is in a Party with other Sims. All Sims will have\n                an interaction pushed in order to keep the Party together.\n                ', tunable=TunableTuple(tag=TunableEnumEntry(description='\n                        An identifying tag that determines how consecutive\n                        rallyable interactions are grouped and handled.\n                        ', tunable_type=RallyableTag, default=None), sources=TunableEnumSet(description='\n                        A list of different rally sources that we want to offer\n                        this rally from.\n                        ', enum_type=RallySource, enum_default=RallySource.ENSEMBLE, default_enum_list=frozenset((RallySource.ENSEMBLE,))), pie_menu_icon=OptionalTunable(description='\n                        If enabled then we will use this pie menu icon on the\n                        interaction.\n                        ', tunable=TunableIconVariant(description='\n                            The icon to display in the pie menu.\n                            ', icon_pack_safe=True)), skip_interaction_test=Tunable(description='\n                        If checked then we will skip testing the Sims we will\n                        rally, with the tests of this interaction.\n                        ', tunable_type=bool, default=False), behavior=TunableVariant(description="\n                        Select the behavior this interaction will have with\n                        respect to members of the Sim's Party.\n                        ", push_affordance=TunableTuple(description='\n                            Bring the Party along and push the specified \n                            interaction on all members.\n                            ', loc_display_name=TunableLocalizedStringFactory(default=3390898100), affordance_target=OptionalTunable(description='\n                                The target of the pushed affordance relative to\n                                original interaction. so actor would be sim\n                                that triggered the rally. Use None for\n                                affordances like sit-smart.\n                                ', tunable=TunableEnumEntry(ParticipantType, ParticipantType.Object), enabled_by_default=True, disabled_name='none', enabled_name='participant_type'), affordance=TunableReference(description='\n                                The affordance to be pushed on Party members\n                                other than the initiating Sim. If no affordance\n                                is specified, push this affordance.\n                                ', manager=services.affordance_manager(), allow_none=True)), solve_static_commodity=TunableTuple(description='\n                            Bring the Party along and try to solve for the \n                            specified static commodity for all members.\n                            ', loc_display_name=TunableLocalizedStringFactory(default=180956154), static_commodity=TunableReference(description='\n                                The static commodity to be solved for all Party \n                                members other than the initiating Sim.\n                                ', manager=services.static_commodity_manager())), default='push_affordance'), push_social=TunableReference(description='\n                        When rallied Sims finish their transition they will\n                        push this affordance if they are no longer in a social\n                        group. e.g. If you run GoHereTogether while your Sims\n                        are in sit_intimate, sit_intimate will cancel, so we\n                        want to put them in chat at the end.\n                        ', manager=services.affordance_manager(), allow_none=True), rally_allow_forward=Tunable(description='\n                        If checked then we will skip testing the Sims we will\n                        rally, with the tests of this interaction.\n                        ', tunable_type=bool, default=False)), tuning_group=GroupNames.SPECIAL_CASES), 'only_available_as_rally': Tunable(description='\n                If checked then this interaction will only be available in its\n                rallyable form.\n                ', tunable_type=bool, default=False, tuning_group=GroupNames.SPECIAL_CASES), 'autonomy_preference': OptionalTunable(description='\n                Autonomy Preference related tuning options for this super\n                interaction. You can make a sim always use the same object, or\n                use the tuned preference score for certain SIs.\n                ', tunable=TunableVariant(use_preference=TunableTuple(preference=TunableAutonomyPreference(is_scoring=False)), scoring_preference=TunableTuple(preference=TunableAutonomyPreference(is_scoring=True), autonomy_score=Tunable(description='\n                            The amount to multiply the autonomous aop score by\n                            when the Sim prefers this object.\n                            ', tunable_type=float, default=1)), default='use_preference'), tuning_group=GroupNames.AUTONOMY), 'disable_autonomous_multitasking_if_user_directed': Tunable(description="\n                If this is checked, if this interaction is user directed and\n                guaranteed, sim will not consider running full autonomy and sim\n                cannot be a target of an full autonomy ping.\n                \n                For Example, if sim started a user directed painting, but don't\n                want sim to be interrupted by a social have this checked.\n                ", tunable_type=bool, default=False, tuning_group=GroupNames.AUTONOMY), 'use_best_scoring_aop': Tunable(description="\n                If checked, autonomy will always use the best scoring aop when\n                there are similar aops. For example, checking this on\n                view_painting will cause only the best scoring painting to be\n                considered.  If you uncheck this for painting, autonomy will\n                consider all paintings, but will use the best scoring painting\n                when scoring against other aops. In other words, if you uncheck\n                this for view_painting and have 10,000 paintings on the lot,\n                the Sim will consider those paintings, but it won't skew the\n                probability.\n                ", tunable_type=bool, default=True, needs_tuning=True, tuning_group=GroupNames.AUTONOMY), 'outfit_change': TunableTuple(description='\n                A structure of outfit change tunables.\n                ', on_route_change=InteractionOnRouteOutfitChange(description='\n                    An outfit change to execute on the first mobile node \n                    of the transition to this interaction.\n                    '), posture_outfit_change_overrides=OptionalTunable(TunableMapping(description='\n                        A mapping of postures to outfit change entry and exit\n                        reason overrides.\n                        ', key_type=TunableReference(description="\n                            If the Sim encounters this posture during this\n                            interaction's transition sequence, the posture's\n                            outfit change reasons will be the ones specified\n                            here.\n                            ", manager=services.get_instance_manager(sims4.resources.Types.POSTURE)), value_type=TunableOutfitChange(description='\n                            Define what outfits the Sim is supposed to wear\n                            when entering or exiting this posture.\n                            '))), tuning_group=GroupNames.CLOTHING_CHANGE), 'outfit_priority': OptionalTunable(description='\n                Enable an outfit change to the sims default outfit during this\n                interaction.\n                ', tunable=TunableTuple(outfit_change_reason=TunableEnumEntry(description='\n                        Outfit Change Reason that is given a default priority.\n                        ', tunable_type=OutfitChangeReason, default=OutfitChangeReason.Invalid), priority=TunableEnumEntry(description="\n                        Priority Level of this Reason for selecting a sim's\n                        default outfit.\n                        ", tunable_type=DefaultOutfitPriority, default=DefaultOutfitPriority.NoPriority)), tuning_group=GroupNames.CLOTHING_CHANGE), 'object_reservation_tests': tests.TunableTestSet(description='\n                Set of Tests that must be passed for a Sim to use an adjacent\n                part of an object while this SI is being performed.\n                ', tuning_group=GroupNames.AVAILABILITY), 'cancel_replacement_affordances': TunableMapping(key_type=TunableEnumEntry(description='\n                    What posture track the specified cancel replacement\n                    affordance will run for.\n                    ', tunable_type=postures.PostureTrackGroup, default=postures.PostureTrackGroup.BODY), value_type=TunableTuple(affordance=TunableReference(description='\n                        The affordance to push instead of the default\n                        affordance when this interaction is canceled. The\n                        replacement interaction must be able to target the same\n                        target of this interaction, and is only applied when\n                        the interaction is a posture source interaction.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), target=OptionalTunable(TunableEnumEntry(description="\n                            The target of the cancel replacement affordance. If\n                            unspecified, the interaction's target will be used.\n                            ", tunable_type=ParticipantType, default=ParticipantType.Object)), always_run=Tunable(description='\n                        If checked, then this cancel replacement affordance is\n                        always going to run after this interaction cancels. In\n                        general, we want this to be unchecked because we do not\n                        want to run a cancel affordance if the next interaction\n                        in the queue can use the posture we are in. However,\n                        there are cases where we want to ensure that a posture\n                        is fully exited before re-entering an SI requiring that\n                        same postures, e.g. exploring space in the Rocket Ship\n                        fully exits the Rocket Ship posture if another Explore\n                        interaction is queued.\n                        ', tunable_type=bool, default=False)), tuning_group=GroupNames.POSTURE), 'privacy': OptionalTunable(description='\n                If enabled, this interaction requires privacy to run and will\n                create a privacy footprint before executing.\n                ', tunable=TunableTuple(description='\n                    Privacy_snippet to run if subject satisfied the specified\n                    tests.\n                    ', tests=tests.TunableTestSet(), privacy_snippet=TunablePrivacySnippet(), animate_shoo=Tunable(description="\n                        If checked, Sims shooing away others from this privacy\n                        instances will play the shoo animation. If unchecked,\n                        they will just idle while Sims vacate the area.\n                        \n                        Disabling this option should be used in cases where we\n                        have no valid shoo animation to play in the postures\n                        leading up to the privacy interaction. For example, the\n                        steamroom goes from sitIntimate to woohoo, and we don't\n                        support multiSim shoo.\n                        ", tunable_type=bool, default=True)), tuning_group=GroupNames.STATE), 'provided_affordances': TunableProvidedAffordances(description='\n            Affordances provided by this Super Interaction. These affordances\n            are available when targeting or picking the Sim running this Super\n            Interaction.\n            \n            Target defaults to the Actor Sim running this interaction.\n            Carry Target defaults to None.\n            ', target_default=ParticipantType.Actor, carry_target_default=ParticipantType.Invalid, class_restrictions=('SuperInteraction',), tuning_group=GroupNames.STATE), 'canonical_animation': OptionalTunable(TunableAnimationReference(description='\n                    A reference to the canonical animation that represents all\n                    the valid constraints for this SI."), description="If\n                    enabled, the constraints for this SI will be the animation\n                    constraint generated from the supplied animation reference.\n                    ', callback=TunableAnimationReference.get_default_callback(InteractionAsmType.Canonical)), tuning_group=GroupNames.CORE), 'idle_animation': OptionalTunable(TunableAnimationReference(description='\n                    A reference to an animation to play when the Sim is blocked\n                    from running other work while running this interaction.\n                    When a Sim must idle to wait to run a real interaction, we\n                    randomly chose from the idle behavior of all running SIs,\n                    with the basic posture idle as a fallback.\n                    \n                    NOTE: This will cause issues if the idle animation tuned\n                    here is also anywhere in the basic content for this Super\n                    Interaction.\n                    '), tuning_group=GroupNames.ANIMATION), 'disable_transitions': Tunable(description='\n                If set, the constraints for this interaction will only be used\n                to determine compatibility with other interactions and will not\n                cause a posture transition sequence to be built for this\n                interaction. Caution: enable this only for interactions that\n                are meant to be proxies for other interactions which will get\n                pushed and then have their constraints solved for by the\n                transition sequence!\n                ', tunable_type=bool, default=False, tuning_group=GroupNames.POSTURE), 'ignore_group_socials': Tunable(description='\n                Whether Sims running this SuperInteraction should ignore group\n                socials. This lets them make more progress on this interaction\n                while socializing.\n                ', tunable_type=bool, default=True, needs_tuning=True, tuning_group=GroupNames.SPECIAL_CASES), 'disallow_as_mixer_target': Tunable(description='\n                If checked, a Sim cannot be the target of any mixer when this interaction\n                is in their SI State. It will cause any targeted mixer to be discarded\n                and not considered.\n                ', tunable_type=bool, default=False, needs_tuning=True, tuning_group=GroupNames.AUTONOMY), 'social_geometry_override': OptionalTunable(description="\n                The special geometry override for socialization in this super\n                interaction. This defines where the Sim's attention is focused\n                and informs the social positioning system where each Sim should\n                stand to look most natural when interacting. Ex: we override\n                the social geometry for a Sim who is bartending to be a wider\n                cone and be in front of the bar instead of embedded within the\n                bar. This encourages Sims to stand on the customer-side of the\n                bar to socialize with this Sim instead of coming around the\n                back.\n                ", tunable=TunableTuple(social_space=TunablePolygon(description='\n                        Social space for this super interaction\n                        '), focal_point=TunableVector3(description='\n                        Focal point when socializing in this super interaction,\n                        relative to Sim.\n                        ', default=sims4.math.Vector3.ZERO())), tuning_group=GroupNames.SPECIAL_CASES), 'relocate_main_group': Tunable(description="\n                The Sim's main social group should be relocated to the target\n                area of this interaction when it runs. This basically triggers\n                rallyable-style behavior without needing complex and sometimes\n                unwanted rallyable functionality. Ex: Card Table games do this\n                because they already have a system of SimPicker-driven\n                interaction pushing on the targets and trying to use rallyable\n                would fight with that.\n                ", tunable_type=bool, default=False, tuning_group=GroupNames.SPECIAL_CASES), 'acquire_targets_as_resource': Tunable(description='\n                If checked, all target Sims will be acquired as part of this\n                interaction.  If unchecked, this interaction can target Sims\n                without having to acquire them.\n                \n                Most interactions will want to acquire targeted Sims.  Not\n                acquiring target Sims will allow an interaction targeting other\n                Sims to run without having to wait for those Sims to become\n                available.\n                \n                Example Use Case: A Sim walks in on a privacy situation and\n                needs to play a reaction interaction with a thought bubble\n                displaying an image of the other Sim.  This interaction needs\n                to target that Sim in order to display their image, but also\n                needs to execute immediately and does not need to take control\n                of that Sim at all.\n                ', tunable_type=bool, default=True, tuning_group=GroupNames.SPECIAL_CASES), 'require_shared_body_target': Tunable(description="\n            If checked, all Sims in this interaction will be required to share\n            the same object as their posture's body target.\n            \n            If no Sim in the interaction has a body_target valid for the\n            others, we find a common matching body_target among all of their\n            possible destinations.\n            \n            If the target Sim already has a body_target that is valid for the\n            others, that body_target will be used.\n            ", tunable_type=bool, default=False, tuning_group=GroupNames.SPECIAL_CASES), 'collapsible': Tunable(description="\n                If checked any previous interaction of the same type will be\n                canceled from the queue.\n                \n                Example: Queue up 'Go Here' and queue up another 'Go Here' the\n                first go here will cancel.\n                ", tunable_type=bool, default=False, tuning_group=GroupNames.UI), '_saveable': OptionalTunable(description='\n                If enabled, this interaction will be saved with the sim and\n                started back up when the sim loads back up.\n                ', tunable=TunableTuple(affordance_to_save=OptionalTunable(description="\n                        By default, we save the affordance that was on the sim\n                        to this super interaction. To override this behavior,\n                        tune the affordance to save instead.\n                        \n                        EX: If you want the Cook Pancake interaction to be\n                            saved, you have to override the affordance to save\n                            to be 'resume cooking' and then tune the target to\n                            be the crafting object.\n                        ", tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions='SuperInteraction'), disabled_name='use_this_si', enabled_name='use_another_si'), target_to_save=TunableEnumEntry(description="\n                        We will get the participant from this\n                        interaction of this type and then save THAT object's id\n                        as the target of this interaction.\n                        ", tunable_type=ParticipantType, default=ParticipantType.Object)), tuning_group=GroupNames.PERSISTENCE), 'test_disallow_while_running': OptionalTunable(TunableTuple(description="\n                    If enabled, interactions set must not be in the sim's si\n                    state (running section of the queue) for this interaction\n                    to be available.\n                    ", test_self=Tunable(description='\n                        If checked, this affordance will not be available if it\n                        is in the si state.\n                        ', tunable_type=bool, default=False), affordances=TunableSet(description='\n                        List of affordance to check.  If sim has any of the\n                        affordances in the si state then this interaction will\n                        not be available.\n                        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True, class_restrictions=('SuperInteraction',)))), tuning_group=GroupNames.AVAILABILITY), 'can_shoo': Tunable(description='\n                Whether this interaction can be canceled by the "Shoo"\n                interaction.\n                ', tunable_type=bool, default=True, tuning_group=GroupNames.SPECIAL_CASES), 'walk_style': OptionalTunable(description="\n            If enabled, specify a walkstyle override to apply to the Sim during\n            the interaction's transition route and execution.\n            \n            e.g.:\n             If Sims were to run to everything they repair, the repari\n             interaction would tuned this to the Run walkstyle.\n            ", tunable=WalkStyleRequest.TunableFactory(), tuning_group=GroupNames.ANIMATION), 'route_events': TunableList(description='\n            If enabled, and the sim transitions to run this interaction, it\n            will play these route events on a route that occurs BEFORE this\n            interaction.\n            ', tunable=TunableTuple(description='\n                The route event and participant to play it.\n                ', route_event=RouteEvent.TunableReference(description='\n                    The route event we want to play after the interaction.\n                    ', pack_safe=True), participant=TunableEnumEntry(description='\n                    The participant we want to play the route event.\n                    ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor)), tuning_group=GroupNames.ANIMATION), 'transition_asm_params': TunableList(description='\n                A list of param name, param value tuples that get passed to\n                ASMs when doing a posture transition, including routes. They\n                can influence posture state machines and clothing changes.\n                \n                NOTE: These can only be enum types in the ASM. If your params\n                are not working, check the type in the ASM and inform your\n                animation partner if they are not enums.\n                ', tunable=TunableTuple(param_name=Tunable(description='\n                        The name of the parameter to override in the transition\n                        ASM. This is typically used if a posture ASM needs\n                        different VFX to play based on some parameter than the\n                        SI can provide.\n                        ', tunable_type=str, default=None), param_value=Tunable(description='\n                        The value to set the provided parameter.\n                        ', tunable_type=str, default=None)), tuning_group=GroupNames.ANIMATION), 'transition_global_asm_params': TunableList(description="\n                These params function similarly to 'Transition Asm Params'\n                except that they are not limited to the asm of this interaction.\n                This tuning should be used in cases where a simultaneous or\n                continuation interaction needs to set a parameter on the asm of\n                a different interaction running on the same sim.\n                ", tunable=TunableTuple(param_name=Tunable(description='\n                        The name of the parameter to override in the transition\n                        ASM. This is typically used if a posture ASM needs\n                        different VFX to play based on some parameter than the\n                        SI can provide.\n                        ', tunable_type=str, default=None), param_value=Tunable(description='\n                        The value to set the provided parameter.\n                        ', tunable_type=str, default=None)), tuning_group=GroupNames.ANIMATION), '_carry_transfer_animation': OptionalTunable(TunableTuple(description='\n                    A reference to an animation to play when starting this\n                    Interaction and to stop/restart when this Interaction has a\n                    carryable target and is transferred to a different posture.\n                    Ex: opening and closing the book on the surface needs to be\n                    hooked up here rather than as part of basic content.\n                    ', begin=TunableAnimationReference(), end=OptionalTunable(description='\n                        If enabled, anytime the Sim changes posture while in\n                        this SI, they will play this animation before the\n                        transition.\n                        ', tunable=TunableAnimationReference())), tuning_group=GroupNames.POSTURE), 'carry_cancel_override_for_displaced_interactions': OptionalTunable(TunableReference(description='\n                    If specified, this affordance will be used in place of the\n                    default one for any interaction displaced by this one and\n                    forced to run a carry cancel aop.\n                    \n                    If the displaced interaction has a custom carry cancel aop\n                    tuned, it will ignore this override.e\n                    ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), tuning_group=GroupNames.POSTURE), '_animation_actor_map': TunableAnimationActorMapSnippet(description='\n                Mapping between animation actors and ParticipantTypes.\n                ', tuning_group=GroupNames.CORE), 'invite_in_after_interaction': Tunable(description='\n            Checking this box will automatically invite the target Sim (if\n            the target is a Sim) into your home as long as you are on your lot \n            and they are not.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.SOCIALS), 'generate_content_set_as_potential_aops': Tunable(description="\n            If checked, any mixer interactions generated by this SI's content\n            set will be propagated to the Pie Menu.\n            ", tunable_type=bool, default=False, tuning_group=GroupNames.UI), 'can_acquire_posture_ownership': Tunable(description="\n            If unchecked, this interaction is not valid to be an owner of\n            the Sim's body posture.\n            ", tunable_type=bool, default=True, tuning_group=GroupNames.POSTURE), 'allow_teleport_style_injection': Tunable(description='\n            If enabled, a teleport style injection could happen when preparing\n            this SuperInteraction, and take place before routing to the target\n            of this Interaction.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.ROUTING)}
    _supported_posture_types = None
    _content_sets_cls = ContentSet.EMPTY_LINKS
    _provided_posture_type_disallowed_ages = None

    @flexproperty
    def _content_sets(cls, inst):
        return cls._content_sets_cls

    _has_visible_content_sets = False
    _teleporting = False
    CARRY_POSTURE_REPLACEMENT_AFFORDANCE = TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), description='The replacement affordance for carry postures. Should only be changed with engineering support.')

    @classmethod
    def _tuning_loaded_callback(cls):
        if cls.basic_content.content_set is not None:
            cls._content_sets_cls = cls.basic_content.content_set()
        super()._tuning_loaded_callback()
        if cls.basic_content is not None and cls._content_sets.phase_tuning is not None and cls._content_sets.num_phases > 0:
            target_value = cls._content_sets.num_phases
            threshold = sims4.math.Threshold(target_value, operator.ge)

            def condition_factory(*args, **kwargs):
                condition = StatisticCondition(who=cls._content_sets.phase_tuning.target, stat=cls._content_sets.phase_tuning.turn_statistic, threshold=threshold, absolute=True, **kwargs)
                return condition

            cls.add_exit_condition([condition_factory])
        cls._has_visible_content_sets = any(affordance.visible for affordance in cls.all_affordances_gen())
        cls._group_size_weight = None
        if cls._party_size_weight_tuning:
            point_list = [(point.x, point.y) for point in cls._party_size_weight_tuning]
            cls._group_size_weight = sims4.math.WeightedUtilityCurve(point_list)
        cls._update_commodity_flags()
        if cls._provided_posture_type is not None:
            disallowed_ages = get_disallowed_ages(cls)
            cls._provided_posture_type_disallowed_ages = frozendict({cls._provided_posture_type_species: disallowed_ages})
        transition_asm_params = {}
        for param_dict in cls.transition_asm_params:
            transition_asm_params[param_dict.param_name] = param_dict.param_value
        if transition_asm_params:
            cls.transition_asm_params = transition_asm_params
        else:
            cls.transition_asm_params = None
        transition_global_asm_params = {}
        for param_dict in cls.transition_global_asm_params:
            transition_global_asm_params[param_dict.param_name] = param_dict.param_value
        if transition_global_asm_params:
            cls.transition_global_asm_params = transition_global_asm_params
        else:
            cls.transition_global_asm_params = None

    @classmethod
    def _verify_tuning_callback(cls):
        super()._verify_tuning_callback()
        self_constraints = Anywhere()
        if ParticipantType.Actor in cls._auto_constraints:
            self_constraints = list(cls._auto_constraints[ParticipantType.Actor])
        for affordance in cls.all_affordances_gen():
            if affordance.allow_user_directed and not affordance.display_name:
                logger.error('Interaction {} on {} does not have a valid display name.', affordance.__name__, cls.__name__)
            mixer_constraints = Anywhere()
            if ParticipantType.Actor in affordance._auto_constraints:
                mixer_constraints = create_constraint_set(list(affordance._auto_constraints[ParticipantType.Actor]))
            if affordance._auto_constraints is not None and cls.target_type == TargetType.ACTOR and cls.target_type != affordance.target_type:
                logger.error('SI: {} has target type {} \n ...but its Mixer:{} is targeting {}', cls, cls.target_type, affordance, affordance.target_type, owner='rmccord')
            constraint_errors = set()
            has_valid_intersection = False
            for constraint in self_constraints:
                intersection = constraint.intersect(mixer_constraints)
                if not intersection.valid:
                    constraint_errors.add('"\n                        A Mixer Interaction is more restrictive than the Super Interaction it\'s attached to.\n                        \tMixer: {}\n                        \tSuper: {}\n                        \tMixer Constraint: {}\n                        \tSuper Constraints: {}\n\t\t\n                        '.format(affordance.__name__, cls.__name__, mixer_constraints, '\n\t\t'.join(str(c) for c in self_constraints)))
                else:
                    has_valid_intersection = True
            if affordance.optional or not has_valid_intersection:
                for constraint_error in constraint_errors:
                    logger.error(constraint_error)
        if cls._auto_constraints is not None and cls.score_additional_sims_for_in_use is not None and cls.basic_reserve_object is None:
            logger.error('Interaction {} has scoring for additional Sims enabled, but no basic reserve object is set.', cls.__name__, owner='jdimailig')

    @classmethod
    def has_slot_constraint(cls, *args, **kwargs):
        if cls.provided_posture_type is not None and not cls.provided_posture_type.mobile:
            return True
        return super().has_slot_constraint(*args, **kwargs)

    @classproperty
    def has_visible_content_sets(cls):
        return cls._has_visible_content_sets

    @classmethod
    def additional_mixers_to_cache(cls):
        basic_content = cls.basic_content
        if basic_content is not None and basic_content.content_set is not None and hasattr(basic_content.content_set, 'additional_mixers_to_cache'):
            return basic_content.content_set.additional_mixers_to_cache.random_int()
        return 0

    @classproperty
    def super_affordance_can_share_target(cls):
        return cls.provided_posture_type is not None or cls._super_affordance_can_share_target

    @classproperty
    def preserve_held_props_during_other_si(cls):
        return cls._preserve_held_props.preserve_during_other_si

    @classproperty
    def preserve_held_props_during_route(cls):
        return cls._preserve_held_props.preserve_during_route

    @classmethod
    def path(cls, target, context):
        pass

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        for aop in cls.get_rallyable_aops_gen(target, context, **kwargs):
            yield aop
        if not (cls._can_rally(context) and cls.only_available_as_rally):
            aop = cls.generate_aop(target, context, **kwargs)
            yield aop

    @classmethod
    def get_rallyable_aops_gen(cls, target, context, rally_constraint=None, **kwargs):
        if cls._can_rally(context):
            for entry in cls.rallyable:
                from interactions.base.rally_interaction import RallyInteraction
                rally_interaction = RallyInteraction.generate(cls, rally_tag=entry.tag, rally_level=0, rally_data=entry.behavior, rally_push_social=entry.push_social, rally_constraint=rally_constraint, rally_sources=entry.sources, rally_pie_menu_icon=entry.pie_menu_icon, rally_allow_forward=entry.rally_allow_forward)
                for aop in rally_interaction.potential_interactions(target, context, **kwargs):
                    initiating_sim = context.sim
                    rally_sims = initiating_sim.get_sims_for_rally(entry.sources)
                    if rally_sims:
                        if entry.skip_interaction_test:
                            yield aop
                        else:
                            for sim in rally_sims:
                                if initiating_sim is not sim:
                                    group_member_context = context.clone_for_sim(sim)
                                    result = ChoiceMenu.is_valid_aop(aop, group_member_context, user_pick_target=target)
                                    if not result:
                                        break
                            yield aop

    @classmethod
    def generate_aop(cls, target, context, **kwargs):
        return AffordanceObjectPair(cls, target, cls, None, **kwargs)

    @classmethod
    def potential_pie_menu_sub_interactions_gen(cls, target, context, scoring_gsi_handler=None, **aop_kwargs):
        if cls.generate_content_set_as_potential_aops:
            content_set = generate_content_set(context.sim, cls, None, context, potential_targets=(target,), scoring_gsi_handler=scoring_gsi_handler, include_failed_aops_with_tooltip=True, push_super_on_prepare=True, check_posture_compatibility=True, aop_kwargs=aop_kwargs)
            for (_, aop, test_result) in content_set:
                yield (aop, test_result)

    @classmethod
    def _can_rally(cls, context):
        if not cls.rallyable:
            return False
        if context is None:
            return False
        if context.sim is None:
            return False
        if context.source == InteractionContext.SOURCE_AUTONOMY:
            return False
        else:
            rally_sims = services.ensemble_service().get_ensemble_sims_for_rally(context.sim)
            main_group = context.sim.get_visible_group()
            if (main_group is None or main_group.is_solo) and len(rally_sims) <= 1:
                return False
        return True

    @classmethod
    def is_allowed_to_forward(cls, obj):
        if cls.is_rally_interaction and cls.rally_allow_forward:
            return True
        return super().is_allowed_to_forward(obj)

    @classproperty
    def provided_posture_type(cls):
        return cls._provided_posture_type

    @classmethod
    def get_provided_posture_change(cls, aop):
        if cls._provided_posture_type is not None:
            return PostureOperation.BodyTransition(cls._provided_posture_type, enumdict(Species, {cls._provided_posture_type_species: aop}), target=aop.target, disallowed_ages=cls._provided_posture_type_disallowed_ages)

    @classmethod
    def get_supported_posture_types(cls, posture_type_filter=None):
        supported_posture_types = {}
        for affordance in itertools.chain(cls.all_affordances_gen(), (cls,)):
            for (participant_type, supported_posture_manifest) in affordance._supported_postures.items():
                if posture_type_filter is not None:
                    supported_posture_manifest = posture_type_filter(participant_type, supported_posture_manifest)
                supported_posture_types_for_participant = postures.get_posture_types_supported_by_manifest(supported_posture_manifest)
                if participant_type not in supported_posture_types:
                    supported_posture_types[participant_type] = supported_posture_types_for_participant
                else:
                    supported_posture_types[participant_type] &= supported_posture_types_for_participant
        return supported_posture_types

    @flexmethod
    def supports_posture_state(cls, inst, posture_state, participant_type=ParticipantType.Actor, posture_type_filter=None, target=DEFAULT):
        inst_or_cls = inst if inst is not None else cls
        body = posture_state.body
        sim = posture_state.sim
        if not inst_or_cls.supports_posture_type(body.posture_type, participant_type=participant_type, posture_type_filter=posture_type_filter):
            return TestResult(False, 'Interaction does not support posture type: {}', body.posture_type)
        interaction_constraint = inst_or_cls.constraint_intersection(sim=sim, target=target, posture_state=None, participant_type=participant_type)
        if not interaction_constraint.valid:
            return TestResult(False, 'Interaction is incompatible with itself.')
        interaction_constraint = inst_or_cls.apply_posture_state_and_interaction_to_constraint(posture_state, interaction_constraint, participant_type=participant_type, invalid_expected=True)
        if not posture_state.compatible_with_pre_resolve(interaction_constraint):
            return TestResult(False, "Posture {}'s constraints are not compatible with {}'s constraints even before applying posture.", posture_state, inst)
        if not interaction_constraint.valid:
            return TestResult(False, "Interaction's constraint doesn't support body posture: {} and {}", interaction_constraint, body)
        return TestResult.TRUE

    @classmethod
    def supports_posture_type(cls, posture_type, *args, participant_type=ParticipantType.Actor, posture_type_filter=None, is_specific=True, **kwargs):
        if posture_type_filter is None:
            if cls._supported_posture_types is None:
                cls._cache_supported_posture_types()
            supported_posture_types = cls._supported_posture_types
        else:
            supported_posture_types = cls.get_supported_posture_types(posture_type_filter=posture_type_filter)
        supported_posture_types_for_participant = supported_posture_types.get(participant_type)
        if supported_posture_types_for_participant is not None:
            if posture_type in supported_posture_types_for_participant:
                return True
            else:
                return TestResult(False, '{} does not support posture type {}.', cls.__name__, posture_type.__name__)
        return True

    @classmethod
    def _cache_supported_posture_types(cls):
        supported_posture_type_filters = {}
        for supported_posture_type_filter in cls.supported_posture_type_filter:
            if supported_posture_type_filter.participant_type in supported_posture_type_filters:
                logger.error('{}: Multiple entries for {} specified in supported_posture_type_filter. This is invalid.', cls.__name__, supported_posture_type_filter.participant_type)
            else:
                supported_posture_type_filters[supported_posture_type_filter.participant_type] = (supported_posture_type_filter.posture_type, supported_posture_type_filter.force_carry_state)

        def _supported_posture_type_filter(participant_type, supported_posture_manifest):
            supported_posture_type_filter = supported_posture_type_filters.get(participant_type)
            if supported_posture_type_filter is not None:
                supported_posture_manifest = cls.filter_supported_postures(supported_posture_manifest, supported_posture_type_filter[0].name, supported_posture_type_filter[1] or None)
            return supported_posture_manifest

        cls._supported_posture_types = cls.get_supported_posture_types(posture_type_filter=_supported_posture_type_filter)

    @caches.cached
    def transition_constraint_intersection(self, sim, participant_type, final_constraint):
        if self._transition_constraints is None:
            return final_constraint
        for constraint_tuple in self._transition_constraints.get(participant_type, ()):
            if constraint_tuple.autonomous_only and self.is_user_directed:
                pass
            else:
                surface_constraint_dict = {}
                for constraint_info in constraint_tuple.constraint_infos:
                    constraints = constraint_info.constraints
                    constraint_target = constraint_info.constraint_target
                    constraint_target_set = set()
                    if constraint_target.is_participant:
                        for target_object in self.get_participants(participant_type=constraint_target.participant):
                            if target_object is not None:
                                if target_object.is_in_inventory():
                                    constraint_target_set.update(target_object.inventoryitem_component.get_root_owner())
                                else:
                                    constraint_target_set.add(target_object)
                    else:
                        constraint_target_set.update(services.object_manager().get_objects_matching_tags(constraint_target.tags, match_any=True))
                    for target in constraint_target_set:
                        while target.bb_parent is not None:
                            target = target.bb_parent
                        interim_constraint = Anywhere()
                        for constraint in constraints:
                            test_constraint = constraint.create_constraint(sim, target)
                            interim_constraint = test_constraint.intersect(interim_constraint)
                        if interim_constraint is not Anywhere():
                            surface = interim_constraint.routing_surface
                            if surface in surface_constraint_dict:
                                existing_constraint = surface_constraint_dict[surface]
                                new_geometry = existing_constraint.geometry.union(interim_constraint.geometry)
                                surface_constraint_dict[surface] = existing_constraint.generate_constraint_with_new_geometry(new_geometry)
                            else:
                                surface_constraint_dict[surface] = interim_constraint.generate_constraint_with_new_geometry(interim_constraint.geometry)
                constraint_set = create_constraint_set(surface_constraint_dict.values())
                if constraint_tuple.test_constraint is None:
                    final_constraint = final_constraint.intersect(constraint_set)
                else:
                    posture_test_constraint = constraint_tuple.test_constraint.create_constraint()
                    final_constraint = final_constraint.tested_intersect(constraint_set, posture_test_constraint)
        return final_constraint

    @classproperty
    def teleporting(cls):
        return cls._teleporting

    @flexmethod
    def content_set_mixer_interaction_groups(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        return inst_or_cls._content_sets.get_mixer_interaction_groups()

    @flexmethod
    def all_affordances_gen(cls, inst, context=None, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        for affordance in inst_or_cls._content_sets.all_affordances_gen(**kwargs):
            yield affordance
        if inst.target is not None:
            target_basic_content = inst.target.get_affordance_basic_content(inst)
            if target_basic_content is not None:
                target_content_set = target_basic_content.content_set
                if target_content_set is not None:
                    for affordance in target_content_set().all_affordances_gen(**kwargs):
                        yield affordance
        target_id = None
        sim = None
        if inst is not None and inst is not None:
            target = inst.target
            sim = inst.sim
            if target.is_sim:
                target_id = target.sim_id
        if context is not None:
            target_id = context.target_sim_id
            sim = context.sim
            if context.pick is not None:
                target = context.pick.target
                if target.is_sim:
                    target_id = target.sim_id
        class_to_check = inst_or_cls.affordance
        if target_id is None and sim is not None:
            if target_id is not None:
                for relbit in sim.relationship_tracker.get_all_bits(target_id):
                    yield from relbit.get_mixers(class_to_check)
            actor_mixers = set()
            actor_mixers |= sim.sim_info.get_actor_mixers(class_to_check)
            actor_mixers |= sim.commodity_tracker.get_cached_actor_mixers(class_to_check)
            actor_mixers |= sim.trait_tracker.get_cached_actor_mixers(class_to_check)
            yield from actor_mixers
        if target_id is not None:
            target_info = services.sim_info_manager().get(target_id)
            if target_info is not None:
                yield from target_info.get_provided_mixers_gen(class_to_check)
                yield from target_info.trait_tracker.get_cached_provided_mixers_gen(class_to_check)

    def get_outside_score_multiplier_override(self):
        pass

    @flexmethod
    def has_affordances(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls._content_sets.has_affordances():
            return True
        elif inst is not None and inst.target is not None:
            target_basic_content = inst.target.get_affordance_basic_content(inst)
            if target_basic_content is not None:
                target_content_set = target_basic_content.content_set
                if target_content_set is not None and target_content_set().has_affordances():
                    return True
        return False

    @classproperty
    def only_use_mixers_from_si(cls):
        if cls.staging:
            return cls.basic_content.content.only_use_mixers_from_SI
        return False

    @classmethod
    def contains_stat(cls, stat):
        if super().contains_stat(stat):
            return True
        for affordance in cls.all_affordances_gen():
            if affordance.contains_stat(stat):
                return True
        return False

    @classmethod
    def _test(cls, target, context, **interaction_parameters):
        if cls.test_disallow_while_running is None:
            return TestResult.TRUE
        test_self = cls.test_disallow_while_running.test_self
        cls_interaction_type = cls.get_interaction_type()
        for si in context.sim.si_state:
            si_affordance = si.get_interaction_type()
            if not (test_self and si_affordance.get_interaction_type() is cls_interaction_type):
                pass
            if 'interaction_starting' in interaction_parameters:
                is_starting = interaction_parameters['interaction_starting']
            else:
                is_starting = False
            if si.target is target and not is_starting:
                return TestResult(False, 'Currently running interaction')
            if si.target is not None and (si.target.is_part and si.target.part_owner is target) and not is_starting:
                return TestResult(False, 'Currently running interaction')
        return TestResult.TRUE

    @classmethod
    def _is_linked_to(cls, super_affordance):
        if cls.super_affordance_compatibility is not None and cls.super_affordance_compatibility(super_affordance, allow_ignore_exclude_all=True):
            return True
        return False

    @classmethod
    def consumes_object(cls):
        for affordance in cls.all_affordances_gen():
            if affordance.consumes_object():
                return True
        return False

    @flexmethod
    def is_linked_to(cls, inst, super_affordance):
        inst_or_cls = inst if inst is not None else cls
        if inst_or_cls.provided_posture_type is not None and (inst_or_cls.provided_posture_type.IS_BODY_POSTURE and super_affordance.provided_posture_type is not None) and super_affordance.provided_posture_type.IS_BODY_POSTURE:
            return False
        if inst_or_cls.provided_posture_type is not None and super_affordance.provided_posture_type is None:
            return cls._is_linked_to(super_affordance)
        if super_affordance.provided_posture_type is not None and inst_or_cls.provided_posture_type is None:
            return super_affordance._is_linked_to(cls)
        return cls._is_linked_to(super_affordance.affordance) and super_affordance._is_linked_to(cls)

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        if inst is not None and inst.is_finishing:
            return
        inst_or_cls = inst if inst is not None else cls
        found_constraint = False
        for constraint in super(SuperInteraction, inst_or_cls)._constraint_gen(sim, inst_or_cls.get_constraint_target(target), participant_type=participant_type):
            found_constraint = True
            yield constraint
        if inst is not None and inst.sim.posture.source_interaction is inst and not (inst.sim.posture.mobile or inst.sim.posture.is_universal):
            slot_constraint = inst.sim.posture.slot_constraint
            if slot_constraint is not None:
                yield slot_constraint
        for tuned_additional_constraint in target.additional_interaction_constraints:
            constraint = tuned_additional_constraint.constraint
            affordance_links = tuned_additional_constraint.affordance_links
            found_constraint = True
            if affordance_links is None or not affordance_links(cls) or constraint is not None:
                created_constraint = target.get_created_constraint(constraint)
                if created_constraint is not None:
                    yield created_constraint
        if not (target is not None and target.additional_interaction_constraints is not None and found_constraint):
            for affordance in inst_or_cls.all_affordances_gen():
                for constraint in affordance.constraint_gen(sim, inst_or_cls.get_constraint_target(target), participant_type=participant_type):
                    yield constraint

    @classproperty
    def involves_carry(cls):
        return cls._animation_actor_map.carry_target is not None

    @property
    def targeted_carryable(self):
        carry_target = self.carry_target
        if carry_target is None:
            carry_target = self.create_target
        return carry_target

    @property
    def combined_posture_preferences(self):
        if self.combinable_interactions and self.combinable_interactions != self.get_combinable_interactions_with_safe_carryables():
            return postures.transition_sequence.PosturePreferencesData(False, False, False, {})
        return self.posture_preferences

    @property
    def combined_posture_target_preference(self):
        if self.combinable_interactions and self.combinable_interactions != self.get_combinable_interactions_with_safe_carryables():
            return self.DEFAULT_POSTURE_TARGET_PREFERENCES
        return self.posture_target_preference

    def remove_self_from_combinable_interactions(self):
        if self.combinable_interactions:
            self.combinable_interactions.discard(self)
            if len(self.combinable_interactions) == 1:
                self.combinable_interactions.clear()

    def on_other_si_phase_change(self, si):
        if self.transition is None or self.transition.running:
            return
        if self.is_related_to(si):
            return
        if not self.transition.get_sims_with_invalid_paths():
            included_sis = self.transition.get_included_sis()
            if si not in included_sis:
                return
        if self.transition is not None:
            self.transition.reset_all_progress()

    def _generate_connectivity(self, ignore_all_other_sis=False):
        if self.transition is None or self.transition.ignore_all_other_sis != ignore_all_other_sis:
            self.transition = postures.transition_sequence.TransitionSequenceController(self, ignore_all_other_sis=ignore_all_other_sis)
        if self.transition.running:
            return
        was_locked = self.is_required_sims_locked()
        if not was_locked:
            self.refresh_and_lock_required_sims()
        self.transition.compute_transition_connectivity()
        if not was_locked:
            self.unlock_required_sims()

    def _generate_routes(self, timeline, ignore_all_other_sis=False):
        if self.transition is None or self.transition.ignore_all_other_sis != ignore_all_other_sis:
            self.transition = postures.transition_sequence.TransitionSequenceController(self, ignore_all_other_sis=ignore_all_other_sis)
        if self.transition.running:
            return
        was_locked = self.is_required_sims_locked()
        if not was_locked:
            self.refresh_and_lock_required_sims()
        yield from self.transition.run_transitions(timeline, progress_max=TransitionSequenceStage.ROUTES)
        if not was_locked:
            self.unlock_required_sims()

    def get_sims_with_invalid_paths(self):
        if self.is_cancel_aop:
            return set()
        if self.is_finishing or self._pipeline_progress >= PipelineProgress.RUNNING:
            return set()
        if self.transition is not None and self.transition.running:
            return set()
        self._generate_connectivity()
        if self.is_finishing:
            return set()
        incompatible_sims = self.transition.get_sims_with_invalid_paths()
        carry_target = self.carry_target
        if carry_target.is_sim:
            for si in carry_target.si_state.all_guaranteed_si_gen(self.priority, self.group_id):
                if self.super_affordance_klobberers is not None and self.super_affordance_klobberers(si.affordance):
                    pass
                else:
                    incompatible_sims.add(carry_target)
        return incompatible_sims

    def _estimate_distance_cache_key(self):
        required_sims = frozenset(self.required_sims())
        all_potentially_included_sis = frozenset((si, si.is_guaranteed) for sim in required_sims for si in sim.si_state if not si.is_finishing)
        return (self.constraint_intersection(posture_state=None).estimate_distance_cache_key(), self.super_affordance_compatibility, self.should_rally, self.sim, required_sims, all_potentially_included_sis)

    @caches.cached(key=_estimate_distance_cache_key)
    def estimate_distance(self):
        return self._estimate_distance(False)

    def estimate_distance_ignoring_other_sis(self):
        return self._estimate_distance(True)

    def estimate_final_path_distance(self, timeline, ignore_all_other_sis):
        with AutonomyAffordanceTimes.profile_section(AutonomyAffordanceTimes.AutonomyAffordanceTimesType.TRANSITION_SEQUENCE):
            yield from self._generate_routes(timeline, ignore_all_other_sis=ignore_all_other_sis)
        with AutonomyAffordanceTimes.profile_section(AutonomyAffordanceTimes.AutonomyAffordanceTimesType.DISTANCE_ESTIMATE):
            try:
                result = self.transition.estimate_distance_for_current_progress()
            finally:
                if ignore_all_other_sis:
                    self.transition = None
            return result

    def _estimate_distance(self, ignore_all_other_sis):
        with AutonomyAffordanceTimes.profile_section(AutonomyAffordanceTimes.AutonomyAffordanceTimesType.TRANSITION_SEQUENCE):
            self._generate_connectivity(ignore_all_other_sis=ignore_all_other_sis)
        with AutonomyAffordanceTimes.profile_section(AutonomyAffordanceTimes.AutonomyAffordanceTimesType.DISTANCE_ESTIMATE):
            try:
                result = self.transition.estimate_distance_for_current_progress()
            finally:
                if ignore_all_other_sis:
                    self.transition = None
            return result

    @classmethod
    def get_affordance_weight_from_group_size(cls, party_size):
        if cls._group_size_weight:
            return cls._group_size_weight.get(party_size)
        logger.error('Attempting to call get_affordance_weight_from_group_size() on affordance {} with no weight curve.'.format(cls), owner='rez')
        return 1

    def __init__(self, aop, context, *args, exit_functions=(), force_inertial=False, additional_post_run_autonomy_commodities=None, cancel_incompatible_with_posture_on_transition_shutdown=True, disable_saving=False, ignore_waiting_line_tuning=False, **kwargs):
        StageControllerElement.__init__(self, context.sim)
        Interaction.__init__(self, aop, context, *args, **kwargs)
        self._interactions = weakref.WeakSet()
        self._exit_functions = []
        for exit_fn in exit_functions:
            self.add_exit_function(exit_fn)
        self._availability_handles = []
        self._post_guaranteed_autonomy_element = None
        self._lifetime_state = LifetimeState.INITIAL
        self._force_inertial = force_inertial
        self._guaranteed_watcher_active = 0
        self._guaranteed_locks = set()
        self._pre_exit_behavior_done = False
        self._outfit_priority_id = None
        self._rejected_account_id_requests = []
        self._cancel_deferred = None
        self._has_pushed_cancel_aop = set()
        self.disable_cancel_by_posture_change = False
        self.additional_post_run_autonomy_commodities = additional_post_run_autonomy_commodities
        self._in_cancel = False
        self._transition = None
        self.owning_transition_sequences = set()
        self.combinable_interactions = WeakSet()
        self._carry_transfer_end_required = False
        self._cancel_incompatible_with_posture_on_transition_shutdown = cancel_incompatible_with_posture_on_transition_shutdown
        self.target_in_inventory_when_queued = False
        self._disable_saving = disable_saving
        self._ignore_waiting_line_tuning = ignore_waiting_line_tuning
        self._setup_animation_actors()
        self._num_nowhere_mixers_executed_in_perform = 0
        self._prepare_liabilities = None

    @property
    def saveable(self):
        return self._saveable is not None and not self._disable_saving

    @property
    def transition(self):
        return self._transition

    @transition.setter
    def transition(self, value):
        if value is self._transition:
            return
        old_transition = self._transition
        self._transition = value
        if old_transition is not None and old_transition.interaction is self:
            old_transition.end_transition()
            old_transition.shutdown()

    @property
    def cancel_incompatible_with_posture_on_transition_shutdown(self):
        return self._cancel_incompatible_with_posture_on_transition_shutdown

    @property
    def preferred_objects(self):
        return self.context.preferred_objects

    def add_preferred_object(self, *args, **kwargs):
        self.context.add_preferred_object(*args, **kwargs)

    def add_preferred_objects(self, *args, **kwargs):
        self.context.add_preferred_objects(*args, **kwargs)

    def add_exit_function(self, exit_fn):
        self._exit_functions.append(exit_fn)

    def __str__(self):
        try:
            is_guaranteed = self.is_guaranteed()
        except:
            is_guaranteed = False
        return '{4} running {0}:{2} on {1}{3}'.format(self.super_affordance.__name__, self.target, self.id, '  (guaranteed)' if is_guaranteed else '', self.sim)

    def __repr__(self):
        return '<SI {2} id:{0} sim:{1}>'.format(self.id, self.sim, self.super_affordance.__name__)

    def log_info(self, phase, msg=None):
        from sims.sim_log import log_interaction
        log_interaction(phase, self, msg=msg)

    def _setup_animation_actors(self):
        carry_participant = self._animation_actor_map.carry_target
        if carry_participant is not None and carry_participant != ParticipantType.CreatedObject:
            carry_target = self.get_participant(carry_participant)
            if carry_target is not None:
                if self.context.carry_target is None:
                    self.context.carry_target = carry_target
                elif carry_target != self.context.carry_target:
                    logger.error('Interaction {} is trying to overwrite its carry target {} to {}.', self, self.context.carry_target, carry_target, owner='tastle')
        elif self.context.carry_target is not None:
            self.context.carry_target = None
        target_participant = self._animation_actor_map.target_override
        if target_participant is not None and carry_participant != ParticipantType.CreatedObject:
            new_target = self.get_participant(target_participant)
            if new_target is not None and new_target != self.target:
                self.set_target(new_target)

    def map_create_target(self, created_obj):
        carry_participant = self._animation_actor_map.carry_target
        if carry_participant == ParticipantType.CreatedObject:
            self.context.carry_target = created_obj
        target_participant = self._animation_actor_map.target_override
        if target_participant == ParticipantType.CreatedObject:
            self.set_target(created_obj)
        self.interaction_parameters['created_target_id'] = created_obj.id

    def should_carry_create_target(self):
        carry_participant = self._animation_actor_map.carry_target
        return carry_participant == ParticipantType.CreatedObject

    @property
    def phase_index(self):
        if self._content_sets.phase_tuning is not None:
            participant = self.get_participant(self._content_sets.phase_tuning.target)
            tracker = participant.get_tracker(self._content_sets.phase_tuning.turn_statistic)
            return tracker.get_int_value(self._content_sets.phase_tuning.turn_statistic)

    def is_guaranteed(self) -> bool:
        if self._guaranteed_locks:
            return True
        if self.pipeline_progress < PipelineProgress.RUNNING:
            return True
        if self.force_inertial:
            return False
        if self.has_active_cancel_replacement:
            return False
        elif not self.satisfied:
            return True
        return False

    @property
    @contextmanager
    def guaranteed_watcher(self):
        was_guaranteed = self.is_guaranteed()
        try:
            yield None
        finally:
            is_guaranteed = self.is_guaranteed()
            if is_guaranteed != was_guaranteed and not self.is_finishing:
                if is_guaranteed:
                    self._on_inertial_to_guaranteed()
                else:
                    self._on_guaranteed_to_inertial()

    def get_potential_mixer_targets(self):
        if self.target is None:
            return ()
        return (self.target,)

    def _get_required_sims(self, *args, **kwargs):
        sims = set()
        required_types = ParticipantType.Actor
        if self.target_type & TargetType.TARGET:
            required_types |= ParticipantType.TargetSim
        if self.target_type & TargetType.GROUP:
            required_types |= ParticipantType.Listeners
            if not self.target_type & TargetType.TARGET:
                required_types |= ParticipantType.TargetSim
        for sim in self.get_participants(required_types):
            if not self.acquire_targets_as_resource:
                if self.get_participant_type(sim) == ParticipantType.Actor:
                    if sim.posture_state is None:
                        logger.error('Found a Sim with a None posture_state. Interaction: {}, Sim: {}', self, sim)
                    else:
                        sims.add(sim)
                        if sim.posture.multi_sim:
                            linked_sim = sim.posture.linked_sim
                            if linked_sim is not None:
                                sims.add(linked_sim)
            if sim.posture_state is None:
                logger.error('Found a Sim with a None posture_state. Interaction: {}, Sim: {}', self, sim)
            else:
                sims.add(sim)
                if sim.posture.multi_sim:
                    linked_sim = sim.posture.linked_sim
                    if linked_sim is not None:
                        sims.add(linked_sim)
        carry_target = self.carry_target
        if carry_target is not None and carry_target.is_sim:
            sims.add(carry_target)
        return sims

    def get_combinable_interactions_with_safe_carryables(self):
        if not self.combinable_interactions:
            return self.combinable_interactions
        combined_carry_targets = set()
        carry_target = self.targeted_carryable
        if carry_target is not None:
            combined_carry_targets.add(carry_target)
        valid_combinables = WeakSet()
        valid_combinables.add(self)
        for combinable in self.combinable_interactions:
            if combinable is self:
                pass
            else:
                combinable_carry = combinable.targeted_carryable
                if combinable_carry is not None and combinable_carry not in combined_carry_targets:
                    if isinstance(combinable_carry, Definition) or combinable_carry.is_sim:
                        pass
                    elif len(combined_carry_targets) > 0:
                        pass
                    else:
                        combined_carry_targets.add(combinable_carry)
                        valid_combinables.add(combinable)
                valid_combinables.add(combinable)
        return valid_combinables

    def get_idle_behavior(self):
        if self.idle_animation is None:
            return
        return self.idle_animation(self)

    def _pre_perform(self):
        self._setup_phase_tuning()
        if self.staging:
            with self.guaranteed_watcher:
                result = super()._pre_perform()
        else:
            result = super()._pre_perform()
        if self.is_user_directed:
            self.force_exit_on_inertia = True
        self._check_if_push_affordance_on_run()
        if self.sim.get_autonomy_state_setting() == autonomy.settings.AutonomyState.MEDIUM and self.source not in InteractionContext.TRANSITIONAL_SOURCES:
            self._update_autonomy_timer()
        self.add_exit_function(self.send_end_progress)
        return result

    def _check_if_push_affordance_on_run(self):
        if not self.staging:
            return
        push_affordance_on_run = self.basic_content.push_affordance_on_run
        if push_affordance_on_run is None:
            return
        push_affordance = push_affordance_on_run.affordance
        affordance_target = self.get_participant(push_affordance_on_run.target) if push_affordance_on_run.target is not None else None
        push_kwargs = {}
        if push_affordance.is_social:
            push_kwargs['social_group'] = self.social_group
        for actor in self.get_participants(push_affordance_on_run.actor):
            unpart_target = affordance_target
            if actor is self.sim:
                context = self.context.clone_for_concurrent_context()
            else:
                context = self.context.clone_for_sim(actor)
                if affordance_target.is_part:
                    unpart_target = affordance_target.part_owner
            if push_affordance_on_run.carry_target is not None:
                context.carry_target = self.get_participants(push_affordance_on_run.carry_target)
            else:
                context.carry_target = None
            for aop in push_affordance.potential_interactions(unpart_target, context, **push_kwargs):
                enqueue_result = aop.test_and_execute(context)
                if not enqueue_result:
                    pass
                else:
                    interaction_pushed = enqueue_result.interaction
                    if push_affordance_on_run.link_cancelling_to_affordance:
                        liability = CancelInteractionsOnExitLiability()
                        interaction_pushed.add_liability(CANCEL_INTERACTION_ON_EXIT_LIABILITY, liability)
                        liability.add_cancel_entry(actor, self)

    def _setup_phase_tuning(self):
        if self._content_sets.phase_tuning is not None and self._content_sets.num_phases > 0:
            participant = self.get_participant(self._content_sets.phase_tuning.target)
            tracker = participant.get_tracker(self._content_sets.phase_tuning.turn_statistic)
            tracker.set_value(self._content_sets.phase_tuning.turn_statistic, 0, add=True)

            def remove_stat_from_target():
                participant = self.get_participant(self._content_sets.phase_tuning.target)
                tracker = participant.get_tracker(self._content_sets.phase_tuning.turn_statistic)
                tracker.remove_statistic(self._content_sets.phase_tuning.turn_statistic)

            self.add_exit_function(remove_stat_from_target)

    def _do_perform_trigger_gen(self, timeline):
        next_stage = self.next_stage()
        result = yield from element_utils.run_child(timeline, next_stage)
        return result

    def _post_perform(self):
        if self.suspended:
            if self.staging:
                if gsi_handlers.interaction_archive_handlers.is_archive_enabled(self):
                    gsi_handlers.interaction_archive_handlers.archive_interaction(self.sim, self, 'Staged')
                services.get_event_manager().process_event(test_events.TestEvent.InteractionStaged, sim_info=self.sim.sim_info, interaction=self)
            return
        if not self.staging:
            self._update_autonomy_timer()
        self._lifetime_state = LifetimeState.PENDING_COMPLETE

    @property
    def visible_as_interaction(self):
        if self.started:
            return False
        return super().visible_as_interaction

    @property
    def interactions(self):
        return self._interactions

    @property
    def super_interaction(self):
        return self

    @classproperty
    def is_super(cls):
        return True

    def _set_pipeline_progress(self, value):
        with self.guaranteed_watcher:
            super()._set_pipeline_progress(value)

    def _set_satisfied(self, value):
        with self.guaranteed_watcher:
            super()._set_satisfied(value)

    @property
    def force_inertial(self):
        return self._force_inertial

    @force_inertial.setter
    def force_inertial(self, value):
        with self.guaranteed_watcher:
            self._force_inertial = value

    def lock_guaranteed(self):
        key = object()
        with self.guaranteed_watcher:
            self._guaranteed_locks.add(key)

        def unlock():
            with self.guaranteed_watcher:
                self._guaranteed_locks.remove(key)

        return unlock

    def queued_sub_interactions_gen(self):
        for interaction in self.sim.queue:
            if interaction.is_super or interaction.super_interaction is self:
                yield interaction

    def can_run_subinteraction(self, interaction_or_aop, context=None):
        context = context or interaction_or_aop.context
        if interaction_or_aop.super_interaction is not self:
            return False
        return self._finisher.can_run_subinteraction()

    @property
    def canceling_incurs_opportunity_cost(self):
        return True

    def _parameterized_autonomy_helper_gen(self, timeline, commodity_info_list, context_bucket, participant_type=ParticipantType.Actor, fallback_notification=None, push_on_success_or_fail=None, as_continuation=True):
        parameterized_requests = []
        for commodity_info in reversed(commodity_info_list):
            commodities = commodity_info.commodities
            static_commodities = commodity_info.static_commodities
            objects = []
            objects_to_ignore = []
            if self.target is not None:
                if commodity_info.same_target_only:
                    objects.append(self.target)
                if not commodity_info.consider_same_target:
                    objects_to_ignore.append(self.target)
            if self.carry_target != self.target:
                if commodity_info.same_target_only:
                    objects.append(self.carry_target)
                if not commodity_info.consider_same_target:
                    objects_to_ignore.append(self.carry_target)
            if not (self.carry_target is not None and objects):
                objects = None
            if not objects_to_ignore:
                objects_to_ignore = None
            if not commodities:
                if static_commodities:
                    request = ParameterizedAutonomyRequestInfo(commodities, static_commodities, objects, commodity_info.retain_priority, commodity_info.retain_carry_target, objects_to_ignore=objects_to_ignore, randomization_override=commodity_info.randomization_override, radius_to_consider=commodity_info.radius_to_consider, consider_scores_of_zero=commodity_info.consider_scores_of_zero, retain_context_source=commodity_info.retain_context_source, test_connectivity_to_target=commodity_info.test_connectivity_to_target, ignore_user_directed_and_autonomous=commodity_info.ignore_user_directed_and_autonomous)
                    parameterized_requests.append(request)
            request = ParameterizedAutonomyRequestInfo(commodities, static_commodities, objects, commodity_info.retain_priority, commodity_info.retain_carry_target, objects_to_ignore=objects_to_ignore, randomization_override=commodity_info.randomization_override, radius_to_consider=commodity_info.radius_to_consider, consider_scores_of_zero=commodity_info.consider_scores_of_zero, retain_context_source=commodity_info.retain_context_source, test_connectivity_to_target=commodity_info.test_connectivity_to_target, ignore_user_directed_and_autonomous=commodity_info.ignore_user_directed_and_autonomous)
            parameterized_requests.append(request)
        if parameterized_requests:
            for sim in self.get_participants(participant_type):
                (result, selected_interaction) = yield from self._process_parameterized_autonomy_request_gen(timeline, sim, parameterized_requests, context_bucket, as_continuation=as_continuation)
                if result:
                    if push_on_success_or_fail is not None:
                        for entry in push_on_success_or_fail:
                            if entry.push_on_fail is False:
                                target_sims = self.get_participants(entry.who)
                                for sim in target_sims:
                                    context = InteractionContext(sim, selected_interaction.source, selected_interaction.priority)
                                    sim.push_super_affordance(entry.affordance, selected_interaction.target, context)
                        if push_on_success_or_fail is not None:
                            for entry in push_on_success_or_fail:
                                if entry.push_on_fail is True:
                                    target_sims = self.get_participants(entry.who)
                                    for sim in target_sims:
                                        context = InteractionContext(sim, self.source, self.priority)
                                        sim.push_super_affordance(entry.affordance, sim, context)
                        if fallback_notification:
                            if sim.is_npc and participant_type & ParticipantType.Actor:
                                pass
                            else:
                                resolver = SingleSimResolver(sim.sim_info)
                                dialog = fallback_notification(sim, resolver)
                                dialog.text = fallback_notification.text
                                dialog.show_dialog(icon_override=IconInfoData(obj_instance=sim))
                else:
                    if push_on_success_or_fail is not None:
                        for entry in push_on_success_or_fail:
                            if entry.push_on_fail is True:
                                target_sims = self.get_participants(entry.who)
                                for sim in target_sims:
                                    context = InteractionContext(sim, self.source, self.priority)
                                    sim.push_super_affordance(entry.affordance, sim, context)
                    if fallback_notification:
                        if sim.is_npc and participant_type & ParticipantType.Actor:
                            pass
                        else:
                            resolver = SingleSimResolver(sim.sim_info)
                            dialog = fallback_notification(sim, resolver)
                            dialog.text = fallback_notification.text
                            dialog.show_dialog(icon_override=IconInfoData(obj_instance=sim))
        return True

    def _process_parameterized_autonomy_request_gen(self, timeline, sim, parameterized_requests, context_bucket, as_continuation=True):
        preferred_carrying_sim = self.target if self.target is not None and self.target.is_sim and self.sim is sim else None
        context = self.context.clone_for_sim(sim, preferred_carrying_sim=preferred_carrying_sim)
        action_selected = False
        autonomy_service = services.autonomy_service()
        for parameterized_request in parameterized_requests:
            if parameterized_request.retain_priority:
                priority = self.priority
            else:
                priority = interactions.priority.Priority.Low
            if parameterized_request.retain_context_source:
                context_source = context.source
            else:
                context_source = InteractionContext.SOURCE_AUTONOMY
            if not (parameterized_request.retain_carry_target and as_continuation):
                group_id = continuation_id = visual_continuation_id = None
                context.carry_target = None
            else:
                group_id = continuation_id = visual_continuation_id = DEFAULT
            if parameterized_request.randomization_override is not None:
                randomization_override = parameterized_request.randomization_override
            else:
                randomization_override = DEFAULT
            context = context.clone_for_parameterized_autonomy(self, source=context_source, priority=priority, bucket=context_bucket, group_id=group_id, continuation_id=continuation_id, visual_continuation_id=visual_continuation_id)
            autonomy_request = autonomy.autonomy_request.AutonomyRequest(sim, FullAutonomy, commodity_list=parameterized_request.commodities, static_commodity_list=parameterized_request.static_commodities, object_list=parameterized_request.objects, ignored_object_list=parameterized_request.objects_to_ignore, affordance_list=parameterized_request.affordances, apply_opportunity_cost=False, is_script_request=True, ignore_user_directed_and_autonomous=parameterized_request.ignore_user_directed_and_autonomous, context=context, si_state_view=sim.si_state, limited_autonomy_allowed=True, radius_to_consider=parameterized_request.radius_to_consider, consider_scores_of_zero=parameterized_request.consider_scores_of_zero, autonomy_mode_label_override='ParameterizedAutonomy', test_connectivity_to_target_object=parameterized_request.test_connectivity_to_target)
            selected_interaction = yield from autonomy_service.find_best_action_gen(timeline, autonomy_request, randomization_override=randomization_override)
            if selected_interaction is None:
                pass
            else:
                result = AffordanceObjectPair.execute_interaction(selected_interaction)
                if result:
                    action_selected = True
        return (action_selected, selected_interaction)

    def _get_autonomy(self, commodity_info_list, fallback_notification=None, as_continuation=True):
        if commodity_info_list:

            def _on_autonomy_gen(timeline):
                yield from self._parameterized_autonomy_helper_gen(timeline, commodity_info_list, InteractionBucketType.DEFAULT, fallback_notification=fallback_notification, as_continuation=as_continuation)

            return _on_autonomy_gen

    def _get_pre_add_autonomy(self):
        return self._get_autonomy(self.pre_add_autonomy_commodities, as_continuation=False)

    def _get_pre_run_autonomy(self):
        return self._get_autonomy(self.pre_run_autonomy_commodities, as_continuation=False)

    def _get_post_guaranteed_autonomy(self):
        return self._get_autonomy(self.post_guaranteed_autonomy_commodities)

    def _get_post_run_autonomy(self):
        post_run_commodites = list()
        fallback_notification = None
        if self.post_run_autonomy_commodities is not None:
            post_run_commodites.extend(self.post_run_autonomy_commodities.requests)
            fallback_notification = self.post_run_autonomy_commodities.fallback_notification
        if self.additional_post_run_autonomy_commodities is not None:
            post_run_commodites.extend(self.additional_post_run_autonomy_commodities)
            return self._get_autonomy(post_run_commodites, fallback_notification=fallback_notification)
        return self._get_autonomy(post_run_commodites, fallback_notification=fallback_notification)

    def provide_route_events(self, route_event_context, sim, path, failed_types=None, **kwargs):
        resolver = self.get_resolver()
        for route_event_tuple in self.route_events:
            participants = self.get_participants(route_event_tuple.participant)
            for participant in participants:
                if not failed_types is None:
                    pass
                if participant is sim and (route_event_context.route_event_already_scheduled(route_event_tuple.route_event) or route_event_tuple.route_event is not None and route_event_tuple.route_event.test(resolver)):
                    route_event_context.add_route_event(RouteEventType.INTERACTION_PRE, route_event_tuple.route_event(provider=self))

    def add_prepare_liability(self, liability):
        if self._prepare_liabilities is None:
            self._prepare_liabilities = []
        self._prepare_liabilities.append(liability)

    def is_route_event_valid(self, route_event, time, sim, path):
        return True

    def prepare_gen(self, timeline, cancel_incompatible_carry_interactions=False):
        current_posture_target = None
        if self.sim.posture.target:
            current_posture_target = self.sim.posture.target.part_owner if self.sim.posture.target.is_part else self.sim.posture.target
        if self.waiting_line is not None and (self._ignore_waiting_line_tuning or self.target is not current_posture_target or self.waiting_line.allow_line_on_same_target):
            self.push_route_nearby_and_wait_in_line()
            self.cancel(FinishingType.NATURAL, cancel_reason_msg='Pushed a Waiting Line interaction.')
            return InteractionQueuePreparationStatus.PUSHED_REPLACEMENT
        if cancel_incompatible_carry_interactions and not self.cancel_incompatible_carry_interactions():
            return InteractionQueuePreparationStatus.NEEDS_DERAIL
        if self.source not in InteractionContext.TRANSITIONAL_SOURCES:
            self.sim.skip_autonomy(self, True)
        autonomy_element = self._get_pre_add_autonomy()
        if autonomy_element is not None:
            result = yield from element_utils.run_child(timeline, autonomy_element)
            if not result:
                logger.error('Failed to run pre_add_autonomy for {}', self)
        for sim in self.get_participants(ParticipantType.AllSims):
            sim.update_related_objects(self.sim, forced_interaction=self)
        if self._run_priority is not None:
            self._priority = self._run_priority
        if self._prepare_liabilities is not None:
            for liability in self._prepare_liabilities:
                result = yield from liability.on_prepare_gen(timeline)
                if result != InteractionQueuePreparationStatus.SUCCESS:
                    return result
            self._prepare_liabilities = None
        return InteractionQueuePreparationStatus.SUCCESS

    def push_route_nearby_and_wait_in_line(self):
        destination_position = self.target.position
        if self.waiting_line.line_origin_override is not None:
            subroot_index = self.waiting_line.line_origin_override
            target_obj = self.target.part_owner if self.target.is_part else self.target
            destination_part = target_obj.get_part_by_index(subroot_index)
            if destination_part is None:
                logger.error("Wait in line for interaction {} is looking for a subroot index {} which the object doesn't have.", self, subroot_index)
            else:
                destination_position = destination_part.position
        routing_surface = self.target.routing_surface
        if self.target.has_component(WAITING_LINE_COMPONENT):
            if self.target.waiting_line_component.is_sim_in_line(self.sim):
                return False
            key = self.waiting_line.waiting_line_key
            waiting_line = self.target.waiting_line_component.get_waiting_line(key)
            if waiting_line is not None:
                last_sim_in_line = waiting_line.last_interaction_in_line.sim
                destination_position = last_sim_in_line.intended_position
                routing_surface = last_sim_in_line.routing_surface
        constraint_circle = interactions.constraints.Circle(destination_position, self.waiting_line.route_nearby_radius, routing_surface)
        if not constraint_circle.valid:
            return False
        constraint_circle = constraint_circle.intersect(STAND_OR_SIT_CONSTRAINT)
        route_near_affordance = LineUtils.ROUTE_TO_WAITING_IN_LINE
        route_near_context = InteractionContext(self.sim, self.context.source, self.priority, insert_strategy=QueueInsertStrategy.FIRST, cancel_if_incompatible_in_queue=True)

        def push_wait_in_line(_):
            self._aop.interaction_parameters['ignore_waiting_line_tuning'] = True
            interaction_data_to_store = (self.aop, self.context, self.waiting_line.waiting_line_key)
            line_head_data_to_store = (self.waiting_line.line_head_position, self.waiting_line.line_head_angle, self.waiting_line.line_cone, self.waiting_line.line_head_los_constraint)
            wait_in_line_affordance = self.waiting_line.waiting_line_interaction
            if wait_in_line_affordance is None:
                logger.error('interaction {} using a waiting line has no waiting line interaction tuned.', self)
                return
            continuation_context = route_near_context.clone_for_continuation(self)
            self.sim.push_super_affordance(wait_in_line_affordance, self.aop.target, continuation_context, allow_posture_changes=False, must_run_next=True, interaction_data=interaction_data_to_store, line_head_data=line_head_data_to_store)

        self.sim.push_super_affordance(route_near_affordance, self.target, route_near_context, constraint_to_satisfy=constraint_circle, allow_posture_changes=True, run_element=element_utils.build_element(push_wait_in_line), name_override='RouteToWaitingLine', display_name_override=self.display_name)

    @classproperty
    def can_holster_incompatible_carries(cls):
        allow_holster = cls.basic_content.allow_holster if cls.basic_content is not None else None
        if allow_holster is not None:
            return allow_holster
        return cls.one_shot

    @classproperty
    def allow_holstering_of_owned_carries(cls):
        return cls.staging

    def excluded_posture_destination_objects(self):
        return set()

    def run_pre_transition_behavior(self):
        if self.is_user_directed:
            targets = self.get_participants(ParticipantType.AllSims)
            for sim in targets:
                sim.clear_lot_routing_restrictions_ref_count()
        if not self.invite_in_after_interaction:
            return True
        target_sim = self.get_participant(ParticipantType.TargetSim)
        if target_sim is not None and (self.is_user_directed and target_sim.is_npc) and (target_sim.sim_info.lives_here or (self.sim.sim_info.lives_here or services.get_zone_situation_manager().is_player_greeted()) and self.sim.is_on_active_lot()):
            has_full_permissions = True
            for role in target_sim.autonomy_component.active_roles():
                if not role.has_full_permissions:
                    has_full_permissions = False
                    break
            if not has_full_permissions:
                self.add_liability(situations.situation_liabilities.AUTO_INVITE_LIABILTIY, situations.situation_liabilities.AutoInviteLiability())
        return True

    def enter_si_gen(self, timeline, must_enter=False, pairwise_intersection=False):
        self._lifetime_state = LifetimeState.RUNNING
        for mixer in self.all_affordances_gen():
            if mixer.lock_out_time_initial is not None:
                self.sim.set_sub_action_lockout(mixer, initial_lockout=True)
        if not SIState.add(self, must_add=must_enter, pairwise_intersection=pairwise_intersection):
            return False
        yield from self.si_state.process_gen(timeline)
        yield from element_utils.run_child(timeline, self._get_pre_run_autonomy())
        return True

    def on_added_to_queue(self, *args, **kwargs):
        if self.target.is_in_inventory():
            self.target_in_inventory_when_queued = True
        return super().on_added_to_queue(*args, **kwargs)

    def set_as_added_to_queue(self, notify_client=True):
        added_to_queue = False
        if self.pipeline_progress == PipelineProgress.NONE:
            self.on_added_to_queue(notify_client=notify_client)
            added_to_queue = True
        return added_to_queue

    @classproperty
    def is_teleport_style_injection_allowed(cls):
        return cls.allow_teleport_style_injection

    def _maybe_acquire_posture_ownership(self):
        if not self.can_acquire_posture_ownership:
            return
        if self.is_finishing:
            return
        if self.disable_transitions or self.is_compatible_with_stand_at_none or self.target is not None and self.carry_target is None:
            body_posture = self.sim.posture_state.body
            if self is not body_posture.source_interaction:
                self.acquire_posture_ownership(body_posture)

    def run_direct_gen(self, timeline, source_interaction=None, pre_run_behavior=None, included_sis=None, acquire_posture_ownership=True):
        notify_client = source_interaction is self
        added_to_queue = self.set_as_added_to_queue(notify_client=notify_client)
        result = not self.is_finishing
        if self.pipeline_progress < PipelineProgress.PREPARED:
            status = yield from self.prepare_gen(timeline)
            if status == InteractionQueuePreparationStatus.NEEDS_DERAIL and self.transition is not None:
                self.transition.derail(DerailReason.PREEMPTED, self.sim)
                return False
            result = status != InteractionQueuePreparationStatus.FAILURE
        if pre_run_behavior is not None:
            result = yield from element_utils.run_child(timeline, pre_run_behavior)
        if result and result and result:
            result = not self.is_finishing
        if self.running or self.pipeline_progress == PipelineProgress.RUNNING:
            return result
        if result:
            if acquire_posture_ownership:
                self._maybe_acquire_posture_ownership()
                if included_sis:
                    for included_si in included_sis:
                        included_si._maybe_acquire_posture_ownership()
            must_enter = pre_run_behavior is not None and self.provided_posture_type is not None
            pairwise_intersection = must_enter and self is not source_interaction
            self.pipeline_progress = PipelineProgress.RUNNING
            result = yield from self.enter_si_gen(timeline, must_enter=must_enter, pairwise_intersection=pairwise_intersection)
            if not result:
                self.pipeline_progress = PipelineProgress.PREPARED
                if added_to_queue:
                    self.on_removed_from_queue()
                if pre_run_behavior is not None:
                    self.sim.reset(ResetReason.RESET_ON_ERROR, self, 'Failed to enter SI State')
                self.cancel(FinishingType.INTERACTION_INCOMPATIBILITY, 'Failed to enter SI state.')
                return False
            if self.transition.interaction is self:
                self.transition._success = True
            self.sim.queue.remove_for_perform(self)
            if self.transition is not None and result:
                result = yield from self.sim.queue.run_interaction_gen(timeline, self, source_interaction=source_interaction)
        elif added_to_queue:
            self.cancel(FinishingType.TRANSITION_FAILURE, 'Failed to do pre-run transition')
            self.on_removed_from_queue()
        return result

    @staticmethod
    def should_replace_posture_source_interaction(new_interaction):
        if new_interaction.simless:
            return False
        elif not (new_interaction.sim.posture.posture_type is new_interaction.provided_posture_type and (new_interaction.sim.posture.source_interaction is not new_interaction and new_interaction.sim.posture.multi_sim) and new_interaction.sim.posture.is_puppet):
            return True
        return False

    @property
    def is_compatible_with_stand_at_none(self):
        interaction_constraint = self.constraint_intersection(posture_state=None)
        for constraint in interaction_constraint:
            posture_state_spec = constraint.posture_state_spec
            if posture_state_spec is not None:
                if posture_state_spec.body_target is PostureSpecVariable.ANYTHING or posture_state_spec.body_target is None:
                    break
                    break
            else:
                break
        return False
        return interaction_constraint.intersect(STAND_NO_SURFACE_CONSTRAINT).valid

    def acquire_posture_ownership(self, posture):
        if posture.target is None and posture.mobile and not posture.skip_route:
            return
        if posture.track == PostureTrack.BODY and self.is_compatible_with_stand_at_none:
            return
        if self in posture.owning_interactions:
            return
        if self.provided_posture_type is posture.posture_type:
            return
        if posture.ownable:
            self.add_liability((OWNS_POSTURE_LIABILITY, posture.track), OwnsPostureLiability(self, posture))
        posture.kill_cancel_aops()

    def _run_interaction_gen(self, timeline):
        if self.should_replace_posture_source_interaction(self):
            posture_source_interaction = self.sim.posture.source_interaction
            if posture_source_interaction is not None and not posture_source_interaction.is_finishing:
                logger.warn("Trying to replace a Posture Interaction that isn't finishing. {}", self)
            self.sim.posture.source_interaction = self
        yield from super()._run_interaction_gen(timeline)
        if self.staging:
            sequence = build_critical_section(flush_all_animations, self._stage())
            yield from element_utils.run_child(timeline, sequence)
        return True

    def _setup_gen(self, timeline):
        SIState.resolve(self)
        if self.disable_transitions or self not in self.si_state:
            logger.warn('Interaction is no longer in the SIState in _setup: {}!', self)
            return False
        self._active = True
        return True

    def get_carry_transfer_begin_element(self):

        def start_carry(timeline):
            if not self._carry_transfer_end_required:
                animation = self._carry_transfer_animation.begin(self, enable_auto_exit=False)
                yield from element_utils.run_child(timeline, animation)
                self._carry_transfer_end_required = True

        return start_carry

    def get_carry_transfer_end_element(self):

        def end_carry(timeline):
            if self._carry_transfer_end_required:
                if self._carry_transfer_animation.end is not None:
                    animation = self._carry_transfer_animation.end(self, enable_auto_exit=False)
                    yield from element_utils.run_child(timeline, animation)
                self._carry_transfer_end_required = False

        return end_carry

    def build_basic_content(self, sequence=(), **kwargs):
        super_build_basic_content = super().build_basic_content
        sequence = super_build_basic_content(sequence=sequence, **kwargs)
        if self._carry_transfer_animation is not None:
            sequence = build_critical_section(self.get_carry_transfer_begin_element(), sequence, self.get_carry_transfer_end_element())
        return sequence

    def build_basic_elements(self, *args, sequence=(), **kwargs):
        commodity_flags = set()
        for provided_affordance_data in self.provided_affordances:
            commodity_flags |= provided_affordance_data.affordance.commodity_flags
        if self.joinable:
            for join_info in self.joinable:
                if join_info.join_affordance.is_affordance:
                    join_affordance = join_info.join_affordance.value
                    if join_affordance is not None:
                        commodity_flags |= join_affordance.commodity_flags
        if commodity_flags:

            def add_flags(*_, **__):
                self.sim.add_dynamic_commodity_flags(self, commodity_flags)

            def remove_flags(*_, **__):
                if self.sim is not None:
                    self.sim.remove_dynamic_commodity_flags(self)

            return build_critical_section_with_finally(add_flags, super().build_basic_elements(*args, sequence=sequence, **kwargs), remove_flags)
        enable_auto_exit = self.basic_content is None or not self.basic_content.staging
        sequence = super().build_basic_elements(*args, enable_auto_exit=enable_auto_exit, sequence=sequence, **kwargs)
        if self.walk_style is not None:
            walkstyle_request = self.walk_style(self.sim)
            sequence = walkstyle_request(sequence=sequence)
        basic_content = self.basic_content
        if basic_content.staging:
            sequence = build_element((self._get_autonomy(basic_content.post_stage_autonomy_commodities), sequence))
        return sequence

    def kill(self):
        if self.has_been_killed:
            return False
        on_cancel_aops = self._get_cancel_replacement_aops_contexts_postures()
        if on_cancel_aops:
            self.sim.reset(ResetReason.RESET_ON_ERROR, self, 'Interaction with cancel aop killed.')
            return False
        self._finisher.on_finishing_move(FinishingType.KILLED, self)
        self.trigger_hard_stop()
        self._interrupt_active_work(True, finishing_type=FinishingType.KILLED)
        self._active = False
        if self.si_state is not None:
            SIState.on_interaction_canceled(self)
        if self.queue is not None:
            self.queue.on_interaction_canceled(self)
        continuation = self.sim.find_continuation_by_id(self.id)
        if continuation is not None:
            continuation.kill()
        return True

    def _get_cancel_replacement_context_for_posture(self, posture, affordance, always_run):
        if posture is None:
            context_source = InteractionContext.SOURCE_AUTONOMY
            continuation_id = None
            priority = self.priority
        elif posture.track == PostureTrack.BODY:
            context_source = InteractionContext.SOURCE_BODY_CANCEL_AOP
            continuation_id = None
            priority = interactions.priority.Priority.Low
        else:
            context_source = InteractionContext.SOURCE_CARRY_CANCEL_AOP
            continuation_id = self.id
            priority = interactions.priority.Priority.High
        if affordance.is_basic_content_one_shot:
            run_priority = None
        else:
            run_priority = interactions.priority.Priority.Low
        bucket = InteractionBucketType.DEFAULT if always_run else InteractionBucketType.BASED_ON_SOURCE
        context = InteractionContext(self.sim, source=context_source, priority=priority, carry_target=self.carry_target, group_id=self.group_id, insert_strategy=QueueInsertStrategy.NEXT, run_priority=run_priority, continuation_id=continuation_id, bucket=bucket)
        return context

    def _get_cancel_replacement_aops_contexts_postures(self, can_transfer_ownership=True, carry_cancel_override=None):
        cancel_aops_contexts_postures = []
        if self.sim is None:
            return cancel_aops_contexts_postures
        new_carry_owner = None
        carry_target = self.carry_target
        if not self.is_putdown:
            head_interaction = self.sim.queue.get_head()
            if head_interaction.carry_target is carry_target or head_interaction.target is carry_target:
                new_carry_owner = head_interaction
        for posture in reversed(self.sim.posture_state.aspects):
            if new_carry_owner is not None and posture.target is carry_target:
                if head_interaction not in posture.owning_interactions:
                    new_carry_owner.acquire_posture_ownership(posture)
                    if self.cancel_replacement_affordances:
                        for (posture_track_group, cancel_affordance_info) in self.cancel_replacement_affordances.items():
                            if not posture_track_group & posture.track:
                                pass
                            else:
                                cancel_affordance = cancel_affordance_info.affordance
                                if cancel_affordance_info.target is None:
                                    target = None
                                else:
                                    target = self.get_participant(cancel_affordance_info.target)
                                    if target.is_part:
                                        target = target.part_owner
                                always_run = cancel_affordance_info.always_run
                                break
                        cancel_affordance = None
                        target = None
                        always_run = False
                    else:
                        cancel_affordance = None
                        target = None
                        always_run = False
                    proxy_posture_owner = self.get_liability(ProxyPostureOwnerLiability.LIABILITY_TOKEN)
                    if proxy_posture_owner is None:
                        if cancel_affordance is not None:
                            cancel_replacement_aop = AffordanceObjectPair(cancel_affordance, target, cancel_affordance, None)
                            context = self._get_cancel_replacement_context_for_posture(posture, cancel_affordance, always_run)
                            cancel_aops_contexts_postures.append((cancel_replacement_aop, context, posture))
                        elif posture.source_interaction is not None and posture.source_interaction is not self:
                            cancel_aops = posture.source_interaction._get_cancel_replacement_aops_contexts_postures(can_transfer_ownership=False, carry_cancel_override=carry_cancel_override)
                            cancel_aops_contexts_postures.extend(cancel_aops)
                        else:
                            if cancel_affordance is not None:
                                cancel_replacement_aop = AffordanceObjectPair(cancel_affordance, target, cancel_affordance, None)
                                replacement_aop = cancel_replacement_aop
                            elif posture.track == PostureTrack.BODY:
                                replacement_aop = posture_graph.PostureGraphService.get_default_aop(self.sim.species)
                            elif posture.target is not None and (posture.target.valid_for_distribution and posture.target.reset_reason != ResetReason.BEING_DESTROYED) and posture.target in self.get_participants(ParticipantType.All):
                                affordance = self.CARRY_POSTURE_REPLACEMENT_AFFORDANCE
                                if not posture.target.is_sim:
                                    affordance = carry_cancel_override
                                replacement_aop = AffordanceObjectPair(affordance, posture.target, affordance, None)
                                context = self._get_cancel_replacement_context_for_posture(posture, replacement_aop.affordance, always_run)
                                cancel_aops_contexts_postures.append((replacement_aop, context, posture))
                            context = self._get_cancel_replacement_context_for_posture(posture, replacement_aop.affordance, always_run)
                            cancel_aops_contexts_postures.append((replacement_aop, context, posture))
                    if cancel_affordance is not None:
                        cancel_replacement_aop = AffordanceObjectPair(cancel_affordance, target, cancel_affordance, None)
                        replacement_aop = cancel_replacement_aop
                    elif posture.track == PostureTrack.BODY:
                        replacement_aop = posture_graph.PostureGraphService.get_default_aop(self.sim.species)
                    elif posture.target is not None and (posture.target.valid_for_distribution and posture.target.reset_reason != ResetReason.BEING_DESTROYED) and posture.target in self.get_participants(ParticipantType.All):
                        affordance = self.CARRY_POSTURE_REPLACEMENT_AFFORDANCE
                        if not posture.target.is_sim:
                            affordance = carry_cancel_override
                        replacement_aop = AffordanceObjectPair(affordance, posture.target, affordance, None)
                        context = self._get_cancel_replacement_context_for_posture(posture, replacement_aop.affordance, always_run)
                        cancel_aops_contexts_postures.append((replacement_aop, context, posture))
                    context = self._get_cancel_replacement_context_for_posture(posture, replacement_aop.affordance, always_run)
                    cancel_aops_contexts_postures.append((replacement_aop, context, posture))
            else:
                if self.cancel_replacement_affordances:
                    for (posture_track_group, cancel_affordance_info) in self.cancel_replacement_affordances.items():
                        if not posture_track_group & posture.track:
                            pass
                        else:
                            cancel_affordance = cancel_affordance_info.affordance
                            if cancel_affordance_info.target is None:
                                target = None
                            else:
                                target = self.get_participant(cancel_affordance_info.target)
                                if target.is_part:
                                    target = target.part_owner
                            always_run = cancel_affordance_info.always_run
                            break
                    cancel_affordance = None
                    target = None
                    always_run = False
                else:
                    cancel_affordance = None
                    target = None
                    always_run = False
                proxy_posture_owner = self.get_liability(ProxyPostureOwnerLiability.LIABILITY_TOKEN)
                if proxy_posture_owner is None:
                    if cancel_affordance is not None:
                        cancel_replacement_aop = AffordanceObjectPair(cancel_affordance, target, cancel_affordance, None)
                        context = self._get_cancel_replacement_context_for_posture(posture, cancel_affordance, always_run)
                        cancel_aops_contexts_postures.append((cancel_replacement_aop, context, posture))
                    elif posture.source_interaction is not None and posture.source_interaction is not self:
                        cancel_aops = posture.source_interaction._get_cancel_replacement_aops_contexts_postures(can_transfer_ownership=False, carry_cancel_override=carry_cancel_override)
                        cancel_aops_contexts_postures.extend(cancel_aops)
                    else:
                        if cancel_affordance is not None:
                            cancel_replacement_aop = AffordanceObjectPair(cancel_affordance, target, cancel_affordance, None)
                            replacement_aop = cancel_replacement_aop
                        elif posture.track == PostureTrack.BODY:
                            replacement_aop = posture_graph.PostureGraphService.get_default_aop(self.sim.species)
                        elif posture.target is not None and (posture.target.valid_for_distribution and posture.target.reset_reason != ResetReason.BEING_DESTROYED) and posture.target in self.get_participants(ParticipantType.All):
                            affordance = self.CARRY_POSTURE_REPLACEMENT_AFFORDANCE
                            if not posture.target.is_sim:
                                affordance = carry_cancel_override
                            replacement_aop = AffordanceObjectPair(affordance, posture.target, affordance, None)
                            context = self._get_cancel_replacement_context_for_posture(posture, replacement_aop.affordance, always_run)
                            cancel_aops_contexts_postures.append((replacement_aop, context, posture))
                        context = self._get_cancel_replacement_context_for_posture(posture, replacement_aop.affordance, always_run)
                        cancel_aops_contexts_postures.append((replacement_aop, context, posture))
                if cancel_affordance is not None:
                    cancel_replacement_aop = AffordanceObjectPair(cancel_affordance, target, cancel_affordance, None)
                    replacement_aop = cancel_replacement_aop
                elif posture.track == PostureTrack.BODY:
                    replacement_aop = posture_graph.PostureGraphService.get_default_aop(self.sim.species)
                elif posture.target is not None and (posture.target.valid_for_distribution and posture.target.reset_reason != ResetReason.BEING_DESTROYED) and posture.target in self.get_participants(ParticipantType.All):
                    affordance = self.CARRY_POSTURE_REPLACEMENT_AFFORDANCE
                    if not posture.target.is_sim:
                        affordance = carry_cancel_override
                    replacement_aop = AffordanceObjectPair(affordance, posture.target, affordance, None)
                    context = self._get_cancel_replacement_context_for_posture(posture, replacement_aop.affordance, always_run)
                    cancel_aops_contexts_postures.append((replacement_aop, context, posture))
                context = self._get_cancel_replacement_context_for_posture(posture, replacement_aop.affordance, always_run)
                cancel_aops_contexts_postures.append((replacement_aop, context, posture))
        return cancel_aops_contexts_postures

    def _on_cancel_aop_canceled(self, posture):
        self._has_pushed_cancel_aop.discard(posture)

    def _try_exit_via_cancel_aop(self, carry_cancel_override=None):
        sim = self.sim
        if sim is None or sim.is_being_destroyed:
            return False
        on_cancel_aops_contexts_postures = self._get_cancel_replacement_aops_contexts_postures(carry_cancel_override=carry_cancel_override)
        if not on_cancel_aops_contexts_postures:
            return sim.posture_state.is_source_interaction(self)
        prevent_from_canceling = False
        for (on_cancel_aop, context, posture) in on_cancel_aops_contexts_postures:
            if on_cancel_aop.affordance is None:
                pass
            elif context.source == InteractionSource.BODY_CANCEL_AOP and sim.parent is not None and sim.parent.is_sim:
                pass
            else:
                if self.staging:
                    prevent_from_canceling = not self.satisfied
                if not (self in sim.si_state and (posture.source_interaction is self or posture is sim.posture) and sim.queue.needs_cancel_aop(on_cancel_aop, context)):
                    pass
                elif posture in self._has_pushed_cancel_aop:
                    pass
                else:
                    cancel_aop_result = on_cancel_aop.test(context)
                    if not cancel_aop_result:
                        logger.warn('Failed to push the cancelation replacement effect ({} -> {}) for {}: {}.', posture, on_cancel_aop, self, cancel_aop_result)
                        sim.reset(ResetReason.RESET_EXPECTED, self, 'Failed to push cancel aop:{}.'.format(on_cancel_aop))
                    execute_result = on_cancel_aop.interaction_factory(context)
                    cancel_interaction = execute_result.interaction
                    if context.source == InteractionContext.SOURCE_BODY_CANCEL_AOP:
                        cancel_interaction.add_liability(CANCEL_AOP_LIABILITY, CancelAOPLiability(sim, cancel_interaction, self, self._on_cancel_aop_canceled, posture))
                    result = AffordanceObjectPair.execute_interaction(cancel_interaction)
                    if result:
                        self._has_pushed_cancel_aop.add(posture)
        return prevent_from_canceling

    @staticmethod
    @contextmanager
    def cancel_deferred(sis):
        for si in sis:
            if si is not None:
                si._cancel_deferred = []
        try:
            yield None
        finally:
            for si in sis:
                if not si is None:
                    if si._cancel_deferred is None:
                        pass
                    else:
                        for (args, kwargs) in si._cancel_deferred:
                            si._cancel(*args, **kwargs)
                        si._cancel_deferred = None

    def _cancel_eventually(self, *args, immediate=False, **kwargs):
        if self.is_finishing or not (self._cancel_deferred is not None and immediate):
            self.log_info('CancelEventually', msg='{}/{}'.format(args, kwargs))
            self._cancel_deferred.append((args, kwargs))
            return False
        return self._cancel(*args, **kwargs)

    def _cancel(self, finishing_type, cancel_reason_msg, notify_UI=False, lifetime_state=None, log_id=None, ignore_must_run=False, carry_cancel_override=None):
        user_cancel_liability = self.get_liability(UserCancelableChainLiability.LIABILITY_TOKEN)
        if user_cancel_liability is not None and finishing_type == FinishingType.USER_CANCEL:
            user_cancel_liability.set_user_cancel_requested()
        if self._in_cancel:
            return False
        self.log_info('Cancel', msg='finishing_type={}, notify_UI={}, lifetime_state={}, log_id={}, cancel_reason_msg={}, ignore_must_run={}, user_cancel={}'.format(finishing_type, notify_UI, lifetime_state, log_id, cancel_reason_msg, ignore_must_run, self.user_canceled))
        try:
            self._in_cancel = True
            if self.must_run and not ignore_must_run:
                return False
            if self.is_finishing:
                return False
            if self.is_cancel_aop and self.pipeline_progress < PipelineProgress.STAGED and finishing_type == FinishingType.USER_CANCEL:
                return False
            self._finisher.on_pending_finishing_move(finishing_type, self)
            self.force_inertial = True
            if self.combinable_interactions:
                for combinable_interaction in set(self.combinable_interactions):
                    combinable_interaction.remove_self_from_combinable_interactions()
                    if combinable_interaction.transition is not None:
                        combinable_interaction.transition.derail(DerailReason.PROCESS_QUEUE, self.sim)
            if self.sim is not None:
                if notify_UI and not (self.is_finishing_naturally or self._finisher.has_pending_natural_finisher):
                    self.sim.ui_manager.set_interaction_canceled(self.id, True)
                posture = self.sim.posture
                if posture.source_interaction is self:
                    if posture.target.is_sim:
                        carry_posture = posture.target.posture_state.get_carry_posture(self.sim)
                        if carry_posture is not None:
                            carry_posture.source_interaction.cancel(finishing_type, cancel_reason_msg)
                            for owning_interaction in tuple(carry_posture.owning_interactions):
                                owning_interaction.cancel(finishing_type, cancel_reason_msg)
                    for owning_interaction in tuple(posture.owning_interactions):
                        if owning_interaction is not self:
                            owning_interaction.cancel(finishing_type, cancel_reason_msg)
            if self._interrupt_active_work(finishing_type=finishing_type, cancel_reason_msg=cancel_reason_msg) and not self._try_exit_via_cancel_aop(carry_cancel_override=carry_cancel_override):
                self._active = False
                if finishing_type is not None:
                    self._finisher.on_finishing_move(finishing_type, self)
                if self.visual_type_override_data.group_cancel_behavior == CancelGroupInteractionType.ALL or self.user_canceled:
                    for grouped_int_info in self.sim.ui_manager.get_grouped_interaction_gen(self.id):
                        if self.id == grouped_int_info.interaction_id:
                            pass
                        else:
                            grouped_interaction = self.sim.find_interaction_by_id(grouped_int_info.interaction_id)
                            if grouped_interaction is not None:
                                grouped_interaction.cancel(finishing_type=finishing_type, cancel_reason_msg='Canceled by group interaction being canceled', ignore_must_run=ignore_must_run, carry_cancel_override=carry_cancel_override)
                if self.si_state is not None:
                    SIState.on_interaction_canceled(self)
                if self.queue is not None:
                    self.queue.on_interaction_canceled(self)
                for transition in self.owning_transition_sequences:
                    transition.on_owned_interaction_canceled(self)
                if self.sim is not None:
                    proxy_posture_owner = self.get_liability(ProxyPostureOwnerLiability.LIABILITY_TOKEN)
                    for posture in self.sim.posture_state.aspects:
                        if self in posture.owning_interactions and (len(posture.owning_interactions) == 1 and (posture.source_interaction is not None and posture.source_interaction is not self)) and proxy_posture_owner is None:
                            source_interaction_finishing_type = finishing_type if finishing_type == FinishingType.NATURAL else FinishingType.SI_FINISHED
                            posture.source_interaction.cancel(source_interaction_finishing_type, cancel_reason_msg='Posture Owning Interaction Canceled', carry_cancel_override=carry_cancel_override)
                if log_id is not None:
                    self.log_info(log_id, msg=cancel_reason_msg)
                if lifetime_state is not None:
                    self._lifetime_state = lifetime_state
                self._on_cancelled_callbacks(self)
                self._on_cancelled_callbacks.clear()
                return True
        except HardStopError:
            raise
        except:
            logger.exception('Exception during SI.cancel {}, cancel_reason_msg is {}:', self, cancel_reason_msg)
            logger.callstack('Invoke Callstack', level=sims4.log.LEVEL_ERROR)
            self._lifetime_state = LifetimeState.CANCELED
            if self._finisher is not None:
                self._finisher.on_finishing_move(FinishingType.KILLED, self)
            sim = self.sim
            if sim is not None:
                if sim.ui_manager is not None:
                    sim.ui_manager.set_interaction_canceled(self.id, True)
                sim.reset(ResetReason.RESET_EXPECTED, self, 'Exception during SI.cancel. {}'.format(cancel_reason_msg))
        finally:
            self._update_autonomy_timer_on_cancel(finishing_type)
            self._in_cancel = False
        return False

    def displace(self, displaced_by, cancel_reason_msg=None, **kwargs):
        if (displaced_by.source == InteractionContext.SOURCE_BODY_CANCEL_AOP or displaced_by.source == InteractionContext.SOURCE_CARRY_CANCEL_AOP) and self.transition is not None and not self.transition.succeeded:
            actor = self.get_participant(ParticipantType.Actor)
            self.transition.derail(DerailReason.DISPLACE, actor)
            return False
        notify_ui = True
        if displaced_by.source == InteractionContext.SOURCE_AUTONOMY:
            notify_ui = False
        if self.source == InteractionContext.SOURCE_AUTONOMY and displaced_by.is_super:
            carry_cancel_override = displaced_by.carry_cancel_override_for_displaced_interactions
        else:
            carry_cancel_override = None
        if cancel_reason_msg is None:
            cancel_reason_msg = 'Interaction displaced by {}.'.format(displaced_by)
        return self._cancel_eventually(FinishingType.DISPLACED, cancel_reason_msg=cancel_reason_msg, notify_UI=notify_ui, log_id='Displace_SI', carry_cancel_override=carry_cancel_override)

    def _auto_complete(self, force_satisfy=False):
        if force_satisfy:
            self.satisfied = True
            self.force_inertial = True
        return self._cancel_eventually(FinishingType.NATURAL, cancel_reason_msg='Interaction Auto Completed', log_id='Complete_SI', ignore_must_run=True)

    def cancel(self, finishing_type, cancel_reason_msg, **kwargs):
        if gsi_handlers.interaction_archive_handlers.is_archive_enabled(self):
            gsi_handlers.interaction_archive_handlers.add_cancel_callstack(self)
        return self._cancel_eventually(finishing_type, cancel_reason_msg, notify_UI=True, lifetime_state=LifetimeState.CANCELED, log_id='Cancel_SI', **kwargs)

    def _interrupt_active_work(self, kill=False, finishing_type=None, cancel_reason_msg=None):
        super()._interrupt_active_work(kill=kill, finishing_type=finishing_type)
        transition_canceled = True
        if self.transition is not None:
            if kill:
                self.transition.cancel(finishing_type=finishing_type, cancel_reason_msg=cancel_reason_msg, si_to_cancel=self)
            else:
                transition_canceled = self.transition.cancel(finishing_type=finishing_type, cancel_reason_msg=cancel_reason_msg, si_to_cancel=self)
        if self._post_guaranteed_autonomy_element is not None:
            if kill:
                self._post_guaranteed_autonomy_element.trigger_hard_stop()
            else:
                self._post_guaranteed_autonomy_element.trigger_soft_stop()
        return transition_canceled

    def on_reset(self):
        if self._finisher.has_been_reset:
            return
        if self.transition is not None:
            self.transition.on_reset()
        if self.owning_transition_sequences:
            owning_transitions = self.owning_transition_sequences.copy()
            for transition in owning_transitions:
                transition.on_reset()
        super().on_reset()
        SIState.remove_immediate(self)

    def stop(self):
        logger.callstack('Calling si.stop()', level=sims4.log.LEVEL_ERROR)

    def _exit(self, timeline, allow_yield):
        if not self.affordance.immediate:
            pass
        exit_functions = self._exit_functions
        self._exit_functions = None
        exit_si_element = None
        self._lifetime_state = LifetimeState.EXITED
        if allow_yield:
            while self.started and not self.stopped:
                exit_si_element = self.next_stage()
                yield from element_utils.run_child(timeline, exit_si_element)
        first_exception = None
        for exit_function in exit_functions:
            try:
                exit_function()
            except BaseException as exc:
                if first_exception is not None:
                    logger.exception('Suppressing duplicate exception when processing exit behavior {}', exit_function, exc=exc)
                else:
                    first_exception = exc
                allow_yield = False
        if first_exception is not None:
            raise first_exception
        if allow_yield and not self.user_canceled:
            post_run_autonomy_requests = self._get_post_run_autonomy()
            if post_run_autonomy_requests is not None:
                yield from element_utils.run_child(timeline, post_run_autonomy_requests)
        if self.sim is not None:
            self.sim.update_last_used_interaction(self)

    def _update_autonomy_timer_on_cancel(self, finishing_type):
        if self.sim is None:
            return
        self.sim.skip_autonomy(self, False)
        if finishing_type == FinishingType.USER_CANCEL or self.is_user_directed:
            self._update_autonomy_timer(force_user_directed=True)
        else:
            self._update_autonomy_timer()

    def add_default_outfit_priority(self):
        if self.outfit_priority is None:
            return
        if self._outfit_priority_id is not None:
            return
        self._outfit_priority_id = self.sim.sim_info.add_default_outfit_priority(self, self.outfit_priority.outfit_change_reason, self.outfit_priority.priority)

    def remove_default_outfit_priority(self):
        if self._outfit_priority_id is not None:
            self.sim.sim_info.remove_default_outfit_priority(self._outfit_priority_id)

    def on_transferred_to_si_state(self, participant_type=ParticipantType.Actor):
        self.log_info('Process_SI')
        if self.pipeline_progress == PipelineProgress.NONE:
            self._entered_pipeline()
        if self.staging:
            self.pipeline_progress = PipelineProgress.STAGED
        if self.should_visualize_interaction_for_sim(participant_type):
            sim = self.get_participant(participant_type)
            sim.ui_manager.transferred_to_si_state(self)
        self.remove_self_from_combinable_interactions()

    def on_removed_from_si_state(self, participant_type=ParticipantType.Actor):
        self.log_info('Remove_SI')
        if self.should_visualize_interaction_for_sim(participant_type):
            sim = self.get_participant(participant_type)
            sim.ui_manager.remove_from_si_state(self)
        if participant_type & ParticipantType.Actor:
            self._exited_pipeline()

    def _entered_pipeline(self):
        super()._entered_pipeline()
        self.add_default_outfit_priority()

    def _exited_pipeline(self, *args, **kwargs):
        self.slot_manifest = None
        for sim in self.required_sims():
            sim.queue.clear_must_run_next_interaction(self)
        super()._exited_pipeline(*args, **kwargs)
        self.remove_default_outfit_priority()
        self.refresh_constraints()
        if self.transition is not None:
            transition = self.transition
            self.transition = None
            if self.owning_transition_sequences and transition not in self.owning_transition_sequences:
                transition.end_transition()
                transition.shutdown()
        if self.owning_transition_sequences:
            owning_transitions = self.owning_transition_sequences.copy()
            self.owning_transition_sequences.clear()
            for transition in owning_transitions:
                transition.end_transition()
                transition.shutdown()
                transition.interaction.transiton = None
        for sim in self.get_participants(ParticipantType.AllSims):
            if sim.posture_state is not None:
                sim.posture_state.remove_constraint(self)
            sim.update_related_objects(self.sim)

    def disallows_full_autonomy(self, disable_full_autonomy=DEFAULT):
        if disable_full_autonomy is DEFAULT:
            disable_full_autonomy = self.disable_autonomous_multitasking_if_user_directed
        if disable_full_autonomy and self.is_user_directed and self.is_guaranteed():
            return True
        return False

    def do_post_guaranteed_autonomy(self):

        def _post_guaranteed_autonomy_gen(timeline):
            sim = self.sim
            if sim.queue is not None:
                for interaction in sim.queue:
                    if interaction.priority is interactions.priority.Priority.High:
                        return
                element = self._get_post_guaranteed_autonomy()
                if element is not None:
                    yield from element_utils.run_child(timeline, element)
                self._post_guaranteed_autonomy_element = None

        self._post_guaranteed_autonomy_element = elements.GeneratorElement(_post_guaranteed_autonomy_gen)
        self.sim.schedule_element(services.time_service().sim_timeline, self._post_guaranteed_autonomy_element)

    def _on_guaranteed_to_inertial(self):
        self.queue.on_si_phase_change(self)
        if self.affordance.force_autonomy_on_inertia:
            self.sim.run_full_autonomy_next_ping()
        if self.active and self.force_exit_on_inertia:
            self._auto_complete()
        if not self._pre_exit_behavior_done:
            self._pre_exit_behavior_done = True
            if self.sim.is_simulating:
                self.do_post_guaranteed_autonomy()

    def _on_inertial_to_guaranteed(self):
        self.apply_posture_state(self.sim.posture_state)
        self.queue.on_si_phase_change(self)

    @property
    def pending_complete(self):
        return self._lifetime_state == LifetimeState.PENDING_COMPLETE or self._lifetime_state == LifetimeState.CANCELED

    @property
    def will_exit(self):
        if self.started and self.is_basic_content_one_shot:
            return True
        return self._lifetime_state >= LifetimeState.PENDING_COMPLETE or self.is_finishing

    @property
    def has_pushed_cancel_aop(self):
        return self._has_pushed_cancel_aop

    def process_events(self):
        if self.pending_complete:
            self._auto_complete(True)

    def completed_by_mixer(self):
        self._lifetime_state = LifetimeState.PENDING_COMPLETE

    def attach_interaction(self, interaction):
        liability = self.get_liability(CANCEL_INTERACTION_ON_EXIT_LIABILITY)
        if liability is None:
            liability = CancelInteractionsOnExitLiability()
            self.add_liability(CANCEL_INTERACTION_ON_EXIT_LIABILITY, liability)
        liability.add_cancel_entry(interaction.context.sim, interaction)
        if interaction.priority > self.priority:
            self.priority = interaction.priority
        if interaction.source != InteractionSource.REACTION and interaction not in self._interactions:
            self._interactions.add(interaction)
            if self.si_state is not None:
                self.si_state.notify_dirty()

    def detach_interaction(self, interaction):
        if interaction in self._interactions:
            self._interactions.remove(interaction)
        liability = self.get_liability(CANCEL_INTERACTION_ON_EXIT_LIABILITY)
        if liability is not None:
            liability.remove_cancel_entry(interaction.sim, interaction)

    def set_stat_asm_parameter(self, asm, actor_name, target_name, sim, target):
        if self.animation_stat is None:
            return
        if self.animation_stat.use_actor_skill:
            skill_sim = sim
            skill_actor_name = actor_name
        else:
            skill_sim = target
            skill_actor_name = target_name
        if not skill_sim.is_sim:
            return
        if self.animation_stat is not None:
            tested_result = self.animation_stat.stat(resolver=self.get_resolver())
            if tested_result is None:
                return
            animation_stat = skill_sim.get_stat_instance(tested_result, add=True)
            if animation_stat is not None:
                (asm_param_name, asm_param_value) = animation_stat.get_asm_param()
                if asm_param_name is not None and asm_param_value is not None:
                    asm.set_actor_parameter(skill_actor_name, skill_sim, asm_param_name, asm_param_value)

    def perform_gen(self, timeline):
        result = yield from Interaction.perform_gen(self, timeline)
        if self.one_shot:
            self.satisfied = True
        if self.is_guaranteed() or self.force_exit_on_inertia or self.one_shot:
            self._auto_complete()
        return result

    def _get_resource_instance_hash(self):
        if self._saveable.affordance_to_save is not None:
            return self._saveable.affordance_to_save.guid64
        return self.guid64

    def _get_save_object(self):
        save_object = self.get_participant(self._saveable.target_to_save)
        return save_object

    def fill_save_data(self, save_data):
        save_data.interaction = self._get_resource_instance_hash()
        save_target = self._get_save_object()
        if save_target is not None:
            save_data.target_id = save_target.id
            if save_target.is_part:
                save_data.target_part_group_index = save_target.part_group_index
        save_data.source = self.context.source
        save_data.priority = self.context.priority
        if self.start_time is not None:
            save_data.start_time = self.start_time.absolute_ticks()

    @classmethod
    def create_special_load_target(cls, sim):
        pass

    @classmethod
    def create_load_context(cls, sim, source, priority):
        context = interactions.context.InteractionContext(sim, source, priority, restored_from_load=True)
        return context

    def pre_route_clothing_change(self, do_spin=True, **kwargs):
        return self.get_on_route_change(do_spin=do_spin, **kwargs)

    def get_on_route_change(self, **kwargs):
        if self.outfit_change is not None and self.outfit_change.on_route_change is not None:
            return self.outfit_change.on_route_change.get_on_entry_change(self, **kwargs)

    def get_on_route_outfit(self):
        if self.outfit_change is not None and self.outfit_change.on_route_change is not None:
            return self.outfit_change.on_route_change.get_on_entry_outfit(self)

    def get_tuned_outfit_changes(self, include_exit_changes=True):
        outfit_changes = set()
        pre_route_change = self.get_on_route_outfit()
        if pre_route_change is not None:
            outfit_changes.add(pre_route_change)
        if self.outfit_change is None:
            return outfit_changes
        overrides = self.outfit_change.posture_outfit_change_overrides
        if not overrides:
            return outfit_changes
        for outfit_change in overrides.values():
            on_entry = outfit_change.get_on_entry_outfit(self)
            if on_entry is not None:
                outfit_changes.add(on_entry)
            if not include_exit_changes:
                pass
            else:
                on_exit = outfit_change.get_on_exit_outfit(self)
                if on_exit is not None:
                    outfit_changes.add(on_exit)
        return outfit_changes

    def add_preload_outfit_changes(self, final_preload_outfit_set):
        final_preload_outfit_set.update(self.get_tuned_outfit_changes(include_exit_changes=False))

    def get_attention_cost(self):
        return self.attention_cost

    @flexmethod
    def can_reserve_target(cls, inst, *, target, context=DEFAULT):
        inst_or_cls = inst if inst is not None else cls
        context = inst.context if context is DEFAULT else context
        sim = context.sim
        if target.is_prop:
            logger.error('Sim {} is checking has_reservation_tests from prop object {} in interaction {}.', sim, target, inst_or_cls, owner='mkartika')
            return False
        if not target._has_reservation_tests:
            return ReservationResult.TRUE
        if not target.is_part:
            return ReservationResult.TRUE
        part_list = target.part_owner.parts
        for part in part_list:
            if part is target:
                pass
            else:
                for using_sim in part.get_users(sims_only=True):
                    if using_sim is sim:
                        pass
                    else:
                        for si in using_sim.si_state:
                            reserve_object_tests = si.object_reservation_tests
                            if reserve_object_tests:
                                reserve_result = reserve_object_tests.run_tests(si.get_resolver(target=sim))
                                if not reserve_result:
                                    return ReservationResult(reserve_result, result_obj=using_sim)
                        if using_sim.queue.transition_controller is not None:
                            transitioning_interaction = using_sim.queue.transition_controller.interaction
                            if transitioning_interaction.is_super:
                                reserve_object_tests = transitioning_interaction.object_reservation_tests
                                if reserve_object_tests:
                                    target_sim = sim if transitioning_interaction.sim is not sim else using_sim
                                    reserve_result = reserve_object_tests.run_tests(transitioning_interaction.get_resolver(target=target_sim))
                                    if not reserve_result:
                                        return ReservationResult(reserve_result, result_obj=using_sim)
                        reserve_object_tests = inst_or_cls.object_reservation_tests
                        if reserve_object_tests:
                            reserve_result = reserve_object_tests.run_tests(inst_or_cls.get_resolver(target=using_sim, context=context))
                            if not reserve_result:
                                return ReservationResult(reserve_result, result_obj=using_sim)
        return True
