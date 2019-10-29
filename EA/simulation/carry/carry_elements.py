import functoolsfrom animation import ClipEventTypefrom animation.animation_utils import flush_all_animations, disable_asm_auto_exitfrom animation.arb import Arbfrom animation.arb_element import distribute_arb_elementfrom carry.carry_tuning import CarryPostureStaticTuningfrom carry.carry_utils import hand_to_track, track_to_hand, SCRIPT_EVENT_ID_START_CARRY, SCRIPT_EVENT_ID_STOP_CARRYfrom element_utils import build_element, build_critical_section, must_run, build_critical_section_with_finallyfrom interactions import ParticipantType, ParticipantTypeSingleSimfrom interactions.aop import AffordanceObjectPairfrom interactions.context import QueueInsertStrategy, InteractionContextfrom postures import PostureTrackfrom postures.context import PostureContextfrom postures.posture_specs import PostureSpecVariable, PostureOperation, PostureAspectBody, PostureAspectSurface, SURFACE_TARGET_INDEX, SURFACE_SLOT_TYPE_INDEX, SURFACE_INDEXfrom postures.transition import PostureTransitionfrom sims4.log import StackVarfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, HasTunableSingletonFactory, TunableEnumEntry, TunableVariant, TunableFactory, TunableTuple, TunablePackSafeReferencefrom singletons import DEFAULTimport element_utilsimport elementsimport servicesimport sims4.logimport sims4.resourcesfrom postures.posture_state import PostureStatelogger = sims4.log.Logger('Carry', default_owner='rmccord')
def _create_enter_carry_posture(sim, posture_state, carry_target, track):
    var_map = {PostureSpecVariable.POSTURE_TYPE_CARRY_OBJECT: carry_target.get_carry_object_posture(), PostureSpecVariable.HAND: track_to_hand(track), PostureSpecVariable.CARRY_TARGET: carry_target}
    pick_up_operation = PostureOperation.PickUpObject(PostureSpecVariable.POSTURE_TYPE_CARRY_OBJECT, PostureSpecVariable.CARRY_TARGET)
    new_source_aop = pick_up_operation.associated_aop(sim, var_map)
    new_posture_spec = pick_up_operation.apply(posture_state.get_posture_spec(var_map), enter_carry_while_holding=True)
    if new_posture_spec is None:
        raise RuntimeError('[rmccord] Failed to create new_posture_spec in enter_carry_while_holding!')
    new_posture_state = PostureState(sim, posture_state, new_posture_spec, var_map)
    new_posture = new_posture_state.get_aspect(track)
    from carry.carry_postures import CarryingNothing
    if new_posture is None or isinstance(new_posture, CarryingNothing):
        raise RuntimeError('[rmccord] Failed to create a valid new_posture ({}) from new_posture_state ({}) in enter_carry_while_holding!'.format(new_posture, new_posture_state))
    new_posture.external_transition = True
    return (new_posture_state, new_posture, new_source_aop, var_map)

