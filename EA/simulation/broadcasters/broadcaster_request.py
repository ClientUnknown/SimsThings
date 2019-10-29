from broadcasters.broadcaster_utils import BroadcasterClockTypefrom element_utils import build_critical_section_with_finally, build_delayed_element, build_critical_sectionfrom event_testing.resolver import SingleObjectResolverfrom interactions import ParticipantTypeSingle, ParticipantTypefrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumEntry, OptionalTunable, TunableSimMinute, TunableReferencefrom singletons import DEFAULTfrom tunable_utils.tested_list import TunableTestedListimport clockimport elementsimport servicesimport sims4.resources
class BroadcasterRequest(elements.ParentElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'broadcaster_types': TunableTestedList(description='\n            A list of broadcasters to request.\n            ', tunable_type=TunableReference(description='\n                The broadcasters to request.\n                ', manager=services.get_instance_manager(sims4.resources.Types.BROADCASTER), pack_safe=True)), 'participant': TunableEnumEntry(description='\n            The participant to which the broadcaster(s) will be attached.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Actor), 'offset_time': OptionalTunable(description='\n            If enabled, the interaction will wait this amount of time\n            after the beginning before running the broadcaster.\n            ', tunable=TunableSimMinute(description='\n                The interaction will wait this amount of time after the \n                beginning before running the broadcaster.\n                ', default=2))}

    def __init__(self, owner, *args, sequence=(), **kwargs):
        super().__init__(*args, **kwargs)
        self._sequence = sequence
        if hasattr(owner, 'target'):
            self._interaction = owner
            self._target = owner.get_participant(self.participant)
        else:
            self._interaction = None
            self._target = owner
        self._broadcasters = []

    @classmethod
    def on_affordance_loaded_callback(cls, affordance, broadcaster_request, object_tuning_id=DEFAULT):
        for broadcaster_type in broadcaster_request.broadcaster_types.get_all():
            broadcaster_type.register_static_callbacks(affordance, object_tuning_id=object_tuning_id)

    def start_one_shot(self, *_, **__):
        if self._target.is_prop:
            return
        current_zone = services.current_zone()
        broadcaster_service = current_zone.broadcaster_service
        broadcaster_service_real_time = current_zone.broadcaster_real_time_service
        game_time_broadcasters = []
        real_time_broadcasters = []
        if broadcaster_service_real_time is not None:
            if self._interaction is not None:
                resolver = self._interaction.get_resolver()
            else:
                resolver = SingleObjectResolver(self._target)
            for broadcaster_type in self.broadcaster_types(resolver=resolver):
                broadcaster = broadcaster_type(broadcasting_object=self._target, interaction=self._interaction)
                if broadcaster.clock_type == BroadcasterClockType.GAME_TIME:
                    game_time_broadcasters.append(broadcaster)
                elif broadcaster.clock_type == BroadcasterClockType.REAL_TIME:
                    real_time_broadcasters.append(broadcaster)
                else:
                    raise NotImplementedError
            if game_time_broadcasters:
                broadcaster_service.update_broadcasters_one_shot(game_time_broadcasters)
            if real_time_broadcasters:
                broadcaster_service_real_time.update_broadcasters_one_shot(real_time_broadcasters)

    def start(self, *_, **__):
        if self._target.is_prop:
            return
        current_zone = services.current_zone()
        broadcaster_service = current_zone.broadcaster_service
        broadcaster_service_real_time = current_zone.broadcaster_real_time_service
        if broadcaster_service_real_time is not None:
            if self._interaction is not None:
                resolver = self._interaction.get_resolver()
            else:
                resolver = SingleObjectResolver(self._target)
            for broadcaster_type in self.broadcaster_types(resolver=resolver):
                broadcaster = broadcaster_type(broadcasting_object=self._target, interaction=self._interaction)
                self._broadcasters.append(broadcaster)
                if broadcaster.clock_type == BroadcasterClockType.GAME_TIME:
                    broadcaster_service.add_broadcaster(broadcaster)
                elif broadcaster.clock_type == BroadcasterClockType.REAL_TIME:
                    broadcaster_service_real_time.add_broadcaster(broadcaster)
                else:
                    raise NotImplementedError

    def stop(self, *_, **__):
        current_zone = services.current_zone()
        broadcaster_service = current_zone.broadcaster_service
        broadcaster_service_real_time = current_zone.broadcaster_real_time_service
        if broadcaster_service_real_time is not None:
            for broadcaster in self._broadcasters:
                if broadcaster.clock_type == BroadcasterClockType.GAME_TIME:
                    broadcaster_service.remove_broadcaster(broadcaster)
                else:
                    broadcaster_service_real_time.remove_broadcaster(broadcaster)
        self._broadcasters = []

    def _run(self, timeline):
        if self._target.is_terrain:
            start = self.start_one_shot
            stop = lambda *args, **kwargs: None
        else:
            start = self.start
            stop = self.stop
        if self.offset_time is None:
            sequence = build_critical_section_with_finally(start, self._sequence, stop)
        else:
            sequence = build_delayed_element(self._sequence, clock.interval_in_sim_minutes(self.offset_time), start)
            sequence = build_critical_section_with_finally(sequence, stop)
        return timeline.run_child(sequence)
