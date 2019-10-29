from debugvis import Contextfrom sims4.color import pseudo_random_colorfrom visualization.constraint_visualizer import _draw_constraintimport servicesimport sims4.color
class BroadcasterVisualizer:

    def __init__(self, layer):
        self.layer = layer
        self._start()

    def _start(self):
        current_zone = services.current_zone()
        current_zone.broadcaster_service.register_callback(self._on_update)
        current_zone.broadcaster_real_time_service.register_callback(self._on_update)
        self._on_update()

    def stop(self):
        current_zone = services.current_zone()
        current_zone.broadcaster_service.unregister_callback(self._on_update)
        current_zone.broadcaster_real_time_service.unregister_callback(self._on_update)

    def _on_update(self):
        with Context(self.layer) as layer:
            self._on_update_real_time(layer)
            self._on_update_game_time(layer)

    def _on_update_game_time(self, layer):
        broadcaster_service = services.current_zone().broadcaster_service
        self._update_broadcaster_service_visualizer(broadcaster_service, layer)

    def _on_update_real_time(self, layer):
        broadcaster_service = services.current_zone().broadcaster_real_time_service
        self._update_broadcaster_service_visualizer(broadcaster_service, layer)

    def _update_broadcaster_service_visualizer(self, broadcaster_service, layer):
        for broadcaster in broadcaster_service.get_broadcasters_debug_gen():
            constraint = broadcaster.get_constraint()
            if constraint is not None:
                color = pseudo_random_color(broadcaster.guid)
                _draw_constraint(layer, constraint, color)
            broadcasting_object = broadcaster.broadcasting_object
            if broadcasting_object is not None:
                broadcaster_center = broadcasting_object.position
                layer.add_circle(broadcaster_center, radius=0.3, color=color)
            for linked_broadcaster in broadcaster.get_linked_broadcasters_gen():
                linked_broadcasting_object = linked_broadcaster.broadcasting_object
                if linked_broadcasting_object is not None:
                    layer.add_point(linked_broadcasting_object.position, size=0.25, color=color)
                    layer.add_segment(broadcaster_center, linked_broadcasting_object.position, color=color)
        for broadcaster in broadcaster_service.get_pending_broadcasters_gen():
            color = pseudo_random_color(broadcaster.guid)
            (r, g, b, a) = sims4.color.to_rgba(color)
            color = sims4.color.from_rgba(r, g, b, a*0.5)
            broadcasting_object = broadcaster.broadcasting_object
            if broadcasting_object is not None:
                layer.add_circle(broadcasting_object.position, color=color)