def enter_carry_while_holding(si, obj=None, carry_obj_participant_type=None, callback=None, create_si_fn=DEFAULT, sim_participant_type=ParticipantType.Actor, target_participant_type=None, owning_affordance=DEFAULT, carry_track_override=None, sequence=None, carry_sim=DEFAULT, track=DEFAULT, asm_context=None, priority_override=None, target_override=None):
    sim = si.get_participant(sim_participant_type) if carry_sim is DEFAULT else carry_sim
    if target_override is None:
        target = si.get_participant(target_participant_type) if target_participant_type is not None else None
    else:
        target = target_override
    context = si.context.clone_for_sim(sim, insert_strategy=QueueInsertStrategy.NEXT)
    if priority_override is not None:
        context.priority = priority_override
    if carry_track_override is not None:
        track = carry_track_override
    if track is DEFAULT:
        track = si.carry_track
    if track is None:
        raise RuntimeError("[rmccord] enter_carry_while_holding: Interaction {} does not have a carry_track, which means its animation tuning doesn't have a carry target or create target specified in object editor or the posture manifest from the swing graph does not require a specific object. {}".format(si, StackVar(('process', '_auto_constraints'))))
    if owning_affordance is None:
        create_si_fn = None
    if create_si_fn is DEFAULT and create_si_fn is DEFAULT:
        if owning_affordance is DEFAULT:
            raise AssertionError("[rmccord] No create_si_fn was provided and we don't know how to make one.")

        def create_si_fn():
            context.carry_target = obj
            aop = AffordanceObjectPair(owning_affordance, target, owning_affordance, None)
            return (aop, context)

    def set_up_transition_gen(timeline):
        nonlocal obj, sequence
        if carry_obj_participant_type is not None:
            obj = si.get_participant(carry_obj_participant_type)
            if obj is None:
                raise ValueError('[rmccord] Attempt to perform an enter carry while holding with None as the carried object. SI: {}'.format(si))
        (new_posture_state, new_posture, new_source_aop, var_map) = _create_enter_carry_posture(sim, sim.posture_state, obj, track)
        if obj.is_sim:
            target_posture_state = new_posture.set_target_linked_posture_data()
        else:
            target_posture_state = None
        got_callback = False

        def event_handler_enter_carry(event_data):
            nonlocal got_callback
            if got_callback:
                logger.warn('Animation({}) calling to start a carry multiple times', event_data.event_data.get('clip_name'))
                return
            got_callback = True
            arb = Arb()
            locked_params = new_posture.get_locked_params(None)
            old_carry_posture = sim.posture_state.get_aspect(track)
            if old_carry_posture is not None:
                old_carry_posture.append_exit_to_arb(arb, new_posture_state, new_posture, var_map)
            new_posture.append_transition_to_arb(arb, old_carry_posture, locked_params=locked_params, in_xevt_handler=True)
            distribute_arb_element(arb)

        if asm_context is not None:
            asm_context.register_event_handler(event_handler_enter_carry, handler_type=ClipEventType.Script, handler_id=SCRIPT_EVENT_ID_START_CARRY, tag='enter_carry')
        else:
            si.store_event_handler(event_handler_enter_carry, handler_id=SCRIPT_EVENT_ID_START_CARRY)

        def maybe_do_transition_gen(timeline):

            def push_si_gen(timeline):
                context = InteractionContext(sim, InteractionContext.SOURCE_POSTURE_GRAPH, si.priority if priority_override is None else priority_override, run_priority=si.run_priority if priority_override is None else priority_override, insert_strategy=QueueInsertStrategy.FIRST, must_run_next=True, group_id=si.group_id)
                result = new_source_aop.interaction_factory(context)
                if not result:
                    return result
                source_interaction = result.interaction
                new_posture.source_interaction = source_interaction
                owning_interaction = None
                if create_si_fn is not None:
                    (aop, context) = create_si_fn()
                    if aop.test(context):
                        result = aop.interaction_factory(context)
                        if result:
                            owning_interaction = result.interaction
                if owning_interaction is None:
                    si.acquire_posture_ownership(new_posture)
                    yield from source_interaction.run_direct_gen(timeline)
                else:
                    owning_interaction.acquire_posture_ownership(new_posture)
                    aop.execute_interaction(owning_interaction)
                    new_source_aop.execute_interaction(source_interaction)
                if target_posture_state is not None:
                    yield from new_posture.kickstart_linked_carried_posture_gen(timeline)
                return result

            def call_callback(_):
                if callback is not None:
                    callback(new_posture, new_posture.source_interaction)

            if got_callback:
                if target_posture_state is not None:
                    obj.posture_state = target_posture_state
                result = yield from element_utils.run_child(timeline, must_run([PostureTransition(new_posture, new_posture_state, context, var_map), push_si_gen, call_callback]))
                return result
            return True

        sequence = disable_asm_auto_exit(sim, sequence)
        with si.cancel_deferred((si,)):
            yield from element_utils.run_child(timeline, must_run(build_critical_section(build_critical_section(sequence, flush_all_animations), maybe_do_transition_gen)))

    return build_element(set_up_transition_gen)

