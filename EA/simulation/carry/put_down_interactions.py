from weakref import WeakSetimport randomfrom sims4.tuning.tunable import Tunable, TunableTuple, TunableReference, OptionalTunable, TunableVariant, AutoFactoryInit, HasTunableSingletonFactory, TunableList, TunableEnumEntryfrom sims4.utils import flexmethod, classproperty, constpropertyfrom singletons import DEFAULTimport enumimport sims4.logfrom animation.posture_manifest import SlotManifestEntry, SlotManifest, Handfrom animation.posture_manifest_constants import STAND_OR_SIT_CONSTRAINT, STAND_POSTURE_MANIFEST, SIT_POSTURE_MANIFESTfrom carry.carry_elements import exit_carry_while_holding, swap_carry_while_holding, enter_carry_while_holdingfrom carry.carry_postures import CarrySystemInventoryTarget, CarrySystemTerrainTarget, CarrySystemTransientTarget, CarrySystemDestroyTargetfrom carry.carry_utils import create_carry_constraint, SCRIPT_EVENT_ID_START_CARRYfrom event_testing.results import TestResultfrom interactions import ParticipantTypefrom interactions.base.basic import TunableBasicContentSetfrom interactions.base.super_interaction import SuperInteractionfrom interactions.constraints import JigConstraint, create_constraint_set, Circle, Constraint, Nowhere, OceanStartLocationConstraint, WaterDepthIntervals, WaterDepthIntervalConstraintfrom objects.components.types import CARRYABLE_COMPONENTfrom objects.helpers.create_object_helper import CreateObjectHelperfrom objects.object_enums import ResetReasonfrom objects.slots import get_surface_height_parameter_for_objectfrom objects.terrain import TerrainSuperInteractionfrom postures.posture_specs import PostureSpecVariablefrom postures.posture_state_spec import PostureStateSpecimport element_utilsimport objects.game_objectimport serviceslogger = sims4.log.Logger('PutDownInteractions')EXCLUSION_MULTIPLIER = NoneOPTIMAL_MULTIPLIER = 0DISCOURAGED_MULTIPLIER = 100PUT_DOWN_GEOMETRY_RADIUS = 1.0
def put_down_geometry_constraint_gen(sim, target):
    if target.is_in_inventory():
        yield Circle(sim.position, PUT_DOWN_GEOMETRY_RADIUS, routing_surface=sim.routing_surface)
    elif hasattr(target, 'get_carry_transition_constraint'):
        yield target.get_carry_transition_constraint(sim, target.position, target.routing_surface)
    else:
        logger.error('Trying to call get_carry_transition_constraint on Object {} that has no such attribute.\n                            Definition: {}\n                            Sim: {}\n                            ', target, target.definition, sim, owner='trevor')

class AggregateObjectOwnership(enum.IntFlags):
    NO_OWNER = 1
    SAME_AS_TARGET = 2
    ACTIVE_HOUSEHOLD = 4

