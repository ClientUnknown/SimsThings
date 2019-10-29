from objects.mixins import AffordanceCacheMixin, ProvidedAffordanceDatafrom statistics.continuous_statistic_tracker import ContinuousStatisticTrackerfrom statistics.skill import Skillfrom statistics.statistic_enums import CommodityTrackerSimulationLevelimport servicesimport simsimport sims4.loglogger = sims4.log.Logger('Commodities')
class CommodityTracker(AffordanceCacheMixin, ContinuousStatisticTracker):
    __slots__ = ('simulation_level', 'load_in_progress', '_super_affordances_cache', '_target_provided_affordances_cache', '_actor_mixers_cache', '_provided_mixers_cache')

    def __init__(self, owner):
        super().__init__(owner)
        self.simulation_level = CommodityTrackerSimulationLevel.REGULAR_SIMULATION
        self.load_in_progress = False

    def add_statistic(self, stat_type, **kwargs):
        commodity = super().add_statistic(stat_type, **kwargs)
        if commodity is not None:
            self.owner.statistic_component.apply_statistic_modifiers_on_stat(commodity)
        return commodity

    def remove_listener(self, listener):
        stat_type = listener.statistic_type
        super().remove_listener(listener)
        self._cleanup_noncore_commodity(stat_type)

    def _cleanup_noncore_commodity(self, stat_type):
        commodity = self.get_statistic(stat_type)
        if commodity is not None and (commodity.core or commodity.remove_on_convergence and commodity.is_at_convergence()):
            self.remove_statistic(stat_type)

    def set_value(self, stat_type, value, from_load=False, from_init=False, **kwargs):
        super().set_value(stat_type, value, from_load=from_load, from_init=from_init, **kwargs)
        self._cleanup_noncore_commodity(stat_type)

    def add_value(self, stat_type, increment, **kwargs):
        super().add_value(stat_type, increment, **kwargs)
        self._cleanup_noncore_commodity(stat_type)

    def send_commodity_progress_update(self, from_add=False):
        for statistic in tuple(self._statistics_values_gen()):
            if not statistic.can_decay():
                pass
            else:
                statistic.create_and_send_commodity_update_msg(from_add=from_add)

    def on_initial_startup(self):
        for commodity in tuple(self._statistics_values_gen()):
            commodity.on_initial_startup()
        self.send_commodity_progress_update(from_add=True)

    def start_low_level_simulation(self):
        self.simulation_level = CommodityTrackerSimulationLevel.LOW_LEVEL_SIMULATION
        self.stop_regular_simulation()
        for commodity in tuple(self._statistics_values_gen()):
            commodity.start_low_level_simulation()
        self.send_commodity_progress_update(from_add=True)

    def stop_low_level_simulation(self):
        for commodity in tuple(self._statistics_values_gen()):
            commodity.stop_low_level_simulation()

    def start_regular_simulation(self):
        self.simulation_level = CommodityTrackerSimulationLevel.REGULAR_SIMULATION
        self.stop_low_level_simulation()
        self.on_initial_startup()
        self._owner.trait_tracker.sort_and_send_commodity_list()

    def stop_regular_simulation(self):
        for commodity in tuple(self._statistics_values_gen()):
            commodity.stop_regular_simulation()

    def on_zone_load(self):
        for commodity in self._statistics_values_gen():
            commodity.on_zone_load()

    def save(self):
        commodities = []
        skills = []
        ranked_statistics = []
        for stat in tuple(self._statistics_values_gen()):
            if not stat.persisted:
                pass
            else:
                try:
                    stat.save_statistic(commodities, skills, ranked_statistics, self)
                except Exception:
                    logger.error('Exception thrown while trying to save stat {}', stat)
        return (commodities, skills, ranked_statistics)

    def load(self, statistics, skip_load=False, update_affordance_cache=True):
        statistic_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
        try:
            self.load_in_progress = True
            owner_lod = self._owner.lod if isinstance(self._owner, sims.sim_info.SimInfo) else None
            for commodity_proto in statistics:
                commodity_class = statistic_manager.get(commodity_proto.name_hash)
                if commodity_class is None:
                    logger.info('Trying to load unavailable STATISTIC resource: {}', commodity_proto.name_hash, owner='rez')
                elif not commodity_class.persisted:
                    logger.info('Trying to load unavailable STATISTIC resource: {}', commodity_proto.name_hash, owner='rez')
                elif self.statistics_to_skip_load is not None and commodity_class in self.statistics_to_skip_load:
                    pass
                elif commodity_class.is_skill and commodity_proto.value == commodity_class.initial_value:
                    pass
                elif skip_load and commodity_class.remove_on_convergence:
                    logger.info('Not loading {} because load is not required.', commodity_class, owner='rez')
                elif not self._should_add_commodity_from_gallery(commodity_class, skip_load):
                    pass
                elif owner_lod is not None and owner_lod < commodity_class.min_lod_value:
                    pass
                else:
                    commodity_class.load_statistic_data(self, commodity_proto)
        finally:
            self.statistics_to_skip_load = None
            self.load_in_progress = False
        if update_affordance_cache:
            self.update_affordance_caches()

    def get_sim(self):
        return self._owner.get_sim_instance()

    def update_all_commodities(self):
        commodities_to_update = tuple(self._statistics_values_gen())
        for commodity in commodities_to_update:
            commodity._update_value()

    def get_all_commodities(self):
        if self._statistics:
            return tuple(self._statistics.values())
        return ()

    def get_provided_super_affordances(self):
        affordances = set()
        target_affordances = list()
        for commodity in self._statistics_values_gen():
            if not commodity.is_skill:
                pass
            else:
                (skill_affordances, skill_target_affordances) = commodity.get_skill_provided_affordances()
                affordances.update(skill_affordances)
                for provided_affordance in skill_target_affordances:
                    provided_affordance_data = ProvidedAffordanceData(provided_affordance.affordance, provided_affordance.object_filter, provided_affordance.allow_self)
                    target_affordances.append(provided_affordance_data)
        return (affordances, target_affordances)

    def get_actor_and_provided_mixers_list(self):
        actor_mixers = []
        for commodity in self._statistics_values_gen():
            if commodity.is_skill:
                skill_provided_actor_mixers = commodity.get_skill_provided_actor_mixers()
                if skill_provided_actor_mixers is not None:
                    actor_mixers.append(skill_provided_actor_mixers)
        return (actor_mixers, ())

    def get_sim_info_from_provider(self):
        return self.owner
