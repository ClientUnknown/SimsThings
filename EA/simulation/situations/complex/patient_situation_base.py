from event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom role.role_state import RoleStatefrom sims4.tuning.tunable import TunableReference, TunableSimMinute, Tunable, OptionalTunable, TunableTuplefrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationState, TunableInteractionOfInterestfrom situations.situation_job import SituationJobfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport servicesimport sims4.loglogger = sims4.log.Logger('Doctor', default_owner='rfleig')WAITING_TIMEOUT = 'waiting_timeout'
class PatientSituationBase(SituationComplexCommon):
    JOB_AND_STATE_GROUP = 'Job and State'
    STATE_ADVANCEMENT_GROUP = 'State Advancement'
    TIMEOUT_GROUP = 'Timeout And Time Jump'
    INSTANCE_TUNABLES = {'situation_job': SituationJob.TunableReference(description='\n            A reference to the doctors Job while in the\n            situation.\n            ', tuning_group=JOB_AND_STATE_GROUP), 'waiting_role_state': RoleState.TunableReference(description='\n            A reference to the hospital patients waiting \n            role state while in the situation. At this \n            point the patient is just chilling in the \n            waiting room till the doctor (or nurse) takes\n            them back to a room.\n            ', tuning_group=JOB_AND_STATE_GROUP, display_name='02_waiting_role_state'), 'treated_role_state': RoleState.TunableReference(description='\n            A reference to the hospital patients treated\n            role state while in the situation. This is\n            the state where the patient has finished their \n            visit to the doctor and most likely only goes\n            home.\n            ', tuning_group=JOB_AND_STATE_GROUP, display_name='05_treated_role_state'), 'arriving_state': OptionalTunable(description='\n            If this is enabled then the situation will start out in the\n            arriving state and will use the go_to_waiting_interactions to move\n            from arriving to waiting.\n            \n            If this is disabled then the situation will start in the waiting\n            state.\n            ', tunable=TunableTuple(go_to_waiting_interactions=TunableInteractionOfInterest(description='\n                    The interactions to look for when a Sim has checked in with \n                    admitting and is now waiting for the doctor to take them to a bed.\n                    '), arriving_role_state=RoleState.TunableReference(description="\n                    A reference to the hospital patient's basic \n                    arriving role state while in the situation.\n                    \n                    e.g. This is when the patient walks up to the \n                    admitting desk and checks in and then changes\n                    to the waiting state.\n                    ")), enabled_by_default=True, tuning_group=JOB_AND_STATE_GROUP, display_name='01_arriving_state'), 'go_to_admitted_interactions': TunableInteractionOfInterest(description='\n            The interactions to look for when a Sim has completed waiting \n            successfully and will now be admitted.\n            ', tuning_group=STATE_ADVANCEMENT_GROUP), 'go_to_treated_interactions': TunableInteractionOfInterest(description='\n            The interactions to look for when a Sim has been treated for illness\n            and their visit to the doctor is now over.\n            ', tuning_group=STATE_ADVANCEMENT_GROUP), 'patient_type_buff': TunableReference(description='\n            A buff used to mark the type of patient the Sim in this situation\n            will be. \n            \n            This buff is where you can tune weights and types of\n            diseases the Sim could get as part of the situation.\n            ', manager=services.get_instance_manager(sims4.resources.Types.BUFF)), 'trigger_symptom_loot': TunableReference(description='\n            The loot to apply to the Sim that triggers them to get a symptom.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), allow_none=True, class_restrictions=('LootActions',)), 'waiting_timeout': TunableSimMinute(description='\n            The amount of time the sim will wait before leaving.\n            ', default=180, tuning_group=TIMEOUT_GROUP), 'waiting_timedout_notification': OptionalTunable(description='\n            When enabled, if the Sim in the situation times out a notification\n            will be displayed letting the player know that they are leaving.\n            ', tunable=TunableUiDialogNotificationSnippet(description='\n                The notification that is displayed whenever a Sim times out while\n                waiting and leaves the lot.\n                '), enabled_by_default=True, tuning_group=TIMEOUT_GROUP), 'waiting_timedout_performance_penalty': Tunable(description='\n            This is the amount of perfomance to add to the Sims work\n            performance when this situation times out while the Sim is waiting.\n            \n            To have this negatively affect the peformance you would use a \n            negative number like -10. Using a positive number will result in \n            it being added to the Sims performance.\n            ', tunable_type=int, default=0, tuning_group=TIMEOUT_GROUP), 'force_sim_to_leave_lot_on_completion': Tunable(description='\n            If set to True then when a Sim completes the situation, whether\n            by timeout or successful completion, the Sim will be forced to \n            leave the lot immediately.\n            \n            If this is set to False then when the situation is completed it\n            will be destroyed without the sim being forced off lot.\n            ', tunable_type=bool, default=True, tuning_group=STATE_ADVANCEMENT_GROUP)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._patient = None

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        if cls.arriving_state is not None:
            return [(cls.situation_job, cls.arriving_state.arriving_role_state)]
        return [(cls.situation_job, cls.waiting_role_state)]

    @classmethod
    def default_job(cls):
        return cls.situation_job

    @classmethod
    def get_tuned_jobs(cls):
        return {cls.situation_job}

    def start_situation(self):
        super().start_situation()
        reader = self._seed.custom_init_params_reader
        if reader is None and not services.current_zone().is_zone_running:
            self._skip_ahead_for_preroll()
        elif self.arriving_state:
            self._change_state(ArrivingState())
        else:
            self._change_state(WaitingState())

    def add_patient_type_buff(self, sim):
        if self.patient_type_buff is not None:
            sim.add_buff(self.patient_type_buff)
        if self.trigger_symptom_loot is not None:
            resolver = SingleSimResolver(sim.sim_info)
            self.trigger_symptom_loot.apply_to_resolver(resolver)

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._patient = sim

    def _on_add_sim_to_situation(self, sim, job_type, role_state_type_override=None):
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override=role_state_type_override)
        self.add_patient_type_buff(sim)

    def get_patient(self):
        return self._patient

    def _on_done_waiting(self):
        self._change_state(TreatedState())

    @classmethod
    def should_load_after_time_jump(cls, seed):
        state_type = cls.get_current_state_type(seed)
        return cls.should_state_type_load_after_time_jump(state_type)

    @classmethod
    def should_state_type_load_after_time_jump(cls, state_type):
        if state_type is None or state_type is ArrivingState or state_type is TreatedState:
            return False
        elif state_type is WaitingState:
            elapsed_time = services.current_zone().time_elapsed_since_last_save().in_minutes()
            if elapsed_time >= cls.waiting_timeout:
                return False
        return True

    def _skip_ahead_for_preroll(self):
        self._change_state(WaitingState())

    def waiting_expired(self):
        pass

    def _on_remove_sim_from_situation(self, sim):
        sim_job = self.get_current_job_for_sim(sim)
        super()._on_remove_sim_from_situation(sim)
        self.manager.add_sim_to_auto_fill_blacklist(sim.id, sim_job)

class ArrivingState(SituationState):

    def on_activate(self, reader=None):
        logger.debug('Sim is entering the Arriving State during a doc visit.')
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.situation_job, self.owner.arriving_state.arriving_role_state)
        for custom_key in self.owner.arriving_state.go_to_waiting_interactions.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)

    def handle_event(self, sim_info, event, resolver):
        patient = self.owner.get_patient()
        if event is TestEvent.InteractionComplete and (patient is not None and sim_info is patient.sim_info) and resolver(self.owner.arriving_state.go_to_waiting_interactions):
            self._change_state(WaitingState())

