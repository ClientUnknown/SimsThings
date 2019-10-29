from distributor.system import Distributorfrom restaurants import restaurant_utils, restaurant_uifrom restaurants.chef_situation import ChefSituationfrom restaurants.restaurant_tuning import MenuPresets, RestaurantTuningfrom sims4.tuning.tunable import TunableEnumEntryHOME_CHEF_GROUP = 'HomeChef'
class HomeChefSituation(ChefSituation):
    INSTANCE_TUNABLES = {'menu_preset': TunableEnumEntry(description='\n            The MenuPreset that this Chef should use.\n            ', tunable_type=MenuPresets, default=MenuPresets.CUSTOMIZE, invalid_enums=(MenuPresets.CUSTOMIZE,), tuning_group=HOME_CHEF_GROUP)}

    def show_menu(self, sim):
        menu_items = RestaurantTuning.MENU_PRESETS[self.menu_preset].recipe_map.items()
        show_menu_message = restaurant_utils.get_menu_message(menu_items, (sim.id,), chef_order=True)
        Distributor.instance().add_op_with_no_owner(restaurant_ui.ShowMenu(show_menu_message))
