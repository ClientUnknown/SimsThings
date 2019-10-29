from interactions import ParticipantTypefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom interactions.utils.loot import LootActions, LootOperationListfrom sims4.tuning.tunable import TunableList, OptionalTunablefrom tunable_utils.tunable_object_generator import TunableObjectGeneratorVariant
class LootElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'loot_list': TunableList(description='\n            A list of loot operations.\n            ', tunable=LootActions.TunableReference(pack_safe=True)), 'object_override': OptionalTunable(description='\n            If disabled, this loot is executed once, and all participants tuned\n            in the various actions are retrieved from the owning interaction.\n            \n            If enabled, this loot is executed once for each of the generated\n            objects. The Object participant corresponds to this object. All\n            other participants (e.g. Actor) are retrieved from the owning\n            interaction.\n            ', tunable=TunableObjectGeneratorVariant(participant_default=ParticipantType.ObjectChildren))}

    def _do_behavior(self, *args, **kwargs):
        if self.object_override is None:
            resolver = self.interaction.get_resolver()
            loots = (LootOperationList(resolver, self.loot_list),)
        else:
            loots = []
            for obj in self.object_override.get_objects(self.interaction):
                resolver = self.interaction.get_resolver(target=obj)
                loots.append(LootOperationList(resolver, self.loot_list))
        for loot in loots:
            loot.apply_operations()
