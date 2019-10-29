import weakreffrom animation.animation_utils import get_auto_exitfrom animation.arb_element import distribute_arb_elementfrom balloon.passive_balloons import PassiveBalloonsfrom element_utils import must_runfrom event_testing.results import TestResultfrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.route_fail import handle_transition_failurefrom postures import PostureTrack, PostureEventfrom postures.posture_state import PostureStatefrom sims4 import mathfrom sims4.collections import frozendictimport animation.arbimport element_utilsimport elementsimport enumimport muteximport simsimport sims4.loglogger = sims4.log.Logger('PostureTransition')
class PostureStateTransition(elements.SubclassableGeneratorElement):

    def __init__(self, dest_state, source_interaction, context, var_map, transition_spec, reason_interaction, owning_interaction, should_reserve, destination_constraint):
        super().__init__()
        self._dest_state = dest_state
        self._source_interaction = source_interaction
        self._context = context
        self._var_map = var_map
        self._reason_interaction_ref = weakref.ref(reason_interaction)
        self._owning_interaction_ref = weakref.ref(owning_interaction) if owning_interaction is not None else None
        self._transition = None
        self._transition_spec = transition_spec
        self._should_reserve = should_reserve
        self._destination_constraint = destination_constraint

    @property
    def is_routing(self):
        if self._transition is not None:
            return self._transition.is_routing
        return False

    @property
    def dest_state(self):
        return self._dest_state

    def _run_gen(self, timeline):
        dest_state = self._dest_state
        sim = dest_state.sim
        source_state = sim.posture_state
        dest_aspect = None
        if source_state.body != dest_state.body:
            dest_aspect = dest_state.body
        if source_state.left != dest_state.left:
            dest_aspect = dest_state.left
        if source_state.right != dest_state.right:
            dest_aspect = dest_state.right

        def create_transition(dest_aspect):
            reserve_target_interaction = None
            if self._should_reserve:
                reserve_target_interaction = self._reason_interaction_ref()
            return PostureTransition(dest_aspect, dest_state, self._context, self._var_map, self._transition_spec, reserve_target_interaction, self._destination_constraint)

        if dest_aspect is None:
            if source_state.body.mobile and dest_state.body.mobile:
                self._transition = create_transition(dest_state.body)
                transition_result = yield from element_utils.run_child(timeline, self._transition)
                if not transition_result:
                    return transition_result
            new_posture_spec = sim.posture_state.get_posture_spec(self._var_map)
            self._dest_state = PostureState(sim, sim.posture_state, new_posture_spec, self._var_map)
            dest_state = self._dest_state
            sim.posture_state = dest_state
            if self._source_interaction is not None:
                dest_state.body.source_interaction = self._source_interaction
            if self._owning_interaction_ref is not None:
                self._owning_interaction_ref().acquire_posture_ownership(dest_state.body)
            yield from sim.si_state.notify_posture_change_and_remove_incompatible_gen(timeline, source_state, dest_state)
            return TestResult.TRUE
        if self._source_interaction is not None:
            dest_aspect.source_interaction = self._source_interaction
        if self._owning_interaction_ref is not None:
            self._owning_interaction_ref().acquire_posture_ownership(dest_aspect)
        self._transition = create_transition(dest_aspect)
        result = yield from element_utils.run_child(timeline, self._transition)
        return result

