from event_testing.test_events import TestEventfrom objects.system import create_objectfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableEnumWithFilter, TunableReference, Tunablefrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import CommonInteractionCompletedSituationState, SituationComplexCommon, TunableSituationJobAndRoleState, CommonSituationState, SituationStateDatafrom situations.situation_types import SituationCreationUIOptionfrom tag import Tagimport placementimport servicesimport sims4.math
class _HasFrontDoorArrivalState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.spawn_pets_state())

    def on_set_sim_job(self, sim, job):
        pass

    def on_remove_sim_from_situation(self, sim):
        pass

class _HasNoFrontDoorArrivalState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.spawn_pets_state())

    def on_set_sim_job(self, sim, job):
        pass

    def on_remove_sim_from_situation(self, sim):
        pass

class _SpawnPetsState(CommonSituationState):
    FACTORY_TUNABLES = {'spawn_offset': Tunable(description='\n            The offset from the center of the crate in the forward direction\n            that is used as the starting location to fgl for pets to spawn.\n            ', tunable_type=float, default=1.0)}

    def __init__(self, spawn_offset, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pets_to_spawn = []
        self._spawn_offset = spawn_offset

    def on_activate(self, reader=None):
        super().on_activate(reader)
        pet_crate_object = self.owner.pet_crate
        pet_crate_position = pet_crate_object.position + pet_crate_object.forward*self._spawn_offset if pet_crate_object is not None else None
        for guest_info in self.owner._guest_list.get_guest_infos_for_job(self.owner.pet_adoption_candidate_job_and_role.job):
            self.owner._fulfill_reservation_guest_info(guest_info, position_override=pet_crate_position)

    def on_set_sim_job(self, sim, job):
        if sim.sim_id in self._pets_to_spawn:
            self._pets_to_spawn.remove(sim.sim_id)
        if not self._pets_to_spawn:
            self._change_state(self.owner.interact_with_pets_state())

    def on_remove_sim_from_situation(self, sim):
        pass

class _InteractWithPetsState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.wait_for_pets_to_despawn_state())

    def timer_expired(self):
        self._change_state(self.owner.wait_for_pets_to_despawn_state())

    def on_set_sim_job(self, sim, job):
        pass

    def on_remove_sim_from_situation(self, sim):
        if not any(self.owner.all_sims_in_job_gen(self.owner.pet_adoption_candidate_job_and_role.job)):
            if self.owner.pet_crate is None:
                self._change_state(self.owner.leave_state())
            else:
                self._change_state(self.owner.pick_up_adoption_crate_state())

class _WaitForPetsToDespawnState(CommonSituationState):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pets_to_despawn = []

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._pets_to_despawn = [sim.sim_id for sim in self.owner.all_sims_in_job_gen(self.owner.pet_adoption_candidate_job_and_role.job)]

    def on_set_sim_job(self, sim, job):
        pass

    def on_remove_sim_from_situation(self, sim):
        if sim.sim_id in self._pets_to_despawn:
            self._pets_to_despawn.remove(sim.sim_id)
        if not self._pets_to_despawn:
            if self.owner.pet_crate is None:
                self._change_state(self.owner.leave_state())
            else:
                self._change_state(self.owner.pick_up_adoption_crate_state())

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        if job_type is not self.owner.pet_adoption_candidate_job_and_role.job:
            return (role_state_type, role_affordance_target)
        return (role_state_type, self.owner.pet_crate)

class _PickUpAdoptionCrateState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.leave_state())

    def on_set_sim_job(self, sim, job):
        pass

    def on_remove_sim_from_situation(self, sim):
        pass

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._test_event_register(TestEvent.OnExitBuildBuy)
        self.owner.remove_destruction_listener()

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.OnExitBuildBuy and self.owner.pet_crate is None:
            self._change_state(self.owner.leave_state())

