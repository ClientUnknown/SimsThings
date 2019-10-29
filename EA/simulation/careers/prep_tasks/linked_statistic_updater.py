
class LinkedStatisticUpdater:

    def __init__(self, sim_info, statistic, linked_statistic, multiplier):
        self._sim_info = sim_info
        self._statistic = statistic
        self._linked_statistic = linked_statistic
        self._multiplier = multiplier
        self._watcher = None

    def setup_watcher(self):
        tracker = self._sim_info.get_tracker(self._linked_statistic)
        self._watcher = tracker.add_delta_watcher(self._on_statistic_updated)

    def remove_watcher(self):
        tracker = self._sim_info.get_tracker(self._linked_statistic)
        if tracker.has_delta_watcher(self._watcher):
            tracker.remove_delta_watcher(self._watcher)
            self._watcher = None

    def _on_statistic_updated(self, stat_type, delta):
        if stat_type is self._linked_statistic:
            self._sim_info.get_statistic(self._statistic).add_value(delta*self._multiplier)
