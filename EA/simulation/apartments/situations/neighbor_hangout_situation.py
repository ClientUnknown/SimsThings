import randomfrom event_testing.tests import TunableTestSetfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable_base import GroupNamesfrom situations.base_situation import _RequestUserDatafrom situations.bouncer.bouncer_request import SelectableSimRequestFactoryfrom situations.bouncer.bouncer_types import BouncerExclusivityCategory, RequestSpawningOption, BouncerRequestPriorityfrom situations.situation_complex import SituationComplexCommon, SituationStateData, CommonSituationState, CommonInteractionCompletedSituationState, TunableSituationJobAndRoleStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_types import SituationCreationUIOptionimport servicesfrom event_testing.resolver import DoubleSimResolver
class _RingDoorbellState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner._wait_to_be_greeted_state())

class _NeighborWaitToBeGreetedState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner._hangout_state())

class _NeighborHangoutState(CommonSituationState):
    pass

class NeighborHangoutSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'player_sim_job_and_default_role_state': TunableSituationJobAndRoleState(description='\n            The Situation Job and role stateto put player Sims in. \n            '), 'neighbor_job_and_default_role_state': TunableSituationJobAndRoleState(description='\n            The Situation Job and Role State for the neighbor.\n            '), '_ring_doorbell_state': _RingDoorbellState.TunableFactory(description="\n            The state for the neighbor to ring the player's doorbell.\n            ", tuning_group=GroupNames.STATE), '_wait_to_be_greeted_state': _NeighborWaitToBeGreetedState.TunableFactory(description='\n            The state for the neighbor to wait until the player invites them in\n            or they timeout.\n            ', tuning_group=GroupNames.STATE), '_hangout_state': _NeighborHangoutState.TunableFactory(description='\n            The state for the neighbor to come in and hang out with the player.\n            ', tuning_group=GroupNames.STATE), 'scheduling_tests': TunableTestSet(description="\n            Tunable tests that run before scheduling this situation. If they\n            pass, the situation is weighed and considered for scheduling.\n            Otherwise it does not take up a slot in the situation manager\n            because the zone director won't consider it.\n            Participants: Actor = active sim, TargetSim = Sim from Job filter.\n            Tests fail if TargetSim is None.\n            ")}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _RingDoorbellState, factory=cls._ring_doorbell_state), SituationStateData(2, _NeighborWaitToBeGreetedState, factory=cls._wait_to_be_greeted_state), SituationStateData(3, _NeighborHangoutState, factory=cls._hangout_state))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def situation_meets_starting_requirements(cls, **kwargs):
        owning_household = services.owning_household_of_active_lot()
        if owning_household is None or not owning_household.get_sims_at_home():
            return False
        neighbor_results = cls.get_filter_results_for_job()
        if not neighbor_results:
            return False
        else:
            for neighbor_result in neighbor_results:
                resolver = DoubleSimResolver(services.active_sim_info(), neighbor_result.sim_info)
                if cls.scheduling_tests.run_tests(resolver):
                    break
            return False
        return True

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.neighbor_job_and_default_role_state.job, cls.neighbor_job_and_default_role_state.role_state), (cls.player_sim_job_and_default_role_state.job, cls.player_sim_job_and_default_role_state.role_state)]

    @classmethod
    def get_filter_results_for_job(cls):
        active_sim_info = services.active_sim_info()
        neighbor_results = services.sim_filter_service().submit_filter(cls.neighbor_job_and_default_role_state.job.filter, callback=None, requesting_sim_info=active_sim_info, allow_yielding=False, blacklist_sim_ids={sim_info.sim_id for sim_info in services.active_household()}, gsi_source_fn=cls.get_sim_filter_gsi_name)
        return neighbor_results

    @classmethod
    def get_predefined_guest_list(cls):
        active_sim_info = services.active_sim_info()
        neighbor_results = cls.get_filter_results_for_job()
        if not neighbor_results:
            return
        neighbor = random.choice(neighbor_results)
        guest_list = SituationGuestList(invite_only=True, host_sim_id=neighbor.sim_info.sim_id, filter_requesting_sim_id=active_sim_info.sim_id)
        guest_list.add_guest_info(SituationGuestInfo(neighbor.sim_info.sim_id, cls.neighbor_job_and_default_role_state.job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP, expectation_preference=True))
        return guest_list

    def start_situation(self):
        super().start_situation()
        self._change_state(self._ring_doorbell_state())

    def _issue_requests(self):
        super()._issue_requests()
        request = SelectableSimRequestFactory(self, callback_data=_RequestUserData(), job_type=self.player_sim_job_and_default_role_state.job, exclusivity=self.exclusivity)
        self.manager.bouncer.submit_request(request)
lock_instance_tunables(NeighborHangoutSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)