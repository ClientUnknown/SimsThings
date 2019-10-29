from protocolbuffers import Consts_pb2from audio.primitive import TunablePlayAudio, play_tunable_audiofrom clock import interval_in_sim_weeksfrom date_and_time import TimeSpan, create_date_and_time, DateAndTimefrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import IconInfoDatafrom event_testing.resolver import SingleSimResolver, GlobalResolverfrom event_testing.tests import TunableTestSetfrom sims.funds import get_funds_for_source, FundsSourcefrom sims.household_utilities.utility_types import Utilities, UtilityShutoffReasonPriorityfrom sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuning, TunableLocalizedStringfrom sims4.tuning.dynamic_enum import DynamicEnum, DynamicEnumLockedfrom sims4.tuning.tunable import Tunable, TunableList, TunableTuple, TunablePercent, TunableInterval, TunableMapping, TunableReference, TunableEnumEntryfrom singletons import DEFAULTfrom tunable_multiplier import TunableMultiplierfrom tunable_time import Days, TunableTimeOfWeekfrom ui.ui_dialog_notification import UiDialogNotification, TunableUiDialogNotificationSnippetimport alarmsimport build_buyimport clockimport servicesimport sims4.loglogger = sims4.log.Logger('Bills', default_owner='rmccord')
class BillReductionEnum(DynamicEnumLocked):
    GlobalPolicy_ControlInvasiveSpecies = 0
    GlobalPolicy_ControlOverfishing = 1
    GlobalPolicy_CoconutRebate = 2
    GlobalPolicy_SupportOrganicProduce = 3
    GlobalPolicy_ExperimentalPollutionCleaner = 4
    GlobalPolicy_LitteringFines = 5

