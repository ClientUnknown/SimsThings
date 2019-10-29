import weakreffrom sims4.tuning.instances import lock_instance_tunablesfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.complex.staffed_object_situation_mixin import StaffedObjectSituationMixinfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateData, CommonInteractionCompletedSituationStatefrom situations.situation_types import SituationCreationUIOptionimport servicesimport sims4.loglogger = sims4.log.Logger('TendObjectSituation', default_owner='rmccord')OBJECT_TOKEN = 'object_id'
class ArriveState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._change_state(self.owner.tend_state())

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.is_sim_in_situation(sim_info.get_sim_instance())

    def timer_expired(self):
        self.owner._change_state(self.owner.tend_state())

class TendState(CommonInteractionCompletedSituationState):

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.is_sim_in_situation(sim_info.get_sim_instance())

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()

    def timer_expired(self):
        self.owner._self_destruct()

class TendObjectSituation(StaffedObjectSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'arrive_state': ArriveState.TunableFactory(description='\n            Situation State for the Sim when they arrive to tend an object.', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_arrive_situation_state'), 'tend_state': TendState.TunableFactory(description='\n            Situation State for the Sim to tend an object.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_tend_situation_state'), 'tendor_job_and_role_state': TunableSituationJobAndRoleState(description='\n            Job and Role State for the tending Sim.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        reader = self._seed.custom_init_params_reader
        if reader is None:
            self._target_id = self._seed.extra_kwargs.get('default_target_id', None)
        else:
            self._target_id = reader.read_uint64(OBJECT_TOKEN, None)
        if self._target_id:
            target = services.object_manager().get(self._target_id)
            if target is not None:
                self._staffed_object = target

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _states(cls):
        return (SituationStateData(1, ArriveState, factory=cls.arrive_state), SituationStateData(2, TendState, factory=cls.tend_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.tendor_job_and_role_state.job, cls.tendor_job_and_role_state.role_state)]

    def start_situation(self):
        super().start_situation()
        self._change_state(self.arrive_state())

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        staffed_object = self.get_staffed_object()
        if staffed_object is not None:
            writer.write_uint64(OBJECT_TOKEN, staffed_object.id)
lock_instance_tunables(TendObjectSituation, exclusivity=BouncerExclusivityCategory.VENUE_EMPLOYEE, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)