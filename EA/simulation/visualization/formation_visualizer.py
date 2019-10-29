from debugvis import Contextfrom interactions.constraints import ANYWHEREfrom routing.formation.formation_type_follow import RoutingFormationFollowTypefrom routing.route_enums import RoutingStageEventfrom sims4.color import pseudo_random_colorfrom visualization.constraint_visualizer import _draw_constraintimport sims4.color
class RoutingFormationVisualizer:

    def __init__(self, sim, layer):
        self._sim = sim.ref()
        self.layer = layer
        self._start()

    @property
    def sim(self):
        if self._sim is not None:
            return self._sim()

    def _start(self):
        self.sim.register_on_location_changed(self._on_position_changed)
        self.sim.routing_component.on_follow_path.append(self._on_intended_position_changed)
        self.sim.routing_component.register_routing_stage_event(RoutingStageEvent.ROUTE_START, self._on_intended_position_changed)
        self.sim.routing_component.register_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_intended_position_changed)
        self._update()

    def stop(self):
        if self._on_intended_position_changed in self.sim.routing_component.on_follow_path:
            self.sim.routing_component.on_follow_path.remove(self._on_intended_position_changed)
        self.sim.routing_component.unregister_routing_stage_event(RoutingStageEvent.ROUTE_START, self._on_intended_position_changed)
        self.sim.routing_component.unregister_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_intended_position_changed)
        self.sim.unregister_on_location_changed(self._on_position_changed)

    def _on_intended_position_changed(self, *_, **__):
        self._update()

    def _on_position_changed(self, *_, **__):
        self._update()

    def _update(self):
        with Context(self.layer) as layer:
            for routing_formation in self.sim.get_all_routing_slave_data_gen():
                self._update_routing_formation_visualizer(routing_formation, self.sim.transform, layer)

    def _update_routing_formation_visualizer(self, routing_formation, transform, layer):
        layer.add_circle(transform.translation, radius=0.3, color=sims4.color.Color.GREEN)
        layer.add_circle(routing_formation.slave.position, radius=0.3, color=sims4.color.Color.RED)
        constraint = routing_formation.get_routing_slave_constraint()
        if constraint is not None or constraint is not ANYWHERE:
            color = pseudo_random_color(routing_formation.guid)
            _draw_constraint(layer, constraint, color)
        offset = sims4.math.Vector3.ZERO()
        previous_offset = sims4.math.Vector3.ZERO()
        for attachment_info in routing_formation.attachment_info_gen():
            color = sims4.color.Color.CYAN if attachment_info.node_type is RoutingFormationFollowType.NODE_TYPE_FOLLOW_LEADER else sims4.color.Color.MAGENTA
            offset.x = offset.x + attachment_info.parent_offset.x
            offset.z = offset.z + attachment_info.parent_offset.y
            layer.add_segment(transform.transform_point(previous_offset), transform.transform_point(offset), color=color, routing_surface=routing_formation.slave.routing_surface)
            previous_offset = sims4.math.Vector3.ZERO() + offset
            offset.x = offset.x - attachment_info.offset.x
            offset.z = offset.z - attachment_info.offset.y
            transformed_point = transform.transform_point(offset)
            layer.add_segment(transform.transform_point(previous_offset), transformed_point, color=color, routing_surface=routing_formation.slave.routing_surface)
            previous_offset = sims4.math.Vector3.ZERO() + offset
            layer.add_circle(transformed_point, radius=attachment_info.radius, color=color, routing_surface=routing_formation.slave.routing_surface)
