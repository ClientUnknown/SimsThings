from _collections import defaultdictfrom collections import namedtupleimport mathimport randomfrom business.business_employee_situation_mixin import BusinessEmployeeSituationMixinfrom event_testing.resolver import DoubleSimResolver, SingleSimResolverfrom event_testing.test_events import TestEventfrom interactions.interaction_cancel_compatibility import InteractionCancelCompatibility, InteractionCancelReasonfrom interactions.interaction_finisher import FinishingTypefrom restaurants.chef_tuning import ChefTuningfrom restaurants.restaurant_order import OrderStatusfrom restaurants.restaurant_tuning import RestaurantTuning, get_restaurant_zone_directorfrom sims4.tuning.tunable import TunableRangefrom situations.complex.staffed_object_situation_mixin import StaffedObjectSituationMixinfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonInteractionCompletedSituationState, SituationStateData, TunableInteractionOfInterestfrom situations.situation_job import SituationJobimport servicesimport sims4.loglogger = sims4.log.Logger('Waitstaff Situation', default_owner='trevor')ChefFeedbackInfo = namedtuple('ChefFeedbackInfo', ('from_sim', 'is_compliment'))
class _WaitstaffSituationStateBase(CommonInteractionCompletedSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        for custom_key in self._interaction_of_interest.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionExitedPipeline, custom_key)

    @property
    def resulting_order_status(self):
        pass

    @property
    def has_target_override(self):
        return False

    def _get_next_state(self):
        return self.owner.get_next_state()

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionExitedPipeline and resolver(self._interaction_of_interest):
            self._on_interaction_of_interest_complete()
        super().handle_event(sim_info, event, resolver)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._try_change_order_status(self.resulting_order_status)
        next_state = self._get_next_state()
        self._change_state(next_state())

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner is None:
            return False
        waitstaff = self.owner.get_staff_member()
        if waitstaff is None:
            return False
        return waitstaff.sim_info is sim_info

    def timer_expired(self):
        next_state = self._get_next_state()
        self._change_state(next_state())

class _WaitstaffIdleState(_WaitstaffSituationStateBase):
    pass

class _WaitstaffTakeOrderForTableState(_WaitstaffSituationStateBase):

    @property
    def resulting_order_status(self):
        return OrderStatus.ORDER_TAKEN

    def on_activate(self, reader=None):
        if self.owner._current_order is None:
            next_state = self._get_next_state()
            self._change_state(next_state())
            return
        super().on_activate(reader)

    @property
    def has_target_override(self):
        return True

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        sim_id = next(iter(self.owner._current_order.sim_ids))
        sim_info = services.sim_info_manager().get(sim_id)
        return (role_state_type, sim_info.get_sim_instance())

    def _get_next_state(self):
        if self.owner._current_order is not None:
            return self.owner.deliver_order_to_chef_state
        return self.owner.get_next_state()

