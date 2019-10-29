from date_and_time import TimeSpanfrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom event_testing.tests import TunableTestSetfrom sims4.callback_utils import CallableListfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableList, TunableRange, TunableSimMinute, TunablePackSafeReference, TunableReference, TunableSet, TunableEnumEntryfrom sims4.utils import classpropertyfrom tag import Tagfrom ui.ui_dialog import UiDialogOkimport alarmsimport build_buyimport date_and_timeimport persistence_error_typesimport servicesimport sims4
class CurfewService(Service):
    ALLOWED_CURFEW_TIMES = TunableList(description='\n        A list of times (in military time) that are allowed to be set as curfew\n        times.\n        \n        NOTE: Many objects will have curfew components and will only support\n        a visual of certain values. Changing these values without making sure\n        the art supports the value will not work properly. Please only change\n        these values if you know for sure they need to be changed and are \n        getting support from modelling to make the change.\n        ', tunable=TunableRange(description='\n            The hour for which the curfew will be set to.\n            ', tunable_type=int, default=0, minimum=0, maximum=23))
    CURFEW_END_TIME = TunableRange(description='\n        The time when the curfew is considered to be over and the Sims are \n        no longer subject to it.\n        \n        This should probably be set to some time in the morning. 6am perhaps.\n        ', tunable_type=int, default=0, minimum=0, maximum=23)
    MINUTES_BEFORE_CURFEW_WARNING = TunableSimMinute(description='\n        The minutes before the curfew starts that a Sim should receive a \n        warning about the curfew being about to start.\n        ', default=30)
    BREAK_CURFEW_WARNING = TunableLocalizedStringFactory(description='\n        The string that is used to warn the player that a pie menu action will\n        cause the Sim to break curfew. This will wrap around the name of the \n        interaction so should be tuned to something like [Warning] {0.String}.\n        ')
    CURFEW_WARNING_TEXT_MESSAGE_DIALOG = UiDialogOk.TunableFactory(description='\n        The dialog to display as a text message when warning a Sim that their\n        curfew is about to expire.\n        ')
    CURFEW_WARNING_SIM_TESTS = TunableTestSet(description='\n        Tests to run on each of the Sims to determine if they should receive\n        the curfew warning text message or not.\n        ')
    BREAK_CURFEW_BUFF = TunablePackSafeReference(description="\n        The buff that get's added to a Sim that breaks curfew. This buff will\n        enable the Sim to be disciplined for their behavior.\n        ", manager=services.buff_manager())
    INTERACTION_BLACKLIST_TAGS = TunableSet(description='\n        A list of all the tags that blacklist interactions from causing Sims to\n        break curfew.\n        ', tunable=TunableEnumEntry(description='\n            A tag that when tagged on the interaction will allow the Sim to run\n            the interaction and not break curfew.\n            ', tunable_type=Tag, default=Tag.INVALID, pack_safe=True))
    CURFEW_BEGIN_LOOT = TunablePackSafeReference(description='\n        The loot to apply to all Sims in the family when curfew begins. This\n        will allow us to give buffs that affect the behavior of the Sims if\n        they pass certain tests.\n        ', manager=services.get_instance_manager(sims4.resources.Types.ACTION))
    CURFEW_END_LOOT = TunablePackSafeReference(description='\n        The loot to apply to all Sims in the family when curfew ends. This will\n        allow us to remove buffs that affect the behavior of the Sims.\n        ', manager=services.get_instance_manager(sims4.resources.Types.ACTION))
    UNSET = -1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zone_curfew_data = {}
        self._curfew_warning_alarm_handle = None
        self._curfew_started_alarm_handle = None
        self._curfew_ended_alarm_handle = None
        self._curfew_message_alarm_handle = None
        self._curfew_warning_callback = CallableList()
        self._curfew_started_callback = CallableList()
        self._curfew_ended_callback = CallableList()
        self._time_set_callback = CallableList()

    def get_zone_curfew(self, zone_id):
        curfew_setting = self._zone_curfew_data.get(zone_id, self.UNSET)
        return curfew_setting

    def set_zone_curfew(self, zone_id, curfew_setting):
        if self._zone_curfew_data.get(zone_id, None) == curfew_setting:
            return
        if curfew_setting not in CurfewService.ALLOWED_CURFEW_TIMES and curfew_setting != CurfewService.UNSET:
            return
        self._zone_curfew_data[zone_id] = curfew_setting
        self._update_curfew_settings(zone_id, curfew_setting)
        self._setup_curfew_text_message()

    def _update_curfew_settings(self, current_zone_id, current_setting):
        self._create_alarm_handles(current_zone_id)
        self._time_set_callback(current_setting)

    def _create_alarm_handles(self, zone_id):
        for alarm in (self._curfew_warning_alarm_handle, self._curfew_started_alarm_handle, self._curfew_ended_alarm_handle):
            if alarm is not None:
                alarms.cancel_alarm(alarm)
        time = self._zone_curfew_data.get(zone_id, self.UNSET)
        now = services.time_service().sim_now
        self._create_warning_callback(now, time)
        self._create_curfew_callback(now, time)
        self._create_curfew_ended_callback(now, time)

    def _create_warning_callback(self, now, time):
        if time is not CurfewService.UNSET:
            alarm_time = date_and_time.create_date_and_time(hours=time - 1)
            warning_span = now.time_till_next_day_time(alarm_time)
            if warning_span.in_ticks() == 0:
                warning_span += TimeSpan(date_and_time.sim_ticks_per_day())
            self._curfew_warning_alarm_handle = alarms.add_alarm(self, warning_span, self._handle_warning_callback, False)

    def _handle_warning_callback(self, handle):
        self._curfew_warning_callback()
        now = services.time_service().sim_now
        time = self._zone_curfew_data.get(services.current_zone_id(), CurfewService.UNSET)
        self._create_warning_callback(now, time)

    def _create_curfew_callback(self, now, time):
        if time is not self.UNSET:
            alarm_time = date_and_time.create_date_and_time(hours=time)
            curfew_span = now.time_till_next_day_time(alarm_time)
            if curfew_span.in_ticks() == 0:
                curfew_span += TimeSpan(date_and_time.sim_ticks_per_day())
            self._curfew_started_alarm_handle = alarms.add_alarm(self, curfew_span, self._handle_curfew_callback, False)

    def _handle_curfew_callback(self, handle):
        self._curfew_started_callback()
        now = services.time_service().sim_now
        time = self._zone_curfew_data.get(services.current_zone_id(), CurfewService.UNSET)
        self.apply_curfew_loots()
        self._create_curfew_callback(now, time)

    def _create_curfew_ended_callback(self, now, time):
        if time is not CurfewService.UNSET:
            alarm_time = date_and_time.create_date_and_time(hours=CurfewService.CURFEW_END_TIME)
            curfew_span = now.time_till_next_day_time(alarm_time)
            if curfew_span.in_ticks() == 0:
                curfew_span += TimeSpan(date_and_time.sim_ticks_per_day())
            self._curfew_ended_alarm_handle = alarms.add_alarm(self, curfew_span, self._handle_curfew_ended_callback, False)

    def _handle_curfew_ended_callback(self, handle):
        self._curfew_ended_callback()
        now = services.time_service().sim_now
        time = CurfewService.CURFEW_END_TIME
        self.remove_curfew_loots()
        self._create_curfew_ended_callback(now, time)

    def register_for_alarm_callbacks(self, warning_callback, curfew_callback, curfew_over_callback, time_set_callback):
        self._curfew_warning_callback.append(warning_callback)
        self._curfew_started_callback.append(curfew_callback)
        self._curfew_ended_callback.append(curfew_over_callback)
        self._time_set_callback.append(time_set_callback)

    def unregister_for_alarm_callbacks(self, warning_callback, curfew_callback, curfew_over_callback, time_set_callback):
        if warning_callback in self._curfew_warning_callback:
            self._curfew_warning_callback.remove(warning_callback)
        if curfew_callback in self._curfew_started_callback:
            self._curfew_started_callback.remove(curfew_callback)
        if curfew_over_callback in self._curfew_ended_callback:
            self._curfew_ended_callback.remove(curfew_over_callback)
        if time_set_callback in self._time_set_callback:
            self._time_set_callback.remove(time_set_callback)

    def sim_breaking_curfew(self, sim, target, interaction=None):
        if interaction is not None and self.interaction_blacklisted(interaction):
            return False
        if sim.sim_info.is_in_travel_group():
            return False
        situation_manager = services.get_zone_situation_manager()
        sim_situations = situation_manager.get_situations_sim_is_in(sim)
        if any(situation.disallows_curfew_violation for situation in sim_situations):
            return False
        active_household = services.active_household()
        if active_household is None:
            return False
        home_zone_id = active_household.home_zone_id
        curfew_setting = self._zone_curfew_data.get(home_zone_id, CurfewService.UNSET)
        if sim.sim_info not in active_household:
            return False
        if curfew_setting is not CurfewService.UNSET:
            if sim.sim_info.is_young_adult_or_older:
                return False
            elif self.past_curfew(curfew_setting):
                if not services.current_zone_id() == home_zone_id:
                    ensemble_service = services.ensemble_service()
                    ensemble = ensemble_service.get_visible_ensemble_for_sim(sim)
                    if ensemble is not None and any(sim.sim_info.is_young_adult_or_older and sim.sim_info in active_household for sim in ensemble):
                        return False
                    return True
                if target is not None and not (target.is_in_inventory() or services.active_lot().is_position_on_lot(target.position)):
                    return True
                elif target is None and not services.active_lot().is_position_on_lot(sim.position):
                    return True
            return True
            if target is not None and not (target.is_in_inventory() or services.active_lot().is_position_on_lot(target.position)):
                return True
            elif target is None and not services.active_lot().is_position_on_lot(sim.position):
                return True
        return False

    def interaction_blacklisted(self, interaction):
        interaction_tags = interaction.get_category_tags()
        for tag in CurfewService.INTERACTION_BLACKLIST_TAGS:
            if tag in interaction_tags:
                return True
        return False

    def past_curfew(self, curfew_setting):
        now = services.time_service().sim_now
        if now.hour() >= curfew_setting or now.hour() < CurfewService.CURFEW_END_TIME:
            return True
        return False

    def _setup_curfew_text_message(self):
        if self._curfew_message_alarm_handle is not None:
            self._curfew_message_alarm_handle.cancel()
            self._curfew_message_alarm_handle = None
        current_household = services.active_household()
        home_zone_id = current_household.home_zone_id
        curfew_setting = self._zone_curfew_data.get(home_zone_id, CurfewService.UNSET)
        if curfew_setting is CurfewService.UNSET:
            return
        now = services.time_service().sim_now
        alarm_time = date_and_time.create_date_and_time(hours=curfew_setting)
        time_till_alarm = now.time_till_next_day_time(alarm_time)
        span = date_and_time.create_time_span(minutes=CurfewService.MINUTES_BEFORE_CURFEW_WARNING)
        time_till_alarm -= span
        self._curfew_message_alarm_handle = alarms.add_alarm(self, time_till_alarm, self._handle_curfew_message_callback, False)

    def _handle_curfew_message_callback(self, handle):
        active_lot = services.active_lot()
        if active_lot.lot_id != services.active_household_lot_id():
            from_sim = None
            for sim_info in services.active_household():
                if sim_info.is_young_adult_or_older and not sim_info.is_instanced():
                    from_sim = sim_info
                    break
            if from_sim is None:
                return
            for sim_info in services.active_household():
                if sim_info.get_sim_instance() is None:
                    pass
                else:
                    resolver = DoubleSimResolver(sim_info, from_sim)
                    if not CurfewService.CURFEW_WARNING_SIM_TESTS.run_tests(resolver):
                        pass
                    else:
                        dialog = self.CURFEW_WARNING_TEXT_MESSAGE_DIALOG(sim_info, target_sim_id=from_sim.id, resolver=resolver)
                        dialog.show_dialog()

    def add_broke_curfew_buff(self, sim):
        if not sim.has_buff(CurfewService.BREAK_CURFEW_BUFF):
            sim.add_buff(CurfewService.BREAK_CURFEW_BUFF)

    def remove_broke_curfew_buff(self, sim):
        if sim.has_buff(CurfewService.BREAK_CURFEW_BUFF):
            sim.remove_buff_by_type(CurfewService.BREAK_CURFEW_BUFF)

    def is_curfew_active_on_lot_id(self, lot_id):
        curfew_setting = self._zone_curfew_data.get(lot_id, CurfewService.UNSET)
        if curfew_setting == CurfewService.UNSET:
            return False
        return self.past_curfew(curfew_setting)

    def apply_curfew_loots(self):
        for sim_info in services.active_household():
            resolver = SingleSimResolver(sim_info)
            CurfewService.CURFEW_BEGIN_LOOT.apply_to_resolver(resolver)

    def remove_curfew_loots(self):
        for sim_info in services.active_household():
            resolver = SingleSimResolver(sim_info)
            CurfewService.CURFEW_END_LOOT.apply_to_resolver(resolver)

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_CURFEW_SERVICE

    def save(self, object_list=None, zone_data=None, open_street_data=None, store_travel_group_placed_objects=False, save_slot_data=None):
        persistence_service = services.get_persistence_service()
        for save_zone_data in persistence_service.zone_proto_buffs_gen():
            setting = self._zone_curfew_data.get(save_zone_data.zone_id, CurfewService.UNSET)
            save_zone_data.gameplay_zone_data.curfew_setting = setting

    def load(self, zone_data=None):
        persistence_service = services.get_persistence_service()
        for zone_data in persistence_service.zone_proto_buffs_gen():
            self._zone_curfew_data[zone_data.zone_id] = zone_data.gameplay_zone_data.curfew_setting

    def on_zone_load(self):
        current_zone_id = services.current_zone_id()
        self._setup_curfew_text_message()
        self._create_alarm_handles(current_zone_id)
        venue_manager = services.get_instance_manager(sims4.resources.Types.VENUE)
        venue_type = venue_manager.get(build_buy.get_current_venue(current_zone_id))
        if venue_type.is_residential:
            current_setting = self._zone_curfew_data.get(current_zone_id, CurfewService.UNSET)
            self._update_curfew_settings(current_zone_id, current_setting)
        else:
            self._update_curfew_settings(current_zone_id, CurfewService.UNSET)
