import services
class SimInfoFavoriteMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._favorite_recipes = []

    def get_favorite_recipe(self, recipe_tags):
        if not self._favorite_recipes:
            return
        if not recipe_tags:
            return self._favorite_recipes[0]
        for recipe in self._favorite_recipes:
            if recipe.recipe_tags & recipe_tags:
                return recipe

    def set_favorite_recipe(self, recipe):
        if recipe not in self._favorite_recipes:
            self._favorite_recipes.append(recipe)

    def save_favorite(self, favorite_data):
        for recipe in self._favorite_recipes:
            favorite_data.recipe_ids.append(recipe.guid64)

    def load_favorite(self, favorite_data):
        recipe_manager = services.recipe_manager()
        for recipe_id in favorite_data.recipe_ids:
            recipe = recipe_manager.get(recipe_id)
            if recipe is not None:
                self.set_favorite_recipe(recipe)
