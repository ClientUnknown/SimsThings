import event_testingfrom event_testing.results import TestResultimport servicesimport sims4.tuningfrom sims4.tuning.tunable import AutoFactoryInit, TunableReference, TunableSet, Tunable, TunableSingletonFactory, TunableEnumWithFilterfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_goal import SituationGoalfrom statistics.mood import Moodimport tag
class MultipleSimInteractionOfInterest(AutoFactoryInit):
    FACTORY_TUNABLES = {'affordance': TunableReference(description='\n                The affordance in question that is being run by all the sims.\n                ', manager=services.affordance_manager(), class_restrictions='SuperInteraction', allow_none=True), 'tags': TunableSet(description='\n                A set of tags that match the affordance being run by all the sims. \n                ', tunable=TunableEnumWithFilter(tunable_type=tag.Tag, default=tag.Tag.INVALID, filter_prefixes=tag.INTERACTION_PREFIX)), 'sim_count': Tunable(description='\n                The number of sims simultaneously running the appropriate interactions.\n                ', tunable_type=int, default=2)}
    expected_kwargs = (('interaction', event_testing.test_constants.FROM_EVENT_DATA),)

    def get_expected_args(self):
        return dict(self.expected_kwargs)

    def __call__(self, interaction=None):
        if interaction.get_interaction_type() is self.affordance:
            return TestResult.TRUE
        if self.tags & interaction.get_category_tags():
            return TestResult.TRUE
        return TestResult(False, 'Failed affordance check: {} is not {} and does not have any matching tags in {}.', interaction.affordance, self.affordance, self.tags)

    def custom_keys_gen(self):
        if self.affordance:
            yield self.affordance
        for tag in self.tags:
            yield tag
TunableMultipleSimInteractionOfInterest = TunableSingletonFactory.create_auto_factory(MultipleSimInteractionOfInterest)
class SituationGoalMultipleSimsInInteraction(SituationGoal):
    INSTANCE_TUNABLES = {'_goal_test': TunableMultipleSimInteractionOfInterest(tuning_group=GroupNames.TESTS), '_select_sims_outside_of_situation': sims4.tuning.tunable.Tunable(bool, False, description='\n                If true, the goal system selects all instantiated sims in the zone.\n                ')}

    def __init__(self, *args, reader=None, **kwargs):
        super().__init__(*args, reader=reader, **kwargs)
        self._sims_running_interaction = set()
        self._test_events = set()

    def setup(self):
        super().setup()

        def test_affordance(sim):
            return sim.si_state.is_running_affordance(self._goal_test.affordance) or sim.get_running_interactions_by_tags(self._goal_test.tags)

        if self._situation is None or self._select_sims_outside_of_situation:
            for sim in services.sim_info_manager().instanced_sims_gen():
                if test_affordance(sim):
                    self._sims_running_interaction.add(sim.id)
        else:
            for sim in self._situation.all_sims_in_situation_gen():
                if test_affordance(sim):
                    self._sims_running_interaction.add(sim.id)
        for custom_key in self._goal_test.custom_keys_gen():
            services.get_event_manager().register_with_custom_key(self, event_testing.test_events.TestEvent.InteractionStart, custom_key)
            services.get_event_manager().register_with_custom_key(self, event_testing.test_events.TestEvent.InteractionComplete, custom_key)

    def _decommision(self):
        for custom_key in self._goal_test.custom_keys_gen():
            services.get_event_manager().unregister_with_custom_key(self, event_testing.test_events.TestEvent.InteractionStart, custom_key)
            services.get_event_manager().unregister_with_custom_key(self, event_testing.test_events.TestEvent.InteractionComplete, custom_key)
        super()._decommision()

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        if self._situation is not None and not self._select_sims_outside_of_situation:
            sim = sim_info.get_sim_instance()
            if not self._situation.is_sim_in_situation(sim):
                return False
        if not resolver(self._goal_test):
            return False
        else:
            if event == event_testing.test_events.TestEvent.InteractionStart:
                self._sims_running_interaction.add(sim_info.id)
            else:
                self._sims_running_interaction.discard(sim_info.id)
            self._on_iteration_completed()
            if len(self._sims_running_interaction) >= self._goal_test.sim_count:
                return True
        return False

    @property
    def completed_iterations(self):
        return len(self._sims_running_interaction)

    @property
    def max_iterations(self):
        return self._goal_test.sim_count
