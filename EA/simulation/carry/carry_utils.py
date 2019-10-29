import functoolsfrom animation.animation_utils import flush_all_animations, create_run_animation, get_auto_exitfrom animation.arb_element import distribute_arb_elementfrom animation.posture_manifest import Hand, PostureManifest, PostureManifestEntry, MATCH_ANY, SlotManifest, MATCH_NONEfrom carry.carry_tuning import CarryPostureStaticTuningfrom element_utils import build_critical_section, build_critical_section_with_finallyfrom objects import VisibilityStatefrom objects.proxy import ProxyObjectfrom postures import PostureTrack, create_posturefrom postures.posture_specs import PostureSpecVariablefrom postures.posture_state_spec import PostureStateSpecfrom singletons import DEFAULTimport animation.arbimport element_utilsimport interactions.constraintsimport sims4.loglogger = sims4.log.Logger('Carry', default_owner='rmccord')SCRIPT_EVENT_ID_START_CARRY = 700SCRIPT_EVENT_ID_STOP_CARRY = 701PARAM_CARRY_TRACK = 'carryTrack'PARAM_CARRY_STATE = 'carryState'
def hand_to_track(hand:Hand) -> PostureTrack:
    if hand == Hand.LEFT:
        return PostureTrack.LEFT
    return PostureTrack.RIGHT

def track_to_hand(track:PostureTrack) -> Hand:
    if track == PostureTrack.LEFT:
        return Hand.LEFT
    return Hand.RIGHT

def set_carry_track_param_if_needed(asm, sim, carry_target_name, carry_target, carry_track=DEFAULT):
    posture_carry_track = sim.posture_state.get_carry_track(carry_target)
    if posture_carry_track is not None:
        carry_track = posture_carry_track
    if carry_track is None or carry_track is DEFAULT:
        return False
    return set_carry_track_param(asm, carry_target_name, carry_target, carry_track)

def set_carry_track_param(asm, carry_target_name, carry_target, carry_track):
    if asm.set_actor_parameter(carry_target_name, carry_target, PARAM_CARRY_TRACK, carry_track.name.lower()):
        return True
    elif asm.set_parameter('carrytrack', carry_track.name.lower()):
        logger.warn('Parameter carrytrack in {} should be renamed to {}:carryTrack.', asm.name, carry_target_name)
        return True
    return False

def interact_with_carried_object(sim, target, posture_state=DEFAULT, interaction=None, create_target_track=None, animation_context=None, must_run=False, sequence=()):
    if interaction is not None:
        if interaction.staging and sim.posture_state.is_source_or_owning_interaction(interaction):
            return sequence
        if interaction.disable_carry_interaction_mask:
            return sequence
    is_carrying_other_object = False
    animation_contexts = set()
    target_ref = target.ref() if must_run or target is not None else None

    def maybe_do_begin(_):
        nonlocal posture_state, is_carrying_other_object
        if posture_state is DEFAULT:
            posture_state = sim.posture_state
        try:
            resolved_target = target_ref() if target_ref is not None else None
            if create_target_track is None:
                target_track = posture_state.get_carry_track(resolved_target)
                if target_track is None:
                    return
                other_carry = posture_state.get_other_carry_posture(resolved_target)
                if other_carry is None or other_carry.holstered:
                    return
            else:
                other_carry = posture_state.right if create_target_track == PostureTrack.LEFT else posture_state.left
                if other_carry.target is None:
                    return
        finally:
            del posture_state
        is_carrying_other_object = True
        if animation_context is not None:
            animation_contexts.add(animation_context)
        if interaction is not None:
            animation_contexts.add(interaction.animation_context)
        sim.asm_auto_exit.apply_carry_interaction_mask += 1
        for context in animation_contexts:
            context.apply_carry_interaction_mask.append('x')

    def maybe_do_end(_):
        if not is_carrying_other_object:
            return
        sim.asm_auto_exit.apply_carry_interaction_mask -= 1
        for context in animation_contexts:
            context.apply_carry_interaction_mask.remove('x')

    return build_critical_section_with_finally(maybe_do_begin, sequence, maybe_do_end)

