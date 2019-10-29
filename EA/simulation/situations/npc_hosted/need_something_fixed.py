import randomfrom sims4.tuning.tunable import TunableMappingfrom sims4.tuning.tunable_base import GroupNamesfrom situations.complex.service_npc_situation import TunableFinishJobStateAndTestfrom situations.situation_complex import SituationComplexCommon, SituationStateData, SituationState, CommonInteractionCompletedSituationState, CommonSituationStatefrom situations.situation_guest_list import SituationGuestListfrom situations.situation_job import SituationJobimport enumimport event_testingimport servicesimport sims4WAIT_TO_BE_LET_IN_TIMEOUT = 'wait_to_be_let_in_timeout'logger = sims4.log.Logger('Need Something Fixed Situation', default_owner='shipark')
class RepairNeighborLeaveReason(enum.Int):
    FINISHED_WORK = 0
    ASKED_TO_LEAVE = 1

class RepairArrivalNoDoorState(CommonInteractionCompletedSituationState):

    def _additional_tests(self, sim_info, event, resolver):
        repair_neighbor = self.owner.get_repair_neighbor()
        if repair_neighbor is None:
            return False
        return repair_neighbor.sim_info is sim_info

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.wait_to_be_let_in_state())

    def timer_expired(self):
        services.get_zone_situation_manager().make_sim_leave_now_must_run(self.owner.get_repair_neighbor())
        self.owner._self_destruct()

class RepairArrivalFrontDoorState(CommonInteractionCompletedSituationState):

    def _additional_tests(self, sim_info, event, resolver):
        repair_neighbor = self.owner.get_repair_neighbor()
        if repair_neighbor is None:
            return False
        return repair_neighbor.sim_info is sim_info

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.wait_to_be_let_in_state())

    def timer_expired(self):
        services.get_zone_situation_manager().make_sim_leave_now_must_run(self.owner.get_repair_neighbor())
        self.owner._self_destruct()

class RepairWaitToBeLetInState(CommonInteractionCompletedSituationState):

    def _additional_tests(self, sim_info, event, resolver):
        repair_neighbor = self.owner.get_repair_neighbor()
        if repair_neighbor is None:
            return False
        return repair_neighbor.sim_info is sim_info

    def timer_expired(self):
        services.get_zone_situation_manager().make_sim_leave_now_must_run(self.owner.get_repair_neighbor())
        self.owner._self_destruct()

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.repair_state())

class RepairSituationState(CommonSituationState):

    def _test_event(self, event, sim_info, resolver, test):
        if event in test.test_events:
            return self.owner.test_interaction_complete_by_job_holder(sim_info, resolver, self.owner.default_job(), test)
        return False

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        repair_job_done_state_and_tests = self.owner.repair_job_done_tests
        for (_, repair_job_state) in repair_job_done_state_and_tests.items():
            for (_, custom_key) in repair_job_state.enter_state_test.get_custom_event_registration_keys():
                self._test_event_register(event_testing.test_events.TestEvent.InteractionComplete, custom_key)
                self._test_event_register(event_testing.test_events.TestEvent.InteractionStart, custom_key)

    def handle_event(self, sim_info, event, resolver):
        repair_job_done_tests_and_states = self.owner.repair_job_done_tests
        for (done_reason, repair_job_state) in repair_job_done_tests_and_states.items():
            if self._test_event(event, sim_info, resolver, repair_job_state.enter_state_test):
                self._change_state(RepairLeaveSituationState(sim_info, done_reason))
                break

