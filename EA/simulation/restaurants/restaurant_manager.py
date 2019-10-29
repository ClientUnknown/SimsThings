from _collections import dequeimport itertoolsfrom protocolbuffers import Business_pb2, DistributorOps_pb2from business.advertising_manager import HasAdvertisingManagerMixinfrom business.business_enums import BusinessType, BusinessAdvertisingTypefrom business.business_manager import BusinessManagerfrom crafting.crafting_tunable import CraftingTuningfrom distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorfrom event_testing.resolver import SingleSimResolverfrom gsi_handlers import business_handlersfrom restaurants.restaurant_summary_dialog import RestaurantSummaryDialogfrom restaurants.restaurant_tag_tuning import RestaurantTagTuningfrom restaurants.restaurant_tuning import RestaurantTuning, get_restaurant_zone_directorimport servicesimport sims4.loglogger = sims4.log.Logger('Restaurant', default_owner='trevor')
class RestaurantManager(HasAdvertisingManagerMixin, BusinessManager):

    def __init__(self):
        super().__init__(BusinessType.RESTAURANT)
        self._ingredient_quality = RestaurantTuning.DEFAULT_INGREDIENT_QUALITY
        self._dining_spot_count = 0
        self._chef_low_skill_message_shown = False
        self._profits_per_meal = deque([RestaurantTuning.DEFAULT_PROFIT_PER_MEAL_FOR_OFF_LOT_SIMULATION], maxlen=RestaurantTuning.MEAL_COUNT_FOR_OFF_LOT_PROFIT_PER_MEAL)
        self._summary_dialog_class = RestaurantSummaryDialog

    def _clear_state(self):
        super()._clear_state()
        self._advertising_manager.clear_state()
        self._chef_low_skill_message_shown = False
        self._off_lot_negative_profit_notification_shown = False

    def _open_business(self):
        super()._open_business()
        self._advertising_manager.open_business()
        services.daycare_service().send_active_household_toddlers_home()
        zone_director = get_restaurant_zone_director()
        if zone_director is not None:
            zone_director.release_all_tables()

    def _close_business(self, **kwargs):
        super()._close_business(**kwargs)
        zone_director = get_restaurant_zone_director()
        if zone_director is not None:
            zone_director.clear_group_orders()
        self.modify_funds(-self._advertising_manager.get_current_advertising_cost(), from_item_sold=False)

    def set_ingredient_quality(self, ingredient_quality):
        self._ingredient_quality = ingredient_quality
        self._distribute_business_manager_data_message()

    def set_dining_spot_count(self, value):
        self._dining_spot_count = value

    def get_ideal_customer_count(self):
        return self.tuning_data.star_rating_to_customer_count_curve.get(self.get_star_rating())*RestaurantTuning.TIME_OF_DAY_TO_CUSTOMER_COUNT_MULTIPLIER_CURVE.get(services.time_service().sim_now.hour())*self.get_advertising_multiplier()

    def _get_off_lot_customer_count(self, hours_since_last_sim):
        customer_count_per_hour = self.get_ideal_customer_count()
        customer_count_per_hour = min(self._dining_spot_count, customer_count_per_hour*self.tuning_data.off_lot_customer_count_multiplier)
        customer_count_per_hour *= self.tuning_data.off_lot_customer_count_penalty_multiplier
        return int(customer_count_per_hour*hours_since_last_sim)

    def calculate_and_apply_expense_for_group_order(self, group_order, refund=False):
        total_price = 0
        for (_, order) in group_order:
            total_price += self._calculate_expense_for_sim_order(order)
        price = total_price if refund else -total_price
        self.modify_funds(price, from_item_sold=False, funds_category=RestaurantTuning.BUSINESS_FUNDS_CATEGORY_FOR_COST_OF_INGREDIENTS)
        if refund:
            self.add_to_funds_category(RestaurantTuning.BUSINESS_FUNDS_CATEGORY_FOR_COST_OF_INGREDIENTS, -price)
        if business_handlers.business_archiver.enabled:
            business_handlers.archive_business_event('Funds', None, 'Apply expense for group order price:{} refund:{}'.format(price, refund))

    def _get_average_profit_per_service(self):
        profit = self._get_running_profit_per_meal_average()
        bucks_tracker = services.active_household().bucks_tracker
        if bucks_tracker.is_perk_unlocked(RestaurantTuning.CUSTOMERS_ORDER_EXPENSIVE_FOOD_PERK_DATA.perk):
            profit *= RestaurantTuning.CUSTOMERS_ORDER_EXPENSIVE_FOOD_PERK_DATA.off_lot_multiplier
        return profit

    def _add_meal_profits(self, profit):
        self._profits_per_meal.append(max(0, profit))

    def _get_running_profit_per_meal_average(self):
        if not self._profits_per_meal:
            return 0
        profits_sum = sum(self._profits_per_meal)
        return profits_sum/len(self._profits_per_meal)

    def _calculate_expense_for_sim_order(self, sim_order):
        recipe_manager = services.recipe_manager()
        expense_multiplier = RestaurantTuning.INGREDIENT_QUALITY_DATA_MAPPING.get(self._ingredient_quality).ingredient_quality_to_restaurant_expense_multiplier
        food = recipe_manager.get(sim_order.food_recipe_id)
        drink = recipe_manager.get(sim_order.drink_recipe_id)
        expense = 0
        if food is not None:
            expense += food.restaurant_base_price*expense_multiplier
        if drink is not None:
            expense += drink.restaurant_base_price*expense_multiplier
        bucks_tracker = services.active_household().bucks_tracker
        for (perk, multiplier) in RestaurantTuning.INGREDIENT_PRICE_PERK_MAP.items():
            if bucks_tracker.is_perk_unlocked(perk):
                expense *= multiplier
        return expense

    def _calculate_sale_price_for_sim_order(self, sim_order):
        recipe_manager = services.recipe_manager()
        total_price = 0
        food = recipe_manager.get(sim_order.food_recipe_id, None)
        drink = recipe_manager.get(sim_order.drink_recipe_id, None)
        if food is not None:
            total_price += self.get_value_with_markup(food.restaurant_base_price)
        if drink is not None:
            total_price += self.get_value_with_markup(drink.restaurant_base_price)
        return total_price

    def calculate_and_apply_sale_of_group_order(self, group_order):
        if group_order.is_complimentary:
            return
        total_price = 0
        for (_, order) in group_order:
            sale_price = self._calculate_sale_price_for_sim_order(order)
            total_price += sale_price
            self._add_meal_profits(sale_price - self._calculate_expense_for_sim_order(order))
        self.modify_funds(total_price, from_item_sold=True)
        if business_handlers.business_archiver.enabled:
            business_handlers.archive_business_event('Funds', None, 'Apply sale for group order price:{}'.format(total_price))

    def comp_order_for_sim(self, sim_order):
        total_price = self._calculate_sale_price_for_sim_order(sim_order)
        self.modify_funds(-total_price, from_item_sold=False, from_comped_item=True)
        if business_handlers.business_archiver.enabled:
            business_handlers.archive_business_event('Funds', None, 'comp_order_for_sim price:{} '.format(-total_price))

    def should_show_no_way_to_make_money_notification(self):
        if not self.meets_minimum_employee_requirment():
            return True
        else:
            zone_director = get_restaurant_zone_director()
            if zone_director is not None:
                menu = zone_director.get_current_menu()
                total_recipes = [recipes for (_, recipes) in menu.items()]
                total_recipes = list(itertools.chain.from_iterable(total_recipes))
                if len(total_recipes) <= 1:
                    return True
        return False

    def meets_minimum_employee_requirment(self):
        if self._employee_manager.employee_count == 0:
            return False
        for employee_type in self.tuning_data.employee_data_map.keys():
            if len(self.get_employees_by_type(employee_type)) == 0:
                return False
        return True

    def set_states_for_recipe(self, recipe, recipe_instance, chef):
        recipe_quality_stat = CraftingTuning.QUALITY_STATISTIC
        quality_stat_tracker = recipe_instance.get_tracker(recipe_quality_stat)
        if quality_stat_tracker is None:
            logger.error("Trying to apply a final quality state to a recipe instance {} but it doesn't have the correct stat tracker {}.", recipe_instance, CraftingTuning.QUALITY_STATISTIC)
            return
        customer_quality_stat = RestaurantTuning.CUSTOMER_QUALITY_STAT
        customer_quality_stat_tracker = recipe_instance.get_tracker(customer_quality_stat)
        if customer_quality_stat_tracker is None:
            logger.error("Trying to apply a customer quality state to a recipe instance {} but it doesn't have the correct stat tracker {}.", recipe_instance, RestaurantTuning.CUSTOMER_QUALITY_STAT)
            return
        customer_value_stat = RestaurantTuning.CUSTOMER_VALUE_STAT
        customer_value_stat_tracker = recipe_instance.get_tracker(customer_value_stat)
        if customer_value_stat_tracker is None:
            logger.error("Trying to apply a customer value state to a recipe instance {} but it doesn't have the correct stat tracker {}.", recipe_instance, RestaurantTuning.CUSTOMER_VALUE_STAT)
            return
        ingredient_quality_data = RestaurantTuning.INGREDIENT_QUALITY_DATA_MAPPING.get(self._ingredient_quality)
        recipe_difficulty_data = RestaurantTuning.RECIPE_DIFFICULTY_DATA_MAPPING.get(recipe.recipe_difficulty)
        markup_data = RestaurantTuning.PRICE_MARKUP_DATA_MAPPING.get(self._markup_multiplier)
        final_recipe_quality = ingredient_quality_data.ingredient_quality_to_final_quality_adder
        recipe_difficulty_adder = recipe_difficulty_data.recipe_difficulty_to_final_quality_adder
        final_recipe_quality += recipe_difficulty_adder
        buff_component = chef.sim_info.Buffs
        for buff in buff_component:
            buff_tuning = RestaurantTuning.COOKING_SPEED_DATA_MAPPING.get(buff.buff_type)
            if not buff_tuning:
                pass
            else:
                final_recipe_quality += buff_tuning.cooking_speed_to_final_quality_adder
        if RestaurantTagTuning.RECIPE_FOOD_TAG in recipe.recipe_tags:
            is_drink = False
            food_skill = RestaurantTuning.CHEF_SKILL_TO_FOOD_FINAL_QUALITY_ADDER_DATA.skill
            final_recipe_quality += RestaurantTuning.CHEF_SKILL_TO_FOOD_FINAL_QUALITY_ADDER_DATA.final_quality_adder_curve.get(chef.get_effective_skill_level(food_skill))
        else:
            is_drink = True
            drink_skill = RestaurantTuning.CHEF_SKILL_TO_DRINK_FINAL_QUALITY_ADDER_DATA.skill
            final_recipe_quality += RestaurantTuning.CHEF_SKILL_TO_DRINK_FINAL_QUALITY_ADDER_DATA.final_quality_adder_curve.get(chef.get_effective_skill_level(drink_skill))
        quality_stat_tracker.set_value(recipe_quality_stat, final_recipe_quality)
        final_recipe_quality_value = recipe_instance.get_state_value_from_stat_type(recipe_quality_stat)
        final_recipe_quality_data = RestaurantTuning.FINAL_QUALITY_STATE_DATA_MAPPING.get(final_recipe_quality_value)
        final_customer_quality = final_recipe_quality_data.final_quality_to_customer_quality_multiplier
        final_customer_quality *= recipe_difficulty_data.recipe_difficulty_to_customer_quality_multiplier
        customer_quality_stat_tracker.set_value(customer_quality_stat, final_customer_quality)
        final_customer_value = final_recipe_quality_data.final_quality_to_customer_value_multiplier
        final_customer_value *= markup_data.markup_to_customer_value_multiplier
        customer_value_stat_tracker.set_value(customer_value_stat, final_customer_value)
        if not self._chef_low_skill_message_shown:
            if is_drink:
                drink_skill_tracker = chef.get_tracker(drink_skill)
                drink_skill_value = drink_skill_tracker.get_user_value(drink_skill)
                total = RestaurantTuning.CHEF_SKILL_TO_DRINK_FINAL_QUALITY_ADDER_DATA.final_quality_adder_curve.get(drink_skill_value)
            else:
                food_skill_tracker = chef.get_tracker(food_skill)
                food_skill_value = food_skill_tracker.get_user_value(food_skill)
                total = RestaurantTuning.CHEF_SKILL_TO_FOOD_FINAL_QUALITY_ADDER_DATA.final_quality_adder_curve.get(food_skill_value)
            total += recipe_difficulty_adder
            if total < RestaurantTuning.CHEF_NOT_SKILLED_ENOUGH_THRESHOLD:
                business_manager = services.business_service().get_business_manager_for_zone()
                if business_manager is None or not business_manager.is_owner_household_active:
                    return
                resolver = SingleSimResolver(chef)
                dialog = RestaurantTuning.CHEF_NOT_SKILLED_ENOUGH_NOTIFICATION(chef, resolver)
                if self.is_owner_household_active:
                    dialog.show_dialog()
                self._chef_low_skill_message_shown = True

    def save_data(self, business_save_data):
        super().save_data(business_save_data)
        business_save_data.restaurant_save_data = Business_pb2.RestaurantSaveData()
        business_save_data.restaurant_save_data.ingredient_quality_enum = self._ingredient_quality
        business_save_data.restaurant_save_data.profit_per_meal_queue.extend(int(profit) for profit in self._profits_per_meal)
        business_save_data.restaurant_save_data.dining_spot_count = self._dining_spot_count
        business_save_data.restaurant_save_data.advertising_type = self._advertising_manager._advertising_type

    def load_data(self, business_save_data, is_legacy=False):
        super().load_data(business_save_data, is_legacy)
        self._ingredient_quality = business_save_data.restaurant_save_data.ingredient_quality_enum
        self._profits_per_meal.clear()
        profit_per_meal_save_data = business_save_data.restaurant_save_data.profit_per_meal_queue
        if profit_per_meal_save_data and len(profit_per_meal_save_data) > RestaurantTuning.MEAL_COUNT_FOR_OFF_LOT_PROFIT_PER_MEAL:
            logger.warn('About to load more values for the profit_per_meal_queue than the tuned max size of the queue. Values will be lost.\n save data queue size:{}\n max queue size:{}', len(profit_per_meal_save_data), RestaurantTuning.MEAL_COUNT_FOR_OFF_LOT_PROFIT_PER_MEAL)
        for profit in profit_per_meal_save_data:
            self._profits_per_meal.append(profit)
        self._dining_spot_count = business_save_data.restaurant_save_data.dining_spot_count
        self.set_advertising_type(business_save_data.restaurant_save_data.advertising_type)

    def _distribute_business_manager_data_message(self):
        msg = self._build_restaurant_data_message()
        op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.RESTAURANT_DATA_UPDATE, msg)
        Distributor.instance().add_op_with_no_owner(op)

    def _build_restaurant_data_message(self):
        msg = Business_pb2.RestaurantBusinessDataUpdate()
        msg.zone_id = self.business_zone_id
        msg.is_ingredient_unlocked = self._quality_unlocked
        msg.ingredient_chosen = self._ingredient_quality
        if self._advertising_manager._advertising_type != BusinessAdvertisingType.INVALID:
            msg.advertising_chosen = self._advertising_manager._advertising_type
        return msg

    def construct_business_message(self, msg):
        super().construct_business_message(msg)
        msg.restaurant_data = self._build_restaurant_data_message()
