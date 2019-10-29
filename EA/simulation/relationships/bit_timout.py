import alarmsimport clockimport servicesimport sims4.loglogger = sims4.log.Logger('Relationship', default_owner='jjacobson')
class BitTimeoutData:

    def __init__(self, bit, alarm_callback):
        self._bit = bit
        self._alarm_callback = alarm_callback
        self._alarm_handle = None
        self._start_time = 0

    @property
    def bit(self):
        return self._bit

    @property
    def alarm_handle(self):
        return self._alarm_handle

    def reset_alarm(self):
        logger.assert_raise(self._bit is not None, '_bit is None in BitTimeoutData.')
        if self._alarm_handle is not None:
            self.cancel_alarm()
        self._set_alarm(self._bit.timeout)

    def cancel_alarm(self):
        if self._alarm_handle is not None:
            alarms.cancel_alarm(self._alarm_handle)
            self._alarm_handle = None

    def load_bit_timeout(self, time):
        self.cancel_alarm()
        time_left = self._bit.timeout - time
        if time_left > 0:
            self._set_alarm(time_left)
            return True
        else:
            logger.warn('Invalid time loaded for timeout for bit {}.  This is valid if the tuning data changed.', self._bit)
            return False

    def get_elapsed_time(self):
        if self._alarm_handle is not None:
            now = services.time_service().sim_now
            delta = now - self._start_time
            return delta.in_minutes()
        return 0

    def _set_alarm(self, time):
        time_span = clock.interval_in_sim_minutes(time)
        self._alarm_handle = alarms.add_alarm(self, time_span, self._alarm_callback, repeating=False, cross_zone=True)
        logger.assert_raise(self._alarm_handle is not None, 'Failed to create timeout alarm for rel bit {}'.format(self.bit))
        self._start_time = services.time_service().sim_now
