from sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableList, TunableTuple, TunableReference, TunableRange, Tunablefrom snippets import define_snippetfrom tunable_multiplier import TunableMultiplierimport servicesimport sims4.loglogger = sims4.log.Logger('Fishing', default_owner='TrevorLindsey')
class FishingData(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'weight_fish': TunableMultiplier.TunableFactory(description='\n            A tunable list of tests and multipliers to apply to the weight \n            used to determine if the Sim will catch a fish instead of treasure \n            or junk. This will be used in conjunction with the Weight Junk and \n            Weight Treasure.\n            '), 'weight_junk': TunableMultiplier.TunableFactory(description='\n            A tunable list of tests and multipliers to apply to the weight\n            used to determine if the Sim will catch junk instead of a fish or \n            treasure. This will be used in conjunction with the Weight Fish and \n            Weight Treasure.\n            '), 'weight_treasure': TunableMultiplier.TunableFactory(description='\n            A tunable list of tests and multipliers to apply to the weight\n            used to determine if the Sim will catch a treasure instead of fish \n            or junk. This will be used in conjunction with the Weight Fish and \n            Weight Junk.\n            '), 'possible_treasures': TunableList(description="\n            If the Sim catches a treasure, we'll pick one of these based on their weights.\n            Higher weighted treasures have a higher chance of being caught.\n            ", tunable=TunableTuple(treasure=TunableReference(manager=services.definition_manager(), pack_safe=True), weight=TunableMultiplier.TunableFactory())), 'possible_fish': TunableList(description="\n            If the Sim catches a fish, we'll pick one of these based on their weights.\n            Higher weighted fish have a higher chance of being caught.\n            ", tunable=TunableTuple(fish=TunableReference(manager=services.definition_manager(), pack_safe=True), weight=TunableMultiplier.TunableFactory()), minlength=1)}

    def _verify_tuning_callback(self):
        import fishing.fish_object
        for fish in self.possible_fish:
            if not issubclass(fish.fish.cls, fishing.fish_object.Fish):
                logger.error("Possible Fish on Fishing Data has been tuned but there either isn't a definition tuned for the fish, or the definition currently tuned is not a Fish.\n{}", self)

    def get_possible_fish_gen(self):
        yield from self.possible_fish

    def choose_fish(self, resolver, require_bait=True):
        weighted_fish = [(f.weight.get_multiplier(resolver), f.fish) for f in self.possible_fish if f.fish.cls.can_catch(resolver, require_bait=require_bait)]
        if weighted_fish:
            return sims4.random.weighted_random_item(weighted_fish)

    def choose_treasure(self, resolver):
        weighted_treasures = [(t.weight.get_multiplier(resolver), t.treasure) for t in self.possible_treasures]
        if weighted_treasures:
            return sims4.random.weighted_random_item(weighted_treasures)
(TunableFishingDataReference, TunableFishingDataSnippet) = define_snippet('fishing_data', FishingData.TunableFactory())
class FishingBait(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'bait_name': TunableLocalizedStringFactory(description='\n            Name of fishing bait.\n            '), 'bait_description': TunableLocalizedStringFactory(description='\n            Description of fishing bait.\n            '), 'bait_icon_definition': TunableReference(description='\n            Object definition that will be used to render icon of fishing bait.\n            ', manager=services.definition_manager()), 'bait_buff': TunableReference(description='\n            Buff of fishing bait.\n            ', manager=services.buff_manager()), 'bait_priority': TunableRange(description='\n            The priority of the bait. When an object can be categorized into\n            multiple fishing bait categories, the highest priority category \n            will be chosen.\n            ', tunable_type=int, default=1, minimum=1)}
(TunableFishingBaitReference, _) = define_snippet('fishing_bait', FishingBait.TunableFactory())