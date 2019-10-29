import randomfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactoryimport craftingimport sims4.loglogger = sims4.log.Logger('Interactions')
class PickerEnumerationStrategy(HasTunableSingletonFactory, AutoFactoryInit):

    def __init__(self):
        self._choices = None

    def build_choice_list(self, si, **kwargs):
        raise NotImplementedError

    def find_best_choice(self, si):
        if self._choices is None:
            logger.error('Calling PickerEnumerationStrategy.find_best_choice() without first calling build_choice_list()', owner='rez')
            return
        return random.choice(self._choices)

    @classmethod
    def has_valid_choice(self, target, context, state=None):
        raise NotImplementedError

    @property
    def choices(self):
        return self._choices

class StatePickerEnumerationStrategy(PickerEnumerationStrategy):

    def build_choice_list(self, si, state, **kwargs):
        self._choices = [client_state for client_state in si.target.get_client_states(state) if client_state.show_in_picker and client_state.test_channel(si.target, si.context)]

    def find_best_choice(self, si):
        if not self._choices:
            logger.error('Calling PickerEnumerationStrategy.find_best_choice() without first calling build_choice_list()', owner='rez')
            return
        weights = []
        for client_state in self._choices:
            weight = client_state.calculate_autonomy_weight(si.sim)
            weights.append((weight, client_state))
        logger.assert_log(weights, 'Failed to find choice in autonomous recipe picker', owner='rez')
        choice = sims4.random.pop_weighted(weights)
        return choice

    @classmethod
    def has_valid_choice(cls, target, context, state=None):
        for client_state in target.get_client_states(state):
            if client_state.show_in_picker and client_state.test_channel(target, context):
                return True
        return False

class RecipePickerEnumerationStrategy(PickerEnumerationStrategy):

    def build_choice_list(self, si, **kwargs):
        self._choices = [recipe for recipe in si.recipes]

    def find_best_choice(self, si):
        if self._choices is None:
            logger.error('Calling PickerEnumerationStrategy.find_best_choice() without first calling build_choice_list()', owner='rez')
            return
        weights = []
        for recipe in self._choices:
            if recipe.all_ingredients_required:
                pass
            else:
                result = crafting.crafting_process.CraftingProcess.recipe_test(si.target, si.context, recipe, si.sim, 0, build_error_list=False, from_autonomy=True)
                if result:
                    weights.append((recipe.calculate_autonomy_weight(si.sim), recipe))
        if not weights:
            logger.error('Failed to find choice in autonomous recipe picker', owner='rez')
            return
        choice = sims4.random.pop_weighted(weights)
        return choice

class SimPickerEnumerationStrategy(PickerEnumerationStrategy):

    def build_choice_list(self, si, sim, test_function=None, **kwargs):
        self._choices = [filter_result for filter_result in si._get_valid_sim_choices_gen(si.target, si.context, test_function=test_function, **kwargs)]

    def find_best_choice(self, si):
        weights = [(filter_result.score, filter_result.sim_info.id) for filter_result in self._choices]
        choice = sims4.random.pop_weighted(weights)
        return choice

class LotPickerEnumerationStrategy(PickerEnumerationStrategy):

    def build_choice_list(self, si, sim, **kwargs):
        self._choices = [filter_result for filter_result in si._get_valid_lot_choices(si.target, si.context)]

    def find_best_choice(self, si):
        choice = random.choice(self._choices)
        return choice

class ObjectPickerEnumerationStrategy(PickerEnumerationStrategy):

    def __init__(self):
        super().__init__()
        self._gen_objects = None

    def build_choice_list(self, si, sim, get_all=False, **kwargs):
        if get_all:
            self._gen_objects = [obj for obj in si._get_objects_with_results_gen(si.target, si.context)]
            self._choices = [obj for (obj, results) in self._gen_objects for (result, _) in results if result]
        else:
            self._choices = [obj for obj in si._get_objects_gen(si.target, si.context)]

    def get_gen_objects(self, **kwargs):
        return self._gen_objects

    def find_best_choice(self, si):
        if not self._choices:
            return
        choice = random.choice(self._choices)
        return choice
