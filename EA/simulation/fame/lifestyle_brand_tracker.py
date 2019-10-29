from protocolbuffers import SimObjectAttributes_pb2, Consts_pb2from bucks.bucks_utils import BucksUtilsfrom event_testing.resolver import SingleSimResolverfrom fame.fame_tuning import LifestyleBrandTargetMarket, LifestyleBrandProduct, FameTunablesfrom scheduler import WeeklySchedulefrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims4.tuning.geometric import TunableCurvefrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, TunableTuple, Tunablefrom sims4.utils import classpropertyfrom tunable_multiplier import TunableMultiplierfrom ui.ui_dialog_notification import UiDialogNotificationimport servicesimport sims4.resources
class LifestyleBrandTracker(SimInfoTracker):
    PAYMENT_SCHEDULE = WeeklySchedule.TunableFactory(description='\n        The schedule for when payments should be made. This is global to all\n        Sims that have lifestyle brands.\n        ')
    LIFESTYLE_BRAND_PAYOUT_MAPPING = TunableMapping(description="\n        This is a mapping of target market to another mapping of product to\n        payout curve.\n        \n        Each combination of target market and product will have it's own unique\n        payout curve.\n        ", key_type=TunableEnumEntry(description='\n            An enum representation of the different kinds of target markets \n            that are available as options for the lifestyle brand.\n            ', tunable_type=LifestyleBrandTargetMarket, default=LifestyleBrandTargetMarket.INVALID, invalid_enums=(LifestyleBrandTargetMarket.INVALID,)), value_type=TunableMapping(description='\n            This mapping is of product to payout curve.\n            ', key_type=TunableEnumEntry(description='\n                An enum representation of the products that are available as \n                options for the lifestyle brand.\n                ', tunable_type=LifestyleBrandProduct, default=LifestyleBrandProduct.INVALID, invalid_enums=(LifestyleBrandProduct.INVALID,)), value_type=TunableTuple(description='\n                Data required to calculate the payout for this product.\n                ', curve=TunableCurve(description='\n                    This curve is days to payout amount in simoleons.\n                    ', x_axis_name='Days Active', y_axis_name='Simoleon Amount'), payment_deviation_percent=Tunable(description='\n                    Once the payment amount is decided (using the Pay Curve and the \n                    Payment Multipliers), it will be multiplied by this number then \n                    added to and subtracted from the final payment amount to give a min \n                    and max. Then, a random amount between the min and max will be \n                    chosen and awarded to the player.\n                    \n                    Example: After using the Payment Curve and the Payment Multipliers,\n                    we get a payment amount of $10.\n                    The Payment Deviation is 0.2. $10 x 0.2 = 2\n                    Min = $10 - 2 = $8\n                    Max = $10 + 2 = $12\n                    Final Payment will be some random amount between $8 and $12,\n                    inclusively.\n                    ', tunable_type=float, default=0))))
    LIFESTYLE_BRAND_EARNINGS_NOTIFICATION = UiDialogNotification.TunableFactory(description='\n        The notification that gets shown when a Sim earns money from their\n        lifestyle brand.\n        \n        Tokens:\n        0 - Sim\n        1 - amount earned\n        2 - brand name\n        ')
    BRAND_PAYMENT_MULTIPLIERS = TunableMultiplier.TunableFactory(description='\n        A list of test sets which, if they pass, will provide a multiplier to \n        each royalty payment.\n        \n        These tests are only run when a brand is created or changed. If it \n        passes then the payouts will be multiplied going forward until the\n        brand is changed or the brand is stopped and started again.\n        ')

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self.clear_brand()
        self._days_active = 0
        self._active_multiplier = 1

    @property
    def active(self):
        return self._product_choice != LifestyleBrandProduct.INVALID and self.target_market != LifestyleBrandTargetMarket.INVALID

    @property
    def days_active(self):
        return self._days_active

    @property
    def product_choice(self):
        return self._product_choice

    @product_choice.setter
    def product_choice(self, value):
        if self._product_choice != value:
            self._restart_days_active()
            self._product_choice = value

    @property
    def target_market(self):
        return self._target_market

    @target_market.setter
    def target_market(self, value):
        if self._target_market != value:
            self._restart_days_active()
            self._target_market = value

    @property
    def logo(self):
        return self._logo

    @logo.setter
    def logo(self, value):
        if self._logo != value:
            self._restart_days_active()
            self._logo = value

    @property
    def brand_name(self):
        return self._brand_name

    @brand_name.setter
    def brand_name(self, value):
        if self._brand_name != value:
            self._restart_days_active()
            self._brand_name = value

    def _restart_days_active(self):
        self._days_active = 0
        self._start_multipliers()

    def update_days_active(self):
        self._days_active += 1

    def _start_multipliers(self):
        self._active_multiplier = LifestyleBrandTracker.BRAND_PAYMENT_MULTIPLIERS.get_multiplier(SingleSimResolver(self._sim_info))

    def payout_lifestyle_brand(self):
        if not self.active:
            return
        if FameTunables.LIFESTYLE_BRAND_PERK is None:
            self.clear_brand()
            return
        bucks_tracker = BucksUtils.get_tracker_for_bucks_type(FameTunables.LIFESTYLE_BRAND_PERK.associated_bucks_type, self._sim_info.id)
        if bucks_tracker is None or not bucks_tracker.is_perk_unlocked(FameTunables.LIFESTYLE_BRAND_PERK):
            self.clear_brand()
            return
        payout = self.get_payout_amount()
        if payout > 0:
            self._sim_info.household.funds.add(payout, Consts_pb2.FUNDS_LIFESTYLE_BRAND)
            self._display_earnings_notification(payout)
        self.update_days_active()

    def get_payout_amount(self):
        payout = 0
        product_data = LifestyleBrandTracker.LIFESTYLE_BRAND_PAYOUT_MAPPING.get(self._target_market)
        if product_data is not None:
            payment_data = product_data.get(self._product_choice)
            if payment_data is not None:
                (final_payment_day, _) = payment_data.curve.points[-1]
                if self._days_active > final_payment_day:
                    self._days_active = int(final_payment_day)
                payout = payment_data.curve.get(self._days_active)
                payout *= self._active_multiplier
                payout = self._apply_deviation_calculation(payout, payment_data.payment_deviation_percent)
        return payout

    def _apply_deviation_calculation(self, payout, deviation_percent):
        deviation = payout*deviation_percent
        min_payment = payout - deviation
        max_payment = payout + deviation
        return int(sims4.random.uniform(min_payment, max_payment))

    def _display_earnings_notification(self, amount_earned):
        resolver = SingleSimResolver(self._sim_info)
        dialog = LifestyleBrandTracker.LIFESTYLE_BRAND_EARNINGS_NOTIFICATION(self._sim_info, resolver)
        dialog.show_dialog(additional_tokens=(amount_earned, self.brand_name))

    def clear_brand(self):
        self._product_choice = LifestyleBrandProduct.INVALID
        self._target_market = LifestyleBrandTargetMarket.INVALID
        self._brand_name = None
        self._logo = None
        self._days_active = 0

    def save(self):
        data = SimObjectAttributes_pb2.PersistableLifestyleBrandTracker()
        if self._product_choice is not None:
            data.product = self._product_choice
        if self._target_market is not None:
            data.target_market = self._target_market
        icon_proto = sims4.resources.get_protobuff_for_key(self._logo)
        if icon_proto is not None:
            data.logo = icon_proto
        if self._brand_name is not None:
            data.brand_name = self._brand_name
        data.days_active = self._days_active
        return data

    def load(self, data):
        self._product_choice = data.product
        self._target_market = data.target_market
        self._logo = sims4.resources.Key(data.logo.type, data.logo.instance, data.logo.group)
        self._brand_name = data.brand_name
        self._days_active = data.days_active

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.FULL

    def on_lod_update(self, old_lod, new_lod):
        if new_lod < self._tracker_lod_threshold:
            self.clear_brand()
        elif old_lod < self._tracker_lod_threshold:
            sim_msg = services.get_persistence_service().get_sim_proto_buff(self._sim_info.id)
            if sim_msg is not None:
                self.load(sim_msg.attributes.lifestyle_brand_tracker)
