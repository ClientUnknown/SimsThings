import randomfrom event_testing.resolver import SingleSimResolverfrom sickness.sickness_handlers import archive_sim_sickness_eventfrom sickness.sickness_tuning import SicknessTuningfrom sickness.sickness_utils import all_sickness_weights_genfrom sims4.callback_utils import CallableTestListfrom sims4.service_manager import Serviceimport alarmsimport date_and_timeimport servicesimport sims4import zone_types
class SicknessService(Service):

    def __init__(self, *_, **__):
        self._alarm_handle = None

    def on_client_connect(self, client):
        current_zone = services.current_zone()
        current_zone.register_callback(zone_types.ZoneState.RUNNING, self._initialize_alarm)
        current_zone.register_callback(zone_types.ZoneState.SHUTDOWN_STARTED, self._on_zone_shutdown)

    def _initialize_alarm(self):
        if not services.time_service():
            return
        current_time = services.time_service().sim_now
        initial_time_span = current_time.time_till_next_day_time(SicknessTuning.SICKNESS_TIME_OF_DAY)
        repeating_time_span = date_and_time.create_time_span(days=1)
        self._alarm_handle = alarms.add_alarm(self, initial_time_span, self._trigger_sickness_distribution_alarm_callback, repeating=True, repeating_time_span=repeating_time_span)

    def _on_zone_shutdown(self):
        current_zone = services.current_zone()
        if self._alarm_handle is not None:
            alarms.cancel_alarm(self._alarm_handle)
        current_zone.unregister_callback(zone_types.ZoneState.SHUTDOWN_STARTED, self._on_zone_shutdown)

    def _trigger_sickness_distribution_alarm_callback(self, _):
        self.trigger_sickness_distribution()

    def trigger_sickness_distribution(self):
        for sim_info in services.sim_info_manager().values():
            if sim_info.sickness_tracker is None:
                pass
            else:
                resolver = SingleSimResolver(sim_info)
                if not self._should_sim_become_sick(resolver):
                    pass
                else:
                    sickness = self._choose_sickness_for_sim(resolver, criteria_func=lambda s: not s.distribute_manually)
                    sickness.apply_to_sim_info(sim_info)

    def can_become_sick(self, resolver):
        return SicknessTuning.SICKNESS_TESTS.run_tests(resolver)

    def get_sickness_chance(self, resolver):
        if not self.can_become_sick(resolver):
            return 0.0
        become_sick = max(0, SicknessTuning.SICKNESS_CHANCE.get_modified_value(resolver))
        chance = become_sick/100.0
        return chance

    def make_sick(self, sim_info, sickness=None, criteria_func=None, only_auto_distributable=True):
        resolver = SingleSimResolver(sim_info)
        if sickness is None:
            criteria_list = CallableTestList()
            if only_auto_distributable:
                criteria_list.append(lambda s: not s.distribute_manually)
            if criteria_func is not None:
                criteria_list.append(criteria_func)
            sickness = self._choose_sickness_for_sim(resolver, criteria_func=criteria_list)
        if sickness is not None:
            self.remove_sickness(sim_info)
            sickness.apply_to_sim_info(sim_info)
            self.add_sickness_event(sim_info, sim_info.current_sickness, 'Added Sickness')

    def remove_sickness(self, sim_info):
        if sim_info.has_sickness_tracking():
            self.add_sickness_event(sim_info, sim_info.current_sickness, 'Removed Sickness')
            sim_info.current_sickness.remove_from_sim_info(sim_info)

    def _should_sim_become_sick(self, sim_resolver):
        chance = self.get_sickness_chance(sim_resolver)
        if not chance:
            return False
        return random.random() < chance

    def _choose_sickness_for_sim(self, sim_resolver, criteria_func=lambda x: True):
        sickness_weights = list(all_sickness_weights_gen(sim_resolver, criteria_func=criteria_func))
        return sims4.random.pop_weighted(sickness_weights)

    def clear_diagnosis_data(self, sim_info):
        if sim_info.sickness_tracker is not None:
            sim_info.sickness_tracker.clear_diagnosis_data()

    def sickness_event_data_gen(self):
        yield from self._sim_data.items()

    def add_sickness_event(self, sim_info, sickness, event_message):
        pass
