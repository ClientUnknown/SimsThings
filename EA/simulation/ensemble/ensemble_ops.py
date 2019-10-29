from interactions import ParticipantTypeSingleSimfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom sims4.tuning.tunable import TunableEnumEntry, TunableReferenceimport servicesimport sims4.loglogger = sims4.log.Logger('Ensembles', default_owner='jjacobson')
class AddToEnsemble(XevtTriggeredElement):
    FACTORY_TUNABLES = {'actor': TunableEnumEntry(description='\n            The Sim who will be inviting the target to the ensemble.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'target': TunableEnumEntry(description='\n            The Sim who will be put into the ensemble with the actor.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.TargetSim), 'ensemble_type': TunableReference(description='\n            The type of ensemble to put these Sims into.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ENSEMBLE))}

    def _do_behavior(self, *args, **kwargs):
        actor = self.interaction.get_participant(self.actor)
        if actor is None:
            logger.error("AddToEnsemble: Trying to add actor Sim who doesn't exist.")
            return
        target = self.interaction.get_participant(self.target)
        if target is None:
            logger.error("AddToEnsemble: Trying to add target Sim who doesn't exist.")
            return
        services.ensemble_service().create_ensemble(self.ensemble_type, (actor, target))

class RemoveFromEnsemble(XevtTriggeredElement):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The Sim that will be removed from an ensemble.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'ensemble_type': TunableReference(description='\n            The type of ensemble to remove these Sims from.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ENSEMBLE))}

    def _do_behavior(self, *args, **kwargs):
        subject = self.interaction.get_participant(self.subject)
        if subject is None:
            logger.error('RemoveFromEnsemble: Trying to remove a non-existent Sim from an ensemble.')
            return
        services.ensemble_service().remove_sim_from_ensemble(self.ensemble_type, subject)

class DestroyEnsemble(XevtTriggeredElement):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description="\n            The Sim who's ensemble will be destroyed.\n            ", tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'ensemble_type': TunableReference(description='\n            The type of ensemble to destroy.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ENSEMBLE))}

    def _do_behavior(self, *args, **kwargs):
        subject = self.interaction.get_participant(self.subject)
        if subject is None:
            logger.error("DestroyEnsemble: Trying to destroy a non-existent Sim's ensemble.")
            return
        services.ensemble_service().destroy_sims_ensemble(self.ensemble_type, subject)
