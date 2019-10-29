from sims4.tuning.tunable import TunableReferencefrom situations.situation import Situationfrom situations.situation_complex import CommonInteractionCompletedSituationState, CommonSituationState, SituationStateData, TunableSituationJobAndRoleState, SituationComplexCommon, CommonInteractionStartedSituationStateimport servicesimport sims4.tuning.instancesWATER_SCOOTER_TOKEN = 'water_scooter_id'
class _DeployWaterScooterState(CommonInteractionCompletedSituationState):

    def _on_set_sim_role_state(self, sim, job_type, role_state_type, role_affordance_target):
        water_scooter_obj = self.owner._create_object_for_situation(sim, self.owner.water_scooter_object_def)
        self.owner._water_scooter_object_id = water_scooter_obj.id

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.get_on_water_scooter_state())

    def timer_expired(self):
        self._change_state(self.owner.put_in_inventory_state())

class _GetOnWaterScooterState(CommonInteractionStartedSituationState):

    def _on_interaction_of_interest_started(self, **kwargs):
        self._change_state(self.owner.ride_around_state())

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        if self.owner.water_scooter is None:
            self._change_state(self.owner.leave_state())
            return (role_state_type, role_affordance_target)
        else:
            return (role_state_type, self.owner.water_scooter)

    def timer_expired(self):
        self._change_state(self.owner.put_in_inventory_state())

class _RideAroundState(CommonSituationState):

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        if self.owner.water_scooter is None:
            self._change_state(self.owner.leave_state())
            return (role_state_type, role_affordance_target)
        else:
            return (role_state_type, self.owner.water_scooter)

    def timer_expired(self):
        self._change_state(self.owner.put_in_inventory_state())

class _PutInInventoryState(CommonInteractionCompletedSituationState):

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        if self.owner.water_scooter is None:
            self._change_state(self.owner.leave_state())
            return (role_state_type, role_affordance_target)
        else:
            return (role_state_type, self.owner.water_scooter)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.leave_state())

    def timer_expired(self):
        self._change_state(self.owner.leave_state())

class _LeaveState(CommonSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        water_scooter = self.owner.water_scooter
        if water_scooter is not None:
            water_scooter.destroy()

class SituationWaterScooterWalkby(SituationComplexCommon):
    INSTANCE_TUNABLES = {'job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role for the one sim involved in the situation.\n            '), 'water_scooter_object_def': TunableReference(description="\n            The definition of the water scooter to spawn in the sim's inventory \n            ", manager=services.definition_manager(), pack_safe=True, allow_none=False), 'deploy_water_scooter_state': _DeployWaterScooterState.TunableFactory(description='\n            The state in which the sim deploys the water scooter then transitions\n            to the get-on-water-scooter state. If the sim fails to complete the\n            interaction within a given timeout, the sim will transition immediately\n            to the leave state.\n            ', display_name='1. Deploy Water Scooter State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'get_on_water_scooter_state': _GetOnWaterScooterState.TunableFactory(description='\n            The state in which the sim gets on the water scooter then transitions\n            to the ride-around-state.\n            ', display_name='2. Get on Water Scooter State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'ride_around_state': _RideAroundState.TunableFactory(description='\n            The state in which the sim rides around in the water scooter for some\n            tuned amount of time.\n            ', display_name='3. Ride Around State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'put_in_inventory_state': _PutInInventoryState.TunableFactory(description='\n            The state in which the sim puts the water scooter back in their inventory.\n            ', display_name='4. Put in Inventory State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'leave_state': _LeaveState.TunableFactory(description='\n            The state in which the sim leaves the situation.\n            ', display_name='5. Leave State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reader = self._seed.custom_init_params_reader
        self._water_scooter_object_id = self._load_object(reader, WATER_SCOOTER_TOKEN, claim=True)

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._water_scooter_object_id is not None:
            writer.write_uint64(WATER_SCOOTER_TOKEN, self._water_scooter_object_id)

    def start_situation(self):
        super().start_situation()
        self._change_state(self.deploy_water_scooter_state())

    def on_remove(self):
        super().on_remove()
        water_scooter = self.water_scooter
        if water_scooter is not None:
            water_scooter.destroy()

    def _get_remaining_time_for_gsi(self):
        if self._cur_state is not None:
            return self._cur_state._get_remaining_alarm_time(self._cur_state._time_out_string)
        else:
            return super()._get_remaining_time_for_gsi()

    @property
    def water_scooter(self):
        water_scooter = None
        if self._water_scooter_object_id is not None:
            water_scooter = services.object_manager().get(self._water_scooter_object_id)
            if water_scooter is None:
                water_scooter = services.inventory_manager().get(self._water_scooter_object_id)
        return water_scooter

    @classmethod
    def default_job(cls):
        return cls.job_and_role.job

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.job_and_role.job, cls.job_and_role.role_state)]

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return 1

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _DeployWaterScooterState, factory=cls.deploy_water_scooter_state), SituationStateData(2, _GetOnWaterScooterState, factory=cls.get_on_water_scooter_state), SituationStateData(3, _RideAroundState, factory=cls.ride_around_state), SituationStateData(4, _PutInInventoryState, factory=cls.put_in_inventory_state), SituationStateData(5, _LeaveState, factory=cls.leave_state))
sims4.tuning.instances.lock_instance_tunables(SituationWaterScooterWalkby, duration=0)