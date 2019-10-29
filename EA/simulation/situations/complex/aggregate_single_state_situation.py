import itertoolsfrom filters.tunable import FilterTermTag, TunableAggregateFilterfrom role.role_state import RoleStatefrom sims4.tuning.tunable import TunableTuple, TunableReference, TunableMapping, TunableEnumEntry, Tunablefrom situations.bouncer.bouncer_types import RequestSpawningOptionfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationState, SituationStateDatafrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_job import SituationJobimport filters.tunableimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('AggregateSingleStateSituation', default_owner='jjacobson')
class AggregateSingleStateSituationState(SituationState):
    pass

class AggregateSingleStateSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'group_filter': TunableAggregateFilter.TunableReference(description='\n            The aggregate filter that we use to find the sims for this\n            situation.\n            '), 'situation_job_mapping': TunableMapping(description='\n            A mapping of filter term tag to situation job.\n            \n            The filter term tag is returned as part of the sim filters used to \n            create the guest list for this particular background situation.\n            \n            The situation job is the job that the Sim will be assigned to in\n            the background situation.\n            ', key_name='filter_tag', key_type=TunableEnumEntry(description='\n                The filter term tag returned with the filter results.\n                ', tunable_type=FilterTermTag, default=FilterTermTag.NO_TAG), value_name='job_and_role', value_type=TunableTuple(description='\n                The job and role state that the Sim will be put into.\n                ', situation_job=SituationJob.TunableReference(description='\n                    A reference to a SituationJob that can be performed at this Situation.\n                    '), role_state=RoleState.TunableReference(description='\n                    A role state the Sim assigned to the job will perform.\n                    '))), 'blacklist_job': SituationJob.TunableReference(description='\n            The default job used for blacklisting Sims from being put into this\n            AggregateSingleStateSituation.\n            '), 'force_leave_on_exit': Tunable(description='\n            If checked, then we will force the Sims to leave when they are\n            removed from the situation.  Otherwise we will just let the leave\n            Situation pick them up as normal.\n            ', tunable_type=bool, default=False)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _verify_tuning_callback(cls):
        super()._verify_tuning_callback()
        for job_role in cls.situation_job_mapping.values():
            if job_role.situation_job.sim_auto_invite.upper_bound > 0:
                logger.error('Situation Job {} used for an aggregate filter specifies Sim Auto Invite.  This is not supported and can cause errors.', job_role.situation_job)

    @classmethod
    def _states(cls):
        return (SituationStateData(1, AggregateSingleStateSituationState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(job_role.situation_job, job_role.role_state) for job_role in cls.situation_job_mapping.values()]

    @classmethod
    def get_predefined_guest_list(cls):
        guest_list = SituationGuestList(invite_only=True)
        situation_manager = services.get_zone_situation_manager()
        instanced_sim_ids = [sim.sim_id for sim in services.sim_info_manager().instanced_sims_gen()]
        household_sim_ids = [sim_info.id for sim_info in services.active_household().sim_info_gen()]
        auto_fill_blacklist = situation_manager.get_auto_fill_blacklist(sim_job=cls.blacklist_job)
        situation_sims = set()
        for situation in situation_manager.get_situations_by_tags(cls.tags):
            situation_sims.update(situation.invited_sim_ids)
        blacklist_sim_ids = set(itertools.chain(situation_sims, instanced_sim_ids, household_sim_ids, auto_fill_blacklist))
        filter_results = services.sim_filter_service().submit_matching_filter(sim_filter=cls.group_filter, allow_yielding=False, blacklist_sim_ids=blacklist_sim_ids, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not filter_results:
            return
        for result in filter_results:
            job_role = cls.situation_job_mapping.get(result.tag, None)
            if job_role is None:
                pass
            else:
                guest_list.add_guest_info(SituationGuestInfo(result.sim_info.sim_id, job_role.situation_job, RequestSpawningOption.DONT_CARE, job_role.situation_job.sim_auto_invite_allow_priority))
        return guest_list

    @classmethod
    def default_job(cls):
        pass

    def start_situation(self):
        super().start_situation()
        self._change_state(AggregateSingleStateSituationState())

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        if self.force_leave_on_exit:
            services.get_zone_situation_manager().make_sim_leave_now_must_run(sim)
