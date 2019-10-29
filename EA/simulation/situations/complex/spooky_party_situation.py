from sims4.tuning.tunable import TunableSimMinute, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_complex import CommonSituationState, SituationComplexCommon, SituationStateDataimport servicesPARTY_TIME_PHASE_TIMEOUT = 'party_time_phase_duration'
class _PartyTimeState(CommonSituationState):
    FACTORY_TUNABLES = {'timeout': TunableSimMinute(description='\n                The amount of time to wait until the party switches to phase 2\n                winding down.\n                ', default=10, minimum=1)}

    def __init__(self, timeout, **kwargs):
        super().__init__(**kwargs)
        self._timeout = timeout

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._create_or_load_alarm(PARTY_TIME_PHASE_TIMEOUT, self._timeout, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def timer_expired(self):
        self._change_state(self.owner.wind_down_state())

class _WindDownState(CommonSituationState):
    pass

class SpookyParty(SituationComplexCommon):
    INSTANCE_TUNABLES = {'party_time_state': _PartyTimeState.TunableFactory(description='\n                The first and main state of the situation, this will be where\n                the actual party is ran before the winding down phase.\n                ', tuning_group=GroupNames.STATE), 'wind_down_state': _WindDownState.TunableFactory(description='\n                Last phase of the situation where desserts will start being\n                served and cleanup will start.\n                ', tuning_group=GroupNames.STATE), '_default_job': TunableReference(description='\n                The job for all of the sims invited to the situation.\n                ', manager=services.situation_job_manager())}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _PartyTimeState, factory=cls.party_time_state), SituationStateData(2, _WindDownState, factory=cls.wind_down_state))

    @classmethod
    def default_job(cls):
        return cls._default_job

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.party_time_state._tuned_values.job_and_role_changes.items())

    def start_situation(self):
        super().start_situation()
        self._change_state(self.party_time_state())
