from builtins import classmethodfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, CommonInteractionCompletedSituationState, SituationStateData, CommonSituationState, SituationStatefrom situations.situation_types import SituationCreationUIOptionimport routingimport services
class _WaitForPetCareWorkerState(SituationState):
    pass

class _PetAccessibleArrivalState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.pet_routes_to_crate_state())

class _PetInaccessibleArrivalState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.pet_routes_to_crate_state())

class _PetRoutesToCrateState(CommonSituationState):

    def on_remove_sim_from_situation(self, sim):
        if self.owner.pet_sim_id == sim.sim_id:
            if self.owner.add_pet_to_adoption_pool:
                adoption_service = services.get_adoption_service()
                adoption_service.add_real_sim_info(sim.sim_info)
            self._change_state(self.owner.leave_state())

class _LeaveState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        sim = self.owner.pet_care_worker_sim()
        if sim is not None:
            services.get_zone_situation_manager().make_sim_leave_now_must_run(sim)
        self.owner._self_destruct()

class PetCareSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'pet_care_worker_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the pet care worker.\n            ', tuning_group=GroupNames.ROLES), 'pet_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the pet being removed from the household.\n            ', tuning_group=GroupNames.ROLES), 'pet_accessible_arrival_state': _PetAccessibleArrivalState.TunableFactory(description='\n            The state for the pet care worker to go to the lot and place the\n            crate object near the pet if the pet care worker can route to the pet.\n            ', display_name='1. Pet Accessible Arrival State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, locked_args={'allow_join_situation': True, 'time_out': None}), 'pet_inaccessible_arrival_state': _PetInaccessibleArrivalState.TunableFactory(description="\n            The state for the pet care worker to go to the lot and place the\n            crate object at the arrival spawn point if the pet care worker can't\n            route to the pet.\n            ", display_name='1. Pet Inaccessible Arrival State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, locked_args={'allow_join_situation': True, 'time_out': None}), 'pet_routes_to_crate_state': _PetRoutesToCrateState.TunableFactory(description='\n            The state for the pet to route to the crate and be removed from the household.\n            ', display_name='2. Pet Routes To Crate State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, locked_args={'allow_join_situation': True, 'time_out': None}), 'leave_state': _LeaveState.TunableFactory(description='\n            The state for the pet care worker to pick up the crate and leave.\n            ', display_name='3. Leave State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, locked_args={'allow_join_situation': True, 'time_out': None}), 'save_lock_tooltip': TunableLocalizedString(description='\n            The tooltip/message to show when the player tries to save the game\n            while this situation is running. Save is locked when situation starts.\n            ', tuning_group=GroupNames.UI), 'add_pet_to_adoption_pool': Tunable(description='\n            If checked, add the pet that was removed from the household to\n            the adoption pool.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.SITUATION)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES
    WAIT_FOR_PET_CARE_WORKER_STATE_UID = 1
    PET_ACCESSIBLE_ARRIVAL_STATE_UID = 2
    PET_INACCESSIBLE_ARRIVAL_STATE_UID = 3
    PET_ROUTES_TO_CRATE_STATE_UID = 4
    LEAVE_STATE_UID = 5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pet_sim_id = 0

    @classmethod
    def _states(cls):
        return (SituationStateData(cls.WAIT_FOR_PET_CARE_WORKER_STATE_UID, _WaitForPetCareWorkerState), SituationStateData(cls.PET_ACCESSIBLE_ARRIVAL_STATE_UID, _PetAccessibleArrivalState, factory=cls.pet_accessible_arrival_state), SituationStateData(cls.PET_INACCESSIBLE_ARRIVAL_STATE_UID, _PetInaccessibleArrivalState, factory=cls.pet_inaccessible_arrival_state), SituationStateData(cls.PET_ROUTES_TO_CRATE_STATE_UID, _PetRoutesToCrateState, factory=cls.pet_routes_to_crate_state), SituationStateData(cls.LEAVE_STATE_UID, _LeaveState, factory=cls.leave_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.pet_care_worker_job_and_role_state.job, cls.pet_care_worker_job_and_role_state.role_state), (cls.pet_job_and_role_state.job, cls.pet_job_and_role_state.role_state)]

    @classmethod
    def default_job(cls):
        pass

    @property
    def pet_sim_id(self):
        return self._pet_sim_id

    def _on_add_sim_to_situation(self, *args, **kwargs):
        super()._on_add_sim_to_situation(*args, **kwargs)
        pet_care_worker = self.pet_care_worker_sim()
        pet = self.pet_sim()
        if pet_care_worker is not None and pet is not None:
            if routing.test_connectivity_pt_pt(pet_care_worker.routing_location, pet.routing_location, pet_care_worker.routing_context):
                self._change_state(self.pet_accessible_arrival_state())
            else:
                self._change_state(self.pet_inaccessible_arrival_state())

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        if job_type is self.pet_job_and_role_state.job:
            self._pet_sim_id = sim.sim_id

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        if self._cur_state is not None and self._state_to_uid(self._cur_state) == PetCareSituation.PET_ROUTES_TO_CRATE_STATE_UID:
            self._cur_state.on_remove_sim_from_situation(sim)

    def pet_care_worker_sim(self):
        sim = next(self.all_sims_in_job_gen(self.pet_care_worker_job_and_role_state.job), None)
        return sim

    def pet_sim(self):
        pet = next(self.all_sims_in_job_gen(self.pet_job_and_role_state.job), None)
        return pet

    def _destroy(self):
        super()._destroy()
        services.get_persistence_service().unlock_save(self)

    def start_situation(self):
        services.get_persistence_service().lock_save(self)
        super().start_situation()
        self._change_state(_WaitForPetCareWorkerState())

    def get_lock_save_reason(self):
        return self.save_lock_tooltip
lock_instance_tunables(PetCareSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0)