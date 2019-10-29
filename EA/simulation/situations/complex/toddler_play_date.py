from sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation_complex import SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleState, CommonInteractionCompletedSituationState, CommonSituationStatefrom situations.situation_guest_list import SituationGuestInfo, SituationInvitationPurposefrom venues.venue_constants import VenueTuningimport servicesimport sims4logger = sims4.log.Logger('Situations')
class _PlayDateState(CommonSituationState):

    def timer_expired(self):
        self._change_state(self.owner._leave_state())

class _LeaveState(CommonInteractionCompletedSituationState):
    pass

class ToddlerPlayDateSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'host_toddler_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state of toddler who planned the Play Date.\n            ', tuning_group=GroupNames.ROLES), 'host_parent_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state of parent who planned the Play Date.\n            ', tuning_group=GroupNames.ROLES), 'guest_toddler_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state of toddler who gets invited for Play Date.\n            ', tuning_group=GroupNames.ROLES), 'guest_parent_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state of parent who gets invited for Play Date.\n            ', tuning_group=GroupNames.ROLES), '_play_date_state': _PlayDateState.TunableFactory(description='\n            The state where Sims will play and take care the toddler.\n            ', display_name='1. PlayDate State', tuning_group=GroupNames.STATE), '_leave_state': _LeaveState.TunableFactory(description='\n            The state where the Sims are done playing and about to leave\n            the lot. Parent will carry their toddler before leaving the lot.\n            ', display_name='2. Leave State', tuning_group=GroupNames.STATE)}

    def __init__(self, seed, *args, **kwargs):
        self._add_host_toddler_to_guest_list(seed)
        super().__init__(seed, *args, **kwargs)

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _PlayDateState, factory=cls._play_date_state), SituationStateData(2, _LeaveState, factory=cls._leave_state))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.host_toddler_job_and_role_state.job, cls.host_toddler_job_and_role_state.role_state), (cls.host_parent_job_and_role_state.job, cls.host_parent_job_and_role_state.role_state), (cls.guest_toddler_job_and_role_state.job, cls.guest_toddler_job_and_role_state.role_state), (cls.guest_parent_job_and_role_state.job, cls.guest_parent_job_and_role_state.role_state)]

    @classmethod
    def get_possible_zone_ids_for_situation(cls, host_sim_info=None, guest_ids=None):
        possible_zones = []
        venue_service = services.current_zone().venue_service
        for venue_type in cls.venue_types:
            if venue_type is VenueTuning.RESIDENTIAL_VENUE_TYPE:
                if host_sim_info is not None:
                    possible_zones.append(host_sim_info.household.home_zone_id)
                    possible_zones.extend(venue_service.get_zones_for_venue_type_gen(venue_type))
            else:
                possible_zones.extend(venue_service.get_zones_for_venue_type_gen(venue_type))
        return possible_zones

    def start_situation(self):
        super().start_situation()
        self._change_state(self._play_date_state())

    def _add_host_toddler_to_guest_list(self, seed):
        host_sim = seed.guest_list.host_sim
        if host_sim is None:
            return
        if host_sim.sim_info.lives_here:
            for sim_info in host_sim.household.sim_info_gen():
                if sim_info.is_toddler and seed.guest_list.get_guest_info_for_sim(sim_info) is None:
                    guest_info = SituationGuestInfo.construct_from_purpose(sim_info.sim_id, self.host_toddler_job_and_role_state.job, SituationInvitationPurpose.HOSTING)
                    seed.guest_list.add_guest_info(guest_info)

    @classmethod
    def _add_guest_parent_to_guest_list(cls, guest_list):
        m = services.sim_info_manager()
        households = {m.get(sim.sim_id).household for sim in guest_list.get_guest_infos_for_job(cls.guest_toddler_job_and_role_state.job)}
        for household in households:
            for sim_info in household.sim_info_gen():
                if sim_info.is_young_adult_or_older:
                    guest_info = SituationGuestInfo.construct_from_purpose(sim_info.sim_id, cls.guest_parent_job_and_role_state.job, SituationInvitationPurpose.INVITED)
                    guest_list.add_guest_info(guest_info)
                    break
            logger.error('Failed to find young adult or older Sim in household {}.', household, owner='mkartika')

    @classmethod
    def get_extended_guest_list(cls, guest_list=None):
        if guest_list is None:
            return
        cls._add_guest_parent_to_guest_list(guest_list)
        return guest_list
lock_instance_tunables(ToddlerPlayDateSituation, exclusivity=BouncerExclusivityCategory.NORMAL)