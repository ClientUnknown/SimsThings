from collections import defaultdictfrom objects.components import Component, componentmethod_with_fallbackfrom objects.components.types import WAITING_LINE_COMPONENTfrom sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.geometric import TunableWeightedUtilityCurveAndWeightimport sims4.loglogger = sims4.log.Logger('Waiting Line', default_owner='ayarger')
class WaitingLine:

    def __init__(self):
        self._line = []
        self._line_head_position = None
        self._line_head_angle = None
        self._line_cone = None
        self._line_head_los_constraint = None

    def _init_line(self, waiting_interaction):
        line_head_data = waiting_interaction.line_head_data
        self._line_head_position = line_head_data[0]
        self._line_head_angle = line_head_data[1]
        self._line_cone = line_head_data[2]
        self._line_head_los_constraint = line_head_data[3]

    def _join_line(self, waiting_interaction):
        if not self._line:
            self._init_line(waiting_interaction)
        self._line.append(waiting_interaction)

    def remove_from_line(self, waiting_interaction):
        if self.is_in_line(waiting_interaction):
            self._line.remove(waiting_interaction)

    def is_in_line(self, interaction):
        return interaction in self._line

    def is_sim_in_line(self, sim):
        return any(sim is interaction.sim for interaction in self._line)

    def is_first_in_line(self, waiting_interaction):
        if not self._line:
            return False
        return self._line[0] is waiting_interaction

    @property
    def first_interaction_in_line(self):
        if self._line:
            return self._line[0]

    @property
    def last_interaction_in_line(self):
        if self._line:
            return self._line[-1]

    def get_neighboring_interaction(self, waiting_interaction, *, offset):
        if waiting_interaction in self._line:
            neighbor_index = self._line.index(waiting_interaction) + offset
            if -1 < neighbor_index and neighbor_index < len(self._line):
                return self._line[neighbor_index]
            else:
                return

    def __len__(self):
        return len(self._line)

class WaitingLineComponent(Component, component_name=WAITING_LINE_COMPONENT, allow_dynamic=True):
    DEFAULT_AUTONOMOUS_WAITING_LINE_PREFERENCE_CURVE = TunableWeightedUtilityCurveAndWeight(description='\n                        A curve that maps the number of sims in a waiting line\n                        for this interaction to an autonomy score multiplier\n                        for this interaction.\n                        \n                        This curve is the default curve for any interaction\n                        that has not yet been tuned to have its own\n                        autonomous_waiting_line_prefence_curve.\n                        ')

    def __init__(self, owner):
        super().__init__(owner)
        self._lines = defaultdict(WaitingLine)

    def join_line(self, waiting_interaction):
        key = waiting_interaction.waiting_line_key
        self._lines[key]._join_line(waiting_interaction)
        return self._lines.get(key)

    def get_waiting_line(self, key):
        return self._lines.get(key)

    def notify_heads_of_lines(self, *args, sim=None):
        for line in self._lines.values():
            if len(line) > 0:
                line.first_interaction_in_line._push_adjustment_interaction()

    def remove_from_lines(self, waiting_interaction):
        key = waiting_interaction.waiting_line_key
        waiting_line = self._lines.get(key)
        if waiting_line is None:
            return
        waiting_line.remove_from_line(waiting_interaction)
        if len(waiting_line) < 1:
            self._lines.pop(key)

    def is_sim_in_line(self, sim):
        return any(line.is_sim_in_line(sim) for line in self._lines.values())

    @componentmethod_with_fallback(lambda _: 1)
    def get_waiting_line_autonomy_multiplier(self, interaction):
        key = interaction.waiting_line.waiting_line_key
        line_quantity_to_multiplier_curve = None
        if interaction.waiting_line.autonomous_waiting_line_prefence_curve is not None:
            line_quantity_to_multiplier_curve = interaction.waiting_line.autonomous_waiting_line_prefence_curve
        elif WaitingLineComponent.DEFAULT_AUTONOMOUS_WAITING_LINE_PREFERENCE_CURVE is not None:
            line_quantity_to_multiplier_curve = WaitingLineComponent.DEFAULT_AUTONOMOUS_WAITING_LINE_PREFERENCE_CURVE
        else:
            raise RuntimeError("WaitingLineComponent.DEFAULT_AUTONOMOUS_WAITING_LINE_PREFERENCE_CURVE has not been tuned! Waiting-Line autonomy integration won't work!")
        waiting_line = self._lines.get(key)
        if waiting_line is not None:
            length_of_line = len(waiting_line)
            return line_quantity_to_multiplier_curve.get(length_of_line)
        return 1
