import randomfrom scheduler import WeeklySchedulefrom sims.bills import BillReductionEnumfrom sims4.tuning.tunable import TunableVariant, TunablePercent, OptionalTunable, HasTunableFactory, AutoFactoryInit, TunableEnumEntry, TunableTuple, HasTunableSingletonFactory, HasTunableReferencefrom zone_modifier.zone_modifier_household_actions import ZoneModifierHouseholdShutOffUtilityimport alarmsimport services
class GlobalPolicyEffectVariants(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, shut_off_utilities=ScheduleUtilityShutOff.TunableFactory(), bill_reduction=BillReduction.TunableFactory(), default='shut_off_utilities', **kwargs)

class GlobalPolicyEffect:

    def turn_on(self, global_policy_id, from_load=False):
        raise NotImplementedError

    def turn_off(self, global_policy_id):
        raise NotImplementedError

class ScheduleUtilityShutOff(GlobalPolicyEffect, ZoneModifierHouseholdShutOffUtility, HasTunableFactory):
    FACTORY_TUNABLES = {'chance': OptionalTunable(description='\n            The percent chance that, after an effect is turned on, that utility\n            will turn off day-to-day. \n            ', tunable=TunablePercent(default=10)), 'schedule_data': WeeklySchedule.TunableFactory(description='\n            The information to schedule points during the week that\n            the Global Policy Effect, if enacted, will turn off the tuned\n            utility.\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._schedule = None
        self._stop_schedule_entry = None

    def turn_on(self, global_policy_id, from_load=False):
        self._schedule = self.schedule_data(start_callback=self.scheduled_start_action, schedule_immediate=True)
        if not from_load:
            services.global_policy_service().add_utility_effect(global_policy_id, self)

    def turn_off(self, global_policy_id):
        household_id = services.active_household().id
        self.stop_action(household_id)
        if self._schedule is not None:
            self._schedule.destroy()
        if self._stop_schedule_entry is not None:
            alarms.cancel_alarm(self._stop_schedule_entry)
        services.global_policy_service().remove_utility_effect(global_policy_id)

    def scheduled_start_action(self, scheduler, alarm_data, extra_data):
        if self.chance and random.random() < self.chance:
            return
        household_id = services.active_household().id
        self.start_action(household_id)
        blackout_end_time = alarm_data[1] - alarm_data[0]
        self._stop_schedule_entry = alarms.add_alarm(self, blackout_end_time, lambda _: self.scheduled_stop_action(household_id), cross_zone=True)

    def scheduled_stop_action(self, household_id):
        self.stop_action(household_id)

class BillReduction(GlobalPolicyEffect, HasTunableSingletonFactory, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'percent_reduction': TunableTuple(description='\n            A mapping of bill reduction reason to percent reduction. Reasons for bill\n            reduction can be added to sims.bills tuning.\n            ', reduction_reason=TunableEnumEntry(description='\n                Reason for bill reduction.\n                ', tunable_type=BillReductionEnum, default=BillReductionEnum.GlobalPolicy_ControlInvasiveSpecies), reduction_amount=TunablePercent(description='\n                Percent by which all household bills are reduced.\n                ', default=50))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def turn_on(self, _, from_load=False):
        services.global_policy_service().add_bill_reduction(self.percent_reduction.reduction_reason, self.percent_reduction.reduction_amount)

    def turn_off(self, _):
        services.global_policy_service().remove_bill_reduction(self.percent_reduction.reduction_reason)
