from sims4.tuning.instances import lock_instance_tunablesfrom sims4.utils import classpropertyfrom situations.base_situation import _RequestUserDatafrom situations.bouncer.bouncer_request import SelectableSimRequestFactoryfrom situations.situation import Situationfrom situations.situation_complex import SituationState, SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateDatafrom situations.situation_types import SituationCreationUIOption, SituationSerializationOption
class _SelectableSimsBackgroundSituationState(SituationState):
    pass

class SelectableSimBackgroundSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role that the selectable Sims will be given.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classproperty
    def situation_serialization_option(cls):
        return SituationSerializationOption.DONT

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _SelectableSimsBackgroundSituationState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.job_and_role.job, cls.job_and_role.role_state)]

    @classmethod
    def default_job(cls):
        pass

    def start_situation(self):
        super().start_situation()
        self._change_state(_SelectableSimsBackgroundSituationState())

    def _issue_requests(self):
        request = SelectableSimRequestFactory(self, callback_data=_RequestUserData(role_state_type=self.job_and_role.role_state), job_type=self.job_and_role.job, exclusivity=self.exclusivity)
        self.manager.bouncer.submit_request(request)
lock_instance_tunables(SelectableSimBackgroundSituation, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)