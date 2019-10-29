import weakreffrom restaurants.restaurant_tag_tuning import RestaurantTagTuningfrom restaurants.restaurant_tuning import RestaurantTuning, get_restaurant_zone_directorfrom sims4.math import MAX_UINT64from uid import unique_idimport enumimport servicesimport sims4logger = sims4.log.Logger('Restaurant', default_owner='cjiang')
class OrderStatus(enum.Int, export=False):
    ORDER_INIT = 0
    MENU_READY = 1
    ORDER_ASSIGNED_TO_WAITSTAFF = 2
    ORDER_TAKEN = 3
    ORDER_GIVEN_TO_CHEF = 4
    ORDER_READY = 5
    ORDER_READY_DELAYED = 6
    ORDER_DELIVERED = 7
    ORDER_DELIVERY_FAILED = 8
    ORDER_CANCELED = 9
    ORDER_READY_FOR_REMOVAL = 10

class OrderRecommendationState(enum.Int, export=False):
    NO_RECOMMENDATION = 0
    RECOMMENDATION_PROPOSAL = 1
    RECOMMENDATION_REJECTED = 2
    RECOMMENDATION_ACCEPTED = 3

class SimOrder:

    def __init__(self, food_recipe_id=None, drink_recipe_id=None, recommendation_state=OrderRecommendationState.NO_RECOMMENDATION):
        self.food_recipe_id = food_recipe_id
        self.drink_recipe_id = drink_recipe_id
        self.recommendation_state = recommendation_state

