from sims.sim_info_tracker import SimInfoTrackerfrom singletons import DEFAULTfrom statistics.base_statistic import GalleryLoadBehaviorfrom statistics.base_statistic_listener import BaseStatisticCallbackListenerimport servicesimport simsimport sims4.callback_utilsimport sims4.logimport uidlogger = sims4.log.Logger('Statistic')with sims4.reload.protected(globals()):
    _handle_id_gen = uid.UniqueIdGenerator(1)
class BaseStatisticTracker(SimInfoTracker):
    __slots__ = ('_statistics', '_owner', '_watchers', '_delta_watchers', '_on_remove_callbacks', 'suppress_callback_setup_during_load', 'statistics_to_skip_load', 'suppress_callback_alarm_calculation')

    def __init__(self, owner=None):
        self._statistics = None
        self._owner = owner
        self._watchers = {}
        self._delta_watchers = {}
        self._on_remove_callbacks = None
        self.suppress_callback_setup_during_load = False
        self.suppress_callback_alarm_calculation = False
        self.statistics_to_skip_load = None

    def __iter__(self):
        if self._statistics is not None:
            return self._statistics.values().__iter__()
        return iter([])

    def __len__(self):
        if self._statistics is not None:
            return len(self._statistics)
        return 0

    @property
    def owner(self):
        return self._owner

    def set_callback_alarm_calculation_supression(self, value):
        self.suppress_callback_alarm_calculation = value
        if self._statistics:
            for stat in self._statistics.values():
                stat._update_callback_listeners()

    def _statistics_values_gen(self):
        if self._statistics:
            for stat in self._statistics.values():
                yield stat

    def destroy(self):
        for stat in list(self):
            stat.on_remove(on_destroy=True)
        self._watchers.clear()
        self._on_remove_callbacks = None

    def on_initial_startup(self):
        pass

    def remove_statistics_on_travel(self):
        for statistic in tuple(self._statistics_values_gen()):
            if not statistic.persisted:
                stat_type = statistic.stat_type
                if not self.owner is None:
                    if not self.owner.is_statistic_type_added_by_modifier(stat_type):
                        self.remove_statistic(stat_type)
                self.remove_statistic(stat_type)

    def create_and_add_listener(self, stat_type, threshold, callback, on_callback_alarm_reset=None) -> BaseStatisticCallbackListener:
        if stat_type.added_by_default():
            add = stat_type.add_if_not_in_tracker
        else:
            add = False
        stat = self.get_statistic(stat_type, add=add)
        if stat is not None:
            callback_listener = stat.create_and_add_callback_listener(threshold, callback, on_callback_alarm_reset=on_callback_alarm_reset)
            return callback_listener

    def remove_listener(self, listener:BaseStatisticCallbackListener):
        stat = self.get_statistic(listener.statistic_type)
        if stat is not None:
            stat.remove_callback_listener(listener)

    def add_watcher(self, callback):
        handle_id = _handle_id_gen()
        self._watchers[handle_id] = callback
        return handle_id

    def has_watcher(self, handle):
        return handle in self._watchers

    def remove_watcher(self, handle):
        del self._watchers[handle]

    def notify_watchers(self, stat_type, old_value, new_value):
        for watcher in list(self._watchers.values()):
            watcher(stat_type, old_value, new_value)

    def add_delta_watcher(self, callback):
        handle_id = _handle_id_gen()
        self._delta_watchers[handle_id] = callback
        return handle_id

    def has_delta_watcher(self, handle):
        return handle in self._delta_watchers

    def remove_delta_watcher(self, handle):
        del self._delta_watchers[handle]

    def notify_delta(self, stat_type, delta):
        for watcher in tuple(self._delta_watchers.values()):
            watcher(stat_type, delta)

    def add_on_remove_callback(self, callback):
        if self._on_remove_callbacks is None:
            self._on_remove_callbacks = sims4.callback_utils.RemovableCallableList()
        self._on_remove_callbacks.append(callback)

    def remove_on_remove_callback(self, callback):
        if self._on_remove_callbacks is not None:
            if callback in self._on_remove_callbacks:
                self._on_remove_callbacks.remove(callback)
            if not self._on_remove_callbacks:
                self._on_remove_callbacks = None

    def add_statistic(self, stat_type, owner=None, **kwargs):
        if self._statistics:
            stat = self._statistics.get(stat_type)
        else:
            stat = None
        if owner is None:
            owner = self._owner
        is_sim = owner.is_sim if owner is not None else False
        if is_sim and stat_type in owner.get_blacklisted_statistics():
            logger.error('Attempting to add stat {} when it is blacklisted on sim {}.', stat_type, self.owner)
            return
        owner_lod = owner.lod if is_sim else None
        if owner_lod is not None and owner_lod < stat_type.min_lod_value:
            return
        if stat is None and stat_type.can_add(owner, **kwargs):
            stat = stat_type(self)
            if self._statistics is None:
                self._statistics = {}
            self._statistics[stat_type] = stat
            stat.on_add()
            value = stat.get_value()
            if self._watchers:
                self.notify_watchers(stat_type, value, value)
        return stat

    def remove_statistic(self, stat_type, on_destroy=False):
        if self.has_statistic(stat_type):
            stat = self._statistics[stat_type]
            del self._statistics[stat_type]
            if self._on_remove_callbacks:
                self._on_remove_callbacks(stat)
            stat.on_remove(on_destroy=on_destroy)

    def get_statistic(self, stat_type, add=False):
        if self._statistics:
            stat = self._statistics.get(stat_type)
        else:
            stat = None
        if add:
            stat = self.add_statistic(stat_type)
        return stat

    def has_statistic(self, stat_type):
        if self._statistics is None:
            return False
        return stat_type in self._statistics

    def get_communicable_statistic_set(self):
        if self._statistics is None:
            return set()
        return {stat_type for stat_type in self._statistics if stat_type.communicable_by_interaction_tag is not None}

    def get_value(self, stat_type, add=False):
        stat = self.get_statistic(stat_type, add=add)
        if stat is not None:
            return stat.get_value()
        else:
            return stat_type.default_value

    def get_int_value(self, stat_type, scale:int=None):
        value = self.get_value(stat_type)
        if scale is not None:
            value = scale*value/stat_type.max_value
        return int(sims4.math.floor(value))

    def get_user_value(self, stat_type):
        stat_or_stat_type = self.get_statistic(stat_type) or stat_type
        return stat_or_stat_type.get_user_value()

    def set_value(self, stat_type, value, add=DEFAULT, from_load=False, from_init=False, **kwargs):
        if add is DEFAULT:
            add = from_load or stat_type.add_if_not_in_tracker
        if not stat_type.added_by_default():
            add = False
        stat = self.get_statistic(stat_type, add=add)
        if from_init and add and stat is not None:
            stat.set_value(value, from_load=from_load)

    def set_user_value(self, stat_type, user_value):
        stat = self.get_statistic(stat_type, add=True)
        stat.set_user_value(user_value)

    def add_value(self, stat_type, amount, **kwargs):
        if amount == 0:
            logger.warn('Attempting to add 0 to stat {}', stat_type)
            return
        stat = self.get_statistic(stat_type, add=stat_type.add_if_not_in_tracker)
        if stat is not None:
            stat.add_value(amount, **kwargs)

    def set_max(self, stat_type):
        stat = self.get_statistic(stat_type, add=stat_type.add_if_not_in_tracker)
        if stat is not None:
            self.set_value(stat_type, stat.max_value)

    def set_min(self, stat_type):
        stat = self.get_statistic(stat_type, add=stat_type.add_if_not_in_tracker)
        if stat is not None:
            self.set_value(stat_type, stat.min_value)

    def get_decay_time(self, stat_type, threshold):
        pass

    def set_convergence(self, stat_type, convergence):
        raise TypeError("This stat type doesn't have a convergence value.")

    def reset_convergence(self, stat_type):
        raise TypeError("This stat type doesn't have a convergence value.")

    def set_all_commodities_to_best_value(self, visible_only=False, core_only=False):
        for stat_type in list(self._statistics):
            stat = self.get_statistic(stat_type)
            if not stat.is_visible:
                if core_only and stat.core:
                    self.set_value(stat_type, stat_type.best_value)
            self.set_value(stat_type, stat_type.best_value)

    def save(self):
        save_list = []
        if self._statistics:
            for stat in self._statistics.values():
                if stat.persisted:
                    value = stat.get_saved_value()
                    save_data = (type(stat).__name__, value)
                    save_list.append(save_data)
        return save_list

    def _should_add_commodity_from_gallery(self, statistic_type, skip_load):
        if statistic_type.gallery_load_behavior == GalleryLoadBehavior.LOAD_FOR_ALL:
            return True
        if self.owner.is_sim:
            if skip_load and statistic_type.gallery_load_behavior != GalleryLoadBehavior.LOAD_ONLY_FOR_SIM:
                return False
        elif self.owner.is_downloaded and statistic_type.gallery_load_behavior != GalleryLoadBehavior.LOAD_ONLY_FOR_OBJECT:
            return False
        return True

    def load(self, load_list):
        try:
            for (stat_type_name, value) in load_list:
                stat_cls = services.get_instance_manager(sims4.resources.Types.STATISTIC).get(stat_type_name)
                if stat_cls is not None and self._sim_info.lod >= stat_cls.min_lod_value:
                    if stat_cls.persisted:
                        self.set_value(stat_cls, value)
                    else:
                        logger.info('Trying to load unavailable STATISTIC resource: {}', stat_type_name)
        except ValueError:
            logger.error('Attempting to load old data in BaseStatisticTracker.load()')

    def debug_output_all(self, _connection):
        if self._statistics:
            for stat in self._statistics.values():
                sims4.commands.output('{:<24} Value: {:-6.2f}'.format(stat.__class__.__name__, stat.get_value()), _connection)

    def debug_set_all_to_max_except(self, stat_to_exclude, core=True):
        for stat_type in list(self._statistics):
            if core:
                pass
            if stat_type != stat_to_exclude:
                self.set_value(stat_type, stat_type.max_value)

    def debug_set_all_to_min(self, core=True):
        for stat_type in list(self._statistics):
            if core:
                if self.get_statistic(stat_type).core:
                    self.set_value(stat_type, stat_type.min_value)
            self.set_value(stat_type, stat_type.min_value)

    def debug_set_all_to_default(self, core=True):
        for stat_type in list(self._statistics):
            if core:
                if self.get_statistic(stat_type).core:
                    self.set_value(stat_type, stat_type.initial_value)
            self.set_value(stat_type, stat_type.initial_value)

    def on_lod_update(self, old_lod, new_lod):
        if self._statistics is None or self._owner is None:
            return
        if not isinstance(self._owner, sims.sim_info.SimInfo):
            raise NotImplementedError('LOD is updating from {} to {} on an non-sim object. This is not supported.'.format(old_lod, new_lod))
        for stat_type in tuple(self._statistics):
            stat_to_test = self.get_statistic(stat_type)
            if stat_to_test is not None and stat_to_test.min_lod_value > new_lod:
                self.remove_statistic(stat_type)
