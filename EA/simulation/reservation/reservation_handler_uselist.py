from reservation.reservation_handler import _ReservationHandlerfrom reservation.reservation_result import ReservationResult
class ReservationHandlerUseList(_ReservationHandler):

    def allows_reservation(self, other_reservation_handler):
        return ReservationResult.TRUE
