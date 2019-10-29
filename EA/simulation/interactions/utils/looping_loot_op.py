from interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableReference, TunableSetimport servicesimport sims4.resources
class LoopingLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'loots_to_apply': TunableSet(description='\n            A list of loot action references to apply to each of the objects \n            specified by the subject participant type on this loop.\n            ', tunable=TunableReference(description='\n                A reference to a loot to apply to any object returned by \n                the specified ParticipantType in Subject. To reference the new\n                object that is the current object in the loop use the\n                ParticipantType.OBJECT option.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ACTION)))}

    def __init__(self, *args, loots_to_apply=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.loots_to_apply = loots_to_apply

    def _apply_to_subject_and_target(self, subject, target, resolver):
        new_resolver = resolver.interaction.get_resolver(target=subject)
        for loot in self.loots_to_apply:
            loot.apply_to_resolver(new_resolver)