class PutDownChooserInteraction(SuperInteraction):

    class _ObjectToPutDownTarget(HasTunableSingletonFactory, AutoFactoryInit):

        def __call__(self, interaction, sim=DEFAULT, target=DEFAULT):
            target = target if target is not DEFAULT else interaction.target
            return target

    class _ObjectToPutDownFromHand(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'hand': TunableVariant(locked_args={'right/mouth': Hand.RIGHT, 'left/back': Hand.LEFT}, default='right/mouth')}

        def __call__(self, interaction, sim=DEFAULT, target=DEFAULT):
            sim = sim if sim is not DEFAULT else interaction.sim
            posture_state = sim.posture_state
            if self.hand == Hand.RIGHT:
                return posture_state.right.target
            elif self.hand == Hand.LEFT:
                return posture_state.left.target

    INSTANCE_TUNABLES = {'object_to_put_down': TunableVariant(description='\n            Define which object the Sim is to put down.\n            ', from_interaction=_ObjectToPutDownTarget.TunableFactory(), from_hand=_ObjectToPutDownFromHand.TunableFactory(), default='from_interaction')}

    def _run_interaction_gen(self, timeline):
        obj = self.object_to_put_down(self)
        if obj is None:
            return True
        carryable_component = obj.carryable_component
        if carryable_component is None:
            logger.error("Attempting to run {} on target {} but it doesn't have a carryable component.", self, obj, owner='tastle')
            return False
        debug_name = 'PutDownChooser'
        context = self.context.clone_for_continuation(self)
        if carryable_component.prefer_owning_sim_inventory_when_not_on_home_lot and obj.get_household_owner_id() == self.sim.household_id and not self.sim.on_home_lot:
            aop = obj.get_put_down_aop(self, context, own_inventory_multiplier=OPTIMAL_MULTIPLIER, on_floor_multiplier=DISCOURAGED_MULTIPLIER, visibility_override=self.visible, display_name_override=self.display_name, add_putdown_liability=True, must_run=self.must_run, debug_name=debug_name)
        else:
            aop = obj.get_put_down_aop(self, context, visibility_override=self.visible, display_name_override=self.display_name, add_putdown_liability=True, must_run=self.must_run, debug_name=debug_name)
        execute_result = aop.test_and_execute(context)
        if not execute_result:
            logger.error('Put down test failed.\n                aop:{}\n                test result:{} [tastle/trevorlindsey]'.format(aop, execute_result.test_result))
            self.sim.reset(ResetReason.RESET_EXPECTED, self, 'Put down test failed.')
        return execute_result

    @classproperty
    def is_putdown(cls):
        return True

    @classproperty
    def requires_target_support(cls):
        return False

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        for constraint in super(SuperInteraction, cls)._constraint_gen(sim, target, participant_type=participant_type):
            yield constraint
        obj = cls.object_to_put_down(inst, sim=sim, target=target)
        yield create_carry_constraint(obj, debug_name='CarryForPutDown')
        yield Circle(sim.position, PUT_DOWN_GEOMETRY_RADIUS, routing_surface=sim.routing_surface)

    def is_object_valid(self, obj, distance_estimator):
        return True

class PutAwayBase(SuperInteraction):

    def _run_interaction_gen(self, timeline):
        yield from super()._run_interaction_gen(timeline)
        main_social_group = self.sim.get_main_group()
        if main_social_group is not None:
            main_social_group.execute_adjustment_interaction(self.sim, force_allow_posture_changes=True)

    def is_object_valid(self, obj, distance_estimator):
        return True

class PutInInventoryInteraction(PutAwayBase):
    INSTANCE_TUNABLES = {'basic_content': TunableBasicContentSet(no_content=True, default='no_content')}

    @classmethod
    def _test(cls, *args, target_with_inventory=None, **interaction_parameters):
        if target_with_inventory is not None:
            if not isinstance(target_with_inventory, objects.game_object.GameObject):
                return TestResult(False, 'target_with_inventory must be a GameObject: {}', target_with_inventory)
            if target_with_inventory.inventory_component is None:
                return TestResult(False, 'target_with_inventory must have an inventory: {}', target_with_inventory)
        return super()._test(*args, target_with_inventory=target_with_inventory, **interaction_parameters)

    def __init__(self, *args, target_with_inventory=None, **kwargs):
        super().__init__(*args, **kwargs)
        if target_with_inventory is None:
            target_with_inventory = self.sim
        self._carry_system_target = CarrySystemInventoryTarget(self.sim, self.target, True, target_with_inventory)

    @constproperty
    def is_put_in_inventory():
        return True

    @classproperty
    def is_putdown(cls):
        return True

    def build_basic_content(self, sequence, **kwargs):
        sequence = super().build_basic_content(sequence, **kwargs)
        return exit_carry_while_holding(self, sequence=sequence, use_posture_animations=True, carry_system_target=self._carry_system_target)

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        for constraint in super(SuperInteraction, cls)._constraint_gen(sim, target, participant_type=participant_type):
            yield constraint
        yield create_carry_constraint(target, debug_name='CarryForPutDown')
        if inst is not None:
            yield inst._carry_system_target.get_constraint(sim)

    @classproperty
    def requires_target_support(cls):
        return False

