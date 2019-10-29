from event_testing.resolver import SingleSimResolver, SingleActorAndObjectResolverfrom sims4.resources import Typesfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableList, TunableTuple, TunableSimMinute, TunableReferenceimport alarmsimport clockimport services
class PeriodicLootOperation(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'periodic_loots': TunableList(description='\n            A list of periodic loots to apply.\n            ', tunable=TunableTuple(initial_delay=TunableSimMinute(description='\n                    Delay before the first loot.\n                    ', default=15, minimum=0), frequency_interval=TunableSimMinute(description='\n                    The time between loot applications. \n                    ', default=15, minimum=5), loots_to_apply=TunableList(description='\n                    The loots to apply\n                    ', unique_entries=True, tunable=TunableReference(description='\n                        The loot to apply.\n                        ', manager=services.get_instance_manager(Types.ACTION), pack_safe=True))))}

    def __init__(self, owner, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner = owner
        self._alarm_handles = []

    def start(self, *_, **__):
        for periodic_loot_data in self.periodic_loots:
            alarm_handle = alarms.add_alarm(self._owner, clock.interval_in_sim_minutes(periodic_loot_data.initial_delay), lambda _, loots=periodic_loot_data.loots_to_apply: self._apply_loots(loots), repeating=True, repeating_time_span=clock.interval_in_sim_minutes(periodic_loot_data.frequency_interval))
            self._alarm_handles.append(alarm_handle)

    def stop(self, *_, **__):
        while self._alarm_handles:
            alarm_handle = self._alarm_handles.pop()
            alarms.cancel_alarm(alarm_handle)

    def _apply_loots(self, loots):
        resolver = SingleSimResolver(self._owner.sim_info) if self._owner.is_sim else SingleActorAndObjectResolver(None, self._owner, self)
        for loot in loots:
            loot.apply_to_resolver(resolver)
