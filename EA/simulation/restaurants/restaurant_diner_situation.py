import itertoolsimport randomimport weakreffrom protocolbuffers import Business_pb2, DistributorOps_pb2from distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorfrom event_testing.resolver import SingleObjectResolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom filters.tunable import FilterTermTagfrom interactions.social.greeting_socials import greetingsfrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom restaurants import restaurant_utilsfrom restaurants.chefs_choice import ChefsChoicefrom restaurants.restaurant_order import OrderStatus, OrderRecommendationStatefrom restaurants.restaurant_tuning import RestaurantTuning, get_restaurant_zone_directorfrom sims4.tuning.tunable import TunableReference, TunableMapping, TunableEnumEntry, OptionalTunable, TunablePackSafeReference, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonSituationState, SituationStateData, CommonInteractionCompletedSituationState, SituationState, CommonInteractionStartedSituationState, TunableInteractionOfInterestfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_job import SituationJobimport enumimport filters.tunableimport servicesimport sims4.resourceslogger = sims4.log.Logger('DinerSitation', default_owner='rfleig')
class RestaurantDinerKeys:
    TEMP_MEAL_COST = 'temp_meal_cost'
    RUNNING_TOTAL = 'running_total'
    GUEST_IDS = 'guest_ids'
    CURRENT_STATE = 'current_state'

class DinerSubSituationState(enum.Int):
    ARRIVAL = 1
    CHECK_IN_WITH_HOST = 2
    WAIT_FOR_TABLE = 3
    PRE_PLACE_ORDER = 4
    ORDER_FROM_CHEF = 5
    POST_PLACE_ORDER = 6
    WAIT_FOR_FOOD_FROM_CHEF = 7
    WAIT_FOR_FOOD_FROM_WAITSTAFF = 8
    EAT_FOOD_STATE = 9
    PREPARE_TO_LEAVE = 10
    LEAVE = 11
    ORDER_PREROLL = 12
    WAIT_FOR_FOOD_PREROLL = 13
    EAT_PREROLL = 14

class _DinerReturnToCheckInStateMixin:
    FACTORY_TUNABLES = {'abandon_table_interaction': TunableInteractionOfInterest(description='\n            The interaction that a Sim can run to release/abandon a table which\n            will lead them to need to go back to the _CheckInWithHostState if\n            they are going to get shown to another table.\n            ')}

    def __init__(self, *args, abandon_table_interaction, **kwargs):
        super().__init__(*args, **kwargs)
        self._registered_for_interaction_complete = False
        self._abandon_table_interaction = abandon_table_interaction

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        if not self._registered_for_interaction_complete:
            for custom_key in self._abandon_table_interaction.custom_keys_gen():
                self._test_event_register(TestEvent.InteractionComplete, custom_key)
            self._registered_for_interaction_complete = True

    def handle_event(self, sim_info, event, resolver):
        func = getattr(super(), 'handle_event', None)
        if func:
            func(sim_info, event, resolver)
        if event == TestEvent.InteractionComplete and resolver(self._abandon_table_interaction) and self.owner.in_dining_party(sim_info):
            self.handle_return_to_check_in_state()
            return

    def handle_return_to_check_in_state(self):
        self.owner.advance_to_check_in_with_host_state()

def check_for_cancel_order(situation_state, sim_info, event, resolver):
    if event == TestEvent.InteractionExitedPipeline and (resolver(situation_state._cancel_order_interaction) and (resolver.interaction.user_canceled and situation_state.owner is not None)) and situation_state.owner.sim_of_interest(sim_info):
        situation_state.owner.cancel_order_for_group()
        situation_state.owner.background_situation.advance_entire_group_to_pre_place_order()
        return True
    return False

class _ArrivalState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner.advance_to_check_in_with_host_state()

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner is not None and self.owner.sim_of_interest(sim_info):
            return True
        return False

class _CheckInWithHostState(CommonInteractionCompletedSituationState):

    def on_activate(self, reader=None):
        if self.owner is not None and not self.owner.background_situation.host_working():
            self.owner.check_sim_in()
            return
        if self.owner is not None and self.owner.background_party_checked_in():
            self.owner.advance_to_wait_for_table_state()
            return
        super().on_activate(reader=reader)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._set_main_sim()
        zone_director = get_restaurant_zone_director()
        if zone_director is not None:
            zone_director.add_group_waiting_to_be_seated(self.owner.background_situation.id)
        self.owner.check_sim_in()

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner is not None and self.owner.sim_of_interest(sim_info):
            return True
        return False

class _WaitForTableState(CommonSituationState):

    def on_activate(self, reader=None):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            logger.warn('Trying to start the wait for table state of the restaurant diner situation on a non restaurant lot???')
            self.owner._self_destruct()
            return
        if self.owner is not None and self.owner.background_situation is not None:
            tables = zone_director.get_tables_by_group_id(self.owner.background_situation.id)
            if tables:
                self.owner.advance_to_pre_place_order_state()
                return
        super().on_activate(reader=reader)
        self._test_event_register(TestEvent.RestaurantTableClaimed)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.RestaurantTableClaimed and self.owner is not None and self.owner.sim_of_interest(sim_info):
            self.owner.advance_to_order_state()

