from _weakrefset import WeakSetfrom animation.animation_utils import flush_all_animationsfrom carry.carry_elements import enter_carry_while_holdingfrom carry.carry_postures import CarryingObjectfrom carry.carry_utils import SCRIPT_EVENT_ID_STOP_CARRY, PARAM_CARRY_TRACKfrom crafting.crafting_interactions import CraftingPhaseSuperInteractionMixin, CraftingPhaseCreateObjectSuperInteractionfrom element_utils import build_element, build_critical_sectionfrom event_testing.results import TestResultfrom interactions import ParticipantTypefrom interactions.aop import AffordanceObjectPairfrom interactions.base.interaction import Interactionfrom interactions.base.super_interaction import SuperInteractionfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.interaction_liabilities import CANCEL_INTERACTION_ON_EXIT_LIABILITYfrom interactions.utils.loot import LootOperationListfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReference, Tunable, TunableEnumEntry, OptionalTunableimport element_utilsimport servicesimport sims4.loglogger = sims4.log.Logger('ServeInteractions')SERVING_TUNING_GROUP = 'Serving Tunings'
def find_serve_target(target, object_info, deliver_part=None):
    object_or_part = deliver_part or target
    if object_or_part.is_part or not object_or_part.parts:
        return object_or_part
    part_owner = object_or_part.part_owner if object_or_part.is_part else object_or_part
    for part in part_owner.parts:
        for runtime_slot in part.get_runtime_slots_gen():
            if runtime_slot.decorative:
                pass
            elif not runtime_slot.is_valid_for_placement(definition=object_info.definition, objects_to_ignore=runtime_slot.children):
                pass
            else:
                return part
    if part_owner.parts:
        logger.error('Could not find a Part on {} with valid slots for {}. Are you sure both objects have the correct slot type set?', part_owner, object_info.definition, owner='rmccord')
    return part_owner

def push_object_pick_up_and_consume(parent_crafting_interaction, order_sim, object_to_serve, consume_affordance_override=None):
    if order_sim is None or order_sim.si_state is None or order_sim.is_being_destroyed:
        object_to_serve.destroy(source=parent_crafting_interaction, cause='Destroying crafted object because ordering Sim no longer exists.')
        return TestResult(False, 'Ordering Sim is None or being destroyed.')
    if not (parent_crafting_interaction.sim is order_sim and (parent_crafting_interaction.process.orders or parent_crafting_interaction.should_push_consume(check_phase=False))):
        return TestResult(False, 'Ordering Sim is not supposed to pick up the object if they are not thirsty.')
    context = InteractionContext(order_sim, parent_crafting_interaction.source, parent_crafting_interaction.priority, insert_strategy=QueueInsertStrategy.NEXT, preferred_carrying_sim=parent_crafting_interaction.sim)
    if context.sim is None:
        logger.warn('Sim is no longer valid. Do not push interaction on destroyed Sim: {}', order_sim, owner='rmccord')
        return TestResult.TRUE
    affordance = object_to_serve.get_consume_affordance() if consume_affordance_override is None else consume_affordance_override
    if affordance is None:
        logger.error('{} cannot find the consume affordance for the final product {}.', parent_crafting_interaction, object_to_serve, owner='rmccord')
        return TestResult(False, '{} cannot find consume affordance'.format(object_to_serve))
    return order_sim.push_super_affordance(affordance, object_to_serve, context)

