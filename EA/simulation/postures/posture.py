from _weakrefset import WeakSetfrom animation.animation_overrides_tuning import TunableParameterMappingfrom collections import defaultdict, namedtuplefrom contextlib import contextmanagerfrom animation import AnimationContextfrom animation.animation_utils import get_auto_exit, flush_all_animationsfrom animation.posture_manifest import PostureManifest, AnimationParticipant, PostureManifestEntry, MATCH_ANY, MATCH_NONEfrom animation.posture_manifest_constants import SWIM_POSTURE_TYPEfrom buffs.appearance_modifier.appearance_modifier import AppearanceModifierfrom caches import cachedfrom carry.carry_utils import PARAM_CARRY_STATE, set_carry_track_param_if_neededfrom element_utils import build_critical_section, build_critical_section_with_finallyfrom event_testing.resolver import DoubleObjectResolver, DoubleSimResolver, SingleSimResolverfrom event_testing.results import TestResultfrom event_testing.tests import TunableGlobalTestSetfrom interactions.constraint_variants import TunableGeometricConstraintVariantfrom interactions.constraints import GLOBAL_STUB_ACTOR, GLOBAL_STUB_TARGET, ANYWHEREfrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.interaction_liabilities import OWNS_POSTURE_LIABILITYfrom interactions.utils.loot import LootActionsfrom interactions.utils.routing import RouteTargetTypefrom postures import PostureTrack, PostureEvent, get_best_supported_posturefrom postures.posture_animation_data import AnimationDataByActorSpeciesfrom postures.posture_primitive import PosturePrimitivefrom postures.posture_tunables import TunableSupportedPostureTransitionDatafrom postures.posture_validators import TunablePostureValidatorVariantfrom sims.occult.occult_enums import OccultTypefrom sims.outfits.outfit_change import TunableOutfitChangefrom sims.sim_info_types import Speciesfrom sims4.collections import frozendictfrom sims4.repr_utils import standard_reprfrom sims4.tuning.geometric import TunablePolygon, TunableVector3from sims4.tuning.instances import TunedInstanceMetaclassfrom sims4.tuning.tunable import Tunable, TunableTuple, TunableList, TunableReference, OptionalTunable, TunableEnumFlags, TunableEnumEntry, HasTunableReference, TunableIntervalfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classproperty, flexmethod, constpropertyfrom singletons import DEFAULTfrom snippets import define_snippet, POSTURE_TYPE_LISTfrom uid import unique_idimport animationimport animation.arbimport animation.asmimport cachesimport element_utilsimport enumimport interactions.constraintsimport objects.systemimport routingimport servicesimport sims4.loglogger = sims4.log.Logger('Postures')TRANSITION_POSTURE_PARAM_NAME = 'transitionPosture'with sims4.reload.protected(globals()):
    POSTURE_FAMILY_MAP = defaultdict(set)
class PosturePreconditions(enum.IntFlags):
    NONE = 0
    SAME_TARGET = 1