class _PrePlaceOrderState(_DinerReturnToCheckInStateMixin, CommonSituationState):

    def on_activate(self, reader=None):
        zone_director = get_restaurant_zone_director()
        if zone_director is not None and self.owner is not None and self.owner.num_of_sims > 0:
            sim = next(self.owner.all_sims_in_situation_gen())
            group_order = zone_director.get_active_group_order_for_sim(sim.id)
            sim_order = group_order.get_sim_order(sim.id) if group_order is not None else None
            if sim_order is not None:
                self.owner.advance_to_post_place_order_state()
                return
        super().on_activate(reader=reader)
        self._test_event_register(TestEvent.RestaurantFoodOrdered)

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.RestaurantFoodOrdered and self.owner is not None and self.owner.sim_of_interest(sim_info):
            self.owner.notify_order_complete(sim_info)

class _PostPlaceOrderState(_DinerReturnToCheckInStateMixin, CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'cancel_order_interaction': TunableInteractionOfInterest(description='\n                 The interaction that when it is cancelled we want to cancel\n                 the order that has been placed.\n                 ')}

    def __init__(self, *args, cancel_order_interaction=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._cancel_order_interaction = cancel_order_interaction

    def on_activate(self, reader=None):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            self.owner.advance_to_wait_for_food_from_chef_state()
            return
        super().on_activate(reader=reader)
        for custom_key in self._cancel_order_interaction.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionExitedPipeline, custom_key)

    def handle_event(self, sim_info, event, resolver):
        if check_for_cancel_order(self, sim_info, event, resolver):
            return
        if event == TestEvent.InteractionExitedPipeline and resolver(self._interaction_of_interest):
            self._on_interaction_of_interest_complete()
        super().handle_event(sim_info, event, resolver)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner.advance_to_wait_for_food_from_waitstaff_state()

    def _additional_tests(self, sim_info, event, resolver):
        sim_infos = [sim.sim_info for sim in self.owner.background_situation.all_sims_in_situation_gen()]
        if sim_info in sim_infos:
            return True
        return False

