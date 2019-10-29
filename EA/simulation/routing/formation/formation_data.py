from distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import DoubleObjectResolverfrom event_testing.tests import TunableTestSetfrom routing.formation.formation_behavior import RoutingFormationBehaviorfrom routing.formation.formation_liability import RoutingFormationLiabilityfrom routing.formation.formation_type_follow import FormationTypeFollowfrom routing.formation.formation_type_paired import FormationTypePairedfrom routing.route_enums import RoutingStageEventfrom routing.walkstyle.walkstyle_request import WalkStyleRequestfrom routing.walkstyle.walkstyle_tuning import TunableWalkstylefrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableReference, TunableMapping, Tunable, TunableVariantfrom sims4.utils import classpropertyfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport servicesimport sims4.loglogger = sims4.log.Logger('RoutingFormations', default_owner='rmccord')
class RoutingFormation(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.snippet_manager()):
    INSTANCE_TUNABLES = {'formation_behavior': RoutingFormationBehavior.TunableFactory(), 'formation_routing_type': TunableVariant(description='\n            The purpose of the routing formation which governs how the slave\n            behaves on routes.\n            ', follow=FormationTypeFollow.TunableFactory(), paired=FormationTypePaired.TunableFactory(), default='follow'), 'formation_compatibility': TunableWhiteBlackList(description='\n            This routing formation is able to coexist with any other formation\n            listed here. For example, "Walk Dog" on the right side of a Sim is\n            compatible with "Walk Dog" on their left side (and vice-versa).\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('RoutingFormation',), pack_safe=True)), 'formation_tests': TunableTestSet(description='\n            A test set to determine whether or not the master and slave can be\n            in a formation together.\n            \n            Master: Participant Actor\n            Slave: Participant Slave\n            '), 'walkstyle_mapping': TunableMapping(description='\n            Mapping of Master walkstyles to Slave walkstyles. This is how we\n            ensure that slaves use a walkstyle to keep pace with their masters.\n            \n            Note you do not need to worry about combo replacement walkstyles\n            like GhostRun or GhostWalk. We get the first non-combo from the\n            master and apply the walkstyle to get any combos from the slave.\n            ', key_type=TunableWalkstyle(description='\n                The walkstyle that the master must be in to apply the value\n                walkstyle to the slave.\n                '), value_type=WalkStyleRequest.TunableFactory(), key_name='Master Walkstyle', value_name='Slave Walkstyle Request'), 'should_increase_master_agent_radius': Tunable(description="\n            If enabled, we combine the slave's agent radius with the master's.\n            ", tunable_type=bool, default=True), 'allow_slave_to_teleport_with_master': Tunable(description='\n            If enabled, when the master teleports using a teleport style, the \n            slave will also be teleported nearby.  If this is false, the master\n            cannot use teleport styles at all while they have a routing slave\n            using this data.\n            ', tunable_type=bool, default=False)}

    def __init__(self, master, slave, *args, interaction=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._master = master
        self._slave = slave
        self._interaction = interaction
        self._routing_type = self.formation_routing_type(self._master, self._slave, self.formation_type)
        self._formation_behavior = self.formation_behavior(master, slave)
        master.routing_component.add_routing_slave(self)
        if interaction is not None:
            formation_liability = RoutingFormationLiability(self)
            interaction.add_liability(formation_liability.LIABILITY_TOKEN, formation_liability)
        else:
            logger.callstack('Routing Formation created without an interaction, this should not happen. Slave: {} Master: {} Formation: {}', slave, master, self)
            self.release_formation_data()

    @classmethod
    def test_formation(cls, master, slave):
        resolver = DoubleObjectResolver(master, slave)
        return cls.formation_tests.run_tests(resolver)

    @classproperty
    def formation_type(cls):
        return cls

    @property
    def master(self):
        return self._master

    @property
    def slave(self):
        return self._slave

    @classproperty
    def max_slave_count(cls):
        return cls.formation_routing_type.factory.get_max_slave_count(cls.formation_routing_type)

    @property
    def offset(self):
        return self._routing_type.offset

    @property
    def route_length_minimum(self):
        return self._routing_type.route_length_minimum

    def on_add(self):
        self.master.register_routing_stage_event(RoutingStageEvent.ROUTE_START, self._on_master_route_start)
        self.master.register_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_master_route_end)
        self._formation_behavior.on_add()

    def on_release(self):
        self._routing_type.on_release()
        self._formation_behavior.on_release()
        self.master.unregister_routing_stage_event(RoutingStageEvent.ROUTE_START, self._on_master_route_start)
        self.master.unregister_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_master_route_end)

    def attachment_info_gen(self):
        yield from self._routing_type.attachment_info_gen()

    def _on_master_route_start(self, *_, **__):
        self._routing_type.on_master_route_start()

    def _on_master_route_end(self, *_, **__):
        self._routing_type.on_master_route_end()

    def get_routing_slave_constraint(self):
        return self._routing_type.get_routing_slave_constraint()

    def get_walkstyle_override(self):
        walkstyle_request = self.walkstyle_mapping.get(self.master.get_walkstyle())
        slaved_walkstyle = self._slave.get_walkstyle()
        if walkstyle_request is not None:
            with self._slave.routing_component.temporary_walkstyle_request(walkstyle_request):
                slaved_walkstyle = self._slave.get_walkstyle()
        return slaved_walkstyle

    def find_good_location_for_slave(self, master_location):
        return self._routing_type.find_good_location_for_slave(master_location)

    def add_routing_slave_to_pb(self, route_pb, path=None):
        slave_pb = route_pb.slaves.add()
        slave_pb.id = self._slave.id
        slave_pb.type = self._routing_type.slave_attachment_type
        walkstyle_override_msg = slave_pb.walkstyle_overrides.add()
        walkstyle_override_msg.from_walkstyle = 0
        walkstyle_override_msg.to_walkstyle = self.get_walkstyle_override()
        for (from_walkstyle, to_walkstyle_request) in self.walkstyle_mapping.items():
            walkstyle_override_msg = slave_pb.walkstyle_overrides.add()
            walkstyle_override_msg.from_walkstyle = from_walkstyle
            with self._slave.routing_component.temporary_walkstyle_request(to_walkstyle_request):
                walkstyle_override_msg.to_walkstyle = self._slave.get_walkstyle()
        for attachment_node in self.attachment_info_gen():
            with ProtocolBufferRollback(slave_pb.offset) as attachment_pb:
                attachment_node.populate_attachment_pb(attachment_pb)
        self._routing_type.build_routing_slave_pb(slave_pb, path=path)
        return (self._slave, slave_pb)

    def release_formation_data(self):
        self._routing_type.on_release()
        self._master.routing_component.clear_slave(self._slave)

    def should_slave_for_path(self, path):
        return self._routing_type.should_slave_for_path(path)

    def update_slave_position(self, master_transform, master_orientation, routing_surface, distribute=True, path=None, canceled=False):
        self._routing_type.update_slave_position(master_transform, master_orientation, routing_surface, distribute=distribute, path=path, canceled=canceled)
