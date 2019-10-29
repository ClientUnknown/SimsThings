import functoolsfrom reservation.reservation_handler import _ReservationHandlerfrom reservation.reservation_handler_interlocked import ReservationHandlerInterlockedfrom reservation.reservation_handler_multi import ReservationHandlerMultifrom reservation.reservation_handler_uselist import ReservationHandlerUseListfrom reservation.reservation_result import ReservationResultimport sims4.loglogger = sims4.log.Logger('Reservation')
class ReservationHandlerBasic(_ReservationHandler):

    def allows_reservation(self, other_reservation_handler):
        if self._is_sim_allowed_to_clobber(other_reservation_handler):
            return ReservationResult.TRUE
        if isinstance(other_reservation_handler, ReservationHandlerUseList):
            return ReservationResult.TRUE
        if isinstance(other_reservation_handler, ReservationHandlerInterlocked):
            return ReservationResult.TRUE
        return ReservationResult(False, '{} disallows any other reservation type: ({})', self, other_reservation_handler, result_obj=self.sim)

    def begin_reservation(self, *args, **kwargs):
        if self.target.parts is not None:
            logger.error("\n                {} is attempting to execute a basic reservation on {}, which has parts. This is not allowed.\n                {} and its associated postures need to be allowed to run on the object's individual parts in order\n                for this to work properly.\n                ", self.sim, self.target, self.reservation_interaction.get_interaction_type() if self.reservation_interaction is not None else 'The reservation owner')
        return super().begin_reservation(*args, **kwargs)

class _ReservationHandlerMultiTarget(_ReservationHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._part_handlers = []

    def _get_reservation_handler_type(self):
        return ReservationHandlerBasic

    def _get_reservation_targets(self):
        raise NotImplementedError

    def allows_reservation(self, other_reservation_handler):
        for handler in self._part_handlers:
            reserve_result = handler.allows_reservation(other_reservation_handler)
            if not reserve_result:
                return reserve_result
        return ReservationResult.TRUE

    def begin_reservation(self, *_, **__):
        handler_type = self._get_reservation_handler_type()
        for target in self._get_reservation_targets():
            part_handler = handler_type(self._sim, target, reservation_interaction=self._reservation_interaction)
            part_handler.begin_reservation()
            self._part_handlers.append(part_handler)

    def end_reservation(self, *_, **__):
        for part_handler in self._part_handlers:
            part_handler.end_reservation()

    def may_reserve(self, **kwargs):
        handler_type = self._get_reservation_handler_type()
        for target in self._get_reservation_targets():
            part_handler = handler_type(self._sim, target, **kwargs)
            result = part_handler.may_reserve(**kwargs)
            if not result:
                return result
        return ReservationResult.TRUE

class ReservationHandlerAllParts(_ReservationHandlerMultiTarget):

    def _get_reservation_targets(self):
        target = self._target
        if target.is_part:
            target = target.part_owner
        if not target.parts:
            targets = (target,)
        else:
            targets = target.parts
        return targets

class ReservationHandlerUnmovableObjects(_ReservationHandlerMultiTarget):

    def _get_reservation_handler_type(self):
        return functools.partial(ReservationHandlerMulti, reservation_limit=None)

    def _get_reservation_targets(self):
        if self._target.live_drag_component is None and self._target.carryable_component is None:
            return (self._target,)
        return ()
