from collections import namedtuplefrom objects.components.state import ObjectStateValuefrom objects.gardening.gardening_tuning import GardeningTuningfrom sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuning, TunableLocalizedStringfrom sims4.tuning.tunable import TunableMapping, TunableTuple, Tunable, TunableList, TunableEnumEntry, TunableReference, TunableRange, HasTunableFactory, TunableFactoryimport enumimport servicesimport tag
class IngredientTooltipStyle(enum.Int):
    DEFAULT_MISSING_INGREDIENTS = 0
    DISPLAY_RECIPE_DESCRIPTION = 1

class IngredientTuning:
    INGREDIENT_QUALITY_MAPPING = TunableMapping(description='\n        Mapping of all possible ingredient quality states to what possible\n        states will the ingredients have.\n        e.g. High quality ingredients need to be mapped to gardening high \n        quality, fish high quality or any state that will indicate what \n        high quality means on a different system.\n        ', key_type=ObjectStateValue.TunableReference(description='\n            The states that will define the ingredient quality.\n            '), value_type=TunableTuple(description='\n            Definition of the ingredient quality state.  This will define\n            the quality boost on the recipe and the possible states an \n            ingredient can have to have this state.\n            ', quality_boost=Tunable(description='\n                Value that will be added to the quality commodity whenever\n                this state is added.\n                ', tunable_type=int, default=1), state_value_list=TunableList(description='\n                List of ingredient states that will give this level of \n                ingredient quality.\n                ', tunable=ObjectStateValue.TunableReference(description='\n                    The states that will define the ingredient quality.\n                    '))))
    INGREDIENT_TAG_DISPLAY_MAPPING = TunableMapping(description='\n        Mapping of all object tags to their localized string that will display\n        on the ingredient list.\n        This will be used for displaying on the recipe\'s when an ingredient is \n        tuned by tag instead of object definition.\n        Example: Display objects of rag FISH as string "Any Fish"\n        ', key_type=TunableEnumEntry(description='\n            Tag corresponding at an ingredient type that can be used in a\n            recipe.\n            ', tunable_type=tag.Tag, default=tag.Tag.INVALID, pack_safe=True), value_type=TunableLocalizedStringFactory())
    INGREDIENT_TAG = TunableEnumEntry(description='\n        Tag to look for when iterating through objects to know if they are \n        ingredients.\n        All ingredients should be tuned with this tag.\n        ', tunable_type=tag.Tag, default=tag.Tag.INVALID)
    SINGLE_INGREDIENT_TYPE_STRING = TunableLocalizedStringFactory(description='\n        The string that contains an ingredient and how much of it the sim has\n        access to. This will be shown in tooltips for pie menu recipe\n        interactions. \n        Example: "{0.String} - ({1.Number}/{2.Number})"\n        Tokens: \n        0 - ingredient string \n        1 - number owned \n        2 - number needed\n        ')
    RECIPE_COMPLETE_INGREDIENT_STRING = TunableLocalizedStringFactory(description='\n        The string for having all of one ingredient type needed for a recipe.\n        This will be shown on tooltips of pie menu recipe interactions.\n        Example: "<span class="hasIngredients">{0.String}</span>" \n        Tokens: \n        0 - String containing an ingredient and how many you own/need.\n        ')
    RECIPE_INCOMPLETE_INGREDIENT_STRING = TunableLocalizedStringFactory(description='\n        The string for not having all of one ingredient type needed for a recipe.\n        This will be shown on tooltips of pie menu recipe interactions.\n        Example: "<span class="noIngredients">{0.String}</span>" \n        Tokens: \n        0 - String containing an ingredient and how many you own/need.\n        ')
    REQUIRED_INGREDIENT_LIST_STRING = TunableLocalizedStringFactory(description='\n        The string for requiring a list of ingredients.\n        This will be shown on tooltips of pie menu recipe interactions.\n        Example: "Required: {0.String}" \n        Tokens: \n        0 - String containing a list of ingredients.\n        ')
    OPTIONAL_INGREDIENT_LIST_STRING = TunableLocalizedStringFactory(description='\n        The string for having an optional list of ingredients.\n        This will be shown on tooltips of pie menu recipe interactions.\n        Example: "Optional: {0.String}" \n        Tokens: \n        0 - String containing a list of ingredients.\n        ')

    @classmethod
    def get_quality_bonus(cls, ingredient):
        for quality_details in IngredientTuning.INGREDIENT_QUALITY_MAPPING.values():
            for state_value in quality_details.state_value_list:
                if ingredient.has_state(state_value.state) and ingredient.state_value_active(state_value):
                    return quality_details.quality_boost
        return 0

    @classmethod
    def get_ingredient_quality_state(cls, quality_bonus):
        state_to_add = None
        bonus_selected = None
        for (quality_state_value, quality_details) in IngredientTuning.INGREDIENT_QUALITY_MAPPING.items():
            if not bonus_selected is None:
                if quality_details.quality_boost <= bonus_selected and bonus_selected >= quality_bonus:
                    bonus_selected = quality_details.quality_boost
                    state_to_add = quality_state_value
            bonus_selected = quality_details.quality_boost
            state_to_add = quality_state_value
        return state_to_add

    @classmethod
    def get_ingredient_string_for_tag(cls, tag):
        string_factory = IngredientTuning.INGREDIENT_TAG_DISPLAY_MAPPING.get(tag)
        if string_factory:
            return string_factory()
        else:
            return
IngredientDisplayData = namedtuple('IngredientDisplayData', ('ingredient_name', 'is_in_inventory'))
class IngredientProcessOrder(enum.Int, export=False):
    NONE = 0
    DEFINITION = 1
    TAG = 2

