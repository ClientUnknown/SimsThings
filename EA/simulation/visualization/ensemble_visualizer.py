import mathfrom debugvis import Contextfrom sims4.color import pseudo_random_colorimport services
class EnsembleVisualizer:

    def __init__(self, layer):
        self.layer = layer
        self._start()

    def _start(self):
        services.ensemble_service().on_ensemble_center_of_mass_changed.append(self._on_update)
        self._on_update()

    def stop(self):
        services.ensemble_service().on_ensemble_center_of_mass_changed.remove(self._on_update)

    def _on_update(self):
        with Context(self.layer) as layer:
            for ensemble in services.ensemble_service().get_all_ensembles():
                color = pseudo_random_color(ensemble.guid)
                if ensemble.last_center_of_mass is None:
                    pass
                else:
                    layer.add_circle(ensemble.last_center_of_mass, radius=math.sqrt(ensemble.max_ensemble_radius), color=color)
                    for sim in ensemble:
                        layer.add_circle(sim.position, radius=0.3, color=color)
