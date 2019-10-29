from _collections import defaultdictimport randomfrom protocolbuffers import Restaurant_pb2, GameplaySaveData_pb2from animation.posture_manifest_constants import PostureConstantsfrom business.business_enums import BusinessEmployeeType, BusinessTypefrom business.business_zone_director_mixin import BusinessZoneDirectorMixinfrom crafting.crafting_process import CraftingProcessfrom crafting.crafting_tunable import CraftingTuningfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom event_testing import test_eventsfrom event_testing.resolver import SingleSimResolver, DoubleObjectResolverfrom event_testing.results import TestResultfrom interactions.context import InteractionContextfrom interactions.interaction_finisher import FinishingTypefrom interactions.priority import Priorityfrom objects import systemfrom restaurants.chef_situation import ChefSituationfrom restaurants.chef_tuning import ChefTuningfrom restaurants.host_situation import HostSituationfrom restaurants.restaurant_order import GroupOrder, OrderStatus, OrderRecommendationStatefrom restaurants.restaurant_tag_tuning import RestaurantTagTuningfrom restaurants.restaurant_tuning import RestaurantTuning, MenuPresets, RestaurantOutfitTypefrom restaurants.restaurant_ui import ShowMenufrom restaurants.restaurant_utils import get_menu_message, food_on_table_genfrom restaurants.waitstaff_situation import WaitstaffSituationfrom sims.outfits.outfit_enums import OutfitCategoryfrom sims.sim_info_base_wrapper import SimInfoBaseWrapperfrom sims.sim_info_types import Genderfrom sims4.tuning.geometric import TunableCurvefrom sims4.tuning.tunable import TunableReference, TunableEnumEntry, TunableTuple, TunableListfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_curve import SituationCurvefrom venues.scheduling_zone_director import SchedulingZoneDirectorfrom venues.visitor_situation_on_arrival_zone_director_mixin import VisitorSituationOnArrivalZoneDirectorMixinimport build_buyimport servicesimport sims4.logimport zone_typeslogger = sims4.log.Logger('Restaurant', default_owner='cjiang')SUPPORTED_BUSINESS_TYPES = (BusinessType.RESTAURANT,)
class DiningSpot:
    __slots__ = ('table_id', 'seat_id', 'table_part_index', 'chair_part_index')

    def __init__(self, table_id, seat_id, table_part_index, chair_part_index):
        self.table_id = table_id
        self.seat_id = seat_id
        self.table_part_index = table_part_index
        self.chair_part_index = chair_part_index

