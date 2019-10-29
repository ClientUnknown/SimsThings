import randomfrom business.business_situation_mixin import BusinessSituationMixinfrom distributor.ops import PurchaseIntentUpdatefrom event_testing.resolver import SingleSimResolverfrom event_testing.results import TestResult, EnqueueResultfrom event_testing.test_events import TestEventfrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom retail.retail_utils import RetailUtilsfrom role.role_state import RoleStatefrom sims4.tuning.geometric import TunableCurvefrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import OptionalTunable, TunableTuple, TunableInterval, TunableSimMinute, TunableReference, TunableRange, TunableVariantfrom sims4.utils import classpropertyfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationState, TunableInteractionOfInterest, SituationStateDatafrom situations.situation_job import SituationJobfrom statistics.statistic import Statisticfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport distributor.systemimport event_testingimport interactionsimport objects.object_testsimport servicesimport sims4.logimport situations.bouncerimport zone_testslogger = sims4.log.Logger('RetailSituation', default_owner='trevor')
class TunableCustomerSituationInitiationTestVariant(TunableVariant):

    def __init__(self, description='A single tunable test.', **kwargs):
        super().__init__(object_criteria=objects.object_tests.ObjectCriteriaTest.TunableFactory(locked_args={'tooltip': None}), zone=zone_tests.ZoneTest.TunableFactory(locked_args={'tooltip': None}), description=description, **kwargs)

class TunableCustomerSituationInitiationSet(event_testing.tests.TestListLoadingMixin):
    DEFAULT_LIST = event_testing.tests.TestList()

    def __init__(self, description=None):
        if description is None:
            description = 'A list of tests.  All tests must succeed to pass the TestSet.'
        super().__init__(description=description, tunable=TunableCustomerSituationInitiationTestVariant())