class CollectManyInteraction(SuperInteraction):
    INTERACTION_TARGET = 'interaction_target'
    INSTANCE_TUNABLES = {'aggregate_object': TunableVariant(description='\n            The type of object to use as the aggregate object.  If a definition\n            is specified, the aggregate object will be created using that\n            definition.  If "interaction_target" is specified, the aggregate object\n            will be created using the definition of the interaction target.\n            ', definitions=TunableList(description='\n                A list of object definitions. One of them will be chosen \n                randomly and created as part of this interaction to represent \n                the many collected objects the participant has picked up.\n                ', tunable=TunableReference(manager=services.definition_manager()), unique_entries=True), locked_args={'interaction_target': INTERACTION_TARGET, 'no_aggregate_object': None}, default='no_aggregate_object'), 'aggregate_object_owner': TunableEnumEntry(description='\n            Specify the owner of the newly created aggregate object.\n            ', tunable_type=AggregateObjectOwnership, default=AggregateObjectOwnership.SAME_AS_TARGET), 'destroy_original_object': Tunable(description="\n            If checked, the original object (the target of this interaction),\n            will be destroyed and replaced with the specified aggregate object.\n            If unchecked, the aggregate object will be created in the Sim's\n            hand, but the original object will not be destroyed.\n            ", tunable_type=bool, default=True)}
    DIRTY_DISH_ACTOR_NAME = 'dirtydish'
    ITEMS_PARAM = 'items'
    _object_create_helper = None
    _collected_targets = WeakSet()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_carry_target = None

    @property
    def create_object_owner(self):
        return self.sim

    @property
    def _aggregate_object_definition(self):
        if self.aggregate_object is None:
            return
        if self.aggregate_object == self.INTERACTION_TARGET:
            return self.target.definition
        return random.choice(self.aggregate_object)

    @property
    def create_target(self):
        if self.context.carry_target is not None:
            return
        return self._aggregate_object_definition

    @property
    def created_target(self):
        return self.context.carry_target

    @classmethod
    def _test(cls, target, context, **interaction_parameters):
        if target is not None and target in cls._collected_targets:
            return TestResult(False, 'Target was already collected.')
        if cls.destroy_original_object and context.sim.posture_state.is_carrying(target):
            return TestResult(False, 'Target to destroy is being carried by this Sim.')
        return super()._test(target, context, **interaction_parameters)

    def setup_asm_default(self, asm, *args, **kwargs):
        result = super().setup_asm_default(asm, *args, **kwargs)
        if self.target is not None:
            surface_height = get_surface_height_parameter_for_object(self.target, sim=self.sim)
            asm.set_parameter('surfaceHeight', surface_height)
        if self._original_carry_target is not None:
            param_overrides = self._original_carry_target.get_param_overrides(self.DIRTY_DISH_ACTOR_NAME, only_for_keys=(self.ITEMS_PARAM,))
            if param_overrides is not None:
                asm.update_locked_params(param_overrides)
        return result

    def build_basic_content(self, sequence=(), **kwargs):
        self.store_event_handler(self._xevt_callback, handler_id=SCRIPT_EVENT_ID_START_CARRY)
        if self._aggregate_object_definition is None or self.carry_target is not None and self._aggregate_object_definition is self.carry_target.definition:
            return super().build_basic_content(sequence, **kwargs)
        if self.carry_target is not None:
            swap_carry = True
            self._original_carry_target = self.carry_target
        else:
            swap_carry = False
        self._object_create_helper = CreateObjectHelper(self.sim, self._aggregate_object_definition.id, self, tag='Aggregate object created for a CollectManyInteraction.', init=self._setup_created_object)
        super_build_basic_content = super().build_basic_content

        def grab_sequence(timeline):
            nonlocal sequence
            sequence = super_build_basic_content(sequence)
            if swap_carry:
                sequence = swap_carry_while_holding(self, self._original_carry_target, self.created_target, callback=self._object_create_helper.claim, sequence=sequence)
            else:
                sequence = enter_carry_while_holding(self, self.created_target, callback=self._object_create_helper.claim, create_si_fn=None, sequence=sequence)
            _ = yield from element_utils.run_child(timeline, sequence)

        return self._object_create_helper.create(grab_sequence)

    def _setup_created_object(self, created_object):
        if self.aggregate_object_owner & AggregateObjectOwnership.SAME_AS_TARGET:
            if self.target is not None:
                created_object.set_household_owner_id(self.target.get_household_owner_id())
        elif self.aggregate_object_owner & AggregateObjectOwnership.ACTIVE_HOUSEHOLD:
            active_household_id = services.active_household_id()
            if active_household_id is not None:
                created_object.set_household_owner_id(active_household_id)

    def _xevt_callback(self, *_, **__):
        if self.target is not None:
            if self._object_create_helper is None:
                for statistic in self.target.statistic_tracker:
                    self.carry_target.statistic_tracker.add_value(statistic.stat_type, statistic.get_value())
            elif self._original_carry_target is not None:
                for statistic in self._original_carry_target.statistic_tracker:
                    self.carry_target.statistic_tracker.add_value(statistic.stat_type, statistic.get_value())
            elif self.aggregate_object is self.INTERACTION_TARGET:
                self.carry_target.copy_state_values(self.target)
            else:
                for statistic in self.target.statistic_tracker:
                    self.carry_target.statistic_tracker.set_value(statistic.stat_type, statistic.get_value())
        if self.carry_target is not None and self.destroy_original_object and self.target is not None:
            self._collected_targets.add(self.target)
            self.target.transient = True
            self.target.remove_from_client()
        if self._original_carry_target is not None:
            self._collected_targets.add(self._original_carry_target)
            self._original_carry_target.transient = True
            self._original_carry_target.remove_from_client()

    @classproperty
    def requires_target_support(cls):
        return False

