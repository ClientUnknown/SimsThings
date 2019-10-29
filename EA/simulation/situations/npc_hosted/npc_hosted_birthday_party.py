from date_and_time import create_time_spanfrom sims4.tuning.tunable import TunableTuple, TunableSimMinute, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_complex import SituationComplexCommon, CommonSituationState, CommonInteractionCompletedSituationState, SituationStateDataimport alarmsimport servicesimport sims4.tuning.instancesimport situations.bouncer.bouncer
class _BirthdayPreperationSituationState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.age_up_host_situation_state())

class _AgeUpHostSituationState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.post_age_up_situation_state())

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.initiating_sim_info is sim_info

class _AgeUpHostBackupSituationState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.post_age_up_situation_state())

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.initiating_sim_info is sim_info

class _PostAgeUpSituationState(CommonSituationState):
    pass

class NPCHostedBirthdayParty(SituationComplexCommon):
    INSTANCE_TUNABLES = {'preparation_situation_state': _BirthdayPreperationSituationState.TunableFactory(description='\n                The first state of this situation.  In this state sims should\n                be socializing and the caterer should be preparing the birthday\n                cake.\n                \n                All jobs and role states should be defined in this situation\n                state.\n                ', tuning_group=GroupNames.STATE), 'age_up_host_situation_state': _AgeUpHostSituationState.TunableFactory(description='\n                Second state of the situation.  This state should start when\n                the caterer has finished setting up the birthday cake.  This\n                situation state will have the host sim try and age up with the\n                birthday cake.\n                ', tuning_group=GroupNames.STATE), 'age_up_host_backup_situation_state': TunableTuple(description='\n                Information related to the Age Up Host Backup Situation State.\n                ', situation_state=_AgeUpHostBackupSituationState.TunableFactory(description="\n                    Backup Situation State.  Hopefully this will never have to be\n                    used.  In the case that the caterer is never able to make a\n                    cake or the host sim isn't able to run the age up interaction\n                    on the cake then this state will be entered.  Within this\n                    state the host sim will attempt to be forced to age up.\n                    "), time_out=TunableSimMinute(description='\n                    The amount of time since the beginning of the situation\n                    that we will be put into the Age Up Host Backup Situation\n                    State if we are not already in the Post Age Up Situation\n                    State.\n                    ', default=1, minimum=1), tuning_group=GroupNames.STATE), 'post_age_up_situation_state': _PostAgeUpSituationState.TunableFactory(description='\n                The third situation state.  This state should encompass all of\n                the situation behavior after the sim has aged up and will\n                continue till the end of the party.\n                ', tuning_group=GroupNames.STATE), '_default_job': TunableReference(description='\n                The default job for Sims in this situation\n                ', manager=services.situation_job_manager(), allow_none=True)}

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _BirthdayPreperationSituationState, factory=cls.preparation_situation_state), SituationStateData(2, _AgeUpHostSituationState, factory=cls.age_up_host_situation_state), SituationStateData(3, _AgeUpHostBackupSituationState, factory=cls.age_up_host_backup_situation_state.situation_state), SituationStateData(4, _PostAgeUpSituationState, factory=cls.post_age_up_situation_state))

    @classmethod
    def default_job(cls):
        return cls._default_job

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.preparation_situation_state._tuned_values.job_and_role_changes.items())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backup_timeout_alarm_handle = None

    def start_situation(self):
        super().start_situation()
        self._change_state(self.preparation_situation_state())
        self._setup_backup_alarm_handle()

    def load_situation(self):
        result = super().load_situation()
        if result:
            self._setup_backup_alarm_handle()
        return result

    def _change_to_backup_state(self, _):
        if type(self._cur_state) is _PostAgeUpSituationState:
            return
        self._change_state(self.age_up_host_backup_situation_state.situation_state())

    def _setup_backup_alarm_handle(self):
        if type(self._cur_state) is _PostAgeUpSituationState:
            return
        backup_time = self._start_time + create_time_span(minutes=self.age_up_host_backup_situation_state.time_out)
        now = services.time_service().sim_now
        time_till_backup_state = backup_time - now
        if time_till_backup_state.in_ticks() <= 0:
            self._change_state(self.age_up_host_backup_situation_state.situation_state())
            return
        self._backup_timeout_alarm_handle = alarms.add_alarm(self, time_till_backup_state, self._change_to_backup_state)
sims4.tuning.instances.lock_instance_tunables(NPCHostedBirthdayParty, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.NORMAL, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE)