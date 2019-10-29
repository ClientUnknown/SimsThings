from sims4.resources import Typesfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableSet, TunableReference, TunableVariantfrom tag import TunableTagsimport services
class _SituationMatchBase:

    def get_situations_for_sim_info(self, sim_info):
        sim = sim_info.get_sim_instance()
        if sim is None:
            return ()
        situation_manager = services.get_zone_situation_manager()
        situations = set(s for s in situation_manager.get_situations_sim_is_in(sim) if self.match(s))
        return situations

    def get_all_matching_situations(self):
        situation_manager = services.get_zone_situation_manager()
        situations = set(s for s in situation_manager.running_situations() if self.match(s))
        return situations

    def match(self, situation):
        raise NotImplementedError('Match must be implemented by subclasses of _SituationMatchBase!')

class SituationByDefinition(_SituationMatchBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'situations': TunableSet(description='\n            Situation types to match.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.SITUATION), pack_safe=True), minlength=1)}

    def match(self, situation):
        return type(situation) in self.situations

class SituationByTags(_SituationMatchBase, HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'situation_tags': TunableTags(description='\n            Situation tags to match.\n            \n            A situation that matches ANY of these tags will match.\n            ', filter_prefixes=('situation',), minlength=1)}

    def match(self, situation):
        return self.situation_tags & situation.tags

class SituationSearchByDefinitionOrTagsVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, by_definition=SituationByDefinition.TunableFactory(), by_tags=SituationByTags.TunableFactory(), default='by_definition', **kwargs)
