import itertoolsimport protocolbuffersfrom careers.career_custom_data import CustomCareerDatafrom careers.career_enums import WORK_CAREER_CATEGORIES, CareerCategoryfrom careers.career_history import CareerHistoryfrom careers.career_tuning import Careerfrom careers.retirement import Retirementfrom careers.career_enums import CareerShiftTypefrom date_and_time import DATE_AND_TIME_ZEROfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimResolverfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom singletons import DEFAULTimport distributorimport servicesimport sims4.resourceslogger = sims4.log.Logger('CareerTracker')
class CareerTracker(SimInfoTracker):

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._careers = {}
        self._career_history = {}
        self._retirement = None
        self._custom_data = None

    def __iter__(self):
        return iter(self._careers.values())

    @property
    def careers(self):
        return self._careers

    @property
    def custom_career_data(self):
        return self._custom_data

    def resend_career_data(self):
        if services.current_zone().is_zone_shutting_down:
            return
        if not self._sim_info.valid_for_distribution:
            return
        op = distributor.ops.SetCareers(self)
        distributor.system.Distributor.instance().add_op(self._sim_info, op)
        careers = self.careers
        for career in careers.values():
            career.send_prep_task_update()

    def _at_work_infos(self):
        at_work_infos = []
        for career in self._careers.values():
            at_work_infos.append(career.create_work_state_msg())
        return at_work_infos

    def resend_at_work_infos(self):
        if self._sim_info.is_npc:
            return
        op = distributor.ops.SetAtWorkInfos(self._at_work_infos())
        distributor.system.Distributor.instance().add_op(self._sim_info, op)

    @property
    def has_custom_career(self):
        return self._custom_data is not None

    @property
    def has_career(self):
        return bool(self._careers)

    def has_career_outfit(self):
        return any(career.has_outfit() for career in self._careers.values())

    def has_part_time_career_outfit(self):
        return any(career.has_outfit() and career.career_category == CareerCategory.AdultPartTime for career in self._careers.values())

    def _on_confirmation_dialog_response(self, dialog, new_career, schedule_shift_override=CareerShiftType.ALL_DAY):
        if dialog.accepted:
            self.add_career(new_career, schedule_shift_override=schedule_shift_override)

    def set_custom_career_data(self, **kwargs):
        if self._custom_data is None:
            self._custom_data = CustomCareerData()
        self._custom_data.set_custom_career_data(**kwargs)
        register_loot = Career.CUSTOM_CAREER_REGISTER_LOOT
        register_loot.apply_to_resolver(SingleSimResolver(self._sim_info))
        self.resend_career_data()

    def remove_custom_career_data(self, send_update=True):
        if self._custom_data is None:
            return
        self._custom_data = None
        unregister_loot = Career.CUSTOM_CAREER_UNREGISTER_LOOT
        unregister_loot.apply_to_resolver(SingleSimResolver(self._sim_info))
        if send_update:
            self.resend_career_data()

    def add_career(self, new_career, show_confirmation_dialog=False, user_level_override=None, career_level_override=None, give_skipped_rewards=True, defer_rewards=False, post_quit_msg=True, schedule_shift_override=CareerShiftType.ALL_DAY, show_join_msg=True, disallowed_reward_types=(), force_rewards_to_sim_info_inventory=False, defer_first_assignment=False):
        if show_confirmation_dialog:
            (level, _, track) = new_career.get_career_entry_data(career_history=self._career_history, user_level_override=user_level_override, career_level_override=career_level_override)
            career_level_tuning = track.career_levels[level]
            if self._retirement is not None:
                self._retirement.send_dialog(Career.UNRETIRE_DIALOG, career_level_tuning.title(self._sim_info), icon_override=DEFAULT, on_response=lambda dialog: self._on_confirmation_dialog_response(dialog, new_career, schedule_shift_override=schedule_shift_override))
                return
            if new_career.can_quit:
                quittable_careers = self.get_quittable_careers(schedule_shift_type=schedule_shift_override)
                if quittable_careers:
                    career = next(iter(quittable_careers.values()))
                    switch_jobs_dialog = Career.SWITCH_JOBS_DIALOG
                    if len(quittable_careers) > 1:
                        switch_jobs_dialog = Career.SWITCH_MANY_JOBS_DIALOG
                    career.send_career_message(switch_jobs_dialog, career_level_tuning.title(self._sim_info), icon_override=DEFAULT, on_response=lambda dialog: self._on_confirmation_dialog_response(dialog, new_career, schedule_shift_override=schedule_shift_override))
                    return
        self.end_retirement()
        self.remove_custom_career_data(send_update=False)
        if new_career.guid64 in self._careers:
            logger.callstack('Attempting to add career {} sim {} is already in.', new_career, self._sim_info)
            return
        if new_career.can_quit:
            self.quit_quittable_careers(post_quit_msg=post_quit_msg, schedule_shift_type=schedule_shift_override)
        self._careers[new_career.guid64] = new_career
        new_career.join_career(career_history=self._career_history, user_level_override=user_level_override, career_level_override=career_level_override, give_skipped_rewards=give_skipped_rewards, defer_rewards=defer_rewards, schedule_shift_override=schedule_shift_override, show_join_msg=show_join_msg, disallowed_reward_types=disallowed_reward_types, force_rewards_to_sim_info_inventory=force_rewards_to_sim_info_inventory, defer_first_assignment=defer_first_assignment)
        self.resend_career_data()

    def remove_career(self, career_uid, post_quit_msg=True):
        if career_uid in self._careers:
            career = self._careers[career_uid]
            career.career_stop()
            career.quit_career(post_quit_msg=post_quit_msg)
            career.on_career_removed(self._sim_info)

    def remove_invalid_careers(self):
        for (career_uid, career) in list(self._careers.items()):
            if not career.is_valid_career():
                self.remove_career(career_uid, post_quit_msg=False)

    def add_ageup_careers(self):
        for career in list(self._careers.values()):
            if career.current_level_tuning.ageup_branch_career is not None:
                new_career = career.current_level_tuning.ageup_branch_career(self._sim_info)
                default_shift_type = CareerShiftType.EVENING
                if career.schedule_shift_type != CareerShiftType.ALL_DAY:
                    default_shift_type = career.schedule_shift_type
                self.add_career(new_career, user_level_override=career.user_level, post_quit_msg=False, schedule_shift_override=default_shift_type, show_join_msg=False)

    def get_career_by_uid(self, career_uid):
        if career_uid in self._careers:
            return self._careers[career_uid]

    def has_career_by_uid(self, career_uid):
        return career_uid in self._careers

    def get_career_by_category(self, career_category):
        for career in self:
            if career.career_category == career_category:
                return career

    def has_work_career(self):
        return any(career.career_category in WORK_CAREER_CATEGORIES for career in self)

    def has_quittable_career(self):
        if self.get_quittable_careers():
            return True
        return False

    def get_quittable_careers(self, schedule_shift_type=CareerShiftType.ALL_DAY):
        quittable_careers = dict((uid, career) for (uid, career) in self._careers.items() if career.can_quit and career.get_is_quittable_shift(schedule_shift_type))
        return quittable_careers

    def quit_quittable_careers(self, post_quit_msg=True, schedule_shift_type=CareerShiftType.ALL_DAY):
        for career_uid in self.get_quittable_careers(schedule_shift_type):
            self.remove_career(career_uid, post_quit_msg=post_quit_msg)

    def get_at_work_career(self):
        for career in self._careers.values():
            if career.currently_at_work:
                return career

    def get_on_assignment_career(self):
        for career in self._careers.values():
            if career.on_assignment:
                return career

    @property
    def currently_at_work(self):
        for career in self._careers.values():
            if career.currently_at_work:
                return True
        return False

    @property
    def currently_during_work_hours(self):
        for career in self._careers.values():
            if career.is_work_time:
                return True
        return False

    @property
    def career_currently_within_hours(self):
        for career in self._careers.values():
            if career.is_work_time:
                return career

    def get_currently_at_work_career(self):
        for career in self._careers.values():
            if career.currently_at_work:
                return career

    def career_leave(self, career):
        self.update_history(career, from_leave=True)
        del self._careers[career.guid64]

    def get_all_career_aspirations(self):
        return tuple(itertools.chain.from_iterable(career.get_all_aspirations() for career in self._careers.values()))

    @property
    def career_history(self):
        return self._career_history

    def update_history(self, career, from_leave=False):
        highest_level = self.get_highest_level_reached(career.guid64)
        if career.user_level > highest_level:
            highest_level = career.user_level
        time_of_leave = services.time_service().sim_now if from_leave else DATE_AND_TIME_ZERO
        self._career_history[career.guid64] = CareerHistory(career_track=career.current_track_tuning, level=career.level, user_level=career.user_level, overmax_level=career.overmax_level, highest_level=highest_level, time_of_leave=time_of_leave, daily_pay=career.get_daily_pay(), days_worked=career.days_worked_statistic.get_value(), active_days_worked=career.active_days_worked_statistic.get_value(), player_rewards_deferred=career.player_rewards_deferred, schedule_shift_type=career.schedule_shift_type)

    def get_highest_level_reached(self, career_uid):
        entry = self._career_history.get(career_uid)
        if entry is not None:
            return entry.highest_level
        return 0

    @property
    def retirement(self):
        return self._retirement

    def retire_career(self, career_uid):
        for uid in list(self._careers):
            self.remove_career(uid, post_quit_msg=False)
        self._retirement = Retirement(self._sim_info, career_uid)
        self._retirement.start(send_retirement_notification=True)

    def end_retirement(self):
        if self._retirement is not None:
            self._retirement.stop()
            self._retirement = None

    @property
    def retired_career_uid(self):
        if self._retirement is not None:
            return self._retirement.career_uid
        return 0

    def start_retirement(self):
        if self._retirement is not None:
            self._retirement.start()

    def set_gig(self, gig, gig_time, gig_customer=None):
        gig_career = self.get_career_by_uid(gig.career.guid64)
        if gig_career is None:
            logger.error("Tried to set gig {} for career {} on sim {} but sim doesn't have career.", gig, gig.career, self._sim_info)
            return
        gig_career.set_gig(gig, gig_time, gig_customer=gig_customer)
        self.resend_career_data()

    def on_sim_added_to_skewer(self):
        for career in self._careers.values():
            career_history = self._career_history.get(career.guid64, None)
            if career_history is not None and career_history.deferred_rewards:
                career.award_deferred_promotion_rewards()
        self.resend_career_data()
        self.resend_at_work_infos()

    def on_loading_screen_animation_finished(self):
        for career in self._careers.values():
            career.on_loading_screen_animation_finished()

    def on_zone_unload(self):
        for career in self._careers.values():
            career.on_zone_unload()

    def on_zone_load(self):
        self.start_retirement()
        for career in self._careers.values():
            career.on_zone_load()

    def on_sim_startup(self):
        for career in self._careers.values():
            career.startup_career()

    def on_death(self):
        for (uid, career) in list(self._careers.items()):
            if career.is_at_active_event:
                career.end_career_event_without_payout()
            self.remove_career(uid, post_quit_msg=False)
        self.end_retirement()

    def clean_up(self):
        for career in self._careers.values():
            career.career_stop()
        self._careers.clear()
        self.end_retirement()

    def on_situation_request(self, situation):
        career = self.get_at_work_career()
        if career is not None:
            if self._sim_info.is_npc:
                career_location = career.get_career_location()
                if services.current_zone_id() == career_location.get_zone_id():
                    return
            if situation.can_remove_sims_from_work and not career.is_at_active_event:
                career.leave_work_early()

    def clear_career_history(self, career_guid):
        if career_guid in self._career_history:
            del self._career_history[career_guid]

    def save(self):
        save_data = protocolbuffers.SimObjectAttributes_pb2.PersistableSimCareers()
        for career in self._careers.values():
            with ProtocolBufferRollback(save_data.careers) as career_proto:
                career_proto.MergeFrom(career.get_persistable_sim_career_proto())
        for (career_uid, career_history) in self._career_history.items():
            with ProtocolBufferRollback(save_data.career_history) as career_history_proto:
                career_history_proto.career_uid = career_uid
                career_history.save_career_history(career_history_proto)
        if self._retirement is not None:
            save_data.retirement_career_uid = self._retirement.career_uid
        if self._custom_data is not None:
            self._custom_data.save_custom_data(save_data)
        return save_data

    def load(self, save_data, skip_load=False):
        self._careers.clear()
        for career_save_data in save_data.careers:
            career_uid = career_save_data.career_uid
            career_type = services.get_instance_manager(sims4.resources.Types.CAREER).get(career_uid)
            if career_type is not None:
                career = career_type(self._sim_info)
                career.load_from_persistable_sim_career_proto(career_save_data, skip_load=skip_load)
                self._careers[career_uid] = career
        self._career_history.clear()
        for history_entry in save_data.career_history:
            if skip_load and history_entry.career_uid not in self._careers:
                pass
            else:
                career_history = CareerHistory.load_career_history(self._sim_info, history_entry)
                self._career_history[history_entry.career_uid] = career_history
                if career_history is not None and career_history.deferred_rewards and history_entry.career_uid in self._careers:
                    self._careers[history_entry.career_uid].defer_player_rewards()
        self._retirement = None
        retired_career_uid = save_data.retirement_career_uid
        if retired_career_uid in self._career_history:
            self._retirement = Retirement(self._sim_info, retired_career_uid)
        if save_data.HasField('custom_career_name'):
            self._custom_data = CustomCareerData()
            self._custom_data.load_custom_data(save_data)

    def activate_career_aspirations(self):
        for career in self._careers.values():
            for aspiration_to_activate in career.aspirations_to_activate:
                aspiration_to_activate.register_callbacks()
                self._sim_info.aspiration_tracker.validate_and_return_completed_status(aspiration_to_activate)
                self._sim_info.aspiration_tracker.process_test_events_for_aspiration(aspiration_to_activate)
            career_aspiration = career._current_track.career_levels[career._level].get_aspiration()
            if career_aspiration is not None:
                career_aspiration.register_callbacks()
                self._sim_info.aspiration_tracker.validate_and_return_completed_status(career_aspiration)
                self._sim_info.aspiration_tracker.process_test_events_for_aspiration(career_aspiration)

    def on_lod_update(self, old_lod, new_lod):
        if new_lod == SimInfoLODLevel.MINIMUM:
            self.clean_up()
