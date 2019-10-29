from interactions import ParticipantTypeActorTargetSim, ParticipantTypeSinglefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom routing.formation.formation_data import RoutingFormationfrom sims4.tuning.tunable import TunableEnumEntry, TunableList
class RoutingFormationElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'master': TunableEnumEntry(description='\n            The Sim that is going to be followed.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'slave': TunableEnumEntry(description='\n            The Sim that will be doing the follow.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.TargetSim), 'routing_formations': TunableList(description='\n            The routing formations we want to use. We will test them in order\n            until the tests pass.\n            \n            Use this list to do things like minimize interactions based on\n            which hand you want to leash a dog with.\n            ', tunable=RoutingFormation.TunableReference(description='\n                The routing formation to use.\n                '), minlength=1)}

    def _do_behavior(self, *args, **kwargs):
        master = self.interaction.get_participant(self.master)
        if master is None:
            return False
        slave = self.interaction.get_participant(self.slave)
        if slave is None:
            return False
        else:
            for formation in self.routing_formations:
                if formation.test_formation(master, slave):
                    formation(master, slave, interaction=self.interaction)
                    break
            return False
        return True
