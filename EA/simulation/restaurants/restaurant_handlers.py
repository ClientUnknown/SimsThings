from restaurants.restaurant_tuning import RestaurantTuning, get_restaurant_zone_directorfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemaimport servicesrestaurant_order_schema = GsiGridSchema(label='Restaurant Order Manager')restaurant_order_schema.add_field('order_id', label='Order Id', width=1, unique_field=True)restaurant_order_schema.add_field('situation_id', label='Situation Id', width=1)restaurant_order_schema.add_field('order_status', label='Order Status', width=2)restaurant_order_schema.add_field('current_bucket', label='Current Bucket', width=2)restaurant_order_schema.add_field('table_ids', label='Table Ids', width=2)restaurant_order_schema.add_field('sim_order_count', label='Sim Order Count', width=1)restaurant_order_schema.add_field('assigned_waiter', label='Waiter', width=1)restaurant_order_schema.add_field('assigned_chef', label='Chef', width=1)restaurant_order_schema.add_field('food_platter', label='Platter', width=1)restaurant_order_schema.add_field('complimentary', label='Complimentary', width=1)with restaurant_order_schema.add_has_many('SimOrders', GsiGridSchema) as sub_schema:
    sub_schema.add_field('sim_name', label='Sim')
    sub_schema.add_field('food_recipe', label='Food')
    sub_schema.add_field('drink_recipe', label='Drink')
    sub_schema.add_field('recommendation_state', label='Recommendation State')
@GsiHandler('restaurant_orders', restaurant_order_schema)
def generate_restaurant_order_data(zone_id:int=None):
    all_orders = []
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        return all_orders
    sim_info_manager = services.sim_info_manager()
    recipe_manager = services.recipe_manager()
    for group_order in zone_director._group_orders.values():
        sim_order_data = []
        for (sim_id, sim_order) in group_order._sim_orders.items():
            sim_info = sim_info_manager.get(sim_id)
            food_recipe_id = sim_order.food_recipe_id
            drink_recipe_id = sim_order.drink_recipe_id
            food_str = ''
            drink_str = ''
            if food_recipe_id is not None:
                food_recipe = recipe_manager.get(food_recipe_id, None)
                if food_recipe is not None:
                    food_str = '{}({})'.format(food_recipe.__name__, food_recipe_id)
            if drink_recipe_id is not None:
                drink_recipe = recipe_manager.get(drink_recipe_id, None)
                if drink_recipe is not None:
                    drink_str = '{}({})'.format(drink_recipe.__name__, drink_recipe_id)
            sim_order_data.append({'sim_name': str(sim_info), 'food_recipe': food_str, 'drink_recipe': drink_str, 'recommendation_state': str(sim_order.recommendation_state)})
        assigned_waiter = group_order.assigned_waitstaff
        assigned_chef = group_order.assigned_chef
        food_platter = group_order.serving_from_chef
        all_orders.append({'order_id': str(group_order.order_id), 'situation_id': str(group_order._situation_id), 'order_status': str(group_order.order_status), 'current_bucket': str(group_order.current_bucket), 'table_ids': ','.join([str(table_id) for table_id in group_order._table_ids]), 'sim_order_count': str(group_order.sim_order_count), 'assigned_waiter': str(assigned_waiter), 'assigned_chef': str(assigned_chef), 'food_platter': str(food_platter), 'complimentary': str(group_order.is_complimentary), 'SimOrders': sim_order_data})
    return all_orders
restaurant_seat_schema = GsiGridSchema(label='Restaurant Seat Manager')restaurant_seat_schema.add_field('table', label='Table', width=2)restaurant_seat_schema.add_field('dining_spots_num', label='Dining Spots Num', width=1)restaurant_seat_schema.add_field('situation', label='Situation', width=1)restaurant_seat_schema.add_field('seated_sim_num', label='Seated Sim Num', width=1)with restaurant_seat_schema.add_has_many('DiningSpots', GsiGridSchema) as sub_schema:
    sub_schema.add_field('part_index', label='Part Index')
    sub_schema.add_field('seat', label='Seat')
    sub_schema.add_field('seated_sim', label='Sim')
    sub_schema.add_field('food_and_drink', label='Meal')
@GsiHandler('restaurant_seats', restaurant_seat_schema)
def generate_restaurant_seat_data(zone_id:int=None):
    all_tables = []
    zone_director = get_restaurant_zone_director()
    if zone_director is None:
        return all_tables
    sim_info_manager = services.sim_info_manager()
    object_manager = services.object_manager(zone_id)
    for (table_id, dining_spots) in zone_director._dining_spots.items():
        table = object_manager.get(table_id)
        if table is None:
            pass
        else:
            situation_str = ''
            situations = zone_director.get_situations_by_table(table_id)
            if situations:
                situation = situations[0]
                situation_str = '{}'.format(situation)
            dining_spot_data = []
            seated_sim_num = 0
            for (part_index, dining_spot) in dining_spots.items():
                seat_object = object_manager.get(dining_spot.seat_id)
                sim_id = zone_director.get_sim_in_seat(table_id, part_index)
                sim_name = ''
                if sim_id is not None:
                    sim_name = str(sim_info_manager.get(sim_id))
                    seated_sim_num += 1
                food_and_drink_objects = []
                for runtime_slot in table.parts[part_index].get_runtime_slots_gen(slot_types={RestaurantTuning.TABLE_DRINK_SLOT_TYPE, RestaurantTuning.TABLE_FOOD_SLOT_TYPE}):
                    food_and_drink_objects.extend([str(child_object) for child_object in runtime_slot.children])
                chair_part_str = ''
                if dining_spot.chair_part_index is not None:
                    chair_part_str = '[{}]'.format(dining_spot.chair_part_index)
                dining_spot_data.append({'part_index': str(part_index), 'seat': str(seat_object) + chair_part_str, 'seated_sim': sim_name, 'food_and_drink': ','.join(food_and_drink_objects)})
            all_tables.append({'table': str(table), 'dining_spots_num': str(len(dining_spots)), 'situation': situation_str, 'seated_sim_num': str(seated_sim_num), 'DiningSpots': dining_spot_data})
    return all_tables
