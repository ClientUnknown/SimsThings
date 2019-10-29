from collections import namedtuplefrom protocolbuffers import Consts_pb2import randomfrom buffs.buff import Bufffrom business.business_employee_situation_mixin import BusinessEmployeeSituationMixinfrom crafting.crafting_process import CraftingProcessfrom event_testing import test_eventsfrom event_testing.test_events import TestEventfrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom objects import systemfrom objects.components import typesfrom objects.components.slot_component import SlotComponentfrom restaurants import restaurant_utilsfrom restaurants.chef_tuning import ChefTuningfrom restaurants.restaurant_order import OrderStatus, GroupOrderfrom restaurants.restaurant_tuning import RestaurantTuning, get_restaurant_zone_directorfrom sims4.tuning.tunable import TunableRange, TunableMapping, Tunablefrom situations.complex.staffed_object_situation_mixin import StaffedObjectSituationMixinfrom situations.situation import Situationfrom situations.situation_complex import CommonInteractionCompletedSituationState, SituationStateData, SituationComplexCommonimport servicesimport sims4.loglogger = sims4.log.Logger('ChefSituation', default_owner='trevor')
class DirectOrder(namedtuple('DirectOrder', 'ordered_recipe ordering_sim')):

    @property
    def is_canceled(self):
        pass

