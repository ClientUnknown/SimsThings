import collectionsimport copyimport functoolsimport operatorfrom animation.posture_manifest import Handfrom build_buy import HouseholdInventoryFlagsfrom carry.carry_postures import CarryingObjectfrom carry.carry_tuning import CarryPostureStaticTuningfrom carry.holstering_tuning import TunableUnholsterWhileRoutingBehaviorVariantfrom carry.put_down_strategy import TunablePutDownStrategySpeciesMappingfrom distributor.system import Distributorfrom interactions import ParticipantTypefrom interactions.aop import AffordanceObjectPairfrom interactions.constraint_variants import TunableConstraintVariant, TunableGeometricConstraintVariantfrom interactions.constraints import Anywhere, TunedCirclefrom interactions.liability import Liabilityfrom interactions.utils.plumbbob import TunableReslotPlumbbob, ReslotPlumbbob, unslot_plumbbob, reslot_plumbbobfrom interactions.utils.tunable_provided_affordances import TunableProvidedAffordancesfrom objects.base_interactions import ProxyInteractionfrom objects.components import componentmethod, Component, componentmethod_with_fallbackfrom objects.components.types import CARRYABLE_COMPONENTfrom placement import FGLSearchFlag, FGLSearchFlagsDefaultForSimfrom routing.portals.portal_tuning import PortalFlagsfrom sims.sim_info_types import Speciesfrom sims4.tuning.tunable import TunableReference, TunableVariant, OptionalTunable, TunableList, Tunable, TunableMapping, AutoFactoryInit, HasTunableFactory, HasTunableSingletonFactory, TunableEnumFlags, TunableRangefrom sims4.utils import classproperty, flexmethodfrom singletons import DEFAULTfrom snippets import TunableAffordanceFilterSnippetimport build_buyimport objects.componentsimport placementimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('CarryableComponent')
class PutDownLiability(Liability):
    LIABILITY_TOKEN = 'PutDownLiability'

    def __init__(self, target_object, **kwargs):
        super().__init__(**kwargs)
        self._interaction = None
        self._parent = None
        self._target_object = target_object

    def on_add(self, interaction):
        self._interaction = interaction
        self._parent = interaction.sim

    def release(self):
        target_object = self._target_object
        carry_component = target_object.get_component(CARRYABLE_COMPONENT)
        if carry_component is None:
            logger.error('Interaction ({0}) has a target ({1}) without a Carryable Component', self._interaction, target_object)
            return
        if target_object.parent is not self._parent:
            carry_component.reset_put_down_count()
            return
        if carry_component.attempted_putdown and carry_component.attempted_alternative_putdown and target_object.transient:
            new_context = self._interaction.context.clone_for_continuation(self._interaction)
            aop = target_object.get_put_down_aop(self._interaction, new_context)
            aop.test_and_execute(new_context)
            return
        if not CarryingObject.snap_to_good_location_on_floor(target_object):
            sim = self._interaction.sim
            if sim.household.id is not target_object.get_household_owner_id() or not sim.inventory_component.player_try_add_object(target_object):
                target_object.release_sim(sim)
                build_buy.move_object_to_household_inventory(target_object, failure_flags=HouseholdInventoryFlags.FORCE_OWNERSHIP)
