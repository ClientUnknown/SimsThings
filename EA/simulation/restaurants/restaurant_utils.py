from protocolbuffers import Restaurant_pb2from business.business_enums import BusinessTypefrom event_testing.resolver import SingleSimResolverfrom restaurants.restaurant_tuning import RestaurantTuning, get_restaurant_zone_directorfrom tunable_multiplier import TunableMultiplierimport services
class RestaurantUtils:
    MEAL_COST_MULTIPLIERS = TunableMultiplier.TunableFactory(description='\n        Multipliers used to change the value of things in a menu and for the\n        overall cost of the meal.\n        \n        If any member of the party meets the requirement of the multiplier then\n        the multiplier is applied once. The benefit will not be applied for \n        each Sim in the group that meets the multiplier tests.\n        ')

def get_chef_situation(chef_sim=None):
    situation_manager = services.get_zone_situation_manager()
    if chef_sim is not None:
        situations = situation_manager.get_situations_sim_is_in(chef_sim)
    else:
        situations = situation_manager.running_situations()
    for situation in situations:
        if type(situation) is RestaurantTuning.CHEF_SITUATION:
            return situation
        if RestaurantTuning.HOME_CHEF_SITUATION_TAG in situation.tags:
            return situation

def get_waitstaff_situation(waitstaff_sim=None):
    situation_manager = services.get_zone_situation_manager()
    if waitstaff_sim is not None:
        situations = situation_manager.get_situations_sim_is_in(waitstaff_sim)
    else:
        situations = situation_manager.running_situations()
    for situation in situations:
        if type(situation) is RestaurantTuning.WAITSTAFF_SITUATION:
            return situation

def get_menu_message(menu_map, group_sim_ids, chef_order=False, daily_special_ids_map=None, is_recommendation=False):
    show_menu_message = Restaurant_pb2.ShowMenu()
    menu = Restaurant_pb2.Menu()
    active_household = services.active_household()
    if active_household is not None:
        holiday_multiplier = active_household.holiday_tracker.get_active_holiday_business_price_multiplier(BusinessType.RESTAURANT)
    else:
        holiday_multiplier = 1.0
    tested_meal_cost_multiplier = tested_cost_multipliers_for_group(group_sim_ids)
    for (course_enum, recipes) in menu_map:
        course_item = menu.courses.add()
        course_item.course_tag = course_enum
        daily_special_ids = daily_special_ids_map.get(course_enum, None) if daily_special_ids_map else None
        for recipe in recipes:
            recipe_item = course_item.items.add()
            recipe_item.recipe_id = recipe.guid64
            is_daily_special = recipe.guid64 == daily_special_ids
            recipe_item.item_type = 1 if is_daily_special else 0
            price = recipe.restaurant_base_price
            price *= holiday_multiplier
            price *= tested_meal_cost_multiplier
            if is_daily_special:
                price *= RestaurantTuning.DAILY_SPECIAL_DISCOUNT
            zone_director = get_restaurant_zone_director()
            if zone_director:
                business_manager = services.business_service().get_business_manager_for_zone()
                if business_manager is not None:
                    price = business_manager.get_value_with_markup(price)
                else:
                    price *= RestaurantTuning.UNOWNED_RESTAURANT_PRICE_MULTIPLIER
            recipe_item.price_override = int(price)
    show_menu_message.menu = menu
    show_menu_message.sim_ids.extend(group_sim_ids)
    show_menu_message.chef_order = chef_order
    show_menu_message.recommend_order = is_recommendation
    return show_menu_message

def food_on_table_gen(table_id):
    slot_types = {RestaurantTuning.TABLE_FOOD_SLOT_TYPE, RestaurantTuning.TABLE_DRINK_SLOT_TYPE}
    object_manager = services.object_manager()
    table = object_manager.get(table_id)
    if table is None:
        return
    for table_part in table.parts:
        for runtime_slot in table_part.get_runtime_slots_gen(slot_types=slot_types):
            yield from runtime_slot.children

def tested_cost_multipliers_for_group(group_sim_ids):
    cost_multiplier = RestaurantUtils.MEAL_COST_MULTIPLIERS.base_value
    sim_info_manager = services.sim_info_manager()
    group_sim_info_resolvers = {}
    for sim_id in group_sim_ids:
        sim_info = sim_info_manager.get(sim_id)
        if sim_info is not None:
            group_sim_info_resolvers[sim_info] = SingleSimResolver(sim_info)
    for multiplier in RestaurantUtils.MEAL_COST_MULTIPLIERS.multipliers:
        for (sim_info, resolver) in group_sim_info_resolvers.items():
            if multiplier.tests.run_tests(resolver):
                cost_multiplier *= multiplier.multiplier
                break
    return cost_multiplier
