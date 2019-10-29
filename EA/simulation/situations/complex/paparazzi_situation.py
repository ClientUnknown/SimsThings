from sims4.tuning.instances import lock_instance_tunablesfrom situations.bouncer.bouncer_types import BouncerExclusivityCategory, RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import SituationStateData, TunableSituationJobAndRoleStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfoimport servicesimport sims4.tuningimport situations.situation_complexfrom sims4.tuning.tunable import OptionalTunable
class _PaparazziMainState(situations.situation_complex.SituationState):
    pass

class PaparazziSituation(situations.situation_complex.SituationComplexCommon):
    INSTANCE_TUNABLES = {'job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the paparazzo\n            '), 'lock_doors_situation': OptionalTunable(tunable=sims4.tuning.tunable.TunableReference(description="\n                A situation that the paparazzi will be placed into in addition that\n                will prevent them from entering the celebrity's house. This\n                is done on a seperate situation so that we can have paparazzi enter\n                houses under some circumstances (like being let in).\n                ", manager=services.get_instance_manager(sims4.resources.Types.SITUATION), tuning_group=sims4.tuning.tunable_base.GroupNames.SITUATION, class_restrictions=('PaparazziLockOutSituation',)))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock_out_situation_id = None

    def _destroy(self):
        if self._lock_out_situation_id is not None:
            situation_manager = services.get_zone_situation_manager()
            if situation_manager.get(self._lock_out_situation_id) is not None:
                situation_manager.destroy_situation_by_id(self._lock_out_situation_id)
                self._lock_out_situation_id = None
        super()._destroy()

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _PaparazziMainState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.job_and_role_state.job, cls.job_and_role_state.role_state)]

    @classmethod
    def default_job(cls):
        pass

    def _on_set_sim_role_state(self, sim, job_type, role_state_type, role_affordance_target):
        super()._on_set_sim_role_state(sim, job_type, role_state_type, role_affordance_target)
        if self.lock_doors_situation is not None:
            guest_list = SituationGuestList(invite_only=True)
            guest_list.add_guest_info(SituationGuestInfo(sim.sim_id, self.lock_doors_situation.get_lock_out_job(), RequestSpawningOption.CANNOT_SPAWN, BouncerRequestPriority.EVENT_DEFAULT_JOB))
            self._lock_out_situation_id = services.get_zone_situation_manager().create_situation(self.lock_doors_situation, user_facing=False, guest_list=guest_list)

    def start_situation(self):
        super().start_situation()
        self._change_state(_PaparazziMainState())
