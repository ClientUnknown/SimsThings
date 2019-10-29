
class ReservationResult:
    __slots__ = ('result', '_reason', '_format_args', 'result_obj')
    TRUE = None

    def __init__(self, result, *args, result_obj=None):
        self.result = result
        if args:
            self._reason = args[0]
            self._format_args = args[1:]
        else:
            (self._reason, self._format_args) = (None, ())
        self.result_obj = result_obj

    def __str__(self):
        if self.reason:
            return self.reason
        return str(self.result)

    def __repr__(self):
        if self.reason:
            return '<ReservationResult: {0} ({1})>'.format(bool(self.result), self.reason)
        return '<ReservationResult: {0}>'.format(bool(self.result))

    def __bool__(self):
        if self.result:
            return True
        return False

    @property
    def reason(self):
        if self._reason:
            self._reason = self._reason.format(*self._format_args)
            self._format_args = ()
        return self._reason
ReservationResult.TRUE = ReservationResult(True)