from event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom interactions.rabbit_hole import RabbitHoleLiabilityfrom interactions.utils.statistic_element import ConditionalInteractionActionfrom rabbit_hole.tunable_rabbit_hole_condition import TunableRabbitHoleConditionfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunablePackSafeReference, TunableReference, TunableList, TunableTuple, Tunablefrom sims4.utils import flexmethodfrom statistics.statistic_conditions import TunableRabbitHoleExitConditionimport servicesimport sims4logger = sims4.log.Logger('Rabbit Hole Service', default_owner='rrodgers')
class RabbitHole(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.RABBIT_HOLE)):
    INSTANCE_TUNABLES = {'affordance': TunableReference(description=' \n            The rabbit hole affordance. This affordance must have a tuned rabbit\n            hole liability and must use a rabbit hole exit condition.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'away_action': TunableReference(description='\n            Away action for the rabbit holed sim info to run.\n            ', manager=services.get_instance_manager(sims4.resources.Types.AWAY_ACTION)), 'go_home_and_attend': TunableReference(description='\n            Sims who are not on the home lot will go home before entering the\n            rabbit hole. This is the interaction they will use.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('GoHomeTravelInteraction',)), 'loot_list': TunableList(description="\n            Loots to apply to rabbit holed sim after they leave the \n            rabbit hole. Won't be applied if the rabbit hole is cancelled.\n            ", tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), 'exit_conditions': TunableList(description='\n            A list of exit conditions for this rabbit hole. When exit\n            conditions are met then the rabbit hole ends.\n            ', tunable=TunableTuple(conditions=TunableList(description='\n                    A list of conditions that all must be satisfied for the\n                    group to be considered satisfied.\n                    ', tunable=TunableRabbitHoleCondition(description='\n                        A condition that must be satisfied.\n                        ')), tests=TunableTestSet(description='\n                    A set of tests. If these tests do not pass, this condition\n                    will not be attached.\n                    ')))}

    @classmethod
    def _verify_tuning_callback(cls):
        affordance = cls.affordance
        if not any(liability.factory is RabbitHoleLiability for liability in affordance.basic_liabilities):
            logger.error('Rabbit hole affordance: {}  must have a rabbit hole liability', affordance)

    def __init__(self, sim_id, alarm_handle=None, callbacks=None, linked_sim_ids=None):
        self.sim_id = sim_id
        self.alarm_handle = alarm_handle
        self.callbacks = callbacks
        if linked_sim_ids is None:
            self.linked_sim_ids = []
        else:
            self.linked_sim_ids = linked_sim_ids
        self.ignore_travel_cancel_callbacks = False

    @property
    def sim(self):
        return services.sim_info_manager().get(self.sim_id)

    @property
    def target(self):
        pass

    @flexmethod
    def get_participant(cls, inst, participant_type=ParticipantType.Actor, **kwargs):
        inst_or_cl = inst if inst is not None else cls
        participants = inst_or_cl.get_participants(participant_type=participant_type, **kwargs)
        if not participants:
            return
        if len(participants) > 1:
            raise ValueError('Too many participants returned for {}!'.format(participant_type))
        return next(iter(participants))

    @flexmethod
    def get_participants(cls, inst, participant_type, *args, **kwargs):
        if inst:
            sim_info = inst.sim
            if participant_type is ParticipantType.Actor:
                return (sim_info,)
            if participant_type is ParticipantType.Lot:
                (services.get_zone(sim_info.zone_id, allow_uninstantiated_zones=True),)