class PutAwayInteraction(SuperInteraction):

    def _run_interaction_gen(self, timeline):
        context = self.context.clone_for_continuation(self)
        aop = self.target.get_put_down_aop(self, context, alternative_multiplier=EXCLUSION_MULTIPLIER, own_inventory_multiplier=EXCLUSION_MULTIPLIER, object_inventory_multiplier=OPTIMAL_MULTIPLIER, in_slot_multiplier=EXCLUSION_MULTIPLIER, on_floor_multiplier=EXCLUSION_MULTIPLIER, visibility_override=self.visible, display_name_override=self.display_name, additional_post_run_autonomy_commodities=self.post_run_autonomy_commodities.requests, debug_name='PutAwayInteraction')
        if aop is not None:
            return aop.test_and_execute(context)
        return False

    @classproperty
    def is_putdown(cls):
        return True

    @classproperty
    def requires_target_support(cls):
        return False

    def _get_post_run_autonomy(self):
        pass

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        for constraint in super(SuperInteraction, cls)._constraint_gen(sim, target, participant_type=participant_type):
            yield constraint
        yield create_carry_constraint(target, debug_name='CarryForPutDown')
        yield from put_down_geometry_constraint_gen(sim, target)

    def is_object_valid(self, obj, distance_estimator):
        return True

class PutDownQuicklySuperInteraction(PutAwayBase):

    def _run_interaction_gen(self, timeline):
        context = self.context.clone_for_continuation(self)
        aop = self.target.get_put_down_aop(self, context, own_inventory_multiplier=OPTIMAL_MULTIPLIER, on_floor_multiplier=DISCOURAGED_MULTIPLIER, in_slot_multiplier=DISCOURAGED_MULTIPLIER, object_inventory_multiplier=DISCOURAGED_MULTIPLIER, visibility_override=self.visible, display_name_override=self.display_name, add_putdown_liability=True, must_run=self.must_run, debug_name='PutDownQuicklyInteraction')
        execute_result = aop.test_and_execute(context)
        if not execute_result:
            logger.error('Put down test failed.\n                aop:{}\n                test result:{} [tastle]'.format(aop, execute_result.test_result))
            self.sim.reset(ResetReason.RESET_EXPECTED, self, 'Put down test failed.')
        return execute_result

    @classproperty
    def is_putdown(cls):
        return True

    @classproperty
    def requires_target_support(cls):
        return False

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        for constraint in super(SuperInteraction, cls)._constraint_gen(sim, target, participant_type=participant_type):
            yield constraint
        yield create_carry_constraint(target, debug_name='CarryForPutDown')
        yield from put_down_geometry_constraint_gen(sim, target)

class AddToWorldSuperInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'basic_content': TunableBasicContentSet(no_content=True, default='no_content'), 'put_down_cost_multipliers': TunableTuple(description='\n            Multipliers to be applied to the different put downs possible when\n            determining the best put down aop.\n            ', in_slot_multiplier=OptionalTunable(enabled_by_default=True, tunable=Tunable(description='\n                    Cost multiplier for sims putting the object down in a slot.\n                    ', tunable_type=float, default=1)), on_floor_multiplier=OptionalTunable(enabled_by_default=True, tunable=Tunable(description='\n                    Cost multiplier for sims putting the object down on the\n                    floor.\n                    ', tunable_type=float, default=1)))}

    @flexmethod
    def skip_test_on_execute(cls, inst):
        return True

    def _run_interaction_gen(self, timeline):
        self.target.inventoryitem_component.clear_previous_inventory()
        context = self.context.clone_for_continuation(self)
        aop = self.target.get_put_down_aop(self, context, own_inventory_multiplier=EXCLUSION_MULTIPLIER, object_inventory_multiplier=EXCLUSION_MULTIPLIER, in_slot_multiplier=self.put_down_cost_multipliers.in_slot_multiplier, on_floor_multiplier=self.put_down_cost_multipliers.on_floor_multiplier, visibility_override=self.visible, display_name_override=self.display_name, debug_name='AddToWorldSuperInteraction')
        if aop is not None:
            return aop.test_and_execute(context)
        return False

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        for constraint in super(SuperInteraction, cls)._constraint_gen(sim, target, participant_type=participant_type):
            yield constraint
        carry_constraint = create_carry_constraint(target, debug_name='CarryForAddInWorld')
        total_constraint = carry_constraint.intersect(STAND_OR_SIT_CONSTRAINT)
        yield total_constraint
        yield from put_down_geometry_constraint_gen(sim, target)

    @classproperty
    def is_putdown(cls):
        return True

    @classproperty
    def requires_target_support(cls):
        return False

    def is_object_valid(self, obj, distance_estimator):
        return True

class SwipeAddToWorldSuperInteraction(SuperInteraction):

    def _run_interaction_gen(self, timeline):
        liability = self.get_liability(JigConstraint.JIG_CONSTRAINT_LIABILITY)
        if self.sim.inventory_component.try_remove_object_by_id(self.target.id):
            new_location = self.target.location.clone(transform=liability.jig.transform, routing_surface=liability.jig.routing_surface)
            self.target.inventoryitem_component.clear_previous_inventory()
            self.target.opacity = 0
            self.target.location = new_location
            self.target.fade_in()

    @classproperty
    def is_putdown(cls):
        return True

    def is_object_valid(self, obj, distance_estimator):
        return True

class PutDownHereInteraction(TerrainSuperInteraction):

    def __init__(self, *args, put_down_transform=None, **kwargs):
        super().__init__(*args, **kwargs)
        if put_down_transform is None:
            put_down_transform = self.target.transform
        if self.carry_target.transient:
            carry_system_target = CarrySystemTransientTarget(self.carry_target, True)
        else:
            carry_system_target = CarrySystemTerrainTarget(self.sim, self.carry_target, True, put_down_transform)
        self._carry_system_target = carry_system_target

    @classproperty
    def is_putdown(cls):
        return True

    def build_basic_content(self, sequence, **kwargs):
        sequence = super().build_basic_content(sequence, **kwargs)
        return exit_carry_while_holding(self, sequence=sequence, use_posture_animations=True, carry_system_target=self._carry_system_target)

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        for constraint in super(TerrainSuperInteraction, cls)._constraint_gen(sim, target, participant_type=participant_type):
            yield constraint
        carry_target = inst.carry_target if inst is not None else None
        if carry_target is not None:
            yield create_carry_constraint(carry_target, debug_name='CarryForPutDown')
            if carry_target.transient or inst._carry_system_target.transform is not None:
                yield carry_target.get_carry_transition_constraint(sim, inst._carry_system_target.transform.translation, sim.routing_surface)

    @classproperty
    def requires_target_support(cls):
        return False

    def _run_interaction_gen(self, timeline):
        yield from super()._run_interaction_gen(timeline)
        execute_social_adjustment = True
        carryable_component = self.carry_target.get_component(CARRYABLE_COMPONENT)
        if carryable_component.defer_putdown:
            execute_social_adjustment = False
        if carryable_component is not None and execute_social_adjustment:
            main_social_group = self.sim.get_main_group()
            if main_social_group is not None:
                main_social_group.execute_adjustment_interaction(self.sim)

    def is_object_valid(self, obj, distance_estimator):
        return True

