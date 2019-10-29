from date_and_time import create_time_spanfrom sims.sim_info_lod import SimInfoLODLevelfrom sims4.tuning.tunable import Tunable, TunablePercentfrom story_progression import StoryProgressionFlagsfrom story_progression.actions import StoryProgressionActionMaxPopulationimport alarmsimport servicesimport sims4.loglogger = sims4.log.Logger('SimInfoFireMeter', default_owner='manus')
class SimInfoFireMeter:
    FIREMETER_FREQUENCY = Tunable(description="\n        The game creates a repeating alarm at this frequency to check whether\n        the SimInfoManager has more than the fire meter's threshold before\n        triggering a purge of sim_infos.\n\n        Please consult a member of performance group before updating this\n        tuning.\n        ", tunable_type=int, default=120)
    SIM_INFO_ALLOWED_PERCENTAGE_ABOVE_CAP = TunablePercent(description="\n        The game triggers an out-of-cycle story progression action to control\n        population when we cross the current sim info cap plus this percentage.\n        For instance, if this percentage is set to 15% and the current Sim Info\n        cap is 100 Sim Infos, we'll start culling Sim Infos once we cross 115\n        (100 + 15%).\n        \n        Please consult a member of the performance group before updating this\n        tuning.\n        ", default=15)

    def __init__(self):
        self._alarm_handle = alarms.add_alarm(self, create_time_span(minutes=self.FIREMETER_FREQUENCY), self._firemeter_callback, repeating=True, use_sleep_time=False)

    def shutdown(self):
        if self._alarm_handle is not None:
            alarms.cancel_alarm(self._alarm_handle)
            self._alarm_handle = None

    def _firemeter_callback(self, _):
        sim_info_manager = services.sim_info_manager()
        sim_info_count = len(sim_info_manager)
        sim_info_cap = sim_info_manager.SIM_INFO_CAP
        if sim_info_count <= sim_info_cap:
            return
        adjusted_sim_info_cap = int(sim_info_cap*(1 + self.SIM_INFO_ALLOWED_PERCENTAGE_ABOVE_CAP))
        if sim_info_count < adjusted_sim_info_cap:
            return
        logger.debug('FireMeter: We have {} sim_infos in the save file. Current cap: {}. Cap after adjustments: {}. Purge begins.', sim_info_count, sim_info_cap, adjusted_sim_info_cap)
        self.trigger()

    def trigger(self):
        story_progression_service = services.get_story_progression_service()
        if story_progression_service is None:
            return
        for action in story_progression_service.ACTIONS:
            if isinstance(action, StoryProgressionActionMaxPopulation):
                action.process_action(StoryProgressionFlags.SIM_INFO_FIREMETER)
                break
