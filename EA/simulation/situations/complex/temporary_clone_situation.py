import servicesimport situationsfrom event_testing.test_events import TestEventfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableSimMinutefrom situations.situation import Situationfrom situations.situation_complex import CommonSituationState, SituationStateData, TunableSituationJobAndRoleState, SituationComplexCommon, CommonInteractionCompletedSituationStatefrom situations.situation_time_jump import SituationTimeJumpSimulate
class _TemporaryCloneState(CommonSituationState):
    FACTORY_TUNABLES = {'time_out': TunableSimMinute(description='\n            How long the clone will last before disappearing.\n            ', default=60, minimum=15), 'locked_args': {'allow_join_situation': True}}

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        self._test_event_register(TestEvent.HouseholdChanged)

    def handle_event(self, sim_info, event, _resolver):
        if event != TestEvent.HouseholdChanged:
            return
        if not self.owner.is_sim_info_in_situation(sim_info):
            return
        if not sim_info.household.hidden:
            self.owner._self_destruct()

    def timer_expired(self):
        self._change_state(self.owner.leave_state())

class _TemporaryCloneLeaveState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'locked_args': {'allow_join_situation': True, 'time_out': None}}

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner.sim_left_lot()

    def _additional_tests(self, sim_info, event, resolver):
        situation = self.owner
        return situation.is_sim_in_situation(situation.get_clone())

class TemporaryCloneSituation(situations.situation_complex.SituationComplexCommon):
    INSTANCE_TUNABLES = {'clone_job_and_role_state': TunableSituationJobAndRoleState(description='\n            Job and Role State for the clone in this situation.\n            '), 'be_clone_state': _TemporaryCloneState.TunableFactory(description='\n            Situation State used by the clone.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'leave_state': _TemporaryCloneLeaveState.TunableFactory(description='\n            Situation State used by the clone to leave the lot.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _TemporaryCloneState, factory=cls.be_clone_state), SituationStateData(2, _TemporaryCloneLeaveState, factory=cls.leave_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.clone_job_and_role_state.job, cls.clone_job_and_role_state.role_state)]

    def start_situation(self):
        super().start_situation()
        self._change_state(self.be_clone_state())

    def load_situation(self):
        clone_guest_info = next(iter(self._guest_list.get_persisted_sim_guest_infos()))
        if clone_guest_info is None:
            return False
        clone_sim_info = services.sim_info_manager().get(clone_guest_info.sim_id)
        if clone_sim_info is None or clone_sim_info.zone_id != services.current_zone_id():
            return False
        if not clone_sim_info.household.hidden:
            return False
        return super().load_situation()

    def _destroy(self):
        zone = services.current_zone()
        if zone is not None and not zone.is_zone_shutting_down:
            clone_sim = self.get_clone()
            self._remove_clone_sim_info(clone_sim)
        super()._destroy()

    @classmethod
    def should_load_after_time_jump(cls, seed):
        elapsed_time = services.time_service().sim_now - seed.start_time
        if elapsed_time.in_minutes() > cls.be_clone_state.time_out:
            clone_sim_info = next(seed.guest_list.invited_sim_infos_gen(), None)
            cls._remove_clone_sim_info(clone_sim_info)
            return False
        return True

    def get_clone(self):
        for sim in self._situation_sims:
            return sim

    def sim_left_lot(self):
        self._register_test_event(TestEvent.ObjectDestroyed)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.ObjectDestroyed:
            destroyed_obj = resolver.get_resolved_arg('obj')
            if destroyed_obj is self.get_clone():
                self._self_destruct()

    @classmethod
    def _remove_clone_sim_info(cls, clone_sim):
        if clone_sim is not None and clone_sim.household.hidden:
            services.sim_info_manager().remove_permanently(clone_sim.sim_info)
lock_instance_tunables(TemporaryCloneSituation, duration=0, time_jump=SituationTimeJumpSimulate())