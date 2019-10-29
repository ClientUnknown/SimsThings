import collectionsfrom buffs.tunable import TunableBuffReferencefrom game_effect_modifier.base_game_effect_modifier import BaseGameEffectModifierfrom game_effect_modifier.game_effect_type import GameEffectTypefrom interactions import ParticipantTypefrom objects.components.statistic_types import StatisticComponentGlobalTuningfrom sims4.collections import FrozenAttributeDict, RestrictedFrozenAttributeDictfrom sims4.repr_utils import standard_auto_reprfrom sims4.tuning.tunable import TunableMapping, Tunable, TunableList, TunableSingletonFactory, TunableEnumEntry, TunableReference, OptionalTunable, TunableTuple, TunableEnumFlags, TunableVariant, TunableRange, TunableSetfrom sims4.tuning.tunable_base import FilterTagfrom singletons import DEFAULTfrom snippets import TunableAffordanceFilterSnippetfrom statistics.base_statistic import StatisticChangeDirectionfrom statistics.commodity import Commodityfrom statistics.life_skill_statistic import LifeSkillStatisticfrom statistics.static_commodity import StaticCommodityfrom statistics.tunable import CommodityDecayModifierMapping, StatisticCategoryModifierMappingfrom tag import Tagimport enumimport relationships.relationship_trackimport servicesimport sims4.logimport sims4.resourcesimport snippetsimport statistics.commodityimport statistics.skillimport statistics.statisticimport taglogger = sims4.log.Logger('AutonomyModifiers', default_owner='rfleig')
class SuperAffordanceSuppression(enum.Int):
    AUTONOMOUS_ONLY = 0
    USER_DIRECTED = 1
    USE_AFFORDANCE_COMPATIBILITY_AND_WHITELIST = 2

class OffLotAutonomyRules(enum.Int):
    DEFAULT = 0
    ON_LOT_ONLY = 1
    OFF_LOT_ONLY = 2
    UNLIMITED = 3
    RESTRICTED = 4
    ANCHORED = 5
