from interactions import ParticipantTypefrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableReference, TunableSet, TunableEnumEntry, OptionalTunableimport servicesimport sims4.resources
class ScheduleDramaNodeLoot(BaseLootOperation):
    FACTORY_TUNABLES = {'drama_node': TunableReference(description='\n            The drama node to schedule.\n            ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE))}

    def __init__(self, drama_node, **kwargs):
        super().__init__(**kwargs)
        self._drama_node = drama_node

    def _apply_to_subject_and_target(self, subject, target, resolver):
        services.drama_scheduler_service().schedule_node(self._drama_node, resolver)

class CancelScheduledDramaNodeLoot(BaseLootOperation):
    FACTORY_TUNABLES = {'drama_nodes': TunableSet(description='\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE))), 'receiver': TunableEnumEntry(description='\n            The recipient of the drama node.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'sender': OptionalTunable(description='\n            The sender of the drama node. Can be left unspecified if there is\n            no sender.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.TargetSim)), 'locked_args': {'subject': None}}

    def __init__(self, drama_nodes, receiver, sender, **kwargs):
        super().__init__(**kwargs)
        self._drama_nodes = drama_nodes
        self._receiver_type = receiver
        self._sender_type = sender

    def _apply_to_subject_and_target(self, subject, target, resolver):
        receiver = resolver.get_participant(self._receiver_type)
        sender = resolver.get_participant(self._sender_type) if self._sender_type is not None else None
        dss = services.drama_scheduler_service()
        for node in tuple(dss.scheduled_nodes_gen()):
            sender_passed = self._sender_type is None or node.get_sender_sim_info() is sender
            if type(node) in self._drama_nodes and node.get_receiver_sim_info() is receiver and sender_passed:
                dss.cancel_scheduled_node(node.uid)
