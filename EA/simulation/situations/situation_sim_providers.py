from interactions import ParticipantTypeSingleSim, ParticipantTypeSituationSimsfrom sims4.resources import Typesfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableReference, TunableEnumEntry, TunableList, HasTunableFactory, TunableMapping, TunablePackSafeReferencefrom situations.situation_by_definition_or_tags import SituationSearchByDefinitionOrTagsVariantimport services
class SituationSimProvider(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'situations': SituationSearchByDefinitionOrTagsVariant(description='\n            The situations to look for.\n            '), 'job': TunablePackSafeReference(description='\n            The Job from which we will find Sims.\n            ', manager=services.get_instance_manager(Types.SITUATION_JOB)), 'situation_participant': TunableEnumEntry(description="\n            Participant used to determine which situations are searched.\n            \n            The situations found will be once the situation_participant is in\n            that match the criteria that is specified in 'situations'\n            ", tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.TargetSim)}

    def get_participants(self, resolver):
        if self.job is None:
            return ()
        situation_participant = resolver.get_participant(self.situation_participant)
        if situation_participant is None:
            return ()
        situation_sims = set()
        for situation in self.situations.get_situations_for_sim_info(situation_participant):
            for situation_sim in situation.all_sims_in_job_gen(self.job):
                situation_sims.add(situation_sim.sim_info)
        return tuple(situation_sims)

class SituationSimParticipantProviderMixin(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'provided_participant_type_to_job_map': TunableMapping(description='\n            Mapping from the liability provided type to the jobs it will search\n            for the participants in.\n            ', key_type=TunableEnumEntry(description='\n                Participant type that will be populated with the found Sims\n                ', tunable_type=ParticipantTypeSituationSims, default=ParticipantTypeSituationSims.SituationParticipants1), value_type=TunableList(description='\n                Situation sim providers allow the ability to search for Sims with specific\n                jobs that share a situation with the provided participant.\n                ', tunable=SituationSimProvider.TunableFactory()))}

    def get_participants(self, participant_type, resolver):
        if participant_type in self.provided_participant_type_to_job_map:
            participants = set()
            for provider in self.provided_participant_type_to_job_map[participant_type]:
                participants.update(provider.get_participants(resolver))
            return tuple(participants)
        return ()
