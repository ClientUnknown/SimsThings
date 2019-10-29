from autonomy.autonomy_modes import FullAutonomyfrom autonomy.autonomy_modifier import TunableOffLotAutonomyfrom autonomy.settings import AutonomyStatefrom interactions.aop import AffordanceObjectPairfrom interactions.context import InteractionContext, InteractionSource, InteractionBucketTypefrom interactions.priority import Priorityfrom interactions.utils.interaction_liabilities import SituationLiability, SITUATION_LIABILITYfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import TunableList, TunableReference, TunableEnumEntry, TunableSet, TunableVariant, AutoFactoryInit, HasTunableSingletonFactory, TunableEnumWithFilter, Tunable, HasDependentTunableReference, OptionalTunablefrom sims4.tuning.tunable_base import FilterTagfrom sims4.utils import classpropertyfrom tag import Tagimport autonomyimport buffs.tunableimport enumimport role.role_state_baseimport servicesimport sims4.logimport sims4.resourcesimport taglogger = sims4.log.Logger('Roles')
class RolePriority(enum.Int):
    LOW = 0
    NORMAL = 1
    HIGH = 2

class RoleStateCraftingOwnershipOverride(enum.Int):
    NO_OVERRIDE = 0
    LOT_OWNER = 1
    ACTIVE_HOUSEHOLD = 2

class SituationAffordanceTarget(enum.Int):
    NO_TARGET = 0
    CRAFTED_OBJECT = 1
    TARGET_OBJECT = 2
    CREATED_OBJECT = 3

