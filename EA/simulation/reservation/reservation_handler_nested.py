from reservation.reservation_result import ReservationResult
class ReservationHandlerNested:

    def __init__(self):
        self._handlers = []

    def get_targets(self):
        targets = set()
        for handler in self._handlers:
            targets.update(handler.get_targets())
        return frozenset(targets)

    def add_handler(self, handler):
        self._handlers.append(handler)

    def begin_reservation(self, *_, **__):
        for handler in self._handlers:
            handler.begin_reservation()

    def end_reservation(self, *_, **__):
        for handler in self._handlers:
            handler.end_reservation()

    def do_reserve(self, sequence=None):
        for handler in self._handlers:
            sequence = handler.do_reserve(sequence=sequence)
        return sequence

    def may_reserve(self, *args, **kwargs):
        for handler in self._handlers:
            reserve_result = handler.may_reserve(*args, **kwargs)
            if not reserve_result:
                return reserve_result
        return ReservationResult.TRUE
