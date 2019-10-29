from debugvis import Contextfrom sims4.color import from_rgba, pseudo_random_colorfrom visualization.constraint_visualizer import _draw_constraint
class ShortestTransitionPathVisualizer:

    def __init__(self, layer):
        self.layer = layer
        self._start()

    def _start(self):
        import postures.posture_graph
        postures.posture_graph.on_transition_destinations_changed.append(self._on_transition_destinations_changed)

    def stop(self):
        import postures.posture_graph
        postures.posture_graph.on_transition_destinations_changed.remove(self._on_transition_destinations_changed)

    def _on_transition_destinations_changed(self, sim, transition_destinations, transition_sources, max_cost, preserve=False):
        POSSIBLE_SOURCE = from_rgba(50, 50, 50, 0.5)
        with Context(self.layer, preserve=preserve) as layer:
            for (path_id, constraint, weight) in transition_destinations:
                alpha = 1.0
                if max_cost > 0:
                    alpha = alpha - weight/max_cost
                    if alpha < 0.01:
                        alpha = 0.01
                color = pseudo_random_color(path_id, a=alpha)
                if constraint.was_selected:
                    _draw_constraint(layer, constraint, color, altitude_modifier=0.5)
                else:
                    _draw_constraint(layer, constraint, color)
            for constraint in transition_sources:
                if constraint.was_selected:
                    _draw_constraint(layer, constraint, POSSIBLE_SOURCE, altitude_modifier=0.5)
                else:
                    _draw_constraint(layer, constraint, POSSIBLE_SOURCE)

class SimShortestTransitionPathVisualizer(ShortestTransitionPathVisualizer):

    def __init__(self, sim, layer):
        self.sim = sim
        super().__init__(layer)

    def _on_transition_destinations_changed(self, sim, *args, **kwargs):
        if self.sim is not None and sim is not self.sim:
            return
        super()._on_transition_destinations_changed(sim, *args, **kwargs)
