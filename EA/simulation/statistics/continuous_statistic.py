import contextlibimport mathimport operatorfrom date_and_time import DateAndTime, create_date_and_timefrom event_testing.resolver import SingleSimResolverfrom sims4.math import Thresholdfrom sims4.tuning.tunable import TunableRangefrom sims4.utils import classproperty, flexmethodfrom singletons import UNSET, DEFAULTfrom statistics.base_statistic import BaseStatisticfrom statistics.base_statistic_listener import BaseStatisticCallbackListenerfrom statistics.statistic_enums import StatisticLockActionimport alarmsimport clockimport date_and_timeimport enumimport servicesimport sims4.logimport sims4.math__unittest__ = 'test.statistics.continuous_statistic_tests'
class DelayedDecayStatus(enum.Int, export=False):
    ACTIVE = -1
    NOT_TUNED = -2
    NOT_TRACKED = -3
logger = sims4.log.Logger('SimStatistics')
class _ContinuousStatisticCallbackData(BaseStatisticCallbackListener):
    __slots__ = '_trigger_time'

    def __init__(self, stat, callback, threshold, on_callback_alarm_reset=None):
        super().__init__(stat, threshold, callback, on_callback_alarm_reset)
        self._trigger_time = UNSET

    def reset_trigger_time(self, new_trigger_interval:float):
        if new_trigger_interval is not None and new_trigger_interval > 0:
            now = services.time_service().sim_now
            self._trigger_time = now + clock.interval_in_sim_minutes(new_trigger_interval)
        else:
            self._trigger_time = None
        if self._on_callback_alarm_reset is not None:
            self._on_callback_alarm_reset(self._stat, self._trigger_time)

    def destroy(self):
        self._trigger_time = UNSET

    def is_valid(self):
        return self._trigger_time is not UNSET

    def will_be_called_at_the_same_time_as(self, other):
        if self.trigger_time is UNSET or (self.trigger_time is None or other.trigger_time is UNSET) or other.trigger_time is None:
            return False
        elif self.trigger_time.absolute_ticks() == other.trigger_time.absolute_ticks():
            return True

    def calculate_next_trigger_time(self):
        if self._trigger_time is UNSET:
            logger.warn('Attempting to calculate the interval on a callback that was never inserted into the _callbacks list: {}', self)
            return
        if self._trigger_time == None:
            return
        now = services.time_service().sim_now
        delta = self._trigger_time - now
        return delta

    @property
    def trigger_time(self):
        return self._trigger_time

    def __lt__(self, other):
        if self._trigger_time is None and other._trigger_time is None:
            return False
        if other._trigger_time is None:
            return True
        if self._trigger_time is None:
            return False
        return self._trigger_time < other._trigger_time

    def __gt__(self, other):
        if self._trigger_time is None and other._trigger_time is None:
            return False
        if other._trigger_time is None:
            return False
        if self._trigger_time is None:
            return True
        return self._trigger_time > other._trigger_time