class RepairLeaveSituationState(SituationState):

    def __init__(self, repair_neighbor_info=None, done_reason=None):
        super().__init__()
        self._done_reason = done_reason

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        self.owner._is_leaving = True
        if reader is None:
            if self._done_reason is not None:
                leave_role_state = self.owner.repair_job_done_tests[self._done_reason].role_state
            repair_neighbor_sim = self.owner.get_repair_neighbor()
            if repair_neighbor_sim is None:
                logger.warn('Repair Neighbor Sim is None for {}.', self)
                return
            if self._done_reason == RepairNeighborLeaveReason.FINISHED_WORK:
                services.get_zone_situation_manager().create_visit_situation(repair_neighbor_sim)
                self.owner._self_destruct()
            elif self._done_reason == RepairNeighborLeaveReason.ASKED_TO_LEAVE:
                services.get_zone_situation_manager().make_sim_leave_now_must_run(repair_neighbor_sim)
                self.owner._self_destruct()
            else:
                if leave_role_state is not None:
                    self.owner._set_job_role_state(self.owner.default_job(), leave_role_state)
                services.get_zone_situation_manager().make_sim_leave_now_must_run(repair_neighbor_sim)
                self.owner._self_destruct()

class NeedSomethingFixedSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'repair_neighbor_job': SituationJob.TunableReference(description='\n            The job for repair neighbor sim in this situation and the corresponding\n            starting role state for service sim.\n            ', tuning_group=GroupNames.SITUATION), 'front_door_repair_arrival': RepairArrivalFrontDoorState.TunableFactory(description='\n            The state in which the repair neighbor arrives when there is not a front door.\n            ', display_name='1. Has Front Door Arrival State', tuning_group=GroupNames.STATE, locked_args={'allow_join_situation': True}), 'no_front_door_repair_arrival': RepairArrivalNoDoorState.TunableFactory(description='\n            The state in which the repair neighbor arrives when there is not a front door.\n            ', display_name='1. Has No Front Door Arrival State', tuning_group=GroupNames.STATE, locked_args={'allow_join_situation': True}), 'wait_to_be_let_in_state': RepairWaitToBeLetInState.TunableFactory(description='\n            Second state of the situation.  In this state the repair neighbor will\n            wait to be let into the house.\n            ', display_name='2. Wait to Be Let in State', tuning_group=GroupNames.STATE, locked_args={'allow_join_situation': True}), 'repair_state': RepairSituationState.TunableFactory(description='\n            ', display_name='3. Repair Situation State', tuning_group=GroupNames.STATE, locked_args={'allow_join_situation': True}), 'repair_job_done_tests': TunableMapping(description='\n            Tune pairs of job finish role states with job finish tests. When\n            those tests pass, the repair neighbor will transition to the paired\n            role state.\n            ', display_name='3. Repair State Job Done Tests', key_name='Leave Reason', key_type=RepairNeighborLeaveReason, value_type=TunableFinishJobStateAndTest(), value_name='Finish Test and Role State', tuning_group=GroupNames.STATE)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._repair_neighbor = None

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._repair_neighbor = sim

    def get_repair_neighbor(self):
        return self._repair_neighbor

    @classmethod
    def default_job(cls):
        return cls.repair_neighbor_job

    @classmethod
    def _states(cls):
        return (SituationStateData.from_auto_factory(1, cls.no_front_door_repair_arrival), SituationStateData.from_auto_factory(2, cls.front_door_repair_arrival), SituationStateData.from_auto_factory(3, cls.wait_to_be_let_in_state), SituationStateData.from_auto_factory(4, cls.repair_state), SituationStateData(5, RepairLeaveSituationState))

    @classmethod
    def get_predefined_guest_list(cls):
        active_sim_info = services.active_sim_info()
        repair_neighbor_results = services.sim_filter_service().submit_filter(cls.repair_neighbor_job.filter, callback=None, requesting_sim_info=active_sim_info, allow_yielding=False, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not repair_neighbor_results:
            return
        repair_neighbor = random.choice(repair_neighbor_results)
        guest_list = SituationGuestList(invite_only=True, host_sim_id=repair_neighbor.sim_info.sim_id, filter_requesting_sim_id=active_sim_info.sim_id)
        return guest_list

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.front_door_repair_arrival._tuned_values.job_and_role_changes.items())

    def start_situation(self):
        super().start_situation()
        if services.get_door_service().has_front_door():
            self._change_state(self.front_door_repair_arrival())
        else:
            self._change_state(self.no_front_door_repair_arrival())
