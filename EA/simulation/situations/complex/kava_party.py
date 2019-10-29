from sims4.tuning.tunable import TunableReference, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_complex import SituationComplexCommon, CommonInteractionCompletedSituationState, CommonSituationState, SituationStateDatafrom situations.situation_guest_list import SituationGuestInfo, SituationInvitationPurposeimport servicesimport sims4.resources
class _PostKavaServed(CommonSituationState):
    pass

class _PreKavaServed(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.post_kava_state())

class KavaPartySituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'_pre_kava_served_state': _PreKavaServed.TunableFactory(description='\n            The situation state used at the start of the party, before the\n            kava has been served for the first time.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_pre_kava_served_state'), '_post_kava_served_state': _PostKavaServed.TunableFactory(description='\n            The situation state used during the party after the kava has been\n            served for the first time.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_post_kava_served_state'), 'guest_job': TunableReference(description='\n            The job that guests will use.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), tuning_group=GroupNames.ROLES), 'host_job': TunableReference(description='\n            The job that the host will use.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), tuning_group=GroupNames.ROLES), 'island_guest_job': TunableReference(description='\n            The job that will be used for Islander auto invited to the party.\n            \n            This needs to be different because it will only filter Island Sims\n            as valid guests, which is different than the regular guest job.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB), tuning_group=GroupNames.ROLES), 'min_number_of_guests': Tunable(description='\n            The minimum number of Sims that should show up for a Kava Party,\n            assuming there is enough room in the Sim cap to accommodate them. \n            \n            If less than this number of Sims is chosen as a \n            guest by the user, then the rest will be filled with random island\n            Sims.\n            ', tunable_type=int, default=8, tuning_group=GroupNames.ROLES)}

    @classmethod
    def _states(cls):
        return [SituationStateData(1, _PreKavaServed, factory=cls._pre_kava_served_state), SituationStateData(2, _PostKavaServed, factory=cls._post_kava_served_state)]

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls._pre_kava_served_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def default_job(cls):
        pass

    def start_situation(self):
        super().start_situation()
        self._change_state(self._pre_kava_served_state())

    @property
    def post_kava_state(self):
        return self._post_kava_served_state

    def _expand_guest_list_based_on_tuning(self):
        num_to_auto_fill = self.min_number_of_guests - len(self._guest_list.get_guest_infos_for_job(self.guest_job))
        if num_to_auto_fill > 0:
            for _ in range(num_to_auto_fill):
                guest_info = SituationGuestInfo.construct_from_purpose(0, self.island_guest_job, SituationInvitationPurpose.AUTO_FILL)
                self._guest_list.add_guest_info(guest_info)
