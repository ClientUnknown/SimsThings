from sims4.localization import TunableLocalizedStringimport sims4.loglogger = sims4.log.Logger('Multi Motive Buff Tracker')
class MultiMotiveBuffTracker:
    MULTI_MOTIVE_BUFF_REASON = TunableLocalizedString(description='\n        The localized string used to give reason why buff was added.  Does not\n        support any tokens.\n        ')

    def __init__(self, sim, multi_motive_buff_motives, buff):
        self._buff_handle = None
        self._owner = sim
        self._motive_count = 0
        self._commodity_callback = {}
        self._watcher_handle = None
        self._multi_motive_buff_motives = multi_motive_buff_motives
        self._buff = buff
        self.setup_callbacks()

    def setup_callbacks(self):
        self._motive_count = 0
        if self._buff_handle is not None:
            self._owner.remove_buff(self._buff_handle)
        self._buff_handle = None
        tracker = self._owner.commodity_tracker
        for (commodity_type, threshold) in self._multi_motive_buff_motives.items():
            commodity_inst = tracker.get_statistic(commodity_type)
            callback = self._commodity_callback.get(commodity_type, None)
            self._commodity_callback[commodity_type] = None
            if commodity_inst is not None:
                if callback is not None:
                    commodity_inst.remove_callback_listener(callback)
                self._add_commodity_callback(commodity_inst, threshold, add=False)
            else:
                if threshold.compare(tracker.get_value(commodity_type)):
                    self._increment_multi_motive_buff_count(None, add=False)
                if self._watcher_handle is None:
                    self._watcher_handle = tracker.add_watcher(self._statistic_added_to_tracker_callback)
        tracker.remove_on_remove_callback(self._statistic_removed_from_tracker)
        tracker.add_on_remove_callback(self._statistic_removed_from_tracker)
        if self._motive_count >= len(self._multi_motive_buff_motives):
            self._buff_handle = self._owner.add_buff(self._buff, buff_reason=self.MULTI_MOTIVE_BUFF_REASON)

    def cleanup_callbacks(self):
        tracker = self._owner.commodity_tracker
        tracker.remove_on_remove_callback(self._statistic_removed_from_tracker)
        if self._buff_handle is not None:
            self._owner.remove_buff(self._buff_handle)
        self._buff_handle = None
        self._buff = None
        for commodity_type in self._multi_motive_buff_motives:
            commodity_inst = tracker.get_statistic(commodity_type)
            if commodity_inst is not None:
                callback = self._commodity_callback.get(commodity_type, None)
                if callback is not None:
                    commodity_inst.remove_callback_listener(callback)
        self._commodity_callback.clear()
        if self._watcher_handle is not None and tracker.has_watcher(self._watcher_handle):
            tracker.remove_watcher(self._watcher_handle)
        self._watcher_handle = None

    def _statistic_added_to_tracker_callback(self, stat_type, old_value, new_value):
        if stat_type not in self._multi_motive_buff_motives:
            return
        callback = self._commodity_callback.get(stat_type, None)
        if callback is not None:
            return
        tracker = self._owner.get_tracker(stat_type)
        stat_instance = tracker.get_statistic(stat_type)
        threshold = self._multi_motive_buff_motives.get(stat_type)
        if threshold.compare(stat_instance.get_value()):
            if threshold.compare(stat_instance.convergence_value):
                self._commodity_callback[stat_type] = stat_instance.create_and_add_callback_listener(self._multi_motive_buff_motives[stat_type].inverse(), self._decrement_multi_motive_buff_count)
            else:
                self._increment_multi_motive_buff_count(stat_instance)
        elif threshold.compare(stat_instance.convergence_value):
            self._decrement_multi_motive_buff_count(stat_instance)
        else:
            self._commodity_callback[stat_type] = stat_instance.create_and_add_callback_listener(threshold, self._increment_multi_motive_buff_count)
        if self._watcher_handle is not None:
            tracker.remove_watcher(self._watcher_handle)
            self._watcher_handle = None

    def _statistic_removed_from_tracker(self, stat_instance):
        stat_type = stat_instance.stat_type
        threshold = self._multi_motive_buff_motives.get(stat_type, None)
        if threshold is not None:
            self._remove_commodity_callback(stat_instance)
            tracker = self._owner.get_tracker(stat_type)
            if threshold.compare(stat_instance.get_value()):
                if not threshold.compare(tracker.get_value(stat_type)):
                    self._decrement_multi_motive_buff_count(stat_instance, add_callback=False)
            elif threshold.compare(tracker.get_value(stat_type)):
                self._increment_multi_motive_buff_count(None, add=True)
            if self._watcher_handle is None:
                self._watcher_handle = tracker.add_watcher(self._statistic_added_to_tracker_callback)
        return False

    def _increment_multi_motive_buff_count(self, stat_instance, add=True):
        if stat_instance is not None:
            commodity_type = stat_instance.stat_type
            self._remove_commodity_callback(stat_instance)
            self._commodity_callback[commodity_type] = stat_instance.create_and_add_callback_listener(self._multi_motive_buff_motives[commodity_type].inverse(), self._decrement_multi_motive_buff_count)
        self._motive_count += 1
        if self._motive_count >= len(self._multi_motive_buff_motives):
            self._buff_handle = self._owner.add_buff(self._buff, buff_reason=self.MULTI_MOTIVE_BUFF_REASON)

    def _decrement_multi_motive_buff_count(self, stat_instance, add_callback=True):
        commodity_type = stat_instance.stat_type
        self._remove_commodity_callback(stat_instance)
        if add_callback:
            self._commodity_callback[commodity_type] = stat_instance.create_and_add_callback_listener(self._multi_motive_buff_motives[commodity_type], self._increment_multi_motive_buff_count)
        if self._buff_handle is not None:
            self._owner.remove_buff(self._buff_handle)
        self._buff_handle = None
        self._motive_count -= 1

    def _add_commodity_callback(self, stat_instance, threshold, add=True):
        stat_type = stat_instance.stat_type
        if threshold.compare(stat_instance.get_value()):
            self._increment_multi_motive_buff_count(stat_instance, add=add)
        else:
            self._commodity_callback[stat_type] = stat_instance.create_and_add_callback_listener(threshold, self._increment_multi_motive_buff_count)

    def _remove_commodity_callback(self, stat_instance):
        stat_type = stat_instance.stat_type
        callback = self._commodity_callback.get(stat_type, None)
        if callback is not None:
            stat_instance.remove_callback_listener(callback)
            self._commodity_callback[stat_type] = None
