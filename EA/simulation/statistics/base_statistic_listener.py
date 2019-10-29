from sims4.repr_utils import standard_reprimport sims4.loglogger = sims4.log.Logger('SimStatistics')
class BaseStatisticCallbackListener:
    __slots__ = ('_stat', '_threshold', '_callback', '_on_callback_alarm_reset')

    def __init__(self, stat, threshold, callback, on_callback_alarm_reset):
        self._stat = stat
        self._threshold = threshold
        self._callback = callback
        self._on_callback_alarm_reset = on_callback_alarm_reset

    @property
    def statistic_type(self):
        return self._stat.stat_type

    def __repr__(self):
        return standard_repr(self, stat=self.statistic_type.__name__, threshold=self._threshold, callback=self._callback.__name__)

    def destroy(self):
        pass

    def check_for_threshold(self, old_value, new_value):
        if self._threshold.compare(old_value) or self._threshold.compare(new_value):
            return True
        return False

    def trigger_callback(self):
        logger.debug('Triggering callback for stat {} at threshold {}; value = {}', self._stat, self._threshold, self._stat.get_value())
        self._callback(self._stat)

    @property
    def stat(self):
        return self._stat

    @property
    def threshold(self):
        return self._threshold