def _create_exit_carry_posture(sim, target, interaction, use_posture_animations, preserve_posture=None):
    failure_result = (None, None, None, None, None)
    slot_manifest = interaction.slot_manifest
    old_carry_posture = sim.posture_state.get_carry_posture(target)
    if old_carry_posture is None:
        return failure_result
    spec_surface = sim.posture_state.spec[SURFACE_INDEX]
    has_slot_surface = spec_surface is not None and spec_surface[SURFACE_SLOT_TYPE_INDEX] is not None
    if target.transient or has_slot_surface:
        put_down_operation = PostureOperation.PutDownObjectOnSurface(PostureSpecVariable.POSTURE_TYPE_CARRY_NOTHING, spec_surface[SURFACE_TARGET_INDEX], spec_surface[SURFACE_SLOT_TYPE_INDEX], PostureSpecVariable.CARRY_TARGET)
    else:
        put_down_operation = PostureOperation.PutDownObject(PostureSpecVariable.POSTURE_TYPE_CARRY_NOTHING, PostureSpecVariable.CARRY_TARGET)
    var_map = {PostureSpecVariable.SLOT_TEST_DEFINITION: interaction.create_target, PostureSpecVariable.SLOT: slot_manifest, PostureSpecVariable.POSTURE_TYPE_CARRY_NOTHING: CarryPostureStaticTuning.POSTURE_CARRY_NOTHING, PostureSpecVariable.HAND: track_to_hand(old_carry_posture.track), PostureSpecVariable.CARRY_TARGET: target}
    current_spec = sim.posture_state.get_posture_spec(var_map)
    if current_spec is None:
        if preserve_posture is None:
            logger.warn('Failed to get posture spec for var_map: {} for {}', sim.posture_state, var_map)
        return failure_result
    new_posture_spec = put_down_operation.apply(current_spec)
    if new_posture_spec is None:
        if preserve_posture is None:
            logger.warn('Failed to apply put_down_operation: {}', put_down_operation)
        return failure_result
    if not new_posture_spec.validate_destination((new_posture_spec,), var_map, interaction.affordance, sim):
        if preserve_posture is None:
            logger.warn('Failed to validate put down spec {}  with var map {}', new_posture_spec, var_map)
        return failure_result
    carry_posture_overrides = {}
    if preserve_posture is not None:
        carry_posture_overrides[preserve_posture.track] = preserve_posture
    new_posture_state = PostureState(sim, sim.posture_state, new_posture_spec, var_map, carry_posture_overrides=carry_posture_overrides)
    new_posture = new_posture_state.get_aspect(old_carry_posture.track)
    new_posture.source_interaction = interaction.super_interaction
    new_posture.external_transition = not use_posture_animations
    posture_context = PostureContext(interaction.context.source, interaction.priority, None)
    transition = PostureTransition(new_posture, new_posture_state, posture_context, var_map, locked_params=interaction.locked_params)
    transition.must_run = True
    return (old_carry_posture, new_posture, new_posture_state, transition, var_map)

