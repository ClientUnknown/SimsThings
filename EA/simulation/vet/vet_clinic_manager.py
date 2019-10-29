from _collections import dequefrom business.advertising_manager import HasAdvertisingManagerMixinfrom business.business_enums import BusinessType, BusinessAdvertisingType, BusinessQualityTypefrom business.business_manager import BusinessManagerfrom distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorfrom protocolbuffers import Business_pb2, DistributorOps_pb2from vet.vet_clinic_summary_dialog import VetClinicSummaryDialogfrom vet.vet_clinic_tuning import VetClinicTuningfrom vet.vet_clinic_utils import get_vet_clinic_zone_director, get_bonus_paymentimport servicesimport sims4.loglogger = sims4.log.Logger('Vet Clinic')
class VetClinicManager(HasAdvertisingManagerMixin, BusinessManager):

    def __init__(self):
        super().__init__(BusinessType.VET)
        self._exam_table_count = 0
        self._quality_setting = self.tuning_data.default_quality
        self._summary_dialog_class = VetClinicSummaryDialog
        self._profits_per_treatment = deque([VetClinicTuning.DEFAULT_PROFIT_PER_TREATMENT_FOR_OFF_LOT_SIMULATION], maxlen=VetClinicTuning.MAX_COUNT_FOR_OFF_LOT_PROFIT_PER_TREATMENT)

    def _open_pure_npc_store(self, is_premade):
        self.set_open(True)

    def save_data(self, business_save_data):
        super().save_data(business_save_data)
        business_save_data.vet_clinic_save_data = Business_pb2.VetClinicSaveData()
        business_save_data.vet_clinic_save_data.advertising_type = self._advertising_manager._advertising_type
        business_save_data.vet_clinic_save_data.quality_type = self.quality_setting
        business_save_data.vet_clinic_save_data.profit_per_treatment_queue.extend(int(profit) for profit in self._profits_per_treatment)
        business_save_data.vet_clinic_save_data.exam_table_count = self._exam_table_count

    def load_data(self, business_save_data, is_legacy=False):
        super().load_data(business_save_data, is_legacy)
        self.set_quality_setting(BusinessQualityType(business_save_data.vet_clinic_save_data.quality_type))
        self.set_advertising_type(business_save_data.vet_clinic_save_data.advertising_type)
        self._profits_per_treatment.clear()
        profit_per_treatment_save_data = business_save_data.vet_clinic_save_data.profit_per_treatment_queue
        if profit_per_treatment_save_data and len(profit_per_treatment_save_data) > VetClinicTuning.MAX_COUNT_FOR_OFF_LOT_PROFIT_PER_TREATMENT:
            logger.info('About to load more values for the profit_per_treatment_queue than the tuned max size of the queue. Values will be lost.\n save data queue size:{}\n max queue size:{}', len(profit_per_treatment_save_data), VetClinicTuning.MAX_COUNT_FOR_OFF_LOT_PROFIT_PER_TREATMENT)
        for profit in profit_per_treatment_save_data:
            self._profits_per_treatment.append(profit)
        self._exam_table_count = business_save_data.vet_clinic_save_data.exam_table_count

    def construct_business_message(self, msg):
        super().construct_business_message(msg)
        msg.vet_clinic_data = self._build_vet_clinic_data_message()

    def set_quality_setting(self, quality_type):
        self._quality_setting = quality_type
        self._distribute_business_manager_data_message()

    @property
    def quality_setting(self):
        return self._quality_setting

    def set_exam_table_count(self, value):
        self._exam_table_count = value

    def get_ideal_customer_count(self):
        return self.tuning_data.star_rating_to_customer_count_curve.get(self.get_star_rating())*self.tuning_data.time_of_day_to_customer_count_multiplier_curve.get(services.time_service().sim_now.hour())*self.get_advertising_multiplier()

    def _get_off_lot_customer_count(self, hours_since_last_sim):
        customer_count_per_hour = self.get_ideal_customer_count()
        customer_count_per_hour = min(self._exam_table_count, customer_count_per_hour*self.tuning_data.off_lot_customer_count_multiplier)
        customer_count_per_hour *= self.tuning_data.off_lot_customer_count_penalty_multiplier
        return int(customer_count_per_hour*hours_since_last_sim)

    def _get_average_profit_per_service(self):
        if not self._profits_per_treatment:
            return 0
        profits_sum = sum(self._profits_per_treatment)
        return profits_sum/len(self._profits_per_treatment)

    def should_show_no_way_to_make_money_notification(self):
        if not self.meets_minimum_employee_requirment():
            return True
        return self._exam_table_count <= 0

    def meets_minimum_employee_requirment(self):
        if self.is_active_household_and_zone():
            return True
        return self.employee_count > 0

    def _open_business(self):
        super()._open_business()
        self._advertising_manager.open_business()

    def _close_business(self, **kwargs):
        super()._close_business(**kwargs)
        self.modify_funds(-self._advertising_manager.get_current_advertising_cost(), from_item_sold=False)

    def _clear_state(self):
        super()._clear_state()
        self._advertising_manager.clear_state()
        if not self.is_active_household_and_zone():
            return
        zone_director = get_vet_clinic_zone_director()
        if zone_director is not None:
            zone_director.clear_state()

    def should_automatically_close(self):
        if self.employee_count > 0:
            return False
        return self.is_owner_household_active and (self._zone_id is not None and self._zone_id != services.current_zone_id())

    def _build_vet_clinic_data_message(self):
        msg = Business_pb2.VetClinicBusinessDataUpdate()
        msg.zone_id = self.business_zone_id
        if self._advertising_manager._advertising_type != BusinessAdvertisingType.INVALID:
            msg.advertising_chosen = self._advertising_manager._advertising_type
        msg.quality_chosen = self._quality_setting
        msg.is_quality_unlocked = self._quality_unlocked
        return msg

    def _distribute_business_manager_data_message(self):
        msg = self._build_vet_clinic_data_message()
        op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.VET_CLINIC_DATA_UPDATE, msg)
        Distributor.instance().add_op_with_no_owner(op)

    def bill_owner_for_treatment(self, treatment_cost, sickness_difficulty, award_difficulty_bonus):
        total_payment = self.get_value_with_markup(treatment_cost)
        if award_difficulty_bonus:
            total_payment += get_bonus_payment(sickness_difficulty)
        self._profits_per_treatment.append(max(0, total_payment - treatment_cost))
        self.modify_funds(total_payment, from_item_sold=True)