SkillTagMultiplier = collections.namedtuple('SkillTagMultiplier', ['multiplier', 'apply_direction'])
class TunableOffLotAutonomy(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(description="\n                The rules to apply for how autonomy handle on-lot and off-lot\n                targets.\n                \n                DEFAULT:\n                    Off-lot sims who are outside the lot's tolerance will not autonomously perform\n                    interactions on the lot. Sims will only autonomously perform off-lot\n                    interactions within their off-lot radius.\n                ON_LOT_ONLY:\n                    Sims will only consider targets on the active lot.\n                OFF_LOT_ONLY:\n                    Sims will only consider targets that are off the active lot.\n                UNLIMITED:\n                    Sims will consider all objects regardless of on/off lot status.\n                FESTIVAL:\n                    Sims will consider all objects within the festival area.\n                ANCHORED:\n                    Sims will only consider objects within a tuned radius of\n                    autonomy anchor objects. Anchor objects can be objects that\n                    match a tag, sims that match a buff, or set by external\n                    systems.\n                ", default_behavior=TunableTuple(description="\n                    Off-lot sims who are outside the lot's tolerance will not autonomously perform\n                    interactions on the lot. Sims will only autonomously perform off-lot\n                    interactions within their off-lot radius.\n                    ", locked_args={'rule': OffLotAutonomyRules.DEFAULT, 'anchor_tag': None, 'anchor_buff': None}, tolerance=Tunable(description='\n                        This is how many meters the Sim can be off of the lot while still being \n                        considered on the lot for the purposes of autonomy.  For example, if \n                        this is set to 5, the sim can be 5 meters from the edge of the lot and \n                        still consider all the objects on the lot for autonomy.  If the sim were \n                        to step 6 meters from the lot, the sim would be considered off the lot \n                        and would only score off-lot objects that are within the off lot radius.\n                        ', tunable_type=float, default=7.5), radius=TunableRange(description='\n                        The radius around the sim in which he will consider off-lot objects.  If it is \n                        0, the Sim will not consider off-lot objects at all.  This is not recommended \n                        since it will keep them from running any interactions unless they are already \n                        within the tolerance for that lot (set with Off Lot Tolerance).\n                        ', tunable_type=float, default=25, minimum=0)), on_lot_only=TunableTuple(description='\n                    Sims will only consider targets on the active lot.\n                    ', locked_args={'rule': OffLotAutonomyRules.ON_LOT_ONLY, 'tolerance': 0, 'radius': 0, 'anchor_tag': None, 'anchor_buff': None}), off_lot_only=TunableTuple(description='\n                    Sims will only consider targets that are off the active lot. \n                    ', locked_args={'rule': OffLotAutonomyRules.OFF_LOT_ONLY, 'tolerance': 0, 'anchor_tag': None, 'anchor_buff': None}, radius=TunableRange(description='\n                        The radius around the sim in which he will consider off-lot objects.  If it is \n                        0, the Sim will not consider off-lot objects at all.  This is not recommended \n                        since it will keep them from running any interactions unless they are already \n                        within the tolerance for that lot (set with Off Lot Tolerance).\n                        ', tunable_type=float, default=1000, minimum=0)), unlimited=TunableTuple(description='\n                    Sims will consider all objects regardless of on/off lot\n                    status.\n                    ', locked_args={'rule': OffLotAutonomyRules.UNLIMITED, 'tolerance': 0, 'radius': 1000, 'anchor_tag': None, 'anchor_buff': None}), restricted=TunableTuple(description='\n                    Sims will consider all objects in the restricted open\n                    street autonomy area.  This is defined by points in world\n                    builder so please make sure that world builder has setup\n                    the objects before trying to use this option.\n                    ', locked_args={'rule': OffLotAutonomyRules.RESTRICTED, 'tolerance': 0, 'radius': 0, 'anchor_tag': None, 'anchor_buff': None}), anchored=TunableTuple(description='\n                    Sims will only consider targets that are off the active lot. \n                    ', locked_args={'rule': OffLotAutonomyRules.ANCHORED, 'tolerance': 0}, radius=TunableRange(description='\n                        The radius around the anchoring point in which the sim will consider objects.\n                        This point must be set on the autonomy component.\n                        \n                        Designers: Please make sure this autonomy modifier is attached to a role or \n                        other other gameplay system that will correctly set the anchoring point before\n                        you set this. Or set the anchor tag on this tunable.\n                        ', tunable_type=float, default=50, minimum=0), anchor_tag=OptionalTunable(description='\n                        If enabled, this will set the autonomy anchor to all\n                        objects that match the tuned tag.\n                        ', tunable=TunableEnumEntry(description='\n                            The tag used to find an object to be an anchor.\n                            ', tunable_type=tag.Tag, default=tag.Tag.INVALID)), anchor_buff=OptionalTunable(description='\n                        If enabled, this will set the autonomy anchor to all\n                        sims that match the tuned buff.\n                        ', tunable=TunableBuffReference(description='\n                            The buff in question.\n                            '))), default='default_behavior')

class AutonomyModifier(BaseGameEffectModifier):
    STATISTIC_RESTRICTIONS = (statistics.commodity.Commodity, statistics.statistic.Statistic, statistics.skill.Skill, LifeSkillStatistic, 'RankedStatistic')
    ALWAYS_WHITELISTED_AFFORDANCES = TunableAffordanceFilterSnippet(description='\n        Any affordances tuned to be compatible with this filter will always be\n        allowed. This is useful for stuff like death and debug interactions,\n        which should never be disallowed by an autonomy modifier.\n        ')

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        for (situation_type, multiplier) in value.situation_type_social_score_multiplier.items():
            if multiplier == 1:
                logger.error('A situation type social score multiplier currently has a tuned multiplier of 1. This is invalid, please change to a value other than 1 or delete the entry. Class: {} Situation Type: {}', instance_class, situation_type)

    FACTORY_TUNABLES = {'verify_tunable_callback': _verify_tunable_callback, 'description': "\n            An encapsulation of a modification to Sim behavior.  These objects\n            are passed to the autonomy system to affect things like scoring,\n            which SI's are available, etc.\n            ", 'provided_affordance_compatibility': TunableAffordanceFilterSnippet(description='\n            Tune this to provide suppression to certain affordances when an object has\n            this autonomy modifier.\n            EX: Tune this to exclude all on the buff for the maid to prevent\n                other sims from trying to chat with the maid while the maid is\n                doing her work.\n            To tune if this restriction is for autonomy only, etc, see\n            super_affordance_suppression_mode.\n            Note: This suppression will also apply to the owning sim! So if you\n                prevent people from autonomously interacting with the maid, you\n                also prevent the maid from doing self interactions. To disable\n                this, see suppress_self_affordances.\n            '), 'super_affordance_suppression_mode': TunableEnumEntry(description='\n            Setting this defines how to apply the settings tuned in Super Affordance Compatibility.', tunable_type=SuperAffordanceSuppression, default=SuperAffordanceSuppression.AUTONOMOUS_ONLY), 'super_affordance_suppress_on_add': Tunable(description='\n            If checked, then the suppression rules will be applied when the\n            modifier is added, potentially canceling interactions the owner is\n            running.\n            ', tunable_type=bool, default=False), 'suppress_self_affordances': Tunable(description="\n            If checked, the super affordance compatibility tuned for this \n            autonomy modifier will also apply to the sim performing self\n            interactions.\n            \n            If not checked, we will not do provided_affordance_compatibility checks\n            if the target of the interaction is the same as the actor.\n            \n            Ex: Tune the maid's provided_affordance_compatibility to exclude all\n                so that other sims will not chat with the maid. But disable\n                suppress_self_affordances so that the maid can still perform\n                interactions on herself (such as her No More Work interaction\n                that tells her she's finished cleaning).\n            ", tunable_type=bool, default=True), 'score_multipliers': TunableMapping(description='\n                Mapping of statistics to multipliers values to the autonomy\n                scores.  EX: giving motive_bladder a multiplier value of 2 will\n                make it so that that motive_bladder is scored twice as high as\n                it normally would be.\n                ', key_type=TunableReference(services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=STATISTIC_RESTRICTIONS, description='\n                    The stat the multiplier will apply to.\n                    '), value_type=Tunable(float, 1, description='\n                    The autonomy score multiplier for the stat.  Multiplies\n                    autonomy scores by the tuned value.\n                    ')), 'static_commodity_score_multipliers': TunableMapping(description='\n                Mapping of statistics to multipliers values to the autonomy\n                scores.  EX: giving motive_bladder a multiplier value of 2 will\n                make it so that that motive_bladder is scored twice as high as\n                it normally would be.\n                ', key_type=TunableReference(description='\n                    The static commodity the multiplier will apply to.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.STATIC_COMMODITY), pack_safe=True), value_type=Tunable(float, 1, description='\n                    The autonomy score multiplier for the static commodity.  Multiplies\n                    autonomy scores by the tuned value.\n                    ')), 'relationship_score_multiplier_with_buff_on_target': TunableMapping(description="\n                Mapping of buffs to multipliers.  The buff must exist on the TARGET sim.\n                If it does, this value will be multiplied into the relationship score.\n                \n                Example: The make children desire to socialize with children, you can add \n                this autonomy modifier to the child's age buff.  You can then map it with \n                a key to the child buff to apply a positive multiplier.  An alternative \n                would be to create a mapping to every other age and apply a multiplier that \n                is smaller than 1.\n                ", key_type=TunableReference(services.get_instance_manager(sims4.resources.Types.BUFF), description='\n                    The buff that the target sim must have to apply this multiplier.\n                    '), value_type=Tunable(float, 1, description='\n                    The multiplier to apply.\n                    ')), 'locked_stats': TunableList(TunableReference(services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=STATISTIC_RESTRICTIONS, pack_safe=True, description='\n                    The stat the modifier will apply to.\n                    '), description='\n                List of the stats we locked from this modifier.  Locked stats\n                are set to their maximum values and then no longer allowed to\n                decay.\n                '), 'locked_stats_autosatisfy_on_unlock': Tunable(description='\n            If true, locked stats will be set to the value on the auto\n            satisfy curve when unlocked.  If false they will remain as-is.\n            (i.e. maxed)\n            ', tunable_type=bool, default=True), 'decay_modifiers': CommodityDecayModifierMapping(description='\n                Statistic to float mapping for decay modifiers for\n                statistics.  All decay modifiers are multiplied together along\n                with the decay rate.\n                '), 'decay_modifier_by_category': StatisticCategoryModifierMapping(description='\n                Statistic Category to float mapping for decay modifiers for\n                statistics. All decay modifiers are multiplied together along with\n                decay rate.\n                '), 'skill_tag_modifiers': TunableMapping(description='\n                The skill_tag to float mapping of skill modifiers.  Skills with\n                these tags will have their amount gained multiplied by the\n                sum of all the tuned values.\n                ', key_type=TunableEnumEntry(tag.Tag, tag.Tag.INVALID, description='\n                    What skill tag to apply the modifier on.\n                    '), value_type=Tunable(float, 0)), 'commodities_to_add': TunableList(TunableReference(services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=statistics.commodity.Commodity, pack_safe=True), description='\n                Commodites that are added while this autonomy modifier is\n                active.  These commodities are removed when the autonomy\n                modifier is removed.\n                '), 'only_scored_stats': OptionalTunable(TunableList(TunableReference(services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=STATISTIC_RESTRICTIONS), description='\n                    List of statistics that will only be considered when doing\n                    autonomy.\n                    '), tuning_filter=FilterTag.EXPERT_MODE, description="\n                If enabled, the sim in this role state will consider ONLY these\n                stats when doing autonomy. EX: for the maid, only score\n                commodity_maidrole_clean so she doesn't consider doing things\n                that she shouldn't care about.\n                "), 'only_scored_static_commodities': OptionalTunable(TunableList(StaticCommodity.TunableReference(), description='\n                    List of statistics that will only be considered when doing\n                    autonomy.\n                    '), tuning_filter=FilterTag.EXPERT_MODE, description='\n                If enabled, the sim in this role state will consider ONLY these\n                static commodities when doing autonomy. EX: for walkbys, only\n                consider the ringing the doorbell\n                '), 'stat_use_multiplier': TunableMapping(description='\n                List of stats and multiplier to affect their increase-decrease.\n                All stats on this list whenever they get modified (e. by a \n                constant modifier on an interaction, an interaction result...)\n                will apply the multiplier to their modified values. \n                e. A toilet can get a multiplier to decrease the repair rate\n                when its used, for this we would tune the commodity\n                brokenness and the multiplier 0.5 (to decrease its effect)\n                This tunable multiplier will affect the object statistics\n                not the ones for the sims interacting with it.\n                ', key_type=TunableReference(description='\n                    The stat the multiplier will apply to.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=STATISTIC_RESTRICTIONS, pack_safe=True), value_type=TunableTuple(description='\n                    Float value to apply to the statistic whenever its\n                    affected.  Greater than 1.0 if you want to increase.\n                    Less than 1.0 if you want a decrease (>0.0). \n                    A value of 0 is considered invalid and is skipped.\n                    ', multiplier=Tunable(description='\n                        Float value to apply to the statistic whenever its\n                        affected.  Greater than 1.0 if you want to increase.\n                        Less than 1.0 if you want a decrease (>0.0). \n                        A value of 0 is considered invalid and is skipped.\n                        ', tunable_type=float, default=1.0), apply_direction=TunableEnumEntry(description='\n                        Direction on when the multiplier should work on the \n                        statistic.  For example a decrease on an object \n                        brokenness rate, should not increase the time it takes to \n                        repair it.\n                        ', tunable_type=StatisticChangeDirection, default=StatisticChangeDirection.BOTH))), 'relationship_multipliers': TunableMapping(description='\n                List of relationship tracks and multiplier to affect their\n                increase or decrease of track value. All stats on this list\n                whenever they get modified (e. by a constant modifier on an\n                interaction, an interaction result...) will apply the\n                multiplier to their modified values. e.g. A LTR_Friendship_Main\n                can get a multiplier to decrease the relationship decay when\n                interacting with someone with a given trait, for this we would\n                tune the relationship track LTR_Friendship_Main and the\n                multiplier 0.5 (to decrease its effect)\n                ', key_type=relationships.relationship_track.RelationshipTrack.TunableReference(description='\n                    The Relationship track the multiplier will apply to.\n                    '), value_type=TunableTuple(description="\n                    Float value to apply to the statistic whenever it's\n                    affected.  Greater than 1.0 if you want to increase.\n                    Less than 1.0 if you want a decrease (>0.0).\n                    ", multiplier=Tunable(tunable_type=float, default=1.0), apply_direction=TunableEnumEntry(description='\n                        Direction on when the multiplier should work on the \n                        statistic.  For example a decrease on an object \n                        brokenness rate, should not increase the time it takes to \n                        repair it.\n                        ', tunable_type=StatisticChangeDirection, default=StatisticChangeDirection.BOTH))), 'object_tags_that_override_off_lot_autonomy': TunableList(description="\n                A list of object tags for objects that are always valid to be considered \n                for autonomy regardless of their on-lot or off-lot status.  Note that this \n                will only override off-lot autonomy availability.  It doesn't affect other \n                ways that objects are culled out.  For example, if an object list is passed\n                into the autonomy request (like when we're looking at targets of a crafting \n                phase), we only consider the objects in that list.  This won't override that \n                list.\n            ", tunable=TunableEnumEntry(tunable_type=tag.Tag, default=tag.Tag.INVALID)), 'off_lot_autonomy_rule': OptionalTunable(tunable=TunableOffLotAutonomy()), 'override_convergence_value': OptionalTunable(description="\n            If enabled it will set a new convergence value to the tuned\n            statistics.  The decay of those statistics will start moving\n            toward the new convergence value.\n            Convergence value will apply as long as these modifier is active,\n            when modifier is removed, convergence value will return to default\n            tuned value.\n            As a tuning restriction when this modifier gets removed we will \n            reset the convergence to its original value.  This means that we \n            don't support two states at the same time overwriting convergence\n            so we should'nt tune multiple convergence overrides on the same \n            object.\n            ", tunable=TunableMapping(description='\n                Mapping of statistic to new convergence value.\n                ', key_type=Commodity.TunableReference(), value_type=Tunable(description='\n                    Value to which the statistic should convert to.\n                    ', tunable_type=int, default=0)), disabled_name='Use_default_convergence', enabled_name='Set_new_convergence_value'), 'subject': TunableVariant(description='\n            Specifies to whom this autonomy modifier will apply.\n            - Apply to owner: Will apply the modifiers to the object or sim who \n            is triggering the modifier.  \n            e.g Buff will apply the modifiers to the sim when he gets the buff.  \n            An object will apply the modifiers to itself when it hits a state.\n            - Apply to interaction participant:  Will save the modifiers to \n            be only triggered when the object/sim who holds the modifier \n            is on an interaction.  When the interaction starts the the subject\n            tuned will get the modifiers during the duration of the interaction. \n            e.g A sim with modifiers to apply on an object will only trigger \n            when the sim is interactin with an object.\n            ', apply_on_interaction_to_participant=OptionalTunable(TunableEnumFlags(description='\n                    Subject on which the modifiers should apply.  When this is set\n                    it will mean that the autonomy modifiers will trigger on a \n                    subect different than the object where they have been added.\n                    e.g. a shower ill have hygiene modifiers that have to affect \n                    the Sim ', enum_type=ParticipantType, default=ParticipantType.Object)), default='apply_to_owner', locked_args={'apply_to_owner': False}), 'suppress_preroll_autonomy': Tunable(description='\n            If checked, sims with this buff will not run preroll autonomy when\n            first loading into a lot. This means that when the loading screen\n            disappears, they will be standing exactly where they spawned,\n            looking like a chump, instead of being somewhere on the lot doing\n            a normal-looking activity. As soon as the loading screen disappears,\n            all bets are off and autonomy will run normally again.\n            ', tunable_type=bool, default=False), 'situation_type_social_score_multiplier': TunableMapping(description='\n                A tunable mapping form situation type to multiplier to apply\n                when the target Sim is in a situation of the specified type with\n                the actor Sim.\n                ', key_type=TunableReference(description='\n                    A reference to the type of situation that both Sims need to\n                    be in together in order for the multiplier to be applied.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), pack_safe=True), value_type=Tunable(description='\n                    The multiplier to apply.\n                    ', tunable_type=float, default=1)), 'transition_from_sit_posture_penalty': OptionalTunable(description='\n            When enabled causes the Sim to be penalized for transitioning\n            from Sit to another posture.\n            ', tunable=Tunable(description='\n                The multiplier to apply to the autonomous interaction score\n                as a result of the Sim transitioning from sit to something\n                else.\n                \n                This number should be less than one (<1) in order for it to be\n                a penalty, otherwise it will be a bonus.\n                ', tunable_type=float, default=1.0)), 'supress_outside_objects_if_sun_out': OptionalTunable(description="\n            When enabled, objects on the outside will be suppressed by autonomy\n            if the sun is out (i.e. region provides light, it's daytime, \n            and weather isn't too cloudy) and will not be used unless they have\n            interactions tagged with 'counts_as_inside'.\n            ", tunable=Tunable(description='\n                When checked, outside objects will be suppressed, otherwise\n                supression will be canceled.\n                Canceling suppression will have a higher priority than an\n                active supression, this is to support cases like vampire buffs\n                always being suppressed, but when they activate the daywalker\n                power, that cancelation of suppression should always have a \n                higher priority. \n                ', tunable_type=bool, default=True)), 'outside_objects_multiplier': OptionalTunable(description="\n            When enabled, objects that are outside will have their interaction \n            scores modified unless they are tagged with 'counts_as_inside'.\n            ", tunable=Tunable(description='\n                Amount to multiple the autonomy score by.\n                ', tunable_type=float, default=1.0)), 'interaction_score_modifier': TunableList(description='\n            A list of score modifications to interactions (specified by list, \n            affordance or tags) to apply when the actor has this autonomy modifier.\n            ', tunable=TunableTuple(modifier=Tunable(description='\n                    Multiply score by this amount.\n                    ', tunable_type=float, default=1.0), affordances=TunableSet(description='\n                    A list of affordances that will be compared against.\n                    ', tunable=TunableReference(services.get_instance_manager(sims4.resources.Types.INTERACTION))), affordance_lists=TunableList(description='\n                    A list of affordance snippets that will be compared against.\n                    ', tunable=snippets.TunableAffordanceListReference()), interaction_category_tags=tag.TunableTags(description='\n                    This attribute is used to test for affordances that contain any of the tags in this set.\n                    ', filter_prefixes=('interaction',))))}

    def __init__(self, score_multipliers=None, static_commodity_score_multipliers=None, relationship_score_multiplier_with_buff_on_target=None, provided_affordance_compatibility=None, super_affordance_suppression_mode=SuperAffordanceSuppression.AUTONOMOUS_ONLY, suppress_self_affordances=False, suppress_preroll_autonomy=False, super_affordance_suppress_on_add=False, locked_stats=None, locked_stats_autosatisfy_on_unlock=None, decay_modifiers=None, statistic_modifiers=None, skill_tag_modifiers=None, commodities_to_add=(), only_scored_stats=None, only_scored_static_commodities=None, stat_use_multiplier=None, relationship_multipliers=None, object_tags_that_override_off_lot_autonomy=None, off_lot_autonomy_rule=None, override_convergence_value=None, subject=None, exclusive_si=None, decay_modifier_by_category=None, situation_type_social_score_multiplier=None, transition_from_sit_posture_penalty=None, supress_outside_objects_if_sun_out=None, outside_objects_multiplier=None, interaction_score_modifier=None):
        self._provided_affordance_compatibility = provided_affordance_compatibility
        self._super_affordance_suppression_mode = super_affordance_suppression_mode
        self._suppress_self_affordances = suppress_self_affordances
        self._super_affordance_suppress_on_add = super_affordance_suppress_on_add
        self._score_multipliers = score_multipliers
        self._locked_stats = tuple(set(locked_stats)) if locked_stats is not None else None
        self.autosatisfy_on_unlock = locked_stats_autosatisfy_on_unlock
        self._decay_modifiers = decay_modifiers
        self._decay_modifier_by_category = decay_modifier_by_category
        self._statistic_modifiers = statistic_modifiers
        self._relationship_score_multiplier_with_buff_on_target = relationship_score_multiplier_with_buff_on_target
        self._skill_tag_modifiers = skill_tag_modifiers
        self._commodities_to_add = commodities_to_add
        self._stat_use_multiplier = stat_use_multiplier
        self._relationship_multipliers = relationship_multipliers
        self._object_tags_that_override_off_lot_autonomy = object_tags_that_override_off_lot_autonomy
        self._off_lot_autonomy_rule = off_lot_autonomy_rule
        self._subject = subject
        self._override_convergence_value = override_convergence_value
        self._exclusive_si = exclusive_si
        self.suppress_preroll_autonomy = suppress_preroll_autonomy
        self._situation_type_social_score_multiplier = situation_type_social_score_multiplier
        self.transition_from_sit_posture_penalty = transition_from_sit_posture_penalty
        self.supress_outside_objects = supress_outside_objects_if_sun_out
        self.outside_objects_multiplier = outside_objects_multiplier
        self._interaction_score_modifier = interaction_score_modifier
        self._skill_tag_modifiers = {}
        if skill_tag_modifiers:
            for (skill_tag, skill_tag_modifier) in skill_tag_modifiers.items():
                skill_modifier = SkillTagMultiplier(skill_tag_modifier, StatisticChangeDirection.INCREASE)
                self._skill_tag_modifiers[skill_tag] = skill_modifier
        if static_commodity_score_multipliers:
            if self._score_multipliers is not None:
                self._score_multipliers = FrozenAttributeDict(self._score_multipliers, dict(static_commodity_score_multipliers))
            else:
                self._score_multipliers = static_commodity_score_multipliers
        self._static_commodity_score_multipliers = static_commodity_score_multipliers
        self._only_scored_stat_types = None
        if only_scored_stats is not None:
            self._only_scored_stat_types = []
            self._only_scored_stat_types.extend(only_scored_stats)
        if only_scored_static_commodities is not None:
            if self._only_scored_stat_types is None:
                self._only_scored_stat_types = []
            self._only_scored_stat_types.extend(only_scored_static_commodities)
        super().__init__(GameEffectType.AUTONOMY_MODIFIER)

    def apply_modifier(self, sim_info):
        return sim_info.add_statistic_modifier(self)

    def remove_modifier(self, sim_info, handle):
        sim_info.remove_statistic_modifier(handle)

    def __repr__(self):
        return standard_auto_repr(self)

    @property
    def exclusive_si(self):
        return self._exclusive_si

    def affordance_suppressed(self, sim, aop_or_interaction, user_directed=DEFAULT):
        user_directed = aop_or_interaction.is_user_directed if user_directed is DEFAULT else user_directed
        if self._suppress_self_affordances or aop_or_interaction.target is sim:
            return False
        affordance = aop_or_interaction.affordance
        if self._provided_affordance_compatibility is None:
            return False
        if user_directed and self._super_affordance_suppression_mode == SuperAffordanceSuppression.AUTONOMOUS_ONLY:
            return False
        if user_directed or self._super_affordance_suppression_mode == SuperAffordanceSuppression.USER_DIRECTED:
            return False
        if self._provided_affordance_compatibility(affordance):
            return False
        elif self.ALWAYS_WHITELISTED_AFFORDANCES(affordance):
            return False
        return True

    def locked_stats_gen(self):
        if self._locked_stats is not None:
            yield from self._locked_stats

    def get_score_multiplier(self, stat_type):
        if self._score_multipliers is not None and stat_type in self._score_multipliers:
            return self._score_multipliers[stat_type]
        return 1

    def get_stat_multiplier(self, stat_type, participant_type):
        if self._stat_use_multiplier is None:
            return 1
        elif self._subject == participant_type and stat_type in self._stat_use_multiplier:
            return self._stat_use_multiplier[stat_type].multiplier
        return 1

    @property
    def subject(self):
        return self._subject

    @property
    def statistic_modifiers(self):
        return self._statistic_modifiers

    @property
    def statistic_multipliers(self):
        return self._stat_use_multiplier

    @property
    def relationship_score_multiplier_with_buff_on_target(self):
        return self._relationship_score_multiplier_with_buff_on_target

    @property
    def situation_type_social_score_multiplier(self):
        return self._situation_type_social_score_multiplier

    @property
    def relationship_multipliers(self):
        return self._relationship_multipliers

    @property
    def decay_modifiers(self):
        return self._decay_modifiers

    @property
    def decay_modifier_by_category(self):
        return self._decay_modifier_by_category

    @property
    def skill_tag_modifiers(self):
        return self._skill_tag_modifiers

    @property
    def commodities_to_add(self):
        return self._commodities_to_add

    @property
    def override_convergence(self):
        return self._override_convergence_value

    def is_locked(self, stat_type):
        if self._locked_stats is None:
            return False
        return stat_type in self._locked_stats

    def is_scored(self, stat_type):
        if self._only_scored_stat_types is None or stat_type in self._only_scored_stat_types:
            return True
        return False

    @property
    def object_tags_that_override_off_lot_autonomy(self):
        return self._object_tags_that_override_off_lot_autonomy

    @property
    def off_lot_autonomy_rule(self):
        return self._off_lot_autonomy_rule

    @property
    def super_affordance_suppress_on_add(self):
        return self._super_affordance_suppress_on_add

    @property
    def interaction_score_modifier(self):
        return self._interaction_score_modifier
TunableAutonomyModifier = TunableSingletonFactory.create_auto_factory(AutonomyModifier)UNLIMITED_AUTONOMY_RULE = RestrictedFrozenAttributeDict(rule=OffLotAutonomyRules.UNLIMITED, tolerance=StatisticComponentGlobalTuning.DEFAULT_OFF_LOT_TOLERANCE, radius=StatisticComponentGlobalTuning.DEFAULT_RADIUS_TO_CONSIDER_OFF_LOT_OBJECTS, anchor_tag=None, anchor_buff=None)DEFAULT_AUTONOMY_RULE = RestrictedFrozenAttributeDict(rule=OffLotAutonomyRules.DEFAULT, tolerance=StatisticComponentGlobalTuning.DEFAULT_OFF_LOT_TOLERANCE, radius=StatisticComponentGlobalTuning.DEFAULT_RADIUS_TO_CONSIDER_OFF_LOT_OBJECTS, anchor_tag=None, anchor_buff=None)