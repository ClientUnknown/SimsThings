from sims4.tuning.instances import lock_instance_tunablesfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationState, TunableSituationJobAndRoleState, SituationComplexCommon, SituationStateDatafrom situations.situation_types import SituationCreationUIOption
class KaraokeDuetState(SituationState):
    pass

class KaraokeDuetSimSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'karaoke_singer_job': TunableSituationJobAndRoleState(description='\n            The default job and role for a Sim in this situation. They only\n            have one role, so this is what will be given for them to do.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self._duet_sim = None

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.karaoke_singer_job.job, cls.karaoke_singer_job.role_state)]

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._duet_sim = sim

    @classmethod
    def default_job(cls):
        return cls.karaoke_singer_job.job

    def start_situation(self):
        super().start_situation()
        self._change_state(KaraokeDuetState())

    def sim_of_interest(self, sim_info):
        if self._duet_sim is not None and self._duet_sim.sim_info is sim_info:
            return True
        return False

    @classmethod
    def _states(cls):
        return (SituationStateData(1, KaraokeDuetState),)
lock_instance_tunables(KaraokeDuetSimSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)