def _get_holstering_setup_asm_func(carry_posture, carry_object):

    def setup_asm(asm):
        old_location = carry_object.location.clone()
        hide_carry_handle = None
        show_carry_handle = None

        def show_carry_object(_):
            carry_object.location = old_location
            carry_object.visibility = VisibilityState(True, True, False)
            carry_posture._event_handler_start_pose()
            show_carry_handle.release()

        def hide_carry_object(_):
            asm.set_current_state('entry')
            carry_object.visibility = VisibilityState(False, False, False)
            hide_carry_handle.release()

        hide_carry_handle = asm.context.register_event_handler(hide_carry_object, handler_id=SCRIPT_EVENT_ID_STOP_CARRY)
        show_carry_handle = asm.context.register_event_handler(show_carry_object, handler_id=SCRIPT_EVENT_ID_START_CARRY)
        asm.set_parameter('surfaceHeight', 'inventory')
        return True

    return setup_asm

def holster_carried_object(sim, interaction, unholster_predicate, flush_before_sequence=False, sequence=None):
    holstered_objects = []
    if interaction.can_holster_incompatible_carries:
        for (_, carry_posture) in interaction.get_uncarriable_objects_gen(allow_holster=False, use_holster_compatibility=True):
            holstered_objects.append(carry_posture.target)
            if not carry_posture.holstered:
                sequence = holster_object(carry_posture, flush_before_sequence=flush_before_sequence, sequence=sequence)
    for (_, carry_posture, carry_object) in get_carried_objects_gen(sim):
        if carry_posture.holstered and carry_object not in holstered_objects and unholster_predicate(carry_object):
            sequence = unholster_object(carry_posture, flush_before_sequence=flush_before_sequence, sequence=sequence)
    return sequence

def holster_objects_for_route(sim, unholster_after_predicate=lambda _: False, sequence=None):
    predicate = sim.is_required_to_holster_while_routing
    return maybe_holster_objects_through_sequence(sim, predicate=predicate, unholster_after_predicate=unholster_after_predicate, sequence=sequence)

def maybe_holster_objects_through_sequence(sim, predicate=lambda _: True, unholster_after_predicate=lambda _: True, sequence=None):
    for aspect in sim.posture_state.carry_aspects:
        if aspect.target is not None and predicate(aspect.target):
            sequence = holster_object(aspect, flush_before_sequence=True, sequence=sequence)
            auto_exit_element = get_auto_exit((sim,), required_actors=(aspect.target,))
            if auto_exit_element is not None:
                sequence = (auto_exit_element, sequence)
    unholster_sequence = None
    for aspect in sim.posture_state.carry_aspects:
        if aspect.target is not None and predicate(aspect.target) and unholster_after_predicate(aspect.target):
            unholster_sequence = unholster_object(aspect, flush_before_sequence=True, sequence=unholster_sequence)
    sequence = (sequence, unholster_sequence)
    return sequence

def hide_held_props(sim, data):
    if sim.id not in data.actors:
        return
    for si in sim.si_state:
        si.animation_context.set_all_prop_visibility(False, held_only=True)

def holster_object(carry_posture, flush_before_sequence=False, sequence=None):
    carry_object = carry_posture.target

    def _set_holster():
        carry_posture.holster_count += 1
        return True

    carry_nothing_posture = create_posture(CarryPostureStaticTuning.POSTURE_CARRY_NOTHING, carry_posture.sim, None, track=carry_posture.track)

    def holster(timeline):
        if carry_object.is_sim:
            return
        if carry_posture.holster_count > 1:
            return

        def stop_carry(*_, **__):
            idle_arb = animation.arb.Arb()
            carry_nothing_posture.asm.request(carry_nothing_posture._state_name, idle_arb)
            distribute_arb_element(idle_arb)

        arb_holster = animation.arb.Arb()
        arb_holster.register_event_handler(stop_carry, handler_id=SCRIPT_EVENT_ID_STOP_CARRY)
        carry_posture.asm.context.register_custom_event_handler(functools.partial(hide_held_props, carry_posture.sim), None, 0, allow_stub_creation=True)
        setup_asm_fn_carry = _get_holstering_setup_asm_func(carry_posture, carry_object)
        setup_asm_fn_carry(carry_posture.asm)
        carry_posture.asm.request(carry_posture._exit_state_name, arb_holster)
        result = carry_nothing_posture.setup_asm_posture(carry_nothing_posture.asm, carry_nothing_posture.sim, None)
        if not result:
            logger.error('Failed to setup asm to holster {}. {} ', carry_object, result, owner='rmccord')
        setup_asm_fn_carry_nothing = _get_holstering_setup_asm_func(carry_nothing_posture, carry_object)
        setup_asm_fn_carry_nothing(carry_nothing_posture.asm)
        carry_nothing_posture.asm.request(carry_nothing_posture._enter_state_name, arb_holster)
        holster_element = create_run_animation(arb_holster)
        if flush_before_sequence:
            holster_element = (holster_element, flush_all_animations)
        yield from element_utils.run_child(timeline, holster_element)

    return (lambda _: _set_holster(), build_critical_section(interact_with_carried_object(carry_posture.sim, carry_object, interaction=carry_posture.source_interaction, animation_context=carry_posture.asm.context, must_run=True, sequence=holster), sequence, flush_all_animations))

