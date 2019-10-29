import randomfrom objects.system import create_objectfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableList, TunableReferencefrom situations.bouncer.bouncer_types import BouncerExclusivityCategory, BouncerRequestPriority, RequestSpawningOptionfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, CommonSituationState, SituationStateDatafrom situations.situation_guest_list import SituationGuestInfo, SituationGuestListfrom situations.situation_types import SituationCreationUIOptionimport servicesTRASH_TOKEN = 'trash_id'
class _TakeOutTrashState(CommonSituationState):

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        if self.owner._trash_id is not None:
            target = services.current_zone().inventory_manager.get(self.owner._trash_id)
        else:
            trash_to_create = random.choice(self.owner.trash_objects_to_create)
            target = self.owner._create_object_for_situation(sim, trash_to_create)
            self.owner._trash_id = target.id
        return (role_state_type, target)

class NeighborTrashChuteSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'take_out_trash_state': _TakeOutTrashState.TunableFactory(description='\n            Situation State for the Sim to take out the trash.\n            '), 'neighbor_job_and_role_state': TunableSituationJobAndRoleState(description='\n            Job and Role State for the neighbor.\n            '), 'trash_objects_to_create': TunableList(description='\n            A list of objects to randomly pick from for this type of neighbor. When\n            the neighbor enters the state to take out trash, we randomly create one\n            of these objects and pass it to the role affordances as the target.\n            ', tunable=TunableReference(description='\n                An object to create.', manager=services.definition_manager()))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        reader = self._seed.custom_init_params_reader
        self._trash_id = self._load_object(reader, TRASH_TOKEN, claim=True)

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _TakeOutTrashState, factory=cls.take_out_trash_state),)

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
        if neighbor_sim_id is None:
            return
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

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.neighbor_job_and_role_state.job, cls.neighbor_job_and_role_state.role_state)]

    def start_situation(self):
        super().start_situation()
        self._change_state(self.take_out_trash_state())

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._trash_id is not None:
            writer.write_uint64(TRASH_TOKEN, self._trash_id)
lock_instance_tunables(NeighborTrashChuteSituation, exclusivity=BouncerExclusivityCategory.WALKBY, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)