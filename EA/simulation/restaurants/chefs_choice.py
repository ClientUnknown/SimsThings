from event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetfrom restaurants.restaurant_tuning import RestaurantTuning, get_restaurant_zone_directorfrom sims4 import randomfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, TunableTuple, TunableRange, TunableList, Tunable, TunableEnumWithFilter, TunablePackSafeReferencefrom tag import Tagimport servicesimport sims4.loglogger = sims4.log.Logger('ChefsChoice', default_owner='trevor')
class ChefsChoice:
    FOOD_COURSES = TunableList(description='\n        A List of all the courses to search through in order to find what an \n        NPC will order.\n        ', tunable=TunableEnumWithFilter(description='\n            A food course that an NPC can order.\n            ', tunable_type=Tag, filter_prefixes=['recipe_course'], default=Tag.INVALID, invalid_enums=(Tag.INVALID,), pack_safe=True))
    DRINK_COURSE = TunableEnumWithFilter(description='\n        The drink course so Sims can order drinks with their meals.\n        ', tunable_type=Tag, filter_prefixes=['recipe_course'], default=Tag.INVALID, invalid_enums=(Tag.INVALID,), pack_safe=True)
    DESSERT_COURSE = TunableEnumWithFilter(description='\n        The dessert course so Sims can order dessert with their meals.\n        ', tunable_type=Tag, filter_prefixes=['recipe_course'], default=Tag.INVALID, invalid_enums=(Tag.INVALID,), pack_safe=True)
    NPC_ORDER_MAP = TunableMapping(description='\n        A mapping of tags to weighted tests. If an item on the menu has the\n        designated tag, it will start with the tuned base weight and then each\n        passing test will add the tested-weight to the total weight for that\n        food object. Once all food objects have been weighed for a given\n        category (apps, entrees, etc.), a weighted random determines the\n        winner.\n        ', key_type=TunableEnumEntry(description='\n            If the food item has this tag, we will apply the corresponding base\n            weight to it and the sum of the weights of any passing tests run on\n            this object.\n            ', tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), pack_safe=True), value_type=TunableTuple(description='\n            The base weight and weighted tests to run.\n            ', base_weight=TunableRange(description='\n                The base weight of this food object. Even if no tests pass,\n                this weight will be applied for use with the weighted random\n                selection.\n                ', tunable_type=float, default=1.0, minimum=0), weighted_tests=TunableList(description='\n                A list of tests and weights. For each passed test, the\n                corresponding weight is added to the base weight of the food\n                object.\n                ', tunable=TunableTuple(description='\n                    Tests and weights. If the test passes, the weight is added\n                    to the base weight of the food object.\n                    ', tests=TunableTestSet(), weight=Tunable(description='\n                        The weight to add to the base weight of the food object\n                        if the corresponding tests pass. A negative value is\n                        valid.\n                        ', tunable_type=float, default=1.0)))))
    WATER_ORDER_FOR_BACKUP = TunablePackSafeReference(description='\n        A reference to the water order that should be available when nothing\n        else is available.\n        ', manager=services.recipe_manager(), class_restrictions=('Recipe',))

    @classmethod
    def get_choice_for_npc_sim(cls, sim, course):
        zone_director = get_restaurant_zone_director()
        menu_items = zone_director.get_menu_for_course(course)
        possible_items = cls.get_possible_orders(sim, menu_items)
        if not possible_items:
            return
        choice = random.weighted_random_item(list(possible_items.items()), flipped=True)
        return choice

    @classmethod
    def get_order_for_npc_sim(cls, sim):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            logger.error('Trying to get an order for an NPC sim but there is no restaurant zone director.')
            return
        menu_items = []
        for course in cls.FOOD_COURSES:
            menu_items.extend(zone_director.get_menu_for_course(course))
        possible_orders = list(cls.get_possible_orders(sim, menu_items).items())
        food_choice = random.weighted_random_item(possible_orders, flipped=True)
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None:
            bucks_tracker = services.active_household().bucks_tracker
            if bucks_tracker.is_perk_unlocked(RestaurantTuning.CUSTOMERS_ORDER_EXPENSIVE_FOOD_PERK_DATA.perk):
                food_choice_2 = random.weighted_random_item(possible_orders, flipped=True)
                if food_choice_2 is not food_choice:
                    choice_1_price = business_manager.get_value_with_markup(food_choice.restaurant_base_price)
                    choice_2_price = business_manager.get_value_with_markup(food_choice_2.restaurant_base_price)
                    if choice_2_price > choice_1_price:
                        food_choice = food_choice_2
        drink_choice = cls.get_choice_for_npc_sim(sim, cls.DRINK_COURSE)
        if food_choice is None and drink_choice is None:
            return (None, cls.WATER_ORDER_FOR_BACKUP)
        return (food_choice, drink_choice)

    @classmethod
    def get_order_for_npc_sim_with_menu(cls, sim, menu_preset):
        chef_menu = RestaurantTuning.MENU_PRESETS[menu_preset]
        menu_items = []
        for course in cls.FOOD_COURSES:
            menu_items.extend(chef_menu.recipe_map.get(course, {}))
        possible_orders = cls.get_possible_orders(sim, menu_items)
        food_order = random.weighted_random_item(list(possible_orders.items()), flipped=True)
        return food_order

    @classmethod
    def get_possible_orders(cls, sim, menu_items):
        resolver = SingleSimResolver(sim)
        possible_orders = {}
        for (order_data_tag, order_data) in cls.NPC_ORDER_MAP.items():
            for recipe in menu_items:
                if order_data_tag in recipe.recipe_tags:
                    if recipe not in possible_orders:
                        possible_orders[recipe] = 0
                    possible_orders[recipe] += order_data.base_weight
                    for weighted_test in order_data.weighted_tests:
                        if weighted_test.tests.run_tests(resolver):
                            possible_orders[recipe] += weighted_test.weight
        return possible_orders