class Bills:
    BILL_ARRIVAL_NOTIFICATION = TunableList(description='\n        A list of notifications that show up if bills are delivered. We run\n        through the notifications and tests in order to see which one passes\n        first.\n        ', tunable=TunableTuple(description='\n            Tests and Notification for when bills are delivered. We run the\n            tests first before popping the notification.\n            ', notification=UiDialogNotification.TunableFactory(description='\n                A notification which pops up when bills are delivered.\n                '), tests=TunableTestSet(description='\n                Tests to determine if we should show this notification.\n                ')))
    REDUCTION_REASON_TEXT_MAP = TunableMapping(description='\n        A mapping of reduction reason to text that will appear as a bullet\n        in a bulleted list in the bill arrival notification.\n        ', key_type=TunableEnumEntry(description='\n            Reason for bill reduction.\n            ', tunable_type=BillReductionEnum, default=BillReductionEnum.GlobalPolicy_ControlInvasiveSpecies), value_type=TunableLocalizedStringFactory(description='\n            A string representing the line item on the notification\n            explaining why Sims are getting a bill reduction.\n            \n            This string is provided one token: the percentage discount\n            obtained due to the reason.\n            \n            e.g.:\n             {0.Number}% off for enacting the Green Energy Policy.\n            '))
    UTILITY_INFO = TunableMapping(key_type=Utilities, value_type=TunableList(description='\n            A list of notifications and tooltips that show up if a utility will\n            soon become delinquent or is shut off. We run through the tests in\n            order to decide which set of notifications and tooltips to show.\n            ', tunable=TunableTuple(description='\n                Notifications and tooltips related to shutting off utilities,\n                accompanied by tests which must pass before we show the\n                notification or tooltip.\n                ', warning_notification=UiDialogNotification.TunableFactory(description='\n                    A notification which appears when the player will be losing this\n                    utility soon due to delinquency.\n                    '), shutoff_notification=UiDialogNotification.TunableFactory(description='\n                    A notification which appears when the player loses this utility\n                    due to delinquency.\n                    '), shutoff_tooltip=TunableLocalizedStringFactory(description='\n                    A tooltip to show when an interaction cannot be run due to this\n                    utility being shutoff.\n                    '), tests=TunableTestSet(description='\n                    Test set which determines if we show the notification and\n                    tooltip or not.\n                    '))))
    BILL_COST_MODIFIERS_SIM = TunableMultiplier.TunableFactory(description='\n        A tunable list of test sets and associated multipliers to apply to the\n        total bill cost per payment on a per Sim basis.\n        ')
    BILL_COST_MODIFIERS_HOUSEHOLD = TunableMultiplier.TunableFactory(description='\n        A tunable list of test sets and associated multipliers to apply to the\n        total bill cost per payment on a per household basis.\n        ')
    BILL_OBJECT = TunableReference(description="\n        The object that will be delivered to the lot's mailbox once bills have\n        been scheduled.\n        ", manager=services.definition_manager())
    DELINQUENCY_FREQUENCY = Tunable(description='\n        Tunable representing the number of Sim hours between utility shut offs.\n        ', tunable_type=int, default=24)
    DELINQUENCY_WARNING_OFFSET_TIME = Tunable(description='\n        Tunable representing the number of Sim hours before a delinquency state\n        kicks in that a warning notification pops up.\n        ', tunable_type=int, default=2)
    BILL_BRACKETS = TunableList(description="\n        A list of brackets that determine the percentages that each portion of\n        a household's value is taxed at.\n        \n        ex: The first $2000 of a household's value is taxed at 10%, and\n        everything after that is taxed at 15%.\n        ", tunable=TunableTuple(description='\n            A value range and tax percentage that define a bill bracket.\n            ', value_range=TunableInterval(description="\n                A tunable range of integers that specifies a portion of a\n                household's total value.\n                ", tunable_type=int, default_lower=0, default_upper=None), tax_percentage=TunablePercent(description="\n                A tunable percentage value that defines what percent of a\n                household's value within this value_range the player is billed\n                for.\n                ", default=10)))
    TIME_TO_PLACE_BILL_IN_HIDDEN_INVENTORY = TunableTimeOfWeek(description="\n        The time of the week that we will attempt to place a bill in this\n        household's hidden inventory so it can be delivered.  This time should\n        be before the mailman shows up for that day or the bill will not be\n        delivered until the following day.\n        ", default_day=Days.MONDAY, default_hour=8, default_minute=0)
    AUDIO = TunableTuple(description='\n        Tuning for all the audio stings that will play as a part of bills.\n        ', delinquency_warning_sfx=TunablePlayAudio(description='\n            The sound to play when a delinquency warning is displayed.\n            '), delinquency_activation_sfx=TunablePlayAudio(description='\n            The sound to play when delinquency is activated.\n            '), delinquency_removed_sfx=TunablePlayAudio(description='\n            The sound to play when delinquency is removed.\n            '), bills_paid_sfx=TunablePlayAudio(description='\n            The sound to play when bills are paid.  If there are any delinquent\n            utilities, the delinquency_removed_sfx will play in place of this.\n            '))
    BILLS_UTILITY_SHUTOFF_REASON = TunableEnumEntry(description='\n        The utility shutoff reason for bills. This determines how important the\n        bills tooltip is when we shutoff the utility for delinquent bills\n        relative to other shutoff reasons.\n        ', tunable_type=UtilityShutoffReasonPriority, default=UtilityShutoffReasonPriority.NO_REASON)
    LOT_OWED_PAYMENT_SUCCEED = TunableUiDialogNotificationSnippet(description='\n        A notification which pops up when payment owed from previous lot is deducted.\n        ')
    LOT_OWED_PAYMENT_FAIL = TunableUiDialogNotificationSnippet(description='\n        A notification which pops up when payment owed from previous lot fails to be deducted.\n        ')

    def __init__(self, household):
        self._household = household
        self._utility_delinquency = {utility: False for utility in Utilities}
        self._can_deliver_bill = False
        self._current_payment_owed = None
        self._bill_timer_handle = None
        self._shutoff_handle = None
        self._warning_handle = None
        self._additional_bill_costs = {}
        self.bill_notifications_enabled = True
        self.autopay_bills = False
        self._stored_bill_timer_ticks = 0
        self._stored_shutoff_timer_ticks = 0
        self._stored_warning_timer_ticks = 0
        self._put_bill_in_hidden_inventory = False
        self._lot_unpaid_bill = {}

    @property
    def can_deliver_bill(self):
        return self._can_deliver_bill

    @property
    def current_payment_owed(self):
        return self._current_payment_owed

    def get_utility_info(self, utility):
        utility_infos = self.UTILITY_INFO[utility]
        resolver = SingleSimResolver(services.active_sim_info())
        for utility_info in utility_infos:
            if utility_info.tests.run_tests(resolver):
                return utility_info
        logger.error('Utility Info could not pass tests for {}. Please check tuning in bills', utility, owner='rmccord')

    def _get_lot(self):
        home_zone = services.get_zone(self._household.home_zone_id)
        if home_zone is not None:
            return home_zone.lot

    def _set_up_alarm(self, timer_data, handle, callback):
        if timer_data <= 0:
            return
        if handle is not None:
            alarms.cancel_alarm(handle)
        return alarms.add_alarm(self._household, clock.TimeSpan(timer_data), callback, use_sleep_time=False, cross_zone=True)

    def _set_up_bill_timer(self):
        if self._current_payment_owed is not None:
            return
        if self._stored_bill_timer_ticks > 0:
            self._bill_timer_handle = self._set_up_alarm(self._stored_bill_timer_ticks, self._bill_timer_handle, lambda _: self.allow_bill_delivery())
            self._stored_bill_timer_ticks = 0
            return
        day = self.TIME_TO_PLACE_BILL_IN_HIDDEN_INVENTORY.day
        hour = self.TIME_TO_PLACE_BILL_IN_HIDDEN_INVENTORY.hour
        minute = self.TIME_TO_PLACE_BILL_IN_HIDDEN_INVENTORY.minute
        time = create_date_and_time(days=day, hours=hour, minutes=minute)
        time_until_bill_delivery = services.time_service().sim_now.time_to_week_time(time)
        bill_delivery_time = services.time_service().sim_now + time_until_bill_delivery
        end_of_first_week = DateAndTime(0) + interval_in_sim_weeks(1)
        if bill_delivery_time < end_of_first_week:
            time_until_bill_delivery += interval_in_sim_weeks(1)
        if time_until_bill_delivery.in_ticks() <= 0:
            time_until_bill_delivery = TimeSpan(1)
        self._bill_timer_handle = alarms.add_alarm(self._household, time_until_bill_delivery, lambda _: self.allow_bill_delivery(), cross_zone=True)

    def _set_up_timers(self):
        self._set_up_bill_timer()
        if self._stored_shutoff_timer_ticks == 0 and self._stored_warning_timer_ticks == 0:
            return
        next_delinquent_utility = None
        for utility in self._utility_delinquency:
            if self._utility_delinquency[utility]:
                pass
            else:
                next_delinquent_utility = utility
                break
        logger.error('Household {} has stored shutoff {} or warning {} ticks but all utilities are already delinquent.', self._household, self._stored_shutoff_timer_ticks, self._stored_warning_timer_ticks)
        self._stored_shutoff_timer_ticks = 0
        self._stored_warning_timer_ticks = 0
        return
        utility_info = self.get_utility_info(next_delinquent_utility)
        if utility_info is not None:
            warning_notification = utility_info.warning_notification
            self._warning_handle = self._set_up_alarm(self._stored_warning_timer_ticks, self._warning_handle, lambda _: self._send_notification(warning_notification))
        self._shutoff_handle = self._set_up_alarm(self._stored_shutoff_timer_ticks, self._shutoff_handle, lambda _: self._shut_off_utility(next_delinquent_utility))
        self._stored_shutoff_timer_ticks = 0
        self._stored_warning_timer_ticks = 0

    def get_bills_arrival_notification(self):
        resolver = SingleSimResolver(services.active_sim_info())
        for notification_tests in self.BILL_ARRIVAL_NOTIFICATION:
            if notification_tests.tests.run_tests(resolver):
                return notification_tests.notification
        logger.error('No tests passed for bills arrival notifications. Please check tuning in bills.', owner='rmccord')

    def sanitize_household_inventory(self):
        if build_buy.is_household_inventory_available(self._household.id):
            bill_ids = build_buy.find_objects_in_household_inventory((self.BILL_OBJECT.id,), self._household.id)
            for bill_id in bill_ids:
                build_buy.remove_object_from_household_inventory(bill_id, self._household)

    def on_all_households_and_sim_infos_loaded(self):
        if self._household.id != services.active_household_id():
            return
        if self._current_payment_owed is not None and self._stored_shutoff_timer_ticks == 0 and not (self._can_deliver_bill or self.is_any_utility_delinquent()):
            logger.error('Household {} loaded in a state where bills will never advance. Kickstarting the system.', self._household)
            self.trigger_bill_notifications_from_delivery()
            return
        if self._can_deliver_bill and self._get_lot() is None:
            self.trigger_bill_notifications_from_delivery()
        else:
            self._set_up_timers()
        if self.current_payment_owed is None:
            self._destroy_all_bills_objects()

    def on_active_sim_set(self):
        if self._household.id != services.active_household_id():
            return
        current_zone_id = services.current_zone_id()
        bills_paid_key_tuple = []
        money_to_pay = 0
        sim_ids_at_current_zone = [sim_info.id for sim_info in self._household.sim_info_gen() if sim_info.zone_id == current_zone_id]
        previous_zone_id = 0
        for (key_tuple, money_info) in self._lot_unpaid_bill.items():
            (zone_id, _) = key_tuple
            if zone_id == current_zone_id:
                pass
            else:
                (money_amount, sim_ids) = money_info
                if not any(sim_id in sim_ids for sim_id in sim_ids_at_current_zone):
                    pass
                else:
                    money_to_pay += money_amount
                    bills_paid_key_tuple.append(key_tuple)
                    previous_zone_id = zone_id
        if money_to_pay > 0:
            active_sim = services.get_active_sim()
            funds = get_funds_for_source(FundsSource.HOUSEHOLD, sim=active_sim)
            payment_succeed_notification = self.LOT_OWED_PAYMENT_SUCCEED
            payment_fail_notification = self.LOT_OWED_PAYMENT_FAIL
            venue_tuning = services.venue_service().get_venue_tuning(previous_zone_id)
            if venue_tuning is not None:
                zone_director_tuning = venue_tuning.zone_director
                if zone_director_tuning.venue_owed_payment_data.payment_succeed_notification is not None:
                    payment_succeed_notification = zone_director_tuning.venue_owed_payment_data.payment_succeed_notification
                if zone_director_tuning.venue_owed_payment_data.payment_fail_notification is not None:
                    payment_fail_notification = zone_director_tuning.venue_owed_payment_data.payment_fail_notification
            if funds.try_remove(money_to_pay, Consts_pb2.TELEMETRY_INTERACTION_COST, active_sim):
                dialog = payment_succeed_notification(active_sim.sim_info, None)
                dialog.show_dialog(additional_tokens=(money_to_pay,))
            else:
                dialog = payment_fail_notification(active_sim.sim_info, None)
                dialog.show_dialog(additional_tokens=(money_to_pay,))
        for key_tuple in bills_paid_key_tuple:
            del self._lot_unpaid_bill[key_tuple]

    def is_utility_delinquent(self, utility):
        if self._utility_delinquency[utility]:
            if self._current_payment_owed is None:
                self._clear_delinquency_status()
                logger.error('Household {} has delinquent utilities without actually owing any money. Resetting delinquency status.', self._household)
                return False
            else:
                return True
        return False

    def is_any_utility_delinquent(self):
        for delinquency_status in self._utility_delinquency.values():
            if delinquency_status:
                return True
        return False

    def mailman_has_delivered_bills(self):
        if self.current_payment_owed is not None and (self._shutoff_handle is not None or self.is_any_utility_delinquent()):
            return True
        return False

    def is_additional_bill_source_delinquent(self, additional_bill_source):
        cost = self._additional_bill_costs.get(additional_bill_source, 0)
        if cost > 0 and any(self._utility_delinquency.values()):
            return True
        return False

    def get_bill_amount(self):
        bill_amount = 0
        plex_service = services.get_plex_service()
        if plex_service.is_zone_an_apartment(self._household.home_zone_id, consider_penthouse_an_apartment=False):
            persistence_service = services.get_persistence_service()
            house_description_id = persistence_service.get_house_description_id(self._household.home_zone_id)
            bill_amount += services.get_rent(house_description_id)
        else:
            billable_household_value = self._household.household_net_worth(billable=True)
            for bracket in Bills.BILL_BRACKETS:
                lower_bound = bracket.value_range.lower_bound
                if billable_household_value >= lower_bound:
                    upper_bound = bracket.value_range.upper_bound
                    if upper_bound is None:
                        upper_bound = billable_household_value
                    bound_difference = upper_bound - lower_bound
                    value_difference = billable_household_value - lower_bound
                    if value_difference > bound_difference:
                        value_difference = bound_difference
                    value_difference *= bracket.tax_percentage
                    bill_amount += value_difference
        for additional_cost in self._additional_bill_costs.values():
            bill_amount += additional_cost
        multiplier = 1
        for sim_info in self._household._sim_infos:
            multiplier *= Bills.BILL_COST_MODIFIERS_SIM.get_multiplier(SingleSimResolver(sim_info))
        multiplier *= Bills.BILL_COST_MODIFIERS_HOUSEHOLD.get_multiplier(SingleSimResolver(GlobalResolver()))
        bill_amount *= multiplier
        bill_reductions = services.global_policy_service().get_bill_reductions()
        if bill_reductions:
            for reduction in bill_reductions.values():
                bill_amount *= reduction
        if bill_amount <= 0 and self._household.is_active_household:
            logger.error('\n                Player household {} has been determined to owe {} Simoleons. \n                Player households are always expected to owe at least some amount \n                of money for bills.\n                ', self._household, bill_amount)
        return int(bill_amount)

    def allow_bill_delivery(self):
        if self._bill_timer_handle is not None:
            alarms.cancel_alarm(self._bill_timer_handle)
            self._bill_timer_handle = None
        self._place_bill_in_hidden_inventory()

    def _place_bill_in_hidden_inventory(self):
        self._current_payment_owed = self.get_bill_amount()
        if self._current_payment_owed <= 0:
            self.pay_bill(sound=False)
            return
        lot = self._get_lot()
        if lot is not None:
            lot.create_object_in_hidden_inventory(self.BILL_OBJECT, self._household.id)
            self._put_bill_in_hidden_inventory = False
            self._can_deliver_bill = True
            return
        self._put_bill_in_hidden_inventory = True
        self.trigger_bill_notifications_from_delivery()

    def _place_bill_in_mailbox(self):
        lot = self._get_lot()
        if lot is None:
            return
        lot.create_object_in_mailbox(self.BILL_OBJECT, self._household.id)
        self._put_bill_in_hidden_inventory = False

    def trigger_bill_notifications_from_delivery(self):
        if self.mailman_has_delivered_bills():
            return
        self._can_deliver_bill = False
        if self.autopay_bills or self._current_payment_owed == 0 or not self._household:
            self.pay_bill(sound=False)
            return
        self._set_next_delinquency_timers()
        bills_arrival_notification = self.get_bills_arrival_notification()
        if bills_arrival_notification is not None:
            self._send_notification(bills_arrival_notification)

    def _destroy_all_bills_objects(self):

        def is_current_households_bill(obj, household_id):
            return obj.definition is self.BILL_OBJECT and (obj.get_household_owner_id() is None or obj.get_household_owner_id() == household_id)

        def remove_from_inventory(inventory):
            for obj in [obj for obj in inventory if is_current_households_bill(obj, self._household.id)]:
                obj.destroy(source=inventory, cause='Paying bills.')

        lot = self._get_lot()
        if lot is not None:
            for (_, inventory) in lot.get_all_object_inventories_gen():
                remove_from_inventory(inventory)
        for sim_info in self._household:
            sim = sim_info.get_sim_instance()
            if sim is not None:
                remove_from_inventory(sim.inventory_component)
        self._put_bill_in_hidden_inventory = False

    def pay_bill(self, sound=True):
        if self._current_payment_owed:
            for status in self._utility_delinquency.values():
                if status:
                    play_tunable_audio(self.AUDIO.delinquency_removed_sfx)
                    break
            if sound:
                play_tunable_audio(self.AUDIO.bills_paid_sfx)
        self._current_payment_owed = None
        self._clear_delinquency_status()
        self._set_up_bill_timer()
        self._destroy_all_bills_objects()

    def _clear_delinquency_status(self):
        for utility in self._utility_delinquency:
            services.utilities_manager(self._household.id).restore_utility(utility, self.BILLS_UTILITY_SHUTOFF_REASON)
            self._utility_delinquency[utility] = False
        self._additional_bill_costs = {}
        if self._shutoff_handle is not None:
            alarms.cancel_alarm(self._shutoff_handle)
            self._shutoff_handle = None
        if self._warning_handle is not None:
            alarms.cancel_alarm(self._warning_handle)
            self._warning_handle = None

    def _set_next_delinquency_timers(self):
        for utility in self._utility_delinquency:
            if self._utility_delinquency[utility]:
                pass
            else:
                utility_info = self.get_utility_info(utility)
                if utility_info is not None:
                    warning_notification = utility_info.warning_notification
                    self._warning_handle = alarms.add_alarm(self, clock.interval_in_sim_hours(self.DELINQUENCY_FREQUENCY - self.DELINQUENCY_WARNING_OFFSET_TIME), lambda _: self._send_notification(warning_notification), cross_zone=True)
                self._shutoff_handle = alarms.add_alarm(self, clock.interval_in_sim_hours(self.DELINQUENCY_FREQUENCY), lambda _: self._shut_off_utility(utility), cross_zone=True)
                break

    def _shut_off_utility(self, utility):
        if self._current_payment_owed == None:
            self._clear_delinquency_status()
            logger.error('Household {} is getting a utility shut off without actually owing any money. Resetting delinquency status.', self._household)
            return
        utility_info = self.get_utility_info(utility)
        shutoff_tooltip = None
        if utility_info is not None:
            shutoff_notification = utility_info.shutoff_notification
            self._send_notification(shutoff_notification)
            shutoff_tooltip = utility_info.shutoff_tooltip
        if self._shutoff_handle is not None:
            alarms.cancel_alarm(self._shutoff_handle)
            self._shutoff_handle = None
        self._utility_delinquency[utility] = True
        self._set_next_delinquency_timers()
        services.utilities_manager(self._household.id).shut_off_utility(utility, self.BILLS_UTILITY_SHUTOFF_REASON, shutoff_tooltip)

    def _send_notification(self, notification):
        current_time = services.time_service().sim_now
        if self._warning_handle is not None and self._warning_handle.finishing_time <= current_time:
            alarms.cancel_alarm(self._warning_handle)
            self._warning_handle = None
            play_tunable_audio(self.AUDIO.delinquency_warning_sfx)
        if not self.bill_notifications_enabled:
            return
        reduction_reasons_string = ''
        bill_reductions = services.global_policy_service().get_bill_reductions()
        if bill_reductions:
            reduction_reasons = []
            for (reduction_reason, reduction) in bill_reductions.items():
                reduction_text = self.REDUCTION_REASON_TEXT_MAP.get(reduction_reason)
                if reduction_text:
                    reduction_reasons.append(reduction_text(reduction*100))
                else:
                    logger.error('Attempting to get reduction reason ({}) bullet point without a tuned value in the Reduction Reason Text Map.', str(reduction_reason), owner='shipark')
                    return
            reduction_reasons_string = LocalizationHelperTuning.get_bulleted_list((None,), reduction_reasons)
        client = services.client_manager().get_client_by_household(self._household)
        if client is not None:
            active_sim_info = client.active_sim_info
            if active_sim_info is not None:
                remaining_time = max(int(self._shutoff_handle.get_remaining_time().in_hours()), 0)
                dialog = notification(active_sim_info, None)
                icon_override = DEFAULT
                plex_service = services.get_plex_service()
                if plex_service.is_zone_a_plex(self._household.home_zone_id):
                    icon_override = IconInfoData(obj_instance=services.get_landlord_service().get_landlord_sim_info())
                dialog.show_dialog(icon_override=icon_override, additional_tokens=(remaining_time, self._current_payment_owed, reduction_reasons_string))

    def add_additional_bill_cost(self, additional_bill_source, cost):
        current_cost = self._additional_bill_costs.get(additional_bill_source, 0)
        self._additional_bill_costs[additional_bill_source] = current_cost + cost

    def add_lot_unpaid_bill(self, zone_id, situation_id, money_amount, sims_on_lot):
        key_tuple = (zone_id, situation_id)
        self._lot_unpaid_bill[key_tuple] = (money_amount, list(sims_on_lot))

    def remove_lot_unpaid_bill(self, zone_id, situation_id):
        key_tuple = (zone_id, situation_id)
        if key_tuple in self._lot_unpaid_bill:
            del self._lot_unpaid_bill[key_tuple]

    def load_data(self, householdProto):
        for additional_bill_cost in householdProto.gameplay_data.additional_bill_costs:
            self.add_additional_bill_cost(additional_bill_cost.bill_source, additional_bill_cost.cost)
        for lot_unpaid_bill_item in householdProto.gameplay_data.lot_unpaid_bill_data:
            key_tuple = (lot_unpaid_bill_item.zone_id, lot_unpaid_bill_item.situation_id)
            sims_on_lot = []
            for sim_id in lot_unpaid_bill_item.sim_ids_on_lot:
                sims_on_lot.append(sim_id)
            self._lot_unpaid_bill[key_tuple] = (lot_unpaid_bill_item.money_amount, sims_on_lot)
        self._can_deliver_bill = householdProto.gameplay_data.can_deliver_bill
        self._put_bill_in_hidden_inventory = householdProto.gameplay_data.put_bill_in_hidden_inventory
        if self._put_bill_in_hidden_inventory:
            self._place_bill_in_mailbox()
        self._current_payment_owed = householdProto.gameplay_data.current_payment_owed
        if self._current_payment_owed == 0:
            self._current_payment_owed = None
        self._stored_bill_timer_ticks = householdProto.gameplay_data.bill_timer
        self._stored_shutoff_timer_ticks = householdProto.gameplay_data.shutoff_timer
        self._stored_warning_timer_ticks = householdProto.gameplay_data.warning_timer
        if self._stored_shutoff_timer_ticks > 0 or self._stored_warning_timer_ticks > 0:
            logger.error('Household {} loaded with utility shutoff or warning timers but no owed payment. Clearing utility shutoff and warning timers.', self._household)
            self._stored_shutoff_timer_ticks = 0
            self._stored_warning_timer_ticks = 0
        if self._stored_bill_timer_ticks > 0:
            logger.error('Household {} loaded with both a bill delivery timer and an owed payment. Clearing bill delivery timer.', self._household)
            self._stored_bill_timer_ticks = 0
        for utility in householdProto.gameplay_data.delinquent_utilities:
            self._utility_delinquency[utility] = True
            utility_info = self.get_utility_info(utility)
            shutoff_tooltip = None
            if utility_info is not None:
                shutoff_tooltip = utility_info.shutoff_tooltip
            services.utilities_manager(self._household.id).shut_off_utility(utility, self.BILLS_UTILITY_SHUTOFF_REASON, shutoff_tooltip, from_load=True)

    def save_data(self, household_msg):
        for utility in Utilities:
            if self.is_utility_delinquent(utility):
                household_msg.gameplay_data.delinquent_utilities.append(utility)
        for (bill_source, cost) in self._additional_bill_costs.items():
            with ProtocolBufferRollback(household_msg.gameplay_data.additional_bill_costs) as additional_bill_cost:
                additional_bill_cost.bill_source = bill_source
                additional_bill_cost.cost = cost
        for (key_tuple, money_sim_info) in self._lot_unpaid_bill.items():
            (zone_id, situation_id) = key_tuple
            with ProtocolBufferRollback(household_msg.gameplay_data.lot_unpaid_bill_data) as lot_unpaid_bill:
                lot_unpaid_bill.zone_id = zone_id
                lot_unpaid_bill.situation_id = situation_id
                (money_amount, sim_ids) = money_sim_info
                lot_unpaid_bill.money_amount = money_amount
                for sim_id in sim_ids:
                    lot_unpaid_bill.sim_ids_on_lot.append(sim_id)
        household_msg.gameplay_data.can_deliver_bill = self._can_deliver_bill
        household_msg.gameplay_data.put_bill_in_hidden_inventory = self._put_bill_in_hidden_inventory
        if self.current_payment_owed is not None:
            household_msg.gameplay_data.current_payment_owed = self.current_payment_owed
        current_time = services.time_service().sim_now
        if self._bill_timer_handle is not None:
            time = max((self._bill_timer_handle.finishing_time - current_time).in_ticks(), 0)
            household_msg.gameplay_data.bill_timer = time
        else:
            household_msg.gameplay_data.bill_timer = self._stored_bill_timer_ticks
        if self._shutoff_handle is not None:
            time = max((self._shutoff_handle.finishing_time - current_time).in_ticks(), 0)
            household_msg.gameplay_data.shutoff_timer = time
        else:
            household_msg.gameplay_data.shutoff_timer = self._stored_shutoff_timer_ticks
        if self._warning_handle is not None:
            time = max((self._warning_handle.finishing_time - current_time).in_ticks(), 0)
            household_msg.gameplay_data.warning_timer = time
        else:
            household_msg.gameplay_data.warning_timer = self._stored_warning_timer_ticks