sims4.tuning.instances.lock_instance_tunables(SituationGoalMultipleSimsInInteraction, _iterations=1)
class MultipleSimMoodOfInterest(AutoFactoryInit):
    FACTORY_TUNABLES = {'mood': Mood.TunableReference(description='\n                The mood that we are hoping for the sims to achieve.\n                '), 'sim_count': Tunable(description='\n                The number of sims the tuned mood at the same time.\n                ', tunable_type=int, default=2)}
TunableMultipleSimMoodOfInterest = TunableSingletonFactory.create_auto_factory(MultipleSimMoodOfInterest)
class SituationGoalMultipleSimsInMood(SituationGoal):
    INSTANCE_TUNABLES = {'_goal_test': TunableMultipleSimMoodOfInterest(tuning_group=GroupNames.TESTS), '_select_sims_outside_of_situation': sims4.tuning.tunable.Tunable(bool, False, description='\n                If true, the goal system selects all instantiated sims in the zone.\n                '), '_give_goal_even_if_it_would_auto_pass': Tunable(description='\n                If checked then this goal will be given even if the goal would\n                instantly complete.  An example wanting this is the Play Date\n                Where there is only one possible goal and we want to give the\n                player the score for completing it.\n                ', tunable_type=bool, default=False)}

    @classmethod
    def can_be_given_as_goal(cls, actor, situation, **kwargs):
        result = super(SituationGoalMultipleSimsInMood, cls).can_be_given_as_goal(actor, situation)
        if not result:
            return result
        if cls._give_goal_even_if_it_would_auto_pass:
            return TestResult.TRUE
        sims_in_the_mood = set()
        if situation is None or cls._select_sims_outside_of_situation:
            for sim in services.sim_info_manager().instanced_sims_gen():
                if sim.get_mood() is cls._goal_test.mood:
                    sims_in_the_mood.add(sim.id)
        else:
            for sim in situation.all_sims_in_situation_gen():
                if sim.get_mood() is cls._goal_test.mood:
                    sims_in_the_mood.add(sim.id)
        if len(sims_in_the_mood) >= cls._goal_test.sim_count:
            return TestResult(False, 'Test Auto Passes: {} sims in {} mood')
        return TestResult.TRUE

    def __init__(self, *args, reader=None, **kwargs):
        super().__init__(*args, reader=reader, **kwargs)
        self._sims_in_the_mood = set()
        self._test_events = set()

    def setup(self):
        super().setup()
        if self._situation is None or self._select_sims_outside_of_situation:
            for sim in services.sim_info_manager().instanced_sims_gen():
                if sim.get_mood() is self._goal_test.mood:
                    self._sims_in_the_mood.add(sim.id)
        else:
            for sim in self._situation.all_sims_in_situation_gen():
                if sim.get_mood() is self._goal_test.mood:
                    self._sims_in_the_mood.add(sim.id)
        self._test_events.add(event_testing.test_events.TestEvent.MoodChange)
        services.get_event_manager().register(self, self._test_events)

    def _decommision(self):
        services.get_event_manager().unregister(self, self._test_events)
        super()._decommision()

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        if self._situation is not None and not (self._select_sims_outside_of_situation or self._situation.is_sim_in_situation(sim_info.get_sim_instance())):
            return False
        else:
            if sim_info.get_mood() is self._goal_test.mood:
                self._sims_in_the_mood.add(sim_info.id)
            else:
                self._sims_in_the_mood.discard(sim_info.id)
            self._on_iteration_completed()
            if len(self._sims_in_the_mood) >= self._goal_test.sim_count:
                return True
        return False

    @property
    def completed_iterations(self):
        return len(self._sims_in_the_mood)

    @property
    def max_iterations(self):
        return self._goal_test.sim_count
sims4.tuning.instances.lock_instance_tunables(SituationGoalMultipleSimsInMood, _iterations=1)