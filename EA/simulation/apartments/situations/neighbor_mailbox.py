import randomfrom sims4.tuning.instances import lock_instance_tunablesfrom situations.bouncer.bouncer_types import BouncerExclusivityCategory, RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, CommonSituationState, SituationStateDatafrom situations.situation_guest_list import SituationGuestInfo, SituationGuestListfrom situations.situation_types import SituationCreationUIOptionimport services
class _CheckMailState(CommonSituationState):
    pass

class NeighborMailboxSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'check_mail_state': _CheckMailState.TunableFactory(description='\n            Situation State for the Sim to check their mail.\n            '), 'neighbor_job_and_role_state': TunableSituationJobAndRoleState(description='\n            Job and Role State for the neighbor.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _CheckMailState, factory=cls.check_mail_state),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.neighbor_job_and_role_state.job, cls.neighbor_job_and_role_state.role_state)]

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def situation_meets_starting_requirements(cls, **kwargs):
        neighbor_sim_id = cls._get_neighbor()
        if neighbor_sim_id is None:
            return False
        return True

    @classmethod
    def get_predefined_guest_list(cls):
        active_sim_info = services.active_sim_info()
        neighbor_sim_id = cls._get_neighbor()
        guest_list = SituationGuestList(invite_only=True, host_sim_id=neighbor_sim_id, filter_requesting_sim_id=active_sim_info.sim_id)
        guest_list.add_guest_info(SituationGuestInfo(neighbor_sim_id, cls.neighbor_job_and_role_state.job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_MEDIUM, expectation_preference=True))
        return guest_list

    @classmethod
    def _get_neighbor(cls):
        active_sim_info = services.active_sim_info()
        neighbors = services.sim_filter_service().submit_filter(cls.neighbor_job_and_role_state.job.filter, callback=None, requesting_sim_info=active_sim_info, allow_yielding=False, blacklist_sim_ids={sim_info.sim_id for sim_info in services.active_household()}, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not neighbors:
            return
        neighbor_sim_infos_at_home = [result.sim_info for result in neighbors if result.sim_info.is_at_home]
        neighbor_sim_id = random.choice(neighbor_sim_infos_at_home).sim_id if neighbor_sim_infos_at_home else None
        return neighbor_sim_id

    def start_situation(self):
        super().start_situation()
        self._change_state(self.check_mail_state())
lock_instance_tunables(NeighborMailboxSituation, exclusivity=BouncerExclusivityCategory.WALKBY, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)