def unholster_object(carry_posture, flush_before_sequence=False, sequence=None):
    carry_object = carry_posture.target

    def _set_unholster():
        carry_posture.holster_count = 0
        return True

    def unholster(timeline):
        if carry_object.is_sim:
            return
        if not carry_posture.holster_count:
            return
        arb_unholster = animation.arb.Arb()

        def start_carry(*_, **__):
            idle_arb = animation.arb.Arb()
            carry_posture.asm.request(carry_posture._state_name, idle_arb)
            distribute_arb_element(idle_arb)

        arb_unholster.register_event_handler(start_carry, handler_id=SCRIPT_EVENT_ID_START_CARRY)
        carry_posture.asm.context.register_custom_event_handler(functools.partial(hide_held_props, carry_posture.sim), None, 0, allow_stub_creation=True)
        carry_posture.asm.set_current_state('entry')
        carry_posture.asm.request(carry_posture._enter_state_name, arb_unholster)
        unholster_element = create_run_animation(arb_unholster)
        if flush_before_sequence:
            unholster_element = (unholster_element, flush_all_animations)
        yield from element_utils.run_child(timeline, unholster_element)

    return build_critical_section(interact_with_carried_object(carry_posture.sim, carry_object, animation_context=carry_posture.asm.context, interaction=carry_posture.source_interaction, must_run=True, sequence=build_critical_section(unholster, lambda _: _set_unholster())), sequence, flush_all_animations)

def get_carried_objects_gen(sim):
    posture_left = sim.posture_state.left
    if posture_left is not None and posture_left.target is not None:
        yield (Hand.LEFT, posture_left, posture_left.target)
    posture_right = sim.posture_state.right
    if posture_right is not None and posture_right.target is not None:
        yield (Hand.RIGHT, posture_right, posture_right.target)

def create_carry_nothing_constraint(hand, debug_name='CarryNothing'):
    entries = []
    if hand == Hand.LEFT:
        entries = (PostureManifestEntry(None, MATCH_ANY, MATCH_ANY, MATCH_ANY, MATCH_NONE, MATCH_ANY, MATCH_ANY),)
    else:
        entries = (PostureManifestEntry(None, MATCH_ANY, MATCH_ANY, MATCH_ANY, MATCH_ANY, MATCH_NONE, MATCH_ANY),)
    carry_posture_manifest = PostureManifest(entries)
    carry_posture_state_spec = PostureStateSpec(carry_posture_manifest, SlotManifest().intern(), PostureSpecVariable.ANYTHING)
    return interactions.constraints.Constraint(debug_name=debug_name, posture_state_spec=carry_posture_state_spec)

def create_carry_constraint(carry_target, hand=DEFAULT, strict=False, debug_name='CarryGeneric'):
    if carry_target is None:
        carry_target = MATCH_NONE
    entries = []
    if strict and hand is DEFAULT or hand == Hand.LEFT:
        entries.append(PostureManifestEntry(None, MATCH_ANY, MATCH_ANY, MATCH_ANY, carry_target, MATCH_ANY, MATCH_ANY))
    if hand is DEFAULT or hand == Hand.RIGHT:
        entries.append(PostureManifestEntry(None, MATCH_ANY, MATCH_ANY, MATCH_ANY, MATCH_ANY, carry_target, MATCH_ANY))
    carry_posture_manifest = PostureManifest(entries)
    carry_posture_state_spec = PostureStateSpec(carry_posture_manifest, SlotManifest().intern(), PostureSpecVariable.ANYTHING)
    return interactions.constraints.Constraint(debug_name=debug_name, posture_state_spec=carry_posture_state_spec)

class _CarryObjectProxy(ProxyObject):

    def __str__(self):
        return '[{}]'.format(super(ProxyObject, self).__str__())

def create_two_handed_carry_constraint(carry_object, carry_hand):
    other_carry_hand = Hand.RIGHT if carry_hand == Hand.LEFT else Hand.LEFT
    constraint_a = create_carry_constraint(carry_object, hand=carry_hand)
    constraint_b = create_carry_constraint(_CarryObjectProxy(carry_object), other_carry_hand)
    constraint = constraint_a.intersect(constraint_b)
    return constraint
