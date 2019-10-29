import itertoolsimport randomfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableRangefrom situations.bouncer.bouncer_types import BouncerExclusivityCategory, RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleState, CommonInteractionStartedSituationState, CommonSituationStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_types import SituationCreationUIOptionfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport servicesimport sims4logger = sims4.log.Logger('Star Placement Ceremony', default_owner='shipark')
class _GatherState(CommonInteractionStartedSituationState):

    def on_active(self, reader=None):
        logger.debug('The crowd is gathering to watch the Placement Ceremony.')
        super().on_activate(reader)

    def timer_expired(self):
        self.owner.display_dialog(self.owner.impatient_notification)
        self._change_state(self.owner.impatient_gather_state())

    def _on_interaction_of_interest_started(self):
        self._change_state(self.owner.start_ceremony_state())

class _ImpatientGatherState(CommonInteractionStartedSituationState):

    def on_activate(self, sim_info=None, reader=None):
        logger.debug("The crowd is restless because the placement hasn't occurred.")
        super().on_activate(reader)

    def _on_interaction_of_interest_started(self):
        self._change_state(self.owner.start_ceremony_state())

    def timer_expired(self):
        self.owner.display_dialog(self.owner.timed_out_notification)
        self.owner._self_destruct()

class _StartCeremonyState(CommonSituationState):

    def on_activate(self, reader=None):
        logger.debug('The honoree has placed the star.')
        super().on_activate(reader)

class StarPlacementCeremonySituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'honoree_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the honoree.\n            '), 'crowd_member_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for a crowd member.\n            '), 'impatient_notification': TunableUiDialogNotificationSnippet(description='\n            The notification that is displayed after the Gather State has timed\n            out.\n            '), 'timed_out_notification': TunableUiDialogNotificationSnippet(description='\n            The notification that is displayed after the Impatient Gather State has timed\n            out.\n            '), 'gather_state': _GatherState.TunableFactory(description='\n            The gather state for the start placement ceremony situation where\n            the crowd gathers around the star. \n            ', display_name='1. Gather State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'impatient_gather_state': _ImpatientGatherState.TunableFactory(description="\n            The crowd grows restless after they've gathered and the star has not been\n            placed.\n            ", display_name='2. Impatient Gather State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'start_ceremony_state': _StartCeremonyState.TunableFactory(description='\n            The crowd reacts to the honoree having placed the star, and the honoree\n            responds with an excited reaction, like a fist pump.\n            ', display_name='3. Start Ceremony State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _GatherState, factory=cls.gather_state), SituationStateData(2, _ImpatientGatherState, factory=cls.impatient_gather_state), SituationStateData(3, _StartCeremonyState, factory=cls.start_ceremony_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.honoree_job_and_role_state.job, cls.honoree_job_and_role_state.role_state), (cls.crowd_member_job_and_role_state.job, cls.crowd_member_job_and_role_state.role_state)]

    @classmethod
    def default_job(cls):
        pass

    def start_situation(self):
        super().start_situation()
        self._change_state(self.gather_state())

    def display_dialog(self, notification):
        active_sim = services.get_active_sim()
        if active_sim is not None:
            dialog = self.impatient_notification(active_sim)
            dialog.show_dialog()
lock_instance_tunables(StarPlacementCeremonySituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)