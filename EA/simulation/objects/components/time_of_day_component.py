import randomfrom event_testing.resolver import SingleObjectResolverfrom event_testing.tests import TunableTestSetfrom interactions.utils.success_chance import SuccessChancefrom objects.components import Component, typesfrom objects.components.state import TunableStateTypeReference, TunableStateValueReferencefrom sims4.tuning.tunable import HasTunableFactory, TunableRange, TunableTuple, TunableMapping, TunableList, TunableReferenceimport alarmsimport clockimport date_and_timeimport servicesimport sims4.resources
class TimeOfDayComponent(Component, HasTunableFactory, component_name=types.TIME_OF_DAY_COMPONENT):
    DAILY_REPEAT = date_and_time.create_time_span(hours=24)
    FACTORY_TUNABLES = {'state_changes': TunableMapping(description='\n            A mapping from state to times of the day when the state should be \n            set to a tuned value.\n            ', key_type=TunableStateTypeReference(description='\n                The state to be set.\n                '), value_type=TunableList(description='\n                List of times to modify the state at.\n                ', tunable=TunableTuple(start_time=TunableRange(description='\n                        The start time (24 hour clock time) for the Day_Time state.\n                        ', tunable_type=float, default=0, minimum=0, maximum=24), value=TunableStateValueReference(description='\n                        New state value.\n                        '), loot_list=TunableList(description='\n                        A list of loot operations to apply when changing state.\n                        ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), chance=SuccessChance.TunableFactory(description='\n                        Percent chance that the state change will be considered. \n                        The chance is evaluated just before running the tests.\n                        '), tests=TunableTestSet(description='\n                        Test to decide whether the state change can be applied.\n                        '))))}

    def __init__(self, owner, *, state_changes):
        super().__init__(owner)
        self.state_changes = state_changes
        self.alarm_handles = []

    def _apply_state_change(self, state, change):
        resolver = SingleObjectResolver(self.owner)
        chance = change.chance.get_chance(resolver)
        if random.random() > chance:
            return
        if not change.tests.run_tests(resolver):
            return
        self.owner.set_state(state, change.value)
        for loot_action in change.loot_list:
            loot_action.apply_to_resolver(resolver)

    def _add_alarm(self, cur_state, state, change):
        now = services.time_service().sim_now
        time_to_day = clock.time_until_hour_of_day(now, change.start_time)

        def alarm_callback(_):
            self._apply_state_change(state, change)

        self.alarm_handles.append(alarms.add_alarm(self.owner, time_to_day, alarm_callback, repeating=True, repeating_time_span=self.DAILY_REPEAT))
        if cur_state is None or time_to_day > cur_state[0]:
            return (time_to_day, change)
        return cur_state

    def on_add(self):
        for (state, changes) in self.state_changes.items():
            current_state = None
            for change in changes:
                current_state = self._add_alarm(current_state, state, change)
            if current_state is not None:
                self._apply_state_change(state, current_state[1])

    def on_remove(self):
        for handle in self.alarm_handles:
            alarms.cancel_alarm(handle)
