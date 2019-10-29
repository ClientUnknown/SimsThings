from protocolbuffers import Restaurant_pb2from event_testing import test_eventsfrom google.protobuf import text_formatfrom restaurants import restaurant_utilsfrom restaurants.chefs_choice import ChefsChoicefrom restaurants.restaurant_diner_situation import DinerSubSituationState, RestaurantDinerSubSituation, RestaurantDinerBackGroundSituationfrom restaurants.restaurant_order import OrderStatus, OrderRecommendationState, GroupOrderfrom restaurants.restaurant_tuning import RestaurantTuning, RestaurantIngredientQualityType, get_restaurant_zone_directorfrom server_commands.argument_helpers import TunableInstanceParam, OptionalTargetParam, get_optional_targetfrom sims import simfrom sims4.protocol_buffer_utils import has_fieldimport servicesimport sims4.commands
@sims4.commands.Command('restaurant.order_food', command_type=sims4.commands.CommandType.Live)
def order_food(recipe_type:TunableInstanceParam(sims4.resources.Types.RECIPE), opt_sim:OptionalTargetParam=None, _connection=None):
    if recipe_type is None:
        sims4.commands.output('Recipe is None', _connection)
        sims4.commands.automation_output('RestaurantOrderFood; Status:Failed', _connection)
        return False
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Sim {} doesn't exist".format(opt_sim), _connection)
        sims4.commands.automation_output('RestaurantOrderFood; Status:Failed', _connection)
        return False
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('Current venue is not restaurant', _connection)
        sims4.commands.automation_output('RestaurantOrderFood; Status:Failed', _connection)
        return False
    zone_director.make_one_order(sim, recipe_type)
    groups = zone_director.get_dining_groups_by_sim(sim)
    if groups is None:
        sims4.commands.output('Sim {} is not in dining group'.format(opt_sim), _connection)
        sims4.commands.automation_output('RestaurantOrderFood; Status:Failed', _connection)
    group = groups.pop()
    group.hold_ordered_cost(recipe_type.restaurant_base_price)
    sims4.commands.automation_output('RestaurantOrderFood; Status:Success', _connection)
    return True