def exit_carry_while_holding(interaction, callback=None, sequence=None, sim_participant_type=ParticipantType.Actor, use_posture_animations=False, carry_system_target=None, target=DEFAULT, arb=None):
    si = interaction.super_interaction
    sim = interaction.get_participant(sim_participant_type)
    target = interaction.carry_target or interaction.target if target is DEFAULT else target

    def set_up_transition_gen(timeline):
        (old_carry_posture, new_posture, _, transition, var_map) = _create_exit_carry_posture(sim, target, interaction, use_posture_animations)
        if transition is None:
            yield from element_utils.run_child(timeline, sequence)
            return
        if arb is None:
            register_event = functools.partial(interaction.store_event_handler, handler_id=SCRIPT_EVENT_ID_STOP_CARRY)
        else:
            register_event = functools.partial(arb.register_event_handler, handler_id=SCRIPT_EVENT_ID_STOP_CARRY)
        exited_carry = False
        if not use_posture_animations:

            def event_handler_exit_carry(event_data):
                nonlocal exited_carry
                exited_carry = True
                arb = Arb()
                old_carry_posture.append_exit_to_arb(arb, None, new_posture, var_map, exit_while_holding=True)
                new_posture.append_transition_to_arb(arb, old_carry_posture, in_xevt_handler=True)
                distribute_arb_element(arb, master=sim)

            register_event(event_handler_exit_carry)
        if callback is not None:
            register_event(callback)

        def maybe_do_transition(timeline):
            nonlocal transition
            (_, _, _, new_transition, _) = _create_exit_carry_posture(sim, target, interaction, use_posture_animations, preserve_posture=new_posture)
            if new_transition is not None:
                transition = new_transition
            if use_posture_animations or not exited_carry:
                event_handler_exit_carry(None)
                if callback is not None:
                    callback()
            if use_posture_animations or exited_carry:
                interaction_target_was_target = False
                si_target_was_target = False
                if old_carry_posture.target_is_transient:
                    if interaction.target == target:
                        interaction_target_was_target = True
                        interaction.set_target(None)
                    if si.target == target:
                        si_target_was_target = True
                        si.set_target(None)
                if carry_system_target is not None:
                    old_carry_posture.carry_system_target = carry_system_target

                def do_transition(timeline):
                    result = yield from element_utils.run_child(timeline, transition)
                    if result:
                        if target.is_sim:
                            body_posture_type = sim.posture_state.spec.body.posture_type
                            if not body_posture_type.multi_sim:
                                post_transition_spec = sim.posture_state.spec.clone(body=PostureAspectBody((body_posture_type, None)), surface=PostureAspectSurface((None, None, None)))
                                post_posture_state = PostureState(sim, sim.posture_state, post_transition_spec, var_map)
                                post_posture_state.body.source_interaction = sim.posture.source_interaction
                                post_transition = PostureTransition(post_posture_state.body, post_posture_state, sim.posture.posture_context, var_map)
                                post_transition.must_run = True
                                yield from element_utils.run_child(timeline, post_transition)
                        interaction_target_was_target = False
                        si_target_was_target = False
                        new_posture.source_interaction = None
                        return True
                    return False

                def post_transition(_):
                    if interaction_target_was_target:
                        interaction.set_target(target)
                    if si_target_was_target:
                        si.set_target(target)
                    if carry_system_target is not None:
                        old_carry_posture.carry_system_target = None

                yield from element_utils.run_child(timeline, must_run(build_critical_section_with_finally(do_transition, post_transition)))

        new_sequence = disable_asm_auto_exit(sim, sequence)
        yield from element_utils.run_child(timeline, build_critical_section(build_critical_section(new_sequence, flush_all_animations), maybe_do_transition))

    return build_element(set_up_transition_gen)