class WaitingState(SituationState):

    def on_activate(self, reader=None):
        logger.debug('Sim is entering the Waiting State during a doc visit.')
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.situation_job, self.owner.waiting_role_state)
        for custom_key in self.owner.go_to_admitted_interactions.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)
        self._create_or_load_alarm(WAITING_TIMEOUT, self.owner.waiting_timeout, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def handle_event(self, sim_info, event, resolver):
        patient = self.owner.get_patient()
        if event is TestEvent.InteractionComplete and (patient is not None and sim_info is patient.sim_info) and resolver(self.owner.go_to_admitted_interactions):
            self.owner._on_done_waiting()

    def timer_expired(self):
        self._display_time_out_notification()
        self._handle_timed_out_performance_hit()
        self.owner.waiting_expired()
        patient = self.owner.get_patient()
        if patient is not None and self.owner.force_sim_to_leave_lot_on_completion:
            self.owner.manager.make_sim_leave_now_must_run(patient)
        self.owner._self_destruct()

    def _display_time_out_notification(self):
        sim_info = self.owner.get_patient()
        resolver = SingleSimResolver(sim_info)
        if self.owner.waiting_timedout_notification:
            dialog = self.owner.waiting_timedout_notification(sim_info, resolver=resolver)
            dialog.show_dialog()

    def _handle_timed_out_performance_hit(self):
        career_service = services.get_career_service()
        active_career = career_service.get_career_in_career_event()
        if active_career is not None:
            work_performance_stat = active_career.work_performance_stat
            work_performance_stat.add_value(self.owner.waiting_timedout_performance_penalty)
            active_career.resend_career_data()

class TreatedState(SituationState):

    def on_activate(self, reader=None):
        logger.debug('Sim is entering the Treated State during a doc visit.')
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.situation_job, self.owner.treated_role_state)
