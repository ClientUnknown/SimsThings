from protocolbuffers import Situations_pb2from distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import build_icon_info_msg, IconInfoDatafrom distributor.system import Distributorfrom holidays.holiday_globals import HolidayTuning, TRADITION_PREFERENCE_CARESfrom sims4.localization import LocalizationHelperTuningfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.base_situation import SituationDisplayPriority, _RequestUserDatafrom situations.bouncer.bouncer_request import BouncerRequestFactoryfrom situations.bouncer.bouncer_types import BouncerRequestPriority, BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateData, SituationStatefrom situations.situation_meter import ValueBasedSituationMeterDatafrom situations.situation_types import SituationDisplayType, SituationSerializationOption, SituationUserFacingType, SituationCreationUIOptionimport distributorimport services
class HolidayParticipantRequestFactory(BouncerRequestFactory):

    def __init__(self, situation, callback_data, job_type, exclusivity, sim_id):
        super().__init__(situation, callback_data=callback_data, job_type=job_type, request_priority=BouncerRequestPriority.EVENT_VIP, user_facing=False, exclusivity=exclusivity)
        self._sim_id = sim_id

    def _can_assign_sim_to_request(self, sim):
        return sim.sim_id == self._sim_id

class _HolidaySituationState(SituationState):
    pass

class HolidaySituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'holiday_situation_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The Situation Job and Role State for the Sim celebrating the holiday.\n            ', tuning_group=GroupNames.ROLES), '_progress_meter_settings': ValueBasedSituationMeterData.TunableFactory(description='\n            The meter used to track the holiday score. The min and max value\n            of this meter is locked to 0-100 as the score is reported to UI as\n            a percentage based on the number of traditions a Sim cares about.\n            ', tuning_group=GroupNames.SITUATION, locked_args={'_meter_id': 1})}
    REMOVE_INSTANCE_TUNABLES = ('main_goal', '_main_goal_visibility_test', 'minor_goal_chains', 'main_goal_audio_sting', 'highlight_first_incomplete_minor_goal', 'screen_slam_gold', 'screen_slam_silver', 'screen_slam_bronze', 'screen_slam_no_medal', 'recommended_job_object_notification', 'recommended_job_object_text', '_buff', 'targeted_situation', '_resident_job', '_relationship_between_job_members', 'force_invite_only') + Situation.SITUATION_START_FROM_UI_REMOVE_INSTANCE_TUNABLES
    DOES_NOT_CARE_MAX_SCORE = -1

    @classproperty
    def situation_serialization_option(cls):
        return SituationSerializationOption.HOLIDAY

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._progress_meter = self._progress_meter_settings.create_meter(self)
        self._goal_preferences = None
        self._max_score = 0
        self._reward = None

    def _destroy(self):
        self._progress_meter.destroy()
        super()._destroy()

    def on_remove(self):
        sim = self.get_situation_goal_actor()
        household = sim.household
        if household is not None and household.holiday_tracker is not None:
            holiday_id = household.holiday_tracker.active_holiday_id
            if holiday_id is not None:
                self.show_holiday_end_notification(holiday_id)
        super().on_remove()

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _HolidaySituationState),)

    @classmethod
    def default_job(cls):
        return cls.holiday_situation_job_and_role_state.job

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.holiday_situation_job_and_role_state.job, cls.holiday_situation_job_and_role_state.role_state)]

    @property
    def situation_display_type(self):
        return SituationDisplayType.SIM_SPECIFIC

    @property
    def situation_display_priority(self):
        return SituationDisplayPriority.HOLIDAY

    @property
    def user_facing_type(self):
        return SituationUserFacingType.HOLIDAY_EVENT

    @classproperty
    def allow_non_prestige_events(cls):
        return True

    @classproperty
    def supports_automatic_bronze(cls):
        return False

    @property
    def start_audio_sting(self):
        active_household = services.active_household()
        if active_household is None:
            return
        holiday_id = active_household.holiday_tracker.active_holiday_id
        if holiday_id is None:
            return
        return services.holiday_service().get_holiday_audio_sting(holiday_id)

    def _get_situation_sim(self):
        return services.sim_info_manager().get(self._guest_list.host_sim_id)

    def build_situation_start_message(self):
        msg = super().build_situation_start_message()
        with ProtocolBufferRollback(msg.meter_data) as meter_data_msg:
            self._progress_meter_settings.build_data_message(meter_data_msg)
        msg.situation_id = self.id
        end_time = HolidayTuning.MAIN_HOLIDAY_START_TIME + HolidayTuning.HOLIDAY_DURATION()
        sim_info = self._get_situation_sim()
        display_name = sim_info.household.holiday_tracker.get_active_holiday_display_name()
        holiday_icon = sim_info.household.holiday_tracker.get_active_holiday_display_icon()
        build_icon_info_msg(IconInfoData(icon_resource=holiday_icon), display_name, msg.icon_info, desc=LocalizationHelperTuning.get_start_time_to_end_time(HolidayTuning.MAIN_HOLIDAY_START_TIME, end_time))
        msg.icon_info.control_id = 0
        msg.display_delay = HolidayTuning.HOLIDAY_DISPLAY_DELAY().in_ticks()
        return msg

    def start_situation(self):
        super().start_situation()
        self._change_state(_HolidaySituationState())
        self._setup_holiday_preferences()

    def _load_situation_states_and_phases(self):
        super()._load_situation_states_and_phases()
        self._setup_holiday_preferences()

    def build_situation_end_message(self):
        if services.current_zone().is_zone_shutting_down or self._reward is not None:
            medal = self.get_level()
            reward = self._reward.get(medal, None)
            if reward is not None:
                reward.give_reward(self.initiating_sim_info)
        return super().build_situation_end_message()

    def show_holiday_end_notification(self, active_holiday_id):
        if self._max_score == self.DOES_NOT_CARE_MAX_SCORE:
            return
        holiday_notifications = HolidayTuning.HOLIDAY_NOTIFICATION_INFORMATION
        medal = self.get_level()
        sim = self.get_situation_goal_actor()
        holiday_service = services.holiday_service()
        for (notification_key, notification_value) in holiday_notifications.items():
            if notification_key is medal:
                holiday_end_dialog = notification_value(sim)
                holiday_name = holiday_service.get_holiday_display_name(active_holiday_id)
                holiday_icon = holiday_service.get_holiday_display_icon(active_holiday_id)
                holiday_end_dialog.show_dialog(additional_tokens=(sim, holiday_name), icon_override=IconInfoData(icon_resource=holiday_icon), secondary_icon_override=IconInfoData(obj_instance=sim))
                break

    def get_situation_goal_actor(self):
        return self._get_situation_sim()

    def _get_effective_score_for_levels(self, score):
        if self._max_score == 0:
            return 0
        if self._max_score == self.DOES_NOT_CARE_MAX_SCORE:
            return 0
        return int(score/self._max_score*100)

    def _get_reward(self):
        if self._max_score == self.DOES_NOT_CARE_MAX_SCORE:
            return
        else:
            medal = self.get_level()
            level_data = self.get_level_data(medal)
            if level_data is not None:
                return level_data.reward
            else:
                return
        return

    def _update_ui(self):
        sim = self.get_situation_goal_actor()
        self._send_icon_update_to_client(sim)
        goal_tracker = self._get_goal_tracker()
        if goal_tracker is not None:
            goal_tracker.send_goal_update_to_client()

    def _setup_max_score(self, num_preferences_sim_cares):
        self._max_score = self.DOES_NOT_CARE_MAX_SCORE
        for scoring_info in HolidayTuning.HOLIDAY_SCORING_INFORMATION:
            if scoring_info.threshold.compare(num_preferences_sim_cares):
                self._max_score = scoring_info.max_score
                self._reward = scoring_info.reward
                break

    def _setup_holiday_preferences(self):
        sim_info = self._get_situation_sim()
        self._goal_preferences = {}
        num_preferences_sim_cares = 0
        for tradition in sim_info.household.holiday_tracker.get_active_traditions():
            (preference, reason) = tradition.get_sim_preference(sim_info)
            self._goal_preferences[tradition.situation_goal] = (preference, reason)
            if preference in TRADITION_PREFERENCE_CARES:
                num_preferences_sim_cares += 1
        self._setup_max_score(num_preferences_sim_cares)
        goal_tracker = self._get_goal_tracker()
        if goal_tracker is not None:
            goal_tracker.set_goal_preferences(self._goal_preferences)

    def on_first_assignment_pass_completed(self):
        super().on_first_assignment_pass_completed()
        active_holiday_id = services.active_household().holiday_tracker.active_holiday_id
        current_traditions = services.holiday_service().get_holiday_traditions(active_holiday_id)
        ordered_goals = [tradition.situation_goal for tradition in current_traditions]
        current_goals = set(ordered_goals)
        saved_goals = {type(goal) for goal in self._goal_tracker.goals}
        added_goals = current_goals - saved_goals
        removed_goals = saved_goals - current_goals
        if added_goals or removed_goals:
            self._goal_tracker.update_goals(added_goals, removed_goals, goal_type_order=ordered_goals)
        self._goal_tracker.send_goal_update_to_client()
        self._progress_meter.send_update()

    def on_goal_completed(self, goal):
        score = goal.score
        (preference, _) = self._goal_preferences[type(goal)]
        if preference in HolidayTuning.TRADITION_PREFERENCE_SCORE_MULTIPLIER:
            score *= HolidayTuning.TRADITION_PREFERENCE_SCORE_MULTIPLIER[preference]
        self.score_update(score)
        self.send_goal_completed_telemetry(score, goal)

    def score_update(self, score_delta):
        score_delta = score_delta
        self._score += score_delta
        if self._max_score == self.DOES_NOT_CARE_MAX_SCORE:
            return
        self._progress_meter.send_update()

    def _send_icon_update_to_client(self, sim):
        display_name = sim.household.holiday_tracker.get_active_holiday_display_name()
        holiday_icon = sim.household.holiday_tracker.get_active_holiday_display_icon()
        msg = Situations_pb2.SituationIconUpdate()
        msg.situation_id = self.id
        end_time = HolidayTuning.MAIN_HOLIDAY_START_TIME + HolidayTuning.HOLIDAY_DURATION()
        build_icon_info_msg(IconInfoData(icon_resource=holiday_icon), display_name, msg.icon_info, desc=LocalizationHelperTuning.get_start_time_to_end_time(HolidayTuning.MAIN_HOLIDAY_START_TIME, end_time))
        msg.icon_info.control_id = 0
        op = distributor.ops.SituationIconUpdateOp(msg)
        Distributor.instance().add_op(self, op)

    def on_holiday_data_changed(self, traditions_added, traditions_removed, ordered_traditions):
        self._dynamic_goals = [tradition.situation_goal for tradition in ordered_traditions]
        added_goals = [tradition.situation_goal for tradition in traditions_added]
        sim = self.get_situation_goal_actor()
        for tradition in traditions_added:
            (preference, reason) = tradition.get_sim_preference(sim)
            self._goal_preferences[tradition.situation_goal] = (preference, reason)
        for tradition in traditions_removed:
            del self._goal_preferences[tradition.situation_goal]
        self._setup_max_score(sum(1 for (preference, _) in self._goal_preferences.values() if preference in TRADITION_PREFERENCE_CARES))
        self._goal_tracker.set_goal_preferences(self._goal_preferences)
        removed_goals = [tradition.situation_goal for tradition in traditions_removed]
        self._goal_tracker.update_goals(added_goals, removed_goals, goal_type_order=self._dynamic_goals)
        self._update_ui()

    def _issue_requests(self):
        request = HolidayParticipantRequestFactory(self, _RequestUserData(), self.default_job(), self.exclusivity, self._guest_list.host_sim_id)
        self.manager.bouncer.submit_request(request)
lock_instance_tunables(HolidaySituation, exclusivity=BouncerExclusivityCategory.NEUTRAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0, _implies_greeted_status=False)