def swap_carry_while_holding(interaction, original_carry_target, new_carry_object, callback=None, sequence=None, sim_participant_type=ParticipantType.Actor, carry_system_target=None):
    si = interaction.super_interaction
    sim = interaction.get_participant(sim_participant_type)

    def set_up_transition(timeline):
        (original_carry_posture, carry_nothing_posture, carry_nothing_posture_state, transition_to_carry_nothing, carry_nothing_var_map) = _create_exit_carry_posture(sim, original_carry_target, interaction, False)
        if transition_to_carry_nothing is None:
            return False
        (final_posture_state, final_posture, final_source_aop, final_var_map) = _create_enter_carry_posture(sim, carry_nothing_posture_state, new_carry_object, original_carry_posture.track)
        got_callback = False

        def event_handler_swap_carry(event_data):
            nonlocal got_callback
            if got_callback:
                logger.warn('Animation({}) calling to start a carry multiple times', event_data.event_data.get('clip_name'))
                return
            got_callback = True
            arb_exit = Arb()
            original_carry_posture.append_exit_to_arb(arb_exit, None, carry_nothing_posture, carry_nothing_var_map, exit_while_holding=True)
            carry_nothing_posture.append_transition_to_arb(arb_exit, original_carry_posture, in_xevt_handler=True)
            distribute_arb_element(arb_exit)
            original_carry_posture.target.transient = True
            original_carry_posture.target.clear_parent(sim.transform, sim.routing_surface)
            original_carry_posture.target.remove_from_client()
            arb_enter = Arb()
            locked_params = final_posture.get_locked_params(None)
            if carry_nothing_posture is not None:
                carry_nothing_posture.append_exit_to_arb(arb_enter, final_posture_state, final_posture, final_var_map)
            final_posture.append_transition_to_arb(arb_enter, carry_nothing_posture, locked_params=locked_params, in_xevt_handler=True)
            distribute_arb_element(arb_enter)

        interaction.store_event_handler(event_handler_swap_carry, handler_id=SCRIPT_EVENT_ID_START_CARRY)
        if callback is not None:
            interaction.store_event_handler(callback, handler_id=SCRIPT_EVENT_ID_START_CARRY)

        def maybe_do_transition(timeline):

            def push_si(_):
                context = InteractionContext(sim, InteractionContext.SOURCE_POSTURE_GRAPH, si.priority, run_priority=si.run_priority, insert_strategy=QueueInsertStrategy.NEXT, must_run_next=True, group_id=si.group_id)
                result = final_source_aop.interaction_factory(context)
                if not result:
                    return result
                final_source_interaction = result.interaction
                si.acquire_posture_ownership(final_posture)
                yield from final_source_interaction.run_direct_gen(timeline)
                final_posture.source_interaction = final_source_interaction
                return result

            if not got_callback:
                event_handler_swap_carry(None)
                if callback is not None:
                    callback()
            if got_callback:
                if original_carry_posture.target_is_transient:
                    if interaction.target == original_carry_target:
                        interaction_target_was_target = True
                        interaction.set_target(None)
                    else:
                        interaction_target_was_target = False
                    if si.target == original_carry_target:
                        si_target_was_target = True
                        si.set_target(None)
                    else:
                        si_target_was_target = False
                else:
                    interaction_target_was_target = False
                    si_target_was_target = False
                if carry_system_target is not None:
                    original_carry_posture.carry_system_target = carry_system_target

                def do_transition(timeline):
                    nonlocal interaction_target_was_target, si_target_was_target
                    result = yield from element_utils.run_child(timeline, transition_to_carry_nothing)
                    if not result:
                        return False
                    interaction_target_was_target = False
                    si_target_was_target = False
                    carry_nothing_posture.source_interaction = None
                    return True

                def post_transition(_):
                    if interaction_target_was_target:
                        interaction.set_target(original_carry_target)
                    if si_target_was_target:
                        si.set_target(original_carry_target)
                    if carry_system_target is not None:
                        original_carry_posture.carry_system_target = None

                exit_carry_result = yield from element_utils.run_child(timeline, must_run(build_critical_section_with_finally(do_transition, post_transition)))
                if not exit_carry_result:
                    raise RuntimeError('[maxr] Failed to exit carry: {}'.format(original_carry_posture))
            if got_callback:
                context = si.context.clone_for_sim(sim)
                yield from element_utils.run_child(timeline, (PostureTransition(final_posture, final_posture_state, context, final_var_map), push_si))

        new_sequence = disable_asm_auto_exit(sim, sequence)
        yield from element_utils.run_child(timeline, build_critical_section(build_critical_section(new_sequence, flush_all_animations), maybe_do_transition))

    return (set_up_transition,)

