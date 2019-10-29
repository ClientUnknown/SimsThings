from interactions import ParticipantTypefrom interactions.constraints import Circlefrom interactions.liability import Liabilityfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumEntry, Tunableimport placementimport servicesimport sims4.geometry
class RouteGoalSuppressionLiability(Liability, HasTunableFactory, AutoFactoryInit):
    LIABILITY_TOKEN = 'RouteGoalSuppressionLiability'
    FACTORY_TUNABLES = {'radius': Tunable(description='\n            The radius around the specified participant to penalize route\n            goals.\n            ', tunable_type=float, default=1, display_name='Radius'), 'participant': TunableEnumEntry(description='\n            The participant of the interaction that we will be used as the\n            center of the radius to penalize route goals.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'use_sim_intended_position': Tunable(description="\n            If enabled, the position to which the Sim is supposed to route will\n            get the penalty region around it. If disabled, the Sim's\n            position at the time the interaction starts will be used.\n            ", tunable_type=bool, default=True)}

    def __init__(self, interaction, **kwargs):
        super().__init__(**kwargs)
        self._quadtree_object_ids = []
        self._current_interaction = None
        self._participant = interaction.get_participant(self.participant)

    def should_transfer(self, continuation):
        return False

    def transfer(self, interaction):
        return super().transfer(interaction)

    def merge(self, interaction, key, new_liability):
        return super().merge(interaction, key, new_liability)

    def on_add(self, interaction):
        if self._participant is None:
            return
        self._current_interaction = interaction
        if self.use_sim_intended_position:
            self._participant.routing_component.on_intended_location_changed.append(self._intended_position_changed)

    def _intended_position_changed(self, *_, **__):
        self._add_region(self._participant.intended_position, self._participant.intended_routing_surface)

    def on_run(self):
        if self._participant is None:
            return
        if not self.use_sim_intended_position:
            self._add_region(self._participant.position, self._participant.routing_surface)

    def _add_region(self, position, routing_surface):
        self._quadtree_object_ids.append(self._current_interaction.id)
        circle = sims4.geometry.generate_circle_constraint(Circle.NUM_SIDES, position, self.radius)
        services.sim_quadtree().insert(self._current_interaction, self._current_interaction.id, placement.ItemType.ROUTE_GOAL_PENALIZER, circle, routing_surface, False, 0)

    def release(self):
        for interaction_id in self._quadtree_object_ids:
            services.sim_quadtree().remove(interaction_id, placement.ItemType.ROUTE_GOAL_PENALIZER, 0)
        if self._intended_position_changed in self._participant.routing_component.on_intended_location_changed:
            self._participant.routing_component.on_intended_location_changed.remove(self._intended_position_changed)