class PushAffordanceFromRole(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': '\n            Push the specific affordance onto the sim.\n            ', 'affordance': TunableReference(manager=services.affordance_manager()), 'super_affordance_for_mixer': OptionalTunable(description='\n            If we want to push mixer directly in the affordance tuning for this\n            role state, we would need to provide a super affordance here to\n            handle the mixer.\n            ', tunable=TunableReference(manager=services.affordance_manager()), disabled_name='do_not_need_si', enabled_name='provide_si'), 'source': TunableEnumEntry(tunable_type=InteractionSource, default=InteractionSource.SCRIPT), 'priority': TunableEnumEntry(description='\n            Priority to push the interaction\n            ', tunable_type=Priority, default=Priority.High), 'run_priority': TunableEnumEntry(description='\n            Priority to run the interaction. None means use the (push) priority\n            ', tunable_type=Priority, default=None), 'target': TunableEnumEntry(description='\n            The target of the affordance. We will try to get\n            the target from the situation the role sim is\n            running.\n            ', tunable_type=SituationAffordanceTarget, default=SituationAffordanceTarget.NO_TARGET), 'leave_situation_on_failure': Tunable(description='\n            If set to True, when push affordance on the sim fails, sim will\n            leave the situation.\n            ', tunable_type=bool, default=False), 'add_situation_liability': Tunable(description='\n            If set to True, we will add a liability to the pushed interaction\n            such that we will cancel the situation owning this role state\n            if the interaction (and its continuations) are completed or \n            canceled.\n            ', tunable_type=bool, default=False)}

    def __call__(self, role_state, role_affordance_target, situation=None, **kwargs):
        sim = role_state.sim
        affordance = self.affordance
        source = self.source
        priority = self.priority
        run_priority = self.run_priority
        if run_priority is None:
            run_priority = priority
        interaction_context = InteractionContext(sim, source, priority, run_priority=run_priority, **kwargs)
        target = role_state._get_target_for_push_affordance(self.target, situation=situation, role_affordance_target=role_affordance_target)
        try:
            push_result = False
            if affordance.is_super:
                push_result = sim.push_super_affordance(affordance, target, interaction_context)
            else:
                super_affordance = self.super_affordance_for_mixer
                if super_affordance is not None:
                    potential_parent_si = sim.si_state.get_si_by_affordance(super_affordance)
                    if potential_parent_si is not None:
                        aop = AffordanceObjectPair(affordance, target, super_affordance, potential_parent_si)
                        push_result = aop.test_and_execute(interaction_context)
            if push_result:
                if self.add_situation_liability:
                    liability = SituationLiability(situation)
                    push_result.interaction.add_liability(SITUATION_LIABILITY, liability)
            elif self.leave_situation_on_failure:
                situation_manager = services.get_zone_situation_manager()
                situation_manager.remove_sim_from_situation(sim, situation.id)
        except AttributeError:
            logger.error('Attribute Error occurred pushing interaction {} on sim: {} for role_state:{}', affordance, sim, role_state, owner='msantander')
            raise

class DoAutonomyPingFromRole(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, role_state, role_affordance_target, situation=None):
        role_state.sim.run_full_autonomy_next_ping()

class DoParameterizedAutonomyPingFromRole(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': '\n            Parameterized autonomy ping to run either during preroll or\n            as soon as the sim is assigned this role.\n            ', 'commodities': TunableSet(description='\n            Set of commodities to run parameterized autonomy against after\n            running this interaction.\n            ', tunable=TunableReference(description='\n                The type of commodity to search for.\n                ', manager=services.statistic_manager())), 'static_commodities': TunableSet(description='\n            Set of static commodities to run parameterized autonomy against\n            after running this interaction.\n            ', tunable=TunableReference(description='\n                The type of static commodity to search for.\n                ', manager=services.static_commodity_manager())), 'source': TunableEnumEntry(description='\n            Set this to *spoof* the source of this interaction. This will have\n            various gameplay effects and should be used after due consideration.\n            ', tunable_type=InteractionSource, default=InteractionSource.AUTONOMY), 'priority': TunableEnumEntry(description='\n            The priority level at which this autonomy will run.\n            ', tunable_type=Priority, default=Priority.Low), 'run_priority': OptionalTunable(description='\n            If enabled, specify the run priority at which the selected affordance\n            (if any is selected) will run.\n            ', tunable=TunableEnumEntry(tunable_type=Priority, default=Priority.Low)), 'radius_to_consider': Tunable(description='\n            The radius around the sim that targets must be in to be valid\n            for Parameterized Autonomy.  Anything outside this radius will\n            be ignored.  A radius of 0 is considered infinite.\n            ', tunable_type=float, default=0), 'consider_scores_of_zero': Tunable(description='\n            The autonomy request will consider scores of zero.  This allows sims to to choose things they \n            might not desire.\n            ', tunable_type=bool, default=False), 'test_connectivity_to_target': Tunable(description='\n            If checked, this test will ensure the Sim can pass a pt to\n            pt connectivity check to the advertising object.\n            ', tunable_type=bool, default=True), 'off_lot_rule': OptionalTunable(tunable=TunableOffLotAutonomy())}

    def __call__(self, role_state, role_affordance_target, situation=None):
        sim = role_state.sim
        context = InteractionContext(sim, self.source, self.priority, run_priority=self.run_priority, bucket=InteractionBucketType.DEFAULT)
        autonomy_request = autonomy.autonomy_request.AutonomyRequest(sim, FullAutonomy, commodity_list=self.commodities, static_commodity_list=self.static_commodities, apply_opportunity_cost=False, is_script_request=True, context=context, si_state_view=sim.si_state, limited_autonomy_allowed=True, radius_to_consider=self.radius_to_consider, consider_scores_of_zero=self.consider_scores_of_zero, autonomy_mode_label_override='ParameterizedAutonomy', off_lot_autonomy_rule_override=self.off_lot_rule, test_connectivity_to_target_object=self.test_connectivity_to_target)
        sim.queue_autonomy_request(autonomy_request)
        sim.run_full_autonomy_next_ping()

class RoleState(HasDependentTunableReference, role.role_state_base.RoleStateBase, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE)):
    INSTANCE_TUNABLES = {'_role_priority': TunableEnumEntry(RolePriority, RolePriority.NORMAL, description='\n                The priority of this role state.  All the role states with the\n                same priority will all be applied together.  The highest group\n                of priorities is considered the active ones.\n                '), '_buffs': TunableList(buffs.tunable.TunableBuffReference(pack_safe=True), description='\n                Buffs that will be added to sim when role is active.\n                '), '_off_lot_autonomy_buff': buffs.tunable.TunableBuffReference(description='A buff that\n            prevents autonomy from considering some objects based on the\n            location of the object (e.g. on lot, off lot, within a radius of the\n            sim).\n             \n            In the buff set: Game Effect Modifiers->Autonomy Modifier->Off Lot\n            Autonomy Rule.\n            ', allow_none=True), 'tags': TunableSet(TunableEnumEntry(Tag, Tag.INVALID), description='\n                Tags for the role state for checking role states against a set\n                of tags rather than against a list of role states.\n                '), 'role_affordances': TunableList(description="\n            A list of affordances that are available on the Sim in this Role\n            State.\n            \n            e.g: when a Maid is in the working Role State, he or she will have\n            the 'Dismiss' and 'Fire' affordances available in the Pie Menu.\n            ", tunable=TunableReference(manager=services.affordance_manager(), class_restrictions=('SuperInteraction',), pack_safe=True)), 'role_target_affordances': TunableList(description='\n            A list of affordances that are available on other Sims when the\n            actor Sim is in this Role State.\n            \n            e.g. a Sim in a specific Role State could have an "Invite to\n            Situation" interaction available when bringing up other Sims\' Pie\n            Menus.\n            ', tunable=TunableReference(manager=services.affordance_manager(), class_restrictions=('SuperInteraction',), pack_safe=True)), 'preroll_affordances': TunableList(description='\n            A list of affordances that are available for sims to consider when\n            running pre-roll. Objects related to role can specify preroll\n            autonomy, but there are some roles that may not have an object\n            associated with it\n            \n            e.g. Romance guru in romance festival preroll to an attractor point.\n            ', tunable=TunableReference(manager=services.affordance_manager(), class_restrictions=('SuperInteraction',), pack_safe=True)), '_on_activate': TunableVariant(description='\n                Select the autonomy behavior when this role state becomes active on the sim.\n                disabled: Take no action.\n                autonomy_ping: We explicitly force an autonomy ping on the sim.\n                push_affordance: Push the specific affordance on the sim.\n                ', locked_args={'disabled': None}, autonomy_ping=DoAutonomyPingFromRole.TunableFactory(), parameterized_autonomy_ping=DoParameterizedAutonomyPingFromRole.TunableFactory(), push_affordance=PushAffordanceFromRole.TunableFactory(), default='disabled'), '_portal_disallowance_tags': TunableSet(description='\n                A set of tags that define what the portal disallowance tags of\n                this role state are.  Portals that include any of these\n                disallowance tags are considered locked for sims that have this\n                role state.\n                ', tunable=TunableEnumWithFilter(description='\n                    A single portal disallowance tag.\n                    ', tunable_type=tag.Tag, default=tag.Tag.INVALID, filter_prefixes=tag.PORTAL_DISALLOWANCE_PREFIX)), '_allow_npc_routing_on_active_lot': Tunable(description='\n                If True, then npc in this role will be allowed to route on the\n                active lot.\n                If False, then npc in this role will not be allowed to route on the\n                active lot, unless they are already on the lot when the role\n                state is activated.\n                \n                This flag is ignored for player sims and npcs who live on the\n                active lot.\n                \n                e.g. ambient walkby sims should not be routing on the active lot\n                because that is rude.\n                ', tunable_type=bool, default=True), '_autonomy_state_override': OptionalTunable(description='\n            If tuned, will force role sims into a specific autonomy state.\n            Please consult your GPE partner before using this.\n            ', tunable=TunableEnumEntry(tunable_type=AutonomyState, default=AutonomyState.LIMITED_ONLY, invalid_enums=(AutonomyState.MEDIUM,)), tuning_filter=FilterTag.EXPERT_MODE), '_crafting_process_override': TunableEnumEntry(description='\n                The override option of who to assign ownership of objects made\n                by Sims in this role state.\n                ', tunable_type=RoleStateCraftingOwnershipOverride, default=RoleStateCraftingOwnershipOverride.NO_OVERRIDE), 'always_active': Tunable(description="\n                If set to True, this role will always be allowed to be active\n                when set on a Sim, regardless of whether or not it is \n                lower priority than the Sim's other currently active roles. \n                Use for roles that are important but retuning priority for it \n                and/or other roles isn't feasible.\n                \n                Consult a GPE before you set this to True.\n                This is not to be used lightly and there may be other options\n                like situation exclusivity that can be explored before you\n                go down this route.\n                \n                e.g. Sim is possessed which runs at HIGH priority.\n                Sim wants to go visit an NPC residential lot, which places\n                Sim in NORMAL priority Role_UngreetedPlayerVisitingNPC, which\n                sets portal disallowance and adds specific buffs.\n                \n                We actually want Role_UngreetedPlayerVisitingNPC to run\n                even though the role priority is now HIGH, because \n                otherwise a possessed Sim visiting an NPC would magically\n                be able to route through homes because portal disallowance\n                is removed.\n                ", tunable_type=bool, default=False)}

    @classmethod
    def _verify_tuning_callback(cls):
        for buff_ref in cls.buffs:
            if buff_ref is None:
                logger.error('{} has empty buff in buff list. Please fix tuning.', cls)
            elif buff_ref.buff_type._temporary_commodity_info is not None:
                logger.error('{} has a buff {} that has a temporary commodity.', cls, buff_ref.buff_type)

    @classproperty
    def role_priority(cls):
        return cls._role_priority

    @classproperty
    def buffs(cls):
        return cls._buffs

    @classproperty
    def off_lot_autonomy_buff(cls):
        return cls._off_lot_autonomy_buff

    @classproperty
    def role_specific_affordances(cls):
        return cls.role_affordances

    @classproperty
    def allow_npc_routing_on_active_lot(cls):
        return cls._allow_npc_routing_on_active_lot

    @classproperty
    def autonomy_state_override(cls):
        return cls._autonomy_state_override

    @classproperty
    def on_activate(cls):
        return cls._on_activate

    @classproperty
    def portal_disallowance_tags(cls):
        return cls._portal_disallowance_tags

    @classproperty
    def has_full_permissions(cls):
        current_venue = services.get_current_venue()
        if current_venue and current_venue.allow_rolestate_routing_on_navmesh:
            return True
        return not cls._portal_disallowance_tags and cls._allow_npc_routing_on_active_lot

    def _get_target_for_push_affordance(self, situation_target, situation=None, role_affordance_target=None):
        if situation_target == SituationAffordanceTarget.NO_TARGET:
            return
        if situation_target == SituationAffordanceTarget.CRAFTED_OBJECT:
            return role_affordance_target
        if situation_target == SituationAffordanceTarget.TARGET_OBJECT and situation is not None:
            return situation.get_target_object()
        if situation_target == SituationAffordanceTarget.CREATED_OBJECT and situation is not None:
            return situation.get_created_object()
        logger.error('Unable to resolve target when trying to push affordance on role state {} activate. requested target type was {}', self, self._on_activate.target)

    @classproperty
    def active_household_crafting_override(cls):
        return cls._crafting_process_override == RoleStateCraftingOwnershipOverride.ACTIVE_HOUSEHOLD

    @classproperty
    def lot_owner_crafting_override(cls):
        return cls._crafting_process_override == RoleStateCraftingOwnershipOverride.LOT_OWNER