@unique_id('order_id', 1, MAX_UINT64 - 2)
class GroupOrder:

    def __init__(self, situation_id=None, table_ids=(), order_status=OrderStatus.ORDER_INIT):
        self._situation_id = situation_id
        self._table_ids = table_ids
        self._order_status = order_status
        self._current_bucket = order_status
        self._sim_orders = {}
        self._assigned_waitstaff_ref = None
        self._assigned_chef = None
        self._serving_from_chef = None
        self._food_platter_id = None
        self._is_complimentary = False
        self._expedited = False

    def __iter__(self):
        return iter(self._sim_orders.items())

    @property
    def table_ids(self):
        return self._table_ids

    @property
    def sim_ids(self):
        return self._sim_orders.keys()

    @property
    def expedited(self):
        return self._expedited

    @expedited.setter
    def expedited(self, value):
        self._expedited = value

    def is_player_group_order(self):
        for sim_id in self.sim_ids:
            sim_info = services.sim_info_manager().get(sim_id)
            if sim_info.is_selectable and sim_info.is_instanced():
                return True
        return False

    @classmethod
    def get_food_drink_recipe_id_tuple(cls, recipe):
        if RestaurantTagTuning.RECIPE_FOOD_TAG in recipe.recipe_tags:
            food_recipe_id = recipe.guid64
            drink_recipe_id = None
        else:
            food_recipe_id = None
            drink_recipe_id = recipe.guid64
        return (food_recipe_id, drink_recipe_id)

    def add_sim_order(self, sim_id, food_recipe_id=None, drink_recipe_id=None, recommendation_state=OrderRecommendationState.NO_RECOMMENDATION, order_status=OrderStatus.MENU_READY):
        if food_recipe_id is None and drink_recipe_id is None:
            return False
        sim_order = self._sim_orders.get(sim_id, None)
        if sim_order is None:
            sim_order = SimOrder(food_recipe_id=food_recipe_id, drink_recipe_id=drink_recipe_id, recommendation_state=recommendation_state)
            self._sim_orders[sim_id] = sim_order
        else:
            if sim_order.food_recipe_id is not None and food_recipe_id is not None:
                return False
            if sim_order.drink_recipe_id is not None and drink_recipe_id is not None:
                return False
            sim_order.food_recipe_id = sim_order.food_recipe_id or food_recipe_id
            sim_order.drink_recipe_id = sim_order.drink_recipe_id or drink_recipe_id
            sim_order.recommendation_state = recommendation_state
        if self._order_status != order_status:
            self._order_status = order_status
        return True

    def need_to_update_bucket(self):
        return self._order_status != self._current_bucket

    def move_to_bucket(self, bucket_status):
        self._current_bucket = bucket_status

    @property
    def current_bucket(self):
        return self._current_bucket

    @property
    def order_status(self):
        return self._order_status

    @property
    def is_canceled(self):
        return self.order_status == OrderStatus.ORDER_CANCELED

    @property
    def is_order_ready(self):
        return self.order_status == OrderStatus.ORDER_READY

    @property
    def sim_order_count(self):
        return len(self._sim_orders)

    def remove_sim_order(self, sim_id):
        if sim_id in self._sim_orders:
            del self._sim_orders[sim_id]

    def get_sim_order(self, sim_id):
        return self._sim_orders.get(sim_id, None)

    def get_first_table(self):
        if not self._table_ids:
            return
        table_id = next(iter(self._table_ids))
        return services.object_manager().get(table_id)

    def assign_waitstaff(self, waitstaff_sim):
        self._assigned_waitstaff_ref = weakref.ref(waitstaff_sim)

    @property
    def assigned_waitstaff(self):
        if self._assigned_waitstaff_ref is None:
            return
        return self._assigned_waitstaff_ref()

    def assign_serving_from_chef(self, serving):
        self._serving_from_chef = weakref.ref(serving)

    def clear_serving_from_chef(self):
        self._serving_from_chef = None

    @property
    def serving_from_chef(self):
        if self._serving_from_chef is None:
            return
        return self._serving_from_chef()

    @property
    def food_platter_id(self):
        if self.serving_from_chef is not None:
            return self.serving_from_chef.id
        return self._food_platter_id

    def assign_chef(self, chef):
        self._assigned_chef = weakref.ref(chef)

    @property
    def assigned_chef(self):
        if self._assigned_chef is None:
            return
        return self._assigned_chef()

    def comp_order(self):
        self._is_complimentary = True

    @property
    def is_complimentary(self):
        return self._is_complimentary

    def has_food_order(self):
        for order in self._sim_orders.values():
            if order.food_recipe_id is not None:
                return True
        return False

    def has_drink_order(self):
        for order in self._sim_orders.values():
            if order.drink_recipe_id is not None:
                return True
        return False

    def is_ready_to_be_taken(self):
        if not self._sim_orders:
            return False
        for order in self._sim_orders.values():
            if order.recommendation_state == OrderRecommendationState.RECOMMENDATION_PROPOSAL:
                return False
        return True

    def slotted_objects_gen(self, slot_types):
        zone_director = get_restaurant_zone_director()
        for sim_id in self.sim_ids:
            table_part = zone_director._get_table_part_by_sim_id(sim_id)
            if table_part is None:
                logger.warn('A Sim in a group no longer has an assigned table part. This might be because that Sim has left the restaurant.')
            else:
                for runtime_slot in table_part.get_runtime_slots_gen(slot_types=slot_types):
                    yield from runtime_slot.children

    def process_table_for_unfinished_food_drink(self):
        zone_director = get_restaurant_zone_director()
        if self.has_food_order():
            for eat_object in self.slotted_objects_gen({RestaurantTuning.TABLE_FOOD_SLOT_TYPE}):
                if eat_object.is_prop or not eat_object.state_value_active(RestaurantTuning.CONSUMABLE_EMPTY_STATE_VALUE):
                    if self._order_status == OrderStatus.ORDER_READY:
                        eat_object.add_state_changed_callback(self._unfinished_food_drink_state_change)
                        zone_director.set_order_status(self, OrderStatus.ORDER_READY_DELAYED)
                    return True
        if self.has_drink_order():
            for drink_object in self.slotted_objects_gen({RestaurantTuning.TABLE_DRINK_SLOT_TYPE}):
                if drink_object.is_prop or not drink_object.state_value_active(RestaurantTuning.CONSUMABLE_EMPTY_STATE_VALUE):
                    if self._order_status == OrderStatus.ORDER_READY:
                        drink_object.add_state_changed_callback(self._unfinished_food_drink_state_change)
                        zone_director.set_order_status(self, OrderStatus.ORDER_READY_DELAYED)
                    return True
        if self._order_status == OrderStatus.ORDER_READY_DELAYED:
            zone_director.set_order_status(self, OrderStatus.ORDER_READY)
        return False

    def _unfinished_food_drink_state_change(self, owner, state, old_value, new_value):
        if new_value == RestaurantTuning.CONSUMABLE_EMPTY_STATE_VALUE:
            owner.remove_state_changed_callback(self._unfinished_food_drink_state_change)
            self.process_table_for_unfinished_food_drink()

    def save_order(self, order_data):
        order_data.order_id = self.order_id
        if self._situation_id is not None:
            order_data.situation_id = self._situation_id
        order_data.order_status = self.order_status
        order_data.current_bucket = self.current_bucket
        order_data.is_complimentary = self._is_complimentary
        if self.table_ids:
            order_data.table_ids.extend(self.table_ids)
        for (sim_id, sim_order) in self._sim_orders.items():
            sim_order_data = order_data.sim_orders.add()
            sim_order_data.sim_id = sim_id
            if sim_order.food_recipe_id is not None:
                sim_order_data.food_recipe_id = sim_order.food_recipe_id
            if sim_order.drink_recipe_id is not None:
                sim_order_data.drink_recipe_id = sim_order.drink_recipe_id
            sim_order_data.recommendation_state = sim_order.recommendation_state
        if self.serving_from_chef is not None:
            order_data.serving_object_id = self.serving_from_chef.id

    def load_order(self, order_data):
        self.order_id = order_data.order_id
        self._situation_id = order_data.situation_id
        if order_data.order_status > self.order_status:
            self._order_status = OrderStatus(order_data.order_status)
        if order_data.current_bucket > self.current_bucket:
            self._current_bucket = OrderStatus(order_data.current_bucket)
        self._table_ids = tuple(order_data.table_ids)
        self._is_complimentary = order_data.is_complimentary
        for sim_order in order_data.sim_orders:
            order_item = SimOrder()
            if sim_order.HasField('food_recipe_id'):
                order_item.food_recipe_id = sim_order.food_recipe_id
            if sim_order.HasField('drink_recipe_id'):
                order_item.drink_recipe_id = sim_order.drink_recipe_id
            order_item.recommendation_state = OrderRecommendationState(sim_order.recommendation_state)
            self._sim_orders[sim_order.sim_id] = order_item
        if order_data.HasField('serving_object_id'):
            self._food_platter_id = order_data.serving_object_id
