from element_utils import build_critical_section_with_finallyfrom interactions import ParticipantTypefrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableList, TunableTuple, TunableReference, TunableEnumEntry, TunableFactory, Tunableimport enumimport interactions.utilsimport servicesimport sims4.loglogger = sims4.log.Logger('Relationship')
class RelationshipBitOperationType(enum.Int):
    INVALID = 0
    ADD = 1
    REMOVE = 2

class RelationshipBitChange(BaseLootOperation):
    FACTORY_TUNABLES = {'bit_operations': TunableList(description='\n            List of operations to perform.\n            ', tunable=TunableTuple(description='\n                Tuple describing the operation to perform.\n                ', bit=TunableReference(description='\n                    The bit to be manipulated.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT)), operation=TunableEnumEntry(description='\n                    The operation to perform.\n                    ', tunable_type=RelationshipBitOperationType, default=RelationshipBitOperationType.INVALID, invalid_enums=(RelationshipBitOperationType.INVALID,)), recipients=TunableEnumEntry(description='\n                    The Sim(s) to apply the bit operation to.\n                    ', tunable_type=ParticipantType, default=ParticipantType.Invalid, invalid_enums=(ParticipantType.Invalid,)), targets=TunableEnumEntry(description='\n                    The target Sim(s) for each bit interaction.\n                    ', tunable_type=ParticipantType, default=ParticipantType.Invalid, invalid_enums=(ParticipantType.Invalid,)), allow_readdition=Tunable(description="\n                    If checked, will re-add a relbit to a relationship even if\n                    that relbit already exists in that relationship. If False,\n                    won't. This can affect applied loots, telemetry events, \n                    or other gameplay systems.\n                    ", tunable_type=bool, default=True))), 'locked_args': {'subject': ParticipantType.Invalid}}

    def __init__(self, bit_operations, **kwargs):
        super().__init__(**kwargs)
        self._bit_operations = bit_operations

    @property
    def subject(self):
        for bit_op in self._bit_operations:
            return bit_op.recipients

    @property
    def loot_type(self):
        return interactions.utils.LootType.RELATIONSHIP_BIT

    def apply_to_resolver(self, resolver, skip_test=False):
        if skip_test or not self.test_resolver(resolver):
            return (False, None)
        participant_cache = dict()
        for bit_operation in self._bit_operations:
            if bit_operation.recipients not in participant_cache:
                participant_cache[bit_operation.recipients] = resolver.get_participants(bit_operation.recipients)
            if bit_operation.targets not in participant_cache:
                participant_cache[bit_operation.targets] = resolver.get_participants(bit_operation.targets)
        for bit_operation in self._bit_operations:
            for recipient in participant_cache[bit_operation.recipients]:
                for target in participant_cache[bit_operation.targets]:
                    if recipient == target:
                        pass
                    elif recipient == ParticipantType.AllRelationships:
                        for recipient_sim_info in target.relationship_tracker.get_target_sim_infos():
                            self._perform_bit_operation(recipient_sim_info, target, bit_operation, allow_readdition=bit_operation.allow_readdition)
                    elif target == ParticipantType.AllRelationships:
                        for target_sim_info in recipient.relationship_tracker.get_target_sim_infos():
                            self._perform_bit_operation(recipient, target_sim_info, bit_operation, allow_readdition=bit_operation.allow_readdition)
                    else:
                        self._perform_bit_operation(recipient, target, bit_operation, allow_readdition=bit_operation.allow_readdition)
        return (True, None)

    def _perform_bit_operation(self, recipient, target, bit_operation, allow_readdition=True):
        if bit_operation.operation == RelationshipBitOperationType.ADD:
            recipient.relationship_tracker.add_relationship_bit(target.sim_id, bit_operation.bit, allow_readdition=allow_readdition)
        elif bit_operation.operation == RelationshipBitOperationType.REMOVE:
            recipient.relationship_tracker.remove_relationship_bit(target.sim_id, bit_operation.bit)
        else:
            raise NotImplementedError

class TunableRelationshipBitElement(TunableFactory):

    @staticmethod
    def _factory(interaction, relationship_bits_begin, relationship_bits_end, sequence=()):

        def begin(_):
            relationship_bits_begin.apply_to_resolver(interaction.get_resolver())

        def end(_):
            relationship_bits_end.apply_to_resolver(interaction.get_resolver())

        return build_critical_section_with_finally(begin, sequence, end)

    def __init__(self, description='A book-ended set of relationship bit operations.', **kwargs):
        super().__init__(relationship_bits_begin=RelationshipBitChange.TunableFactory(description='A list of relationship bit operations to perform at the beginning of the interaction.'), relationship_bits_end=RelationshipBitChange.TunableFactory(description='A list of relationship bit operations to performn at the end of the interaction'), description=description)

    FACTORY_TYPE = _factory
