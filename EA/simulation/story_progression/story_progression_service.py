from alarms import AlarmHandlefrom scheduling import Timelinefrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableList, TunableRealSecondfrom sims4.utils import classpropertyfrom story_progression import StoryProgressionFlagsfrom story_progression.actions import TunableStoryProgressionActionVariantfrom story_progression.story_progression_demographic import TunableStoryProgressionDemographicVariantimport alarmsimport clockimport gsi_handlersimport persistence_error_typesimport servicesimport simsimport sims4.logimport zone_typeslogger = sims4.log.Logger('StoryProgression')
class StoryProgressionService(Service):
    GLOBAL_DEMOGRAPHICS = TunableList(description='\n        A list of demographics affecting the entire universe. This includes all\n        worlds as well as townie Sims.\n        ', tunable=TunableStoryProgressionDemographicVariant())
    INTERVAL = TunableRealSecond(description='\n        The time between Story Progression actions. A lower number will\n        impact performance.\n        ', default=5)
    ACTIONS = TunableList(description='\n        A list of actions that are available to Story Progression.\n        ', tunable=TunableStoryProgressionActionVariant())

    def __init__(self):
        self._alarm_handle = None
        self._next_action_index = 0
        self._story_progression_flags = StoryProgressionFlags.DISABLED
        self._demographics = None
        self._timeline = None
        self._timeline_update = None
        self._timeline_multiplier = 1

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_STORY_PROGRESSION_SERVICE

    def load_options(self, options_proto):
        if options_proto is None:
            return
        if options_proto.npc_population_enabled:
            self._story_progression_flags |= StoryProgressionFlags.ALLOW_POPULATION_ACTION
            self._story_progression_flags |= StoryProgressionFlags.ALLOW_INITIAL_POPULATION

    def setup(self, save_slot_data=None, **kwargs):
        if save_slot_data is not None:
            sims.global_gender_preference_tuning.GlobalGenderPreferenceTuning.enable_autogeneration_same_sex_preference = save_slot_data.gameplay_data.enable_autogeneration_same_sex_preference

    def save(self, save_slot_data=None, **kwargs):
        if save_slot_data is not None:
            save_slot_data.gameplay_data.enable_autogeneration_same_sex_preference = sims.global_gender_preference_tuning.GlobalGenderPreferenceTuning.enable_autogeneration_same_sex_preference

    def on_all_households_and_sim_infos_loaded(self, client):
        self.update()
        self.get_demographics()
        for sim_info in services.sim_info_manager().get_all():
            if sim_info.story_progression_tracker is not None:
                sim_info.story_progression_tracker.on_all_households_and_sim_infos_loaded()
        return super().on_all_households_and_sim_infos_loaded(client)

    def enable_story_progression_flag(self, story_progression_flag):
        self._story_progression_flags |= story_progression_flag

    def disable_story_progression_flag(self, story_progression_flag):
        self._story_progression_flags &= ~story_progression_flag

    def is_story_progression_flag_enabled(self, story_progression_flag):
        return self._story_progression_flags & story_progression_flag

    def on_client_connect(self, client):
        current_zone = services.current_zone()
        current_zone.register_callback(zone_types.ZoneState.RUNNING, self._initialize_alarm)
        current_zone.register_callback(zone_types.ZoneState.SHUTDOWN_STARTED, self._on_zone_shutdown)

    def _on_zone_shutdown(self):
        current_zone = services.current_zone()
        if self._alarm_handle is not None:
            alarms.cancel_alarm(self._alarm_handle)
        current_zone.unregister_callback(zone_types.ZoneState.SHUTDOWN_STARTED, self._on_zone_shutdown)

    def _initialize_alarm(self):
        current_zone = services.current_zone()
        current_zone.unregister_callback(zone_types.ZoneState.RUNNING, self._initialize_alarm)
        time_span = clock.interval_in_sim_minutes(self.INTERVAL)
        self._alarm_handle = alarms.add_alarm(self, time_span, self._process_next_action, repeating=True)

    def _process_next_action(self, _):
        self.process_action_index(self._next_action_index)
        self._next_action_index += 1
        if self._next_action_index >= len(self.ACTIONS):
            self._next_action_index = 0

    def process_action_index(self, index):
        if index >= len(self.ACTIONS):
            logger.error('Trying to process index {} where max index is {}', index, len(self.ACTIONS) - 1)
            return
        action = self.ACTIONS[index]
        if action.should_process(self._story_progression_flags):
            if gsi_handlers.story_progression_handlers.story_progression_archiver.enabled:
                gsi_handlers.story_progression_handlers.archive_story_progression(action, 'Processing started.')
            action.process_action(self._story_progression_flags)
            if gsi_handlers.story_progression_handlers.story_progression_archiver.enabled:
                gsi_handlers.story_progression_handlers.archive_story_progression(action, 'Processing complete.')
        elif gsi_handlers.story_progression_handlers.story_progression_archiver.enabled:
            gsi_handlers.story_progression_handlers.archive_story_progression(action, 'Processing skipped.')

    def process_all_actions(self):
        for i in range(len(self.ACTIONS)):
            self.process_action_index(i)

    def get_demographics(self):
        if self._demographics is None:
            self._demographics = [demographic() for demographic in self.GLOBAL_DEMOGRAPHICS]
        return self._demographics

    def register_action(self, story_progression_action):
        story_progression_action.update_demographics(self._demographics)
        alarm_handle = AlarmHandle(story_progression_action, story_progression_action.on_execute_action, self._timeline, self._timeline.now + story_progression_action.get_duration())
        story_progression_action.set_alarm_handle(alarm_handle)

    def unregister_action(self, story_progression_action):
        self._demographics = None

    def set_time_multiplier(self, time_multiplier):
        if time_multiplier < 0:
            logger.error('Unable to set Story Progression time multiplier to {}', time_multiplier)
            return
        self._timeline_multiplier = time_multiplier

    def update(self):
        current_time = services.time_service().sim_now
        if self._timeline is None:
            self._timeline = Timeline(current_time)
        if self._timeline_update is None:
            self._timeline_update = current_time
            return
        delta_time = current_time - self._timeline_update
        self._timeline_update = current_time
        delta_time *= self._timeline_multiplier
        self._timeline.simulate(self._timeline.now + delta_time)
