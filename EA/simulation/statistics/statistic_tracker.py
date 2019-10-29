from protocolbuffers import SimObjectAttributes_pb2 as protocolsimport servicesimport simsimport sims4.logimport statistics.base_statistic_trackerlogger = sims4.log.Logger('Statistic')
class StatisticTracker(statistics.base_statistic_tracker.BaseStatisticTracker):
    __slots__ = '_monetary_value_statistics'

    def __init__(self, owner=None):
        super().__init__(owner)
        self._monetary_value_statistics = []

    def save(self):
        save_list = []
        for stat in self._statistics_values_gen():
            if stat.persisted:
                try:
                    statistic_data = protocols.Statistic()
                    statistic_data.name_hash = stat.guid64
                    statistic_data.value = stat.get_saved_value()
                    save_list.append(statistic_data)
                except Exception:
                    logger.exception('Exception thrown while trying to save stat {}', stat, owner='rez')
        return save_list

    def load(self, statistics, skip_load=False):
        try:
            statistics_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
            owner_lod = self._owner.lod if isinstance(self._owner, sims.sim_info.SimInfo) else None
            for statistics_data in statistics:
                stat_cls = statistics_manager.get(statistics_data.name_hash)
                if stat_cls is not None:
                    if not self._should_add_commodity_from_gallery(stat_cls, skip_load):
                        pass
                    elif not stat_cls.persisted:
                        pass
                    elif self.statistics_to_skip_load is not None and stat_cls in self.statistics_to_skip_load:
                        pass
                    elif owner_lod is not None and owner_lod < stat_cls.min_lod_value:
                        pass
                    else:
                        self.set_value(stat_cls, statistics_data.value, from_load=True)
                        logger.info('Trying to load unavailable STATISTIC resource: {}', statistics_data.name_hash)
                else:
                    logger.info('Trying to load unavailable STATISTIC resource: {}', statistics_data.name_hash)
        finally:
            self.statistics_to_skip_load = None

    def add_statistic(self, stat_type, **kwargs):
        stat = super().add_statistic(stat_type, **kwargs)
        if stat is not None and stat.apply_value_to_object_cost and stat not in self._monetary_value_statistics:
            self._monetary_value_statistics.append(stat)
        return stat

    def remove_statistic(self, stat_type, on_destroy=False):
        if self.has_statistic(stat_type):
            stat = self._statistics[stat_type]
            if stat.apply_value_to_object_cost and stat in self._monetary_value_statistics:
                self._monetary_value_statistics.remove(stat)
        super().remove_statistic(stat_type, on_destroy)

    def get_monetary_value_statistics(self):
        return self._monetary_value_statistics
