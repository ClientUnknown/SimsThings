from alarms import add_alarm, cancel_alarmfrom sims4.service_manager import Servicefrom situations.service_npcs.modify_lot_items_tuning import ModifyAllLotItemsimport date_and_timeimport servicesimport tunable_time
class CleanupService(Service):
    OPEN_STREET_CLEANUP_ACTIONS = ModifyAllLotItems.TunableFactory()
    OPEN_STREET_CLEANUP_TIME = tunable_time.TunableTimeOfDay(description='\n        What time of day the open street cleanup will occur.\n        ', default_hour=4)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._alarm_handle = None

    def start(self):
        current_time = services.time_service().sim_now
        initial_time_span = current_time.time_till_next_day_time(self.OPEN_STREET_CLEANUP_TIME)
        repeating_time_span = date_and_time.create_time_span(days=1)
        self._alarm_handle = add_alarm(self, initial_time_span, self._on_update, repeating=True, repeating_time_span=repeating_time_span)

    def stop(self):
        if self._alarm_handle is not None:
            cancel_alarm(self._alarm_handle)
            self._alarm_handle = None

    def _on_update(self, _):
        self._do_cleanup()

    def _do_cleanup(self):
        cleanup = CleanupService.OPEN_STREET_CLEANUP_ACTIONS()

        def object_criteria(obj):
            if obj.in_use:
                return False
            elif obj.is_on_active_lot():
                return False
            return True

        cleanup.modify_objects(object_criteria=object_criteria)

    def on_cleanup_zone_objects(self, client):
        time_of_last_save = services.current_zone().time_of_last_save()
        now = services.time_service().sim_now
        time_to_now = now - time_of_last_save
        time_to_cleanup = time_of_last_save.time_till_next_day_time(CleanupService.OPEN_STREET_CLEANUP_TIME)
        if time_to_now > time_to_cleanup:
            self._do_cleanup()