(TunablePostureTypeListReference, TunablePostureTypeListSnippet) = define_snippet(POSTURE_TYPE_LIST, TunableList(tunable=TunableTuple(posture_type=TunableReference(description='\n                Posture that is supported by this object.\n                ', manager=services.posture_manager(), pack_safe=True), required_clearance=OptionalTunable(tunable=Tunable(description='\n                    Amount of clearance you need in front of the object or part\n                    for this posture to be supported.\n                    ', tunable_type=float, default=1)))))
@unique_id('id')
class Posture(HasTunableReference, metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.POSTURE)):
    INSTANCE_TUNABLES = {'cost': Tunable(description='\n           ( >= 0 ) The distance a Sim is willing to pay to avoid using this\n           posture (higher number discourage using the posture).\n           ', tunable_type=float, default=0, tuning_group=GroupNames.CORE), '_supported_postures': TunableList(TunableTuple(description='\n                A list of postures that this posture supports entrance from and\n                exit to.\n                ', posture_type=TunableReference(description='\n                    A supported posture.\n                    ', manager=services.posture_manager(), pack_safe=True), entry=TunableSupportedPostureTransitionData(description='\n                    If enabled, an edge is generated from the supported posture\n                    to this posture.\n                    '), exit=TunableSupportedPostureTransitionData(description='\n                    If enabled, an edge is generated from this posture to the\n                    supported posture.\n                    '), preconditions=TunableEnumFlags(PosturePreconditions, PosturePreconditions.NONE)), tuning_group=GroupNames.CORE), 'global_validator': OptionalTunable(description='\n            If enabled, specify a test that validates whether or not this\n            posture is available for a given Sim and a target. Posture\n            transition generation should be efficient, so this should only be\n            reserved for postures whose availability is not strictly tied to a\n            single interaction (e.g. carry).\n            \n            e.g.: the "Carry Sim" posture can be transitioned in and out\n            of as part of a transition sequence that requires, say, a toddler to\n            sit on a sofa. We don\'t want to have adult Sims think they can be\n            carried to transition to the same posture. So the "Carry Sim"\n            posture globally validates that the Sim is a toddler and the target\n            a TYAE Sim.\n            \n            e.g.: Sims are supposed to be able to sit while reading. However,\n            Sims are unable to sit on charred objects. If the object is charred,\n            the posture providing interaction testing out is enough information\n            for the transition sequence not to consider sitting a valid posture.\n            ', tunable=TunablePostureValidatorVariant(), tuning_group=GroupNames.CORE), 'appearance_modifier': OptionalTunable(description='\n            If enabled, we will apply an appearance modifier on the entry and\n            exit animations for this posture.\n            ', tunable=TunableTuple(description="\n                Appearance Modifier and xevents for entry and exit, which\n                default to the posture's xevents.\n                ", modifier=AppearanceModifier.TunableFactory(), entry_xevt=Tunable(description='\n                    The xevent id to apply the appearance modifier.\n                    ', tunable_type=int, default=750), exit_xevt=Tunable(description='\n                    The xevent id to remove the appearance modifier.\n                    ', tunable_type=int, default=751), tuning_group=GroupNames.OUTFITS)), 'loot_actions_on_exit': TunableList(description='\n            List of loot actions to apply when exiting the posture.\n            \n            Caution: This should only be used if we need the loot to apply\n            after the exit transition has been planned by the Sim.\n            eg. Removing a buff that is used in a validator to determine the\n            correct posture to exit to.\n            \n            Please talk to your GPE if you are adding loot actions here.\n            ', tunable=LootActions.TunableReference(), tuning_group=GroupNames.SPECIAL_CASES), 'switch_occult': OptionalTunable(description='\n            If enabled, switch the Sim into the specified occult type.\n            ', tunable=TunableTuple(description="\n                Occult types and xevt for entry and exit, which default to the\n                posture's xevts.\n                ", entry=TunableTuple(description='\n                    The occult type to switch to and the xevt on which to \n                    trigger the switch on entry.\n                    ', entry_xevt=Tunable(description='\n                        The xevt on which to trigger the occult switch on entry.\n                        ', tunable_type=int, default=750), entry_occult=TunableEnumEntry(description='\n                        The occult to switch to on entry.\n                        ', tunable_type=OccultType, default=OccultType.HUMAN)), exit=TunableTuple(description='\n                    The occult type to switch to and the xevt on which to \n                    trigger the switch on exit.\n                    ', exit_xevt=Tunable(description='\n                        The xevt on which to trigger the occult switch on exit.\n                        ', tunable_type=int, default=750), exit_occult=TunableEnumEntry(description='\n                        The occult to switch to on exit.\n                        ', tunable_type=OccultType, default=OccultType.HUMAN)))), 'outfit_change': TunableOutfitChange(description='\n            Define what outfits the Sim is supposed to wear when entering or\n            exiting this posture.\n            ', tuning_group=GroupNames.OUTFITS), 'override_outfit_changes': TunableList(description='\n            Define override outfits for entering this posture.\n            The first override that passes its tests will be applied.\n            ', tunable=TunableTuple(outfit_change=TunableOutfitChange(), tests=TunableGlobalTestSet(description='\n                    Tests to determine if this override should be applied.\n                    ')), tuning_group=GroupNames.OUTFITS), 'outfit_exit_xevt': OptionalTunable(description='\n            If enabled, the exit outfit change for this posture executes on an\n            event. This is useful if the animation itself incorporates some sort\n            of outfit switch.\n            \n            If disabled, the outfit change normally occurs after the posture has\n            exited, before the transition to the next posture (if supported).\n            ', tunable=Tunable(description='\n                The event to trigger the outfit change on.\n                ', tunable_type=int, default=101), tuning_group=GroupNames.OUTFITS), 'supports_outfit_change': Tunable(description='\n            Whether or not this posture supports outfit changes.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.OUTFITS), '_animation_data': AnimationDataByActorSpecies.TunableFactory(tuning_group=GroupNames.ANIMATION), '_apply_target_to_interaction_asms': Tunable(description="\n            When checked, we apply the targets in the posture ASM to other ASMs\n            that support the posture. This is important for postures like Sit,\n            because if you're doing a seated chat, the social needs to have the\n            sitTemplate because it's referenced in the animations.\n            \n            For a posture like Swim, the sit template is only used in the\n            portal animation, so other ASMs don't need the virtual actors.\n            ", tunable_type=bool, default=True, tuning_group=GroupNames.ANIMATION), 'mutex_entry_exit_animations': Tunable(description='\n            Mutex the entrance / exit animations into / out of this posture.\n            This is useful for preventing sims from clipping through each other\n            while entering / exiting multi-reserve postures on the same part.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.ANIMATION), 'rerequests_idles': Tunable(description="\n            If checked, this posture needs to re-request its idle in-between\n            actions to ensure that there are no gaps in between interactions.\n            \n            This should be unchecked for postures like those in the movingStand\n            family like Swim for which interaction animations play on Normal\n            Plus. These postures shouldn't re-request their idles because the\n            idles on the Normal track will never be stopped.\n            ", tunable_type=bool, default=True, tuning_group=GroupNames.ANIMATION), 'default_animation_params': TunableParameterMapping(description='\n            A list of param name, param value tuples will be used as the default\n            for this posture.  Should generally only be used if posture has\n            different get ins, and the object name method (used in posture_sit) would\n            require a significant amount of retuning, or would simply be\n            impossible because the posture needs to also support @none.\n            \n            example: posture_kneel (needs to support @none)          \n            ', tuning_group=GroupNames.ANIMATION), 'additional_put_down_distance': Tunable(description="\n            An additional distance in front of the Sim to start searching for\n            valid put down locations when in this posture.\n            \n            This tunable is only respected for the Sim's body posture.\n            ", tunable_type=float, default=0.5, tuning_group=GroupNames.CARRY), '_supports_carry': Tunable(description='\n            Whether or not there should be a carry version of this posture in\n            the posture graph.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.CARRY), 'holster_for_entries_and_exits': Tunable(description='\n            If enabled, the Sim will holster all carried objects before\n            entering and exiting this posture.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.CARRY), 'unconstrained': Tunable(description='\n            When checked, the Sim can stand anywhere in this posture.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.CONSTRAINTS), 'universal': OptionalTunable(description='\n            If set, this posture is meant to be used with "Universal Get In/Get Out".\n            ', tunable=TunableTuple(constraint=TunableList(description='\n                    This defines the geometric constraints to be used for\n                    generating get in *and* get out goals.\n                    \n                    NOTE: you MUST tune a geometric requirement, e.g. a cone or circle.\n                    \n                    NOTE: You MUST tune a facing requirement. For get outs, the facing\n                    requirement is automatically inverted.\n                    ', tunable=TunableGeometricConstraintVariant(circle_locked_args={'require_los': True}, disabled_constraints={'spawn_points', 'current_position'})), y_delta_interval=OptionalTunable(description='\n                    The Sim can only transition to this posture if the y delta\n                    between it and the containment slot is within these bounds.\n                    ', tunable=TunableInterval(tunable_type=float, default_lower=-10, default_upper=10)), raycast_test=OptionalTunable(description='\n                    If enabled, the raycast between the Sim and the containment\n                    slot must be unobstructed.\n                    ', tunable=TunableTuple(vertical_offset=Tunable(description='\n                            Vertical offset from the containment slot for the\n                            raycast target.\n                            ', tunable_type=float, default=0.25), horizontal_offset=Tunable(description='\n                            Horizontal offset from the containment slot for\n                            the raycast target. Positive is away from the Sim,\n                            negative is towards the Sim.\n                            ', tunable_type=float, default=-0.5)))), tuning_group=GroupNames.CONSTRAINTS), 'additional_interaction_jig_fgl_distance': Tunable(description='\n            An additional distance (in meters) in front of the Sim to start \n            searching when using FGL to place a Jig to run an interaction.\n            ', tunable_type=float, default=0, tuning_group=GroupNames.CONSTRAINTS), 'surface_types': TunableList(description='\n            A list of surfaces a Sim can use this posture on.\n            ', tunable=TunableEnumEntry(description='\n                The surface type this posture is on. e.g. stand is on the world\n                surface and swim is on the pool surface\n                ', tunable_type=routing.SurfaceType, default=routing.SurfaceType.SURFACETYPE_WORLD), tuning_group=GroupNames.CONSTRAINTS), 'jig': OptionalTunable(description='\n            An optional jig to place while the Sim is in this posture.\n            ', tunable=TunableReference(description='\n                The jig to place while the Sim is in this posture.\n                ', manager=services.definition_manager()), tuning_group=GroupNames.CONSTRAINTS), 'use_containment_slot_for_exit': Tunable(description="\n            If checked, the sim will use the posture's containment slot as\n            their new position when exiting this posture. If unchecked, the\n            sim's current position will be used instead. Generally, this should\n            be checked for every posture that doesn't change a Sim's position.\n            Exceptions to this rule are things like the cell door posture and\n            Stand.\n            ", tunable_type=bool, default=True, tuning_group=GroupNames.CONSTRAINTS), 'is_canonical_family_posture': Tunable(description='\n            If checked, the sim will substitute their posture state\n            specification from the final constraint with this representative\n            posture from its family.\n            \n            Only representative postures like Stand, Sit, etc. would have this\n            checked.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.CONSTRAINTS), 'ownable': Tunable(description="\n            When checked, this posture is ownable by interactions. \n            \n            e.g.: A posture like carry_nothing should not be ownable, because it\n            will cause strange cancelations that don't make sense.\n            ", tunable_type=bool, default=True, tuning_group=GroupNames.CONSTRAINTS), 'allow_affinity': Tunable(description="\n            If True, Sims will prefer to use this posture if someone they're\n            interacting with is using the posture.\n                            \n            e.g.: If you chat with a sitting Sim, you will prefer to sit with\n            them and chat.\n            ", tunable_type=bool, default=True, tuning_group=GroupNames.SOCIALS), 'allow_social_adjustment': Tunable(description="\n            If enabled, Sims in this posture will still be considered for social\n            adjustment. If disabled, Sims in this posture will not be considered\n            for social adjustment.\n            \n            e.g.: When a Sim is sitting in the hospital exam bed, we never want\n            them to stand up out of it due to social adjustment, because it\n            doesn't make sense in context. They should stay in the bed when Sims\n            chat with them.\n            ", tunable_type=bool, default=True, tuning_group=GroupNames.SOCIALS), 'social_geometry': TunableTuple(description='\n            The special geometry for socialization in this posture.\n            ', social_space=TunablePolygon(description="\n                The special geometry override for socialization in this posture.\n                This defines where the Sim's attention is focused and informs\n                the social positioning system where each Sim should stand to\n                look most natural when interacting with this Sim. \n                \n                e.g.: we override the social geometry for a Sim who is tending\n                the bar to be a wider cone and be in front of the bar instead of\n                embedded within the bar. This encourages Sims to stand on the\n                customer- side of the bar to socialize with this Sim instead of\n                coming around the back.\n                "), focal_point=TunableVector3(description='\n                Focal point when socializing in this posture, relative to Sim\n                ', default=sims4.math.Vector3.ZERO()), tuning_group=GroupNames.SOCIALS)}
    IS_BODY_POSTURE = True
    _provided_postures = frozendict({Species.HUMAN: PostureManifest().intern()})
    _posture_name = None
    family_name = None
    supports_swim = False
    PostureTransitionData = namedtuple('PostureTransitionData', ('preconditions', 'transition_cost', 'validators'))
    _posture_transitions = {}

    def __init__(self, sim, target, track, animation_context=None, is_throwaway=False):
        self._asm = None
        self._create_asm(sim, target, animation_context, is_throwaway)
        self._source_interaction = None
        self._primitive = None
        self._owning_interactions = set()
        self._target = None
        self._target_part = None
        self._surface_target_ref = None
        self._track = None
        self._slot_constraint = {}
        self._jig_instance = None
        self._context = None
        self._asm_registry = defaultdict(dict)
        self._asms_with_posture_info = set()
        self._failed_parts = set()
        self._sim = None
        self._bind(sim, target, track)
        self._linked_posture = None
        self._entry_anim_complete = False
        self._exit_anim_complete = False
        self.external_transition = False
        self._appearance_modifier_active = False
        self._entry_occult_switch_processed = False
        self._active_cancel_aops = WeakSet()
        self._saved_exit_clothing_change = None
        self.previous_posture = None
        self.fallback_occult_on_posture_reset = None
        self._primitive_created = False

    def __str__(self):
        return '{0}:{1}'.format(self.name, self.id)

    def __repr__(self):
        return standard_repr(self, self.id, self.target)

    @classmethod
    def _tuning_loading_callback(cls):

        def delclassattr(name):
            if name in cls.__dict__:
                delattr(cls, name)

        delclassattr('_provided_postures')
        delclassattr('_posture_name')
        delclassattr('family_name')

    @classmethod
    def _tuning_loaded_callback(cls):
        supports_carry = False
        species_to_provided_postures = {}
        family_name = None
        for (species, provided_postures, asm) in cls._animation_data.get_provided_postures_gen():
            specific_name = None
            for entry in provided_postures:
                entry_specific_name = entry.specific
                if not entry_specific_name:
                    raise ValueError('{} must provide a specific posture for all posture definition rows.'.format(asm.name))
                if specific_name is None:
                    specific_name = entry_specific_name
                elif entry_specific_name != specific_name:
                    raise ValueError('{}: {} provides multiple specific postures: {}'.format(cls, asm.name, [specific_name, entry_specific_name]))
                entry_family_name = entry.family
                if entry_family_name:
                    if family_name is None:
                        family_name = entry_family_name
                    elif entry_family_name != family_name:
                        raise ValueError('{}: {} provides multiple family postures: {}'.format(cls, asm.name, [family_name, entry_family_name]))
                if entry.left != MATCH_NONE or entry.right != MATCH_NONE:
                    supports_carry = True
                species_to_provided_postures[species] = provided_postures
            if species_to_provided_postures:
                cls._provided_postures = frozendict(species_to_provided_postures)
            if cls._posture_name != None:
                if cls._posture_name != specific_name:
                    logger.error('Two species in posture {} are trying to set this posture to different names. The postures must have the same name.', cls)
                    cls._posture_name = specific_name
            else:
                cls._posture_name = specific_name
        for posture_data in cls._supported_postures:
            if posture_data.entry is not None:
                transition_data = cls.PostureTransitionData(posture_data.preconditions, posture_data.entry.cost, posture_data.entry.validators)
                cls._add_posture_transition(posture_data.posture_type, cls, transition_data)
            if posture_data.exit is not None:
                transition_data = cls.PostureTransitionData(posture_data.preconditions, posture_data.exit.cost, posture_data.exit.validators)
                cls._add_posture_transition(cls, posture_data.posture_type, transition_data)
            if posture_data.posture_type.name == SWIM_POSTURE_TYPE:
                cls.supports_swim = True
        if supports_carry or cls._supports_carry:
            logger.error('{} is tuned to support carry, but none of its ASMs has a posture manifest entry supporting carry', cls)
        cls.family_name = family_name
        POSTURE_FAMILY_MAP[cls.family_name].add(cls)

    @contextmanager
    def __reload_context__(oldobj, newobj):
        posture_transitions = dict(oldobj._posture_transitions)
        yield None
        oldobj._posture_transitions.update(posture_transitions)

    @classproperty
    def posture_type(cls):
        return cls

    @classproperty
    def name(cls):
        return cls._posture_name or cls.__name__

    @constproperty
    def mobile():
        return False

    @constproperty
    def skip_route():
        return False

    @constproperty
    def is_vehicle():
        return False

    @classproperty
    def multi_sim(cls):
        return False

    @classproperty
    def is_universal(cls):
        if cls.universal is not None:
            return True
        return False

    @flexmethod
    def get_actor_name(cls, inst, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        animation_data = inst_or_cls.get_animation_data(**kwargs)
        return animation_data._actor_param_name

    @flexmethod
    def get_target_name(cls, inst, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        animation_data = inst_or_cls.get_animation_data(**kwargs)
        return animation_data._target_name

    @classmethod
    def get_transition_costs(cls, posture_type):
        transition_data = cls._posture_transitions.get((cls, posture_type))
        return transition_data.transition_cost.get_cost(cls, posture_type)

    @classmethod
    def _get_top_level_parent(cls, target):
        if target is None:
            logger.error('Trying to validate invalid target {} for posture {}', target, cls, owner='camilogarcia')
            return
        top_parent = target
        while top_parent.parent is not None:
            top_parent = top_parent.parent
        top_parent = top_parent.part_owner if top_parent.is_part else top_parent
        return top_parent

    @classmethod
    def is_available_transition(cls, destination_posture_type, targets_match=False):
        key = (cls, destination_posture_type)
        if key not in cls._posture_transitions:
            return False
        if targets_match:
            return True
        else:
            transition_data = cls._posture_transitions[key]
            preconditions = transition_data.preconditions
            if preconditions is not None and int(preconditions) & PosturePreconditions.SAME_TARGET:
                return False
        return True

    @classmethod
    def is_same_posture_or_family(cls, other_cls):
        if cls == other_cls:
            return True
        return cls.family_name is not None and cls.family_name == other_cls.family_name

    @classmethod
    def is_valid_transition(cls, destination_posture_type, resolver):
        transition_data = cls._posture_transitions.get((cls, destination_posture_type))
        if transition_data is None:
            return False
        return all(validator(resolver) for validator in transition_data.validators)

    @classmethod
    def get_exit_postures_gen(cls, sim, target):
        resolver = DoubleSimResolver(sim, target)
        for ((posture_type, exit_posture_type), transition_data) in cls._posture_transitions.items():
            if posture_type is not cls:
                pass
            elif not all(validator(resolver) for validator in transition_data.validators):
                pass
            else:
                yield exit_posture_type

    @classmethod
    @cached(maxsize=512)
    def is_valid_target(cls, sim, target):
        if sim is target:
            return False
        resolver = DoubleObjectResolver(sim, target)
        if cls.global_validator is not None and not cls.global_validator(resolver):
            return False
        elif target is not None and target.is_sim and target.is_hidden():
            return False
        return True

    @classmethod
    def is_valid_destination_target(cls, sim, target, adjacent_target=None, **kwargs):
        if adjacent_target is None:
            return True
        else:
            target_part_owner = cls._get_top_level_parent(target)
            adjacent_target_part_owner = cls._get_top_level_parent(adjacent_target)
            if target_part_owner is adjacent_target_part_owner and (target.may_reserve(sim) or target.usable_by_transition_controller(sim.queue.transition_controller)):
                return True
        return False

    @classmethod
    def has_mobile_entry_transition(cls):
        for (previous_posture, next_posture) in cls._posture_transitions:
            if next_posture is not cls:
                pass
            elif previous_posture.mobile:
                return True
        return False

    @classmethod
    def supports_posture_type(cls, posture_type, *args, is_specific=True, **kwargs):
        return (cls, posture_type) in cls._posture_transitions or (posture_type, cls) in cls._posture_transitions

    @property
    def posture_context(self):
        return self._context

    @property
    def animation_context(self):
        return self._animation_context

    @property
    def surface_target(self):
        return self.sim.posture_state.surface_target

    @property
    def source_interaction(self):
        return self._source_interaction

    @source_interaction.setter
    def source_interaction(self, value):
        if value is None:
            logger.error('Posture {} get a None source interaction set', self)
            return
        self._source_interaction = value

    @property
    def saved_exit_clothing_change(self):
        return self._saved_exit_clothing_change

    @saved_exit_clothing_change.setter
    def saved_exit_clothing_change(self, value):
        self._saved_exit_clothing_change = value

    @property
    def owning_interactions(self):
        return self._owning_interactions

    @property
    def sim(self):
        if self._sim is not None:
            return self._sim()

    @property
    def target(self):
        if self._target_part is not None:
            return self._target_part()
        elif self._target is not None:
            return self._target()

    @property
    def target_part(self):
        if self._target_part is not None:
            return self._target_part()

    @property
    def _asm_key(self):
        return self.get_animation_data()._asm_key

    @property
    def _actor_param_name(self):
        return self.get_animation_data()._actor_param_name

    @property
    def _enter_state_name(self):
        return self.get_animation_data()._enter_state_name

    @property
    def _exit_state_name(self):
        return self.get_animation_data()._exit_state_name

    @property
    def _state_name(self):
        return self.get_animation_data()._state_name

    @property
    def idle_animation(self):
        animation_data = self.get_animation_data()
        occult_idle = animation_data._idle_animation_occult_overrides.get(self.sim.sim_info.current_occult_types, None)
        if occult_idle is not None:
            return occult_idle
        return animation_data._idle_animation

    @property
    def track(self):
        return self._track

    @property
    def is_active_carry(self):
        return PostureTrack.is_carry(self.track) and self.target is not None

    @property
    def is_puppet(self):
        return False

    @property
    def is_mirrored(self):
        if self.target is not None and self.target.is_part:
            return self.target.is_mirrored() or False
        return False

    @property
    def linked_posture(self):
        return self._linked_posture

    @linked_posture.setter
    def linked_posture(self, posture):
        self._linked_posture = posture

    @property
    def asm(self):
        return self._asm

    @property
    def _locked_params(self):
        params = self.default_animation_params
        anim_overrides_actor = self.sim.get_anim_overrides(self._actor_param_name)
        params += anim_overrides_actor.params
        if self.target is not None:
            anim_overrides_target = self.target.get_anim_overrides(self.get_target_name())
            if anim_overrides_target is not None:
                params += anim_overrides_target.params
            if self.target.is_part:
                part_suffix = self.target.part_suffix
                if part_suffix is not None:
                    params += {'subroot': part_suffix}
        if self.is_mirrored is not None:
            params += {'isMirrored': self.is_mirrored}
        return params

    @property
    def locked_params(self):
        if self.slot_constraint is None or self.slot_constraint.locked_params is None:
            return self._locked_params
        return self._locked_params + self.slot_constraint.locked_params

    def get_locomotion_surface(self):
        if self.target is None:
            return
        if not self.get_animation_data()._set_locomotion_surface:
            return
        return self.target

    def last_owning_interaction(self, interaction):
        if interaction not in self.owning_interactions:
            return False
        for owning_interaction in self.owning_interactions:
            if owning_interaction is not interaction and not owning_interaction.is_finishing:
                return False
        return True

    def add_owning_interaction(self, interaction):
        self._owning_interactions.add(interaction)

    def remove_owning_interaction(self, interaction):
        self._owning_interactions.remove(interaction)

    def clear_owning_interactions(self):
        try:
            for interaction in list(self._owning_interactions):
                interaction.remove_liability((OWNS_POSTURE_LIABILITY, self.track))
        finally:
            self._owning_interactions.clear()

    def add_cancel_aop(self, cancel_aop):
        self._active_cancel_aops.add(cancel_aop)

    def kill_cancel_aops(self):
        for owning_interaction in self.owning_interactions:
            if owning_interaction.has_pushed_cancel_aop:
                owning_interaction.cancel(FinishingType.INTERACTION_QUEUE, cancel_reason_msg="PostureOwnership. This interaction had pushed a cancel aopand was waiting to be canceled by that aop's successful completion and corresponding posture change, but a new interaction came in and took ownership over this posture, so it killed that cancel aop.")
        for interaction in self._active_cancel_aops:
            interaction.cancel(FinishingType.INTERACTION_QUEUE, cancel_reason_msg='PostureOwnership. This posture wasgoing to be canceled, but another interaction took ownership over the posture. Most likely the current posture was already valid for the new interaction.')

    def get_idle_behavior(self, setup_asm_override=DEFAULT):
        if self.idle_animation is None:
            logger.error('{} has no idle animation tuning! This tuning is required for all body postures!', self)
            return
        if self.source_interaction is None:
            logger.error('Posture({}) on sim:{} has no source interaction.', self, self.sim, owner='Maxr', trigger_breakpoint=True)
            return
        if self.rerequests_idles or self.sim.last_animation_factory is not None:
            return

        def maybe_idle(timeline):
            if self.sim.last_animation_factory == self.idle_animation.factory:
                return True
            if self.target is not None and self.target.is_sim and not self.target.posture_state.is_carrying(self.sim):
                return True
            self.sim.last_affordance = None
            self.sim.last_animation_factory = self.idle_animation.factory
            if self.owning_interactions and (self.multi_sim or list(self.owning_interactions)[0].target is self.source_interaction.target):
                interaction = list(self.owning_interactions)[0]
            else:
                interaction = self.source_interaction
            additional_animation_blockers = []
            if self.previous_posture is not None:
                previous_posture_target = self.previous_posture.target
                if previous_posture_target is not None and previous_posture_target.is_sim:
                    additional_animation_blockers.append(previous_posture_target)
                if self.target is not None and self.target.is_sim:
                    additional_animation_blockers.append(self.target)
            idle = self.idle_animation(interaction, setup_asm_override=setup_asm_override, additional_blockers=additional_animation_blockers)
            auto_exit = get_auto_exit((self.sim,), asm=idle.get_asm())
            sequence = build_critical_section(auto_exit, idle, flush_all_animations)
            if self.previous_posture is not None:

                def _clear_previous_posture(_):
                    self.previous_posture = None

                sequence = build_critical_section_with_finally(sequence, _clear_previous_posture)
            yield from element_utils.run_child(timeline, sequence)

        return maybe_idle

    def log_info(self, phase, msg=None):
        from sims.sim_log import log_posture
        log_posture(phase, self, msg=msg)

    def _create_asm(self, sim, target, animation_context, is_throwaway):
        self._animation_context = animation_context or AnimationContext(is_throwaway=is_throwaway)
        if not is_throwaway:
            self._animation_context.add_posture_owner(self)
        if sim is not None:
            animation_data = self.get_animation_data(sim=sim, target=target)
            self._asm = animation.asm.create_asm(animation_data._asm_key, self._animation_context)

    @staticmethod
    def _add_posture_transition(source_posture, dest_posture, transition_data):
        Posture._posture_transitions[(source_posture, dest_posture)] = transition_data

    @flexmethod
    def get_provided_postures(cls, inst, surface_target=DEFAULT, concrete=False, species=None):
        if inst is None:
            if species is not None:
                return cls._provided_postures[species]
            provided_postures = PostureManifest()
            for posture_manifest in cls._provided_postures.values():
                provided_postures.update(posture_manifest)
            return provided_postures
        if species is not None:
            provided_postures = inst._provided_postures[species]
        else:
            provided_postures = PostureManifest()
            for posture_manifest in inst._provided_postures.values():
                provided_postures.update(posture_manifest)
        surface_target = inst._resolve_surface_target(surface_target)
        if surface_target is None or surface_target == MATCH_NONE:
            surface_restriction = MATCH_NONE
        elif surface_target == MATCH_ANY:
            surface_restriction = surface_target
        else:
            surface_restriction = surface_target if concrete else AnimationParticipant.SURFACE
        if surface_restriction is not None:
            filter_entry = PostureManifestEntry(MATCH_ANY, MATCH_ANY, MATCH_ANY, MATCH_ANY, MATCH_ANY, MATCH_ANY, surface_restriction, True)
            provided_postures = provided_postures.intersection_single(filter_entry)
        return provided_postures

    def get_asm_registry_text(self):
        registry = []
        for (cache_key, asm_dict) in self._asm_registry.items():
            for asm in asm_dict.values():
                registry.append({'cache_key': str(cache_key), 'asm': '{} :: {}'.format(str(asm), str(asm.current_state))})
        registry.append({'cache_key': 'In Posture', 'asm': '{} :: {}'.format(str(self._asm), str(self._asm.current_state))})
        return registry

    def _resolve_surface_target(self, surface_target):
        if surface_target is DEFAULT:
            return self.surface_target
        return surface_target

    def _resolve_body_target(self, body_target):
        if body_target is DEFAULT:
            return self.body_target
        return body_target

    def invalidate_slot_constraints(self):
        logger.info('Posture {} invalidated slot constraints.', self, owner='rmccord')
        self._slot_constraint = {}

    def _bind(self, sim, target, track):
        if self.sim is sim and self.target is target and self.target_part is None or self.target_part is target and self._track == track:
            return
        target_name = self.get_target_name(sim=sim, target=target)
        if track == PostureTrack.BODY:
            part_suffix = self.get_part_suffix()
            for asm in self._asms_with_posture_info:
                if not asm.remove_virtual_actor(target_name, self.target, suffix=part_suffix):
                    logger.error('Failed to remove previously-bound virtual posture container {} from asm {} on posture {}.', self.target, asm, self)
        if self.target is not None and sim is not None:
            self._sim = sim.ref()
        else:
            self._sim = None
        self._intersection = None
        self._asm_registry.clear()
        self._asms_with_posture_info.clear()
        if target is not None:
            if target_name is not None and target is not sim:
                (route_type, _) = target.route_target
                if route_type != RouteTargetType.NONE:
                    if self._target is not None and (self._target() is not None and self._target().parts is not None) and target in self._target().parts:
                        self._target_part = target.ref()
                    else:
                        self._target_part = None
                        self._target = target.ref()
            else:
                self._target = target.ref()
        else:
            self._target_part = None
            self._target = None
        if track is not None:
            self._track = track
        else:
            self._track = None
        self._slot_constraint = {}

    def rebind(self, target, animation_context=None):
        self._release_animation_context()
        self._create_asm(self.sim, target, animation_context, False)
        self._bind(self.sim, target, self.track)

    def reset(self):
        self._reset_occult()
        if self._saved_exit_clothing_change is not None:
            self.sim.sim_info.set_current_outfit(self._saved_exit_clothing_change)
            self._saved_exit_clothing_change = None
        resolver = SingleSimResolver(self.sim.sim_info)
        for loot_action in self.loot_actions_on_exit:
            loot_action.apply_to_resolver(resolver)
        self._entry_anim_complete = False
        self._exit_anim_complete = False
        self._release_animation_context()
        self._source_interaction = None
        if self._appearance_modifier_active:
            self.sim.sim_info.appearance_tracker.remove_appearance_modifiers(self.posture_type.guid64, source=self.name)
            self._appearance_modifier_active = False

    def _reset_occult(self):
        occult_tracker = self.sim.sim_info.occult_tracker
        occult_form_before_reset = occult_tracker.get_current_occult_types()
        if self.sim.posture_state.body is self:
            if self._entry_occult_switch_processed:
                if occult_tracker.has_occult_type(self.switch_occult.exit.exit_occult):
                    occult_tracker.switch_to_occult_type(self.switch_occult.exit.exit_occult)
                self._entry_occult_switch_processed = False
            elif self.fallback_occult_on_posture_reset is not None and occult_tracker.has_occult_type(self.fallback_occult_on_posture_reset):
                occult_tracker.switch_to_occult_type(self.fallback_occult_on_posture_reset)
            occult_tracker.validate_appropriate_occult(self.sim, occult_form_before_reset)

    def _release_animation_context(self):
        if self._animation_context is not None:
            self._animation_context.remove_posture_owner(self)
            self._animation_context = None

    def kickstart_gen(self, timeline, posture_state, routing_surface, target_override=None):
        if PostureTrack.is_carry(self.track):
            is_body = False
            self.asm.set_parameter('location', 'inventory')
        else:
            is_body = True
            self.source_interaction = self.sim.create_default_si(target_override=target_override)
            if self.mobile:
                target_override = None
        idle_arb = animation.arb.Arb()
        self.append_transition_to_arb(idle_arb, None, target_override=target_override)
        self.append_idle_to_arb(idle_arb)
        begin_element = self.get_begin(idle_arb, posture_state, routing_surface)
        yield from element_utils.run_child(timeline, begin_element)
        if is_body:
            yield from self.kickstart_source_interaction_gen(timeline)

    def kickstart_source_interaction_gen(self, timeline):
        default_si = self.source_interaction
        default_si.sim.ui_manager.add_queued_interaction(default_si)
        yield from default_si.prepare_gen(timeline)
        yield from default_si.enter_si_gen(timeline)
        yield from default_si.setup_gen(timeline)
        result = yield from default_si.perform_gen(timeline)
        if not result:
            raise RuntimeError('Sim: {} failed to enter default si: {}'.format(self, default_si))

    def get_registered_asm(self, animation_context, asm_key, setup_asm_func, use_cache=True, cache_key=DEFAULT, interaction=None, posture_manifest_overrides=None, **kwargs):
        dict_key = animation_context if cache_key is DEFAULT else cache_key
        if use_cache:
            asm_dict = self._asm_registry[dict_key]
            asm = asm_dict.get(asm_key)
            if asm is None:
                asm = animation.asm.create_asm(asm_key, context=animation_context, posture_manifest_overrides=posture_manifest_overrides)
                if interaction is not None:
                    asm.on_state_changed_events.append(interaction.on_asm_state_changed)
                asm_dict[asm_key] = asm
        else:
            asm = animation.asm.create_asm(asm_key, context=animation_context)
            if interaction is not None:
                asm.on_state_changed_events.append(interaction.on_asm_state_changed)
        if asm.current_state == 'exit':
            asm.set_current_state('entry')
        if setup_asm_func is not None:
            result = setup_asm_func(asm)
            if not result:
                logger.error('Failed to setup ASM: {}, {}', asm, result, owner='rmccord')
                return
        return asm

    def remove_from_cache(self, cache_key):
        if cache_key in self._asm_registry:
            for asm in self._asm_registry[cache_key].values():
                del asm._on_state_changed_events[:]
            del self._asm_registry[cache_key]

    def _create_primitive(self, animate_in, dest_state, routing_surface):
        return PosturePrimitive(self, animate_in, dest_state, self._context, routing_surface)

    def _on_reset(self):
        self._primitive = None

    @flexmethod
    def get_animation_data(cls, inst, sim=DEFAULT, target=DEFAULT):
        sim = inst.sim if sim is DEFAULT else sim
        target = inst.target if target is DEFAULT else target
        animation_data = cls._animation_data.get_animation_data(sim, target)
        if animation_data is None:
            if sim.species != Species.HUMAN:
                inst_or_cls = inst if inst is not None else cls
                return inst_or_cls.get_animation_data(GLOBAL_STUB_ACTOR, GLOBAL_STUB_TARGET)
            raise KeyError('Missing animations for posture {}. Missing animation data for {}.'.format(sim.species, cls))
        return animation_data

    @classmethod
    def is_animation_available_for_species(cls, species):
        return species in cls.get_animation_species()

    @classmethod
    def get_animation_species(cls):
        return cls._animation_data.get_animation_species()

    def get_slot_offset_locked_params(self, anim_overrides=None):
        locked_params = self._locked_params
        if anim_overrides is not None:
            locked_params += anim_overrides.params
        return locked_params

    @flexmethod
    def get_carry_constraint(cls, inst, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        animation_data = inst_or_cls.get_animation_data(**kwargs)
        return animation_data._carry_constraint

    def build_slot_constraint(self, posture_state_spec=DEFAULT):
        if self.target is not None and PostureTrack.is_body(self.track):
            return interactions.constraints.RequiredSlot.create_slot_constraint(self, posture_state_spec=posture_state_spec)

    @property
    def slot_constraint_simple(self):
        if self.sim.species not in self._slot_constraint:
            self._slot_constraint[self.sim.species] = self.build_slot_constraint(posture_state_spec=None)
        return self._slot_constraint[self.sim.species]

    @property
    def slot_constraint(self):
        if self.sim.species not in self._slot_constraint:
            self._slot_constraint[self.sim.species] = self.build_slot_constraint()
        return self._slot_constraint[self.sim.species]

    def _setup_asm_container_parameter(self, asm, target, actor_name, part_suffix, target_name=None):
        if asm in self._asms_with_posture_info:
            return True
        if asm is not self.asm and not self._apply_target_to_interaction_asms:
            return True
        if target_name is None:
            target_name = self.get_target_name(target=target)
        result = False
        if target_name is not None:
            result = asm.add_potentially_virtual_actor(actor_name, self.sim, target_name, target, part_suffix, target_participant=AnimationParticipant.CONTAINER)
            if not self._setup_custom_posture_target_name(asm, target):
                logger.error('Failed to set custom posture target {}', target)
                result = False
        if target is not None and result:
            self._asms_with_posture_info.add(asm)
        return result

    def _setup_custom_posture_target_name(self, asm, target):
        _custom_target_name = target.custom_posture_target_name
        if _custom_target_name in asm.actors:
            (_custom_target_actor, _) = asm.get_actor_and_suffix(_custom_target_name)
            if _custom_target_actor is None:
                return asm.set_actor(target.custom_posture_target_name, target, suffix=None, actor_participant=AnimationParticipant.CONTAINER)
        return True

    def _setup_asm_carry_parameter(self, asm, target):
        pass

    def get_part_suffix(self, target=DEFAULT):
        if target is DEFAULT:
            target = self.target
        if target is not None:
            return target.part_suffix

    def setup_asm_posture(self, asm, sim, target, locked_params=frozendict(), actor_param_name=DEFAULT):
        if actor_param_name is DEFAULT:
            actor_param_name = self._actor_param_name
        if asm is None:
            return TestResult(False, '{}: Attempting to setup an asm whose value is None.'.format(self))
        if sim is None:
            return TestResult(False, '{}: Attempting to setup an asm {} on a sim whose value is None.'.format(self, asm))
        if not asm.set_actor(actor_param_name, sim, actor_participant=AnimationParticipant.ACTOR):
            return TestResult(False, '{}: Failed to set actor sim: {} on asm {}'.format(self, actor_param_name, asm))
        target_name = self.get_target_name(target=target)
        if target_name is not None and target is not None:
            if target.is_part:
                is_mirrored = target.is_mirrored()
                if is_mirrored is not None:
                    locked_params += {'isMirrored': is_mirrored}
            part_suffix = self.get_part_suffix(target=target)
            if not self._setup_asm_container_parameter(asm, target, actor_param_name, part_suffix):
                return TestResult(False, '{}: Failed to set actor target: {} on asm {}'.format(self, target_name, asm))
        jig_name = self.get_animation_data()._jig_name
        if jig_name is not None and self._jig_instance is not None and not self._setup_asm_container_parameter(asm, self._jig_instance, actor_param_name, None, target_name=jig_name):
            return TestResult(False, '{}: Failed to set actor jig: {} on asm {}'.format(self, self._jig_instance, asm))
        if not PostureTrack.is_body(self.track):
            self._update_non_body_posture_asm()
            sim.on_posture_event.append(self._update_on_posture_event)
        if locked_params:
            virtual_actor_map = {self.get_target_name(): self.target}
            asm.update_locked_params(locked_params, virtual_actor_map)
        sim.set_mood_asm_parameter(asm, actor_param_name)
        sim.set_trait_asm_parameters(asm, actor_param_name)
        self._setup_asm_carry_parameter(asm, target)
        return True

    def _update_on_posture_event(self, change, dest_state, track, old_value, new_value):
        if track == PostureTrack.BODY and track != self.track:
            if new_value is not None:
                try:
                    self._update_non_body_posture_asm()
                except:
                    pass
        elif new_value is not self and new_value.track == self.track:
            self.sim.on_posture_event.remove(self._update_on_posture_event)

    def _update_non_body_posture_asm(self):
        if self.sim.posture.target is not None:
            previous_target_name = self.sim.posture.get_target_name()
            (previous_target, previous_suffix) = self.asm.get_virtual_actor_and_suffix(self._actor_param_name, previous_target_name)
            if previous_target is not None:
                self.asm.remove_virtual_actor(previous_target_name, previous_target, previous_suffix)
        return self.sim.posture.setup_asm_interaction(self.asm, self.sim, self.target, self._actor_param_name, self.get_target_name())

    def _setup_asm_interaction_add_posture_info(self, asm, sim, target, actor_name, target_name, carry_target, carry_target_name, surface_target=DEFAULT, carry_track=DEFAULT):

        def set_posture_param(posture_param_str, carry_param_str, carry_actor_name, surface_actor_name):
            if not asm.set_actor_parameter(actor_name, sim, 'posture', posture_param_str):
                if not asm.set_parameter('posture', posture_param_str):
                    return False
                else:
                    logger.warn('Backwards compatibility with old posture parameter required by {}', asm.name)
                    if not asm.set_actor_parameter(actor_name, sim, PARAM_CARRY_STATE, carry_param_str):
                        asm.set_parameter('carry', carry_param_str)
                    asm.set_parameter('isMirrored', self.is_mirrored)
                    if carry_actor_name is not None:
                        if target_name == carry_actor_name and target is not None:
                            set_carry_track_param_if_needed(asm, sim, target_name, target, carry_track=carry_track)
                        if carry_target_name == carry_actor_name and carry_target is not None:
                            set_carry_track_param_if_needed(asm, sim, carry_target_name, carry_target, carry_track=carry_track)
                    if surface_actor_name is not None:
                        _surface_target = self._resolve_surface_target(surface_target)
                        if _surface_target:
                            asm.add_potentially_virtual_actor(actor_name, sim, surface_actor_name, _surface_target, target_participant=AnimationParticipant.SURFACE)
                        else:
                            return False
            if not asm.set_actor_parameter(actor_name, sim, PARAM_CARRY_STATE, carry_param_str):
                asm.set_parameter('carry', carry_param_str)
            asm.set_parameter('isMirrored', self.is_mirrored)
            if carry_actor_name is not None:
                if target_name == carry_actor_name and target is not None:
                    set_carry_track_param_if_needed(asm, sim, target_name, target, carry_track=carry_track)
                if carry_target_name == carry_actor_name and carry_target is not None:
                    set_carry_track_param_if_needed(asm, sim, carry_target_name, carry_target, carry_track=carry_track)
            if surface_actor_name is not None:
                _surface_target = self._resolve_surface_target(surface_target)
                if _surface_target:
                    asm.add_potentially_virtual_actor(actor_name, sim, surface_actor_name, _surface_target, target_participant=AnimationParticipant.SURFACE)
                else:
                    return False
            return True

        def build_carry_str(carry_state):
            if carry_state[0]:
                if carry_state[1]:
                    return 'both'
                return 'left'
            elif carry_state[1]:
                return 'right'
            return 'none'

        def setup_asm_container_parameter(chosen_posture_type):
            jig_name = self.get_animation_data()._jig_name
            if jig_name is not None and self._jig_instance is not None and not self._setup_asm_container_parameter(asm, self._jig_instance, actor_name, None, target_name=jig_name):
                return TestResult(False, '{}: Failed to set actor jig: {} on asm {}'.format(self, self._jig_instance, asm))
            if self.target is None:
                return True
            container_name = chosen_posture_type.get_target_name(sim=sim, target=self.target)
            if not container_name:
                return True
            part_suffix = self.get_part_suffix()
            if self._setup_asm_container_parameter(asm, self.target, actor_name, part_suffix, target_name=container_name):
                return True
            return TestResult(False, 'Failed to set actor {} as container parameter {} on asm {} for {}'.format(self.target, actor_name, asm, chosen_posture_type))

        carry_state = sim.posture_state.get_carry_state()
        supported_postures = asm.get_supported_postures_for_actor(actor_name)
        if not supported_postures:
            return True
        filtered_supported_postures = self.sim.filter_supported_postures(supported_postures)
        if surface_target is DEFAULT:
            surface_target = self._resolve_surface_target(surface_target)
            if surface_target is not None:
                surface_target_provided = MATCH_ANY
            else:
                surface_target_provided = MATCH_NONE
        elif surface_target is not None:
            surface_target_provided = MATCH_ANY
        else:
            surface_target_provided = MATCH_NONE
        result = False
        provided_postures = self.get_provided_postures(surface_target=surface_target_provided)
        best_supported_posture = get_best_supported_posture(provided_postures, filtered_supported_postures, carry_state)
        if best_supported_posture is None:
            return TestResult(False, 'Failed to find supported posture for actor {} on {} for posture ({}),\nInteraction info claims this should work.\n  Source interaction ({}),\n  Carry ({}).\n  Surface Target Provided: {}\n  Provided Posture: {}\n  Supported Postures: {}\n  Filted Supported Postures: {}\n', sim, asm, self, self.source_interaction, carry_state, surface_target_provided, provided_postures, supported_postures, filtered_supported_postures)
        carry_param_str = build_carry_str(carry_state)
        carry_actor_name = best_supported_posture.carry_target
        surface_actor_name = best_supported_posture.surface_target
        if not isinstance(surface_actor_name, str):
            surface_actor_name = None
        param_str_specific = best_supported_posture.posture_param_value_specific
        if set_posture_param(param_str_specific, carry_param_str, carry_actor_name, surface_actor_name):
            if best_supported_posture.is_overlay:
                return True
            result = setup_asm_container_parameter(best_supported_posture.posture_type_specific)
            if result:
                return True
        param_str_family = best_supported_posture.posture_param_value_family
        if param_str_specific and param_str_family and set_posture_param(param_str_family, carry_param_str, carry_actor_name, surface_actor_name):
            if best_supported_posture.is_overlay:
                return True
            else:
                return setup_asm_container_parameter(best_supported_posture.posture_type_family)
        return result

    def setup_asm_interaction(self, asm, sim, target, actor_name, target_name, carry_target=None, carry_target_name=None, create_target_name=None, surface_target=DEFAULT, carry_track=DEFAULT, actor_participant=AnimationParticipant.ACTOR, invalid_expected=False, base_object=None, base_object_name=None):
        if target_name is not None and (target_name == self.get_target_name() and (target is not None and self.target is not None)) and target.id != self.target.id:
            if target.is_sim and target.posture is not None and target.posture.target.id == self.target.id:
                target = target.posture.target
            else:
                if not invalid_expected:
                    logger.error('Animation targets a different object than its posture, but both use the same actor name for the object. This is impossible to resolve. Actor name: {}, posture target: {}, interaction target: {}', target_name, target, self.target)
                return TestResult(False, "Animation targets different object than it's posture.")
        if actor_name not in asm._virtual_actors and not (asm.set_actor(actor_name, sim, actor_participant=actor_participant) or asm.add_virtual_actor(actor_name, sim)):
            logger.error('Failed to set actor: {0} on asm {1}', actor_name, asm)
            return TestResult(False, 'Failed to set actor: {0} on asm {1}'.format(actor_name, asm))
        if sim.asm_auto_exit.apply_carry_interaction_mask:
            asm._set_actor_trackmask_override(actor_name, 50000, 'Trackmask_CarryInteraction')
        if target is not None and target_name is not None:
            from sims.sim import Sim
            target_definition = asm.get_actor_definition(target_name)
            if target_definition.is_virtual or isinstance(target, Sim):
                result = target.posture.setup_asm_interaction(asm, target, None, target_name, None, actor_participant=AnimationParticipant.TARGET)
                if not result:
                    return result
            else:
                asm.add_potentially_virtual_actor(actor_name, sim, target_name, target, target_participant=AnimationParticipant.TARGET)
                anim_overrides = target.get_anim_overrides(target_name)
                if anim_overrides is not None and anim_overrides.params:
                    virtual_actor_target_name = self.get_target_name(sim=sim, target=target) or target_name
                    virtual_actor_map = {virtual_actor_target_name: self.target}
                    asm.update_locked_params(anim_overrides.params, virtual_actor_map)
            if not self._setup_custom_posture_target_name(asm, target):
                logger.error('Unable to setup custom posture target name for {} on {}', target, asm)
        base_object = base_object if base_object is not None else self.target
        if base_object is not None and base_object_name is not None:
            asm.add_potentially_virtual_actor(actor_name, sim, base_object_name, base_object, target_participant=AnimationParticipant.BASE_OBJECT)
        _carry_target_name = carry_target_name or create_target_name
        if carry_target is not None and _carry_target_name is not None:
            asm.add_potentially_virtual_actor(actor_name, sim, _carry_target_name, carry_target, target_participant=AnimationParticipant.CARRY_TARGET)
        result = self._setup_asm_interaction_add_posture_info(asm, sim, target, actor_name, target_name, carry_target, carry_target_name, surface_target, carry_track)
        if not result:
            return result
        return True

    def get_begin(self, animate_in, dest_state, routing_surface):
        if self._primitive is not None:
            raise RuntimeError('Posture Entry({}) called multiple times without a paired exit.'.format(self))
        self._primitive = self._create_primitive(animate_in, dest_state, routing_surface)
        self._primitive_created = True
        return self._primitive.next_stage()

    def begin(self, animate_in, dest_state, context, routing_surface):
        self._context = context

        def _do_begin(timeline):
            logger.debug('{} begin Posture: {}', self.sim, self)
            begin = self.get_begin(animate_in, dest_state, routing_surface)
            result = yield from element_utils.run_child(timeline, begin)
            return result

        return _do_begin

    def get_end(self):
        if self._primitive is None:
            sim = self.sim
            if sim is not None:
                runtime_error_string = f'Posture Exit({self}) called multiple times without a paired entry or never called (PrimitiveCreated: {self._primitive_created}). Sim ID: {sim.id}'
            else:
                runtime_error_string = f'Posture Exit({self}) called multiple times without a paired entry or never called (PrimitiveCreated: {self._primitive_created}). Sim has already been cleaned up or not set'
            raise RuntimeError(runtime_error_string)
        exit_behavior = self._primitive.next_stage()
        self._primitive = None
        return exit_behavior

    def end(self):

        def _do_end(timeline):
            logger.debug('{} end Posture: {}', self.sim, self)
            end = self.get_end()
            result = yield from element_utils.run_child(timeline, end)
            return result

        return _do_end

    def get_create_jig(self):

        def create_and_place_jig(_):
            if self.jig is None:
                return
            has_slot_constraints = self.slot_constraint is not None and self.slot_constraint is not ANYWHERE
            if self.target is not None and has_slot_constraints:
                for constraint in self.slot_constraint:
                    if self.target.provided_routing_surface is not None:
                        jig_routing_surface = self.target.provided_routing_surface
                    else:
                        jig_routing_surface = self.target.routing_surface
                    jig_transform = constraint.containment_transform
                    break
            else:
                jig_routing_surface = self.sim.routing_surface
                jig_transform = self.sim.transform
            self._jig_instance = objects.system.create_object(self.jig)
            self._jig_instance.move_to(transform=jig_transform, routing_surface=jig_routing_surface)
            self.sim.routing_context.ignore_footprint_contour(self._jig_instance.routing_context.object_footprint_id)

        return create_and_place_jig

    def get_destroy_jig(self):

        def destroy_jig(_):
            if self._jig_instance is None:
                return
            self.sim.routing_context.remove_footprint_contour_override(self._jig_instance.routing_context.object_footprint_id)
            self._jig_instance.destroy(source=self, cause='Destroying jig for posture.')
            self._jig_instance = None

        return destroy_jig

    def add_transition_extras(self, sequence, *, arb):
        return (self.get_create_jig(), sequence)

    def get_locked_params(self, source_posture):
        if source_posture is None:
            return self._locked_params
        updates = {TRANSITION_POSTURE_PARAM_NAME: source_posture.name}
        if source_posture.target is None:
            return self._locked_params + updates
        if self.target.is_part:
            if self.target.is_mirrored(source_posture.target):
                direction = 'fromSimLeft'
            else:
                direction = 'fromSimRight'
            updates['direction'] = direction
            part_suffix = source_posture.target.part_suffix
            if part_suffix is not None:
                updates['subrootFrom'] = part_suffix
            part_suffix = self.target.part_suffix
            if part_suffix is not None:
                updates['subrootTo'] = part_suffix
        return self._locked_params + updates

    def append_transition_to_arb(self, arb, source_posture, locked_params=frozendict(), target_override=None, **kwargs):
        if not self._entry_anim_complete:
            locked_params += self.get_locked_params(source_posture)
            if source_posture is not None:
                locked_params += {TRANSITION_POSTURE_PARAM_NAME: source_posture.name}
            result = self.setup_asm_posture(self.asm, self.sim, target_override or self.target, locked_params=locked_params)
            if not result:
                logger.error('Failed to setup the asm for the posture {}. {}', self, result)
                return
            self.add_appearance_modifier_entry_event(arb)
            self.add_switch_occult_entry_event(arb)
            self._setup_asm_target_for_transition(source_posture)
            self.asm.request(self._enter_state_name, arb)
            linked_posture = self.linked_posture
            if linked_posture is not None:
                locked_params = linked_posture.get_locked_params(source_posture)
                linked_posture.setup_asm_posture(linked_posture._asm, linked_posture.sim, linked_posture.target, locked_params=locked_params)
                if not self.multi_sim:
                    linked_posture._asm.request(linked_posture._enter_state_name, arb)
            self._entry_anim_complete = True

    def append_idle_to_arb(self, arb):
        self.asm.request(self._state_name, arb)
        if self._linked_posture is not None:
            self._linked_posture.append_idle_to_arb(arb)

    def append_exit_to_arb(self, arb, dest_state, dest_posture, var_map, locked_params=frozendict(), target_override=None):
        if not self._exit_anim_complete:
            if target_override is not None:
                self._bind(self.sim, target_override, self.track)
                self.asm.set_current_state(self._state_name)
            if target_override is not None and not self.setup_asm_posture(self.asm, self.sim, target_override or self.target, locked_params=locked_params):
                logger.error('Failed to setup the asm for the posture {}', self)
                return
            self._setup_asm_target_for_transition(dest_posture)
            self.add_outfit_exit_event(arb)
            self.add_appearance_modifier_exit_event(arb)
            self.add_switch_occult_exit_event(arb)
            resolver = SingleSimResolver(self.sim.sim_info)
            for loot_action in self.loot_actions_on_exit:
                loot_action.apply_to_resolver(resolver)
            locked_params += self._locked_params
            if dest_posture is not None:
                locked_params += {TRANSITION_POSTURE_PARAM_NAME: dest_posture.name}
            if locked_params:
                virtual_actor_map = {self.get_target_name(): self.target}
                self.asm.update_locked_params(locked_params, virtual_actor_map)
            try:
                self.asm.request(self._exit_state_name, arb)
            except RuntimeError as err:
                source_interaction = self.source_interaction
                running_interaction = self.sim.queue.running
                additional_message = '\nsource_interaction = {}\nrunning interaction = {}'.format(source_interaction, running_interaction)
                sim_of_interest = self.sim
                if running_interaction.sim is not self.sim:
                    additional_message += '\nPosture Sim different than Running interaction sim'
                    sim_of_interest = running_interaction.sim
                mixers = tuple(sim_of_interest.queue.mixer_interactions_gen())
                if running_interaction is not None and running_interaction.is_social and mixers:
                    additional_message += '\nRunning Interaction Mixers:'
                    for mixer in mixers:
                        additional_message += '\n    {}'.format(mixer)
                err.args = (err.args[0] + additional_message,)
                raise
            self._exit_anim_complete = True

    def _setup_asm_target_for_transition(self, transition_posture):
        if transition_posture is None:
            return True
        transition_posture_target_name = transition_posture.get_target_name()
        if transition_posture_target_name is None or transition_posture_target_name == self.get_target_name():
            return True
        if transition_posture_target_name in self.asm.actors:
            actor_name = self.asm.get_actor_name_from_id(transition_posture.sim.id)
            if not actor_name:
                logger.error('Failed to setup target container for transition posture {}', transition_posture)
                return False
            else:
                (previous_target, previous_suffix) = self.asm.get_virtual_actor_and_suffix(actor_name, transition_posture_target_name)
                if previous_target is not None:
                    self.asm.remove_virtual_actor(transition_posture_target_name, previous_target, previous_suffix)
                if not transition_posture._setup_asm_container_parameter(self.asm, transition_posture.target, actor_name, transition_posture.get_part_suffix()):
                    logger.error('Failed to setup target container {} on {} from transition posture {}', transition_posture_target_name, self, transition_posture)
                    return False
        return True

    @flexmethod
    def _get_override_outfit_change(cls, inst, sim_info):
        inst_or_cls = inst if inst is not None else cls
        for entry in inst_or_cls.override_outfit_changes:
            if not entry.tests:
                return entry.outfit_change
            resolver = SingleSimResolver(sim_info)
            if entry.tests.run_tests(resolver):
                return entry.outfit_change

    @flexmethod
    def post_route_clothing_change(cls, inst, interaction, do_spin=True, **kwargs):
        if inst is None:
            inst_or_cls = cls
            sim_info = interaction.sim.sim_info
        else:
            inst_or_cls = inst
            sim_info = inst.sim.sim_info
        si_outfit_change = interaction.outfit_change
        if si_outfit_change is not None and si_outfit_change.posture_outfit_change_overrides is not None:
            overrides = si_outfit_change.posture_outfit_change_overrides.get(inst_or_cls.posture_type)
            if overrides is not None:
                entry_outfit = overrides.get_on_entry_outfit(interaction)
                if entry_outfit is not None:
                    return overrides.get_on_entry_change(interaction, do_spin=do_spin, **kwargs)
        override_outfit_change = inst_or_cls._get_override_outfit_change(sim_info)
        if override_outfit_change is not None:
            return override_outfit_change.get_on_entry_change(interaction, do_spin=do_spin, **kwargs)
        elif inst_or_cls.outfit_change is not None:
            return inst_or_cls.outfit_change.get_on_entry_change(interaction, do_spin=do_spin, **kwargs)

    def add_appearance_modifier_exit_event(self, arb):
        if self.appearance_modifier is not None:

            def _remove_appearance_modifier(*_, **__):
                self.sim.sim_info.appearance_tracker.remove_appearance_modifiers(self.posture_type.guid64, source=self.name)

            arb.register_event_handler(_remove_appearance_modifier, handler_id=self.appearance_modifier.exit_xevt)

    def add_appearance_modifier_entry_event(self, arb):
        if self.appearance_modifier is not None:

            def _apply_appearance_modifier(*_, **__):
                self._appearance_modifier_active = True
                new_appearance_modifier = self.appearance_modifier.modifier
                self.sim.sim_info.appearance_tracker.add_appearance_modifiers(new_appearance_modifier.appearance_modifiers, self.posture_type.guid64, new_appearance_modifier.priority, new_appearance_modifier.apply_to_all_outfits, source=self.name)

            arb.register_event_handler(_apply_appearance_modifier, handler_id=self.appearance_modifier.entry_xevt)

    def add_switch_occult_exit_event(self, arb):
        if self.switch_occult is not None:

            def _exit_switch_occult(*_, **__):
                if self.sim.sim_info.occult_tracker.has_occult_type(self.switch_occult.exit.exit_occult):
                    self.sim.sim_info.occult_tracker.switch_to_occult_type(self.switch_occult.exit.exit_occult)

            arb.register_event_handler(_exit_switch_occult, handler_id=self.switch_occult.exit.exit_xevt)

    def pretend_entry_occult_switch_processed(self):
        self._entry_occult_switch_processed = True

    def add_switch_occult_entry_event(self, arb):
        if self.switch_occult is not None:

            def _entry_switch_occult(*_, **__):
                self._entry_occult_switch_processed = True
                if self.sim.sim_info.occult_tracker.has_occult_type(self.switch_occult.entry.entry_occult):
                    self.sim.sim_info.occult_tracker.switch_to_occult_type(self.switch_occult.entry.entry_occult)

            arb.register_event_handler(_entry_switch_occult, handler_id=self.switch_occult.entry.entry_xevt)

    def add_outfit_exit_event(self, arb):
        if self.outfit_exit_xevt is not None:

            def _do_outfit_change(*_, **__):
                if self._saved_exit_clothing_change is None:
                    return
                if self.sim.get_current_outfit() != self._saved_exit_clothing_change:
                    self.sim.set_current_outfit(self._saved_exit_clothing_change)
                    self._saved_exit_clothing_change = None

            arb.register_event_handler(_do_outfit_change, handler_id=self.outfit_exit_xevt)

    def transfer_exit_clothing_change(self, aspect):
        if self is aspect:
            return
        if aspect.outfit_exit_xevt is None:
            self._saved_exit_clothing_change = aspect.saved_exit_clothing_change
            aspect.saved_exit_clothing_change = None

    def prepare_exit_clothing_change(self, interaction, **kwargs):
        si_outfit_change = interaction.outfit_change
        if si_outfit_change is not None and si_outfit_change.posture_outfit_change_overrides is not None:
            overrides = si_outfit_change.posture_outfit_change_overrides.get(self.posture_type)
            if overrides is not None:
                exit_outfit = overrides.get_on_exit_outfit(interaction, **kwargs)
                if exit_outfit is not None:
                    self._saved_exit_clothing_change = overrides.get_on_exit_outfit(interaction, **kwargs)
                    return
        override_outfit_change = self._get_override_outfit_change(self.sim.sim_info)
        if override_outfit_change is not None:
            self._saved_exit_clothing_change = override_outfit_change.get_on_exit_outfit(interaction, **kwargs)
        if self._saved_exit_clothing_change is None:
            self._saved_exit_clothing_change = self.outfit_change.get_on_exit_outfit(interaction, **kwargs)

    def has_exit_change(self, interaction, **kwargs):
        si_outfit_change = interaction.outfit_change
        if si_outfit_change is not None and si_outfit_change.posture_outfit_change_overrides is not None:
            overrides = si_outfit_change.posture_outfit_change_overrides.get(self.posture_type)
            if overrides is not None and overrides.has_exit_change(interaction, **kwargs):
                return True
            elif self.outfit_change and self.outfit_change.get_on_exit_outfit(interaction):
                return self.outfit_change.has_exit_change(interaction, **kwargs)
        elif self.outfit_change and self.outfit_change.get_on_exit_outfit(interaction):
            return self.outfit_change.has_exit_change(interaction, **kwargs)
        return False

    def exit_clothing_change(self, interaction, *, sim_info=DEFAULT, do_spin=True, **kwargs):
        if self._saved_exit_clothing_change is None or interaction is None:
            return
        sim_info = interaction.sim.sim_info if sim_info is DEFAULT else sim_info
        return build_critical_section(sim_info.get_change_outfit_element_and_archive_change_reason(self._saved_exit_clothing_change, do_spin=do_spin, interaction=interaction, change_reason=self.name), flush_all_animations)

    def ensure_exit_clothing_change_application(self):
        if self._saved_exit_clothing_change is not None:
            if self.sim.sim_info.get_current_outfit() != self._saved_exit_clothing_change:
                self.sim.sim_info.set_current_outfit(self._saved_exit_clothing_change)
            self._saved_exit_clothing_change = None

    def get_target_and_target_name(self):
        if self.target is not None and self.get_target_name() is not None:
            return (self.target, self.get_target_name())
        elif self._jig_instance is not None and self.get_animation_data()._jig_name is not None:
            return (self._jig_instance, self.get_animation_data()._jig_name)
        return (None, None)

    def get_occult_for_posture_reset(self):
        if self._entry_occult_switch_processed:
            return self.switch_occult.exit.exit_occult
        else:
            return self.fallback_occult_on_posture_reset
