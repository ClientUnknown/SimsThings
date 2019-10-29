from distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorfrom event_testing.resolver import SingleSimResolverfrom protocolbuffers import Area_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom sims4.localization import LocalizationHelperTuningfrom ui.screen_slam import ScreenSlamimport event_testing.event_data_tracker as data_trackerimport event_testing.test_events as test_eventsimport gsi_handlers.achievement_handlersimport pathsimport servicesimport sims4.logimport telemetry_helperlogger = sims4.log.Logger('Achievements')TELEMETRY_GROUP_ACHIEVEMENTS = 'ACHI'TELEMETRY_HOOK_ADD_ACHIEVEMENT = 'ACHA'TELEMETRY_OBJECTIVE_ID = 'obid'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_ACHIEVEMENTS)
class AchievementTracker(data_tracker.EventDataTracker):

    def __init__(self, account_id):
        super().__init__()
        self._account_id = account_id

    def _get_milestone_manager(self):
        return services.get_instance_manager(sims4.resources.Types.ACHIEVEMENT)

    @property
    def simless(self):
        return True

    @property
    def owner_sim_info(self):
        client = services.client_manager().get_first_client()
        if client is not None:
            return client.active_sim_info

    def gsi_event(self, event):
        return {'account': self._account_id, 'event': str(event)}

    def post_to_gsi(self, message):
        gsi_handlers.achievement_handlers.archive_achievement_event_set(message)

    def _send_tracker_to_client(self, init=False):
        msg_empty = True
        msg = Area_pb2.AchievementTrackerUpdate()
        for achievement in self._completed_milestones:
            if not self.milestone_sent(achievement):
                self._sent_milestones.add(achievement)
                msg.achievements_completed.append(achievement.guid64)
                if msg_empty:
                    msg_empty = False
        for objective in self._completed_objectives:
            if not self.objective_sent(objective):
                self._sent_objectives.add(objective)
                msg.objectives_completed.append(objective.guid64)
                if msg_empty:
                    msg_empty = False
        if not msg_empty:
            msg.account_id = self._account_id
            msg.init_message = init
            cheat_service = services.get_cheat_service()
            msg.cheats_used = cheat_service.cheats_ever_enabled
            distributor = Distributor.instance()
            owner = self.owner_sim_info
            if owner is None:
                distributor.add_op_with_no_owner(GenericProtocolBufferOp(Operation.ACCT_ACHIEVEMENT_TRACKER_UPDATE, msg))
            else:
                distributor.add_op(owner, GenericProtocolBufferOp(Operation.ACCT_ACHIEVEMENT_TRACKER_UPDATE, msg))

    def _send_objectives_update_to_client(self):
        msg = Area_pb2.AcctGoalsStatusUpdate()
        if self._update_objectives_msg_for_client(msg):
            msg.account_id = self._account_id
            distributor = Distributor.instance()
            owner = self.owner_sim_info
            if owner is None:
                distributor.add_op_with_no_owner(GenericProtocolBufferOp(Operation.ACCT_GOALS_STATUS_UPDATE, msg))
            else:
                distributor.add_op(owner, GenericProtocolBufferOp(Operation.ACCT_GOALS_STATUS_UPDATE, msg))

    def complete_milestone(self, achievement, sim_info):
        super().complete_milestone(achievement, sim_info)
        if paths.IS_DESKTOP:
            tutorial_service = services.get_tutorial_service()
            if tutorial_service is None or not tutorial_service.is_tutorial_running():
                if achievement.screen_slam is not None:
                    achievement.screen_slam.send_screen_slam_message(sim_info, achievement.display_name)
                achievement.show_achievement_notification(sim_info)
        if achievement.reward is not None:
            achievement.reward.give_reward(sim_info)
        services.get_event_manager().process_event(test_events.TestEvent.UnlockEvent, sim_info=sim_info, unlocked=achievement)

    def complete_objective(self, objective_instance):
        super().complete_objective(objective_instance)
        with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_ADD_ACHIEVEMENT) as hook:
            hook.write_guid(TELEMETRY_OBJECTIVE_ID, objective_instance.guid64)

    def reset_milestone(self, completed_milestone):
        for objective in completed_milestone.objectives:
            if objective.resettable:
                objective.reset_objective(self.data_object)
                self.reset_objective(objective)
        super().reset_milestone(completed_milestone)

    def _update_timer_alarm(self, _):
        self.update_timers()
