from interactions import ParticipantTypefrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableVariant, TunableEnumEntry
class SquadLootOp(BaseLootOperation):
    ADD_SIM = 0
    REMOVE_SIM = 1
    FACTORY_TUNABLES = {'action': TunableVariant(description='\n            The choice of whether or not to add or remove the target from the\n            actors squad.\n            ', locked_args={'add_to': ADD_SIM, 'remove_from': REMOVE_SIM}, default='add_to'), 'target_sim': TunableEnumEntry(description='\n            The Sim that is being added to/removed from the subjects squad.\n            ', tunable_type=ParticipantType, default=ParticipantType.TargetSim)}

    def __init__(self, *args, action=None, actor=None, target_sim=None, **kwargs):
        super().__init__(*args, target_participant_type=target_sim, **kwargs)
        self._action = action
        self._actor = actor
        self._target_sim = target_sim

    def _apply_to_subject_and_target(self, subject, target_sim, resolver):
        if self._action == SquadLootOp.ADD_SIM:
            subject.add_sim_info_id_to_squad(target_sim.id)
            return
        if target_sim.id in subject.squad_members:
            subject.remove_sim_info_id_from_squad(target_sim.id)
