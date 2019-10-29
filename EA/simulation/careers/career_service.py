from _collections import dequefrom collections import namedtuplefrom random import Randomimport mathimport randomfrom date_and_time import TimeSpanfrom objects import ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZEDfrom sims4.localization import LocalizationHelperTuningfrom sims4.math import MAX_UINT64from sims4.service_manager import Servicefrom sims4.utils import classpropertyfrom ui.ui_dialog import ButtonTypeimport game_servicesimport persistence_error_typesimport servicesimport sims4.loglogger = sims4.log.Logger('Career Save Game Data')_PendingCareerEvent = namedtuple('_PendingCareerEvent', ('career', 'career_event', 'on_accepted', 'on_canceled'))
class CareerService(Service):

    def __init__(self):
        self._shuffled_career_list = None
        self._career_list_seed = None
        self._last_day_updated = None
        self._pending_career_events = deque()
        self._main_career_event_zone_id = None
        self._save_lock = None
        self.enabled = True

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_CAREER_SERVICE

    def start(self):
        services.venue_service().on_venue_type_changed.register(self._remove_invalid_careers)
        return super().start()

    def stop(self):
        services.venue_service().on_venue_type_changed.unregister(self._remove_invalid_careers)
        return super().stop()

    def load(self, zone_data=None):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        if save_slot_data_msg.gameplay_data.HasField('career_choices_seed'):
            self._career_list_seed = save_slot_data_msg.gameplay_data.career_choices_seed

    def save(self, object_list=None, zone_data=None, open_street_data=None, store_travel_group_placed_objects=False, save_slot_data=None):
        if self._career_list_seed is not None:
            save_slot_data.gameplay_data.career_choices_seed = self._career_list_seed
        if game_services.service_manager.is_traveling:
            manager = services.sim_info_manager()
            for sim_info in manager.get_all():
                tracker = sim_info.career_tracker
                if tracker is not None:
                    for career in tracker.careers.values():
                        career.update_should_restore_state()

    def _remove_invalid_careers(self):
        for sim_info in services.sim_info_manager().get_all():
            if sim_info.career_tracker is None:
                pass
            else:
                sim_info.career_tracker.remove_invalid_careers()

    def get_days_from_time(self, time):
        return math.floor(time.absolute_days())

    def get_seed(self, days_now):
        if self._career_list_seed is None:
            self._career_list_seed = random.randint(0, MAX_UINT64)
        return self._career_list_seed + days_now

    def get_career_list(self):
        career_list = []
        career_manager = services.get_instance_manager(sims4.resources.Types.CAREER)
        for career_id in career_manager.types:
            career_tuning = career_manager.get(career_id)
            career_list.append(career_tuning)
        return career_list

    def get_shuffled_career_list(self):
        time_now = services.time_service().sim_now
        days_now = self.get_days_from_time(time_now)
        if self._shuffled_career_list is None or self._last_day_updated != days_now:
            career_seed = self.get_seed(days_now)
            career_rand = Random(career_seed)
            self._last_day_updated = days_now
            self._shuffled_career_list = self.get_career_list()
            career_rand.shuffle(self._shuffled_career_list)
        return self._shuffled_career_list

    def get_random_career_type_for_sim(self, sim_info):
        career_types = tuple(career_type for career_type in self.get_career_list() if career_type.is_valid_career(sim_info=sim_info))
        if career_types:
            return random.choice(career_types)

    def restore_career_state(self):
        try:
            manager = services.sim_info_manager()
            zone = services.current_zone()
            zone_id = zone.id
            zone_restored_sis = zone.should_restore_sis()
            for sim_info in manager.get_all():
                if zone_restored_sis and sim_info.has_loaded_si_state:
                    pass
                else:
                    sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED)
                    if sim_info.is_npc:
                        if sim is not None and sim_info.can_go_to_work(zone_id=zone_id):
                            for career in sim_info.careers.values():
                                (time_to_work, start_time, end_time) = career.get_next_work_time(check_if_can_go_now=True)
                                if time_to_work is not None and time_to_work == TimeSpan.ZERO and career.should_restore_career_state:
                                    sim.set_allow_route_instantly_when_hitting_marks(True)
                                    career.start_new_career_session(start_time, end_time)
                                    result = career.push_go_to_work_affordance()
                                    if result:
                                        manager.set_sim_to_skip_preroll(sim_info.id)
                                    break
                            career = sim_info.career_tracker.career_currently_within_hours
                            if career is None:
                                pass
                            elif career.is_at_active_event:
                                if not career.career_event_manager.is_valid_zone_id(sim_info.zone_id):
                                    career.end_career_event_without_payout()
                                    if career.currently_at_work and not sim_info.can_go_to_work(zone_id=sim_info.zone_id):
                                        career.leave_work(left_early=True)
                                    if sim is not None:
                                        if career.currently_at_work and career.push_go_to_work_affordance():
                                            sim.set_allow_route_instantly_when_hitting_marks(True)
                                            manager.set_sim_to_skip_preroll(sim_info.id)
                                            if career.should_restore_career_state:
                                                if sim_info.household.home_zone_id != sim_info.zone_id:
                                                    career.send_uninstantiated_sim_home_for_work()
                                                else:
                                                    career.attend_work()
                                    elif career.should_restore_career_state:
                                        if sim_info.household.home_zone_id != sim_info.zone_id:
                                            career.send_uninstantiated_sim_home_for_work()
                                        else:
                                            career.attend_work()
                            else:
                                if career.currently_at_work and not sim_info.can_go_to_work(zone_id=sim_info.zone_id):
                                    career.leave_work(left_early=True)
                                if sim is not None:
                                    if career.currently_at_work and career.push_go_to_work_affordance():
                                        sim.set_allow_route_instantly_when_hitting_marks(True)
                                        manager.set_sim_to_skip_preroll(sim_info.id)
                                        if career.should_restore_career_state:
                                            if sim_info.household.home_zone_id != sim_info.zone_id:
                                                career.send_uninstantiated_sim_home_for_work()
                                            else:
                                                career.attend_work()
                                elif career.should_restore_career_state:
                                    if sim_info.household.home_zone_id != sim_info.zone_id:
                                        career.send_uninstantiated_sim_home_for_work()
                                    else:
                                        career.attend_work()
                    else:
                        career = sim_info.career_tracker.career_currently_within_hours
                        if career is None:
                            pass
                        elif career.is_at_active_event:
                            if not career.career_event_manager.is_valid_zone_id(sim_info.zone_id):
                                career.end_career_event_without_payout()
                                if career.currently_at_work and not sim_info.can_go_to_work(zone_id=sim_info.zone_id):
                                    career.leave_work(left_early=True)
                                if sim is not None:
                                    if career.currently_at_work and career.push_go_to_work_affordance():
                                        sim.set_allow_route_instantly_when_hitting_marks(True)
                                        manager.set_sim_to_skip_preroll(sim_info.id)
                                        if career.should_restore_career_state:
                                            if sim_info.household.home_zone_id != sim_info.zone_id:
                                                career.send_uninstantiated_sim_home_for_work()
                                            else:
                                                career.attend_work()
                                elif career.should_restore_career_state:
                                    if sim_info.household.home_zone_id != sim_info.zone_id:
                                        career.send_uninstantiated_sim_home_for_work()
                                    else:
                                        career.attend_work()
                        else:
                            if career.currently_at_work and not sim_info.can_go_to_work(zone_id=sim_info.zone_id):
                                career.leave_work(left_early=True)
                            if sim is not None:
                                if career.currently_at_work and career.push_go_to_work_affordance():
                                    sim.set_allow_route_instantly_when_hitting_marks(True)
                                    manager.set_sim_to_skip_preroll(sim_info.id)
                                    if career.should_restore_career_state:
                                        if sim_info.household.home_zone_id != sim_info.zone_id:
                                            career.send_uninstantiated_sim_home_for_work()
                                        else:
                                            career.attend_work()
                            elif career.should_restore_career_state:
                                if sim_info.household.home_zone_id != sim_info.zone_id:
                                    career.send_uninstantiated_sim_home_for_work()
                                else:
                                    career.attend_work()
        except:
            logger.exception('Exception raised while trying to restore career interactions.', owner='tingyul')

    def create_career_event_situations_during_zone_spin_up(self):
        try:
            active_household = services.active_household()
            if active_household is None:
                return
            current_zone_id = services.current_zone_id()
            for sim_info in active_household:
                if sim_info.zone_id == current_zone_id:
                    career = sim_info.career_tracker.career_currently_within_hours
                    if career is not None:
                        career.create_career_event_situations_during_zone_spin_up()
        except:
            logger.exception('Exception raised while trying to restore career event.', owner='tingyul')

    def get_career_in_career_event(self):
        active_household = services.active_household()
        if active_household is not None:
            for sim_info in active_household:
                career = sim_info.career_tracker.get_at_work_career()
                if career is not None and career.is_at_active_event:
                    return career

    def add_pending_career_event_offer(self, career, career_event, on_accepted, on_canceled):
        pending = _PendingCareerEvent(career=career, career_event=career_event, on_accepted=on_accepted, on_canceled=on_canceled)
        self._pending_career_events.append(pending)
        if len(self._pending_career_events) == 1:
            self._try_offer_next_career_event()

    def _try_offer_next_career_event(self):
        if self._pending_career_events:
            pending = self._pending_career_events[0]
            pending.career.send_career_message(pending.career.career_messages.career_event_confirmation_dialog, on_response=self._on_career_event_response, auto_response=ButtonType.DIALOG_RESPONSE_OK)

    def _on_career_event_response(self, dialog):
        pending = self._pending_career_events.popleft()
        if dialog.accepted:
            self._cancel_pending_career_events()
            pending.on_accepted(pending.career_event)
        else:
            self._try_offer_next_career_event()
            pending.on_canceled(pending.career_event)

    def _cancel_pending_career_events(self):
        for pending in self._pending_career_events:
            pending.on_canceled(pending.career_event)
        self._pending_career_events.clear()

    def get_career_event_situation_is_running(self):
        career = self.get_career_in_career_event()
        if career is not None:
            manager = career.career_event_manager
            if manager is not None and manager.scorable_situation_id is not None:
                return True
        return False

    def set_main_career_event_zone_id_and_lock_save(self, main_zone_id):

        class _SaveLock:

            def get_lock_save_reason(self):
                return LocalizationHelperTuning.get_raw_text('')

        self._save_lock = _SaveLock()
        services.get_persistence_service().lock_save(self._save_lock)
        self._main_career_event_zone_id = main_zone_id

    def get_main_career_event_zone_id_and_unlock_save(self):
        if self._save_lock is not None:
            services.get_persistence_service().unlock_save(self._save_lock)
            self._save_lock = None
        zone_id = self._main_career_event_zone_id
        self._main_career_event_zone_id = None
        return zone_id