class ServeObjectMixin:

    def __init__(self, *args, order_sim=None, object_info=None, deliver_part=None, consume_affordance_override=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_sim = order_sim
        self._object_info = object_info
        self._deliver_part = deliver_part
        self.dest_slot = None
        self.order_sim_cancel_entries = None
        self.consume_affordance_override = consume_affordance_override

    @property
    def disable_carry_interaction_mask(self):
        return True

    def _clean_up_cancel_order_entries(self):
        if self.order_sim_cancel_entries is not None:
            for affordance_or_interaction in tuple(self.order_sim_cancel_entries):
                if isinstance(affordance_or_interaction, Interaction):
                    interaction = affordance_or_interaction
                else:
                    interaction = self.order_sim.si_state.get_si_by_affordance(affordance_or_interaction)
                if interaction is not None:
                    interaction.cancel(FinishingType.CRAFTING, cancel_reason_msg="Canceled Ordering Sim's Wait Affordance.")

    def _custom_claim_callback(self):
        if self.phase.object_info_is_final_product:
            lot_owning_household = services.owning_household_of_active_lot()
            if lot_owning_household is not None:
                self.object_to_serve.set_household_owner_id(lot_owning_household.id)
            elif self.order_sim is not None:
                self.object_to_serve.set_household_owner_id(self.order_sim.sim_info.household_id)
            self.process.apply_quality_and_value(self.object_to_serve)
            self.object_to_serve.on_crafting_process_finished()
            loot = LootOperationList(self.get_resolver(), self.process.recipe.final_product.loot_list)
            loot.apply_operations()
        self.add_exit_function(self._clean_up_cancel_order_entries)
lock_instance_tunables(ServeObjectMixin, _saveable=None)
class ServeObjectToSlotMixin(ServeObjectMixin):
    INSTANCE_TUNABLES = {'put_down_object_xevt_id': Tunable(int, 101, description='Xevt id for when the object should be parented to the slot.')}
    old_object = None
    put_down = False

    def _custom_content_sequence(self, sequence):

        def select_serve_slot(*_, **__):
            object_or_part = self._deliver_part or self.target
            old_age = 0
            old_slot = None
            self.dest_slot = None
            for runtime_slot in object_or_part.get_runtime_slots_gen():
                if runtime_slot.decorative:
                    pass
                elif not runtime_slot.is_valid_for_placement(obj=self.object_to_serve, objects_to_ignore=runtime_slot.children):
                    pass
                elif runtime_slot.empty:
                    self.dest_slot = runtime_slot
                    break
                else:
                    child_objects = runtime_slot.children
                    for child in child_objects:
                        if child.objectage_component and not child.in_use_by(self.sim):
                            current_age = child.get_current_age()
                            if current_age > old_age:
                                self.old_object = child
                                old_age = current_age
                                old_slot = runtime_slot
            if self.dest_slot is None and self.old_object is not None:
                logger.assert_raise(not self.old_object.in_use_by(self.sim), 'Chose to destroy an old object ({}) still in use by actor ({}) in ({}) to place new object ({}) for interaction({}).  Please do more->GSI', self.old_object, self.sim, ', '.join(str(reservation_handler) for reservation_handler in self.old_object.get_reservation_handlers()), self.object_to_serve, self, owner='nabaker')
                self.dest_slot = old_slot

                def destroy_old_object():
                    logger.assert_raise(not self.old_object.in_use_by(self.sim), 'Chose to destroy an old object ({}) still in use by actor ({}) in ({}) to place new object ({}) for interaction({}).  Please do more->GSI', self.old_object, self.sim, ', '.join(str(reservation_handler) for reservation_handler in self.old_object.get_reservation_handlers()), self.object_to_serve, self, owner='jdimailig')
                    self.old_object.destroy(source=self, cause='Destroying an old object ({}) to make room for a new one ({}).'.format(self.old_object, self.object_to_serve))
                    self.old_object = None

                self.add_exit_function(destroy_old_object)
            if self.dest_slot is not None:
                return True
            logger.error('No non-deco slots found on {} that support {}.', object_or_part, self.object_to_serve, owner='rmccord')
            return False

        return (select_serve_slot, sequence)

    def _custom_claim_callback(self):
        super()._custom_claim_callback()
        if self.put_down:
            return
        if self.dest_slot is not None:
            self.dest_slot.add_child(self.object_to_serve)
        else:
            CarryingObject.snap_to_good_location_on_floor(self.object_to_serve)
        self.put_down = True

        def push_consume():
            logger.debug('Push customer to pick up the object.')
            self.object_to_serve.set_ready_to_serve()
            push_object_pick_up_and_consume(self, self.order_sim, self.object_to_serve, consume_affordance_override=self.consume_affordance_override)

        self.add_exit_function(push_consume)

    def _build_sequence_with_callback(self, callback=None, sequence=()):
        self.store_event_handler(callback, handler_id=self.put_down_object_xevt_id)
        sequence = self._custom_content_sequence(sequence)
        return build_element(sequence)

class ServeObjectToSitSlotMixin(ServeObjectToSlotMixin):

    def _custom_content_sequence(self, sequence):

        def select_serve_slot(*_, **__):
            surface_or_part = self._deliver_part or self.target
            for runtime_slot in surface_or_part.get_runtime_slots_gen():
                if runtime_slot.is_valid_for_placement(obj=self.object_to_serve):
                    self.dest_slot = runtime_slot
                    break
            if self.dest_slot is not None:
                return True
            return False

        return (select_serve_slot, sequence)

class ServeObjectToCustomerMixin(ServeObjectMixin):

    def setup_asm_default(self, asm, *args, **kwargs):
        result = super().setup_asm_default(asm, *args, **kwargs)
        if result:
            asm.set_parameter(PARAM_CARRY_TRACK, self._object_info.carry_track.name.lower())
        return result

    @property
    def create_object_owner(self):
        return self.order_sim

    def _build_sequence_with_callback(self, callback=None, sequence=()):

        def create_si():
            object_to_serve = self.object_to_serve
            target_affordance = object_to_serve.get_consume_affordance()
            if target_affordance is None:
                logger.error('{} cannot find the consume interaction from the final product {}.', self, object_to_serve)
                return (None, None)
            context = InteractionContext(self.order_sim, self.source, self.priority, insert_strategy=QueueInsertStrategy.NEXT, group_id=self.group_id)
            aop = AffordanceObjectPair(target_affordance, object_to_serve, target_affordance, None)
            return (aop, context)

        return enter_carry_while_holding(self, self.object_to_serve, create_si_fn=create_si, callback=callback, carry_sim=self.order_sim, track=self.object_info.carry_track, sequence=sequence)

class ServeObjectToSelfMixin(ServeObjectMixin):

    def _custom_claim_callback(self):
        super()._custom_claim_callback()

        def push_consume():
            logger.debug('Push customer to pick up the object.')
            push_object_pick_up_and_consume(self, self.order_sim, self.object_to_serve, consume_affordance_override=self.consume_affordance_override)

        self.add_exit_function(push_consume)

class CraftingPhaseServeObjectSuperInteraction(CraftingPhaseSuperInteractionMixin, SuperInteraction):

    @property
    def _apply_state_xevt_id(self):
        return SCRIPT_EVENT_ID_STOP_CARRY

    @property
    def object_to_serve(self):
        return self.carry_target

    def build_basic_content(self, sequence, **kwargs):
        super_build_basic_content = super().build_basic_content

        def callback(*_, **__):
            self._custom_claim_callback()

        def crafting_sequence(timeline):
            nonlocal sequence
            sequence = super_build_basic_content(sequence, **kwargs)
            sequence = build_critical_section(sequence, flush_all_animations)
            sequence = self._build_sequence_with_callback(callback, sequence=sequence)
            result = yield from element_utils.run_child(timeline, sequence)
            return result

        return (build_element(crafting_sequence),)

    def _run_interaction_gen(self, timeline):
        cancel_interactions_liability = self.get_liability(CANCEL_INTERACTION_ON_EXIT_LIABILITY)
        if self.order_sim is not None:
            cancel_entries = cancel_interactions_liability.get_cancel_entries_for_sim(self.order_sim)
            if cancel_entries is not None:
                self.order_sim_cancel_entries = WeakSet(cancel_entries)
                for entry in tuple(self.order_sim_cancel_entries):
                    cancel_interactions_liability.remove_cancel_entry(self.order_sim, entry)

class ServeToSlotSuperInteraction(ServeObjectToSlotMixin, CraftingPhaseServeObjectSuperInteraction):
    pass

class ServeToSitSlotSuperInteraction(ServeObjectToSitSlotMixin, CraftingPhaseServeObjectSuperInteraction):
    pass

class CreateAndServeObjectSuperInteraction(CraftingPhaseCreateObjectSuperInteraction):
    INSTANCE_TUNABLES = {'fill_object_xevt_id': Tunable(int, 100, description='Xevt id for when to apply final states.'), 'fill_object_actor_name': Tunable(str, 'consumable', description='Name in Swing of the actor for the object being filled.')}

    @property
    def _apply_state_xevt_id(self):
        return self.fill_object_xevt_id

    @property
    def object_to_serve(self):
        return self.created_target

    def setup_asm_default(self, asm, *args, **kwargs):
        if not asm.set_actor(self.fill_object_actor_name, self.object_to_serve):
            return TestResult(False, 'CreateAndServeObjectSuperInteraction could not set actor {} on actor name {} for interaction {} and asm {}'.format(self.created_target, self.fill_object_actor_name, self, asm))
        return super().setup_asm_default(asm, *args, **kwargs)

class CreateAndServeToSlotSuperInteraction(ServeObjectToSlotMixin, CreateAndServeObjectSuperInteraction):
    pass

class CreateAndServeToSitSlotSuperInteraction(ServeObjectToSitSlotMixin, CreateAndServeObjectSuperInteraction):
    pass

class CreateAndServeToCustomerSuperInteraction(ServeObjectToCustomerMixin, CreateAndServeObjectSuperInteraction):
    pass

class ChooseDeliverySuperInteraction(CraftingPhaseSuperInteractionMixin, SuperInteraction):
    INSTANCE_TUNABLES = {'serve_to_slot_affordance': OptionalTunable(description='\n            If tuned, the Sim has the ability to serve to a slot on a surface.\n            ', tunable=TunableReference(description='\n                Affordance used to serve an object to a slot, if the ordering Sim\n                is not at a surface.\n                ', manager=services.affordance_manager(), class_restrictions=('ServeToSlotSuperInteraction', 'CreateAndServeToSlotSuperInteraction')), tuning_group=SERVING_TUNING_GROUP), 'serve_to_sit_slot_affordance': OptionalTunable(description='\n            If tuned, the Sim has the ability to serve to a slot on a surface\n            that the ordering Sim is sitting at.\n            ', tunable=TunableReference(description='\n                Affordance used to serve an object to a slot on a Surface that a\n                Sim is sitting at.\n                ', manager=services.affordance_manager(), class_restrictions=('ServeToSitSlotSuperInteraction', 'CreateAndServeToSitSlotSuperInteraction')), tuning_group=SERVING_TUNING_GROUP), 'serve_target_override': OptionalTunable(description="\n            An optional target override for the Serve interactions that are\n            pushed during this one.\n            \n            Example: This interaction is tuned on the Espresso Machine because\n            you don't need an Espresso Bar to make drinks, but we need to be\n            able to serve to an Espresso bar underneath using the same recipe.\n            ", tunable=TunableEnumEntry(description='\n                The participant type to use as the target of the serve\n                interactions.\n                ', tunable_type=ParticipantType, default=ParticipantType.Object), tuning_group=SERVING_TUNING_GROUP), 'consume_affordance_override': OptionalTunable(description="\n            If tuned, this will forward a consume affordance override to the\n            serving interactions instead of getting the consume affordance from\n            the object's consumable component. Useful if we want the Sim to do\n            something instead of consume the object after it has been served.\n            ", tunable=TunableReference(description='\n                Affordance override for when we want to push a consume.\n                ', manager=services.affordance_manager(), class_restrictions=('SuperInteraction',)), tuning_group=SERVING_TUNING_GROUP), 'skip_serve_if_crafter_is_orderer': Tunable(description='\n            If true, and the crafter is the orderer, we will use Consume\n            Affordance Override or get the consume affordance on the object,\n            and push that instead of serve to self.\n            \n            NOTE: This will only work if the final product has already been\n            created as part of the crafting process before this affordance is\n            run.\n            ', tunable_type=bool, default=False, tuning_group=SERVING_TUNING_GROUP)}

    @classmethod
    def _verify_tuning_callback(cls):
        if cls.skip_serve_if_crafter_is_orderer or cls.serve_to_slot_affordance is None and cls.serve_to_sit_slot_affordance is None:
            logger.error('{} has no serve affordances tuned and does not skip the serve interaction. This will never serve a final product correctly.', cls.__name__, owner='rmccord')

    @property
    def auto_goto_next_phase(self):
        return False

    @classmethod
    def is_guaranteed(cls, *args, **kwargs):
        return True

    def _pick_serve_affordance(self, order_sim, object_info, context):
        deliver_part = None
        carry_track = object_info.carry_track
        deliver_to_slot = self.serve_to_slot_affordance
        deliver_to_sit_slot = self.serve_to_sit_slot_affordance
        if self.serve_target_override is None:
            target = self.target
        else:
            target = self.get_participant(self.serve_target_override)
            if target is None:
                logger.error("{} couldn't find serve or consume target override for participant {}", self, self.serve_target_override, owner='rmccord')
                target = self.target
        if order_sim is not None and order_sim.is_simulating:
            order_surface_target = order_sim.posture_state.surface_target
            if order_surface_target is not None and order_surface_target.is_part and deliver_to_sit_slot is not None:
                serve_object = None
                if target.is_part:
                    serve_object = target.part_owner
                if order_surface_target.part_owner is serve_object and order_surface_target.is_valid_for_placement(definition=object_info.definition):
                    deliver_part = order_surface_target
                    return (deliver_to_sit_slot, target, deliver_part, carry_track)
        serve_target = find_serve_target(target, object_info, deliver_part=deliver_part)
        return (deliver_to_slot, serve_target, None, carry_track)

    def _push_serve_affordance(self, order_sim, recipe):
        object_info = recipe.final_product
        context = self.context.clone_for_continuation(self)
        (deliver_affordance, target, deliver_part, carry_track) = self._pick_serve_affordance(order_sim, object_info, context)
        if deliver_affordance is None:
            logger.error('{} failed to find serve affordance to deliver final product.', self, owner='rmccord')
            return TestResult(False, 'failed to find serve affordance to deliver final product')
        if object_info.carry_track != carry_track:
            aop_obj_info = object_info.clone_with_overrides(carry_track=carry_track)
        else:
            aop_obj_info = object_info
        self.process.ready_to_serve = True
        new_process = self.process.copy_for_serve_interaction(recipe)
        anim_overrides = self.process.phase.anim_overrides if self.process.phase is not None else None
        aop = AffordanceObjectPair(deliver_affordance, target, deliver_affordance, None, order_sim=order_sim, object_info=aop_obj_info, deliver_part=deliver_part, consume_affordance_override=self.consume_affordance_override, phase=self.process.phase, crafting_process=new_process, anim_overrides=anim_overrides)
        self._went_to_next_phase_or_finished_crafting = True
        return aop.test_and_execute(context)

    def _push_consume_affordance(self, order_sim, recipe):
        self._went_to_next_phase_or_finished_crafting = True
        if self.process.orders or not self.should_push_consume(check_phase=False):
            return TestResult(False, 'Ordering Sim cannot push consume affordance but skip_serve_if_crafter_is_orderer is True.')
        serve_object = None
        current_ico = self.process.current_ico
        if current_ico.definition is recipe.final_product.definition:
            serve_object = current_ico
        if current_ico is not None and serve_object is None:
            logger.error("{} couldn't find serve or consume target override for participant {}", self, self.serve_target_override, owner='rmccord')
            serve_object = self.target
        return push_object_pick_up_and_consume(self, order_sim, serve_object, consume_affordance_override=self.consume_affordance_override)

    def _run_interaction_gen(self, timeline):
        (order_sim, recipe) = self.process.pop_order()
        if self.skip_serve_if_crafter_is_orderer and order_sim is self.process.crafter:
            result = self._push_consume_affordance(order_sim, recipe)
        else:
            result = self._push_serve_affordance(order_sim, recipe)
        return result
lock_instance_tunables(ChooseDeliverySuperInteraction, basic_content=None)