from collections import Counterfrom event_testing.results import TestResultfrom sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuningfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableRange, TunableList, TunableTuple, HasTunableSingletonFactory, AutoFactoryInit, TunableReference, TunableVariantimport event_testingimport services
class ItemCostBase:

    def consume_interaction_cost(self, interaction):

        def do_consume(*args, **kwargs):
            for item in self.ingredients:
                for _ in range(item.quantity):
                    if not interaction.sim.inventory_component.try_destroy_object_by_definition(item.ingredient, source=interaction, cause='Consuming the cost of the interaction'):
                        return False
            return True

        return do_consume

    def get_test_result(self, sim, cls):
        unavailable_items = Counter()
        for item in self.ingredients:
            item_count = sim.inventory_component.get_item_quantity_by_definition(item.ingredient)
            if item_count < item.quantity:
                unavailable_items[item.ingredient] += item.quantity - item_count
        if unavailable_items:
            tooltip = LocalizationHelperTuning.get_bulleted_list(ItemCost.UNAVAILABLE_TOOLTIP_HEADER(sim), tuple(LocalizationHelperTuning.get_object_count(count, item) for (item, count) in unavailable_items.items()))
            return event_testing.results.TestResult(False, "Sim doesn't have the required items in inventory.", tooltip=lambda *_, **__: tooltip)
        return TestResult.TRUE

    def get_interaction_tooltip(self, tooltip=None, sim=None):
        if self.ingredients:
            item_tooltip = LocalizationHelperTuning.get_bulleted_list(ItemCost.AVAILABLE_TOOLTIP_HEADER(sim), tuple(LocalizationHelperTuning.get_object_count(ingredient.quantity, ingredient.ingredient) for ingredient in self.ingredients))
            if tooltip is None:
                return item_tooltip
            else:
                return LocalizationHelperTuning.get_new_line_separated_strings(tooltip, item_tooltip)
        return tooltip

    def get_interaction_name(self, cls, display_name):
        if cls.ITEM_COST_NAME_FACTORY is not None:
            for item in self.ingredients:
                display_name = ItemCost.ITEM_COST_NAME_FACTORY(display_name, item.quantity, item.ingredient)
        return display_name

class ItemCost(ItemCostBase, AutoFactoryInit, HasTunableSingletonFactory):
    UNAVAILABLE_TOOLTIP_HEADER = TunableLocalizedStringFactory(description='\n        A string to be used as a header for a bulleted list of items that the\n        Sim is missing in order to run this interaction.\n        ')
    AVAILABLE_TOOLTIP_HEADER = TunableLocalizedStringFactory(description='\n        A string to be used as a header for a bulleted list of items that the\n        Sim will consume in order to run this interaction.\n        ')
    FACTORY_TUNABLES = {'ingredients': TunableList(description='\n            List of tuples of Objects and Quantity, which will indicate\n            the cost of items for this interaction to run\n            ', tunable=TunableTuple(description='\n                Pair of Object and Quantity needed for this interaction\n                ', ingredient=TunableReference(description='\n                    Object reference of the type of game object needed.\n                    ', manager=services.definition_manager()), quantity=TunableRange(description='\n                    Quantity of objects needed\n                    ', tunable_type=int, default=1, minimum=1)))}

class SpellCost(ItemCostBase, AutoFactoryInit, HasTunableSingletonFactory):
    FACTORY_TUNABLES = {'from_spell': TunableReference(description='The spell to pull ingredients from.', manager=services.get_instance_manager(Types.SPELL))}

    @property
    def ingredients(self):
        return self.from_spell.ingredients.ingredients

class InteractionItemCostVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, explicit_item_cost=ItemCost.TunableFactory(), spell_cost=SpellCost.TunableFactory(), default='explicit_item_cost', **kwargs)
