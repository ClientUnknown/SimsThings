import random
class _LoungerSituationState(SituationState):
    pass

class PoolVenueLoungerSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'lounger_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role for Pool Venue lounger.\n            '), 'duration_randomizer': TunableSimMinute(description="\n            A random time between 0 and this tuned time will be added to the\n            situation's duration.\n            ", default=10, minimum=0)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _LoungerSituationState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.lounger_job_and_role.job, cls.lounger_job_and_role.role_state)]

    @classmethod
    def default_job(cls):
        return cls.lounger_job_and_role.job

    def start_situation(self):
        super().start_situation()
        self._change_state(_LoungerSituationState())

    def _get_duration(self):
        if self._seed.duration_override is not None:
            return self._seed.duration_override
        return self.duration + random.randint(0, self.duration_randomizer)
