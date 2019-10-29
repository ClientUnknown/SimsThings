from event_testing.test_events import TestEventfrom role.role_state import RoleStatefrom sims4.tuning.tunable import TunableSimMinute, Tunablefrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.complex.hospital_patient_situation import PatientSituationBasefrom situations.complex.patient_situation_base import ArrivingState, WaitingState, TreatedStatefrom situations.situation_complex import SituationState, SituationStateDatafrom situations.situation_guest_list import SituationGuestList, SituationGuestInfoimport servicesimport sims4.logimport telemetry_helperTELEMETRY_GROUP_EMERGENCY = 'EMER'TELEMETRY_EMERGENCY_FAIL = 'EMFL'TELEMETRY_EMERGENCY_SUCCESS = 'EMSU'logger = sims4.log.Logger('Patient_Emergency_Situation', default_owner='rfleig')emergency_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_EMERGENCY)WAITING_TIMEOUT = 'waiting_timeout'
class PatientEmergencySituation(PatientSituationBase):
    INSTANCE_TUNABLES = {'procedure_role_state': RoleState.TunableReference(description='\n            A reference to the hospital patients diagnosed\n            role state while in the situation. This is\n            the state where the patient has been diagnosed \n            but it still waiting for the doctor to treat\n            them.\n            ', tuning_group=PatientSituationBase.JOB_AND_STATE_GROUP, display_name='03_procedure_role_state'), 'procedure_duration_for_time_jump': TunableSimMinute(description='\n            The amount of time allowed to pass before a Sim in the procedure\n            state will be ignored on load with a time jump.\n            ', default=180, tuning_group=PatientSituationBase.TIMEOUT_GROUP), 'force_patient_on_active_career_sim': Tunable(description='\n            If true then the patient will be the active career sim, otherwise\n            we will let the filter service select a sim.\n            ', tunable_type=bool, default=False, tuning_group=PatientSituationBase.JOB_AND_STATE_GROUP)}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, ArrivingState), SituationStateData(2, WaitingState), SituationStateData(3, _ProcedureState), SituationStateData(4, TreatedState))

    def _on_done_waiting(self):
        self._change_state(_ProcedureState())

    @classmethod
    def should_state_type_load_after_time_jump(cls, state_type):
        if not super().should_state_type_load_after_time_jump(state_type):
            return False
        elif state_type is _ProcedureState:
            elapsed_time = services.current_zone().time_elapsed_since_last_save().in_minutes()
            if elapsed_time >= cls.procedure_duration_for_time_jump:
                return False
        return True

    def waiting_expired(self):
        with telemetry_helper.begin_hook(emergency_telemetry_writer, TELEMETRY_EMERGENCY_FAIL) as hook:
            hook.write_guid('type', self.guid64)

    @classmethod
    def get_predefined_guest_list(cls):
        if not cls.force_patient_on_active_career_sim:
            return
        career = services.get_career_service().get_career_in_career_event()
        if career is None:
            return
        guest_list = SituationGuestList(invite_only=True)
        guest_list.add_guest_info(SituationGuestInfo(career.sim_info.sim_id, cls.default_job(), RequestSpawningOption.CANNOT_SPAWN, BouncerRequestPriority.EVENT_VIP))
        return guest_list

class _ProcedureState(SituationState):

    def on_activate(self, reader=None):
        logger.debug('Sim is entering the Procedure State during a doc visit.')
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.situation_job, self.owner.procedure_role_state)
        for custom_key in self.owner.go_to_treated_interactions.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)

    def handle_event(self, sim_info, event, resolver):
        if event is TestEvent.InteractionComplete and (resolver.interaction.has_been_reset or resolver(self.owner.go_to_treated_interactions)):
            with telemetry_helper.begin_hook(emergency_telemetry_writer, TELEMETRY_EMERGENCY_SUCCESS) as hook:
                hook.write_guid('type', self.owner.guid64)
            self._change_state(TreatedState())
