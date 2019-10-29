from event_testing.test_events import TestEventfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_complex import SituationComplexCommon, CommonSituationState, CommonInteractionCompletedSituationState, SituationStateDatafrom tag import TunableTags
class _ActingEmployeePrePerformanceState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'locked_args': {'time_out': None}}

    def _on_interaction_of_interest_complete(self, resolver=None, **kwargs):
        if resolver and resolver.interaction.has_been_reset:
            return
        self._change_state(self.owner._go_to_marks_state())

class _ActingEmployeeGoToMarksState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'locked_args': {'time_out': None}}

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner._performance_state())

class _ActingEmployeePerformanceState(CommonSituationState):
    FACTORY_TUNABLES = {'locked_args': {'time_out': None}}

class _ActingEmployeePostPerformanceState(CommonSituationState):
    FACTORY_TUNABLES = {'locked_args': {'time_out': None}}

class ActingEmployeeSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'_pre_performance_state': _ActingEmployeePrePerformanceState.TunableFactory(description='\n            The initial state for npc co star sims.\n            ', tuning_group=GroupNames.STATE, display_name='01_pre_performance_state'), '_go_to_marks_state': _ActingEmployeeGoToMarksState.TunableFactory(description='\n            The employee sim will go to this state once the player says their\n            ready to perform.\n            ', tuning_group=GroupNames.STATE, display_name='02_go_to_marks_state'), '_performance_state': _ActingEmployeePerformanceState.TunableFactory(description='\n            Once the employee gets to their marks, they will end up in this\n            state. The only interactions that should be valid at this point is\n            some idle interaction and the performance interactions.\n            ', tuning_group=GroupNames.STATE, display_name='03_performance_state'), '_post_performance_state': _ActingEmployeePostPerformanceState.TunableFactory(description='\n            When the main situation goal is completed by the player, employees will be pushed into\n            this state.\n            ', tuning_group=GroupNames.STATE, display_name='04_post_performance_state'), '_actor_career_event_situation_tags': TunableTags(description='\n            A set of tags that can identify an actor career event situation.\n            \n            Used to track when the actor completes the performance.\n            ', tuning_group=GroupNames.SITUATION, filter_prefixes=('Situation',))}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _ActingEmployeePrePerformanceState, factory=cls._pre_performance_state), SituationStateData(2, _ActingEmployeeGoToMarksState, factory=cls._go_to_marks_state), SituationStateData(3, _ActingEmployeePerformanceState, factory=cls._performance_state), SituationStateData(4, _ActingEmployeePostPerformanceState, factory=cls._post_performance_state))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls._pre_performance_state._tuned_values.job_and_role_changes.items())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._register_test_event_for_keys(TestEvent.MainSituationGoalComplete, self._actor_career_event_situation_tags)
        self._register_test_event_for_keys(TestEvent.SituationEnded, self._actor_career_event_situation_tags)

    def start_situation(self):
        super().start_situation()
        self._change_state(self._pre_performance_state())

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.MainSituationGoalComplete:
            self._change_state(self._post_performance_state())
        elif event == TestEvent.SituationEnded:
            self._change_state(self._post_performance_state())