class _LeaveState(CommonSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        sim = self.owner.adoption_officer_sim()
        if sim is not None:
            services.get_zone_situation_manager().make_sim_leave_now_must_run(sim)
        self.owner._self_destruct()

    def on_set_sim_job(self, sim, job):
        pass

    def on_remove_sim_from_situation(self, sim):
        pass

class SituationComplexAdoption(SituationComplexCommon):
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES
PET_CRATE_X = 'pet_crate_x'PET_CRATE_Y = 'pet_crate_y'PET_CRATE_Z = 'pet_crate_z'
class SituationComplexAdoptionPet(SituationComplexAdoption):
    INSTANCE_TUNABLES = {'adoption_officer_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role state for the pet adoption officer.\n            '), 'pet_adoption_candidate_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role state for the pets that are adoption candidates.\n            '), 'has_front_door_arrival_state': _HasFrontDoorArrivalState.TunableFactory(description='\n            The arrival state for the adoption officer if the lot has a front\n            door.\n            ', display_name='1. Has Front Door Arrival State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'has_no_front_door_arrival_state': _HasNoFrontDoorArrivalState.TunableFactory(description='\n            The arrival state for the adoption officer if the lot does not have\n            a front door.\n            ', display_name='1. Has No Front Door Arrival State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'spawn_pets_state': _SpawnPetsState.TunableFactory(description='\n            The state in which adoption candidate pets are spawned.\n            ', display_name='2. Spawn Pets State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'interact_with_pets_state': _InteractWithPetsState.TunableFactory(description='\n            The state for Sims to interact with adoption candidate pets.\n            ', display_name='3. Interact With Pets State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'wait_for_pets_to_despawn_state': _WaitForPetsToDespawnState.TunableFactory(description='\n            The state where any adoption candidate pets that were not adopted\n            are despawned.\n            ', display_name='4. Wait For Pets To Despawn State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'pick_up_adoption_crate_state': _PickUpAdoptionCrateState.TunableFactory(description='\n            The state for the adoption officer to pick up the adoption crate.\n            ', display_name='5. Pick Up Adoption Crate State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'leave_state': _LeaveState.TunableFactory(description='\n            The state for the adoption officer to leave.\n            ', display_name='6. Leave State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'pet_crate_tag': TunableEnumWithFilter(description='\n            Tag used to find the pet crate object.\n            ', tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), filter_prefixes=('func',)), 'pet_crate_object_definition': TunableReference(description='\n            Object definition of the pet crate object that will be created as\n            part of this situation.\n            ', manager=services.definition_manager())}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pet_crate_object_id = None
        reader = self._seed.custom_init_params_reader
        if reader is None:
            self._pet_crate_x = None
            self._pet_crate_y = None
            self._pet_crate_z = None
        else:
            self._pet_crate_x = reader.read_float(PET_CRATE_X, None)
            self._pet_crate_y = reader.read_float(PET_CRATE_Y, None)
            self._pet_crate_z = reader.read_float(PET_CRATE_Z, None)
        self._register_test_event(TestEvent.OnExitBuildBuy)
        self._register_test_event(TestEvent.ObjectDestroyed)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.OnExitBuildBuy:
            if self.pet_crate is None:
                self._restore_crate()
            self._pet_crate_x = None
            self._pet_crate_y = None
            self._pet_crate_z = None
        if services.current_zone().is_in_build_buy:
            destroyed_obj = resolver.get_resolved_arg('obj')
            if destroyed_obj is self.pet_crate:
                position = destroyed_obj.position
                self._pet_crate_x = position.x
                self._pet_crate_y = position.y
                self._pet_crate_z = position.z

    def remove_destruction_listener(self):
        self._unregister_test_event(TestEvent.ObjectDestroyed)

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _HasFrontDoorArrivalState, factory=cls.has_front_door_arrival_state), SituationStateData(2, _HasNoFrontDoorArrivalState, factory=cls.has_no_front_door_arrival_state), SituationStateData(3, _SpawnPetsState, factory=cls.spawn_pets_state), SituationStateData(4, _InteractWithPetsState, factory=cls.interact_with_pets_state), SituationStateData(5, _WaitForPetsToDespawnState, factory=cls.wait_for_pets_to_despawn_state), SituationStateData(6, _PickUpAdoptionCrateState, factory=cls.pick_up_adoption_crate_state), SituationStateData(7, _LeaveState, factory=cls.leave_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.adoption_officer_job_and_role.job, cls.adoption_officer_job_and_role.role_state), (cls.pet_adoption_candidate_job_and_role.job, cls.pet_adoption_candidate_job_and_role.role_state)]

    @classmethod
    def default_job(cls):
        pass

    @property
    def pet_crate(self):
        object_manager = services.object_manager()
        pet_crate = None
        if self._pet_crate_object_id is not None:
            pet_crate = object_manager.get(self._pet_crate_object_id)
        if pet_crate is None:
            for obj in services.object_manager().get_objects_with_tag_gen(self.pet_crate_tag):
                pet_crate = obj
                self._pet_crate_object_id = pet_crate.id
                break
        return pet_crate

    def _on_set_sim_job(self, sim, job):
        super()._on_set_sim_job(sim, job)
        self._cur_state.on_set_sim_job(sim, job)

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        if self._cur_state is not None:
            self._cur_state.on_remove_sim_from_situation(sim)

    def adoption_officer_sim(self):
        sim = next(self.all_sims_in_job_gen(self.adoption_officer_job_and_role.job), None)
        return sim

    def adoptee_pets_gen(self):
        yield from self.all_sims_in_job_gen(self.pet_adoption_candidate_job_and_role.job)

    def start_situation(self):
        super().start_situation()
        if services.get_door_service().has_front_door():
            self._change_state(self.has_front_door_arrival_state())
        else:
            self._change_state(self.has_no_front_door_arrival_state())

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        pet_crate = self.pet_crate
        if pet_crate is not None:
            position = pet_crate.position
            writer.write_float(PET_CRATE_X, position.x)
            writer.write_float(PET_CRATE_Y, position.y)
            writer.write_float(PET_CRATE_Z, position.z)

    def load_situation(self):
        result = super().load_situation()
        if result:
            self._restore_crate()
            self._pet_crate_x = None
            self._pet_crate_y = None
            self._pet_crate_z = None
        return result

    def _restore_crate(self):
        if self._pet_crate_x is None:
            return
        obj = create_object(self.pet_crate_object_definition)
        if obj is None:
            return
        position = sims4.math.Vector3(float(self._pet_crate_x), float(self._pet_crate_y), float(self._pet_crate_z))
        starting_location = placement.create_starting_location(position=position)
        fgl_context = placement.create_fgl_context_for_object(starting_location, obj, ignored_object_ids=(obj.id,))
        (position, orientation) = placement.find_good_location(fgl_context)
        if position is not None and orientation is not None:
            obj.move_to(translation=position, orientation=orientation)
        else:
            obj.destroy()
lock_instance_tunables(SituationComplexAdoptionPet, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)