class _OrderFromChefState(_DinerReturnToCheckInStateMixin, CommonSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        self._test_event_register(TestEvent.RestaurantFoodOrdered)

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.RestaurantFoodOrdered and self.owner.sim_of_interest(sim_info):
            self.owner.notify_order_complete(sim_info)

class _WaitForFoodFromChefState(_DinerReturnToCheckInStateMixin, CommonSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        self._test_event_register(TestEvent.RestaurantOrderDelivered)

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.RestaurantOrderDelivered and self.owner.sim_of_interest(sim_info):
            self.owner.start_eating()

class _WaitForFoodFromWaitStaffState(_DinerReturnToCheckInStateMixin, CommonSituationState):
    FACTORY_TUNABLES = {'cancel_order_interaction': TunableInteractionOfInterest(description='\n                 The interaction that when it is cancelled we want to cancel\n                 the order that has been placed.\n                 ')}

    def __init__(self, *args, cancel_order_interaction=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._cancel_order_interaction = cancel_order_interaction

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        self._test_event_register(TestEvent.RestaurantOrderDelivered)
        for custom_key in self._cancel_order_interaction.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionExitedPipeline, custom_key)

    def handle_event(self, sim_info, event, resolver):
        if check_for_cancel_order(self, sim_info, event, resolver):
            return
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.RestaurantOrderDelivered and self.owner.sim_of_interest(sim_info):
            self.owner.start_eating()

class _EatFoodState(_DinerReturnToCheckInStateMixin, CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'interaction_target_tests': TunableTestSet(description='\n            A set of tests that the target of the completed interaction must\n            pass in order for the interaction to be considered complete for\n            the purposes of this state.\n            \n            For example this should have a state test for Empty because a Sim\n            is not done eating until their plate is empty.\n            ')}

    def __init__(self, *args, interaction_target_tests, **kwargs):
        super().__init__(*args, **kwargs)
        self._interaction_target_tests = interaction_target_tests
        self._test_event_register(TestEvent.RestaurantFoodOrdered)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner.notify_meal_complete()

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner is None or not self.owner.sim_of_interest(sim_info):
            return False
        if resolver.interaction.target is None:
            return False
        else:
            resolver = SingleObjectResolver(resolver.interaction.target)
            if not self._interaction_target_tests.run_tests(resolver):
                return False
        return True

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.RestaurantFoodOrdered and self.owner.sim_of_interest(sim_info):
            if self.owner.background_situation.waitstaff_working:
                self.owner.advance_to_post_place_order_state()
            else:
                self.owner.advance_to_wait_for_food_from_chef_state()

class _PrepareToLeaveState(CommonInteractionCompletedSituationState):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._test_event_register(TestEvent.RestaurantFoodOrdered)

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.RestaurantFoodOrdered and self.owner.sim_of_interest(sim_info):
            if self.owner.background_situation.waitstaff_working:
                self.owner.advance_to_post_place_order_state()
            else:
                self.owner.advance_to_wait_for_food_from_chef_state()

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner.notify_guest_ready_to_leave()

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner is not None and self.owner.sim_of_interest(sim_info):
            return True
        return False

    def timer_expired(self):
        self.owner.notify_guest_ready_to_leave()

class _LeaveState(CommonInteractionCompletedSituationState):
    pass

class _OrderPrerollState(CommonInteractionStartedSituationState):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._test_event_register(TestEvent.RestaurantFoodOrdered)

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.RestaurantFoodOrdered and self.owner.sim_of_interest(sim_info):
            if self.owner.background_situation.waitstaff_working:
                self.owner.advance_to_post_place_order_state()
            else:
                self.owner.advance_to_wait_for_food_from_chef_state()

    def _on_interaction_of_interest_started(self):
        self.owner.advance_to_order_state()
        self.owner.advance_to_pre_place_order_state()

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner.sim_of_interest(sim_info):
            return True
        return False

class _WaitForFoodPrerollState(CommonInteractionStartedSituationState):

    def _on_interaction_of_interest_started(self):
        if self.owner.background_situation.waitstaff_working():
            self.owner.advance_to_wait_for_food_from_waitstaff_state()
        else:
            self.owner.advance_to_wait_for_food_from_chef_state()

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner.sim_of_interest(sim_info):
            return True
        return False

class _EatPrerollState(CommonInteractionStartedSituationState):

    def _on_interaction_of_interest_started(self):
        self.owner.start_eating()

    def _additional_tests(self, sim_info, event, resolver):
        if not self.owner.sim_of_interest(sim_info):
            return True
        return False

class RestaurantDinerSubSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'_arrival_state': _ArrivalState.TunableFactory(description='\n            The tuning for arrival state which will complete when the tuned\n            interaction is run.\n            ', tuning_group=GroupNames.STATE, display_name='01_arrival_state'), '_check_in_with_host_state': _CheckInWithHostState.TunableFactory(description='\n            The state tuning for when the Sims are checking in with the host\n            at the restaurant (if there is one) to get a table.\n            ', tuning_group=GroupNames.STATE, display_name='02_check_in_with_host_state'), '_wait_for_table_state': _WaitForTableState.TunableFactory(description='\n            The state tuning for when the Sims are waiting for a claimed table\n            to begin their dining experience.\n            ', tuning_group=GroupNames.STATE, display_name='03_wait_for_table_state'), '_pre_place_order_state': _PrePlaceOrderState.TunableFactory(description='\n            The state tuning for when the Sims are at their assigned table\n            waiting for the waiter to come take the groups order.\n            ', tuning_group=GroupNames.STATE, display_name='04_pre_place_order_state'), '_order_from_chef_state': _OrderFromChefState.TunableFactory(description='\n            The state tuning for when a Sim needs to order from the chef \n            directly instead of from a waiter/waitress.\n            ', tuning_group=GroupNames.STATE, display_name='05_order_from_chef_state'), '_post_place_order_state': _PostPlaceOrderState.TunableFactory(description='\n            The state tuning for when the Sims have already ordered their meal\n            and are waiting for the food to be delivered to the table by the\n            wait staff.\n            ', tuning_group=GroupNames.STATE, display_name='06_post_place_order_state'), '_wait_for_food_from_chef_state': _WaitForFoodFromChefState.TunableFactory(description='\n            The state tuning for when the Sims are waiting for their orders to\n            be delivered by the chef.\n            ', tuning_group=GroupNames.STATE, display_name='07_wait_for_food_from_chef_state'), '_wait_for_food_from_waitstaff_state': _WaitForFoodFromWaitStaffState.TunableFactory(description='\n            The state tuning for when the Sims are waiting for their orders to\n            be delivered by the waitstaff.\n            ', tuning_group=GroupNames.STATE, display_name='08_wait_for_food_from_waitstaff_state'), '_eat_food_state': _EatFoodState.TunableFactory(description='\n            The state tuning for when the Sims have received their food and are\n            now chowing down on their meals.\n            ', tuning_group=GroupNames.STATE, display_name='09_eat_food_state'), '_prepare_to_leave_state': _PrepareToLeaveState.TunableFactory(description='\n            The state tuning for when the Sims are finished eating but not quite\n            ready to leave yet.\n            ', tuning_group=GroupNames.STATE, display_name='10_prepare_to_leave_state'), '_leave_state': _LeaveState.TunableFactory(description='\n            The state tuning for when the Sims are done and about to leave the\n            restaurant. This is the last thing they will do before the situation\n            self destructs and the Sim is placed in the leave now situation which\n            will have the Sim actually exit the lot. You do not need to tune\n            behavior for them to leave the lot.\n            ', tuning_group=GroupNames.STATE, display_name='11_leave_state'), '_order_preroll_state': _OrderPrerollState.TunableFactory(description='\n            The state tuning for the state that will advance the Sims straight\n            to the order state during preroll. \n            \n            This state should limit the Sims autonomy so that all they can do\n            is get into a state that is appropriate for this state. For example\n            running an interaction that sits the sim in their assigned chair so\n            that when the curtain comes up you see the group sitting at the\n            table.\n            ', tuning_group=GroupNames.STATE, display_name='12_order_preroll_state'), '_wait_for_food_preroll_state': _WaitForFoodPrerollState.TunableFactory(description='\n            The state tuning for the state that will advance the Sims straight\n            to the wait for food state during preroll. \n            \n            This state should limit the Sims autonomy so that all they can do\n            is get into a state that is appropriate for this state. For example\n            running an interaction that sits the sim in their assigned chair so\n            that when the curtain comes up you see the group sitting at the\n            table.\n            ', tuning_group=GroupNames.STATE, display_name='13_wait_for_food_preroll_state'), '_eat_preroll_state': _WaitForFoodPrerollState.TunableFactory(description='\n            The state tuning for the state that will advance the Sims straight\n            to the eat state during preroll. \n            \n            This state should limit the Sims autonomy so that all they can do\n            is get into a state that is appropriate for this state. For example\n            running an interaction that sits the sim in their assigned chair so\n            that when the curtain comes up you see the group sitting at the\n            table.\n            ', tuning_group=GroupNames.STATE, display_name='14_eat_preroll_state'), 'situation_default_job': SituationJob.TunableReference(description='\n            The default job that a visitor will be in during the situation.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, seed, *args, **kwargs):
        super().__init__(seed, *args, **kwargs)
        self.background_situation = seed.extra_kwargs.get('background_situation', None)

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls._arrival_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def _states(cls):
        return [SituationStateData(DinerSubSituationState.ARRIVAL, _ArrivalState, factory=cls._arrival_state), SituationStateData(DinerSubSituationState.CHECK_IN_WITH_HOST, _CheckInWithHostState, factory=cls._check_in_with_host_state), SituationStateData(DinerSubSituationState.WAIT_FOR_TABLE, _WaitForTableState, factory=cls._wait_for_table_state), SituationStateData(DinerSubSituationState.PRE_PLACE_ORDER, _PrePlaceOrderState, factory=cls._pre_place_order_state), SituationStateData(DinerSubSituationState.ORDER_FROM_CHEF, _OrderFromChefState, factory=cls._order_from_chef_state), SituationStateData(DinerSubSituationState.POST_PLACE_ORDER, _PostPlaceOrderState, factory=cls._post_place_order_state), SituationStateData(DinerSubSituationState.WAIT_FOR_FOOD_FROM_CHEF, _WaitForFoodFromChefState, factory=cls._wait_for_food_from_chef_state), SituationStateData(DinerSubSituationState.WAIT_FOR_FOOD_FROM_WAITSTAFF, _WaitForFoodFromWaitStaffState, factory=cls._wait_for_food_from_waitstaff_state), SituationStateData(DinerSubSituationState.EAT_FOOD_STATE, _EatFoodState, factory=cls._eat_food_state), SituationStateData(DinerSubSituationState.PREPARE_TO_LEAVE, _PrepareToLeaveState, factory=cls._prepare_to_leave_state), SituationStateData(DinerSubSituationState.LEAVE, _LeaveState, factory=cls._leave_state), SituationStateData(DinerSubSituationState.ORDER_PREROLL, _OrderPrerollState, factory=cls._order_preroll_state), SituationStateData(DinerSubSituationState.WAIT_FOR_FOOD_PREROLL, _WaitForFoodPrerollState, factory=cls._wait_for_food_preroll_state), SituationStateData(DinerSubSituationState.EAT_PREROLL, _EatPrerollState, factory=cls._eat_preroll_state)]

    def start_situation(self):
        super().start_situation()
        if self._arrival_state is not None:
            self._change_state(self._arrival_state())

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._business_manager = services.business_service().get_business_manager_for_zone()
        if self._business_manager is not None:
            self._business_manager.add_customer(sim.sim_info)
        self._send_customer_update_message(sim.sim_info.sim_id)
        if type(self._cur_state) == _ArrivalState and not sim.is_npc:
            self.bypass_arrival_state()

    def sim_of_interest(self, sim_info):
        if sim_info in [sim.sim_info for sim in self.all_sims_in_situation_gen()]:
            return True
        return False

    def in_dining_party(self, sim_info):
        return self.background_situation.sim_of_interest(sim_info)

    def request_state_change(self, state_index):
        state_id = self._state_to_uid(self._cur_state)
        if state_id < state_index:
            self._change_state(self._states()[state_index - 1]._factory())

    def bypass_arrival_state(self):
        self.advance_to_wait_for_table_state()

    def check_sim_in(self):
        self.background_situation.check_all_guests_in()

    def advance_to_check_in_with_host_state(self):
        self._change_state(self._check_in_with_host_state())

    def advance_to_wait_for_table_state(self):
        self._change_state(self._wait_for_table_state())

    def advance_to_order_state(self):
        self.background_situation.advance_to_order_state()

    def advance_to_pre_place_order_state(self):
        self._change_state(self._pre_place_order_state())

    def notify_order_complete(self, sim_info):
        self.background_situation.guest_order_complete(sim_info)
        self.advance_to_post_place_order_state()

    def advance_to_post_place_order_state(self):
        self._change_state(self._post_place_order_state())

    def advance_to_wait_for_food_from_chef_state(self):
        self._change_state(self._wait_for_food_from_chef_state())

    def advance_to_wait_for_food_from_waitstaff_state(self):
        self._change_state(self._wait_for_food_from_waitstaff_state())

    def start_eating(self):
        self._change_state(self._eat_food_state())
        self.background_situation.order_delivered()

    def notify_meal_complete(self):
        for sim in self.all_sims_in_situation_gen():
            self.background_situation.guest_meal_complete(sim.sim_info)

    def notify_guest_ready_to_leave(self):
        for sim in tuple(self.all_sims_in_situation_gen()):
            sim_info = sim.sim_info
            self.background_situation.guest_ready_to_leave(sim_info)

    def cancel_order_for_group(self):
        zone_director = restaurant_utils.get_restaurant_zone_director()
        if zone_director is None:
            return
        zone_director.cancel_sims_group_order(next(self.all_sims_in_situation_gen()))
        self.background_situation.clear_temp_cost()

    def _set_main_sim(self):
        if self._situation_sims:
            self.background_situation.set_main_sim(next(self.all_sims_in_situation_gen()))
        else:
            logger.warn('Attempting to set the main sim on a dining background situation to a non existent sim in situation {}', self)

    def current_state_index(self):
        return self._state_to_uid(self._cur_state)

    def load_state(self, state_index):
        if state_index <= 0:
            logger.error("Trying to load a sub situation into a state index ({}) that doesn't exist. This is a GPE error.", state_index)
            return
        self._change_state(self._states()[state_index - 1]._factory())

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        self._send_customer_update_message(sim.sim_info.sim_id, from_add=False)

    def _send_customer_update_message(self, customer_sim_id, from_add=True):
        customer_msg = Business_pb2.BusinessCustomerUpdate()
        customer_msg.sim_id = customer_sim_id
        message_type = DistributorOps_pb2.Operation.BUSINESS_CUSTOMER_ADD if from_add else DistributorOps_pb2.Operation.BUSINESS_CUSTOMER_REMOVE
        op = GenericProtocolBufferOp(message_type, customer_msg)
        Distributor.instance().add_op_with_no_owner(op)

    def background_party_checked_in(self):
        return self.background_situation.party_checked_in()

class _DinerArrivalState(CommonSituationState):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._arrived_sim_infos = []

    def on_activate(self, reader=None):
        for situation in self.owner.sub_situations:
            situation.request_state_change(DinerSubSituationState.Arrival)

class _DinerOrderState(CommonSituationState):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ordered_sim_infos = []

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        for situation in self.owner.sub_situations:
            situation.request_state_change(DinerSubSituationState.PRE_PLACE_ORDER)

    def guest_ordered(self, sim_info):
        self._ordered_sim_infos.append(sim_info)
        sims_needing_to_order = [sim.sim_info for sim in self.owner.all_sims_in_situation_gen() if sim.sim_info not in self._ordered_sim_infos]
        if not sims_needing_to_order:
            self.owner.advance_to_eat_state()

class _DinerEatState(CommonSituationState):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._finished_eating_sim_infos = []

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)

    def guest_ate(self, sim_info):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            return
        if zone_director.get_active_group_order_for_sim(sim_info.sim_id) is not None:
            return
        self._finished_eating_sim_infos.append(sim_info)
        sims_needing_to_eat = [sim.sim_info for sim in self.owner.all_sims_in_situation_gen() if sim.sim_info not in self._finished_eating_sim_infos]
        if not sims_needing_to_eat:
            self._change_state(self.owner._diner_leave_state())

class _DinerLeaveState(CommonSituationState):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._leaving_sim_infos = []

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        for situation in self.owner.sub_situations:
            if situation is not None:
                situation.request_state_change(DinerSubSituationState.PREPARE_TO_LEAVE)

    def guest_ready_to_leave(self, sim_info):
        self.owner.leave()

class _DinerAdvanceToSeatedOrEating(SituationState):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim_count = 0

    def on_activate(self, reader=None):
        if reader is not None or services.current_zone().is_zone_running:
            self.owner._change_state(self.owner._diner_arrival_state())

    def sim_added(self):
        self._sim_count += 1
        if self._sim_count >= self.owner.num_invited_sims:
            zone_director = get_restaurant_zone_director()
            if zone_director is None:
                return
            tables = zone_director.get_tables_by_group_id(self.owner.id)
            if not tables:
                sims = [sim for sim in self.owner._situation_sims]
                zone_director.claim_table(sims[0])
                tables = zone_director.get_tables_by_group_id(self.owner.id)
                if not tables:
                    return
            self.owner.advance_for_preroll()

class RestaurantDinerBackGroundSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'_diner_arrival_state': OptionalTunable(description='\n            If enabled then this will place all sims in the arrival state to \n            begin with. If not then the arrival state will be skipped and\n            ', tunable=_DinerArrivalState.TunableFactory(description='\n                The state when a dining group first arrives the lot. They will wait\n                to be hosted, or claim a table directly. The state will transit to\n                order state when a table is claimed.\n                '), tuning_group=GroupNames.STATE), '_diner_order_state': _DinerOrderState.TunableFactory(description='\n            The state for the dining group to order food. They can either sit\n            at the table and order food from waiter, or wait in line to order\n            food. The state will switch to eat state when the table order is\n            delivered, or last sim in the group finished their order and get\n            the food from the chef station.\n            ', tuning_group=GroupNames.STATE), '_diner_eat_state': _DinerEatState.TunableFactory(description='\n            The state that all the dining group Sims are eating the food.\n            ', tuning_group=GroupNames.STATE), '_diner_leave_state': _DinerLeaveState.TunableFactory(description='\n            The state handles the pay bill process or they finished eating and\n            decides to leave.\n            ', tuning_group=GroupNames.STATE), 'blacklist_job': SituationJob.TunableReference(description='\n            The default job used for blacklisting Sims from coming back as\n            Diners right away.\n            '), 'group_filter': OptionalTunable(description='\n            If enabled allows the tuning of an Aggregate Group Filter for who\n            should be involved with this group. If disabled then no Sims will\n            be added to the group by default. This is probably only desirable \n            for user sims situations where the guest list is being created by\n            another process.\n            ', tunable=TunableReference(description='\n                The group filter for these Sims. This filter is what will\n                setup the Sims that need to spawn in. The value of the tags will\n                determine what sub situation the Sim will end up in.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=filters.tunable.TunableAggregateFilter), tuning_group=GroupNames.ROLES), 'situation_job_mapping': TunableMapping(description='\n            A mapping of filter term tag to situation job.\n            \n            The filter term tag is returned as part of the sim filters used to \n            create the guest list for this particular background situation.\n            \n            The situation job is the job that the Sim will be assigned to in\n            the background situation.\n            ', key_name='filter_tag', key_type=TunableEnumEntry(description='\n                The filter term tag returned with the filter results.\n                ', tunable_type=FilterTermTag, default=FilterTermTag.NO_TAG), value_name='job', value_type=TunableReference(description='\n                The job the Sim will receive when added to the background\n                situation.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB))), 'sub_situation_mapping': TunableMapping(description='\n            A mapping from Job to Sub Situation.\n            \n            The job is the job that the Sim is beign given in the background \n            situation.\n            \n            the sub situation is the individual sub situation that will be used\n            to control the behavior of the Sim in the background situation. The\n            background situation will request the different phases of the sub\n            situations to affect change in the Sims behavior.\n            ', key_name='job', key_type=TunableReference(description='\n                The job the Sim is being added to in the background situation.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), value_name='sub_situation', value_type=TunableReference(description='\n                The sub situation that will be created for the Sim when they\n                are given the job that is the corresponding key value.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), class_restrictions=(RestaurantDinerSubSituation,))), 'group_rel_bit': TunablePackSafeReference(description="\n            The short term relationship bit that get's added to all of the Sims in\n            a dining group to help encourage them to socialize with each other.\n            ", manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT)), 'allow_preroll': Tunable(description='\n            If set to True then this situation may advance past arrival on\n            preroll. If false then this situation must go through the normal\n            flow every time.\n            \n            This should mainly be used to keep user situations from prerolling.\n            ', tunable_type=bool, default=True)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._guest_sub_situation_dict = {}
        self._meal_cost = 0
        self._temp_cost = 0
        self._zone_director_data_cleaned = False
        self._main_sim_ref = None
        self._guest_current_state_save_data = {}
        self._completed_meal = False
        reader = self._seed.custom_init_params_reader
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None:
            business_manager.on_store_closed.register(self._on_store_closed)
        if reader is not None:
            self._meal_cost = reader.read_uint64(RestaurantDinerKeys.RUNNING_TOTAL, 0)
            self._temp_cost = reader.read_uint64(RestaurantDinerKeys.TEMP_MEAL_COST, 0)
            guest_ids = reader.read_uint64s(RestaurantDinerKeys.GUEST_IDS, None)
            current_states = reader.read_uint64s(RestaurantDinerKeys.CURRENT_STATE, None)
            if guest_ids is not None and current_states is not None:
                for (guest_id, state) in zip(guest_ids, current_states):
                    self._guest_current_state_save_data[guest_id] = state
            else:
                logger.error('Attempting to load bad data for {}. The sub situation state data is bad.', self)

    @classmethod
    def _states(cls):
        return [SituationStateData(1, _DinerArrivalState, factory=cls._diner_arrival_state), SituationStateData(2, _DinerOrderState, factory=cls._diner_order_state), SituationStateData(3, _DinerEatState, factory=cls._diner_eat_state), SituationStateData(4, _DinerLeaveState, factory=cls._diner_leave_state), SituationStateData(5, _DinerAdvanceToSeatedOrEating, factory=_DinerAdvanceToSeatedOrEating)]

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        if cls._diner_arrival_state is not None:
            return list(cls._diner_arrival_state._tuned_values.job_and_role_changes.items())
        return list(cls._diner_order_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def get_predefined_guest_list(cls):
        guest_list = SituationGuestList(invite_only=True)
        if cls.group_filter is None:
            return
        situation_manager = services.get_zone_situation_manager()
        worker_filter = cls.group_filter if cls.group_filter is not None else cls.default_job().filter
        instanced_sim_ids = [sim.sim_info.id for sim in services.sim_info_manager().instanced_sims_gen()]
        household_sim_ids = [sim_info.id for sim_info in services.active_household().sim_info_gen()]
        auto_fill_blacklist = situation_manager.get_auto_fill_blacklist(sim_job=cls.blacklist_job)
        situation_sims = set()
        for situation in situation_manager.get_situations_by_tags(cls.tags):
            situation_sims.update(situation.invited_sim_ids)
        blacklist_sim_ids = set(itertools.chain(situation_sims, instanced_sim_ids, household_sim_ids, auto_fill_blacklist))
        filter_results = services.sim_filter_service().submit_matching_filter(sim_filter=worker_filter, allow_yielding=False, blacklist_sim_ids=blacklist_sim_ids, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not filter_results:
            return guest_list
        for result in filter_results:
            job = cls.situation_job_mapping.get(result.tag, cls.default_job())
            guest_list.add_guest_info(SituationGuestInfo(result.sim_info.sim_id, job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_MEDIUM))
        return guest_list

    def start_situation(self):
        if self._seed._guest_list.guest_info_count == 0:
            self._self_destruct()
            return
        super().start_situation()
        reader = self._seed.custom_init_params_reader
        if self.allow_preroll and reader is None and not services.current_zone().is_zone_running:
            self._change_state(_DinerAdvanceToSeatedOrEating())
            return
        if self._diner_arrival_state is not None:
            self._change_state(self._diner_arrival_state())
        else:
            self._change_state(self._diner_order_state())

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        situation_manager = services.get_zone_situation_manager()
        current_dining_groups = situation_manager.get_situations_sim_is_in_by_tag(sim, RestaurantTuning.DINING_SITUATION_TAG)
        for situation in current_dining_groups:
            if situation is not self:
                situation._self_destruct()
        individual_situation = self.sub_situation_mapping.get(job_type, None)
        if individual_situation is None:
            logger.error('Failed to create a sub situation for {} in {}', sim, self)
            return
        guest_list = SituationGuestList(invite_only=True)
        guest_list.add_guest_info(SituationGuestInfo(sim.sim_id, individual_situation.situation_default_job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_MEDIUM))
        situation_id = situation_manager.create_situation(individual_situation, guest_list=guest_list, user_facing=False, background_situation=self)
        situation_manager.disable_save_to_situation_manager(situation_id)
        self._guest_sub_situation_dict[sim.id] = situation_id
        if sim.id in self._guest_current_state_save_data:
            situation = situation_manager.get(situation_id)
            situation.load_state(self._guest_current_state_save_data[sim.id])
        elif self.cur_state_is_correct_state_type(_DinerOrderState):
            situation = situation_manager.get(situation_id)
            situation.request_state_change(DinerSubSituationState.CHECK_IN_WITH_HOST)
        elif self.cur_state_is_correct_state_type(_DinerAdvanceToSeatedOrEating):
            self._cur_state.sim_added()
        for member in self._situation_sims:
            if not self.is_player_group():
                self.add_has_met_rel_bit(sim.sim_info, member.sim_info)
            greetings.add_greeted_rel_bit(sim.sim_info, member.sim_info)
            sim_rel_tracker = sim.sim_info.relationship_tracker
            if member is not sim and sim_rel_tracker is not None:
                sim_rel_tracker.add_relationship_bit(member.id, self.group_rel_bit)

    def add_has_met_rel_bit(self, a_sim_info, b_sim_info):
        a_sim_info.relationship_tracker.add_relationship_bit(b_sim_info.id, RelationshipGlobalTuning.HAS_MET_RELATIONSHIP_BIT)

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        self.cleanup_sub_situations(sim)
        zone_director = get_restaurant_zone_director()
        if zone_director is not None:
            zone_director.release_sims_seat(sim)
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None:
            business_manager.remove_customer(sim.sim_info, review_business=self._completed_meal)

    @property
    def sub_situations(self):
        sub_situations = set()
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None:
            return sub_situations
        for situation_id in self._guest_sub_situation_dict.values():
            situation = situation_manager.get(situation_id)
            if situation is not None:
                sub_situations.add(situation)
        return sub_situations

    def cur_state_is_correct_state_type(self, state_type):
        return isinstance(self._cur_state, state_type)

    def sim_of_interest(self, sim_info):
        if sim_info in [sim.sim_info for sim in self.all_sims_in_situation_gen()]:
            return True
        return False

    def is_player_group(self):
        for sim in self.all_sims_in_situation_gen():
            if not sim.is_npc:
                return True
        return False

    def advance_for_preroll(self):
        rand = random.randint(0, 1)
        if rand == 0:
            self.advance_preroll_to_preorder()
        elif not self.order_for_table(order_status=OrderStatus.ORDER_GIVEN_TO_CHEF):
            self.advance_preroll_to_preorder()
        else:
            self.advance_preroll_to_waitforfood()

    def advance_preroll_to_preorder(self):
        self._change_state(self._diner_order_state())
        for situation in self.sub_situations:
            situation.request_state_change(DinerSubSituationState.ORDER_PREROLL)

    def order_for_table(self, order_status=OrderStatus.MENU_READY, active_group_order=None, fire_event=False):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            return False
        chef_situation = restaurant_utils.get_chef_situation()
        if chef_situation is None:
            return False
        recipes = []
        for sim in self.all_sims_in_situation_gen():
            if active_group_order is not None:
                sim_order = active_group_order.get_sim_order(sim.sim_id)
                if sim_order is not None and sim_order.recommendation_state == OrderRecommendationState.RECOMMENDATION_PROPOSAL:
                    sim_order.recommendation_state = OrderRecommendationState.NO_RECOMMENDATION
                    zone_director.send_food_ordered_message_for_order(sim.sim_id)
                else:
                    (food_recipe, drink_recipe) = ChefsChoice.get_order_for_npc_sim(sim)
                    if food_recipe is not None:
                        recipes.append((sim, food_recipe))
                    if drink_recipe is not None:
                        recipes.append((sim, drink_recipe))
            else:
                (food_recipe, drink_recipe) = ChefsChoice.get_order_for_npc_sim(sim)
                if food_recipe is not None:
                    recipes.append((sim, food_recipe))
                if drink_recipe is not None:
                    recipes.append((sim, drink_recipe))
        if not recipes:
            if active_group_order is None:
                return False
            if active_group_order.is_ready_to_be_taken():
                zone_director.set_order_status(active_group_order, order_status)
                return True
        if self.waitstaff_working():
            zone_director.order_for_table([(sim.id, recipe.guid64) for (sim, recipe) in recipes], order_status=order_status, group_order=active_group_order)
        else:
            for (sim, order) in recipes:
                chef_situation.add_direct_order(order, sim)
        return True

    def order_course_for_group(self, course, complimentary=False):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            return False
        recipes = []
        for sim in self.all_sims_in_situation_gen():
            chosen_recipe = ChefsChoice.get_choice_for_npc_sim(sim, course)
            if chosen_recipe is not None:
                recipes.append((sim, chosen_recipe))
        if self.waitstaff_working():
            zone_director.order_for_table([(sim.id, recipe.guid64) for (sim, recipe) in recipes], complimentary=True)
        else:
            chef_situation = restaurant_utils.get_chef_situation()
            if chef_situation is None:
                return False
            for (sim, order) in recipes:
                chef_situation.add_direct_order(order, sim)
        return True

    def advance_preroll_to_waitforfood(self):
        self._change_state(self._diner_eat_state())
        for situation in self.sub_situations:
            situation.request_state_change(DinerSubSituationState.WAIT_FOR_FOOD_PREROLL)

    def waitstaff_working(self):
        zone_director = get_restaurant_zone_director()
        if zone_director is not None:
            return zone_director.waitstaff_working()
        return False

    def host_working(self):
        zone_director = get_restaurant_zone_director()
        if zone_director is not None:
            return zone_director.host_working()
        return False

    def check_all_guests_in(self):
        for sub_situation in self.sub_situations:
            sub_situation.advance_to_wait_for_table_state()

    def advance_to_order_state(self):
        self._change_state(self._diner_order_state())

    def guest_order_complete(self, sim_info):
        if self.cur_state_is_correct_state_type(_DinerOrderState):
            self._cur_state.guest_ordered(sim_info)

    def advance_to_eat_state(self):
        self._change_state(self._diner_eat_state())

    def guest_meal_complete(self, sim_info):
        if self.cur_state_is_correct_state_type(_DinerEatState):
            self._cur_state.guest_ate(sim_info)

    def advance_to_leave_state(self):
        self._change_state(self._diner_leave_state())

    def guest_ready_to_leave(self, sim_info):
        if self.cur_state_is_correct_state_type(_DinerLeaveState):
            self._cur_state.guest_ready_to_leave(sim_info)

    def advance_entire_group_to_pre_place_order(self):
        for situation in self.sub_situations:
            situation.advance_to_pre_place_order_state()

    def leave(self):
        zone_director = restaurant_utils.get_restaurant_zone_director()
        if zone_director is not None:
            zone_director.cancel_sims_group_order(next(self.all_sims_in_situation_gen()))
        self._completed_meal = True
        self.cleanup_sub_situations()
        self._self_destruct()

    def cleanup_sub_situations(self, sim=None):
        for situation in self.sub_situations:
            if situation and (sim is not None and sim not in situation.all_sims_in_situation_gen()) and situation.get_num_sims_in_job() > 0:
                pass
            elif situation is not None:
                situation._self_destruct()
        self.sub_situations.clear()

    def _destroy(self):
        self._clean_zone_director_data()
        self.cleanup_sub_situations()
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None and self._on_store_closed in business_manager.on_store_closed:
            business_manager.on_store_closed.unregister(self._on_store_closed)
        super()._destroy()

    def _self_destruct(self):
        self._clean_zone_director_data()
        super()._self_destruct()

    def _clean_zone_director_data(self):
        if self._zone_director_data_cleaned:
            return
        zone_director = get_restaurant_zone_director()
        if zone_director is not None:
            tables = zone_director.get_tables_by_sim_ids(self.invited_sim_ids)
            for table in tables:
                zone_director.release_table(release_table_id=table, from_situation_destroy=True)
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is not None:
            for sim in self.all_sims_in_situation_gen():
                situation_manager.add_sim_to_auto_fill_blacklist(sim.id, sim_job=self.blacklist_job)
        self._zone_director_data_cleaned = True

    def hold_ordered_cost(self, cost):
        self._temp_cost += cost

    def order_delivered(self):
        self._meal_cost += self._temp_cost
        self._temp_cost = 0
        if self.meal_cost != 0:
            self._check_modify_lot_owed_payment()

    def pay_for_group(self, payment):
        self._meal_cost -= payment
        if self._meal_cost == 0:
            self._check_modify_lot_owed_payment(add_payment=False)
        else:
            logger.error('{} have meal cost {} left after pay {}', self, self._meal_cost, payment, owner='cjiang')

    def _check_modify_lot_owed_payment(self, add_payment=True):
        household = services.active_household()
        player_sim_ids = (sim.sim_id for sim in self.all_sims_in_situation_gen() if not sim.is_npc)
        if not player_sim_ids:
            return
        zone_id = services.current_zone_id()
        if add_payment:
            household.bills_manager.add_lot_unpaid_bill(zone_id, self.id, self.meal_cost, player_sim_ids)
        else:
            household.bills_manager.remove_lot_unpaid_bill(zone_id, self.id)

    @property
    def meal_cost(self):
        return self._meal_cost

    @property
    def seated(self):
        if self.cur_state_is_correct_state_type(_DinerArrivalState):
            return False
        return True

    def set_main_sim(self, sim):
        self._main_sim_ref = weakref.ref(sim) if sim is not None else None

    def get_main_sim(self):
        if self._main_sim_ref is not None:
            return self._main_sim_ref()

    def clear_temp_cost(self):
        self._temp_cost = 0

    def _on_store_closed(self):
        zone_director = restaurant_utils.get_restaurant_zone_director()
        if zone_director is None:
            return
        order_canceled = False
        if not self.is_player_group():
            for sim in self.all_sims_in_situation_gen():
                if not order_canceled:
                    zone_director.cancel_sims_group_order(sim, refund_cost=True)
                    order_canceled = True
                services.get_zone_situation_manager().make_sim_leave_now_must_run(sim)
        self._self_destruct()

    def party_checked_in(self):
        if self.is_player_group():
            return False
        return not self.cur_state_is_correct_state_type(_DinerArrivalState)

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        writer.write_uint64(RestaurantDinerKeys.RUNNING_TOTAL, self._meal_cost)
        writer.write_uint64(RestaurantDinerKeys.TEMP_MEAL_COST, self._temp_cost)
        guest_ids = []
        current_states = []
        situation_manager = services.get_zone_situation_manager()
        for (guest_id, situation_id) in self._guest_sub_situation_dict.items():
            situation = situation_manager.get(situation_id)
            if situation is not None:
                guest_ids.append(guest_id)
                current_states.append(situation.current_state_index())
        writer.write_uint64s(RestaurantDinerKeys.GUEST_IDS, guest_ids)
        writer.write_uint64s(RestaurantDinerKeys.CURRENT_STATE, current_states)
