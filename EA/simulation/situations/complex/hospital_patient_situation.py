from event_testing.test_events import TestEventfrom role.role_state import RoleStatefrom sims4.tuning.tunable import TunableSimMinute, Tunablefrom situations.complex.patient_situation_base import PatientSituationBase, ArrivingState, WaitingState, TreatedStatefrom situations.situation_complex import SituationState, TunableInteractionOfInterest, SituationStateDataimport servicesimport sims4.loglogger = sims4.log.Logger('Doctor', default_owner='rfleig')
class HospitalPatientSituation(PatientSituationBase):
    INSTANCE_TUNABLES = {'admitted_role_state': RoleState.TunableReference(description='\n            A reference to the hospital patients admitted\n            role state while in the situation. This is the\n            state where the patient is assigned to a bed \n            and the doctor is actively trying to diagnose\n            the issue.\n            ', tuning_group=PatientSituationBase.JOB_AND_STATE_GROUP, display_name='03_admitted_role_state'), 'diagnosed_role_state': RoleState.TunableReference(description='\n            A reference to the hospital patients diagnosed\n            role state while in the situation. This is\n            the state where the patient has been diagnosed \n            but it still waiting for the doctor to treat\n            them.\n            ', tuning_group=PatientSituationBase.JOB_AND_STATE_GROUP, display_name='04_diagnosed_role_state'), 'go_to_diagnosed_interactions': TunableInteractionOfInterest(description='\n            The interactions to look for when a Sim has been diagnosed by a \n            doctor and is now waiting for treatment.\n            ', tuning_group=PatientSituationBase.STATE_ADVANCEMENT_GROUP), 'admitted_duration_for_time_jump': TunableSimMinute(description='\n            The amount of time allowed to pass before a Sim in the admitted\n            state will be ignored on load with a time jump.\n            ', default=180, tuning_group=PatientSituationBase.TIMEOUT_GROUP), 'diagnosed_duration_for_time_jump': TunableSimMinute(description='\n            The amount of time allowed to pass before a Sim in the diagnosed\n            state will be ignored on load with a time jump.\n            ', default=180, tuning_group=PatientSituationBase.TIMEOUT_GROUP), 'pre_diagnosed': Tunable(description='\n            If this is true then when the Sim is pre-rolled it will skip to the\n            _DiagnosedState(). \n            \n            If it is False then it will default to pre-rolling\n            the Sim to _AdmittedState().\n            ', tunable_type=bool, default=False)}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, ArrivingState), SituationStateData(2, WaitingState), SituationStateData(3, _AdmittedState), SituationStateData(4, _DiagnosedState), SituationStateData(5, TreatedState))

    def _skip_ahead_for_preroll(self):
        if self.pre_diagnosed:
            self._change_state(_DiagnosedState())
        else:
            self._change_state(_AdmittedState())

    def _on_done_waiting(self):
        self._change_state(_AdmittedState())

    @classmethod
    def should_state_type_load_after_time_jump(cls, state_type):
        if not super().should_state_type_load_after_time_jump(state_type):
            return False
        else:
            elapsed_time = services.current_zone().time_elapsed_since_last_save().in_minutes()
            if state_type is _AdmittedState:
                timeout = cls.admitted_duration_for_time_jump
            elif state_type is _DiagnosedState:
                timeout = cls.diagnosed_duration_for_time_jump
            else:
                timeout = None
            if timeout is not None and elapsed_time >= timeout:
                return False
        return True

class _AdmittedState(SituationState):

    def on_activate(self, reader=None):
        logger.debug('Sim is entering the Admitted State during a doc visit.')
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.situation_job, self.owner.admitted_role_state)
        for custom_key in self.owner.go_to_diagnosed_interactions.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)

    def handle_event(self, sim_info, event, resolver):
        patient = self.owner.get_patient()
        if event is TestEvent.InteractionComplete and (patient is not None and sim_info is patient.sim_info) and (resolver.interaction.has_been_reset or resolver(self.owner.go_to_diagnosed_interactions)):
            self._change_state(_DiagnosedState())

class _DiagnosedState(SituationState):

    def on_activate(self, reader=None):
        logger.debug('Sim is entering the Diagnosed State during a doc visit.')
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.situation_job, self.owner.diagnosed_role_state)
        for custom_key in self.owner.go_to_treated_interactions.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)

    def handle_event(self, sim_info, event, resolver):
        patient = self.owner.get_patient()
        if event is TestEvent.InteractionComplete and (patient is not None and sim_info is patient.sim_info) and (resolver.interaction.has_been_reset or resolver(self.owner.go_to_treated_interactions)):
            self._change_state(TreatedState())
