from sims4.tuning.tunable import TunableVariant, TunableTuple, Tunablefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposeimport event_testing.resultsimport interactions.base.super_interactionimport servicesimport sims4.logimport sims4.resourcesimport sims4.tuninglogger = sims4.log.Logger('Interactions')
class RunSituationSuperInteraction(interactions.base.super_interaction.SuperInteraction):
    INSTANCE_TUNABLES = {'situation': sims4.tuning.tunable.TunableReference(description='\n            The situation to launch upon execution of this interaction.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), tuning_group=sims4.tuning.tunable_base.GroupNames.SITUATION), 'job_mapping': sims4.tuning.tunable.TunableMapping(description='\n                This is a mapping of participant type to situation job.  These must match up with \n                the jobs in the actual situation.\n                ', key_type=sims4.tuning.tunable.TunableEnumEntry(description='\n                The participant type that will be given this job.\n                ', tunable_type=interactions.ParticipantType, default=interactions.ParticipantType.Actor), value_type=sims4.tuning.tunable.TunableReference(description='\n                The situation job applied to this participant type.  This MUST\n                be a valid job for the situation.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), tuning_group=sims4.tuning.tunable_base.GroupNames.SITUATION), 'host_sim': sims4.tuning.tunable.OptionalTunable(description='\n            The participant type that will be made the host. If disabled, the\n            host will be None which is okay in circumstances where there is no\n            need for a host (i.e. a walkbye or a ghost situation).\n            ', tunable=sims4.tuning.tunable.TunableEnumFlags(description='\n                The participant type that will be made the host.\n                ', enum_type=interactions.ParticipantType, default=interactions.ParticipantType.Actor), enabled_by_default=True, disabled_name='NoHost', tuning_group=sims4.tuning.tunable_base.GroupNames.SITUATION), 'invite_only': sims4.tuning.tunable.Tunable(description='\n            If checked then the situation guest list will be invite only.\n            ', tunable_type=bool, default=False, tuning_group=sims4.tuning.tunable_base.GroupNames.SITUATION), 'ui_options': TunableVariant(description='\n            Options for setting up the situation UI.\n            ', user_facing=TunableTuple(description='\n                Enable the user facing situation UI, displaying the situation name,\n                goals, and scoring where appropriate. \n                ', scoring_enabled=Tunable(description='\n                    If disabled, will only show the situation name and time.\n                    ', tunable_type=bool, default=True)), locked_args={'disabled': None}, default='disabled', tuning_group=sims4.tuning.tunable_base.GroupNames.SITUATION)}

    def _run_interaction_gen(self, timeline):
        logger.assert_raise(self.situation is not None, 'No situation tuned on RunSituationSuperInteraction: {}'.format(self), owner='rez')
        situation_manager = services.get_zone_situation_manager()
        host_sim_id = 0
        if self.host_sim is not None:
            host_sim = self.get_participant(self.host_sim)
            if host_sim is not None:
                host_sim_id = host_sim.sim_id
        guest_list = SituationGuestList(invite_only=self.invite_only, host_sim_id=host_sim_id)
        if self.job_mapping:
            for (participant_type, job) in self.job_mapping.items():
                sim = self.get_participant(participant_type)
                if sim is not None and sim.is_sim:
                    guest_info = SituationGuestInfo.construct_from_purpose(sim.sim_id, job, SituationInvitationPurpose.INVITED)
                    guest_list.add_guest_info(guest_info)
        user_facing = False
        scoring_enabled = True
        if self.ui_options is not None:
            user_facing = True
            scoring_enabled = self.ui_options.scoring_enabled
        situation_manager.create_situation(self.situation, guest_list=guest_list, user_facing=user_facing, interaction=self, scoring_enabled=scoring_enabled)
        return event_testing.results.ExecuteResult.NONE
