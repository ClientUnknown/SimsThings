from sims4.tuning.instances import lock_instance_tunablesfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationState, SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateDatafrom situations.situation_types import SituationCreationUIOption
class _BartenderSituationState(SituationState):
    pass

class BartenderSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'bartender_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role of the bartender.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _BartenderSituationState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.bartender_job_and_role.job, cls.bartender_job_and_role.role_state)]

    @classmethod
    def default_job(cls):
        pass

    def start_situation(self):
        super().start_situation()
        self._change_state(_BartenderSituationState())
lock_instance_tunables(BartenderSituation, exclusivity=BouncerExclusivityCategory.VENUE_EMPLOYEE, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0, _implies_greeted_status=False)