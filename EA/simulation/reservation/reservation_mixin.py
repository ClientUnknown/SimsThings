from _collections import defaultdictfrom _weakrefset import WeakSetimport itertoolsfrom interactions.priority import Priorityfrom objects.object_enums import ResetReasonfrom reservation.reservation_handler_basic import ReservationHandlerBasic, ReservationHandlerAllPartsfrom reservation.reservation_handler_uselist import ReservationHandlerUseListfrom services.reset_and_delete_service import ResetRecordfrom sims4.callback_utils import CallableListimport gsi_handlersimport sims4.loglogger = sims4.log.Logger('ReservationHandler')
class ReservationMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reservation_handlers = ()
        self._on_reservation_handlers_changed = None
        self._reservation_clobberers = None

    @property
    def in_use(self):
        if self._reservation_handlers:
            return True
        return False

    @property
    def self_or_part_in_use(self):
        if self._reservation_handlers:
            return True
        elif self.parts:
            return any(part.in_use for part in self.parts)
        return False

    def in_use_by(self, sim, owner=None):
        for handler in self._reservation_handlers:
            if handler.sim is not sim:
                pass
            elif owner is not None and handler.reservation_interaction is not owner:
                pass
            else:
                return True
        return False

    def get_users(self, sims_only=False):
        users = set(handler.sim for handler in self._reservation_handlers if not sims_only or handler.sim.is_sim)
        if self.parts:
            for part in self.parts:
                users |= part.get_users(sims_only=sims_only)
        return frozenset(users)

    def get_reservation_handler(self, sim, **kwargs):
        reservation_type = ReservationHandlerBasic if not self.parts else ReservationHandlerAllParts
        return reservation_type(sim, self, **kwargs)

    def get_use_list_handler(self, sim, **kwargs):
        return ReservationHandlerUseList(sim, self, **kwargs)

    def may_reserve(self, sim, *_, reservation_handler=None, _from_reservation_call=False, **kwargs):
        if reservation_handler is None:
            reservation_handler = self.get_reservation_handler(sim)
        reserve_result = reservation_handler.may_reserve_internal(**kwargs)
        if gsi_handlers.sim_handlers_log.sim_reservation_archiver.enabled:
            reserve_result_str = '{}: {}'.format('reserve' if not _from_reservation_call else 'may_reserve', reserve_result)
            gsi_handlers.sim_handlers_log.archive_sim_reservation(reservation_handler, reserve_result_str)
        return reserve_result

    def add_reservation_handler(self, reservation_handler):
        if isinstance(self._reservation_handlers, tuple):
            self._reservation_handlers = WeakSet()
        self._reservation_handlers.add(reservation_handler)
        if self._on_reservation_handlers_changed:
            self._on_reservation_handlers_changed(user=reservation_handler.sim, added=True)

    def get_reservation_handlers(self):
        return tuple(self._reservation_handlers)

    def remove_reservation_handler(self, reservation_handler):
        if not self._reservation_handlers:
            return
        self._reservation_handlers.discard(reservation_handler)
        if self._on_reservation_handlers_changed:
            self._on_reservation_handlers_changed(user=reservation_handler.sim, added=False)

    def add_reservation_clobberer(self, reservation_holder, reservation_clobberer):
        if self._reservation_clobberers is None:
            self._reservation_clobberers = defaultdict(WeakSet)
        self._reservation_clobberers[reservation_holder].add(reservation_clobberer)

    def is_reservation_clobberer(self, reservation_holder, reservation_clobberer):
        if self._reservation_clobberers is None:
            return False
        if reservation_holder not in self._reservation_clobberers:
            return False
        return reservation_clobberer in self._reservation_clobberers[reservation_holder]

    def remove_reservation_clobberer(self, reservation_holder, reservation_clobberer):
        if self._reservation_clobberers is None:
            return
        if reservation_holder not in self._reservation_clobberers:
            return
        self._reservation_clobberers[reservation_holder].discard(reservation_clobberer)
        if not self._reservation_clobberers[reservation_holder]:
            del self._reservation_clobberers[reservation_holder]
        if not self._reservation_clobberers:
            self._reservation_clobberers = None

    def on_reset_get_interdependent_reset_records(self, reset_reason, reset_records):
        super().on_reset_get_interdependent_reset_records(reset_reason, reset_records)
        relevant_sims = self.get_users(sims_only=True)
        for sim in relevant_sims:
            if self.reset_reason() == ResetReason.BEING_DESTROYED:
                reset_records.append(ResetRecord(sim, ResetReason.RESET_EXPECTED, self, 'In use list of object being destroyed.'))
            else:
                body_target_part_owner = sim.posture_state.body.target
                if body_target_part_owner.is_part:
                    body_target_part_owner = body_target_part_owner.part_owner
                transition_controller = sim.queue.transition_controller
                if not transition_controller is None:
                    if not transition_controller.will_derail_if_given_object_is_reset(self):
                        reset_records.append(ResetRecord(sim, ResetReason.RESET_EXPECTED, self, 'Transitioning To or In.'))
                reset_records.append(ResetRecord(sim, ResetReason.RESET_EXPECTED, self, 'Transitioning To or In.'))

    def usable_by_transition_controller(self, transition_controller):
        if transition_controller is None:
            return False
        required_sims = transition_controller.interaction.required_sims()
        targets = (self,) + tuple(self.get_overlapping_parts()) if self.is_part else (self,)
        for reservation_handler in itertools.chain.from_iterable(target.get_reservation_handlers() for target in targets):
            if reservation_handler.sim in required_sims:
                pass
            else:
                reservation_interaction = reservation_handler.reservation_interaction
                if reservation_interaction is None:
                    pass
                else:
                    if reservation_interaction.priority >= transition_controller.interaction.priority:
                        return False
                    if transition_controller.interaction.priority <= Priority.Low:
                        return False
        return True

    def register_on_use_list_changed(self, callback):
        if self._on_reservation_handlers_changed is None:
            self._on_reservation_handlers_changed = CallableList()
        self._on_reservation_handlers_changed.append(callback)

    def unregister_on_use_list_changed(self, callback):
        if callback in self._on_reservation_handlers_changed:
            self._on_reservation_handlers_changed.remove(callback)
            if not self._on_reservation_handlers_changed:
                self._on_reservation_handlers_changed = None