class _WaitstaffDeliverOrderToChefState(_WaitstaffSituationStateBase):

    def __init__(self, *args, expedited=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._expedited = expedited

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if self._expedited:
            self.owner.expedite_current_order()

    @property
    def resulting_order_status(self):
        return OrderStatus.ORDER_GIVEN_TO_CHEF

    @property
    def has_target_override(self):
        return True

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        situation_manager = services.get_zone_situation_manager()
        chef_situations = situation_manager.get_situations_by_type(RestaurantTuning.CHEF_SITUATION)
        while chef_situations:
            assign_to_chef_situation = random.choice(chef_situations)
            chef_situations.remove(assign_to_chef_situation)
            chef = assign_to_chef_situation.get_staff_member()
            if chef is not None and self.owner._current_order is not None:
                self.owner._current_order.assign_chef(chef)
                return (role_state_type, assign_to_chef_situation.get_staffed_object())
        return (role_state_type, role_affordance_target)

class _WaitstaffDeliverOrderToTableState(_WaitstaffSituationStateBase):
    FACTORY_TUNABLES = {'must_exit_naturally_interactions': TunableInteractionOfInterest(description='\n                 The interaction(s) that will cause this state to be exited if\n                 they are removed from pipeline for any reason other than\n                 exiting naturally.\n                 '), 'resubmit_order_interactions': TunableInteractionOfInterest(description='\n                 The interaction(s) that will require the situation to go back\n                 to resubmit the order to the chef state.\n                 ')}

    def __init__(self, *args, must_exit_naturally_interactions=None, resubmit_order_interactions=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._must_exit_naturally_interactions = must_exit_naturally_interactions
        self._resubmit_order_interactions = resubmit_order_interactions

    @property
    def resulting_order_status(self):
        return OrderStatus.ORDER_DELIVERED

    @property
    def has_target_override(self):
        return True

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, self.owner._current_order.get_first_table())

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionExitedPipeline:
            if resolver(self._interaction_of_interest):
                if self.owner._current_order is not None:
                    self.owner._try_change_order_status(OrderStatus.ORDER_DELIVERY_FAILED)
                self.owner.advance_to_idle_state()
                return
            if resolver(self._resubmit_order_interactions):
                if self.owner._current_order is not None:
                    self.owner._try_change_order_status(OrderStatus.ORDER_TAKEN)
                    self._change_state(self.owner.deliver_order_to_chef_state(expedited=True))
                return
            if resolver(self._must_exit_naturally_interactions):
                if not resolver.interaction.is_finishing_naturally:
                    if self.owner._current_order is not None:
                        self.owner._try_change_order_status(OrderStatus.ORDER_DELIVERY_FAILED)
                    self.owner.advance_to_idle_state()
                return
        super().handle_event(sim_info, event, resolver)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._current_order.clear_serving_from_chef()
        super()._on_interaction_of_interest_complete()

    def on_activate(self, reader=None):
        order = self.owner._current_order
        skip_state = False
        if order is not None:
            if order.process_table_for_unfinished_food_drink():
                if self.owner._current_order.is_player_group_order():
                    waitstaff = self.owner.get_staff_member()
                    resolver = SingleSimResolver(waitstaff)
                    dialog = RestaurantTuning.FOOD_STILL_ON_TABLE_NOTIFICATION(waitstaff, resolver)
                    dialog.show_dialog()
                self.owner._current_order = None
                skip_state = True
        else:
            logger.error('Waitstaff {} entered the Deliver Order To Table state but has no current order.', self.owner.get_staff_member())
            skip_state = True
        if skip_state:
            next_state = self._get_next_state()
            self.owner._change_state(next_state())
        else:
            for custom_key in self._resubmit_order_interactions.custom_keys_gen():
                self._test_event_register(TestEvent.InteractionExitedPipeline, custom_key)
            for custom_key in self._must_exit_naturally_interactions.custom_keys_gen():
                self._test_event_register(TestEvent.InteractionExitedPipeline, custom_key)
            super().on_activate(reader)

class _WaitstaffGiveChefFeedbackState(_WaitstaffSituationStateBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._chef_sim = None

    def on_activate(self, reader=None):
        chef_feedback_dict = self.owner._chef_feedback
        if chef_feedback_dict:
            self._chef_sim = list(chef_feedback_dict.keys())[0]
        super().on_activate(reader)
        if not self._chef_sim:
            logger.error('Waitstaff {} entered the Give Chef Feedback state without any feedback to give', self.owner.get_staff_member())
            next_state = self._get_next_state()
            self._change_state(next_state())

    @property
    def has_target_override(self):
        return True

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, self._chef_sim)

    def _on_interaction_of_interest_complete(self, **kwargs):
        chef_feedback_infos = self.owner._chef_feedback.pop(self._chef_sim, None)
        for chef_feedback_info in chef_feedback_infos:
            double_sim_resolver = DoubleSimResolver(chef_feedback_info.from_sim, self._chef_sim)
            if chef_feedback_info.is_compliment:
                ChefTuning.CHEF_COMPLIMENT_LOOT.apply_to_resolver(double_sim_resolver)
            else:
                ChefTuning.CHEF_INSULT_LOOT.apply_to_resolver(double_sim_resolver)
        next_state = self._get_next_state()
        self._change_state(next_state())

class _WaitstaffCleanTablesState(_WaitstaffSituationStateBase):
    pass
WAITSTAFF_GROUP = 'Waitstaff'
class WaitstaffSituation(BusinessEmployeeSituationMixin, StaffedObjectSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'situation_job': SituationJob.TunableReference(description='\n            The job that a staff member will be in during the situation.\n            '), 'idle_state': _WaitstaffIdleState.TunableFactory(description='\n            The waitstaff route to the waitstation and idle.\n            ', tuning_group=WAITSTAFF_GROUP), 'take_order_for_table_state': _WaitstaffTakeOrderForTableState.TunableFactory(description='\n            The waitstaff rout to the appropriate table and take their order.\n            ', tuning_group=WAITSTAFF_GROUP), 'deliver_order_to_chef_state': _WaitstaffDeliverOrderToChefState.TunableFactory(description='\n            The waitstaff take the order to the chef station.\n            ', tuning_group=WAITSTAFF_GROUP), 'deliver_order_to_table_state': _WaitstaffDeliverOrderToTableState.TunableFactory(description='\n            The waitstaff pick the order up from the chef station and take it to the appropriate table.\n            ', tuning_group=WAITSTAFF_GROUP), 'give_chef_feedback_state': _WaitstaffGiveChefFeedbackState.TunableFactory(description='\n            If a patron has told the waitstaff to compliment/insult the chef,\n            they will be pushed into this state.\n            ', tuning_group=WAITSTAFF_GROUP), 'clean_tables_state': _WaitstaffCleanTablesState.TunableFactory(description="\n            One of the waitstaff's idles. If there is nothing else for them to\n            do, they can route to a dirty table and clean it off.\n            ", tuning_group=WAITSTAFF_GROUP), 'staff_table_count': TunableRange(description='\n            The number of tables that the waitstaff should serve.\n            ', tunable_type=int, default=2, minimum=1)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._chef_feedback = defaultdict(list)
        self._current_order = None
        self._zone_director = get_restaurant_zone_director()

    @classmethod
    def _states(cls):
        return [SituationStateData(0, _WaitstaffIdleState, cls.idle_state), SituationStateData(1, _WaitstaffTakeOrderForTableState, cls.take_order_for_table_state), SituationStateData(2, _WaitstaffDeliverOrderToChefState, cls.deliver_order_to_chef_state), SituationStateData(3, _WaitstaffDeliverOrderToTableState, cls.deliver_order_to_table_state), SituationStateData(4, _WaitstaffGiveChefFeedbackState, cls.give_chef_feedback_state), SituationStateData(5, _WaitstaffCleanTablesState, cls.clean_tables_state)]

    def _get_role_state_affordance_override_kwargs(self):
        if isinstance(self._cur_state, _WaitstaffDeliverOrderToTableState):
            return {'carry_target': self._current_order.serving_from_chef}
        return {}

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.idle_state._tuned_values.job_and_role_changes.items())

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        if self._cur_state is not None and self._cur_state.has_target_override:
            return self._cur_state._get_role_state_overrides(sim, job_type, role_state_type, role_affordance_target)
        return super()._get_role_state_overrides(sim, job_type, role_state_type, role_affordance_target)

    def start_situation(self):
        super().start_situation()
        self._change_state(self.idle_state())

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._start_work_duration()

    def advance_to_idle_state(self):
        self._change_state(self.idle_state())

    def get_next_state(self):
        staff_member = self.get_staff_member()
        if staff_member is None:
            return self.idle_state
        if self._current_order is not None:
            logger.error("Trying to get the next state for a waitstaff situation but current order isn't None. An order is about to be lost. current state:{}, order status:{}", self._cur_state, self._current_order._order_status)
        next_state = self._try_find_order_and_get_next_situation_state()
        if next_state is not None:
            return next_state
        if self._chef_feedback:
            return self.give_chef_feedback_state
        return self.idle_state

    def _try_find_order_and_get_next_situation_state(self):
        waitstaff = self.get_staff_member()
        if waitstaff is None:
            logger.warn("Trying to get the next state of a waitstaff situation that doesn't have a staff member. Returning Idle state as the next state until a staff member is assigned.")
            return self.idle_state
        for order in self._zone_director.get_all_group_orders_with_status(OrderStatus.ORDER_READY_DELAYED):
            order.process_table_for_unfinished_food_drink()
        while True:
            potential_order = self._zone_director.get_group_order_with_status_for_waitstaff(OrderStatus.ORDER_READY, waitstaff)
            if potential_order is None:
                break
            if potential_order.process_table_for_unfinished_food_drink():
                if potential_order.is_player_group_order():
                    waitstaff = self.get_staff_member()
                    resolver = SingleSimResolver(waitstaff)
                    dialog = RestaurantTuning.FOOD_STILL_ON_TABLE_NOTIFICATION(waitstaff, resolver)
                    dialog.show_dialog()
                    if self._zone_director.table_needs_cleaning(potential_order):
                        return self.clean_tables_state
                    self._current_order = potential_order
                    return self.deliver_order_to_table_state
            else:
                if self._zone_director.table_needs_cleaning(potential_order):
                    return self.clean_tables_state
                self._current_order = potential_order
                return self.deliver_order_to_table_state
        potential_order = self._zone_director.get_group_order_with_status(OrderStatus.MENU_READY)
        if potential_order:
            potential_order.assign_waitstaff(waitstaff)
            self._zone_director.set_order_status(potential_order, OrderStatus.ORDER_ASSIGNED_TO_WAITSTAFF)
            self._current_order = potential_order
            return self.take_order_for_table_state
        potential_order = self._zone_director.get_unclaimed_group_order_with_status(OrderStatus.ORDER_ASSIGNED_TO_WAITSTAFF)
        if potential_order:
            potential_order.assign_waitstaff(waitstaff)
            self._current_order = potential_order
            return self.take_order_for_table_state
        else:
            failed_order = self._zone_director.get_group_order_with_status(OrderStatus.ORDER_DELIVERY_FAILED)
            if failed_order and failed_order.assigned_waitstaff is waitstaff:
                self._zone_director.set_order_status(failed_order, OrderStatus.ORDER_READY)
                self._current_order = failed_order
                return self.deliver_order_to_table_state

    def give_chef_feedback(self, to_chef, from_sim, is_compliment):
        chef_feedback_info = ChefFeedbackInfo(from_sim, is_compliment)
        self._chef_feedback[to_chef].append(chef_feedback_info)

    def expedite_current_order(self):
        self._current_order.expedite = True

    def _try_change_order_status(self, order_status):
        if self._current_order is None or order_status is None:
            return
        self._zone_director.set_order_status(self._current_order, order_status)
        if order_status == OrderStatus.ORDER_GIVEN_TO_CHEF or order_status == OrderStatus.ORDER_DELIVERED or order_status == OrderStatus.ORDER_DELIVERY_FAILED:
            self._current_order = None

    def is_delivering_food(self, serving_platter):
        if not isinstance(self._cur_state, _WaitstaffDeliverOrderToTableState):
            return False
        elif self._current_order.serving_from_chef is serving_platter:
            return True
        return False

    def cancel_delivering_food(self):
        if not isinstance(self._cur_state, _WaitstaffDeliverOrderToTableState):
            return
        sim = self.get_staff_member()
        InteractionCancelCompatibility.cancel_interactions_for_reason(sim, InteractionCancelReason.WEDDING, FinishingType.SITUATIONS, 'Interaction was canceled due to the order being delivered getting canceled.')
        self._change_state(self.get_next_state()())

    @classmethod
    def situation_meets_starting_requirements(cls, **kwargs):
        if not super().situation_meets_starting_requirements(**kwargs):
            return False
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            return False
        else:
            waitstaff_needs = max(math.ceil(zone_director.get_table_count()/cls.staff_table_count), 1)
            situation_manager = services.get_zone_situation_manager()
            wait_situations = situation_manager.get_situations_by_type(cls)
            if len(wait_situations) < waitstaff_needs:
                return True
        return False
