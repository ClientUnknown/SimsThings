from sims.occult.occult_enums import OccultTypefrom sims.occult.occult_tracker import OccultTrackerfrom sims.occult.occult_tuning import OccultTuningfrom sims.sim_info_base_wrapper import SimInfoBaseWrapperfrom traits.trait_tracker import HasTraitTrackerMixinimport distributor
class SimInfoWithOccultTracker(HasTraitTrackerMixin, SimInfoBaseWrapper):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._occult_tracker = OccultTracker(self)
        self._base.occult_types = OccultType.HUMAN
        self._base.current_occult_types = OccultType.HUMAN
        self.desired_occult_rank = {}

    @property
    def occult_tracker(self):
        return self._occult_tracker

    @distributor.fields.Field(op=distributor.ops.SetOccultTypes)
    def occult_types(self):
        return OccultType(self._base.occult_types)

    @occult_types.setter
    def occult_types(self, value):
        if self._base.occult_types != value:
            self._base.occult_types = value

    @distributor.fields.Field(op=distributor.ops.SetCurrentOccultTypes)
    def current_occult_types(self):
        return OccultType(self._base.current_occult_types)

    @current_occult_types.setter
    def current_occult_types(self, value):
        if self._base.current_occult_types != value:
            self._base.current_occult_types = value

    def apply_age(self, age):
        return self._occult_tracker.apply_occult_age(age)

    def apply_genetics(self, parent_a, parent_b, seed, **kwargs):
        return self._occult_tracker.apply_occult_genetics(parent_a, parent_b, seed=seed, **kwargs)

    def add_trait(self, trait, **kwargs):
        success = super().add_trait(trait, **kwargs)
        if success:
            for (occult_type, trait_data) in OccultTracker.OCCULT_DATA.items():
                if trait_data.occult_trait is trait:
                    self._occult_tracker.add_occult_type(occult_type)
                    if self.is_baby and trait_data.add_current_occult_trait_to_babies:
                        self.add_trait(trait_data.current_occult_trait)
                if trait_data.current_occult_trait is trait:
                    self._occult_tracker.switch_to_occult_type(occult_type)
        self.trait_tracker.update_trait_effects()
        if self.occult_tracker.has_any_occult_or_part_occult_trait():
            self.remove_trait(OccultTuning.NO_OCCULT_TRAIT)
        return success

    def on_add_ranked_statistic(self):
        self._set_desired_initial_occult_rank_from_occult_rank_filter()

    def _set_desired_initial_occult_rank_from_occult_rank_filter(self):
        if len(self.desired_occult_rank) > 0:
            deleted_keys = []
            for (key, rank_value) in self.desired_occult_rank.items():
                occult_data = self.occult_tracker.OCCULT_DATA.get(key, None)
                xpranked_stat = occult_data.experience_statistic
                stat = self.commodity_tracker.get_statistic(xpranked_stat)
                if stat is not None:
                    points_needed = stat.points_to_rank(rank_value)
                    self.commodity_tracker.set_value(stat.stat_type, points_needed)
                    deleted_keys.append(key)
            for key in deleted_keys:
                del self.desired_occult_rank[key]

    def remove_trait(self, trait, **kwargs):
        success = super().remove_trait(trait, **kwargs)
        if success:
            for (occult_type, trait_data) in OccultTracker.OCCULT_DATA.items():
                if trait_data.occult_trait is trait:
                    self._occult_tracker.remove_occult_type(occult_type)
                if trait_data.current_occult_trait is trait:
                    self._occult_tracker.switch_to_occult_type(OccultType.HUMAN)
            if not self.occult_tracker.has_any_occult_or_part_occult_trait():
                self.add_trait(OccultTuning.NO_OCCULT_TRAIT)
        self.trait_tracker.update_trait_effects()
        return success

    def on_all_traits_loaded(self):
        super().on_all_traits_loaded()
        self._occult_tracker.on_all_traits_loaded()
        self._occult_tracker.post_load()
