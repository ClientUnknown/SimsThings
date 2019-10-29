from event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom sims4.tuning.tunable import TunableSimMinute, Tunable, OptionalTunable, TunableReferencefrom situations.complex.staffed_object_situation_mixin import StaffedObjectSituationMixinfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonInteractionCompletedSituationState, SituationStateData, CommonInteractionStartedSituationStatefrom situations.situation_job import SituationJobfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport servicesimport sims4.loglogger = sims4.log.Logger('Object Staff', default_owner='rfleig')ACTIVELY_WORKING_TIMEOUT = 'acively_working_timeout'BORED_TIMEOUT = 'bored_timeout'
class _ArrivingState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner.display_dialog(self.owner.arrival_notification)
        self._change_state(self.owner._actively_working_situation_state())

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner.sim_of_interest(sim_info):
            return True
        return False

class _ActivelyWorkingState(CommonInteractionCompletedSituationState):

    def on_activate(self, reader=None):
        logger.debug('Staff Member is now actively working.')
        super().on_activate(reader)
        for custom_key in self._interaction_of_interest.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionStart, custom_key)
        staff_member = self.owner.get_staff_member()
        if not (staff_member and staff_member.queue.running and self._interaction_of_interest(staff_member.queue.running)):
            self._create_or_load_alarm(ACTIVELY_WORKING_TIMEOUT, self.owner.actively_working_timeout, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionStart and resolver(self._interaction_of_interest) and self._additional_tests(sim_info, event, resolver):
            self._cancel_alarm(ACTIVELY_WORKING_TIMEOUT)
            return
        super().handle_event(sim_info, event, resolver)

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner.sim_of_interest(sim_info):
            return True
        return False

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.restart_timer()

    def restart_timer(self):
        logger.debug('Actively Working timeout has been reset.')
        self._cancel_alarm(ACTIVELY_WORKING_TIMEOUT)
        self._create_or_load_alarm(ACTIVELY_WORKING_TIMEOUT, self.owner.actively_working_timeout, lambda _: self.timer_expired(), should_persist=True)

    def timer_expired(self):
        self._change_state(self.owner._bored_situation_state())

class _BoredState(CommonInteractionStartedSituationState):

    def on_activate(self, reader=None):
        logger.debug('Staff Member is now bored from lack of work.')
        super().on_activate(reader)
        if self.owner.bored_timeout:
            self._create_or_load_alarm(BORED_TIMEOUT, self.owner.bored_timeout, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner.sim_of_interest(sim_info):
            return True
        return False

    def _on_interaction_of_interest_started(self):
        logger.debug('The Staff Member has run an appropriate work interaction and is no longer bored.')
        self._change_state(self.owner._actively_working_situation_state())

    def timer_expired(self):
        self.owner.display_dialog(self.owner.bored_timeout_notification)
        self.owner.release_claimed_staffed_object()
        staff_member = self.owner.get_staff_member()
        if staff_member is not None and self.owner.force_sim_to_leave_lot_on_completion:
            self.owner.manager.make_sim_leave_now_must_run(staff_member)
        self.owner._self_destruct()

class StaffMemberSituation(StaffedObjectSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'situation_job': SituationJob.TunableReference(description='\n            The job that a staff member will be in during the situation.\n            '), 'actively_working_timeout': TunableSimMinute(description='\n            The timeout for a staff member in the actively working state.\n            If none of the return_to_actively_working_interactions are run before\n            time expires then the therapist will transition to the bored state.\n            ', default=60, tuning_group=SituationComplexCommon.TIMEOUT_GROUP), 'bored_timeout': OptionalTunable(description="\n            If this is enabled then the bored state will have a timeout. If \n            the timer goes off then the Sim will leave. Leave this disabled if\n            you don't ever want a Sim to leave (e.g. a venue staff person)\n            ", tunable=TunableSimMinute(description='\n                The timeout for a staff member in the bored state. If none of\n                the return_to_actively_working_interactions are run before the\n                timeout expires then the therapist will transition to the leaving\n                state.\n                ', default=60, tuning_group=SituationComplexCommon.TIMEOUT_GROUP)), 'force_sim_to_leave_lot_on_completion': Tunable(description='\n            If set to True, when a Sim enters the leaving state she will be\n            forced to leave the lot right away.\n            \n            If set to False, when a Sim enters the leaving state she will leave\n            at her earliest convenience.\n            ', tunable_type=bool, default=True, tuning_group=SituationComplexCommon.TIMEOUT_GROUP), 'arrival_notification': OptionalTunable(description='\n            When enabled, when the Sim arrives on the lot this notification \n            will be displayed to announce their arrival.\n            ', tunable=TunableUiDialogNotificationSnippet(description='\n                The notification that is displayed whenever a Sim times out while\n                waiting and leaves the lot.\n                '), enabled_by_default=True, tuning_group=SituationComplexCommon.NOTIFICATION_GROUP), 'bored_timeout_notification': OptionalTunable(description='\n            When enabled, when the bored timeout expires and the staff \n            member advances to the leaving state, this notification will be\n            displayed.\n            ', tunable=TunableUiDialogNotificationSnippet(description='\n                A notification letting the user know that the staff member\n                is done standing around being bored. This likely means that\n                the time has come for the staff member to leave.\n                '), enabled_by_default=True, tuning_group=SituationComplexCommon.NOTIFICATION_GROUP), '_arriving_situation_state': _ArrivingState.TunableFactory(description='\n            The situation state used for when a Sim is arriving as a staff \n            member.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_arriving_situation_state'), '_actively_working_situation_state': _ActivelyWorkingState.TunableFactory(description='\n            The situation state when a staff member is standing \n            professionally around the table and not much else. If they spend\n            too much time in this state without doing any work it will progress\n            to the bored state.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_actively_working_situation_state'), '_bored_situation_state': _BoredState.TunableFactory(description='\n            The situation state for the staff member that has been \n            standing idly by for a while without working. If the staff member\n            is in this state too long without working then they will leave.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='03_bored_situation_state'), 'arrival_interaction': OptionalTunable(description='\n            The interaction to push on the staff member in this situation when\n            they enter the ArrivingState.\n            ', disabled_name='not_required', enabled_name='push_interaction', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return [SituationStateData(1, _ArrivingState, factory=cls._arriving_situation_state), SituationStateData(2, _ActivelyWorkingState, factory=cls._actively_working_situation_state), SituationStateData(3, _BoredState, factory=cls._bored_situation_state)]

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls._arriving_situation_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def default_job(cls):
        pass

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        if self._cur_state is None:
            return (role_state_type, role_affordance_target)
        return self._cur_state._get_role_state_overrides(sim, job_type, role_state_type, role_affordance_target)

    def start_situation(self):
        super().start_situation()
        self._change_state(self._arriving_situation_state())

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        arrival_interaction = self.arrival_interaction
        staff_member = self.get_staff_member()
        if arrival_interaction is not None and staff_member is not None:
            interaction_context = InteractionContext(staff_member, InteractionContext.SOURCE_SCRIPT, Priority.Low)
            staffed_object = self.get_staffed_object()
            enqueue_result = staff_member.push_super_affordance(self.arrival_interaction, staffed_object, interaction_context)
            if not enqueue_result:
                logger.error('Failed to push the arrival interaction for the Staff Situation.')

    def display_dialog(self, dialog_tuning):
        staff_member = self.get_staff_member()
        if dialog_tuning is not None and staff_member is not None:
            resolver = SingleSimResolver(staff_member)
            dialog = dialog_tuning(staff_member.sim_info, resolver=resolver)
            dialog.show_dialog()