class RetailCustomerSituation(BusinessSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'customer_job': SituationJob.TunableReference(description='\n            The situation job for the customer.\n            '), 'role_state_go_to_store': RoleState.TunableReference(description='\n            The role state for getting the customer inside the store. This is\n            the default role state and will be run first before any other role\n            state can start.\n            '), 'role_state_browse': OptionalTunable(description='\n            If enabled, the customer will be able to browse items.\n            ', tunable=TunableTuple(role_state=RoleState.TunableReference(description='\n                    The role state for the customer browsing items.\n                    '), browse_time_min=TunableSimMinute(description='\n                    The minimum amount of time, in sim minutes, the customer\n                    will browse before moving on to the next state. When the\n                    customer begins browsing, a random time will be chosen\n                    between the min and max browse time.\n                    ', default=10), browse_time_max=TunableSimMinute(description='\n                    The maximum amount of time, in sim minutes, the customer\n                    will browse before moving on to the next state. When the\n                    customer begins browsing, a random time will be chosen\n                    between the min and max browse time.\n                    ', default=20), browse_time_extension_tunables=OptionalTunable(TunableTuple(description='\n                    A set of tunables related to browse time extensions.\n                    ', extension_perk=TunableReference(description='\n                        Reference to a perk that, if unlocked, will increase\n                        browse time by a set amount.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK)), time_extension=TunableSimMinute(description='\n                        The amount of time, in Sim minutes, that browse time\n                        will be increased by if the specified "extension_perk"\n                        is unlocked.\n                        ', default=30))))), 'role_state_buy': OptionalTunable(description='\n            If enabled, the customer will be able to buy items.\n            ', tunable=TunableTuple(role_state=RoleState.TunableReference(description='\n                    The role state for the customer buying items.\n                    '), price_range=TunableInterval(description='\n                    The minimum and maximum price of items this customer will\n                    buy.\n                    ', tunable_type=int, default_lower=1, default_upper=100, minimum=1))), 'role_state_loiter': RoleState.TunableReference(description='\n            The role state for the customer loitering. If Buy Role State and\n            Browse Role State are both disabled, the Sim will fall back to\n            loitering until Total Shop Time runs out.\n            '), 'go_to_store_interaction': TunableInteractionOfInterest(description='\n            The interaction that, when run by a customer, will switch the\n            situation state to start browsing, buying, or loitering.\n            '), 'total_shop_time_max': TunableSimMinute(description="\n            The maximum amount of time, in sim minutes, a customer will shop.\n            This time starts when they enter the store. At the end of this\n            time, they'll finish up whatever their current interaction is and\n            leave.\n            ", default=30), 'total_shop_time_min': TunableSimMinute(description="\n            The minimum amount of time, in sim minutes, a customer will shop.\n            This time starts when they enter the store. At the end of this\n            time, they'll finish up whatever their current interaction is and\n            leave.\n            ", default=1), 'buy_interaction': TunableInteractionOfInterest(description='\n            The interaction that, when run by a customer, buys an object.\n            '), 'initial_purchase_intent': TunableInterval(description="\n            The customer's purchase intent statistic is initialized to a random\n            value in this interval when they enter the store.\n            ", tunable_type=int, default_lower=0, default_upper=100), 'purchase_intent_extension_tunables': OptionalTunable(TunableTuple(description='\n            A set of tunables related to purchase intent extensions.\n            ', extension_perk=TunableReference(description='\n                Reference to a perk that, if unlocked, will increase purchase\n                intent by a set amount.\n                ', manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK)), purchase_intent_extension=TunableRange(description='\n                The amount to increase the base purchase intent statistic by if\n                the specified "extension_perk" is unlocked.\n                ', tunable_type=int, default=5, minimum=0, maximum=100))), 'purchase_intent_empty_notification': TunableUiDialogNotificationSnippet(description='\n            Notification shown by customer when purchase intent hits bottom and\n            the customer leaves.\n            '), 'nothing_in_price_range_notification': TunableUiDialogNotificationSnippet(description="\n            Notification shown by customers who are ready to buy but can't find\n            anything in their price range.\n            "), '_situation_start_tests': TunableCustomerSituationInitiationSet(description='\n            A set of tests that will be run when determining if this situation\n            can be chosen to start. \n            ')}
    CONTINUE_SHOPPING_THRESHOLD = TunableSimMinute(description="\n        If the customer has this much time or more left in their total shop\n        time, they'll start the browse/buy process over again after purchasing\n        something. If they don't have this much time remaining, they'll quit\n        shopping.\n        ", default=30)
    PRICE_RANGE = TunableTuple(description='\n        Statistics that are set to the min and max price range statistics.\n        These are automatically added to the customer in this situation and\n        will be updated accordingly.\n        \n        The stats should not be persisted -- the situation will readd them\n        on load.\n        ', min=Statistic.TunablePackSafeReference(), max=Statistic.TunablePackSafeReference())
    PURCHASE_INTENT_STATISTIC = Statistic.TunablePackSafeReference(description="\n        A statistic added to customers that track their intent to purchase\n        something. At the minimum value they will leave, and at max value they\n        will immediately try to buy something. Somewhere in between, there's a\n        chance for them to not buy something when they go to the buy state.\n        ")
    PURCHASE_INTENT_CHANCE_CURVE = TunableCurve(description='\n        A mapping of Purchase Intent Statistic value to the chance (0-1) that\n        the customer will buy something during the buy state.\n        ', x_axis_name='Purchase Intent', y_axis_name='Chance')
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def can_start_situation(cls, resolver):
        return cls._situation_start_tests.run_tests(resolver)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._customer = None
        self._showing_purchase_intent = False
        reader = self._seed.custom_init_params_reader
        if reader is None:
            self._saved_purchase_intent = None
        else:
            self._saved_purchase_intent = reader.read_int64('purchase_intent', None)
        self._min_price_range_multiplier = 1
        self._max_price_range_multiplier = 1
        self._total_shop_time_multiplier = 1
        self._purchase_intent_watcher_handle = None

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._customer is not None:
            purchase_intent = self._customer.get_stat_value(self.PURCHASE_INTENT_STATISTIC)
            writer.write_int64('purchase_intent', int(purchase_intent))

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _GoToStoreState), SituationStateData(2, _BrowseState), SituationStateData(3, _BuyState), SituationStateData(4, _LoiterState))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.customer_job, cls.role_state_go_to_store)]

    @classmethod
    def default_job(cls):
        return cls.customer_job

    def start_situation(self):
        super().start_situation()
        self._change_state(_GoToStoreState())

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return 1

    @classproperty
    def situation_serialization_option(cls):
        return situations.situation_types.SituationSerializationOption.LOT

    def validate_customer(self, sim_info):
        if self._customer is None:
            return False
        return self._customer.sim_info is sim_info

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._customer = sim
        self._update_price_range_statistics()
        self._initialize_purchase_intent()

    def _on_remove_sim_from_situation(self, sim):
        sim_job = self.get_current_job_for_sim(sim)
        super()._on_remove_sim_from_situation(sim)
        self._remove_purchase_intent()
        self._customer = None
        services.get_zone_situation_manager().add_sim_to_auto_fill_blacklist(sim.id, sim_job)
        self._self_destruct()

    def _situation_timed_out(self, *args, **kwargs):
        if not isinstance(self._cur_state, _BuyState):
            super()._situation_timed_out(*args, **kwargs)

    def adjust_browse_time(self, multiplier):
        if type(self._cur_state) is _BrowseState:
            self._cur_state.adjust_timeout(multiplier)

    def adjust_total_shop_time(self, multiplier):
        if multiplier == 0:
            self._self_destruct()
        elif type(self._cur_state) is _GoToStoreState:
            self._total_shop_time_multiplier *= multiplier
        else:
            remaining_minutes = self._get_remaining_time_in_minutes()
            remaining_minutes *= multiplier
            self.change_duration(remaining_minutes)

    def adjust_price_range(self, min_multiplier=1, max_multiplier=1):
        if self.role_state_buy is None:
            return
        self._min_price_range_multiplier *= min_multiplier
        self._max_price_range_multiplier *= max_multiplier
        self._update_price_range_statistics()

    def _update_price_range_statistics(self):
        (min_price, max_price) = self._get_min_max_price_range()
        if self.PRICE_RANGE.min is not None:
            min_stat = self._customer.get_statistic(self.PRICE_RANGE.min)
            min_stat.set_value(min_price)
        if self.PRICE_RANGE.max is not None:
            max_stat = self._customer.get_statistic(self.PRICE_RANGE.max)
            max_stat.set_value(max_price)

    def _get_min_max_price_range(self):
        price_range = self.role_state_buy.price_range
        return (max(0, price_range.lower_bound*self._min_price_range_multiplier), max(1, price_range.upper_bound*self._max_price_range_multiplier))

    def _initialize_purchase_intent(self):
        if self.role_state_buy is None:
            return
        if self._saved_purchase_intent is None:
            purchase_intent = random.randint(self.initial_purchase_intent.lower_bound, self.initial_purchase_intent.upper_bound)
            if self.purchase_intent_extension_tunables is not None:
                active_household = services.active_household()
                if active_household.bucks_tracker.is_perk_unlocked(self.purchase_intent_extension_tunables.extension_perk):
                    purchase_intent += self.purchase_intent_extension_tunables.purchase_intent_extension
            purchase_intent = sims4.math.clamp(self.PURCHASE_INTENT_STATISTIC.min_value + 1, purchase_intent, self.PURCHASE_INTENT_STATISTIC.max_value - 1)
        else:
            purchase_intent = self._saved_purchase_intent
        tracker = self._customer.get_tracker(self.PURCHASE_INTENT_STATISTIC)
        tracker.set_value(self.PURCHASE_INTENT_STATISTIC, purchase_intent, add=True)
        self._purchase_intent_watcher_handle = tracker.add_watcher(self._purchase_intent_watcher)
        if self._on_social_group_changed not in self._customer.on_social_group_changed:
            self._customer.on_social_group_changed.append(self._on_social_group_changed)

    def _remove_purchase_intent(self):
        if self._customer is not None:
            if self._purchase_intent_watcher_handle is not None:
                tracker = self._customer.get_tracker(self.PURCHASE_INTENT_STATISTIC)
                tracker.remove_watcher(self._purchase_intent_watcher_handle)
                self._purchase_intent_watcher_handle = None
                tracker.remove_statistic(self.PURCHASE_INTENT_STATISTIC)
            if self._on_social_group_changed in self._customer.on_social_group_changed:
                self._customer.on_social_group_changed.remove(self._on_social_group_changed)
            self._set_purchase_intent_visibility(False)

    def _on_social_group_changed(self, sim, group):
        if self._customer in group:
            if self._on_social_group_members_changed not in group.on_group_changed:
                group.on_group_changed.append(self._on_social_group_members_changed)
        elif self._on_social_group_members_changed in group.on_group_changed:
            group.on_group_changed.remove(self._on_social_group_members_changed)

    def _on_social_group_members_changed(self, group):
        if self._customer is not None:
            employee_still_in_group = False
            business_manager = services.business_service().get_business_manager_for_zone()
            if self._customer in group:
                for sim in group:
                    if not business_manager.is_household_owner(sim.household_id):
                        if business_manager.is_employee(sim.sim_info):
                            employee_still_in_group = True
                            break
                    employee_still_in_group = True
                    break
            if employee_still_in_group:
                self._set_purchase_intent_visibility(True)
            else:
                self._set_purchase_intent_visibility(False)

    def on_sim_reset(self, sim):
        super().on_sim_reset(sim)
        if isinstance(self._cur_state, _BuyState) and self._customer is sim:
            new_buy_state = _BuyState()
            new_buy_state.object_id = self._cur_state.object_id
            self._change_state(new_buy_state)

    def _set_purchase_intent_visibility(self, toggle):
        if self._showing_purchase_intent is not toggle and toggle and isinstance(self._cur_state, _BrowseState):
            self._showing_purchase_intent = toggle
            stat = self._customer.get_statistic(self.PURCHASE_INTENT_STATISTIC, add=False)
            if stat is not None:
                value = stat.get_value()
                self._send_purchase_intent_message(stat.stat_type, value, value, toggle)

    def _purchase_intent_watcher(self, stat_type, old_value, new_value):
        if stat_type is not self.PURCHASE_INTENT_STATISTIC:
            return
        self._send_purchase_intent_message(stat_type, old_value, new_value, self._showing_purchase_intent)
        if new_value == self.PURCHASE_INTENT_STATISTIC.max_value:
            self._on_purchase_intent_max()
        elif new_value == self.PURCHASE_INTENT_STATISTIC.min_value:
            self._on_purchase_intent_min()

    def _send_purchase_intent_message(self, stat_type, old_value, new_value, toggle):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None and business_manager.is_owner_household_active:
            op = PurchaseIntentUpdate(self._customer.sim_id, stat_type.convert_to_normalized_value(old_value), stat_type.convert_to_normalized_value(new_value), toggle)
            distributor.system.Distributor.instance().add_op(self._customer, op)

    def _on_purchase_intent_max(self):
        if isinstance(self._cur_state, _BuyState):
            return
        if isinstance(self._cur_state, _GoToStoreState):
            self._set_shop_duration()
        self._change_state(_BuyState())

    def _on_purchase_intent_min(self):
        resolver = SingleSimResolver(self._customer)
        dialog = self.purchase_intent_empty_notification(self._customer, resolver)
        dialog.show_dialog()
        self._self_destruct()

    def _choose_starting_state(self):
        if self.role_state_browse is not None:
            return _BrowseState()
        if self.role_state_buy is not None:
            return _BuyState()
        return _LoiterState()

    def _choose_post_browse_state(self):
        if self._customer is None:
            return
        if self.role_state_buy is not None:
            stat = self._customer.get_statistic(self.PURCHASE_INTENT_STATISTIC, add=False)
            if stat is not None:
                value = stat.get_value()
                chance = self.PURCHASE_INTENT_CHANCE_CURVE.get(value)
                if random.random() > chance:
                    return _BrowseState()
            self._set_purchase_intent_visibility(False)
            return _BuyState()
        return _LoiterState()

    def _choose_post_buy_state(self):
        minutes_remaining = self._get_remaining_time_in_minutes()
        if minutes_remaining < self.CONTINUE_SHOPPING_THRESHOLD:
            return
        if self.role_state_browse is not None:
            return _BrowseState()
        return _LoiterState()

    def _set_shop_duration(self):
        shop_time = random.randint(self.total_shop_time_min, self.total_shop_time_max)
        shop_time *= self._total_shop_time_multiplier
        self.change_duration(shop_time)
lock_instance_tunables(RetailCustomerSituation, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.NORMAL, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE, duration=0)
class _GoToStoreState(SituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        for custom_key in self.owner.go_to_store_interaction.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)
        self.owner._set_job_role_state(self.owner.customer_job, self.owner.role_state_go_to_store)

    def handle_event(self, sim_info, event, resolver):
        if not self.owner.validate_customer(sim_info):
            return
        if resolver(self.owner.go_to_store_interaction):
            self.owner._set_shop_duration()
            self._change_state(self.owner._choose_starting_state())

class _BrowseState(SituationState):
    BROWSE_STATE_TIMEOUT = 'browse_timeout'

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.customer_job, self.owner.role_state_browse.role_state)
        browse_time = random.randint(self.owner.role_state_browse.browse_time_min, self.owner.role_state_browse.browse_time_max)
        browse_time_extension_tunables = self.owner.role_state_browse.browse_time_extension_tunables
        if browse_time_extension_tunables is not None:
            active_household = services.active_household()
            if active_household.bucks_tracker.is_perk_unlocked(browse_time_extension_tunables.extension_perk):
                browse_time += browse_time_extension_tunables.time_extension
        self._create_or_load_alarm(_BrowseState.BROWSE_STATE_TIMEOUT, browse_time, lambda _: self._timer_expired(), should_persist=True, reader=reader)

    def _timer_expired(self):
        new_state = self.owner._choose_post_browse_state()
        if new_state is None:
            self.owner._self_destruct()
        else:
            self._change_state(new_state)

    def adjust_timeout(self, multiplier):
        if multiplier == 0:
            self._cancel_alarm(_BrowseState.BROWSE_STATE_TIMEOUT)
            new_state = self.owner._choose_post_browse_state()
            if new_state is None:
                self.owner._self_destruct()
            else:
                self._change_state(new_state)
        else:
            minutes_remaining = self._get_remaining_alarm_time(_BrowseState.BROWSE_STATE_TIMEOUT).in_minutes()
            minutes_remaining *= multiplier
            self._cancel_alarm(_BrowseState.BROWSE_STATE_TIMEOUT)
            self._create_or_load_alarm(_BrowseState.BROWSE_STATE_TIMEOUT, minutes_remaining, lambda _: self._timer_expired(), should_persist=True)

class _BuyState(SituationState):
    OBJECT_ID_KEY = 'id'
    MAX_BUY_OBJECT_TESTS = 50
    BUY_STATE_VERIFICATION = 'buy_verification'
    BUY_STATE_VERIFICATION_TIME = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object_id = None
        self.alarm_handle = None

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.customer_job, self.owner.role_state_buy.role_state)
        customer_sim = self.owner._customer
        if customer_sim is None:
            logger.warn('No customer Sim on retail customer situation. Cannot complete _BuyState')
            self._advance_state()
            return
        if reader is not None:
            self.object_id = reader.read_uint64(self.OBJECT_ID_KEY, None)
        result = False
        if self.object_id is not None:
            object_to_buy = services.current_zone().find_object(self.object_id)
            if self._is_object_valid_to_buy(object_to_buy):
                (object_to_buy, result) = self._test_execute_buy_affordance(object_to_buy)
        else:
            object_to_buy = None
        if not (object_to_buy is None or result):
            (object_to_buy, result) = self._try_find_object_and_push_buy_affordance()
        if object_to_buy is None or not result:
            self.owner._self_destruct()
        else:
            self._create_or_load_alarm(_BuyState.BUY_STATE_VERIFICATION, _BuyState.BUY_STATE_VERIFICATION_TIME, lambda _: self._verify_buy_state_interactions(), should_persist=False, reader=reader)

    def _is_object_valid_to_buy(self, obj):
        if obj is None:
            return False
        customer = self.owner._customer
        if obj.in_use and not obj.in_use_by(customer):
            return False
        return obj.is_connected(customer)

    def handle_event(self, sim_info, event, resolver):
        if not self.owner.validate_customer(sim_info):
            return
        if resolver(self.owner.buy_interaction):
            self.owner._remove_purchase_intent()
            self.owner._initialize_purchase_intent()
            self._advance_state()

    def save_state(self, writer):
        super().save_state(writer)
        if self.object_id is not None:
            writer.write_uint64(self.OBJECT_ID_KEY, self.object_id)

    def _advance_state(self):
        next_state = self.owner._choose_post_buy_state()
        if next_state is None:
            self.owner._self_destruct()
        else:
            self.owner._change_state(next_state)

    def _test_execute_buy_affordance(self, object_to_buy):
        retail_component = object_to_buy.retail_component
        if retail_component is None:
            return (object_to_buy, TestResult(False, '{} missing retail component'))
        buy_affordance = retail_component.get_buy_affordance()
        if buy_affordance is None:
            return (object_to_buy, TestResult(False, '{} missing buy affordance'))
        context = InteractionContext(self.owner._customer, InteractionContext.SOURCE_SCRIPT, Priority.High, client=services.client_manager().get_first_client())
        buy_aop = interactions.aop.AffordanceObjectPair(buy_affordance, object_to_buy, buy_affordance, None)
        test_result = buy_aop.test(context)
        execute_result = None
        if test_result:
            execute_result = buy_aop.execute(context)
            if execute_result:
                for custom_key in self.owner.buy_interaction.custom_keys_gen():
                    self._test_event_register(TestEvent.InteractionComplete, custom_key)
                self.object_id = object_to_buy.id
        return (object_to_buy, EnqueueResult(test_result, execute_result))

    def _try_find_object_and_push_buy_affordance(self):
        (min_price, max_price) = self.owner._get_min_max_price_range()
        found_object = None
        objects_in_price_range = []
        other_potential_objects = []
        for found_object in RetailUtils.all_retail_objects_gen(allow_sold=False):
            if found_object.in_use and not found_object.in_use_by(self.owner._customer):
                pass
            else:
                sell_price = found_object.retail_component.get_sell_price()
                if min_price <= sell_price and sell_price <= max_price:
                    objects_in_price_range.append(found_object)
                else:
                    other_potential_objects.append(found_object)
        random.shuffle(objects_in_price_range)
        for price_range_object in objects_in_price_range:
            (_, result) = self._test_execute_buy_affordance(price_range_object)
            if result:
                return (price_range_object, result)
        random.shuffle(other_potential_objects)
        num_objects_tested = 0
        for potential_object in other_potential_objects:
            if num_objects_tested >= _BuyState.MAX_BUY_OBJECT_TESTS:
                logger.warn('Retail Customer {} hit MAX_BUY_OBJECT_TESTS when looking for an object to buy.', owner='rmccord')
                return (None, False)
            (_, result) = self._test_execute_buy_affordance(potential_object)
            if result:
                return (potential_object, result)
            num_objects_tested += 1
        return (None, False)

    def _verify_buy_state_interactions(self):
        object_to_buy = None
        should_restart = False
        if self.object_id is not None:
            current_zone = services.current_zone()
            object_to_buy = current_zone.find_object(self.object_id)
            if not (object_to_buy is None or any(interaction.sim is self.owner._customer for interaction in list(object_to_buy.interaction_refs))):
                should_restart = True
        if should_restart:
            new_buy_state = _BuyState()
            new_buy_state.object_id = self.object_id
            self._change_state(new_buy_state)
        else:
            self._create_or_load_alarm(_BuyState.BUY_STATE_VERIFICATION, _BuyState.BUY_STATE_VERIFICATION_TIME, lambda _: self._verify_buy_state_interactions(), should_persist=False)

class _LoiterState(SituationState):

    def __init__(self):
        super().__init__()

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.customer_job, self.owner.role_state_loiter)