class Ingredient:

    def __init__(self, obj, count):
        self.obj_ref = obj.ref()
        self.count = count

    @property
    def ingredient_object(self):
        if self.obj_ref is not None:
            return self.obj_ref()

    @ingredient_object.setter
    def ingredient_object(self, obj):
        self.obj_ref = obj.ref()

    def get_cumulative_quality(self, ingredient_logger):
        quality_level = self.get_quality_level()
        ingredient_logger.append({'ingredient': str(self.ingredient_object) if self.obj_ref is not None else '', 'quality': str(quality_level), 'count': str(self.count)})
        return quality_level*self.count

    def get_quality_level(self):
        obj = self.ingredient_object
        if obj is not None:
            return IngredientTuning.get_quality_bonus(obj)
        return 0

class IngredientRequirement(HasTunableFactory):
    FACTORY_TUNABLES = {'count': TunableRange(description='\n            The number of this ingredient allowed/required.\n            ', tunable_type=int, minimum=1, default=1)}

    def __init__(self, *args, count=1, **kwargs):
        super().__init__(*args, **kwargs)
        self._count_required = count
        self._count_using = 0
        self._ingredients = []

    @property
    def count_required(self):
        return self._count_required

    @property
    def count_satisfied(self):
        return self._count_using

    @property
    def count_unsatisfied(self):
        return self.count_required - self.count_satisfied

    @property
    def satisfied(self):
        return not self.count_unsatisfied

    @classmethod
    def get_sort_index(cls):
        return IngredientProcessOrder.NONE

    def get_diplay_name(self):
        raise NotImplementedError

    def get_display_info(self):
        display_info = IngredientTuning.SINGLE_INGREDIENT_TYPE_STRING(self.get_diplay_name(), self._count_using, self._count_required)
        if self.satisfied:
            return IngredientTuning.RECIPE_COMPLETE_INGREDIENT_STRING(display_info)
        else:
            return IngredientTuning.RECIPE_INCOMPLETE_INGREDIENT_STRING(display_info)

    def get_display_data(self):
        return IngredientDisplayData(self.get_display_info(), self.satisfied)

    def _is_valid_ingredient(self, ingredient_obj):
        return not GardeningTuning.is_unidentified(ingredient_obj)

    def get_cumulative_quality(self, ingredient_logger):
        return sum(ingredient.get_cumulative_quality(ingredient_logger) for ingredient in self._ingredients)

    def check_ingredients_used(self, ingredients_used):
        valid_ingredients = []
        for ingredient in self._ingredients:
            ingredient_obj = ingredient.ingredient_object
            if ingredient_obj is not None:
                current_count = ingredients_used.get(ingredient_obj, 0)
                count_using = ingredient.count + current_count
                ingredients_used[ingredient_obj] = count_using
                valid_ingredients.append(ingredient)
            else:
                self._count_using -= ingredient.count
        self._ingredients = valid_ingredients

    def _attempt_use_ingredient(self, ingredient_obj, ingredients_used):
        count_using = ingredients_used.get(ingredient_obj, 0)
        count_leftover = ingredient_obj.stack_count() - count_using
        if count_leftover:
            count_usable = count_leftover if self.count_unsatisfied >= count_leftover else self.count_unsatisfied
            ingredient_instance = Ingredient(ingredient_obj, count_usable)
            self._ingredients.append(ingredient_instance)
            self._count_using += ingredient_instance.count
            ingredients_used[ingredient_obj] = count_using + count_usable

    def attempt_satisfy_ingredients(self, candidate_ingredients, ingredients_used):
        for ingredient_obj in candidate_ingredients:
            if self._is_valid_ingredient(ingredient_obj):
                self._attempt_use_ingredient(ingredient_obj, ingredients_used)
            if self.satisfied:
                break

class IngredientRequirementByDef(IngredientRequirement):

    @TunableFactory.factory_option
    def ingredient_override(pack_safe=False):
        return {'ingredient_ref': TunableReference(description='\n                Reference to ingredient object definition.\n                Example: gardenFruitGENOnion_01\n                ', manager=services.definition_manager(), pack_safe=pack_safe)}

    def __init__(self, *args, ingredient_ref=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._definition = ingredient_ref

    def _is_valid_ingredient(self, ingredient_obj):
        if not super()._is_valid_ingredient(ingredient_obj):
            return False
        return ingredient_obj.definition is self._definition

    def get_diplay_name(self):
        return LocalizationHelperTuning.get_object_name(self._definition)

    @classmethod
    def get_sort_index(cls):
        return IngredientProcessOrder.DEFINITION

    def get_ingredient_count_in_inventory(self, inventory_owner):
        return inventory_owner.get_count(self._definition)

class IngredientRequirementByTag(IngredientRequirement):
    FACTORY_TUNABLES = {'ingredient_tag': TunableEnumEntry(description='\n            Tag that ingredient object should have.\n            Example: Func_Ingredient_Fruit\n            ', tunable_type=tag.Tag, default=tag.Tag.INVALID)}

    def __init__(self, *args, ingredient_tag=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._tag = ingredient_tag

    def _is_valid_ingredient(self, ingredient_obj):
        if not super()._is_valid_ingredient(ingredient_obj):
            return False
        return ingredient_obj.definition.has_build_buy_tag(self._tag)

    def get_diplay_name(self):
        return IngredientTuning.get_ingredient_string_for_tag(self._tag)

    @classmethod
    def get_sort_index(cls):
        return IngredientProcessOrder.TAG

    def get_ingredient_count_in_inventory(self, inventory_owner):
        return inventory_owner.get_count_by_tag(self._tag)
