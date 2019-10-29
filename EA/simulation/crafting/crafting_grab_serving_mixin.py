import servicesfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableList, TunableReference, Tunable
class GrabServingMixin:
    INSTANCE_TUNABLES = FACTORY_TUNABLES = {'use_linked_recipe_mapping': Tunable(description='\n            If enabled, when creating the recipe, instead of using the base recipe it will look into \n            the recipe linked recipe tuning and find what recipes it can generate.\n            This is used to support multiple recipes generated from the same multiserve.\n            i.e. Ice cream carton can generate bowls, milkshakes and cones.\n            ', tunable_type=bool, default=False), 'use_base_recipe_on_setup': Tunable(description='\n            If enabled, the created serving will use the Base Object when being set up. \n            Otherwise, the recipe tuning will be used. In general, this  should stay checked. \n            Unchecking this is useful for objects like the Pit BBQ where a group serving is being pulled \n            from another group serving. The "Call to Meal" interactions will be forwarded correctly.\n            ', tunable_type=bool, default=True), 'transferred_stats': TunableList(description='\n            A list of stats to be copied over to the created object.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.STATISTIC), pack_safe=True)), 'transferred_states': TunableList(description='\n            A list of states to be copied over to the created object.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.OBJECT_STATE), pack_safe=True))}

    def _setup_crafted_object(self, recipe, servings_source, crafted_object):
        crafting_process = servings_source.get_crafting_process()
        if self.use_linked_recipe_mapping:
            crafting_process.recipe = recipe
        crafting_process.setup_crafted_object(crafted_object, use_base_recipe=self.use_base_recipe_on_setup, is_final_product=True, owning_household_id_override=servings_source.get_household_owner_id())
        self._setup_transferred_stats(servings_source, crafted_object)
        self._setup_transferred_states(servings_source, crafted_object)
        crafting_process.apply_simoleon_value(crafted_object, single_serving=True)
        for apply_state in reversed(recipe.final_product.apply_states):
            crafted_object.set_state(apply_state.state, apply_state)
        crafted_object.append_tags(recipe.apply_tags)

    def _setup_transferred_stats(self, serving_source, created_object):
        for stat in self.transferred_stats:
            tracker = serving_source.get_tracker(stat)
            value = tracker.get_value(stat)
            tracker = created_object.get_tracker(stat)
            tracker.set_value(stat, value)

    def _setup_transferred_states(self, serving_source, crafted_object):
        for state in self.transferred_states:
            state_value = serving_source.get_state(state)
            crafted_object.set_state(state, state_value)
