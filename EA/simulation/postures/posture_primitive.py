from animation.animation_utils import create_run_animation, flush_all_animations_instantly, flush_all_animationsfrom animation.awareness.awareness_elements import with_audio_awarenessfrom element_utils import CleanupTypefrom element_utils import build_element, build_critical_section_with_finallyfrom postures import PostureEvent, PostureTrackfrom primitives.staged import StageControllerElementimport element_utilsimport servicesimport sims4.loglogger = sims4.log.Logger('Postures')
class PosturePrimitive(StageControllerElement):

    def __init__(self, posture, animate_in, dest_state, context, routing_surface):
        super().__init__(posture.sim)
        self._posture = posture
        self._animate_in = animate_in
        self._dest_state = dest_state
        self._context = context
        self._routing_surface = routing_surface
        self._posture_censor_handle = None
        self.finished = False
        self._prev_posture = None
        if dest_state.body.source_interaction is None:
            logger.error('{}: Aspect has no source: {}', self, dest_state.body)

    def __repr__(self):
        return '{}({})'.format(type(self).__name__, self._posture)

    def _do_perform_gen(self, timeline):
        posture_element = self._get_behavior()
        result = yield from element_utils.run_child(timeline, posture_element)
        return result

    def _get_behavior(self):
        posture = self._posture
        sim = posture.sim
        multi_sim_posture_transition = posture.multi_sim and not posture.is_puppet
        prev_posture_state = sim.posture_state
        self._prev_posture = prev_posture_state.get_aspect(posture.track)
        animate_in = None
        if not self._animate_in.empty:
            animate_in = create_run_animation(self._animate_in)
        my_stage = self._stage()

        def posture_change(timeline):
            posture.log_info('Change', msg='{}'.format(posture.track.name if posture.track is not None else 'NO TRACK!'))
            prev_posture_state = sim.posture_state
            prev_posture = prev_posture_state.get_aspect(posture.track)
            sim.posture_state = self._dest_state
            sim.on_posture_event(PostureEvent.POSTURE_CHANGED, self._dest_state, posture.track, prev_posture, posture)
            if sim.routing_surface != self._routing_surface:
                sim.move_to(routing_surface=self._routing_surface)
            yield from sim.si_state.notify_posture_change_and_remove_incompatible_gen(timeline, prev_posture_state, self._dest_state)
            prev_posture.clear_owning_interactions()
            if multi_sim_posture_transition:
                linked_posture_begin = posture.linked_posture.begin(self._animate_in, self._dest_state.linked_posture_state, posture._context, self._routing_surface)
                self._dest_state = None
                yield from element_utils.run_child(timeline, linked_posture_begin)
            else:
                self._dest_state = None
            return True

        def end_posture_on_same_track(timeline):
            if self._prev_posture is not None and self._prev_posture is not posture:
                prev_posture = self._prev_posture
                self._prev_posture = None
                result = yield from element_utils.run_child(timeline, build_element(prev_posture.end()))
                return result
            return True

        if multi_sim_posture_transition or self._animate_in is not None and services.current_zone().animate_instantly:
            flush = flush_all_animations_instantly
        else:
            flush = flush_all_animations
        sequence = (posture_change, animate_in, flush, end_posture_on_same_track, my_stage)
        if posture.target is not None:
            sequence = with_audio_awareness(posture.target, sequence=sequence)
        sequence = build_element(sequence, critical=CleanupType.RunAll)
        sequence = build_critical_section_with_finally(sequence, lambda _: posture._release_animation_context())
        sequence = build_critical_section_with_finally(sequence, self._posture.get_destroy_jig())
        if posture.target is not None:
            if PostureTrack.is_body(posture.track):
                reserve_handler = posture.source_interaction.get_interaction_reservation_handler(target=posture.target) if posture.source_interaction is not None else None
            else:
                reserve_handler = posture.target.get_reservation_handler(sim)
            if reserve_handler is None:
                reserve_handler = posture.target.get_use_list_handler(sim)
            sequence = reserve_handler.do_reserve(sequence=sequence)

        def stage_on_fail(timeline):
            if not self.has_staged:
                yield from element_utils.run_child(timeline, self._stage_fail())

        sequence = element_utils.build_critical_section(sequence, stage_on_fail)
        return sequence

    def _hard_stop(self):
        super()._hard_stop()
        if self._prev_posture._primitive is not self:
            self._prev_posture._primitive.trigger_hard_stop()
            self._prev_posture = None
        if self._prev_posture is not None and self._prev_posture._primitive is not None and self._posture is not None:
            self._posture._on_reset()
            self._posture = None
