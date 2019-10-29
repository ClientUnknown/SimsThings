from celebrity_fans.fan_zone_director_mixin import FanZoneDirectorMixinfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableSimMinute, TunableList, TunableTuple, TunableEnumEntry, TunableVariant, Tunable, TunableReferencefrom situations.additional_situation_sources import HolidayWalkbys, ZoneModifierSituations, NarrativeSituationsfrom situations.situation_curve import SituationCurve, ShiftlessDesiredSituationsfrom situations.situation_guest_list import SituationGuestListfrom situations.situation_types import SituationSerializationOptionfrom venues.object_based_situation_zone_director import ObjectBasedSituationZoneDirectorMixinfrom zone_director import ZoneDirectorBaseimport alarmsimport clockimport enumimport servicesimport sims4.loglogger = sims4.log.Logger('ZoneDirectorScheduling')
class SituationChurnOperation(enum.Int, export=False):
    DO_NOTHING = 0
    START_SITUATION = 1
    REMOVE_SITUATION = 2

class SituationShiftStrictness(enum.Int):
    DESTROY = 0
    OVERLAP = 1

class SchedulingZoneDirectorMixin:

    @staticmethod
    def _verify_situations_on_load_callback(instance_class, tunable_name, source, value, **kwargs):
        for situation in value:
            if situation.situation_serialization_option != SituationSerializationOption.DONT:
                logger.error('Situation {} in situations on load tuning for zone director {} has an invalid persistence option. Only DONT is acceptable.', situation, instance_class)

    INSTANCE_TUNABLES = {'situations_on_load': TunableList(description="\n            Situations that are always started when the zone director loads and\n            are only shut down by the zone director when the zone director shuts\n            down (although they can still end by other means). Because these\n            situations are always restarted, it is invalid to schedule\n            situations with a positive persistence option here (ask a GPE if you\n            need to determine a situation's persistence option).\n            ", tunable=TunableReference(manager=services.get_instance_manager(Types.SITUATION), pack_safe=True), verify_tunable_callback=_verify_situations_on_load_callback), 'situation_shifts': TunableList(description='\n            A list of situation distributions and their strictness rules.\n            ', tunable=TunableTuple(shift_curve=TunableVariant(curve_based=SituationCurve.TunableFactory(get_create_params={'user_facing': True}), shiftless=ShiftlessDesiredSituations.TunableFactory(get_create_params={'user_facing': True}), default='curve_based'), shift_strictness=TunableEnumEntry(description='\n                    Determine how situations on shift will be handled on shift\n                    change.\n                    \n                    Example: I want 3 customers between 10-12.  then after 12 I\n                    want only 1.  Having this checked will allow 3 customers to\n                    stay and will let situation duration kick the sim out when\n                    appropriate.  This will not create new situations if over\n                    the cap.\n                    ', tunable_type=SituationShiftStrictness, default=SituationShiftStrictness.DESTROY), additional_sources=TunableList(description='\n                    Any additional sources of NPCs that we want to use to add\n                    into the possible situations of this shift curve.\n                    ', tunable=TunableVariant(description='\n                        The different additional situation sources that we\n                        want to use to get additional situation possibilities\n                        that can be chosen.\n                        ', holiday=HolidayWalkbys.TunableFactory(), zone_modifier=ZoneModifierSituations.TunableFactory(), narrative=NarrativeSituations.TunableFactory(), default='holiday')), count_based_on_expected_sims=Tunable(description='\n                    If checked then we will count based on the number of Sims\n                    that are expected to be in the Situation rather than the\n                    number of situations.\n                    ', tunable_type=bool, default=False))), 'churn_alarm_interval': TunableSimMinute(description='\n            Number sim minutes to check to make sure shifts and churn are being accurate.\n            ', default=10), 'set_host_as_active_sim': Tunable(description='\n            If checked then the active Sim will be set as the host of\n            situations started from this director if we do not have a pre-made\n            guest list.\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._shift_alarm_handles = {}
        self._situation_shifts_to_situation_ids = {}
        self._situation_shift_ideal_situations = {}
        self._situations_on_load_ids = []

    def can_schedule_situation(self, situation, limit_based_on_sims=False, number_of_sims_desired=0, **kwargs):
        if services.game_clock_service().clock_speed == clock.ClockSpeedMode.SUPER_SPEED3 and not situation.allowed_in_super_speed_3:
            return False
        if limit_based_on_sims and not situation.can_start_walkby(services.active_lot_id(), number_of_sims_desired):
            return False
        return situation.situation_meets_starting_requirements(**kwargs) and not services.get_zone_modifier_service().is_situation_prohibited(services.current_zone_id(), situation)

    def on_startup(self):
        super().on_startup()
        time_of_day = services.time_service().sim_now
        churn_interval = clock.interval_in_sim_minutes(self.churn_alarm_interval)
        for situation_shift in self.situation_shifts:
            alarm_handle = alarms.add_alarm(self, churn_interval, self._shift_churn_alarm_callback, repeating=True)
            self._shift_alarm_handles[alarm_handle] = situation_shift
            time_span = situation_shift.shift_curve.get_timespan_to_next_shift_time(time_of_day)
            if time_span is not None:
                alarm_handle = alarms.add_alarm(self, time_span, self._shift_change_alarm_callback)
                self._shift_alarm_handles[alarm_handle] = situation_shift

    def on_shutdown(self):
        self.destroy_shifts()
        situation_manager = services.get_zone_situation_manager()
        for situation_id in self._situations_on_load_ids:
            situation_manager.destroy_situation_by_id(situation_id)
        self._situations_on_load_ids.clear()
        super().on_shutdown()

    def destroy_shifts(self):
        for alarm_handle in self._shift_alarm_handles:
            alarms.cancel_alarm(alarm_handle)
        self._shift_alarm_handles.clear()
        situation_manager = services.get_zone_situation_manager()
        for situation_ids in self._situation_shifts_to_situation_ids.values():
            for situation_id in situation_ids:
                situation_manager.destroy_situation_by_id(situation_id)
        self._situation_shifts_to_situation_ids.clear()
        self._situation_shift_ideal_situations.clear()

    def create_situations_during_zone_spin_up(self):
        super().create_situations_during_zone_spin_up()
        for situation_shift in self.situation_shifts:
            self._handle_situation_shift_churn(situation_shift, reserve_object_relationships=True)
        if not self._situations_on_load_ids:
            situation_manager = services.get_zone_situation_manager()
            for situation in self.situations_on_load:
                situation_id = situation_manager.create_situation(situation, user_facing=False, creation_source='Situations on load')
                self._situations_on_load_ids.append(situation_id)

    def _get_default_guest_list(self):
        host_sim_id = 0
        if self.set_host_as_active_sim:
            active_sim_info = services.active_sim_info()
            if active_sim_info is not None:
                host_sim_id = active_sim_info.sim_id
        return SituationGuestList(invite_only=True, host_sim_id=host_sim_id)

    def _shift_change_alarm_callback(self, alarm_handle=None):
        situation_shift = self._shift_alarm_handles.pop(alarm_handle, None)
        if situation_shift is None:
            return
        situation_manager = services.get_zone_situation_manager()
        situation_ids = self._situation_shifts_to_situation_ids.get(situation_shift, [])
        situation_ids = self._prune_stale_situations(situation_ids)
        number_sims_desired_for_shift = situation_shift.shift_curve.get_desired_sim_count().random_int()
        if not situation_shift.shift_curve.desired_sim_count_multipliers:
            self._situation_shift_ideal_situations[situation_shift] = number_sims_desired_for_shift
        if situation_shift.shift_strictness == SituationShiftStrictness.DESTROY:
            for situation_id in situation_ids:
                situation_manager.destroy_situation_by_id(situation_id)
            situation_ids.clear()
        elif situation_shift.shift_strictness == SituationShiftStrictness.OVERLAP:
            if situation_shift.count_based_on_expected_sims:
                for situation_id in situation_ids:
                    situation = situation_manager.get(situation_id)
                    sims_in_situation = situation.get_sims_expected_to_be_in_situation()
                    if sims_in_situation is None:
                        logger.error('Trying to get expected Sims for situation {} that does not provide that information.  Treating as a single Sim.  This situation does not support this behavior.  Contact your GPE partner to fix this.', situation, owner='jjacobson')
                        sims_in_situation = 1
                    number_sims_desired_for_shift -= sims_in_situation
            else:
                number_sims_desired_for_shift -= len(situation_ids)
        logger.debug('Situation Shift Change: Adding {}', number_sims_desired_for_shift)
        while number_sims_desired_for_shift > 0:
            additional_situations = []
            for situation_source in situation_shift.additional_sources:
                additional_situations.extend(situation_source.get_additional_situations(predicate=lambda potential_situation: self.can_schedule_situation(potential_situation, limit_based_on_sims=situation_shift.count_based_on_expected_sims, number_of_sims_desired=number_sims_desired_for_shift)))
            (situation_to_start, params) = situation_shift.shift_curve.get_situation_and_params(predicate=lambda potential_situation: self.can_schedule_situation(potential_situation, limit_based_on_sims=situation_shift.count_based_on_expected_sims, number_of_sims_desired=number_sims_desired_for_shift), additional_situations=additional_situations)
            if situation_to_start is not None:
                guest_list = situation_to_start.get_predefined_guest_list()
                if guest_list is None:
                    guest_list = self._get_default_guest_list()
                logger.debug('Situation Shift Change: Adding situation: {}', situation_to_start)
                try:
                    creation_source = self.instance_name
                except:
                    creation_source = str(self)
                situation_id = situation_manager.create_situation(situation_to_start, guest_list=guest_list, spawn_sims_during_zone_spin_up=True, creation_source=creation_source, **params)
                if situation_id is not None:
                    situation_ids.append(situation_id)
                    if situation_shift.count_based_on_expected_sims:
                        sims_in_situation = situation_to_start.get_sims_expected_to_be_in_situation()
                        if sims_in_situation is None:
                            logger.error('Trying to get expected Sims for situation {} that does not provide that information.  Treating as a single Sim.  This situation does not support this behavior.  Contact your GPE partner to fix this.', situation, owner='jjacobson')
                            sims_in_situation = 1
                        number_sims_desired_for_shift -= sims_in_situation
                    else:
                        number_sims_desired_for_shift -= 1
                else:
                    number_sims_desired_for_shift -= 1
            else:
                number_sims_desired_for_shift -= 1
        self._situation_shifts_to_situation_ids[situation_shift] = situation_ids
        if alarm_handle is not None:
            time_of_day = services.time_service().sim_now
            time_span = situation_shift.shift_curve.get_timespan_to_next_shift_time(time_of_day)
            alarm_handle = alarms.add_alarm(self, time_span, self._shift_change_alarm_callback)
            self._shift_alarm_handles[alarm_handle] = situation_shift

    def _shift_churn_alarm_callback(self, alarm_handle):
        situation_shift = self._shift_alarm_handles.get(alarm_handle, None)
        if situation_shift is None:
            return
        self._handle_situation_shift_churn(situation_shift)

    def _handle_situation_shift_churn(self, situation_shift, reserve_object_relationships=False):
        if situation_shift.shift_curve.is_shift_churn_disabled:
            return
        number_situations_desire = self._situation_shift_ideal_situations.get(situation_shift, None)
        if number_situations_desire is None:
            number_situations_desire = situation_shift.shift_curve.get_desired_sim_count().random_int()
            if not situation_shift.shift_curve.desired_sim_count_multipliers:
                self._situation_shift_ideal_situations[situation_shift] = number_situations_desire
        situation_ids = self._situation_shifts_to_situation_ids.get(situation_shift, [])
        situation_ids = self._prune_stale_situations(situation_ids)
        current_count = 0
        situation_manager = services.get_zone_situation_manager()
        if situation_shift.count_based_on_expected_sims:
            for situation_id in situation_ids:
                situation = situation_manager.get(situation_id)
                sims_in_situation = situation.get_sims_expected_to_be_in_situation()
                if sims_in_situation is None:
                    logger.error('Trying to get expected Sims for situation {} that does not provide that information.  Treating as a single Sim.  This situation does not support this behavior.  Contact your GPE partner to fix this.', situation, owner='jjacobson')
                    sims_in_situation = 1
                current_count += sims_in_situation
        else:
            current_count = len(situation_ids)
        op = SituationChurnOperation.DO_NOTHING
        situation_to_start = None
        if number_situations_desire > current_count:
            reserved_object_relationships = 0
            if reserve_object_relationships:
                reserved_object_relationships = len(situation_ids)
            predicate = lambda situation: self.can_schedule_situation(situation, limit_based_on_sims=situation_shift.count_based_on_expected_sims, number_of_sims_desired=number_situations_desire - current_count, reserved_object_relationships=reserved_object_relationships)
            additional_situations = []
            for situation_source in situation_shift.additional_sources:
                additional_situations.extend(situation_source.get_additional_situations(predicate=predicate))
            (situation_to_start, params) = situation_shift.shift_curve.get_situation_and_params(predicate=predicate, additional_situations=additional_situations)
            if situation_to_start is not None:
                op = SituationChurnOperation.START_SITUATION
        elif not situation_shift.shift_strictness == SituationShiftStrictness.OVERLAP:
            op = SituationChurnOperation.REMOVE_SITUATION
        if op == SituationChurnOperation.START_SITUATION:
            if situation_to_start is not None:
                guest_list = situation_to_start.get_predefined_guest_list()
                if guest_list is None:
                    guest_list = self._get_default_guest_list()
                try:
                    creation_source = self.instance_name
                except:
                    creation_source = str(self)
                situation_id = situation_manager.create_situation(situation_to_start, guest_list=guest_list, spawn_sims_during_zone_spin_up=True, creation_source=creation_source, **params)
                if situation_id is not None:
                    situation_ids.append(situation_id)
            self._situation_shifts_to_situation_ids[situation_shift] = situation_ids
        elif op == SituationChurnOperation.REMOVE_SITUATION:
            time_of_day = services.time_service().sim_now
            situations = [situation_manager.get(situation_id) for situation_id in situation_ids]
            situations.sort(key=lambda x: time_of_day - x.situation_start_time, reverse=True)
            situation_to_remove = next(iter(situations))
            if situation_to_remove is not None:
                logger.debug('Situation Churn Alarm Callback: Removing Situation: {}', situation_to_remove)
                situation_manager.destroy_situation_by_id(situation_to_remove.id)

    def _save_custom_zone_director(self, zone_director_proto, writer):
        self._save_situation_shifts(zone_director_proto, writer)
        super()._save_custom_zone_director(zone_director_proto, writer)

    def _load_custom_zone_director(self, zone_director_proto, reader):
        self._load_situation_shifts(zone_director_proto, reader)
        super()._load_custom_zone_director(zone_director_proto, reader)

    def _save_situation_shifts(self, zone_director_proto, writer):
        for (index, situation_shift) in enumerate(self.situation_shifts):
            situation_ids = self._situation_shifts_to_situation_ids.get(situation_shift, [])
            situation_ids = self._prune_stale_situations(situation_ids)
            if situation_ids:
                situation_data_proto = zone_director_proto.situations.add()
                situation_data_proto.situation_list_guid = index
                situation_data_proto.situation_ids.extend(situation_ids)

    def _load_situation_shifts(self, zone_director_proto, reader):
        for situation_data_proto in zone_director_proto.situations:
            if situation_data_proto.situation_list_guid >= len(self.situation_shifts):
                pass
            else:
                situation_shift = self.situation_shifts[situation_data_proto.situation_list_guid]
                situation_ids = []
                situation_ids.extend(situation_data_proto.situation_ids)
                self._situation_shifts_to_situation_ids[situation_shift] = situation_ids

    def save_situation_shifts(self, proto):
        self._save_situation_shifts(proto, None)

    def load_situation_shifts(self, proto):
        self._load_situation_shifts(proto, None)

class SchedulingZoneDirector(FanZoneDirectorMixin, ObjectBasedSituationZoneDirectorMixin, SchedulingZoneDirectorMixin, ZoneDirectorBase):
    pass
