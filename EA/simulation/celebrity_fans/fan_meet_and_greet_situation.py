from sims4.tuning.tunable import TunableReference, TunableMapping, TunableRangefrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_complex import SituationState, SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateDatafrom situations.situation_guest_list import SituationGuestInfo, SituationInvitationPurposeimport servicesimport sims4.resources
class MeetAndGreetSituationState(SituationState):
    pass

class FanMeetAndGreetSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'celebrity': TunableSituationJobAndRoleState(description='\n            The job and role of the main celebrity of the event.\n            ', tuning_group=GroupNames.ROLES), 'bartender': TunableSituationJobAndRoleState(description='\n            The job and role of the bartender of the event.\n            ', tuning_group=GroupNames.ROLES), 'fan': TunableSituationJobAndRoleState(description='\n            The job and role of the fans of the event.\n            ', tuning_group=GroupNames.ROLES), 'fan_count_statistic': TunableReference(description='\n            The ranked statistic that we will use in order to determine how\n            many fans we want to invite to the event at minimum.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('RankedStatistic',), tuning_group=GroupNames.ROLES), 'rank_to_fan_count': TunableMapping(description='\n            A mapping between the rank level of the Fan Count Statistic and\n            the number of fans that we want at minimum.\n            ', key_type=TunableRange(description='\n                The statistic rank of the celebrity Sim.\n                ', tunable_type=int, default=0, minimum=0), value_type=TunableRange(description='\n                The minimum number of fans we want to have based on the rank\n                level.\n                ', tunable_type=int, default=0, minimum=0))}
    REMOVE_INSTANCE_TUNABLES = ('venue_invitation_message', 'venue_situation_player_job')

    @classmethod
    def _states(cls):
        return (SituationStateData(1, MeetAndGreetSituationState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.celebrity.job, cls.celebrity.role_state), (cls.bartender.job, cls.bartender.role_state), (cls.fan.job, cls.fan.role_state)]

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def resident_job(cls):
        return cls.fan.job

    def get_situation_goal_actor(self):
        celebrity = next(iter(self._guest_list.get_guest_infos_for_job(self.celebrity.job)))
        return services.sim_info_manager().get(celebrity.sim_id)

    def start_situation(self):
        super().start_situation()
        self._change_state(MeetAndGreetSituationState())

    def _expand_guest_list_based_on_tuning(self):
        host_sim_id = self._guest_list.host_sim_id
        if self.resident_job() is not None and host_sim_id != 0 and self._guest_list.get_guest_info_for_sim_id(host_sim_id) is None:
            guest_info = SituationGuestInfo.construct_from_purpose(host_sim_id, self.resident_job(), SituationInvitationPurpose.HOSTING)
            self._guest_list.add_guest_info(guest_info)
        for job_type in self._jobs:
            if job_type is self.fan.job:
                celebrity_guest_info = next(iter(self._guest_list.get_guest_infos_for_job(self.celebrity.job)))
                celebrity = services.sim_info_manager().get(celebrity_guest_info.sim_id)
                fan_statistic = celebrity.get_statistic(self.fan_count_statistic, add=False)
                if fan_statistic is None:
                    value = 0
                else:
                    value = fan_statistic.rank_level
                num_to_auto_fill = self.rank_to_fan_count.get(value, 0) - len(self._guest_list.get_guest_infos_for_job(job_type))
            else:
                num_to_auto_fill = job_type.get_auto_invite() - len(self._guest_list.get_guest_infos_for_job(job_type))
            for _ in range(num_to_auto_fill):
                guest_info = SituationGuestInfo.construct_from_purpose(0, job_type, SituationInvitationPurpose.AUTO_FILL)
                self._guest_list.add_guest_info(guest_info)
