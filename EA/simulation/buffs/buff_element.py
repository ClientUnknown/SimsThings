from buffs.tunable import TunablePackSafeBuffReferencefrom interactions import ParticipantTypeSingleSimfrom interactions.utils.interaction_elements import XevtTriggeredElementimport sims4.logfrom sims4.tuning.tunable import TunableEnumEntrylogger = sims4.log.Logger('Buffs')
class BuffFireAndForgetElement(XevtTriggeredElement):

    @staticmethod
    def _verify_tunable_callback(cls, tunable_name, source, buff, participant, success_chance, timing):
        if buff.buff_type._temporary_commodity_info is None:
            logger.error('BuffFireAndForgetElement: {} has a buff element with a buff {} without a temporary commodity tuned.', cls, buff.buff_type)

    FACTORY_TUNABLES = {'buff': TunablePackSafeBuffReference(description='\n            A buff to be added to the Sim.\n            '), 'participant': TunableEnumEntry(description='\n            The Sim to give the buff to.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'verify_tunable_callback': _verify_tunable_callback}

    def _do_behavior(self, *args, **kwargs):
        if self.buff.buff_type is None:
            return
        participant = self.interaction.get_participant(self.participant)
        if participant is None:
            logger.error('Got a None participant trying to run a BuffFireAndForgetElement element.')
            return False
        participant.add_buff_from_op(self.buff.buff_type, buff_reason=self.buff.buff_reason)
