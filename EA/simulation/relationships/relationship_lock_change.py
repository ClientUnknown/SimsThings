from interactions import ParticipantTypeSimfrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableReference, TunableEnumEntryimport servicesimport sims4.resources
class UnlockRelationshipBitLock(BaseLootOperation):
    FACTORY_TUNABLES = {'relationship_lock': TunableReference(description='\n            The type of relationship lock to change.\n            ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_LOCK)), 'target': TunableEnumEntry(description='\n            The target of this loot operation.\n            ', tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.TargetSim)}

    def __init__(self, relationship_lock, target, **kwargs):
        super().__init__(target_participant_type=target, **kwargs)
        self._relationship_lock = relationship_lock

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None or target is None:
            return
        relationship_service = services.relationship_service()
        relationship_lock = relationship_service.get_relationship_lock(subject.sim_id, target.sim_id, self._relationship_lock)
        if relationship_lock is None:
            return
        relationship_lock.unlock()