class RestaurantZoneDirector(BusinessZoneDirectorMixin, VisitorSituationOnArrivalZoneDirectorMixin, SchedulingZoneDirector):
    INSTANCE_TUNABLES = {'food_reaction_affordance': TunableReference(description='\n            The reaction interaction that gets pushed on Sims when their food is \n            created at the table. This interaction should have the constraints to\n            make sure the Sims is sitting at the table before reacting or they\n            might react from somewhere other than their table.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'picnic_part_definition': TunableReference(description='\n            The part definition for picnic table, zone director need to use\n            this to detect picnic table parts as dining spots.\n            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_PART)), 'customer_situation_type_curve': SituationCurve.TunableFactory(description="\n            When customer situations are being generated, they'll be pulled\n            based on the tuning in this.\n            ", tuning_group=GroupNames.BUSINESS, get_create_params={'user_facing': False}), 'business_chef_employee_type_and_situation': TunableTuple(description='\n            The Business Employee Type of the Chef as well as the list of\n            situations that will be randomly chosen from when we spawn a hired\n            chef.\n            ', employee_type=TunableEnumEntry(description='\n                The Business Employee Type for the Chef.\n                ', tunable_type=BusinessEmployeeType, default=BusinessEmployeeType.INVALID, invalid_enums=(BusinessEmployeeType.INVALID,)), situation_list=TunableList(description='\n                The list of possible chef situations, chosen at random, for\n                hired chefs to be in.\n                ', tunable=ChefSituation.TunableReference(description='\n                    A potential chef situation for hired chefs to be in.\n                    ')), tuning_group=GroupNames.BUSINESS), 'business_host_employee_type_and_situation': TunableTuple(description='\n            The Business Employee Type of the Host as well as the list of\n            situations that will be randomly chosen from when we spawn a hired\n            host.\n            ', employee_type=TunableEnumEntry(description='\n                The Business Employee Type for the Host.\n                ', tunable_type=BusinessEmployeeType, default=BusinessEmployeeType.INVALID, invalid_enums=(BusinessEmployeeType.INVALID,)), situation_list=TunableList(description='\n                The list of possible host situations, chosen at random, for\n                hired hosts to be in.\n                ', tunable=HostSituation.TunableReference(description='\n                    A potential host situation for hired hosts to be in.\n                    ')), tuning_group=GroupNames.BUSINESS), 'business_waitstaff_employee_type_and_situation': TunableTuple(description='\n            The Business Employee Type of the waitstaff as well as the list of\n            situations that will be randomly chosen from when we spawn a hired\n            waitstaff.\n            ', employee_type=TunableEnumEntry(description='\n                The Business Employee Type for the waitstaff.\n                ', tunable_type=BusinessEmployeeType, default=BusinessEmployeeType.INVALID, invalid_enums=(BusinessEmployeeType.INVALID,)), situation_list=TunableList(description='\n                The list of possible waitstaff situations, chosen at random, for\n                hired waitstaff to be in.\n                ', tunable=WaitstaffSituation.TunableReference(description='\n                    A potential waitstaff situation for hired waitstaff to be in.\n                    ')), tuning_group=GroupNames.BUSINESS)}
    EVENTS = (test_events.TestEvent.SimDeathTypeSet,)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._group_orders = {}
        self._order_bucket = defaultdict(list)
        self._table_group = {}
        self._sim_order_cache = {}
        self._dining_spot_pair_tests = None
        self._dining_spots = defaultdict(dict)
        self._table_dict_by_dining_num = defaultdict(list)
        self._groups_waiting_for_table = []
        self._attire_outfit_category = OutfitCategory.EVERYDAY
        self._preset_id = RestaurantTuning.DEFAULT_MENU
        self._custom_menu_map = None
        self._customize_staff_uniform = []
        self._default_staff_uniform = []
        self._daily_special_recipe_ids = {}
        self._last_daily_special_aboslute_day = 0
        services.get_event_manager().register(self, self.EVENTS)

    def create_situations_during_zone_spin_up(self):
        is_active_business = self.business_manager is not None and self.business_manager.is_owner_household_active
        if is_active_business and (services.current_zone().time_has_passed_in_world_since_zone_save() or services.current_zone().active_household_changed_between_save_and_load()) and self.business_manager.is_open:
            self._business_manager.start_already_opened_business()
            self._on_customer_situation_request()
        if is_active_business:
            return
        super().create_situations_during_zone_spin_up()
        time_of_day = services.time_service().sim_now
        for situation_shift in self.situation_shifts:
            time_span = situation_shift.shift_curve.get_timespan_to_next_shift_time(time_of_day)
            if time_span is not None:
                self._handle_situation_shift_churn(situation_shift, reserve_object_relationships=True)

    def on_startup(self):
        super().on_startup()
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None and business_manager.is_owner_household_active:
            self.destroy_shifts()
        self._load_default_uniforms()
        self._update_restaurant_config()
        self._update_dining_spots()
        self._try_choose_daily_special()

    def on_shutdown(self):
        event_manager = services.get_event_manager()
        if event_manager is not None:
            event_manager.unregister(self, self.EVENTS)
        self.clear_group_orders()
        if self._business_manager is not None:
            self._business_manager.prepare_for_off_lot_simulation()

    def clear_group_orders(self):
        for group_order in tuple(self._group_orders.values()):
            self._remove_group_order(group_order)

    def on_exit_buildbuy(self):
        super().on_exit_buildbuy()
        self.refresh_configuration()

    def refresh_configuration(self):
        self._update_restaurant_config()
        self._update_dining_spots()
        self._check_chef_reset_on_exit_build_buy()
        self._try_choose_daily_special()

    def _load_default_uniforms(self):
        self._load_uniform_from_resource(RestaurantTuning.UNIFORM_CHEF_MALE)
        self._load_uniform_from_resource(RestaurantTuning.UNIFORM_CHEF_FEMALE)
        self._load_uniform_from_resource(RestaurantTuning.UNIFORM_WAITSTAFF_MALE)
        self._load_uniform_from_resource(RestaurantTuning.UNIFORM_WAITSTAFF_FEMALE)
        self._load_uniform_from_resource(RestaurantTuning.UNIFORM_HOST_MALE)
        self._load_uniform_from_resource(RestaurantTuning.UNIFORM_HOST_FEMALE)

    def _load_uniform_from_resource(self, uniform_resource):
        sim_info_wrapper = SimInfoBaseWrapper()
        sim_info_wrapper.load_from_resource(uniform_resource)
        sim_info_wrapper.set_current_outfit((OutfitCategory.CAREER, 0))
        self._default_staff_uniform.append(sim_info_wrapper)

    def _on_objects_loaded(self):
        food_platters = list(services.object_manager().get_objects_of_type_gen(ChefTuning.CHEF_STATION_SERVING_PLATTER_OBJECT))
        business_manager = services.business_service().get_business_manager_for_zone()
        for order in self._group_orders.values():
            if any(food_platter.id == order.food_platter_id for food_platter in food_platters):
                self.set_order_status(order, OrderStatus.ORDER_GIVEN_TO_CHEF)
                if business_manager is not None:
                    business_manager.calculate_and_apply_expense_for_group_order(order, refund=True)
        for platter in food_platters:
            platter.destroy(cause='Remove loaded food platters')

    def _update_restaurant_config(self):
        config_data = build_buy.get_current_venue_config(services.current_zone_id())
        if config_data is None:
            return
        restaurant_config = Restaurant_pb2.RestaurantConfiguration()
        restaurant_config.ParseFromString(config_data)
        if restaurant_config.HasField('attire_id'):
            self._attire_outfit_category = restaurant_config.attire_id
        if self._business_manager is not None:
            self._preset_id = MenuPresets.CUSTOMIZE
        elif restaurant_config.HasField('preset_id'):
            self._preset_id = restaurant_config.preset_id
        if self._preset_id == MenuPresets.CUSTOMIZE and restaurant_config.HasField('custom_menu') and len(restaurant_config.custom_menu.courses) > 0:
            self._custom_menu_map = {}
            recipe_manager = services.recipe_manager()
            for course in restaurant_config.custom_menu.courses:
                course_tag = course.course_tag
                recipe_ids = []
                for recipe_item in course.items:
                    recipe = recipe_manager.get(recipe_item.recipe_id)
                    if recipe is not None:
                        recipe_ids.append(recipe)
                self._custom_menu_map[course_tag] = recipe_ids
        else:
            self._custom_menu_map = None
        self._customize_staff_uniform.clear()
        if len(restaurant_config.outfits) > 0:
            for outfit_data in restaurant_config.outfits:
                sim_info_wrapper = None
                mannequin_data = outfit_data.mannequin
                if mannequin_data.HasField('mannequin_id') and mannequin_data.HasField('gender'):
                    sim_info_wrapper = SimInfoBaseWrapper()
                    sim_info_wrapper.load_sim_info(outfit_data.mannequin)
                    sim_info_wrapper.set_current_outfit((OutfitCategory.CAREER, 0))
                self._customize_staff_uniform.append((outfit_data.outfit_index, sim_info_wrapper))

    def _update_dining_spots(self):
        dining_spot_tests = self._get_dining_spot_tests()
        if not dining_spot_tests:
            logger.error(' No dining spot test found in current venue. Please\n                check venue Required Object tuning to make sure\n                RestaurantTagTuning.DINING_SPOT_OBJECT_TEST_TAG is tuned under one\n                test set.')
            return
        table_ids_dirty = set()
        object_manager = services.object_manager()
        table_list = []
        child_tags = set()
        for test in dining_spot_tests:
            child_tags.update(test.object_tags.tag_set)
            for table in object_manager.get_objects_with_tags_gen(*test.parent_tags.tag_set):
                if table not in table_list and table.is_on_active_lot():
                    table_list.append(table)
        table_id_dict = {table.id: table for table in table_list}
        table_ids_removed = []
        for table_id in self._dining_spots:
            if table_id not in table_id_dict.keys():
                table_ids_removed.append(table_id)
        for table_id in self._table_group:
            if table_id not in table_id_dict.keys() and table_id not in table_ids_removed:
                table_ids_removed.append(table_id)
        for table_id_remove in table_ids_removed:
            table_ids_dirty.add(table_id_remove)
            if table_id_remove in self._dining_spots:
                del self._dining_spots[table_id_remove]
        self._table_dict_by_dining_num.clear()
        for table in table_list:
            dining_spot_dict = self._dining_spots[table.id]
            for part in table.parts:
                dining_spot = dining_spot_dict.get(part.part_group_index, None)
                seat_found = False
                if part.part_definition is self.picnic_part_definition:
                    seat_found = True
                    dining_spot = DiningSpot(table.id, None, part.part_group_index, None)
                else:
                    for child in part.children:
                        if child.has_any_tag(child_tags):
                            seat_found = True
                            child_part_index = child.part_group_index if child.is_part else None
                            if dining_spot is not None:
                                table_ids_dirty.add(table.id)
                                dining_spot.seat_id = child.id
                                dining_spot.chair_part_index = child_part_index
                            else:
                                dining_spot = DiningSpot(table.id, child.id, part.part_group_index, child_part_index)
                            break
                if dining_spot is not None:
                    sim_id = self.get_sim_in_seat(dining_spot.table_id, dining_spot.table_part_index)
                    if sim_id is not None:
                        sim = services.object_manager().get(sim_id)
                        if sim is not None:
                            dining_groups = self.get_dining_groups_by_sim(sim)
                            current_tables = self.get_tables_by_group_id(dining_groups[0].id)
                            if not self.assign_empty_seat_at_group_table(sim, current_tables):
                                table_ids_dirty.add(table.id)
                    dining_spot = None
                if seat_found or dining_spot is not None:
                    dining_spot_dict[part.part_group_index] = dining_spot
                elif part.part_group_index in dining_spot_dict:
                    del dining_spot_dict[part.part_group_index]
            dining_num = len(dining_spot_dict)
            if dining_num == 0:
                del self._dining_spots[table.id]
            else:
                self._table_dict_by_dining_num[dining_num].append(table.id)
        self._update_dirty_tables(table_ids_dirty)
        if self._business_manager is not None:
            self._business_manager.set_dining_spot_count(self.get_dining_spot_count())

    MIN_REQUIRED_ITEMS_FOR_DAILY_SPECIAL = 2

    def _try_choose_daily_special(self):
        if self._business_manager is not None and self._business_manager.is_owner_household_active:
            self._daily_special_recipe_ids = None
            return
        now = services.time_service().sim_now
        day_unchanged = int(now.absolute_days()) == self._last_daily_special_aboslute_day
        self._last_daily_special_aboslute_day = int(now.absolute_days())
        menu = self.get_current_menu()
        for (course, items) in menu.items():
            valid_items = list(items)
            for invalid_item in RestaurantTuning.INVALID_DAILY_SPECIAL_RECIPES:
                if invalid_item in valid_items:
                    valid_items.remove(invalid_item)
            if day_unchanged and course in self._daily_special_recipe_ids.keys():
                course_recipe_id = self._daily_special_recipe_ids[course]
                if any(valid_item.guid64 == course_recipe_id for valid_item in valid_items):
                    pass
                elif valid_items and len(valid_items) >= self.MIN_REQUIRED_ITEMS_FOR_DAILY_SPECIAL:
                    self._daily_special_recipe_ids[course] = random.choice(tuple(valid_items)).guid64
            elif valid_items and len(valid_items) >= self.MIN_REQUIRED_ITEMS_FOR_DAILY_SPECIAL:
                self._daily_special_recipe_ids[course] = random.choice(tuple(valid_items)).guid64

    def _update_dirty_tables(self, table_ids_dirty):
        table_ids_handled = []
        for table_id in table_ids_dirty:
            if table_id in table_ids_handled:
                pass
            elif table_id not in self._table_group:
                table_ids_handled.append(table_id)
            else:
                table_released = self.release_table(release_table_id=table_id)
                table_ids_handled.extend(table_released)

    def _get_dining_spot_tests(self):
        if self._dining_spot_pair_tests is not None:
            return self._dining_spot_pair_tests
        venue_tuning = services.venue_service().venue
        if venue_tuning is None:
            return
        tests = []
        for required_object_test in venue_tuning.required_objects:
            for pair_test in required_object_test.object_parent_pair_tests:
                if pair_test.required_object_test_tag == RestaurantTagTuning.DINING_SPOT_OBJECT_TEST_TAG:
                    tests.append(pair_test)
        self._dining_spot_pair_tests = tests
        return tests

    def is_dining_table(self, obj):
        return obj.id in self._dining_spots

    def is_picnic_table(self, obj_or_part):
        if obj_or_part.is_part:
            return obj_or_part.part_definition is self.picnic_part_definition
        if not obj_or_part.parts:
            return False
        for part in obj_or_part.parts:
            if part.part_definition is self.picnic_part_definition:
                return True
        return False

    def get_dining_table_by_chair(self, obj):
        for (table_id, dining_spots) in self._dining_spots.items():
            for dining_spot in dining_spots.values():
                if obj.id == dining_spot.seat_id:
                    return services.object_manager().get(table_id)

    def table_needs_cleaning(self, group_order):
        for eat_drink_object in group_order.slotted_objects_gen({RestaurantTuning.TABLE_DRINK_SLOT_TYPE, RestaurantTuning.TABLE_FOOD_SLOT_TYPE}):
            if eat_drink_object.state_value_active(RestaurantTuning.CONSUMABLE_EMPTY_STATE_VALUE):
                return True
        return False

    def make_one_order(self, sim, recipe):
        group_order = self.get_group_order(sim.id)
        (food_recipe_id, drink_recipe_id) = GroupOrder.get_food_drink_recipe_id_tuple(recipe)
        group_order.add_sim_order(sim.id, food_recipe_id=food_recipe_id, drink_recipe_id=drink_recipe_id)
        self.send_food_ordered_message_for_order(sim.id)
        self.on_order_update(group_order)

    def send_food_ordered_message_for_order(self, sim_id):
        zone = services.get_zone_manager().current_zone
        object_manager = services.object_manager(zone.id)
        sim = object_manager.get(sim_id)
        if sim is None:
            return
        services.get_event_manager().process_event(test_events.TestEvent.RestaurantFoodOrdered, sim_info=sim.sim_info)

    def order_for_table(self, sim_orders, recommendation_state=OrderRecommendationState.NO_RECOMMENDATION, order_status=OrderStatus.MENU_READY, group_order=None, send_order=True, complimentary=False):
        recipe_manager = services.recipe_manager()
        for (sim_id, recipe_id) in sim_orders:
            recipe = recipe_manager.get(recipe_id)
            if group_order is None:
                group_order = self.get_group_order(sim_id)
            self._sim_order_cache[sim_id] = group_order.order_id
            (food_recipe_id, drink_recipe_id) = GroupOrder.get_food_drink_recipe_id_tuple(recipe)
            group_order.add_sim_order(sim_id, food_recipe_id=food_recipe_id, drink_recipe_id=drink_recipe_id, recommendation_state=recommendation_state, order_status=order_status)
            if send_order:
                self.send_food_ordered_message_for_order(sim_id)
        if complimentary and group_order is not None:
            group_order.comp_order()
        self.on_order_update(group_order)

    def set_order_status(self, group_order, order_status):
        if group_order._order_status == order_status:
            return
        group_order._order_status = order_status
        self.on_order_update(group_order)

    def on_order_update(self, group_order):
        if group_order is None or not group_order.need_to_update_bucket():
            return
        if group_order.order_status == OrderStatus.ORDER_DELIVERED:
            self._remove_sims_from_sim_order_cache(group_order)
            if self.business_manager is None:
                group_order._order_status = OrderStatus.ORDER_READY_FOR_REMOVAL
        current_bucket_list = self._order_bucket[group_order.current_bucket]
        if current_bucket_list or group_order.current_bucket != OrderStatus.ORDER_INIT:
            logger.warn('Order {} is not in its current bucket {}', group_order.order_id, group_order.current_bucket)
        elif group_order.order_id in current_bucket_list:
            current_bucket_list.remove(group_order.order_id)
        self._order_bucket[group_order.order_status].append(group_order.order_id)
        group_order.move_to_bucket(group_order.order_status)
        if group_order.order_status == OrderStatus.ORDER_READY_FOR_REMOVAL:
            self._remove_group_order(group_order)

    def _remove_group_order(self, group_order):
        if group_order.order_id in self._group_orders:
            self._group_orders.pop(group_order.order_id)
        self._remove_sims_from_sim_order_cache(group_order)

    def _remove_sims_from_sim_order_cache(self, group_order):
        for sim_id in group_order.sim_ids:
            if sim_id in self._sim_order_cache:
                del self._sim_order_cache[sim_id]

    def get_all_group_orders_with_status(self, order_status):
        orders = []
        for group_order in self._group_orders.values():
            if group_order._order_status == order_status:
                orders.append(group_order)
        return orders

    def get_group_order_with_status(self, order_status):
        for group_order in self._group_orders.values():
            if group_order._order_status == order_status:
                return group_order

    def get_unclaimed_group_order_with_status(self, order_status):
        for group_order in self._group_orders.values():
            if group_order._order_status == order_status and group_order.assigned_waitstaff is None:
                return group_order

    def get_group_order_with_status_for_waitstaff(self, order_status, waitstaff):
        if order_status != OrderStatus.ORDER_READY:
            logger.error('Trying to get a group order for a waitstaff, {}, with an invalid status, {}.', waitstaff, order_status, owner='trevor')
            return
        none_waitstaff_orders = []
        for group_order in self._group_orders.values():
            if group_order.order_status == order_status:
                assigned_waitstaff = group_order.assigned_waitstaff
                if assigned_waitstaff is waitstaff:
                    return group_order
                else:
                    if assigned_waitstaff is None:
                        none_waitstaff_orders.append(group_order)
                    if none_waitstaff_orders:
                        order = none_waitstaff_orders.pop()
                        order.assign_waitstaff(waitstaff)
                        return order
        if none_waitstaff_orders:
            order = none_waitstaff_orders.pop()
            order.assign_waitstaff(waitstaff)
            return order

    def get_group_order_with_status_for_chef(self, order_status, chef):
        if order_status != OrderStatus.ORDER_GIVEN_TO_CHEF:
            logger.error('Trying to get a group order for a chef, {}, with an invalid status, {}.', chef, order_status, owner='trevor')
            return
        none_chef_orders = []

        def expedited_first(order):
            if order.expedited:
                return 0
            return 1

        for group_order in sorted(self._group_orders.values(), key=expedited_first):
            if group_order.order_status == order_status:
                assigned_chef = group_order.assigned_chef
                if assigned_chef is chef:
                    return group_order
                else:
                    if assigned_chef is None:
                        none_chef_orders.append(group_order)
                    if none_chef_orders:
                        order = none_chef_orders.pop()
                        order.assign_chef(chef)
                        return order
        if none_chef_orders:
            order = none_chef_orders.pop()
            order.assign_chef(chef)
            return order

    def _create_new_group(self, sim_id):
        group = GroupOrder(table_ids=self.get_tables_by_sim_ids((sim_id,)))
        group_id = group.order_id
        self._sim_order_cache[sim_id] = group_id
        self._group_orders[group_id] = group
        return group_id

    def get_group_order(self, sim_id):
        group_id = self._sim_order_cache.get(sim_id, None)
        if group_id is None:
            group_id = self._create_new_group(sim_id)
        group_order = self._group_orders[group_id]
        if group_order.order_status == OrderStatus.ORDER_DELIVERED or group_order.order_status == OrderStatus.ORDER_READY_FOR_REMOVAL:
            new_group_id = self._create_new_group(sim_id)
            group_order = self._group_orders[new_group_id]
        return group_order

    def has_group_order(self, sim_id):
        group_id = self._sim_order_cache.get(sim_id, None)
        if group_id is not None:
            return True
        return False

    def get_active_group_order_for_sim(self, sim_id):
        for group_order in self._group_orders.values():
            if not group_order.order_status == OrderStatus.ORDER_DELIVERED:
                if group_order.order_status == OrderStatus.ORDER_READY_FOR_REMOVAL:
                    pass
                elif sim_id in group_order.sim_ids:
                    return group_order

    def get_delivered_orders_for_sim(self, sim_id):
        return [order for order in self._group_orders.values() if order.order_status == OrderStatus.ORDER_DELIVERED and sim_id in order.sim_ids]

    def get_active_group_order_for_table(self, table_id):
        for group_order in self._group_orders.values():
            if not group_order.order_status == OrderStatus.ORDER_DELIVERED:
                if group_order.order_status == OrderStatus.ORDER_READY_FOR_REMOVAL:
                    pass
                elif table_id in group_order.table_ids:
                    return group_order

    def create_food_for_group_order(self, group_order):
        for (sim_id, sim_order) in group_order:
            food_recipe_id = sim_order.food_recipe_id
            drink_recipe_id = sim_order.drink_recipe_id
            table_part = self._get_table_part_by_sim_id(sim_id)
            diner_sim_info = services.sim_info_manager().get(sim_id)
            if table_part is None:
                logger.warn('Sim {} sim_id {} does not have a table part assigned for food order {} and drink order {}', diner_sim_info, sim_id, food_recipe_id, drink_recipe_id)
            else:
                diner_sim = diner_sim_info.get_sim_instance() if diner_sim_info is not None else None
                if diner_sim is not None:
                    self._create_and_slot_food_and_drink_to_table(food_recipe_id, drink_recipe_id, table_part, diner_sim, group_order.assigned_chef)
                    services.get_event_manager().process_event(test_events.TestEvent.RestaurantOrderDelivered, sim_info=diner_sim_info)
        self._try_show_food_delivered_notification(group_order)
        if self.business_manager is not None:
            self.business_manager.calculate_and_apply_sale_of_group_order(group_order)

    def _create_and_slot_food_and_drink_to_table(self, food_id, drink_id, table_part, diner_sim, chef_sim):
        if food_id is None and drink_id is None:
            return
        recipe_manager = services.recipe_manager()
        food_recipe = recipe_manager.get(food_id) if food_id is not None else None
        drink_recipe = recipe_manager.get(drink_id) if drink_id is not None else None
        food_instance = None
        if food_recipe is not None:
            food_instance = self._create_single_recipe_and_slot(food_recipe, RestaurantTuning.TABLE_FOOD_SLOT_TYPE, table_part, chef_sim)
            if food_instance is not None:
                food_instance.set_state(RestaurantTuning.CONSUMABLE_FULL_STATE_VALUE.state, RestaurantTuning.CONSUMABLE_FULL_STATE_VALUE)
                diner_sim.set_autonomy_preference(RestaurantTuning.FOOD_AUTONOMY_PREFERENCE, food_instance)
        if drink_recipe is not None:
            drink_instance = self._create_single_recipe_and_slot(drink_recipe, RestaurantTuning.TABLE_DRINK_SLOT_TYPE, table_part, chef_sim, push_reaction=food_instance is None)
            if drink_instance is not None:
                drink_instance.set_state(RestaurantTuning.CONSUMABLE_FULL_STATE_VALUE.state, RestaurantTuning.CONSUMABLE_FULL_STATE_VALUE)
                diner_sim.set_autonomy_preference(RestaurantTuning.DRINK_AUTONOMY_PREFERENCE, drink_instance)

    def _create_single_recipe_and_slot(self, recipe, slot_type, table_part, chef_sim, push_reaction=True):
        recipe_definition = recipe.final_product_definition
        recipe_instance = system.create_object(recipe_definition)
        if recipe_instance is None:
            logger.error('Trying to create recipe {} for table but failed', recipe_definition, owner='trevor')
            return
        slot_result = table_part.slot_object(parent_slot=slot_type, slotting_object=recipe_instance, objects_to_ignore=list(table_part.part_owner.children))
        if not slot_result:
            logger.error('Trying to slot created recipe {} to part {} but failed', recipe_instance, table_part, owner='trevor')
            recipe_instance.destroy()
            return
        if push_reaction:
            self._push_reaction_interaction(recipe_instance, table_part)
        for initial_state in reversed(recipe.final_product.initial_states):
            recipe_instance.set_state(initial_state.state, initial_state, from_init=True)
        for apply_state in reversed(recipe.final_product.apply_states):
            recipe_instance.set_state(apply_state.state, apply_state, from_init=True)
        crafting_process = CraftingProcess(crafter=chef_sim, recipe=recipe)
        crafting_process.setup_crafted_object(recipe_instance, is_final_product=True)
        if self.business_manager is not None:
            self.business_manager.set_states_for_recipe(recipe, recipe_instance, chef_sim)
        resolver = DoubleObjectResolver(chef_sim.sim_info, recipe_instance)
        for loot in recipe.final_product.chef_loot_list:
            loot.apply_to_resolver(resolver)
        resolver = SingleSimResolver(chef_sim.sim_info)
        if CraftingTuning.FOOD_POISONING_STATE is not None and recipe.food_poisoning_chance:
            chance = recipe.food_poisoning_chance.get_chance(resolver)
            if random.random() <= chance:
                recipe_instance.set_state(CraftingTuning.FOOD_POISONING_STATE, CraftingTuning.FOOD_POISONING_STATE_VALUE, from_init=True)
        return recipe_instance

    def _try_show_food_delivered_notification(self, group_order):
        for sim_id in group_order.sim_ids:
            sim_info = services.sim_info_manager().get(sim_id)
            if sim_info is None:
                logger.error("Trying to show the food delivered notification for sim id {} which doesn't have a sim info. Group Order = {}", sim_id, group_order)
                return
            if sim_info.is_selectable and sim_info.is_instanced():
                waitstaff = group_order.assigned_waitstaff
                if waitstaff is not None:
                    resolver = SingleSimResolver(waitstaff)
                    dialog = RestaurantTuning.FOOD_DELIVERED_TO_TABLE_NOTIFICATION(waitstaff, resolver)
                    dialog.show_dialog()
                    return

    def trigger_recommendation_interaction(self, restaurant_owner, customer_sim):
        context = InteractionContext(restaurant_owner, InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT, Priority.High)
        restaurant_owner.push_super_affordance(RestaurantTuning.RECOMMENDED_ORDER_INTERACTION, customer_sim, context)

    def _push_reaction_interaction(self, recipe_instance, table_part):
        object_manager = services.object_manager()
        for (table_id, dining_spots) in self._table_group.items():
            table = object_manager.get(table_id)
            if table_part.part_owner is table:
                for (sim_id, part_id) in dining_spots:
                    if part_id == table_part.part_group_index:
                        target_sim_id = sim_id
                        break
                break
        target_sim = object_manager.get(target_sim_id)
        if target_sim is not None:
            context = InteractionContext(target_sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
            target_sim.push_super_affordance(self.food_reaction_affordance, recipe_instance, context)

    def cancel_sims_group_order(self, sim, refund_cost=False):
        group_order = self.get_active_group_order_for_sim(sim.sim_info.id)
        if group_order is None:
            return
        self.cancel_group_order(group_order, refund_cost=refund_cost)

    def cancel_group_order(self, group_order, refund_cost=False):
        if group_order.order_status == OrderStatus.ORDER_READY or group_order.order_status == OrderStatus.ORDER_READY_DELAYED:
            if group_order.serving_from_chef is not None and group_order.serving_from_chef.parent is not None and not group_order.serving_from_chef.parent.is_sim:
                self._cancel_waitstaff_serve(group_order.serving_from_chef)
                group_order.serving_from_chef.schedule_destroy_asap()
                group_order.clear_serving_from_chef()
            if refund_cost:
                business_manager = services.business_service().get_business_manager_for_zone()
                if business_manager is not None:
                    business_manager.calculate_and_apply_expense_for_group_order(group_order, refund=True)
        self.set_order_status(group_order, OrderStatus.ORDER_CANCELED)
        self._remove_group_order(group_order)

    def assign_empty_seat_at_group_table(self, sim, table_ids):
        for current_table in table_ids:
            if self.claim_empty_spot_at_table(sim, current_table):
                return True
        return False

    def claim_table(self, sim, table=None):
        dining_groups = self.get_dining_groups_by_sim(sim)
        if dining_groups:
            current_tables = self.get_tables_by_group_id(dining_groups[0].id)
            if not self.assign_empty_seat_at_group_table(sim, current_tables):
                for current_table in current_tables:
                    self.release_table(None, current_table)
            table_to_claim = None
            if table is not None:
                if self.table_has_been_claimed(table.id):
                    self.release_table(None, table.id)
                table_to_claim = table
            if table_to_claim is not None and table_to_claim.id not in self._dining_spots:
                logger.error('Try to claim {} with no dining spots', table_to_claim)
                return
            invited_sim_ids = set()
            for situation in dining_groups:
                invited_sim_ids.update(situation.invited_sim_ids)
            sim_num = len(invited_sim_ids)
            tables_found = []
            table_id_to_claim = None
            if table_to_claim is not None:
                table_id_to_claim = table_to_claim.id
                sim_num -= len(self._dining_spots[table_id_to_claim])
                tables_found.append(table_id_to_claim)
            (sim_num_left, extra_tables) = self._find_tables_by_sim_num(sim_num, table_id_to_claim, tables_found)
            tables_found.extend(extra_tables)
            if sim_num_left > 0:
                (_, released_extra_tables) = self._find_tables_by_sim_num(sim_num_left, table_id_to_claim, tables_found, consider_occupied=True)
                tables_found.extend(released_extra_tables)
            if not tables_found:
                tables_available = self._find_tables_by_sim_num(sim_num, table_id_to_claim, tables_found, consider_occupied=False, search_only=True)
                logger.error('No table could be claimed by {}. Tables Available? {} Number of Sims: {} Number of Sims left {}', sim, tables_available, sim_num, sim_num_left)
                return
            for table_id in tables_found:
                dining_spots = self._dining_spots[table_id]
                sim_spot_list = []
                for dining_spot in dining_spots.values():
                    if dining_spot is None:
                        pass
                    else:
                        if not invited_sim_ids:
                            break
                        sim_id = invited_sim_ids.pop()
                        sim_spot_list.append((sim_id, dining_spot.table_part_index))
                if sim_spot_list:
                    self._table_group[table_id] = sim_spot_list
        for situation in dining_groups:
            self.remove_group_waiting_to_be_seated(situation.id)
            if not self.host_working():
                for sim in situation.all_sims_in_situation_gen():
                    services.get_event_manager().process_event(test_events.TestEvent.RestaurantTableClaimed, sim_info=sim.sim_info)

    def can_find_seating_for_group(self, group_size, consider_occupied=True):
        (sim_num_left, _) = self._find_tables_by_sim_num(group_size, consider_occupied=consider_occupied, search_only=True)
        if sim_num_left > 0:
            return False
        return True

    def release_table(self, sim=None, release_table_id=None, from_situation_destroy=False):
        target_table_found = False
        table_released = []
        if release_table_id is not None and release_table_id in self._dining_spots and not self.table_has_been_claimed(release_table_id):
            logger.warn("Trying to release table id: {} when it hasn't been claimed. Did something go wrong?", release_table_id)
            return table_released
        if sim is not None:
            dining_groups = self.get_dining_groups_by_sim(sim)
        elif release_table_id is not None:
            dining_groups = self.get_situations_by_table(release_table_id)
        else:
            logger.error('Trying to release a table with both the sim and table values set to None.')
            return table_released
        if not dining_groups:
            if release_table_id in self._table_group:
                table_released.append(release_table_id)
                del self._table_group[release_table_id]
            return table_released
        for situation in dining_groups:
            table_ids = self.get_tables_by_group_id(situation.id)
            table_released.extend(table_ids)
            if release_table_id in table_ids:
                target_table_found = True
            for table_id in table_ids:
                del self._table_group[table_id]
                self.empty_food_on_table(table_id)
            self.cancel_sims_group_order(next(situation.all_sims_in_situation_gen()))
            for sim in situation.all_sims_in_situation_gen():
                context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
                sim.push_super_affordance(RestaurantTuning.STAND_UP_INTERACTION, None, context)
            if not from_situation_destroy:
                situation.leave()
        if release_table_id is not None and not target_table_found:
            logger.error('{} tries to release {} not occupied by situations {}', sim, release_table_id, dining_groups)
        return table_released

    def release_all_tables(self):
        for table_id in self._dining_spots:
            if self.table_has_been_claimed(table_id):
                self.release_table(None, table_id)

    def claim_empty_spot_at_table(self, sim, table):
        dining_spots = self._dining_spots.get(table, None)
        if dining_spots is None:
            return False
        seated_sims = self._table_group[table]
        for dining_spot in dining_spots.values():
            for (_, table_part_id) in seated_sims:
                if dining_spot.table_part_index == table_part_id:
                    break
            seated_sims.append((sim.id, dining_spot.table_part_index))
            return True
        return False

    def claimed_table_test(self, sim_or_obj):
        if sim_or_obj.is_sim:
            return self.has_claimed_table(sim_or_obj)
        else:
            return self.table_has_been_claimed(sim_or_obj.id)

    def _get_sims_in_groups(self, dining_groups):
        sims = set()
        for group in dining_groups:
            sims.update(group.all_sims_in_situation_gen())
        return sims

    def get_dining_groups_by_sim(self, sim):
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None:
            return ()
        return situation_manager.get_situations_sim_is_in_by_tag(sim, RestaurantTuning.DINING_SITUATION_TAG)

    def get_group_sims_by_sim(self, sim):
        groups = self.get_dining_groups_by_sim(sim)
        sims = self._get_sims_in_groups(groups)
        sims.add(sim)
        return sims

    def get_group_sims_by_table(self, table_id):
        groups = self.get_situations_by_table(table_id)
        sims = self._get_sims_in_groups(groups) if groups is not None else ()
        return sims

    def get_situations_by_table(self, table_id):
        if table_id not in self._table_group:
            return
        (sim_id, _) = self._table_group[table_id][0]
        sim_info = services.sim_info_manager().get(sim_id)
        sim = sim_info.get_sim_instance() if sim_info is not None else None
        if sim is None:
            return
        return self.get_dining_groups_by_sim(sim)

    def has_claimed_table(self, sim):
        for (_, group_info) in self._table_group.items():
            for sim_part_tuple in group_info:
                (sim_id, _) = sim_part_tuple
                if sim_id == sim.id:
                    return True
        return False

    def has_sim_claimed_table(self, sim, table):
        tables = self.get_tables_by_sim_ids((sim.id,))
        if table.id not in tables:
            return False
        return True

    def table_has_been_claimed(self, table_id):
        if table_id not in self._dining_spots:
            return TestResult(False, '{} is not a table or not counted as dining table'.format(table_id))
        if table_id not in self._table_group:
            return TestResult(False, '{} is not claimed'.format(table_id))
        return TestResult.TRUE

    def _find_tables_by_sim_num(self, sim_num, table_id_to_claim=None, tables_found=(), consider_occupied=False, search_only=False):
        table_result = []
        if sim_num <= 0:
            return (0, table_result)
        dining_number_list = sorted(self._table_dict_by_dining_num.keys())
        for dining_num in dining_number_list:
            if dining_num < sim_num:
                pass
            else:
                closest_table_id = self._find_closest_table(table_id_to_claim, self._table_dict_by_dining_num[dining_num], tables_found, consider_occupied=consider_occupied, search_only=search_only)
                if closest_table_id is not None:
                    table_result.append(closest_table_id)
                    return (0, table_result)
        for dining_num in reversed(dining_number_list):
            if dining_num >= sim_num:
                pass
            else:
                closest_table_id = self._find_closest_table(table_id_to_claim, self._table_dict_by_dining_num[dining_num], tables_found, consider_occupied=consider_occupied, search_only=search_only)
                if closest_table_id is not None:
                    table_result.append(closest_table_id)
                    if table_id_to_claim is None:
                        table_id_to_claim = closest_table_id
                    temp_tables_found = []
                    temp_tables_found.append(closest_table_id)
                    temp_tables_found.extend(tables_found)
                    (sim_num_left, small_tables_found) = self._find_tables_by_sim_num(sim_num - dining_num, table_id_to_claim, temp_tables_found, consider_occupied=consider_occupied)
                    table_result.extend(small_tables_found)
                    return (sim_num_left, table_result)
        if not search_only:
            logger.error('Find nothing when try to claim {} for {} sims', table_id_to_claim, sim_num)
        return (sim_num, table_result)

    def _find_closest_table(self, original_table_id, table_ids, tables_found, consider_occupied=False, search_only=False):
        shortest_distance = sims4.math.MAX_FLOAT
        found_table_id = None
        found_table_dirty_id = None
        found_occupied_table_id = None
        object_manager = services.object_manager()
        original_table = None
        if original_table_id is not None:
            original_table = object_manager.get(original_table_id)
        for table_id in table_ids:
            table_obj = object_manager.get(table_id)
            if table_obj is None:
                pass
            elif table_id in tables_found:
                pass
            else:
                table_occupied = table_id in self._table_group
                table_dirty = self.table_has_dishes(table_obj)
                if table_occupied:
                    if not consider_occupied:
                        pass
                    else:
                        dining_groups = self.get_situations_by_table(table_id)
                        if dining_groups is not None and any(group.is_player_group() for group in dining_groups):
                            pass
                        else:
                            if original_table is None:
                                if table_occupied:
                                    found_occupied_table_id = table_id
                                elif table_dirty:
                                    found_table_dirty_id = table_id
                                else:
                                    found_table_id = table_id
                                    break
                            distance = (original_table.position - table_obj.position).magnitude_squared()
                            if distance < shortest_distance:
                                shortest_distance = distance
                                found_table_id = table_id
                else:
                    if original_table is None:
                        if table_occupied:
                            found_occupied_table_id = table_id
                        elif table_dirty:
                            found_table_dirty_id = table_id
                        else:
                            found_table_id = table_id
                            break
                    distance = (original_table.position - table_obj.position).magnitude_squared()
                    if distance < shortest_distance:
                        shortest_distance = distance
                        found_table_id = table_id
        if found_table_id is not None:
            return found_table_id
        if found_table_dirty_id is not None:
            return found_table_dirty_id
        if found_occupied_table_id is not None and not search_only:
            self.release_table(None, found_occupied_table_id)
        return found_occupied_table_id

    def table_has_dishes(self, table):
        if table.parts:
            for part in table.parts:
                for runtime_slot in part.get_runtime_slots_gen(slot_types={RestaurantTuning.TABLE_DRINK_SLOT_TYPE, RestaurantTuning.TABLE_FOOD_SLOT_TYPE}):
                    if runtime_slot.children:
                        return True
        return False

    def get_tables_by_group_id(self, group_id):
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None:
            return []
        group = situation_manager.get(group_id)
        if group is None:
            return []
        sims_in_group = self._get_sims_in_groups((group,))
        return self.get_tables_by_sims(sims_in_group)

    def get_tables_by_sim_ids(self, sim_ids):
        tables = set()
        for (table_id, group_info) in self._table_group.items():
            for (sim_id, _) in group_info:
                if sim_id in sim_ids:
                    tables.add(table_id)
        return tables

    def get_tables_by_sims(self, sims):
        ids = [sim.id for sim in sims]
        return self.get_tables_by_sim_ids(ids)

    def seat_claimed_by_sim(self, sim, seat):
        if self.is_picnic_table(seat):
            table_part = seat
        else:
            table_part = seat.parent
        if table_part is None:
            return False
        table_id = table_part.part_owner.id
        if table_id not in self._table_group:
            return False
        else:
            group_info = self._table_group[table_id]
            for (sim_id, table_part_index) in group_info:
                if table_part_index == table_part.part_group_index:
                    if sim_id == sim.id:
                        return True
                    return False
        return False
        return False

    def seat_is_dining_spot(self, seat):
        if self.is_picnic_table(seat):
            return True
        table_part = seat.parent
        if table_part is None:
            return False
        table_id = table_part.part_owner.id
        return table_id in self._dining_spots

    def group_waiting_to_be_seated(self):
        return len(self._group_waiting_for_table) > 0

    def get_next_group_id_to_seat(self):
        if self._groups_waiting_for_table:
            return self._groups_waiting_for_table[0]

    def get_sims_seat(self, sim):
        found_table_id = None
        for (table_id, table_part_data) in self._table_group.items():
            for (sim_id, table_part_id) in table_part_data:
                if sim_id == sim.id:
                    found_table_id = table_id
                    found_part_id = table_part_id
                    break
            if found_table_id is not None:
                break
        if found_table_id is not None:
            for (table_id, data) in self._dining_spots.items():
                if table_id == found_table_id:
                    for (part_id, dining_spot) in data.items():
                        if part_id == found_part_id:
                            if dining_spot.seat_id is None and self.is_picnic_table(services.object_manager().get(found_table_id)):
                                return (dining_spot.table_id, dining_spot.table_part_index)
                            return (dining_spot.seat_id, dining_spot.chair_part_index)
        return (None, None)

    def release_sims_seat(self, sim):
        table_part = self._get_table_part_by_sim_id(sim.sim_info.id)
        if table_part is None:
            return
        table = table_part.part_owner
        table_part_data = self._table_group[table.id]
        for (sim_id, table_part_index) in table_part_data:
            if sim_id == sim.id:
                if len(table_part_data) == 1:
                    del self._table_group[table.id]
                else:
                    table_part_data.remove((sim_id, table_part_index))

    def get_dining_spot_by_seat(self, seat_id, chair_part_index=None, use_table_as_seat=False):
        for (_, dining_spots) in self._dining_spots.items():
            for dining_spot in dining_spots.values():
                if not seat_id == dining_spot.seat_id:
                    if use_table_as_seat and seat_id == dining_spot.table_id:
                        if use_table_as_seat:
                            if not dining_spot.table_part_index == chair_part_index:
                                pass
                            else:
                                return dining_spot
                        elif not dining_spot.chair_part_index == chair_part_index:
                            pass
                        else:
                            return dining_spot
                        return dining_spot
                if use_table_as_seat:
                    if not dining_spot.table_part_index == chair_part_index:
                        pass
                    else:
                        return dining_spot
                elif not dining_spot.chair_part_index == chair_part_index:
                    pass
                else:
                    return dining_spot
                return dining_spot

    def _get_table_part_by_sim_id(self, sim_id):
        for (table_id, table_part_data) in self._table_group.items():
            for (data_sim_id, table_part_index) in table_part_data:
                if data_sim_id == sim_id:
                    table = services.object_manager().get(table_id)
                    if table is not None:
                        return table.parts[table_part_index]

    def reassign_dining_spot(self, new_sim_id, dining_spot):
        for (table_id, seat_data) in self._table_group.items():
            if table_id == dining_spot.table_id:
                for (sim_id, table_part_index) in seat_data:
                    if table_part_index == dining_spot.table_part_index:
                        break
                sim_id = None
                if sim_id is not None:
                    seat_data.remove((sim_id, table_part_index))
                if new_sim_id is not None:
                    seat_data.append((new_sim_id, dining_spot.table_part_index))
                return sim_id

    def get_sim_in_seat(self, table_id, table_part_index):
        seat_info = self._table_group.get(table_id, [])
        for (sim_id, part_index) in seat_info:
            if part_index == table_part_index:
                return sim_id

    def add_group_waiting_to_be_seated(self, group_id):
        self._groups_waiting_for_table.append(group_id)
        services.get_event_manager().process_event(test_events.TestEvent.GroupWaitingToBeSeated)

    def remove_group_waiting_to_be_seated(self, group_id):
        if group_id in self._groups_waiting_for_table:
            self._groups_waiting_for_table.remove(group_id)

    def waitstaff_working(self):
        situation_manager = services.get_zone_situation_manager()
        return situation_manager.get_situation_by_type(RestaurantTuning.WAITSTAFF_SITUATION) is not None

    def host_working(self):
        situation_manager = services.get_zone_situation_manager()
        return situation_manager.get_situation_by_type(RestaurantTuning.HOST_SITUATION) is not None

    def show_menu(self, sim, chef_order=False, is_recommendation=False):
        if chef_order or is_recommendation:
            group_sim_ids = (sim.id,)
        else:
            group_sims = self.get_group_sims_by_sim(sim)
            group_sim_ids = [sim.id for sim in group_sims]
        now = services.time_service().sim_now
        if int(now.absolute_days()) != self._last_daily_special_aboslute_day:
            self._try_choose_daily_special()
        show_menu_message = get_menu_message(self.get_current_menu().items(), group_sim_ids, chef_order=chef_order, is_recommendation=is_recommendation, daily_special_ids_map=self._daily_special_recipe_ids)
        if sim.sim_id in self._sim_order_cache:
            group_id = self._sim_order_cache[sim.sim_id]
            group_order = self._group_orders[group_id]
            for (sim_id, sim_order) in group_order:
                if sim_order.food_recipe_id is not None:
                    order_item = show_menu_message.sim_orders.add()
                    order_item.sim_id = sim_id
                    order_item.recipe_id = sim_order.food_recipe_id
                    order_item.locked = True
                if sim_order.drink_recipe_id is not None:
                    order_item = show_menu_message.sim_orders.add()
                    order_item.sim_id = sim_id
                    order_item.recipe_id = sim_order.drink_recipe_id
                    order_item.locked = True
        dining_groups = self.get_dining_groups_by_sim(sim)
        show_menu_message.running_bill_total = sum(dining_group.meal_cost for dining_group in dining_groups)
        op = ShowMenu(show_menu_message)
        Distributor.instance().add_op_with_no_owner(op)

    def get_current_menu(self):
        if self._custom_menu_map is not None:
            return self._custom_menu_map
        current_preset = RestaurantTuning.MENU_PRESETS[self._preset_id]
        return current_preset.recipe_map

    def get_menu_for_course(self, course_tag):
        return self.get_current_menu().get(course_tag, {})

    def apply_zone_outfit(self, sim_info, situation):
        outfit_type = self._get_outfit_type(sim_info, situation)
        if outfit_type is not None:
            outfit_index = 0
            outfit_data = None
            if self._customize_staff_uniform:
                (outfit_index, outfit_data) = self._customize_staff_uniform[outfit_type]
            if outfit_data is None:
                outfit_data = self._default_staff_uniform[outfit_type]
            sim_info.generate_merged_outfit(outfit_data, (OutfitCategory.CAREER, 0), sim_info.get_current_outfit(), (OutfitCategory.CAREER, outfit_index))
            sim_info.set_current_outfit((OutfitCategory.CAREER, 0))
            sim_info.resend_current_outfit()
        else:
            sim_info.set_current_outfit_for_category(self._attire_outfit_category)
            sim_info.resend_current_outfit()

    def _get_outfit_type(self, sim_info, situation):
        if sim_info.clothing_preference_gender == Gender.MALE:
            if isinstance(situation, RestaurantTuning.WAITSTAFF_SITUATION):
                return RestaurantOutfitType.MALE_WAITSTAFF
            if isinstance(situation, RestaurantTuning.HOST_SITUATION):
                return RestaurantOutfitType.MALE_HOST
            if isinstance(situation, RestaurantTuning.CHEF_SITUATION):
                return RestaurantOutfitType.MALE_CHEF
        elif sim_info.clothing_preference_gender == Gender.FEMALE:
            if isinstance(situation, RestaurantTuning.WAITSTAFF_SITUATION):
                return RestaurantOutfitType.FEMALE_WAITSTAFF
            if isinstance(situation, RestaurantTuning.HOST_SITUATION):
                return RestaurantOutfitType.FEMALE_HOST
            elif isinstance(situation, RestaurantTuning.CHEF_SITUATION):
                return RestaurantOutfitType.FEMALE_CHEF

    def get_zone_dress_code(self):
        return self._attire_outfit_category

    def get_table_count(self):
        return len(self._dining_spots)

    def get_dining_spot_count(self):
        dining_spots = set()
        for dining_spot_data in self._dining_spots.values():
            dining_spots.update(dining_spot_data.values())
        return len(dining_spots)

    def zone_director_specific_destination_tests(self, sim, obj):
        if self.get_dining_spot_by_seat(obj.id, use_table_as_seat=self.is_picnic_table(obj)) and not self.seat_claimed_by_sim(sim, obj):
            return False
        return True

    def additional_social_picker_tests(self, actor, target):
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None:
            return True
        actor_dining_groups = situation_manager.get_situations_sim_is_in_by_tag(actor, RestaurantTuning.DINING_SITUATION_TAG)
        target_dining_groups = situation_manager.get_situations_sim_is_in_by_tag(target, RestaurantTuning.DINING_SITUATION_TAG)
        actor_seated = any(actor_dining_group.seated for actor_dining_group in actor_dining_groups)
        target_seated = any(target_dining_group.seated for target_dining_group in target_dining_groups)
        if actor_seated != target_seated:
            return TestResult(False, 'Cannot socialize with {} because we are at different parts of the restaurant dining flow. {} Seated: {}, {} Seated: {}', target, actor, actor_seated, target, target_seated)
        elif actor_seated and actor.posture.posture_type is PostureConstants.SIT_POSTURE_TYPE and target.posture.posture_type is not PostureConstants.SIT_POSTURE_TYPE:
            return TestResult(False, "{} is currently sitting and {} is not. We don't want Sims in restaurants getting up to follow people away from the table.", actor, target)
        return True

    def disable_sim_affinity_posture_scoring(self, sim):
        tolerance = sim.get_off_lot_autonomy_rule().tolerance
        if sim.is_on_active_lot(tolerance=tolerance):
            return True
        return False

    def _cancel_waitstaff_serve(self, serving_platter=None):
        situation_manager = services.get_zone_situation_manager()
        waitstaff_situations = situation_manager.get_situations_by_type(RestaurantTuning.WAITSTAFF_SITUATION)
        for waitstaff in waitstaff_situations:
            if waitstaff.is_delivering_food(serving_platter):
                waitstaff.cancel_delivering_food()

    def empty_food_on_table(self, table_id):
        for consumable in food_on_table_gen(table_id):
            if consumable.state_component:
                consumable.set_state(CraftingTuning.CONSUMABLE_EMPTY_STATE_VALUE.state, CraftingTuning.CONSUMABLE_EMPTY_STATE_VALUE)
            consumable.cancel_interactions_running_on_object(FinishingType.OBJECT_CHANGED, cancel_reason_msg='Food was emptied as a result of giving up a table which cancels consumption.')

    def _check_chef_reset_on_exit_build_buy(self):
        situation_manager = services.get_zone_situation_manager()
        for chef_situation in situation_manager.get_situations_by_type(RestaurantTuning.CHEF_SITUATION):
            chef_situation.check_reset_on_exit_build_buy()

    def _save_custom_zone_director(self, zone_director_proto, writer):
        zone_director_proto.restaurant_data = GameplaySaveData_pb2.RestaurantZoneDirectorData()
        for (table_id, sim_seats) in self._table_group.items():
            table_group_data = zone_director_proto.restaurant_data.table_group.add()
            table_group_data.table_id = table_id
            for (sim_id, part_index) in sim_seats:
                sim_seat_data = table_group_data.sim_seats.add()
                sim_seat_data.sim_id = sim_id
                sim_seat_data.part_index = part_index
        if self._daily_special_recipe_ids is not None:
            zone_director_proto.restaurant_data.last_daily_special_absolute_day = self._last_daily_special_aboslute_day
            for (course, recipe_id) in self._daily_special_recipe_ids.items():
                saved_daily_special = zone_director_proto.restaurant_data.saved_daily_specials.add()
                saved_daily_special.course_tag = course
                saved_daily_special.recipe_id = recipe_id
        for (_, group_order) in self._group_orders.items():
            with ProtocolBufferRollback(zone_director_proto.restaurant_data.group_orders) as group_order_data:
                group_order.save_order(group_order_data)
        super()._save_custom_zone_director(zone_director_proto, writer)

    def _save_employee_situations(self, zone_director_proto, writer):
        pass

    def _load_custom_zone_director(self, zone_director_proto, reader):
        restaurant_data = zone_director_proto.restaurant_data
        if not services.current_zone().active_household_changed_between_save_and_load():
            for table_group_data in restaurant_data.table_group:
                if table_group_data.table_id not in self._dining_spots:
                    pass
                else:
                    sim_seat_list = []
                    for sim_seat in table_group_data.sim_seats:
                        sim_seat_list.append((sim_seat.sim_id, sim_seat.part_index))
                    self._table_group[table_group_data.table_id] = sim_seat_list
            for group_order_data in restaurant_data.group_orders:
                group_order = GroupOrder()
                group_order.load_order(group_order_data)
                self._group_orders[group_order.order_id] = group_order
                self._order_bucket[group_order.current_bucket].append(group_order.order_id)
                for (sim_id, _) in group_order:
                    self._sim_order_cache[sim_id] = group_order.order_id
        logger.debug('Restaurant Loaded, {} seats and {} orders', len(self._table_group), len(self._group_orders))
        if services.current_zone().time_has_passed_in_world_since_zone_save() or self._daily_special_recipe_ids is not None:
            self._last_daily_special_aboslute_day = restaurant_data.last_daily_special_absolute_day
            for saved_daily_special in restaurant_data.saved_daily_specials:
                self._daily_special_recipe_ids[saved_daily_special.course_tag] = saved_daily_special.recipe_id
            self._try_choose_daily_special()
        current_zone = services.current_zone()
        if current_zone.is_zone_loading:
            current_zone.register_callback(zone_types.ZoneState.OBJECTS_LOADED, self._on_objects_loaded)
        else:
            self._on_objects_loaded()
        super()._load_custom_zone_director(zone_director_proto, reader)

    def _load_employee_situations(self, zone_director_proto, reader):
        pass

    def _get_employee_situation_for_employee_type(self, employee_type):
        if employee_type == self.business_waitstaff_employee_type_and_situation.employee_type:
            return random.choice(self.business_waitstaff_employee_type_and_situation.situation_list)
        if employee_type == self.business_host_employee_type_and_situation.employee_type:
            return random.choice(self.business_host_employee_type_and_situation.situation_list)
        if employee_type == self.business_chef_employee_type_and_situation.employee_type:
            return random.choice(self.business_chef_employee_type_and_situation.situation_list)
        logger.error('Trying to get an npc employee situation for an invalid employee type: {}.', employee_type, owner='trevor')

    def _get_npc_employee_situation_for_employee_type(self, employee_type):
        return self._get_employee_situation_for_employee_type(employee_type)

    def _on_customer_situation_request(self):
        self.remove_stale_customer_situations()
        situation_manager = services.get_zone_situation_manager()
        desired_customer_count = self._get_ideal_customer_count()
        current_customer_count = sum([situation_manager.get(situation_id).num_invited_sims for situation_id in self._customer_situation_ids])
        needed_customer_count = desired_customer_count - current_customer_count
        while needed_customer_count > 0:
            (new_customer_situation, params) = self.customer_situation_type_curve.get_situation_and_params()
            if new_customer_situation is None:
                break
            situation_id = self.start_customer_situation(new_customer_situation, create_params=params)
            if situation_id is None:
                logger.error('Trying to create a new customer situation for restaurants but failed.')
                return
            created_situation = services.get_zone_situation_manager().get(situation_id)
            needed_customer_count -= created_situation.num_invited_sims

    def _on_customers_disallowed(self):
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None:
            return
        bouncer = situation_manager.bouncer
        unfulfilled_restaurant_sit = bouncer.get_unfulfilled_situations_by_tag(RestaurantTuning.DINING_SITUATION_TAG)
        for (situation_id, _) in unfulfilled_restaurant_sit.items():
            situation_manager.destroy_situation_by_id(situation_id)

    def _get_ideal_customer_count(self):
        ideal_count = self._business_manager.get_ideal_customer_count()
        if self.business_manager.owner_household_id is not None:
            tracker = services.business_service().get_business_tracker_for_household(self.business_manager.owner_household_id, self.business_manager.business_type)
            ideal_count += tracker.addtitional_customer_count
        return min(ideal_count, self.get_dining_spot_count())

    def handle_event(self, sim_info, event, resolver):
        if event == test_events.TestEvent.SimDeathTypeSet:
            business_manager = services.business_service().get_business_manager_for_zone()
            if business_manager is None or business_manager.is_owned_by_npc:
                return
            if business_manager.should_show_no_way_to_make_money_notification():
                active_sim_info = services.active_sim_info()
                notification = business_manager.tuning_data.no_way_to_make_money_notification(active_sim_info, resolver=SingleSimResolver(active_sim_info))
                notification.show_dialog()

    def _process_zone_saved_sim(self, sim_info):
        if services.current_zone().time_has_passed_in_world_since_zone_save() or services.current_zone().active_household_changed_between_save_and_load():
            self._on_clear_zone_saved_sim(sim_info)
            return
        super()._process_zone_saved_sim(sim_info)

    @property
    def supported_business_types(self):
        return SUPPORTED_BUSINESS_TYPES