ScoredAOP = collections.namedtuple('ScoredAOP', ['score', 'aop'])
class CarryTargetInteraction(ProxyInteraction):
    INSTANCE_SUBCLASSES_ONLY = True

    @classproperty
    def proxy_name(cls):
        return '[CarryTarget]'

    @classmethod
    def generate(cls, proxied_affordance, carry_target):
        result = super().generate(proxied_affordance)
        result._carry_target_ref = carry_target.ref()
        return result

    @property
    def carry_target(self):
        if self._carry_target_ref is not None:
            return self._carry_target_ref()

    @flexmethod
    def get_participants(cls, inst, participant_type, *args, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        if participant_type == ParticipantType.CarriedObject and inst_or_cls._carry_target_ref is not None:
            return {inst_or_cls._carry_target_ref()}
        return super(__class__, inst_or_cls).get_participants(participant_type, *args, **kwargs)

class CarryableComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=objects.components.types.CARRYABLE_COMPONENT):

    class _CarryableAllowedHands(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'biped_allowed_hands': TunableVariant(locked_args={'both': (Hand.LEFT, Hand.RIGHT), 'left_only': (Hand.LEFT,), 'right_only': (Hand.RIGHT,)}, default='both'), 'quadruped_allowed_hands': TunableVariant(locked_args={'both': (Hand.LEFT, Hand.RIGHT), 'mouth_only': (Hand.RIGHT,), 'back_only': (Hand.LEFT,)}, default='mouth_only')}

        def get_allowed_hands(self, sim):
            if sim is None:
                return self.biped_allowed_hands
            return sim.get_allowed_hands_type(self)

    class _CarryableTransitionConstraint(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'constraint_mobile': TunableList(description='\n                The constraint to use when the Sim is in a mobile posture.\n                ', tunable=TunableGeometricConstraintVariant(disabled_constraints={'spawn_points', 'relative_circle', 'current_position'})), 'constraint_non_mobile': TunableList(description='\n                The constraint to use when the Sim is not in a mobile posture.\n                ', tunable=TunableGeometricConstraintVariant(disabled_constraints={'spawn_points', 'relative_circle', 'current_position'}))}

    DEFAULT_GEOMETRIC_TRANSITION_CONSTRAINT = _CarryableTransitionConstraint.TunableFactory(description='\n        Unless specifically overridden, the constraint to use when transitioning\n        into and out of a carry for any carryable object.\n        ')
    DEFAULT_GEOMETRIC_TRANSITION_LARGE = TunableRange(description='\n        This is a large transition distance. This is used by:\n            * TYAE humans picking up any pet\n        ', tunable_type=float, default=0.7, minimum=0)
    DEFAULT_GEOMETRIC_TRANSITION_MEDIUM = TunableRange(description='\n        This is a medium transition distance. This is used by:\n            * TYAE humans picking up P humans\n        ', tunable_type=float, default=0.6, minimum=0)
    DEFAULT_GEOMETRIC_TRANSITION_SMALL = TunableRange(description='\n        This is a small transition distance. This is used by:\n            * C humans picking up AE cats and AE small dogs\n        ', tunable_type=float, default=0.503, minimum=0)
    DEFAULT_GEOMETRIC_TRANSITION_TINY = TunableRange(description='\n        This is a tiny transition distance. This is used by:\n            * C humans picking up C cats and C dogs and small dogs\n        ', tunable_type=float, default=0.419, minimum=0)
    DEFAULT_CARRY_AFFORDANCES = TunableList(description='\n        The list of default carry affordances.\n        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)))
    PUT_IN_INVENTORY_AFFORDANCE = TunableReference(description='\n        The affordance used by carryable component to put objects in inventory.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
    PUT_DOWN_HERE_AFFORDANCE = TunableReference(description='\n        The affordance used by carryable component to put down here via the\n        PutDownLiability liability.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
    PUT_DOWN_ANYWHERE_AFFORDANCE = TunableReference(description='\n        The affordance used by carryable component to put down objects anywhere\n        via the PutDownLiability liability.\n        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))
    FACTORY_TUNABLES = {'put_down_tuning': TunableVariant(description='\n            Define how Sims prefer to put this object down.\n            ', reference=TunablePutDownStrategySpeciesMapping(description='\n                Define specific costs for all the possible locations this object\n                could be put down. Also, define, if necessary, custom\n                interactions to put the object down.\n                \n                If this is not specified, and the default is used, the most\n                appropriate put down strategy is used. This allows the object to\n                be put down in most places (floor, inventory, slots). Also,\n                species might specify their own custom behavior.\n                '), locked_args={'use_default': None}, default='use_default'), 'state_based_put_down_tuning': TunableMapping(description='\n            A mapping from a state value to a putdownstrategy. If the owning\n            object is in any of the states tuned here, it will use that state\'s\n            associated putdownstrategy in place of the one putdownstrategy tuned\n            in the "put_down_tuning" field. If the object is in multiple states\n            listed in this mapping, the behavior is undefined.\n            ', key_type=TunableReference(description='\n                The state value this object must be in in order to use the\n                associated putdownstrategy.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE)), value_type=TunableVariant(reference=TunablePutDownStrategySpeciesMapping(description='\n                    Tuning for how to score where a Sim might want to set an\n                    object down.\n                    ')), key_name='State', value_name='PutDownStrategy'), 'carry_affordances': OptionalTunable(tunable=TunableList(tunable=TunableReference(description='\n                    The versions of the HoldObject affordance that this object\n                    supports.\n                    ', manager=services.affordance_manager())), disabled_name='use_default_affordances', enabled_name='use_custom_affordances'), 'provided_affordances': TunableProvidedAffordances(description='\n            Affordances that are generated when a Sim holding this object\n            selects another object to interact with. The generated interactions\n            target the selected object, and have their carry target set to the\n            component\'s owner.\n            \n            By default, this is applied to Sims. e.g.: The "Drink" interaction\n            provides "Make Toast" on other Sims.\n            \n            Optionally, you can specify a tag to have the interaction appear on\n            other objects. e.g.: The "Hold Puppy" interaction might unlock "Put\n            Down Here" on sofas.\n                \n            Target defaults to the object selected (Invalid). Carry Target is\n            locked to this object being carried. If is_linked is\n            checked, the affordance will be linked to the interaction\n            carrying this object.\n            ', class_restrictions=('SuperInteraction',), locked_args={'allow_self': False, 'target': ParticipantType.Object, 'carry_target': ParticipantType.CarriedObject}), 'constraint_pick_up': OptionalTunable(description='\n            A list of constraints that must be fulfilled in order to\n            interact with this object.\n            ', tunable=TunableList(tunable=TunableConstraintVariant(description='\n                    A constraint that must be fulfilled in order to\n                    interact with this object.\n                    '))), 'allowed_hands_data': _CarryableAllowedHands.TunableFactory(), 'holster_while_routing': Tunable(description='\n            If True, the Sim will holster the object before routing and\n            unholster when the route is complete.\n            ', tunable_type=bool, default=False), 'holster_compatibility': TunableAffordanceFilterSnippet(description='\n            Define interactions for which holstering this object is\n            explicitly disallowed.\n            \n            e.g. The Scythe is tuned to be holster-incompatible with\n            sitting, meaning that Sims will holster the Sctyhe when sitting.\n            '), 'unholster_when_routing': TunableUnholsterWhileRoutingBehaviorVariant(), 'prefer_owning_sim_inventory_when_not_on_home_lot': Tunable(description="\n            If checked, this object will highly prefer to be put into the\n            owning Sim's inventory when being put down by the owning Sim on\n            a lot other than their home lot.\n            \n            Certain objects, like consumables, should be exempt from this.\n            ", tunable_type=bool, default=True), 'is_valid_posture_graph_object': Tunable(description='\n            If this is checked, this object is allowed to provide postures and\n            expand in the posture graph, despite its ability to be carried.\n            \n            Normally, for the performance reasons, carryable objects are not\n            posture providing objects. The preferred way of interacting with a\n            carryable object is marking it as a carry requirement in the ASM.\n            \n            However, there are objects for which this is not possible. For\n            example, Nesting Blocks are carryable, but toddlers interact with\n            them while in the "Sit On Ground" posture, which must be provided by\n            the object\'s parts.\n            \n            This field should be used with caution, since posture graph\n            generation is one of our slowest systems. Do not enable it on\n            objects such as food or drinks, since the world is bound to have\n            many of them.\n            ', tunable_type=bool, default=False), 'portal_key_mask_flags': TunableEnumFlags(description="\n            Any flag tuned here will be kept on the Sim routing context who's\n            picking up this object.  This will allow a Sim to pickup some\n            type of objects and still be allowed to transition through\n            some portals while carrying an object.\n            ", enum_type=PortalFlags, allow_no_flags=True), 'reslot_plumbbob': OptionalTunable(description='\n            If tuned, the plumbbob will be repositioned when this item is carried.\n            Reslot will always go away when sim stops carrying the object.\n            ', tunable=TunableReslotPlumbbob()), 'defer_putdown': Tunable(description='\n            If true, the put down will be deferred to the end of the route. \n            If false, put down will be done at the start of the route. This\n            should be the default behavior. \n            ', tunable_type=bool, default=False), 'put_down_height_tolerance': TunableRange(description='\n            Maximum height tolerance on the terrain we will use for the \n            placement of this object when asking FGL to find a spot on the\n            floor.\n            Having a high value here will make it so an object can be placed\n            in a terrain spot with a high slope that might result with\n            clipping depending on the width of the object.  The way this will\n            work will be using the object footprint, if the edges are at a\n            height higher than the height tolerance, then the location will\n            not be valid.\n            ', tunable_type=float, default=1.1, minimum=0)}

    def __init__(self, owner, **kwargs):
        super().__init__(owner, **kwargs)
        self._attempted_putdown = False
        self._attempted_alternative_putdown = False
        self._cached_put_down_strategy = None

    @property
    def attempted_putdown(self):
        return self._attempted_putdown

    @property
    def attempted_alternative_putdown(self):
        return self._attempted_alternative_putdown

    @property
    def ideal_slot_type_set(self):
        put_down_strategy = self.get_put_down_strategy()
        return put_down_strategy.ideal_slot_type_set

    @componentmethod
    def get_carry_object_posture(self):
        if self.carry_affordances is None:
            return CarryPostureStaticTuning.POSTURE_CARRY_OBJECT
        return self.carry_affordances[0].provided_posture_type

    @componentmethod_with_fallback(lambda *_, **__: ())
    def get_allowed_hands(self, sim):
        return self.allowed_hands_data.get_allowed_hands(sim)

    @componentmethod_with_fallback(lambda *_, **__: 0)
    def get_portal_key_make_for_carry(self):
        return self.portal_key_mask_flags

    @componentmethod
    def should_unholster(self, *args, **kwargs):
        return self.unholster_when_routing.should_unholster(*args, **kwargs)

    @componentmethod
    def get_put_down_strategy(self, parent=DEFAULT):
        if self._cached_put_down_strategy is None:
            parent = self.owner.parent if parent is DEFAULT else parent
            species = parent.species if parent is not None else Species.HUMAN
            for (state_value, put_down_strategy) in self.state_based_put_down_tuning.items():
                if self.owner.state_value_active(state_value):
                    self._cached_put_down_strategy = put_down_strategy.get(species)
                    break
            if self.put_down_tuning is not None:
                self._cached_put_down_strategy = self.put_down_tuning.get(species)
            if self._cached_put_down_strategy is None:
                put_down_strategy = parent.get_default_put_down_strategy()
                self._cached_put_down_strategy = put_down_strategy
        return self._cached_put_down_strategy

    def _get_carry_transition_distance_for_sim(self, sim):
        carry_sim = self.owner.sim_info
        carrying_sim = sim.sim_info
        if carry_sim.is_toddler:
            return self.DEFAULT_GEOMETRIC_TRANSITION_MEDIUM
        if carrying_sim.is_teen_or_older:
            return self.DEFAULT_GEOMETRIC_TRANSITION_LARGE
        if carry_sim.is_teen_or_older:
            return self.DEFAULT_GEOMETRIC_TRANSITION_SMALL
        return self.DEFAULT_GEOMETRIC_TRANSITION_TINY

    def _get_adjusted_circle_constraint(self, sim, constraint):
        if not self.owner.is_sim:
            return constraint
        if not isinstance(constraint, TunedCircle):
            return constraint
        ideal_radius_override = self._get_carry_transition_distance_for_sim(sim)
        constraint = copy.copy(constraint)
        constraint.ideal_radius_width = constraint.ideal_radius_width/constraint.ideal_radius*ideal_radius_override
        constraint.radius = constraint.radius/constraint.ideal_radius*ideal_radius_override
        constraint.ideal_radius = ideal_radius_override
        return constraint

    @componentmethod
    def get_carry_transition_constraint(self, sim, position, routing_surface, cost=0, mobile=True):
        constraints = self.DEFAULT_GEOMETRIC_TRANSITION_CONSTRAINT
        constraints = constraints.constraint_mobile if mobile else constraints.constraint_non_mobile
        final_constraint = Anywhere()
        for constraint in constraints:
            if mobile:
                constraint = self._get_adjusted_circle_constraint(sim, constraint)
            final_constraint = final_constraint.intersect(constraint.create_constraint(None, None, target_position=position, routing_surface=routing_surface))
        final_constraint = final_constraint.generate_constraint_with_cost(cost)
        final_constraint = final_constraint._copy(_multi_surface=True)
        return final_constraint

    @componentmethod
    def get_pick_up_constraint(self, sim):
        if self.constraint_pick_up is None:
            return
        final_constraint = Anywhere()
        for constraint in self.constraint_pick_up:
            constraint = self._get_adjusted_circle_constraint(sim, constraint)
            constraint = constraint.create_constraint(sim, target=self.owner)
            final_constraint = final_constraint.intersect(constraint)
        final_constraint = final_constraint._copy(_multi_surface=True)
        return final_constraint

    @componentmethod
    def get_provided_aops_gen(self, target, context, **kwargs):
        for provided_affordance_data in self.provided_affordances:
            if not provided_affordance_data.affordance.is_affordance_available(context=context):
                pass
            elif not provided_affordance_data.object_filter.is_object_valid(target):
                pass
            else:
                if provided_affordance_data.affordance.is_social and not target.is_sim:
                    affordance = provided_affordance_data.affordance
                    interaction_target = self.owner
                    preferred_objects = (target,)
                else:
                    affordance = CarryTargetInteraction.generate(provided_affordance_data.affordance, self.owner)
                    interaction_target = target
                    preferred_objects = ()
                depended_on_si = None
                parent = self.owner.parent
                if parent.is_sim:
                    carry_posture = parent.posture_state.get_carry_posture(self.owner)
                    if provided_affordance_data.is_linked:
                        depended_on_si = carry_posture.source_interaction
                yield from affordance.potential_interactions(interaction_target, context, depended_on_si=depended_on_si, preferred_objects=preferred_objects, **kwargs)

    def component_super_affordances_gen(self, **kwargs):
        if self.carry_affordances is None:
            affordances = self.DEFAULT_CARRY_AFFORDANCES
        else:
            affordances = self.carry_affordances
        for affordance in affordances:
            yield affordance

    def component_interactable_gen(self):
        yield self

    def on_state_changed(self, state, old_value, new_value, from_init):
        if new_value in self.state_based_put_down_tuning or old_value in self.state_based_put_down_tuning:
            self._cached_put_down_strategy = None

    def component_reset(self, reset_reason):
        self.reset_put_down_count()

    @componentmethod
    def get_initial_put_down_position(self, carrying_sim=None):
        carrying_sim = carrying_sim or self.owner.parent
        if carrying_sim is None:
            return (self.owner.position, self.owner.routing_surface)
        additional_put_down_distance = carrying_sim.posture.additional_put_down_distance
        position = carrying_sim.position + carrying_sim.forward*(carrying_sim.object_radius + additional_put_down_distance)
        sim_los_constraint = carrying_sim.lineofsight_component.constraint
        if not sims4.geometry.test_point_in_compound_polygon(position, sim_los_constraint.geometry.polygon):
            position = carrying_sim.position
        return (position, carrying_sim.routing_surface)

    @componentmethod
    def get_put_down_aop(self, interaction, context, alternative_multiplier=1, own_inventory_multiplier=1, object_inventory_multiplier=DEFAULT, in_slot_multiplier=DEFAULT, on_floor_multiplier=1, visibility_override=None, display_name_override=None, additional_post_run_autonomy_commodities=None, add_putdown_liability=False, **kwargs):
        sim = interaction.sim
        owner = self.owner
        if owner.transient:
            return self._get_destroy_aop(sim, **kwargs)
        put_down_strategy = self.get_put_down_strategy(parent=sim)
        if object_inventory_multiplier is DEFAULT:
            object_inventory_multiplier = sim.get_put_down_object_inventory_cost_override()
        if in_slot_multiplier is DEFAULT:
            in_slot_multiplier = sim.get_put_down_slot_cost_override()
        slot_types_and_costs = self.get_slot_types_and_costs(multiplier=in_slot_multiplier)
        (terrain_transform, terrain_routing_surface) = self._get_terrain_transform(interaction)
        objects = self._get_objects_with_inventory(interaction)
        objects = [obj for obj in objects if obj.can_access_for_putdown(sim)]
        if put_down_strategy.floor_cost is not None and on_floor_multiplier is not None:
            world_cost = put_down_strategy.floor_cost*on_floor_multiplier
        else:
            world_cost = None
        if put_down_strategy.inventory_cost is not None and own_inventory_multiplier is not None:
            sim_inventory_cost = put_down_strategy.inventory_cost*own_inventory_multiplier
        else:
            sim_inventory_cost = None
        if put_down_strategy.object_inventory_cost is not None and object_inventory_multiplier is not None:
            object_inventory_cost = put_down_strategy.object_inventory_cost*object_inventory_multiplier
        else:
            object_inventory_cost = None
        if not put_down_strategy.affordances:
            self._attempted_alternative_putdown = True
        if self._attempted_alternative_putdown and self.owner.is_sim:
            self._attempted_alternative_putdown = True
            scored_aops = []
            for scored_aop in self._gen_affordance_score_and_aops(interaction, slot_types_and_costs=slot_types_and_costs, world_cost=world_cost, sim_inventory_cost=sim_inventory_cost, object_inventory_cost=object_inventory_cost, terrain_transform=terrain_transform, terrain_routing_surface=terrain_routing_surface, objects_with_inventory=objects, visibility_override=visibility_override, display_name_override=display_name_override, additional_post_run_autonomy_commodities=additional_post_run_autonomy_commodities, multiplier=alternative_multiplier, add_putdown_liability=add_putdown_liability):
                if scored_aop.aop.test(context):
                    scored_aops.append(scored_aop)
            if scored_aops:
                scored_aops.sort(key=operator.itemgetter(0))
                return scored_aops[-1].aop
        affordance = CarryableComponent.PUT_DOWN_ANYWHERE_AFFORDANCE
        if add_putdown_liability:
            liabilities = ((PutDownLiability.LIABILITY_TOKEN, PutDownLiability(self.owner)),)
        else:
            liabilities = ()
        aop = AffordanceObjectPair(affordance, self.owner, affordance, None, slot_types_and_costs=slot_types_and_costs, world_cost=world_cost, sim_inventory_cost=sim_inventory_cost, object_inventory_cost=object_inventory_cost, terrain_transform=terrain_transform, terrain_routing_surface=terrain_routing_surface, objects_with_inventory=objects, visibility_override=visibility_override, display_name_override=display_name_override, additional_post_run_autonomy_commodities=additional_post_run_autonomy_commodities, liabilities=liabilities, **kwargs)
        self._attempted_putdown = True
        return aop

    def _gen_affordance_score_and_aops(self, interaction, slot_types_and_costs, world_cost, sim_inventory_cost, object_inventory_cost, terrain_transform, terrain_routing_surface, objects_with_inventory, visibility_override, display_name_override, additional_post_run_autonomy_commodities, multiplier=1, add_putdown_liability=False):
        put_down_strategy = self.get_put_down_strategy()
        for affordance in put_down_strategy.affordances:
            if add_putdown_liability:
                liabilities = ((PutDownLiability.LIABILITY_TOKEN, PutDownLiability(self.owner)),)
            else:
                liabilities = ()
            aop = AffordanceObjectPair(affordance, self.owner, affordance, None, slot_types_and_costs=slot_types_and_costs, world_cost=world_cost, sim_inventory_cost=sim_inventory_cost, object_inventory_cost=object_inventory_cost, terrain_transform=terrain_transform, terrain_routing_surface=terrain_routing_surface, objects_with_inventory=objects, visibility_override=visibility_override, display_name_override=display_name_override, additional_post_run_autonomy_commodities=additional_post_run_autonomy_commodities, liabilities=liabilities)
            yield ScoredAOP(multiplier, aop)

    def _get_cost_for_slot_type(self, slot_type):
        put_down_strategy = self.get_put_down_strategy()
        if slot_type in self.owner.ideal_slot_types:
            return put_down_strategy.preferred_slot_cost
        return put_down_strategy.normal_slot_cost

    def get_slot_types_and_costs(self, multiplier=1):
        slot_types_and_costs = []
        for slot_type in self.owner.all_valid_slot_types:
            cost = self._get_cost_for_slot_type(slot_type)
            if cost is not None and multiplier is not None:
                cost *= multiplier
            else:
                cost = None
            slot_types_and_costs.append((slot_type, cost))
        return slot_types_and_costs

    def _get_terrain_transform(self, interaction):
        if self.owner.is_sim or self.owner.footprint_component is None:
            return (None, None)
        else:
            sim = interaction.sim
            put_down_position = interaction.interaction_parameters.get('put_down_position')
            put_down_routing_surface = interaction.interaction_parameters.get('put_down_routing_surface')
            if put_down_position is None:
                (starting_position, starting_routing_surface) = self.get_initial_put_down_position(carrying_sim=sim)
            else:
                starting_position = put_down_position
                starting_routing_surface = put_down_routing_surface
            starting_location = placement.create_starting_location(position=starting_position, orientation=sim.orientation, routing_surface=starting_routing_surface)
            if self.owner.is_sim:
                search_flags = FGLSearchFlagsDefaultForSim | FGLSearchFlag.STAY_IN_CURRENT_BLOCK
                fgl_context_fn = functools.partial(placement.create_fgl_context_for_sim, search_flags=search_flags)
            else:
                search_flags = FGLSearchFlag.STAY_IN_CURRENT_BLOCK | FGLSearchFlag.SHOULD_TEST_ROUTING | FGLSearchFlag.CALCULATE_RESULT_TERRAIN_HEIGHTS | FGLSearchFlag.DONE_ON_MAX_RESULTS | FGLSearchFlag.SHOULD_TEST_BUILDBUY
                fgl_context_fn = functools.partial(placement.create_fgl_context_for_object, search_flags=search_flags)
            MAX_PUTDOWN_STEPS = 8
            MAX_PUTDOWN_DISTANCE = 10
            fgl_context = fgl_context_fn(starting_location, self.owner, max_steps=MAX_PUTDOWN_STEPS, max_distance=MAX_PUTDOWN_DISTANCE, height_tolerance=self.put_down_height_tolerance)
            (position, orientation) = placement.find_good_location(fgl_context)
            if position is not None:
                put_down_transform = sims4.math.Transform(position, orientation)
                return (put_down_transform, starting_routing_surface)
        return (None, None)

    def _get_objects_with_inventory(self, interaction):
        objects = []
        inventory_item = self.owner.inventoryitem_component
        if CarryableComponent.PUT_IN_INVENTORY_AFFORDANCE is not None:
            for obj in inventory_item.valid_object_inventory_gen():
                objects.append(obj)
        return objects

    def _get_destroy_aop(self, sim, **kwargs):
        affordance = CarryableComponent.PUT_DOWN_HERE_AFFORDANCE
        return AffordanceObjectPair(affordance, self.owner, affordance, None, put_down_transform=None, **kwargs)

    def reset_put_down_count(self):
        self._attempted_alternative_putdown = False
        self._attempted_putdown = False
        self._cached_put_down_strategy = None

    def on_object_carry(self, actor, *_, **__):
        if self.reslot_plumbbob is not None:
            reslot_plumbbob(actor, self.reslot_plumbbob)

    def on_object_uncarry(self, actor, *_, **__):
        if self.reslot_plumbbob is not None:
            unslot_plumbbob(actor)