class EnterCarryWhileHolding(elements.ParentElement, HasTunableFactory, AutoFactoryInit):

    class TrackOverrideExplicit(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'carry_track': TunableEnumEntry(description='\n                Which hand to carry the object in.\n                ', tunable_type=PostureTrack, default=PostureTrack.RIGHT, invalid_enums=(PostureTrack.BODY,))}

        def get_override(self, *args, **kwargs):
            return self.carry_track

    class TrackOverrideHandedness(HasTunableSingletonFactory, AutoFactoryInit):

        def get_override(self, interaction, sim_participant, *args, **kwargs):
            carry_participant = interaction.get_participant(sim_participant)
            if carry_participant is None:
                return
            hand = carry_participant.get_preferred_hand()
            return hand_to_track(hand)

    NONE = 1
    OBJECT_TO_BE_CARRIED = 2
    PARTICIPANT_TYPE = 3
    FACTORY_TUNABLES = {'carry_obj_participant_type': TunableEnumEntry(description='\n            The object that will be carried.\n            ', tunable_type=ParticipantType, default=ParticipantType.CarriedObject), 'sim_participant_type': TunableEnumEntry(description='\n            The Sim that will get a new carry.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'target': TunableVariant(description='\n            Specify what to use as the target of\n            the owning affordance.\n            ', object_to_be_carried=TunableTuple(description='\n                Target is the object that WILL be carried.\n                ', locked_args={'target_type': OBJECT_TO_BE_CARRIED}), none=TunableTuple(description='\n                Target is None\n                ', locked_args={'target_type': NONE}), participant_type=TunableTuple(description='\n                Target is the specified participant of THIS interaction.\n                \n                This is necessary if we need to target another participant\n                when we push the owning affordance\n                ', participant=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.CarriedObject), locked_args={'target_type': PARTICIPANT_TYPE}), default='object_to_be_carried'), 'owning_affordance': TunablePackSafeReference(description='\n            The interaction that will be pushed that will own the carry\n            state (e.g. a put down).\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), allow_none=True), 'carry_track_override': TunableVariant(description='\n            Specify the carry track, instead of using the carry of the SI.\n            ', explicit=TrackOverrideExplicit.TunableFactory(), handedness=TrackOverrideHandedness.TunableFactory(), default='disabled', locked_args={'disabled': None})}

    def __init__(self, interaction, *args, sequence=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.interaction = interaction
        self.sequence = sequence

    def _run(self, timeline):
        carry_track_override = self.carry_track_override.get_override(self.interaction, self.sim_participant_type) if self.carry_track_override is not None else None
        target = self.target
        if target.target_type == EnterCarryWhileHolding.NONE:
            target_participant_type = None
        elif target.target_type == EnterCarryWhileHolding.OBJECT_TO_BE_CARRIED:
            target_participant_type = self.carry_obj_participant_type
        elif target.target_type == EnterCarryWhileHolding.PARTICIPANT_TYPE:
            target_participant_type = target.participant
        carry_element = enter_carry_while_holding(self.interaction, sequence=self.sequence, carry_obj_participant_type=self.carry_obj_participant_type, sim_participant_type=self.sim_participant_type, target_participant_type=target_participant_type, owning_affordance=self.owning_affordance, carry_track_override=carry_track_override)
        return timeline.run_child(carry_element)

class TunableExitCarryWhileHolding(TunableFactory):
    FACTORY_TYPE = staticmethod(exit_carry_while_holding)

    def __init__(self, *args, description='Exit the carry for the target or carry_target of an interaction.  The animations played during the interaction should exit the carry via an XEVT.', **kwargs):
        super().__init__(*args, description=description, sim_participant_type=TunableEnumEntry(description='\n                 The Sim that will exit a carry.\n                 ', tunable_type=ParticipantType, default=ParticipantType.Actor), **kwargs)

class TransferCarryWhileHolding(elements.ParentElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'enter_carry_while_holding': EnterCarryWhileHolding.TunableFactory(), 'exit_carry_while_holding': TunableExitCarryWhileHolding()}

    def __init__(self, interaction, *args, sequence=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.interaction = interaction
        self.sequence = sequence

    def _run(self, timeline):
        obj = self.interaction.get_participant(self.enter_carry_while_holding.carry_obj_participant_type)
        source_sim = self.interaction.get_participant(self.exit_carry_while_holding.sim_participant_type)
        target_sim = self.interaction.get_participant(self.enter_carry_while_holding.sim_participant_type)

        def _add_reservation_clobberer(_):
            obj.add_reservation_clobberer(source_sim, target_sim)

        def _remove_reservation_clobberer(_):
            obj.remove_reservation_clobberer(source_sim, target_sim)

        sequence = self.enter_carry_while_holding(self.interaction, sequence=self.sequence)
        sequence = self.exit_carry_while_holding(self.interaction, sequence=sequence)
        sequence = element_utils.build_critical_section_with_finally(_add_reservation_clobberer, sequence, _remove_reservation_clobberer)
        return timeline.run_child(sequence)