class _ChefSituationStateBase(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        next_state = self._get_next_state()
        if next_state is not None:
            self._change_state(next_state())

    def _get_next_state(self):
        return self.owner.get_next_state()

    def _additional_tests(self, sim_info, event, resolver):
        chef = self.owner.get_staff_member()
        if chef is None:
            return False
        return chef.sim_info is sim_info

    def timer_expired(self):
        self._on_interaction_of_interest_complete()

class _ChefBeginState(_ChefSituationStateBase):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._create_cooking_objects()
        super()._on_interaction_of_interest_complete()

    def _get_next_state(self):
        return self.owner._get_next_cooking_state()

class _ChefPanState(_ChefSituationStateBase):
    pass

class _ChefPotState(_ChefSituationStateBase):
    pass

class _ChefCuttingBoardState(_ChefSituationStateBase):
    pass

class _ChefServeState(_ChefSituationStateBase):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._create_serving()
        super()._on_interaction_of_interest_complete()
CHEF_GROUP = 'Chef'
class ChefSituation(BusinessEmployeeSituationMixin, StaffedObjectSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'begin_state': _ChefBeginState.TunableFactory(description='\n            The first state a chef starts in. This should route them to the\n            chef station and perform the generic swipe. When the interaction of\n            interest completes, the cooking objects will appear on the chef\n            station.\n            ', tuning_group=CHEF_GROUP), 'pan_state': _ChefPanState.TunableFactory(description="\n            The state the Chef is in when they're using the Pan portion of the\n            Chef Station. This should push the Pan SI as well as have the Pan\n            SI tuned as the Interaction of Interest.\n            ", tuning_group=CHEF_GROUP), 'pot_state': _ChefPotState.TunableFactory(description="\n            The state the Chef is in when they're using the Pot portion of the\n            Chef Station. This should push the Pot SI as well as have the Pot\n            SI tuned as the Interaction of Interest.\n            ", tuning_group=CHEF_GROUP), 'cutting_board_state': _ChefCuttingBoardState.TunableFactory(description="\n            The state the Chef is in when they're using the cutting board\n            portion of the Chef Station. This should push the Cutting Board SI\n            as well as have the Cutting Board SI tuned as the Interaction of\n            Interest.\n            ", tuning_group=CHEF_GROUP), 'serve_state': _ChefServeState.TunableFactory(description="\n            The state the Chef is in when they're serving food. This should\n            push the Serve SI as well as have the Serve SI tuned as the\n            Interaction of Interest.\n            ", tuning_group=CHEF_GROUP), 'active_cooking_states_before_delivery': TunableRange(description='\n            The number of situation states (cooking on the pot, pan, cutting\n            board) the Chef will perform between gaining an order and\n            delivering it.\n            \n            Note: this is a "best case scenario" number. If there are no serve\n            slots available, for example, the Chef will continue cook (keeping\n            the Has Order buff) until they are able to deliver the order to a\n            slot.\n            ', tunable_type=int, default=2, minimum=1), 'buff_to_active_cooking_states_count_delta_map': TunableMapping(description='\n            A mapping of buffs to a delta that will adjust how many active\n            cooking states it takes for an order to be completed.\n            ', key_name='Buff on Chef', key_type=Buff.TunableReference(description='\n                If the chef has this buff, the tuned delta will be applied to\n                the number of active cooking states the chef must go through to\n                complete an order.\n                '), value_name='Active Cooking States Before Delivery Delta', value_type=Tunable(description='\n                The amount by which to adjust the number of active cooking\n                states the chef must complete before completing the order. For\n                instance, if a -1 is tuned here, the chef will have to complete\n                one less state than normal. Regardless of how the buffs are\n                tuned, the chef will always run at least one state before\n                completing the order.\n                ', tunable_type=int, default=-1))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES
    TOO_MANY_ORDERS_WARNING = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._created_pot = None
        self._created_pan = None
        self._created_cutting_board = None
        self._has_order_state_count = 0
        self._direct_orders = []
        self._zone_director = get_restaurant_zone_director()
        self._current_order = None
        services.get_event_manager().register_single_event(self, TestEvent.OnSimReset)
        self._chef_reset_in_build_buy = False

    @classmethod
    def _states(cls):
        return [SituationStateData(0, _ChefBeginState, cls.begin_state), SituationStateData(1, _ChefPanState, cls.pan_state), SituationStateData(2, _ChefPotState, cls.pot_state), SituationStateData(3, _ChefCuttingBoardState, cls.cutting_board_state), SituationStateData(4, _ChefServeState, cls.serve_state)]

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.begin_state._tuned_values.job_and_role_changes.items())

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        restaurant_zone_director = get_restaurant_zone_director()
        if restaurant_zone_director is None:
            return
        chef_sim = self.get_staff_member()
        if chef_sim is None or chef_sim.sim_info is not sim_info:
            return
        if event == TestEvent.OnSimReset:
            if services.current_zone().is_in_build_buy:
                self._chef_reset_in_build_buy = True
            elif self.is_running:
                next_state = self.get_next_state()
                self._change_state(next_state())

    def check_reset_on_exit_build_buy(self):
        if self._chef_reset_in_build_buy:
            self._chef_reset_in_build_buy = False
            next_state = self.get_next_state()
            self._change_state(next_state())

    def start_situation(self):
        super().start_situation()
        self._change_state(self.begin_state())

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        chef_station = self.get_staffed_object()
        if chef_station is None:
            self._self_destruct()
            return
        if chef_station.has_component(types.STORED_SIM_INFO_COMPONENT):
            chef_station.remove_component(types.STORED_SIM_INFO_COMPONENT)
        chef_station.add_dynamic_component(types.STORED_SIM_INFO_COMPONENT, sim_id=sim.id)
        self._find_and_assign_cooking_objects()
        self._start_work_duration()

    def _get_role_state_affordance_override_kwargs(self):
        if isinstance(self._cur_state, _ChefPanState):
            return {'create_target_override': self._created_pan}
        if isinstance(self._cur_state, _ChefPotState):
            return {'create_target_override': self._created_pot}
        elif isinstance(self._cur_state, _ChefCuttingBoardState):
            return {'create_target_override': self._created_cutting_board}
        return {}

    def _self_destruct(self):
        services.get_event_manager().unregister_single_event(self, TestEvent.OnSimReset)
        self._destroy_cooking_objects()
        self._chef_remove_order()
        super()._self_destruct()

    def _chef_has_order(self):
        chef = self.get_staff_member()
        if chef is None:
            return False
        return chef.has_buff(ChefTuning.CHEF_HAS_ORDER_BUFF)

    def _try_chef_add_order(self):
        chef = self.get_staff_member()
        if chef is None:
            return
        if self._zone_director is not None:
            self._current_order = self._zone_director.get_group_order_with_status_for_chef(OrderStatus.ORDER_GIVEN_TO_CHEF, chef)
        if self._direct_orders:
            self._current_order = self._direct_orders.pop()
        if self._current_order is None and self._current_order is not None:
            chef.add_buff(ChefTuning.CHEF_HAS_ORDER_BUFF)

    def _chef_remove_order(self):
        self._current_order = None
        chef = self.get_staff_member()
        if chef is None:
            return
        has_order_buff = ChefTuning.CHEF_HAS_ORDER_BUFF
        if chef.has_buff(has_order_buff):
            chef.remove_buff_by_type(has_order_buff)

    def _get_next_cooking_state(self):
        chef = self.get_staff_member()
        if chef is None:
            self._self_destruct()
            return
        states = []
        if not self._chef_has_order():
            self._try_chef_add_order()
        if self._chef_has_order():
            if self._has_order_state_count == 0:
                return self.cutting_board_state
            states.append(self.cutting_board_state)
        states.extend((self.pan_state, self.pot_state))
        return random.choice(states)

    def _should_serve_order(self):
        if not self._chef_has_order():
            return False
        if self._current_order is None:
            return False
        if self._current_order.is_canceled:
            self._chef_remove_order()
            return False
        chef_buff_component = self.get_staff_member().sim_info.Buffs
        cooking_states_before_deliver = self.active_cooking_states_before_delivery
        for buff in chef_buff_component:
            buff_tuning = RestaurantTuning.COOKING_SPEED_DATA_MAPPING.get(buff.buff_type)
            if not buff_tuning:
                pass
            else:
                cooking_states_before_deliver += buff_tuning.active_cooking_states_delta
        if self._has_order_state_count >= max(1, cooking_states_before_deliver) and self._chef_station_has_available_serve_slot():
            self._has_order_state_count = 0
            return True
        self._has_order_state_count += 1
        return False

    def _chef_station_has_available_serve_slot(self):
        chef_station = self.get_staffed_object()
        for slot in chef_station.get_runtime_slots_gen(slot_types={ChefTuning.CHEF_STATION_SERVE_SLOT_TYPE}):
            if slot.is_valid_for_placement(definition=ChefTuning.CHEF_STATION_SERVING_PLATTER_OBJECT):
                return True
        return False

    def get_next_state(self):
        if self._should_serve_order():
            return self.serve_state
        return self._get_next_cooking_state()

    @classmethod
    def _create_and_slot_cooking_object(cls, chef_station, cooking_object, slot, find_existing=False):
        if find_existing:
            for slot_info in chef_station.get_runtime_slots_gen():
                if type(slot) is str and not slot_info.slot_name_hash == SlotComponent.to_slot_hash(slot):
                    pass
                else:
                    for child in slot_info.children:
                        if child.definition == cooking_object:
                            return child
        cooking_object_instance = system.create_object(cooking_object)
        if cooking_object_instance is None:
            logger.error('Failed to create a cooking object for the chef station. Please ensure the tuning in the restaurants.chef_tuning instance in Object Editor looks correct for the various cooking objects.')
            return
        else:
            slot_result = chef_station.slot_object(parent_slot=slot, slotting_object=cooking_object_instance)
            if not slot_result:
                logger.error('Failed to slot the cooking object ({}) on the chef station. Please ensure the slot is unobstructed and make sure the tuning in the restaurants.chef_tuning instance in Object Editor looks correct for the various slot names.')
                cooking_object_instance.destroy()
                return
        return cooking_object_instance

    def _create_cooking_objects(self):
        chef_station = self.get_staffed_object()
        if chef_station is None:
            chef = self.get_staff_member()
            logger.error('Trying to create the cooking objects for {}, chef {}, but the situation has no Chef Station.', self, chef)
            return
        self._created_pot = self._create_and_slot_cooking_object(chef_station, ChefTuning.CHEF_STATION_POT_OBJECT, ChefTuning.CHEF_STATION_POT_SLOT, find_existing=True)
        self._created_pan = self._create_and_slot_cooking_object(chef_station, ChefTuning.CHEF_STATION_PAN_OBJECT, ChefTuning.CHEF_STATION_PAN_SLOT, find_existing=True)
        self._created_cutting_board = self._create_and_slot_cooking_object(chef_station, ChefTuning.CHEF_STATION_CUTTING_BOARD_OBJECT, ChefTuning.CHEF_STATION_CUTTING_BOARD_SLOT, find_existing=True)

    def _find_cooking_object_on_slot(self, chef_station, parent_slot):
        slot_hash = sims4.hash_util.hash32(parent_slot)
        for child in chef_station.children:
            if slot_hash == child.location.slot_hash or child.location.joint_name_hash:
                return child

    def _find_and_assign_cooking_objects(self):
        chef_station = self.get_staffed_object()
        if chef_station is None:
            chef = self.get_staff_member()
            logger.error('Trying to find the cooking objects for {}, chef {}, but the situation has no Chef Station.', self, chef)
            return
        self._created_pot = self._find_cooking_object_on_slot(chef_station, ChefTuning.CHEF_STATION_POT_SLOT)
        self._created_pan = self._find_cooking_object_on_slot(chef_station, ChefTuning.CHEF_STATION_PAN_SLOT)
        self._created_cutting_board = self._find_cooking_object_on_slot(chef_station, ChefTuning.CHEF_STATION_CUTTING_BOARD_SLOT)

    def _destroy_cooking_objects(self):
        if self._created_pot is not None:
            self._created_pot.destroy()
            self._created_pot = None
        if self._created_pan is not None:
            self._created_pan.destroy()
            self._created_pan = None
        if self._created_cutting_board is not None:
            self._created_cutting_board.destroy()
            self._created_cutting_board = None

    def _create_serving(self):
        chef_station = self.get_staffed_object()
        if chef_station is None:
            logger.error('Trying to create the serving platter for the chef station but the situation has no Chef Station.')
            return
        if self._current_order is None:
            logger.error('Trying to create a meal for the chef to serve at the chef station but the situation has no current order.')
            return
        if isinstance(self._current_order, GroupOrder):
            if not self._current_order.is_canceled:
                serving_platter = self._create_and_slot_cooking_object(chef_station, ChefTuning.CHEF_STATION_SERVING_PLATTER_OBJECT, ChefTuning.CHEF_STATION_SERVE_SLOT_TYPE)
                self._current_order.assign_serving_from_chef(serving_platter)
                business_manager = services.business_service().get_business_manager_for_zone()
                if business_manager is not None:
                    business_manager.calculate_and_apply_expense_for_group_order(self._current_order)
                self._zone_director.set_order_status(self._current_order, OrderStatus.ORDER_READY)
            else:
                self._chef_remove_order()
        else:
            ordered_recipe = self._current_order.ordered_recipe
            ordered_recipe_definition = ordered_recipe.final_product_definition
            created_order = self._create_and_slot_cooking_object(chef_station, ordered_recipe_definition, ChefTuning.CHEF_STATION_SERVE_SLOT_TYPE)
            for initial_state in reversed(ordered_recipe.final_product.initial_states):
                created_order.set_state(initial_state.state, initial_state, from_init=True)
            for apply_state in reversed(ordered_recipe.final_product.apply_states):
                created_order.set_state(apply_state.state, apply_state, from_init=True)
            crafting_process = CraftingProcess(crafter=self.get_staff_member(), recipe=ordered_recipe)
            crafting_process.setup_crafted_object(created_order, is_final_product=True)
            self._push_sim_to_pick_up_order(self._current_order.ordering_sim, created_order)
            services.get_event_manager().process_event(test_events.TestEvent.RestaurantOrderDelivered, sim_info=self._current_order.ordering_sim.sim_info)
        self._chef_remove_order()

    def show_menu(self, sim):
        self._zone_director.show_menu(sim, chef_order=True)

    def add_direct_order(self, ordered_recipe, ordering_sim):
        self._direct_orders.append(DirectOrder(ordered_recipe, ordering_sim))
        tested_meal_cost_multiplier = restaurant_utils.tested_cost_multipliers_for_group((ordering_sim.id,))
        meal_cost = ordered_recipe.restaurant_base_price*tested_meal_cost_multiplier
        ordering_sim.household.funds.try_remove(meal_cost, reason=Consts_pb2.TELEMETRY_INTERACTION_COST, sim=ordering_sim)

    def _push_sim_to_pick_up_order(self, sim, order):
        context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
        sim.push_super_affordance(ChefTuning.PICK_UP_ORDER_INTERACTION, order, context)
