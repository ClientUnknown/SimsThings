from sims4.tuning.tunable_base import GroupNamesfrom situations.complex.give_job_object_situation_mixin import GiveJobObjectSituationMixinfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonSituationState, SituationStateData, TunableSituationJobAndRoleStateimport sims4logger = sims4.log.Logger('SuntannerSituation', default_owner='msundaram')
class _SuntannerSituationState(CommonSituationState):
    pass

class SuntannerSituation(GiveJobObjectSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'situation_default_job_and_role': TunableSituationJobAndRoleState(description='\n            The default job that a visitor will be in during the situation.\n            '), 'default_state': _SuntannerSituationState.TunableFactory(description='\n            The default state of this situation.\n            ', display_name='State', tuning_group=GroupNames.STATE)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def default_job(cls):
        return cls.situation_default_job_and_role.job

    @classmethod
    def _states(cls):
        return [SituationStateData(1, _SuntannerSituationState, factory=cls.default_state)]

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.situation_default_job_and_role.job, cls.situation_default_job_and_role.role_state)]

    def start_situation(self):
        super().start_situation()
        self._change_state(self.default_state())
