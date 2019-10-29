from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom distributor.rollback import ProtocolBufferRollbackfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims4.tuning.tunable import TunableRangeimport gsi_handlers.story_progression_handlersimport servicesimport sims4.resources
class StoryProgressionTracker(SimInfoTracker):
    MAXIMUM_ACTION_COUNT = TunableRange(description='\n        Define the maximum number of actions that a Sim may run at any given\n        time.\n        ', tunable_type=int, default=1, minimum=1)

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._actions = []

    def clear_story_progression_tracker(self):
        self._actions.clear()

    def get_actions_gen(self):
        yield from self._actions

    def _get_best_scored_action(self, action_scores):
        if not action_scores:
            return
        return max(action_scores, key=lambda x: action_scores[x])

    def _get_combined_score(self, story_progression_action, global_demographics):
        score = story_progression_action.get_score()
        if not (score and global_demographics):
            return (score, global_demographics)
        action_demographics = tuple(d.get_demographic_clone() for d in global_demographics)
        story_progression_action.update_demographics(action_demographics)
        average_demographic_score = 1 - sum(d.get_demographic_error() for d in action_demographics)/len(action_demographics)
        return (score + average_demographic_score, action_demographics)

    def _log_gsi_entry(self, action, result, **kwargs):
        if gsi_handlers.story_progression_handlers.story_progression_sim_archiver.enabled:
            gsi_handlers.story_progression_handlers.archive_sim_story_progression(self._sim_info, action, result=result, **kwargs)

    def find_best_story_progression_action(self):
        if len(self._actions) >= self.MAXIMUM_ACTION_COUNT:
            return
        story_progression_manager = services.get_instance_manager(sims4.resources.Types.STORY_PROGRESSION_ACTION)
        if story_progression_manager is None:
            return
        story_progression_service = services.get_story_progression_service()
        if story_progression_service is None:
            return
        global_demographics = story_progression_service.get_demographics()
        available_action_scores = dict()
        for story_progression_action_type in story_progression_manager.types.values():
            for story_progression_action in story_progression_action_type.get_potential_actions_gen(self._sim_info):
                (score, action_demographics) = self._get_combined_score(story_progression_action, global_demographics)
                self._log_gsi_entry(story_progression_action, score, global_demographics=global_demographics, action_demographics=action_demographics)
                if score:
                    available_action_scores[story_progression_action] = score
        best_action = self._get_best_scored_action(available_action_scores)
        if best_action is not None:
            best_action.set_duration()
            story_progression_service.register_action(best_action)
            self._actions.append(best_action)
        return best_action

    def on_all_households_and_sim_infos_loaded(self):
        story_progression_service = services.get_story_progression_service()
        for story_progression_action in self._actions:
            story_progression_service.register_action(story_progression_action)

    def load(self, data):
        story_progression_manager = services.get_instance_manager(sims4.resources.Types.STORY_PROGRESSION_ACTION)
        for action_data in data.actions:
            story_progression_action_type = story_progression_manager.get(action_data.guid)
            if story_progression_action_type is None:
                pass
            else:
                try:
                    story_progression_action = story_progression_action_type(self._sim_info)
                    story_progression_action.load(action_data)
                except TypeError:
                    continue
                self._actions.append(story_progression_action)

    def save(self):
        data = protocols.PersistableStoryProgressionTracker()
        for story_progression_action in self._actions:
            with ProtocolBufferRollback(data.actions) as action_data:
                story_progression_action.save(action_data)
        return data

    def on_lod_update(self, old_lod, new_lod):
        if new_lod == SimInfoLODLevel.MINIMUM:
            self.clear_story_progression_tracker()
