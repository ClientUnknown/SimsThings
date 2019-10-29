import operatorfrom sims4.math import Thresholdimport sims4.loglogger = sims4.log.Logger('ProgressiveStatisticCallbackMixin', default_owner='rfleig')
class ProgressiveStatisticCallbackMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._callback_handle = None
        if self.tracker.owner.is_simulating:
            self.on_initial_startup()

    def on_initial_startup(self):
        super().on_initial_startup()
        if self.tracker.owner.is_selectable or self.process_non_selectable_sim:
            self.refresh_threshold_callback()

    def _destory_callback_handle(self):
        if self._callback_handle is not None:
            self.remove_callback_listener(self._callback_handle)
            self._callback_handle = None

    @staticmethod
    def _callback_handler(stat_inst):
        pass

    def refresh_threshold_callback(self):
        if self._decay_callback_handle is not None:
            self.remove_callback_listener(self._decay_callback_handle)
            self._decay_callback_handle = None
        if self.decay_enabled:
            self._decay_callback_handle = self.create_and_add_callback_listener(Threshold(self._get_previous_level_bound(), operator.lt), self._callback_handler)
        self._destory_callback_handle()
        self._callback_handle = self.create_and_add_callback_listener(Threshold(self._get_next_level_bound(), operator.ge), self._callback_handler)

    @classmethod
    def get_level_list(cls):
        return NotImplementedError

    @classmethod
    def _get_level_bounds(cls, level):
        level_list = cls.get_level_list()
        level_min = sum(level_list[:level])
        if level < cls.max_level:
            level_max = sum(level_list[:level + 1])
        else:
            level_max = sum(level_list)
        return (level_min, level_max)

    def _get_next_level_bound(self):
        level = self.convert_to_user_value(self._value)
        (_, level_max) = self._get_level_bounds(level)
        return level_max

    def _get_previous_level_bound(self):
        level = self.convert_to_user_value(self._value)
        (level_min, _) = self._get_level_bounds(level)
        return level_min

    @classmethod
    def get_max_skill_value(cls):
        level_list = cls.get_level_list()
        return sum(level_list)

    @classmethod
    def get_skill_value_for_level(cls, level):
        level_list = cls.get_level_list()
        if level > len(level_list):
            logger.error('Level {} out of bounds', level)
            return 0
        return sum(level_list[:level])

    @property
    def reached_max_level(self):
        max_value = self.get_max_skill_value()
        if self.get_value() >= max_value:
            return True
        return False

    @property
    def process_non_selectable_sim(self):
        return False

    @classmethod
    def _tuning_loaded_callback(cls):
        super()._tuning_loaded_callback()
        level_list = cls.get_level_list()
        cls.max_level = len(level_list)
