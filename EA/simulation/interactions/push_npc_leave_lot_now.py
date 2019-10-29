from interactions import ParticipantTypeSingleSimfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom sims4.tuning.tunable import TunableEnumEntry, Tunable, TunableReference, TunableSetimport servicesimport sims4.resourceslogger = sims4.log.Logger('PushNpcLeaveLotNowInteraction', default_owner='trevor')
class PushNpcLeaveLotNowInteraction(XevtTriggeredElement):
    NPC_LEAVE_LOT_NOW_AFFORDANCES = TunableSet(TunableReference(description='\n            The default interaction an NPC Sim will run when they are pushed to\n            leave the lot.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), allow_none=False))
    NPC_LEAVE_LOT_NOW_MUST_RUN_AFFORDANCE = TunableSet(TunableReference(description='\n            The default interaction an NPC Sim will run when they are pushed the\n            "must run" version of leave lot.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), allow_none=False))
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant on which to push the Leave Lot Now interaction.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Invalid, invalid_enums=(ParticipantTypeSingleSim.Invalid,)), 'must_run': Tunable(description='\n            If checked, the "Must Run" version of the Leave Lot Now interaction\n            will be used.\n            ', tunable_type=bool, default=False)}

    def can_push(self, participant, affordance):
        to_consider = []
        for existing_si in participant.si_state.all_guaranteed_si_gen(self.interaction.context.run_priority, group_id=self.interaction.context.group_id):
            if affordance.super_affordance_klobberers and affordance.super_affordance_klobberers(existing_si.affordance):
                pass
            else:
                to_consider.append(existing_si)
        for existing_si in to_consider:
            if existing_si is self.interaction:
                pass
            elif not existing_si.si_state.test_non_constraint_compatibility(existing_si, affordance, participant):
                return False
        return True

    def _do_behavior(self):
        participant = self.interaction.get_participant(self.participant)
        if participant is None:
            logger.error('Got no participant trying to run the PushNpcLeaveLotNowInteraction Basic Extra.')
            return
        trait_leave_lot_interactions = participant.trait_tracker.get_leave_lot_now_interactions(self.must_run)
        for interaction in trait_leave_lot_interactions:
            if self.must_run or not self.can_push(participant, interaction):
                pass
            elif participant.push_super_affordance(interaction, None, self.interaction.context):
                return
        if self.must_run:
            for interaction in PushNpcLeaveLotNowInteraction.NPC_LEAVE_LOT_NOW_MUST_RUN_AFFORDANCE:
                if participant.push_super_affordance(interaction, None, self.interaction.context):
                    return
        else:
            for interaction in PushNpcLeaveLotNowInteraction.NPC_LEAVE_LOT_NOW_AFFORDANCES:
                if not self.can_push(participant, interaction):
                    pass
                elif participant.push_super_affordance(interaction, None, self.interaction.context):
                    return
