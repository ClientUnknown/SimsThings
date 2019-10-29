from sims4.resources import Typesfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReferencefrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationState, SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateDatafrom situations.situation_types import SituationCreationUIOptionimport services
class _FanSituationState(SituationState):
    pass

class FanSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the fan.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _FanSituationState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.job_and_role_state.job, cls.job_and_role_state.role_state)]

    @classmethod
    def default_job(cls):
        pass

    @classproperty
    def fan_job(cls):
        return cls.job_and_role_state.job

    def start_situation(self):
        super().start_situation()
        self._change_state(_FanSituationState())
lock_instance_tunables(FanSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)
class StanSituation(FanSituation):
    INSTANCE_TUNABLES = {'cooldown_bit': TunableReference(description='\n            Cooldown bit set on the stan when it is added to this situation.\n            This rel-bit should have a timeout.\n            \n            While this stat is set, a Sim assigned to this situation will\n            not be able to stan for a while after this situation expires.\n            ', manager=services.get_instance_manager(Types.RELATIONSHIP_BIT), tuning_group='Fans')}

    def _on_set_sim_job(self, sim, job):
        super()._on_set_sim_job(sim, job)
        stanned_sim_id = self.initiating_sim_info.sim_id
        services.relationship_service().add_relationship_bit(sim.sim_id, stanned_sim_id, self.cooldown_bit, send_rel_change_event=False)

    def _gsi_additional_data_gen(self):
        yield ('Stanned Sim', str(self.initiating_sim_info))
