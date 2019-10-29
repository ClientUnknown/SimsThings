from distributor.shared_messages import build_icon_info_msg, IconInfoDataimport uid
class BaseSituationGoalTracker:

    def __init__(self, situation):
        self._situation = situation
        self._has_offered_goals = False
        self._goal_id_generator = uid.UniqueIdGenerator(1)

    def destroy(self):
        self._situation = None

    def save_to_seed(self, situation_seed):
        raise NotImplementedError

    def load_from_seedling(self, tracker_seedling):
        raise NotImplementedError

    def autocomplete_goals_on_load(self, previous_zone_id):
        pass

    def has_offered_goals(self):
        return self._has_offered_goals

    def refresh_goals(self, completed_goal=None):
        new_goals_offered = self._offer_goals()
        if new_goals_offered or completed_goal is not None:
            self.send_goal_update_to_client(completed_goal=completed_goal)

    def _offer_goals(self):
        raise NotImplementedError

    def get_goal_info(self):
        raise NotImplementedError

    def get_completed_goal_info(self):
        raise NotImplementedError

    def send_goal_update_to_client(self, completed_goal=None, goal_preferences=None):
        raise NotImplementedError

    def _build_goal_message(self, goal_msg, goal):
        goal_msg.goal_id = goal.id
        goal_name = goal.get_display_name()
        if goal_name is not None:
            goal_msg.goal_name = goal_name
        goal_msg.max_iterations = goal.max_iterations
        if goal.completed_time is None:
            goal_msg.current_iterations = goal.completed_iterations
        else:
            goal_msg.current_iterations = goal.max_iterations
        goal_tooltip = goal.get_display_tooltip()
        if goal_tooltip is not None:
            goal_msg.goal_tooltip = goal_tooltip
        if goal.audio_sting_on_complete is not None:
            goal_msg.audio_sting.type = goal.audio_sting_on_complete.type
            goal_msg.audio_sting.group = goal.audio_sting_on_complete.group
            goal_msg.audio_sting.instance = goal.audio_sting_on_complete.instance
        build_icon_info_msg(IconInfoData(icon_resource=goal.display_icon), goal_name, goal_msg.icon_info)
        goal_msg.display_type = goal.display_type.value