@sims4.commands.Command('restaurant.show_menu', command_type=sims4.commands.CommandType.Live)
def show_menu(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Sim {} doesn't exist".format(opt_sim), _connection)
        return False
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('Current venue is not restaurant', _connection)
        return False
    zone_director.show_menu(sim)

@sims4.commands.Command('restaurant.show_menu_for_chef', command_type=sims4.commands.CommandType.Live)
def show_menu_for_chef(opt_sim:OptionalTargetParam=None, chef_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Sim {} doesn't exist".format(opt_sim), _connection)
        return False
    chef_sim = get_optional_target(chef_sim, _connection)
    if chef_sim is None:
        sims4.commands.output("Chef {} doesn't exist.".format(chef_sim), _connection)
        return False
    chef_situation = restaurant_utils.get_chef_situation(chef_sim=chef_sim)
    if chef_situation is None:
        sims4.commands.output("Couldn't find a Chef Situation in this zone.")
        return False
    chef_situation.show_menu(sim)

@sims4.commands.Command('restaurant.show_recommendation_menu_for_sim', command_type=sims4.commands.CommandType.Live)
def show_recommendation_menu_for_sim(opt_sim:OptionalTargetParam=None, owner_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Sim {} doesn't exist".format(opt_sim), _connection)
        return False
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('Current venue is not restaurant', _connection)
        return False
    zone_director.show_menu(sim, is_recommendation=True)

@sims4.commands.Command('restaurant.claim_table', command_type=sims4.commands.CommandType.Live)
def claim_table(opt_sim:OptionalTargetParam=None, opt_table:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Sim {} doesn't exist".format(opt_sim), _connection)
        return False
    table_to_claim = get_optional_target(opt_table, _connection)
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('Current venue is not restaurant', _connection)
        return False
    zone_director.claim_table(sim, table_to_claim)

@sims4.commands.Command('restaurant.order_for_table', command_type=sims4.commands.CommandType.Live)
def order_for_table(sim_orders:str, _connection=None):
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('Current venue is not restaurant', _connection)
        return False
    proto = Restaurant_pb2.SimOrders()
    text_format.Merge(sim_orders, proto)
    orders = [(order.sim_id, order.recipe_id) for order in proto.sim_orders]
    sim = services.object_manager().get(orders[0][0])
    if sim is None:
        sims4.commands.output("Trying to order for a Sim that isn't on the lot", _connection)
        return False
    zone_director.order_for_table(orders)
    groups = zone_director.get_dining_groups_by_sim(sim)
    group = groups.pop()
    group.hold_ordered_cost(proto.meal_cost if has_field(proto, 'meal_cost') else 0)
    return True

@sims4.commands.Command('restaurant.comp_drinks_for_group', command_type=sims4.commands.CommandType.Live)
def comp_drinks_for_group(opt_sim:OptionalTargetParam=None, _connection=None):
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('Current venue is not restaurant', _connection)
        return False
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Sim {} doesn't exist".format(opt_sim), _connection)
        return False
    groups = zone_director.get_dining_groups_by_sim(sim)
    group = groups.pop()
    group.order_course_for_group(ChefsChoice.DRINK_COURSE, complimentary=True)
    return True

@sims4.commands.Command('restaurant.comp_desserts_for_group', command_type=sims4.commands.CommandType.Live)
def comp_desserts_for_group(opt_sim:OptionalTargetParam=None, _connection=None):
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('Current venue is not restaurant', _connection)
        return False
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Sim {} doesn't exist".format(opt_sim), _connection)
        return False
    groups = zone_director.get_dining_groups_by_sim(sim)
    group = groups.pop()
    group.order_course_for_group(ChefsChoice.DESSERT_COURSE, complimentary=True)
    return True

@sims4.commands.Command('restaurant.recommend_order_for_table', command_type=sims4.commands.CommandType.Live)
def recommend_order_for_table(sim_orders:str, _connection=None):
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('Current venue is not restaurant', _connection)
        return False
    proto = Restaurant_pb2.SimOrders()
    text_format.Merge(sim_orders, proto)
    orders = [(order.sim_id, order.recipe_id) for order in proto.sim_orders]
    sims_in_order = set([services.object_manager().get(order_sim_id) for order_sim_id in [order[0] for order in orders]])
    for sim in sims_in_order:
        if sim is None:
            sims4.commands.output("Trying to target order for a Sim that isn't on the lot", _connection)
            return False
        active_group_order = _get_active_group_order_for_dining_group(sim)
    if active_group_order:
        recipe_manager = services.get_instance_manager(sims4.resources.Types.RECIPE)
        for order in orders:
            recipe = recipe_manager.get(order[1])
            recipes = GroupOrder.get_food_drink_recipe_id_tuple(recipe)
            active_group_order.add_sim_order(order[0], food_recipe_id=recipes[0], drink_recipe_id=recipes[1], recommendation_state=OrderRecommendationState.RECOMMENDATION_PROPOSAL, order_status=OrderStatus.ORDER_INIT)
    else:
        zone_director.order_for_table(orders, send_order=False, recommendation_state=OrderRecommendationState.RECOMMENDATION_PROPOSAL, order_status=OrderStatus.ORDER_INIT)
    groups = zone_director.get_dining_groups_by_sim(sim)
    group = groups.pop()
    group.hold_ordered_cost(proto.meal_cost if has_field(proto, 'meal_cost') else 0)
    for sim in sims_in_order:
        zone_director.trigger_recommendation_interaction(services.get_active_sim(), sim)
    return True

@sims4.commands.Command('restaurant.npc_accept_or_reject_recommendation', command_type=sims4.commands.CommandType.Live)
def npc_accept_or_reject_recommendation(opt_sim:OptionalTargetParam=None, accept_recommendation:bool=True, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Sim {} doesn't exist.".format(opt_sim), _connection)
        return False
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('Current venue is not restaurant', _connection)
        return False
    group_order = zone_director.get_active_group_order_for_sim(sim.sim_id)
    if group_order is None:
        sims4.commands.output('Sim {} was not offered a recommendation.'.format(opt_sim), _connection)
        return False
    if accept_recommendation:
        sim_order = group_order.get_sim_order(sim.sim_id)
        if sim_order is not None:
            sim_order.recommendation_state = OrderRecommendationState.RECOMMENDATION_ACCEPTED
    else:
        group_order.remove_sim_order(sim.sim_id)
        (food_recipe, drink_recipe) = ChefsChoice.get_order_for_npc_sim(sim)
        group_order.add_sim_order(sim.sim_id, food_recipe_id=food_recipe.guid64, drink_recipe_id=drink_recipe.guid64, recommendation_state=OrderRecommendationState.RECOMMENDATION_REJECTED, order_status=OrderStatus.ORDER_INIT)
    return True

@sims4.commands.Command('restaurant.order_food_at_chef_station', command_type=sims4.commands.CommandType.Live)
def order_food_at_chef_station(recipe_type:TunableInstanceParam(sims4.resources.Types.RECIPE), opt_sim:OptionalTargetParam=None, _connection=None):
    if recipe_type is None:
        sims4.commands.output('Recipe is None', _connection)
        return False
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Sim {} doesn't exist.".format(opt_sim), _connection)
        return False
    chef_situation = restaurant_utils.get_chef_situation()
    if chef_situation is None:
        sims4.commands.output("Couldn't find a Chef Situation in this zone.")
        return False
    chef_situation.add_direct_order(recipe_type, sim)
    services.get_event_manager().process_event(test_events.TestEvent.RestaurantFoodOrdered, sim_info=sim.sim_info)
    return True

@sims4.commands.Command('restaurant.npc_order_food_at_chef_station', command_type=sims4.commands.CommandType.Live)
def npc_order_food_at_chef_station(opt_sim:OptionalTargetParam=None, chef_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Sim {} doesn't exist.".format(opt_sim), _connection)
        return False
    chef_sim = get_optional_target(chef_sim, _connection)
    if chef_sim is None:
        sims4.commands.output("Chef {} doesn't exist.".format(chef_sim), _connection)
        return False
    chef_situation = restaurant_utils.get_chef_situation(chef_sim=chef_sim)
    if chef_situation is None:
        sims4.commands.output("Couldn't find a Chef Situation in this zone.")
        return False
    if chef_situation.menu_preset is not None:
        food_order = ChefsChoice.get_order_for_npc_sim_with_menu(sim, chef_situation.menu_preset)
    else:
        (food_order, _) = ChefsChoice.get_order_for_npc_sim(sim)
    chef_situation.add_direct_order(food_order, sim)
    services.get_event_manager().process_event(test_events.TestEvent.RestaurantFoodOrdered, sim_info=sim.sim_info)
    return True

@sims4.commands.Command('restaurant.give_chef_feedback', command_type=sims4.commands.CommandType.Live)
def give_chef_feedback(to_chef_sim_id:OptionalTargetParam=None, from_sim_id:OptionalTargetParam=None, is_compliment:bool=True, waitstaff_sim_id:OptionalTargetParam=None, _connection=None):
    from_sim = get_optional_target(from_sim_id, _connection)
    if from_sim is None:
        sims4.commands.output("From Sim {} doesn't exist.".format(from_sim_id), _connection)
        return False
    to_chef_sim = get_optional_target(to_chef_sim_id, _connection)
    if to_chef_sim is None:
        sims4.commands.output("To Chef Sim {} doesn't exist.".format(to_chef_sim_id), _connection)
        return False
    waitstaff_sim = get_optional_target(waitstaff_sim_id, _connection)
    if waitstaff_sim is None:
        sims4.commands.output("Waitstaff Sim {} doesn't exist.".format(waitstaff_sim_id), _connection)
        return False
    waitstaff_situation = restaurant_utils.get_waitstaff_situation(waitstaff_sim)
    waitstaff_situation.give_chef_feedback(to_chef_sim, from_sim, is_compliment)

@sims4.commands.Command('restaurant.npc_order_food_from_waitstaff', command_type=sims4.commands.CommandType.Live)
def npc_order_food_from_waitstaff(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Sim {} doesn't exist.".format(opt_sim), _connection)
        return False
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('Not currently on a restaurant lot so cannot place orders with the waitstaff for NPC groups.', _connection)
        return False
    active_group_order = _get_active_group_order_for_dining_group(sim)
    dining_groups = zone_director.get_dining_groups_by_sim(sim)
    for dining_group in dining_groups:
        if not dining_group.order_for_table(active_group_order=active_group_order):
            sims4.commands.output('Failed to place order for dining group.', _connection)
            return False
    return True

@sims4.commands.Command('restaurant.comp_order_for_sim', command_type=sims4.commands.CommandType.Live)
def comp_order_for_sim(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.Command("Sim {} doesn't exist.".format(opt_sim), _connection)
        return False
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.Command('Not currently on a restaurant lot.', _connection)
        return False
    business_manager = zone_director.business_manager
    if business_manager is None:
        sims4.commands.Command("The current zone doesn't have a business manager.", _connection)
        return False
    for group_order in zone_director.get_delivered_orders_for_sim(sim.id):
        business_manager.comp_order_for_sim(group_order.get_sim_order(sim.id))

@sims4.commands.Command('restaurant.create_food_for_group_order_sim', command_type=sims4.commands.CommandType.Live)
def create_food_for_group_order_sim(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Sim {} doesn't exist.".format(opt_sim), _connection)
        return False
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('Not currently on a restaurant lot so can not create an order for a table.', _connection)
        return False
    group_order = zone_director.get_active_group_order_for_sim(sim.id)
    if group_order is None:
        sims4.commands.output('There is no group order in for the passed in sim {}.'.format(sim), _connection)
        return False
    zone_director.create_food_for_group_order(group_order)
    return True

@sims4.commands.Command('restaurant.create_food_for_group_order_table', command_type=sims4.commands.CommandType.Live)
def create_food_for_group_order_table(table_id:OptionalTargetParam=None, _connection=None):
    table = get_optional_target(table_id, _connection)
    if table is None:
        sims4.commands.output("Table {} doesn't exist.".format(table_id), _connection)
        return False
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('Not currently on a restaurant lot so can not create an order for a table.', _connection)
        return False
    group_order = zone_director.get_active_group_order_for_table(table.id)
    if group_order is None:
        sims4.commands.output('There is no group order in for the passed in sim {}.'.format(sim), _connection)
        return False
    zone_director.create_food_for_group_order(group_order)
    return True

@sims4.commands.Command('restaurant.set_ingredient_quality', command_type=sims4.commands.CommandType.Live)
def set_ingredient_quality(ingredient_quality:RestaurantIngredientQualityType, _connection=None):
    business_manager = services.business_service().get_business_manager_for_zone()
    if business_manager is None:
        sims4.commands.output('Trying to set the ingredient quality for a restaurant but there was no valid business manager found for the current zone.')
        return False
    business_manager.set_ingredient_quality(ingredient_quality)

@sims4.commands.Command('restaurant.expedite_sims_order', command_type=sims4.commands.CommandType.Live)
def expedite_sim_order(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Sim {} doesn't exist.".format(opt_sim), _connection)
        return False
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('Not on a restaurant lot.', _connection)
        return
    if not zone_director.has_group_order(sim.id):
        sims4.commands.output('Sim {} does not have an order.'.format(sim), _connection)
        return
    group_order = zone_director.get_group_order(sim.id)
    if group_order is not None:
        group_order.expedited = True

@sims4.commands.Command('restaurant.refresh_configuration', command_type=sims4.commands.CommandType.Live)
def refresh_configuration(_connection=None):
    zone_director = get_restaurant_zone_director()
    if zone_director is not None:
        zone_director.refresh_configuration()

def _get_active_group_order_for_dining_group(sim):
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        return
    dining_groups = zone_director.get_dining_groups_by_sim(sim)
    for dining_group in dining_groups:
        for group_sim in dining_group.all_sims_in_situation_gen():
            active_group_order = zone_director.get_active_group_order_for_sim(group_sim.sim_id)
            if active_group_order:
                return active_group_order

@sims4.commands.Command('restaurant.sim_is_employee', command_type=sims4.commands.CommandType.Automation)
def sim_is_employee(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("False, Sim {} doesn't exist.".format(opt_sim), _connection)
        sims4.commands.automation_output('RestaurantIsEmployee; Status:InvalidSim', _connection)
        return False
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('False, Not on a restaurant lot.', _connection)
        sims4.commands.automation_output('RestaurantIsEmployee; Status:NotOnLot', _connection)
        return False
    situation_manager = services.get_zone_situation_manager()
    if situation_manager is None:
        sims4.commands.output('False, There is no situation manager on this lot.', _connection)
        sims4.commands.automation_output('RestaurantIsEmployee; Status:NoSituationMgr', _connection)
        return False
    business_manager = zone_director.business_manager
    if business_manager is None:
        sim_situations = situation_manager.get_situations_sim_is_in(sim)
        for situation in sim_situations:
            if type(situation) in (RestaurantTuning.CHEF_SITUATION, RestaurantTuning.HOST_SITUATION, RestaurantTuning.WAITSTAFF_SITUATION):
                sims4.commands.output('True, Sim is an employee of the current restaurant.', _connection)
                sims4.commands.automation_output('RestaurantIsEmployee; Status:Success', _connection)
                return True
    elif business_manager.is_employee(sim.sim_info):
        sims4.commands.output('True, Sim is currently an employee', _connection)
        sims4.commands.automation_output('RestaurantIsEmployee; Status:Success', _connection)
        return True
    sims4.commands.output('False, Sim is not an employee of the current restaurant.', _connection)
    sims4.commands.automation_output('RestaurantIsEmployee; Status:Failed', _connection)
    return False

@sims4.commands.Command('restaurant.is_open', command_type=sims4.commands.CommandType.Automation)
def is_open(_connection=None):
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('False, Not on a restaurant lot.', _connection)
        sims4.commands.automation_output('RestaurantIsOpen; Status:NotOnLot', _connection)
        return False
    if zone_director.business_manager is None:
        sims4.commands.output('True, unowned restaurants are always open.', _connection)
        sims4.commands.automation_output('RestaurantIsOpen; Status:Success', _connection)
        return True
    if zone_director.business_manager.is_open:
        sims4.commands.output('True, this owned restaurant is currently open', _connection)
        sims4.commands.automation_output('RestaurantIsOpen; Status:Success', _connection)
        return True
    sims4.commands.output('False, this owned restaurant is currently closed', _connection)
    sims4.commands.automation_output('RestaurantIsOpen; Status:Failed', _connection)
    return False

@sims4.commands.Command('restaurant.get_sim_diner_state', command_type=sims4.commands.CommandType.Automation)
def get_sim_dining_state(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Sim {} doesn't exist".format(opt_sim), _connection)
        return False
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        sims4.commands.output('Not on a restaurant lot.', _connection)
        return False
    groups = zone_director.get_dining_groups_by_sim(sim)
    if not groups:
        sims4.commands.output('Sim {} is not in dining group'.format(sim), _connection)
        sims4.commands.automation_output('RestaurantDinerState; Status:NotReady', _connection)
        return True
    dining_group = groups.pop()
    for sub_situation in dining_group.sub_situations:
        state = sub_situation.current_state_index().name
        sims4.commands.automation_output('RestaurantDinerState; Status:{}'.format(state), _connection)
    return True