class ContinuousStatistic(BaseStatistic):
    SAVE_VALUE_MULTIPLE = TunableRange(description='\n        When saving the value of a continuous statistic, we force stats to the \n        nearest multiple of this tunable for save of inventory \n        items to increase the chance of stacking success.-Mike Duke\n        \n        EX: 95+ = 100, 85 to 94.9 = 90, ..., -5 to 5 = 0, ..., -95 to -100 = -100\n        ', tunable_type=int, minimum=1, default=10)
    decay_rate = 0
    _default_convergence_value = 0

    def __init__(self, tracker, initial_value):
        super().__init__(tracker, initial_value)
        self._decay_enabled = False
        self._decay_rate_override = UNSET
        self._delayed_decay_rate_override = UNSET
        self._initial_delay_override = UNSET
        self._final_delay_override = UNSET
        self._suppress_update_active_callbacks = False
        self._alarm_handle = None
        self._active_callback = None
        self._last_update = services.time_service().sim_now
        self._decay_rate_modifier = 1
        self._decay_rate_modifiers = None
        self._convergence_value = self._default_convergence_value
        if self._tracker is None or not self._tracker.load_in_progress:
            self._recalculate_modified_decay_rate()
        self._delayed_decay_timer = None
        self._time_of_last_value_change = None
        self._delayed_decay_active = False
        self._decay_callback_handle = None

    def on_initial_startup(self):
        pass

    def start_low_level_simulation(self):
        pass

    def stop_low_level_simulation(self):
        pass

    def stop_regular_simulation(self):
        pass

    def on_zone_load(self):
        pass

    @classproperty
    def default_value(cls):
        return cls._default_convergence_value

    @classproperty
    def continuous(self):
        return True

    @flexmethod
    def get_value(cls, inst):
        if inst is not None:
            inst._update_value()
        return super(ContinuousStatistic, inst if inst is not None else cls).get_value()

    def set_value(self, value, **kwargs):
        self._update_value()
        super().set_value(value, **kwargs)
        if self._use_delayed_decay():
            self._update_value()
            self._time_of_last_value_change = services.time_service().sim_now
            self._delayed_decay_active = False
            self._start_delayed_decay_timer()

    def _get_minimum_decay_level(self):
        return self.min_value

    def on_remove(self, on_destroy=False):
        super().on_remove(on_destroy=on_destroy)
        self._destroy_alarm()
        self._active_callback = None

    def create_callback_listener(self, threshold, callback, on_callback_alarm_reset=None):
        self._update_value()
        callback_data = _ContinuousStatisticCallbackData(self, callback, threshold, on_callback_alarm_reset=on_callback_alarm_reset)
        return callback_data

    def add_callback_listener(self, callback_data:_ContinuousStatisticCallbackData, update_active_callback=True) -> type(None):
        super().add_callback_listener(callback_data)
        if update_active_callback and callback_data is self._callback_queue_head:
            self._update_active_callback()

    def remove_callback_listener(self, callback_listener:_ContinuousStatisticCallbackData):
        listener_removed = super().remove_callback_listener(callback_listener)
        if listener_removed and self._active_callback is callback_listener:
            self._update_active_callback()
        return listener_removed

    def _insert_callback_listener(self, callback_data:_ContinuousStatisticCallbackData):
        if self._tracker is not None and self._tracker.suppress_callback_alarm_calculation:
            self._statistic_callback_listeners.append(callback_data)
            return
        self._update_value()
        trigger_interval = self._calculate_minutes_until_value_is_reached_through_decay(callback_data.threshold.value, callback_data.threshold)
        callback_data.reset_trigger_time(trigger_interval)
        try:
            insertion_index = self._find_insertion_point(0, len(self._statistic_callback_listeners), callback_data)
        except Exception:
            if self.tracker and self.tracker.owner and self.tracker.owner.is_sim:
                self.tracker.owner.log_sim_info(logger.error, additional_msg='Failed to find insertion point for {}.'.format(self))
            else:
                logger.error('Failed to find insertion point for {}.', self)
            raise
        self._statistic_callback_listeners.insert(insertion_index, callback_data)

    def fixup_callbacks_during_load(self):
        pass

    @property
    def decay_enabled(self):
        return self._decay_enabled

    @decay_enabled.setter
    def decay_enabled(self, value):
        if self._decay_enabled != value:
            logger.debug('Setting decay for {} to {}', self, value)
            self._update_value()
            self._decay_enabled = value
            self._update_callback_listeners()
            if value:
                sleep_time_now = services.time_service().sim_now
                if self._last_update is None or self._last_update < sleep_time_now:
                    self._last_update = sleep_time_now

    def get_decay_rate(self, use_decay_modifier=True):
        if self._decay_enabled and self._get_change_rate_without_decay() == 0:
            start_value = self._value
            if use_decay_modifier:
                decay_rate = self.base_decay_rate*self._decay_rate_modifier
            else:
                decay_rate = self.base_decay_rate
            if start_value > self.convergence_value:
                decay_sign = -1
            elif start_value < self.convergence_value:
                decay_sign = 1
            else:
                decay_sign = 0
            return decay_rate*decay_sign
        else:
            return 0

    def has_decay_rate_modifier(self, value):
        return self._decay_rate_modifiers and value in self._decay_rate_modifiers

    def add_decay_rate_modifier(self, value):
        if value < 0:
            logger.error('Attempting to add negative decay rate modifier of {} to {}', value, self)
            return
        logger.debug('Adding decay rate modifier of {} to {}', value, self)
        self._update_value()
        if self._decay_rate_modifiers is None:
            self._decay_rate_modifiers = []
        self._decay_rate_modifiers.append(value)
        self._recalculate_modified_decay_rate()

    def remove_decay_rate_modifier(self, value):
        if self._decay_rate_modifiers is None:
            return
        if value in self._decay_rate_modifiers:
            logger.debug('Removing decay rate modifier of {} from {}', value, self)
            self._update_value()
            self._decay_rate_modifiers.remove(value)
            self._recalculate_modified_decay_rate()
        if not self._decay_rate_modifiers:
            self._decay_rate_modifiers = None

    def get_decay_rate_modifier(self):
        return self._decay_rate_modifier

    @property
    def convergence_value(self):
        return self._convergence_value

    @convergence_value.setter
    def convergence_value(self, value):
        self._update_value()
        self._convergence_value = value
        self._update_callback_listeners()

    def reset_convergence_value(self):
        self._update_value()
        self._convergence_value = self._default_convergence_value
        self._update_callback_listeners()

    def is_at_convergence(self):
        if self.get_value() == self.convergence_value:
            return True
        return False

    def get_decay_time(self, threshold, use_decay_modifier=True):
        self._update_value()
        return self._calculate_minutes_until_value_is_reached_through_decay(threshold.value, threshold, use_decay_modifier=use_decay_modifier)

    def get_change_rate(self):
        change_rate = self._get_change_rate_without_decay()
        if change_rate != 0:
            return change_rate
        return self.get_decay_rate()

    def get_change_rate_without_decay(self):
        return self._get_change_rate_without_decay()

    @property
    def base_decay_rate(self):
        if self._decay_rate_override is not UNSET:
            return self._decay_rate_override
        if self._delayed_decay_active and self._use_delayed_decay():
            if self._delayed_decay_rate_override is not UNSET:
                return self._delayed_decay_rate_override
            return self.delayed_decay_rate.delayed_decay_rate
        return self.decay_rate

    def _get_change_rate_without_decay(self):
        if self._statistic_modifier > 0:
            return self._statistic_modifier*self._statistic_multiplier_increase
        else:
            return self._statistic_modifier*self._statistic_multiplier_decrease

    def _update_value(self, minimum_decay_value=DEFAULT):
        tracker = self._tracker
        if tracker is not None and tracker.load_in_progress:
            return 0
        now = services.time_service().sim_now
        delta_time = now - self._last_update
        if delta_time <= date_and_time.TimeSpan.ZERO:
            return 0
        self._last_update = now
        local_time_delta = delta_time.in_minutes()
        start_value = self._value
        change_rate = self._get_change_rate_without_decay()
        decay_rate = self.get_decay_rate()
        new_value = None
        if change_rate == 0 and decay_rate != 0:
            time_to_convergence = self._calculate_minutes_until_value_is_reached_through_decay(self.convergence_value)
            if local_time_delta > time_to_convergence:
                new_value = self.convergence_value
            delta_rate = decay_rate
        else:
            if self._use_delayed_decay():
                self._time_of_last_value_change = now
            delta_rate = change_rate
        if new_value is None:
            new_value = start_value + local_time_delta*delta_rate
        if minimum_decay_value is not DEFAULT:
            new_value = max(new_value, minimum_decay_value)
        if new_value != self._value and tracker is not None:
            tracker.notify_delta(self.stat_type, new_value - self._value)
        self._value = new_value
        self._clamp()
        return local_time_delta

    @contextlib.contextmanager
    def _suppress_update_active_callbacks_context_manager(self):
        if self._suppress_update_active_callbacks:
            yield None
        else:
            self._suppress_update_active_callbacks = True
            try:
                yield None
            finally:
                self._suppress_update_active_callbacks = False

    def _update_callback_listeners(self, old_value=0, new_value=0, resort_list=True):
        if not self._statistic_callback_listeners:
            return
        if self._tracker is not None and self._tracker.suppress_callback_alarm_calculation:
            return
        self._update_value()
        callback_tuple = None
        if old_value <= new_value:
            callback_tuple = tuple(self._statistic_callback_listeners)
        else:
            callback_tuple = tuple(reversed(self._statistic_callback_listeners))
        for callback_data in callback_tuple:
            if old_value != new_value and callback_data.check_for_threshold(old_value, new_value):
                callback_data.trigger_callback()
            if not self._tracker is None:
                if not self._tracker.suppress_callback_setup_during_load:
                    trigger_interval = self._calculate_minutes_until_value_is_reached_through_decay(callback_data.threshold.value, callback_data.threshold)
                    callback_data.reset_trigger_time(trigger_interval)
            trigger_interval = self._calculate_minutes_until_value_is_reached_through_decay(callback_data.threshold.value, callback_data.threshold)
            callback_data.reset_trigger_time(trigger_interval)
        if resort_list:
            self._statistic_callback_listeners.sort()
        self._update_active_callback()

    def _update_active_callback(self):
        if self._suppress_update_active_callbacks:
            return
        if self._tracker is not None and self._tracker.suppress_callback_alarm_calculation:
            return
        if not self._statistic_callback_listeners:
            if self._active_callback is not None or self._alarm_handle:
                logger.debug('_callback list is empty; destroying alarm & active callback.  Last active callback was {}', self._active_callback)
                self._destroy_alarm()
                self._active_callback = None
            return
        self._destroy_alarm()
        while self._statistic_callback_listeners:
            callback_data = self._callback_queue_head
            next_trigger_time = callback_data.calculate_next_trigger_time()
            if next_trigger_time is None:
                self._active_callback = None
                break
            if next_trigger_time.in_ticks() <= 0:
                self._trigger_callback(callback_data)
                self._update_active_callback()
            else:
                if self._alarm_handle:
                    self._destroy_alarm()
                logger.debug('Creating alarm for callback: {}', callback_data)
                self._alarm_handle = alarms.add_alarm(self, next_trigger_time, self._alarm_callback)
                self._active_callback = callback_data
                break

    def _destroy_alarm(self):
        if self._alarm_handle is not None:
            alarms.cancel_alarm(self._alarm_handle)
            self._alarm_handle = None

    def _alarm_callback(self, handle):
        self._alarm_handle = None
        callbacks_to_call = [callback for callback in self._statistic_callback_listeners if self._active_callback.will_be_called_at_the_same_time_as(callback)]
        with self._suppress_update_active_callbacks_context_manager():
            for callback in callbacks_to_call:
                self._trigger_callback(callback)
        self._update_active_callback()

    def _trigger_callback(self, callback):
        if callback is None:
            logger.error('Attempting to trigger a None callback.')
            self._update_active_callback()
            return
        callback.trigger_callback()
        if self.remove_callback_listener(callback):
            self.add_callback_listener(callback, update_active_callback=False)

    def _find_insertion_point(self, start, end, callback_data):
        if start == end:
            return start
        index = int((start + end)/2)
        if index == len(self._statistic_callback_listeners):
            return index
        if callback_data > self._statistic_callback_listeners[index]:
            return self._find_insertion_point(index + 1, end, callback_data)
        elif index == 0 or callback_data < self._statistic_callback_listeners[index] and callback_data < self._statistic_callback_listeners[index - 1]:
            return self._find_insertion_point(start, end - 1, callback_data)
        else:
            return index
        return index

    def _find_nearest_threshold(self, interval, comparison):
        num_intervals = (self.get_value() - self.min_value)/interval
        if comparison is operator.ge or comparison is operator.gt:
            next_interval = math.floor(num_intervals) + 1
        else:
            next_interval = math.ceil(num_intervals) - 1
        threshold = next_interval*interval + self.min_value
        if threshold >= self.min_value and threshold <= self.max_value:
            return threshold

    def _calculate_minutes_until_value_is_reached_through_decay(self, target_value, threshold=None, use_decay_modifier=True):
        if threshold is not None:
            if threshold.comparison is operator.gt:
                target_value = target_value + sims4.math.EPSILON
            elif threshold.comparison is operator.lt:
                target_value = target_value - sims4.math.EPSILON
        current_value = self._value
        if threshold is not None and threshold.compare(current_value):
            return 0
        if current_value == target_value:
            return 0
        if target_value < self._get_minimum_decay_level() and self._get_minimum_decay_level() <= current_value:
            return
        else:
            change_rate = self._get_change_rate_without_decay()
            if change_rate != 0:
                if change_rate > 0 and target_value > current_value or change_rate < 0 and target_value < current_value:
                    result = (target_value - current_value)/change_rate
                    return abs(result)
                return
        return
        decay_rate = self.get_decay_rate(use_decay_modifier=use_decay_modifier)
        if decay_rate != 0:
            if decay_rate < 0 and target_value > current_value or decay_rate > 0 and target_value < current_value:
                return
            if not (current_value < self.convergence_value and self.convergence_value < target_value):
                if current_value > self.convergence_value and self.convergence_value > target_value:
                    return
                else:
                    result = (target_value - current_value)/decay_rate
                    return abs(result)
            else:
                return
            result = (target_value - current_value)/decay_rate
            return abs(result)

    def _recalculate_modified_decay_rate(self):
        old_decay_rate = self.get_decay_rate()
        self._decay_rate_modifier = 1
        if self._decay_rate_modifiers is not None:
            for val in self._decay_rate_modifiers:
                self._decay_rate_modifier *= val
        if self.tracker is not None:
            multiplier = self.get_skill_based_statistic_multiplier([self.tracker.owner], -1)
            self._decay_rate_modifier *= multiplier
        resort_callbacks = False
        if self.get_decay_rate() != 0:
            resort_callbacks = True
        self._update_callback_listeners(resort_list=resort_callbacks)

    def add_statistic_modifier(self, value):
        self._update_value()
        super().add_statistic_modifier(value)

    def remove_statistic_modifier(self, value):
        if self._statistic_modifiers is None:
            return
        if value in self._statistic_modifiers:
            self._update_value()
            super().remove_statistic_modifier(value)
            self._update_value()

    def _on_statistic_modifier_changed(self, notify_watcher=True):
        self._update_value()
        super()._on_statistic_modifier_changed(notify_watcher=notify_watcher)
        self._update_callback_listeners()

    @flexmethod
    def get_saved_value(cls, inst):
        cls_or_inst = inst if inst is not None else cls
        value = cls_or_inst.get_value()
        if inst is not None:
            owner = inst._tracker.owner
            if owner.inventoryitem_component.save_for_stack_compaction:
                value = round(value/cls.SAVE_VALUE_MULTIPLE)*cls.SAVE_VALUE_MULTIPLE
        return value

    def unlocks_skills_on_max(self):
        return False

    @classmethod
    def send_commodity_update_message(cls, sim_info, old_value, new_value):
        pass

    def can_decay(self):
        return True

    def on_lock(self, action_on_lock):
        self.decay_enabled = False
        if action_on_lock == StatisticLockAction.USE_MAX_VALUE_TUNING:
            self.set_value(self.max_value)
        elif action_on_lock == StatisticLockAction.USE_MIN_VALUE_TUNING:
            self.set_value(self.min_value)
        elif action_on_lock == StatisticLockAction.USE_BEST_VALUE_TUNING:
            self.set_value(self.best_value)
        self.send_commodity_progress_msg()

    def on_unlock(self, auto_satisfy=True):
        self.decay_enabled = True
        if self._use_delayed_decay():
            self._delayed_decay_active = False
            self._time_of_last_value_change = services.time_service().sim_now
            self._start_delayed_decay_timer()
        self.send_commodity_progress_msg()

    def needs_fixup_on_load(self):
        return False

    def needs_fixup_on_load_for_objects(self):
        return False

    def has_auto_satisfy_value(self):
        return False

    def _use_delayed_decay(self):
        if self.delayed_decay_rate is None:
            return False
        elif self.delayed_decay_rate.npc_decay or self.tracker.owner.is_npc:
            return False
        return True

    def _start_delayed_decay_timer(self):
        self.refresh_threshold_callback()
        if self._delayed_decay_timer is not None:
            alarms.cancel_alarm(self._delayed_decay_timer)
            self._delayed_decay_timer = None
        initial_delay = self._get_initial_delay()
        final_delay = self._get_final_delay()
        now = services.time_service().sim_now
        time_passed = 0
        if self._time_of_last_value_change is not None:
            time_passed = now - self._time_of_last_value_change
            time_passed = time_passed.in_minutes()
        if time_passed < initial_delay:
            length = date_and_time.create_time_span(minutes=initial_delay - time_passed)
            self._delayed_decay_timer = alarms.add_alarm(self, length, self._display_decay_warning)
        elif time_passed < initial_delay + final_delay:
            time_into_final_delay = time_passed - initial_delay
            length = date_and_time.create_time_span(minutes=final_delay - time_into_final_delay)
            self._delayed_decay_timer = alarms.add_alarm(self, length, self._start_delayed_decay)
        else:
            self._start_delayed_decay(None)

    def _get_initial_delay(self):
        if self._initial_delay_override is UNSET:
            return self.delayed_decay_rate.initial_delay
        return self._initial_delay_override

    def _get_final_delay(self):
        if self._final_delay_override is UNSET:
            return self.delayed_decay_rate.final_delay
        return self._final_delay_override

    def _display_decay_warning(self, timeline):
        if self.should_start_delayed_decay():
            if self.should_display_delayed_decay_warning():
                sim = self.tracker.owner
                resolver = SingleSimResolver(sim)
                notification = self.delayed_decay_rate.decay_warning(sim, resolver)
                notification.show_dialog()
            self._start_delayed_decay_timer()

    def _start_delayed_decay(self, timeline):
        self._update_value()
        if not self.tracker.owner.is_locked(self):
            self._delayed_decay_active = True
            self.decay_enabled = True
        self.refresh_threshold_callback()
        self._update_callback_listeners(resort_list=False)
        self.send_commodity_progress_msg()

    def should_start_delayed_decay(self):
        if self.is_at_convergence():
            return False
        elif self.tracker.owner.is_locked(self):
            return False
        return True

    def should_display_delayed_decay_warning(self):
        if self._decay_rate_modifier == 0 or self.delayed_decay_rate.decay_warning is None:
            return False
        return True

    def send_commodity_progress_msg(self, is_rate_change=True):
        pass

    def get_time_till_decay_starts(self):
        if self.delayed_decay_rate is None:
            return DelayedDecayStatus.NOT_TUNED
        if self._time_of_last_value_change is None or not (self.tracker.owner.is_npc and self.delayed_decay_rate.npc_decay):
            return DelayedDecayStatus.NOT_TRACKED
        now = services.time_service().sim_now
        time_passed = now - self._time_of_last_value_change
        initial_delay = date_and_time.create_time_span(minutes=self._get_initial_delay())
        final_delay = date_and_time.create_time_span(minutes=self._get_final_delay())
        time_remaining = initial_delay + final_delay - time_passed
        if time_remaining < date_and_time.create_time_span(minutes=0):
            return DelayedDecayStatus.ACTIVE
        return time_remaining.in_minutes()

    def refresh_threshold_callback(self):
        pass

    @classmethod
    def load_statistic_data(cls, tracker, data):
        tracker.set_value(cls, data.value, from_load=True)

    def load_time_of_last_value_change(self, data):
        if self.delayed_decay_rate is None:
            return
        if not data.time_of_last_value_change:
            return
        owner = self.tracker.owner
        if owner.is_sim and owner.is_npc and self.delayed_decay_rate.npc_decay:
            last_save_time = services.current_zone().time_of_last_save()
            timer_start_time = DateAndTime(data.time_of_last_value_change)
            difference = timer_start_time - last_save_time
            self._time_of_last_value_change = services.time_service().sim_now + difference
            self._start_delayed_decay_timer()
            return
        self._time_of_last_value_change = DateAndTime(data.time_of_last_value_change)