class PutDownInSlotInteraction(PutAwayBase):
    INSTANCE_TUNABLES = {'basic_content': TunableBasicContentSet(no_content=True, default='no_content')}

    def __init__(self, *args, slot_types_and_costs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if slot_types_and_costs is None:
            in_slot_multiplier = self.sim.get_put_down_slot_cost_override()
            slot_types_and_costs = self.carry_target.carryable_component.get_slot_types_and_costs(multiplier=in_slot_multiplier)
        self._slot_types_and_costs = slot_types_and_costs

    @classmethod
    def _test(cls, target, context, slot=None, **kwargs):
        carried_obj = context.carry_target if context.carry_target is not None else target
        if carried_obj.transient:
            return TestResult(False, 'Target is transient.')
        if slot is not None and not slot.is_valid_for_placement(obj=carried_obj):
            return TestResult(False, 'destination slot is occupied or not enough room for {}', carried_obj)
        return TestResult.TRUE

    @classproperty
    def is_putdown(cls):
        return True

    @classproperty
    def requires_target_support(cls):
        return False

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        inst_or_cls = inst if inst is not None else cls
        for constraint in super(SuperInteraction, inst_or_cls)._constraint_gen(sim, target, participant_type=participant_type):
            yield constraint
        if inst is not None:
            slot_constraint = create_put_down_in_slot_type_constraint(sim, inst.carry_target, inst._slot_types_and_costs, target=target)
            yield slot_constraint

def create_put_down_in_slot_type_constraint(sim, carry_target, slot_types_and_costs, target=None):
    constraints = []
    for (slot_type, cost) in slot_types_and_costs:
        if cost is None:
            pass
        else:
            if target is not None and target is not carry_target:
                slot_manifest_entry = SlotManifestEntry(carry_target, PostureSpecVariable.INTERACTION_TARGET, slot_type)
            else:
                slot_manifest_entry = SlotManifestEntry(carry_target, PostureSpecVariable.ANYTHING, slot_type)
            slot_manifest = SlotManifest((slot_manifest_entry,))
            posture_state_spec_stand = PostureStateSpec(STAND_POSTURE_MANIFEST, slot_manifest, PostureSpecVariable.ANYTHING)
            posture_constraint_stand = Constraint(debug_name='PutDownInSlotTypeConstraint_Stand', posture_state_spec=posture_state_spec_stand, cost=cost)
            constraints.append(posture_constraint_stand)
            posture_state_spec_sit = PostureStateSpec(SIT_POSTURE_MANIFEST, slot_manifest, PostureSpecVariable.ANYTHING)
            posture_constraint_sit = Constraint(debug_name='PutDownInSlotTypeConstraint_Sit', posture_state_spec=posture_state_spec_sit, cost=cost)
            constraints.append(posture_constraint_sit)
    if not constraints:
        return Nowhere('Carry Target has no slot types or costs tuned for put down: {} Sim:{}', carry_target, sim)
    final_constraint = create_constraint_set(constraints)
    return final_constraint

def create_put_down_on_ground_constraint(sim, target, terrain_transform, routing_surface=DEFAULT, cost=0):
    if cost is None or terrain_transform is None:
        return Nowhere('Put Down On Ground with either no Cost({}) or Transform({}) Sim:{} Target:{}', cost, terrain_transform, sim, target)
    routing_surface = sim.routing_surface if routing_surface is DEFAULT else routing_surface
    swipe_constraint = target.get_carry_transition_constraint(sim, terrain_transform.translation, routing_surface)
    if target.is_sim:
        if target.should_be_swimming_at_position(terrain_transform.translation, routing_surface.secondary_id, check_can_swim=False):
            DEFAULT_SIM_PUT_DOWN_OCEAN_CONSTRAINT_RADIUS = 10.0
            DEFAULT_SIM_PUT_DOWN_OCEAN_INTERVAL = WaterDepthIntervals.WET
            start_constraint = OceanStartLocationConstraint.create_simple_constraint(DEFAULT_SIM_PUT_DOWN_OCEAN_INTERVAL, DEFAULT_SIM_PUT_DOWN_OCEAN_CONSTRAINT_RADIUS, target, target_position=terrain_transform.translation, routing_surface=routing_surface)
            depth_constraint = WaterDepthIntervalConstraint.create_water_depth_interval_constraint(target, DEFAULT_SIM_PUT_DOWN_OCEAN_INTERVAL)
            swipe_constraint = swipe_constraint.generate_alternate_geometry_constraint(start_constraint.geometry)
            swipe_constraint = swipe_constraint.generate_alternate_water_depth_constraint(depth_constraint.get_min_water_depth(), depth_constraint.get_max_water_depth())
        swipe_constraint = swipe_constraint._copy(_multi_surface=False)
    carry_constraint = create_carry_constraint(target, debug_name='CarryForPutDownOnGround')
    final_constraint = swipe_constraint.intersect(carry_constraint).intersect(STAND_OR_SIT_CONSTRAINT)
    return final_constraint.generate_constraint_with_cost(cost)

def create_put_down_in_inventory_constraint(inst, sim, target, targets_with_inventory, cost=0):
    if cost is None or not targets_with_inventory:
        return Nowhere('No Cost({}) or No Targets with an inventory of the correct type. Sim: {} Target: {}', cost, sim, target)
    carry_constraint = create_carry_constraint(target, debug_name='CarryForPutDownInInventory')
    carry_constraint = carry_constraint.generate_constraint_with_cost(cost)
    object_constraints = []
    for target_with_inventory in targets_with_inventory:
        constraint = target_with_inventory.get_inventory_access_constraint(sim, True, target)
        if constraint is None:
            logger.error('{} failed to get inventory access constraint for {}, \n            If you cannot put down objects in this inventory, you should uncheck: Components -> Inventory -> Allow Putdown In Inventory.\n            If you can, you need to properly tune GetPut', sim, target, owner='tastle')
            return Nowhere('Failed Inventory Access Constraint: See Gameplay Console for error.')
        constraint = constraint.apply_posture_state(None, inst.get_constraint_resolver(None))
        object_constraints.append(constraint)
    final_constraint = create_constraint_set(object_constraints)
    final_constraint = carry_constraint.intersect(final_constraint)
    return final_constraint

class PutDownAnywhereInteraction(PutAwayBase):

    def __init__(self, *args, slot_types_and_costs, world_cost, sim_inventory_cost, object_inventory_cost, terrain_transform, terrain_routing_surface, objects_with_inventory, visibility_override=None, display_name_override=None, debug_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._slot_types_and_costs = slot_types_and_costs
        self._world_cost = world_cost
        self._sim_inventory_cost = sim_inventory_cost
        self._object_inventory_cost = object_inventory_cost
        self._terrain_transform = terrain_transform
        self._objects_with_inventory = objects_with_inventory
        self._slot_constraint = None
        self._world_constraint = None
        self._sim_inventory_constraint = None
        self._object_inventory_constraint = None
        if visibility_override is not None:
            self.visible = visibility_override
        if display_name_override is not None:
            self.display_name = display_name_override
        self._max_route_distance = None
        if self._world_cost is None and self._sim_inventory_cost is None or not self._slot_types_and_costs:
            self._max_route_distance = None
        else:
            if self._world_cost is None:
                best_non_route_cost = self._sim_inventory_cost
            elif self._sim_inventory_cost is None:
                best_non_route_cost = self._world_cost
            else:
                best_non_route_cost = min(self._world_cost, self._sim_inventory_cost)
            costs = tuple(slot_and_score[1] for slot_and_score in self._slot_types_and_costs if slot_and_score[1] is not None)
            if costs:
                best_slot_type_cost = min(costs)
                if best_slot_type_cost > best_non_route_cost:
                    self._max_route_distance = best_non_route_cost
                else:
                    self._max_route_distance = best_non_route_cost - best_slot_type_cost

    @classproperty
    def is_putdown(cls):
        return True

    @classproperty
    def requires_target_support(cls):
        return False

    def build_basic_content(self, sequence, **kwargs):
        sequence = super().build_basic_content(sequence, **kwargs)
        constraint_intersection = self.sim.posture_state.constraint_intersection
        if self.target is None:
            return
        target_parent = self.target.parent
        if target_parent is not None and (target_parent.is_sim or constraint_intersection.intersect(self._slot_constraint).valid):
            return sequence
        can_exit_carry = False
        if target_parent is not None:
            if target_parent is self.sim:
                can_exit_carry = True
        elif self.sim.posture_state.is_carrying(self.target):
            can_exit_carry = True
        if can_exit_carry:
            if constraint_intersection.intersect(self._object_inventory_constraint).valid:
                carry_system_target = CarrySystemInventoryTarget(self.sim, self.target, True, self.sim.posture_state.surface_target)
                return exit_carry_while_holding(self, use_posture_animations=True, carry_system_target=carry_system_target, sequence=sequence)
            world_valid = constraint_intersection.intersect(self._world_constraint).valid and self._world_cost is not None
            sim_inventory_valid = constraint_intersection.intersect(self._sim_inventory_constraint).valid and self._sim_inventory_cost is not None
            if world_valid and sim_inventory_valid:
                sim_inv_chosen = self._sim_inventory_cost <= self._world_cost
            else:
                sim_inv_chosen = sim_inventory_valid
            if sim_inv_chosen:
                carry_system_target = CarrySystemInventoryTarget(self.sim, self.target, True, self.sim)
                return exit_carry_while_holding(self, use_posture_animations=True, carry_system_target=carry_system_target, sequence=sequence)
            if self.sim.posture.is_vehicle and not self.target.transient:
                carry_system_target = CarrySystemDestroyTarget(self.target, True)
                return exit_carry_while_holding(self, use_posture_animations=True, carry_system_target=carry_system_target, sequence=sequence)
            else:
                carry_system_target = CarrySystemTerrainTarget(self.sim, self.target, True, self._terrain_transform)
                return exit_carry_while_holding(self, use_posture_animations=True, carry_system_target=carry_system_target, sequence=sequence)

    @flexmethod
    def _constraint_gen(cls, inst, sim, target, participant_type=ParticipantType.Actor):
        inst_or_cls = inst if inst is not None else cls
        yield from super(__class__, inst_or_cls)._constraint_gen(sim, target, participant_type=participant_type)
        if inst is not None:
            inst._slot_constraint = create_put_down_in_slot_type_constraint(sim, target, inst._slot_types_and_costs)
            inst._world_constraint = create_put_down_on_ground_constraint(sim, target, inst._terrain_transform, cost=inst._world_cost)
            inst._sim_inventory_constraint = create_put_down_in_inventory_constraint(inst, sim, target, targets_with_inventory=[sim], cost=inst._sim_inventory_cost)
            inst._object_inventory_constraint = create_put_down_in_inventory_constraint(inst, sim, target, targets_with_inventory=inst._objects_with_inventory, cost=inst._object_inventory_cost)
            if inst._slot_constraint.valid or (inst._world_constraint.valid or inst._sim_inventory_constraint.valid) or inst._object_inventory_constraint.valid:
                constraints = [inst._slot_constraint, inst._world_constraint, inst._sim_inventory_constraint, inst._object_inventory_constraint]
                final_constraint = create_constraint_set(constraints)
            else:
                final_constraint = Nowhere('PutDownAnywhere could not create any valid putdown constraint.')
            yield final_constraint

    @flexmethod
    def apply_posture_state_and_interaction_to_constraint(cls, inst, posture_state, *args, invalid_expected=False, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        result = super(SuperInteraction, inst_or_cls).apply_posture_state_and_interaction_to_constraint(posture_state, *args, invalid_expected=True, **kwargs)
        if result.valid or not invalid_expected:
            logger.error('Failed to resolve {} with posture state {}. Result: {}', inst_or_cls, posture_state, result, owner='maxr', trigger_breakpoint=True)
        return result

    def is_object_valid(self, obj, distance_estimator):
        if self._max_route_distance is None:
            return True
        locations = obj.get_locations_for_posture(None)
        for location in locations:
            estimated_distance = distance_estimator.estimate_distance((distance_estimator.sim.routing_location, location))
            if estimated_distance < self._max_route_distance:
                return True
        return False
