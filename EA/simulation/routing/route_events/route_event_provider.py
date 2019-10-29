from element_utils import build_critical_section_with_finallyfrom elements import ParentElementfrom event_testing.resolver import SingleObjectResolver, SingleSimResolverfrom interactions import ParticipantTypefrom routing.route_enums import RouteEventTypefrom routing.route_events.route_event import RouteEventfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableList, TunableTuple, TunableEnumEntryimport sims4.loglogger = sims4.log.Logger('RouteEventProviders', default_owner='rmccord')
class RouteEventProviderMixin:

    def on_event_executed(self, route_event, sim):
        pass

    def provide_route_events(self, route_event_context, sim, path, failed_types=None, start_time=0, end_time=None, **kwargs):
        raise NotImplementedError

    def is_route_event_valid(self, route_event, time, sim, path):
        raise NotImplementedError

class RouteEventProviderRequest(RouteEventProviderMixin, ParentElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'route_events': TunableTuple(description='\n            There are two kinds of route events. One is an that has a chance to\n            play every route at a low priority. One is repeating and gets\n            dispersed throughout the route at a very low priority.\n            ', single_events=TunableList(description='\n                Single Route Events to possibly play once on a route while the\n                Sim has this request active.\n                ', tunable=RouteEvent.TunableReference(description='\n                    A single route event that may happen once when a Sim is\n                    routing with this request on them.\n                    ', pack_safe=True)), repeating_events=TunableList(description='\n                Repeating Route Events which can occur multiple times over the\n                course of a route while this request is active.\n                ', tunable=RouteEvent.TunableReference(description="\n                    A repeating route event which will be dispersed throughout\n                    a Sim's route while they have this request on them.\n                    ", pack_safe=True))), 'participant': TunableEnumEntry(description='\n            The participant to which the Route Events will be attached.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor)}

    def __init__(self, owner, *args, sequence=(), **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(owner, 'is_super'):
            self._target = next(iter(owner.get_participants(self.participant)))
        else:
            self._target = owner
        self._sequence = sequence

    def start(self, *args, **kwargs):
        if self._target.routing_component is None:
            logger.error('Route Event Provider target {} has no routing component.', self._target)
            return
        self._target.routing_component.add_route_event_provider(self)

    def stop(self, *args, **kwargs):
        if self._target.routing_component is None:
            logger.error('Route Event Provider target {} has no routing component.', self._target)
            return
        self._target.routing_component.remove_route_event_provider(self)

    def provide_route_events(self, route_event_context, sim, path, failed_types=None, start_time=0, end_time=None, **kwargs):
        if self._target.is_sim:
            resolver = SingleSimResolver(self._target.sim_info)
        else:
            resolver = SingleObjectResolver(self._target)
        for route_event_cls in self.route_events.single_events:
            if not failed_types is None:
                pass
            if route_event_cls is not None and (route_event_context.route_event_already_scheduled(route_event_cls) or route_event_context.route_event_already_fully_considered(route_event_cls, self) or route_event_cls.test(resolver)):
                route_event_context.add_route_event(RouteEventType.LOW_SINGLE, route_event_cls(provider=self, provider_required=True))
        for route_event_cls in self.route_events.repeating_events:
            if not failed_types is None:
                pass
            if route_event_cls is not None and (route_event_context.route_event_already_fully_considered(route_event_cls, self) or route_event_cls.test(resolver)):
                route_event_context.add_route_event(RouteEventType.LOW_REPEAT, route_event_cls(provider=self, provider_required=True))

    def is_route_event_valid(self, route_event, time, sim, path):
        return True

    def _run(self, timeline):
        sequence = build_critical_section_with_finally(self.start, self._sequence, self.stop)
        return timeline.run_child(sequence)
