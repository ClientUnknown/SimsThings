from routing.route_events.route_event_mixins import RouteEventDataBasefrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableRange
class RouteEventTypeEmpty(RouteEventDataBase, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'duration_override': TunableRange(description='\n            The duration we want this route event to have. This modifies\n            how much of the route time this event will take up.\n            ', tunable_type=float, default=0.1, minimum=0.1)}

    def prepare(self, actor):
        pass

    def execute(self, actor, **kwargs):
        pass

    def process(self, actor):
        pass