class PostureTransition(elements.SubclassableGeneratorElement):

    class Status(enum.Int, export=False):
        INITIAL = 0
        ROUTING = 1
        ANIMATING = 2
        FINISHED = 3

    IDLE_TRANSITION_XEVT = 750
    IDLE_STOP_CUSTOM_XEVT = 751
    DISTANCE_HIGH = 1.0
    DISTANCE_MID = 0.8

    def __init__(self, dest, dest_state, context, var_map, transition_spec=None, interaction=None, constraint=None, locked_params=frozendict()):
        super().__init__()
        self._source = None
        self._dest = dest
        self._dest_state = dest_state
        self._context = context
        self._var_map = var_map
        self._status = self.Status.INITIAL
        self._transition_spec = transition_spec
        self._interaction = interaction
        self._constraint = constraint
        self._locked_params = locked_params

    def __repr__(self):
        return '<PostureTransition: {} to {}>'.format(self._source or 'current posture', self._dest)

    @property
    def destination_posture(self):
        return self._dest

    @property
    def status(self):
        return self._status

    @property
    def is_routing(self):
        return self._status == self.Status.ROUTING

    @property
    def source(self):
        return self._source

    def get_entry_exit_mutex_key(self):
        if self._source.mutex_entry_exit_animations and self._dest.mutex_entry_exit_animations:
            logger.assert_raise(True, 'Attempt to mutex both the source and dest of a posture transition: {} -> {}'.format(self._source, self._dest))
        if self._source.mutex_entry_exit_animations:
            return self._source.target
        elif self._dest.mutex_entry_exit_animations:
            return self._dest.target

    def _get_unholster_predicate(self, sim, interaction):

        def unholster_predicate(obj):
            if self._transition_spec is not None:
                path = self._transition_spec.path
                if path is not None and obj.should_unholster(sim=sim, path=path):
                    return True
            if interaction is None:
                return True
            return interaction.should_unholster_carried_object(obj)

        return unholster_predicate

    def _get_unholster_after_predicate(self, sim, interaction):

        def unholster_after_predicate(obj):
            if interaction is not None:
                if interaction.should_unholster_carried_object(obj):
                    return True
                elif sim.is_required_to_holster_while_routing(obj):
                    return False
            return True

        return unholster_after_predicate

    @classmethod
    def calculate_distance_param(cls, source, dest):
        if source is None or dest is None:
            return
        distance_vector = source.position - dest.position
        distance_from_pos = distance_vector.magnitude()
        if distance_from_pos < math.EPSILON:
            distance_param = 'zero'
        elif distance_from_pos >= cls.DISTANCE_HIGH:
            distance_param = 'high'
        elif distance_from_pos >= cls.DISTANCE_MID and distance_from_pos < cls.DISTANCE_HIGH:
            distance_param = 'mid'
        else:
            distance_param = 'low'
        return distance_param

    def _do_transition(self, timeline) -> bool:
        source = self._source
        dest = self._dest
        sim = dest.sim
        posture_track = dest.track
        starting_position = sim.position

        def do_auto_exit(timeline):
            auto_exit_element = get_auto_exit((sim,), asm=source.asm)
            if auto_exit_element is not None:
                yield from element_utils.run_child(timeline, auto_exit_element)

        if self._transition_spec is not None and self._transition_spec.portal_obj is not None:
            portal_obj = self._transition_spec.portal_obj
            if self._transition_spec.portal_id is not None:
                new_routing_surface = portal_obj.get_target_surface(self._transition_spec.portal_id)
        elif dest.unconstrained or dest.target is not None:
            new_routing_surface = dest.target.routing_surface
        elif self._constraint is not None:
            new_routing_surface = self._constraint.routing_surface
        else:
            new_routing_surface = sim.routing_surface
        arb = animation.arb.Arb()
        if dest.external_transition:
            dest_begin = dest.begin(None, self._dest_state, self._context, new_routing_surface)
            result = yield from element_utils.run_child(timeline, must_run(dest_begin))
            return result
        try:
            sim.active_transition = self
            posture_idle_started = False

            def start_posture_idle(*_, **__):
                nonlocal posture_idle_started
                if posture_idle_started:
                    return
                dest.log_info('Idle')
                posture_idle_started = True
                idle_arb = animation.arb.Arb()
                dest.append_idle_to_arb(idle_arb)
                distribute_arb_element(idle_arb, master=sim)

            arb.register_event_handler(start_posture_idle, handler_id=self.IDLE_TRANSITION_XEVT)
            if self._transition_spec is not None:
                if sim.posture.mobile and self._transition_spec.path is not None:
                    yield from element_utils.run_child(timeline, do_auto_exit)
                    result = yield from self.do_transition_route(timeline, sim, source, dest)
                    if not result:
                        if self._transition_spec.is_failure_path:
                            (failure_reason, failure_target) = sim.transition_controller.get_failure_reason_and_target(sim)
                            if failure_reason is not None or failure_target is not None:
                                if self._interaction is not None:
                                    yield from element_utils.run_child(timeline, handle_transition_failure(sim, self._interaction.target, self._interaction, failure_reason=failure_reason, failure_object_id=failure_target))
                                sim.transition_controller.cancel(cancel_reason_msg='Transition canceled due to successful route failure.')
                        return result
                else:
                    result = self._transition_spec.do_reservation(sim)
                    if not result:
                        return result
            if source is dest:
                sim.on_posture_event(PostureEvent.POSTURE_CHANGED, self._dest_state, dest.track, source, dest)
                return TestResult.TRUE
            self._status = self.Status.ANIMATING
            source_locked_params = frozendict()
            dest_locked_params = frozendict()
            if self._transition_spec is not None:
                source_locked_params = self._transition_spec.locked_params
                dest_locked_params = self._transition_spec.locked_params
            dest_posture_spec = None
            import services
            zone = services.current_zone()
            fire_service = services.get_fire_service()
            lot_on_fire = fire_service.fire_is_active
            distance_param = PostureTransition.calculate_distance_param(source.target, dest.target)
            if dest.track == PostureTrack.BODY:
                if not source.mobile:
                    source_locked_params += {'onFire': lot_on_fire}
                    if distance_param is not None:
                        source_locked_params += {'distance': distance_param}
                if not dest.mobile:
                    dest_locked_params += {'onFire': lot_on_fire}
                    if self._interaction is not None:
                        transition_asm_params = sim.get_transition_asm_params()
                        dest_locked_params += transition_asm_params
                        source_locked_params += transition_asm_params
                    if distance_param is not None:
                        dest_locked_params += {'distance': distance_param}
                elif self._transition_spec.portal_obj is not None:
                    transition_asm_params = sim.get_transition_asm_params()
                    dest_locked_params += transition_asm_params
                    source_locked_params += transition_asm_params
                transition_global_asm_params = sim.get_transition_global_asm_params()
                dest_locked_params += transition_global_asm_params
                source_locked_params += transition_global_asm_params
                dest_posture_spec = self._transition_spec.posture_spec
            source_locked_params += self._locked_params
            dest_locked_params += self._locked_params
            if self._transition_spec is not None and self._transition_spec is not None and self._transition_spec.portal_obj is not None:
                target_override = self._transition_spec.portal_obj
                portal_params = self._transition_spec.portal_obj.get_portal_asm_params(self._transition_spec.portal_id, sim)
                source_locked_params += portal_params
                dest_locked_params += portal_params
            else:
                target_override = None

            def do_transition_animation(timeline):
                yield from element_utils.run_child(timeline, do_auto_exit)
                if PostureTrack.is_carry(dest.track) and dest.target is not None and dest.target.is_sim:
                    auto_exit_element = get_auto_exit((dest.target,), asm=source.asm)
                    if auto_exit_element is not None:
                        yield from element_utils.run_child(timeline, auto_exit_element)
                source.append_exit_to_arb(arb, self._dest_state, dest, self._var_map, locked_params=source_locked_params, target_override=target_override)
                dest.append_transition_to_arb(arb, source, locked_params=dest_locked_params, posture_spec=dest_posture_spec, target_override=target_override)
                dest_begin = dest.begin(arb, self._dest_state, self._context, new_routing_surface)
                result = yield from element_utils.run_child(timeline, [do_auto_exit, dest_begin])
                return result

            sequence = (do_transition_animation,)
            from carry.carry_utils import interact_with_carried_object, holster_carried_object, maybe_holster_objects_through_sequence
            if dest.track.is_carry(dest.track):
                if dest.target is not None:
                    carry_target = dest.target
                    carry_posture_state = self._dest_state
                    carry_animation_context = dest.asm.context
                else:
                    carry_target = source.target
                    carry_posture_state = sim.posture_state
                    carry_animation_context = source.asm.context
                sequence = interact_with_carried_object(sim, carry_target, posture_state=carry_posture_state, interaction=dest.source_interaction, animation_context=carry_animation_context, sequence=sequence)
            if sim.is_required_to_holster_for_transition(source, dest):
                sequence = maybe_holster_objects_through_sequence(sim, sequence=sequence, unholster_after_predicate=self._get_unholster_after_predicate(sim, dest.source_interaction))
            else:
                sequence = holster_carried_object(sim, dest.source_interaction, self._get_unholster_predicate(sim, dest.source_interaction), flush_before_sequence=True, sequence=sequence)
            sequence = dest.add_transition_extras(sequence, arb=arb)
            mutex_key = self.get_entry_exit_mutex_key()
            if mutex_key is not None:
                sequence = mutex.with_mutex(mutex_key, element_utils.build_element(sequence))
            sis = set()
            sis.add(source.source_interaction)
            sis.add(dest.source_interaction)
            sis.update(source.owning_interactions)
            sis.update(dest.owning_interactions)
            for si in sis:
                if si is None:
                    pass
                else:
                    with si.cancel_deferred(sis):
                        result = yield from element_utils.run_child(timeline, must_run(sequence))
                    break
            result = yield from element_utils.run_child(timeline, must_run(sequence))
            if result:
                start_posture_idle()
            yield from sim.si_state.process_gen(timeline)
        finally:
            sim.active_transition = None
            self._status = self.Status.FINISHED
            if self._transition_spec is not None:
                self._transition_spec.release_additional_reservation_handlers()
                self._transition_spec.remove_props_created_to_reserve_slots(sim)
                if self._transition_spec.portal_obj is not None:
                    self._transition_spec.portal_obj.clear_portal_cost_override(self._transition_spec.portal_id, sim=sim)
        if sim.posture_state.get_aspect(posture_track) is not dest:
            logger.debug("{}: _do_transition failed: after transition Sim's posture state aspect isn't destination posture.")
            if dest.source_interaction is not None:
                dest.source_interaction.cancel(FinishingType.TRANSITION_FAILURE, cancel_reason_msg='Transition canceled during transition.')
            return TestResult(False, "After transition Sim's posture state aspect isn't destination posture.")
        if dest.unconstrained or not (sim.transition_controller is not None and sims4.math.vector3_almost_equal(sim.position, starting_position, epsilon=sims4.geometry.ANIMATION_SLOT_EPSILON)):
            sim.transition_controller.release_stand_slot_reservations((sim,))
        return TestResult.TRUE

    def do_transition_route(self, timeline, sim, source, dest):
        self._status = self.Status.ROUTING
        if self._transition_spec is None:
            return TestResult.TRUE
        path = self._transition_spec.path
        if path is None:
            return TestResult.TRUE
        constraint = self._dest_state.constraint_intersection
        fade_sim_out = self._interaction.should_fade_sim_out() if self._interaction is not None else False
        lock_out_socials = isinstance(self._interaction, sims.self_interactions.TravelInteraction)
        sequence = self._transition_spec.get_transition_route(sim, fade_sim_out, lock_out_socials, dest)
        from carry.carry_utils import holster_objects_for_route, holster_carried_object
        if path.length() > 0:
            sequence = holster_objects_for_route(sim, sequence=sequence)
        if self._interaction.walk_style is not None:
            walkstyle_request = self._interaction.walk_style(sim)
            sequence = walkstyle_request(sequence=sequence)
        sequence = holster_carried_object(sim, dest.source_interaction, self._get_unholster_predicate(sim, dest.source_interaction), flush_before_sequence=True, sequence=sequence)
        if self._interaction is not None and self._interaction is not None:
            PassiveBalloons.request_routing_to_object_balloon(sim, self._interaction)
        result = yield from element_utils.run_child(timeline, sequence)
        sim.schedule_environment_score_update(force_run=True)
        if not result:
            logger.debug('{}: Transition canceled or failed: {}', self, result)
            return TestResult(False, 'Transition Route/Reservation Failed')
        return TestResult.TRUE

    def _run_gen(self, timeline):
        dest = self._dest
        posture_track = dest.track
        sim = dest.sim
        source = sim.posture_state.get_aspect(posture_track)
        self._source = source
        dest.log_info('Transition', msg='from {}'.format(source))
        dest.sim.on_posture_event(PostureEvent.TRANSITION_START, self._dest_state, posture_track, source, dest)
        result = yield from self._do_transition(timeline)
        if result:
            dest.sim.on_posture_event(PostureEvent.TRANSITION_COMPLETE, self._dest_state, posture_track, source, dest)
        else:
            dest.sim.on_posture_event(PostureEvent.TRANSITION_FAIL, self._dest_state, posture_track, source, dest)
        return result
