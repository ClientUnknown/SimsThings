from event_testing.test_events import TestEventimport servicesfrom sims4.tuning.tunable import OptionalTunable, TunableEnumEntry, TunableMapping, TunableRange, TunableReference, TunableTuplefrom situations.situation_goal import SituationGoalimport sims4.resources
class SituationGoalSimoleonsCollected(SituationGoal):
    SIMOLEONS_COLLECTED = 'simoleons_collected'
    REMOVE_INSTANCE_TUNABLES = ('_post_tests',)
    INSTANCE_TUNABLES = {'test_events_to_collect': TunableMapping(description='\n            A mapping of test event -> score achieved when successfully ran.\n            ', key_type=TunableEnumEntry(description='\n                The event to listen to for goal completion.\n                ', tunable_type=TestEvent, default=TestEvent.Invalid), value_type=TunableTuple(description='\n                A tuple of the Simoleon amount to increment and other checks \n                to make on the event before it satisfies the goal.\n                ', simoleons=TunableRange(description='\n                    The Simoleon amount the interaction results when completed.\n                    ', tunable_type=int, minimum=1, default=1), interaction=OptionalTunable(description='\n                    When enabled, there will be a test to verify that the \n                    interaction sending the associated test event is the same\n                    as the tuned interaction.\n                    ', tunable=TunableReference(description='\n                        The interaction to require the event to come from in\n                        order for it to satisfy the goal.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION))))), 'amount_to_collect': TunableRange(description='\n            The amount of Simoleons collected from all relevant activities for \n            this goal to pass.\n            ', tunable_type=int, minimum=1, default=100)}

    def __init__(self, *args, reader=None, **kwargs):
        super().__init__(*args, reader=reader, **kwargs)
        self._total_simoleons_collected = 0
        if reader is not None:
            simoleons_collected = reader.read_uint64(self.SIMOLEONS_COLLECTED, 0)
            self._total_simoleons_collected = simoleons_collected

    def setup(self):
        super().setup()
        for test_event in self.test_events_to_collect:
            services.get_event_manager().register_single_event(self, test_event)

    def create_seedling(self):
        seedling = super().create_seedling()
        writer = seedling.writer
        writer.write_uint64(self.SIMOLEONS_COLLECTED, self._total_simoleons_collected)
        return seedling

    def _decommision(self):
        for test_event in self.test_events_to_collect:
            services.get_event_manager().unregister_single_event(self, test_event)
        super()._decommision()

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        result = super()._run_goal_completion_tests(sim_info, event, resolver)
        if not result:
            return False
        event_simoleons = self.test_events_to_collect.get(event, None)
        if event_simoleons is not None:
            if event_simoleons.interaction is not None and event_simoleons.interaction is not resolver.interaction.affordance:
                return False
            self._total_simoleons_collected += event_simoleons.simoleons
            if self._total_simoleons_collected >= self.amount_to_collect:
                super()._on_goal_completed()
            else:
                self._on_iteration_completed()

    @property
    def completed_iterations(self):
        return self._total_simoleons_collected

    @property
    def max_iterations(self):
        return self.amount_to_collect
