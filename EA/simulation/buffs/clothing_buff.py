import operatorfrom autonomy.autonomy_modifier import AutonomyModifierfrom buffs.buff import Buff, NO_TIMEOUTfrom sims4.tuning.tunable import TunableSimMinuteimport sims4
class ClothingBuff(Buff):
    INSTANCE_TUNABLES = {'removal_minutes': TunableSimMinute(description='\n            Number of sim minutes till buff is removed.  This meant to be used\n            in conjunction with temporary commodity but if using a commodity\n            that already exist commodity convergence value must be minimum\n            value of commodity.\n            ', default=40)}

    @classmethod
    def can_add(cls, owner):
        if cls.commodity is None:
            return True
        tracker = owner.get_tracker(cls.commodity)
        value = tracker.get_value(cls.commodity)
        if value is None:
            return True
        elif value < cls.commodity.max_value:
            return True
        return False

    @classmethod
    def _create_temporary_commodity(cls, *args, **kwargs):
        super()._create_temporary_commodity(*args, create_buff_state=False, initial_value=1, **kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._commodity_callback = None
        self._autonomy_handle = None

    def _remove_buff_statistic_callback(self, stat_instance):
        if not self.handle_ids:
            return
        self._owner.remove_buff(self.handle_ids[0])
        stat_instance.decay_enabled = False

    def on_add(self, *args, **kwargs):
        super().on_add(*args, **kwargs)
        if self.commodity is None:
            return
        tracker = self._get_tracker()
        stat = tracker.add_statistic(self.commodity)
        threshold = sims4.math.Threshold(stat.max_value, operator.ge)
        self._commodity_callback = tracker.create_and_add_listener(self.commodity, threshold, self._remove_buff_statistic_callback)
        modification = (stat.max_value - stat.min_value)/self.removal_minutes
        auto_mod = AutonomyModifier(statistic_modifiers={self.commodity: modification})
        self._autonomy_handle = self._owner.add_statistic_modifier(auto_mod)

    def on_remove(self, *args, **kwargs):
        super().on_remove(*args, **kwargs)
        if self.commodity is None:
            return
        if self._commodity_callback is not None:
            tracker = self._get_tracker()
            tracker.remove_listener(self._commodity_callback)
            self._commodity_callback = None
        if self._autonomy_handle is not None:
            self._owner.remove_statistic_modifier(self._autonomy_handle)
            self._autonomy_handle = None

    def get_timeout_time(self):
        commodity_instance = self.get_commodity_instance()
        if commodity_instance is None:
            return NO_TIMEOUT
        threshold = sims4.math.Threshold(commodity_instance.max_value, operator.ge)
        return self._get_absolute_timeout_time(commodity_instance, threshold)
