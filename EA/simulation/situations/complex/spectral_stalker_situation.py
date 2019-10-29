import servicesimport sims4.logfrom date_and_time import create_time_spanfrom event_testing.test_events import TestEventfrom sims4.tuning.tunable import TunableInterval, TunableSimMinutefrom situations.situation import Situationfrom situations.situation_complex import CommonInteractionCompletedSituationState, SituationComplexCommon, SituationStateData, CommonSituationStatefrom situations.situation_job import SituationJoblogger = sims4.log.Logger('SpectralStalkerSituation', default_owner='trevor')
class _BaseSpectralStalkerState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        next_state = self.owner.exit_state if self.owner.should_exit_situation() else self._get_next_state()
        self._change_state(next_state())

    def _get_next_state(self):
        raise NotImplementedError

    def timer_expired(self):
        next_state = self.owner.exit_state if self.owner.should_exit_situation() else self._get_next_state()
        self._change_state(next_state())

class _SpectralStalkerEnterState(_BaseSpectralStalkerState):

    def _get_next_state(self):
        return self.owner.chase_state

class _SpectralStalkerChaseState(_BaseSpectralStalkerState):

    def _get_next_state(self):
        return self.owner.idle_state

class _SpectralStalkerIdleState(_BaseSpectralStalkerState):

    def _get_next_state(self):
        return self.owner.chase_state

class _SpectralStalkerExitState(CommonSituationState):

    def timer_expired(self):
        for sim in self.owner.all_sims_in_situation_gen():
            if sim.sim_info == self.owner._stalker_sim_info:
                services.get_zone_situation_manager().make_sim_leave_now_must_run(sim)
        self.owner._self_destruct()
STALKER_GROUP = 'Spectral_Stalker'
class SpectralStalkerSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'enter_state': _SpectralStalkerEnterState.TunableFactory(description='\n            The first state the Spectral Stalker starts in. This should handle any\n            spawning behavior. When the Interaction Of Interest completes, the \n            Stalker will be pushed to chase the target Sim.\n            ', tuning_group=STALKER_GROUP), 'chase_state': _SpectralStalkerChaseState.TunableFactory(description='\n            The stalker chases the target Sim.\n            ', tuning_group=STALKER_GROUP), 'idle_state': _SpectralStalkerIdleState.TunableFactory(description="\n            The stalker Idles until it's time to chase again.\n            ", tuning_group=STALKER_GROUP), 'exit_state': _SpectralStalkerExitState.TunableFactory(description='\n            The Spectral Stalker exits the world.\n            ', tuning_group=STALKER_GROUP), 'target_job': SituationJob.TunableReference(description='\n            The Situation Job on the target of the Spectral Stalker.\n            '), 'time_to_chase': TunableInterval(description='\n            The upper and lower limit for the amount of time, in Sim Minutes, to \n            chase a Sim before exiting the situation. When the Stalker starts, a \n            random time between these values will be chosen.\n            ', tunable_type=TunableSimMinute, default_lower=30, default_upper=120, minimum=1, tuning_group=STALKER_GROUP)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES
    TEST_EVENTS = (TestEvent.OnSimReset, TestEvent.SimDeathTypeSet)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target_sim_info = None
        self._stalker_sim_info = None
        self._stalk_finish_ticks = None

    @classmethod
    def _states(cls):
        return [SituationStateData(0, _SpectralStalkerEnterState, cls.enter_state), SituationStateData(1, _SpectralStalkerChaseState, cls.chase_state), SituationStateData(2, _SpectralStalkerIdleState, cls.idle_state), SituationStateData(3, _SpectralStalkerExitState, cls.exit_state)]

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.enter_state._tuned_values.job_and_role_changes.items())

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if sim_info is self._target_sim_info and (event == TestEvent.OnSimReset or event == TestEvent.SimDeathTypeSet):
            self._stalk_finish_ticks = None
            self._change_state(self.exit_state())

    def start_situation(self):
        super().start_situation()
        self._change_state(self.enter_state())

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        if job_type is self.target_job:
            self._target_sim_info = sim.sim_info
            services.get_event_manager().register(self, self.TEST_EVENTS)
        else:
            self._stalker_sim_info = sim.sim_info
            self._stalk_finish_ticks = services.time_service().sim_now.absolute_ticks() + create_time_span(minutes=self.time_to_chase.random_int()).in_ticks()

    def _self_destruct(self):
        services.get_event_manager().unregister(self, self.TEST_EVENTS)
        super()._self_destruct()

    def should_exit_situation(self):
        if not self._stalk_finish_ticks:
            return True
        return services.time_service().sim_now.absolute_ticks() >= self._stalk_finish_ticks
