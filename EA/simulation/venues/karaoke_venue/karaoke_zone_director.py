from scheduler import SituationWeeklySchedulefrom situations.situation_guest_list import SituationGuestListfrom venues.scheduling_zone_director import SchedulingZoneDirectorimport services
class KaraokeZoneDirector(SchedulingZoneDirector):
    INSTANCE_TUNABLES = {'special_event_schedule': SituationWeeklySchedule.TunableFactory(description='\n            The schedule to trigger the different special scheduled events.\n            ', schedule_entry_data={'pack_safe': True})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._special_event_schedule = None

    def on_loading_screen_animation_finished(self):
        self._special_event_schedule = self.special_event_schedule(start_callback=self._start_special_event)

    def _start_special_event(self, scheduler, alarm_data, extra_data):
        situation = alarm_data.entry.situation
        if not situation.situation_meets_starting_requirements():
            return
        situation_manager = services.get_zone_situation_manager()
        if any(situation is type(running_situation) for running_situation in situation_manager.running_situations()):
            return
        guest_list = SituationGuestList(invite_only=True)
        situation_manager.create_situation(situation, guest_list=guest_list, user_facing=False, scoring_enabled=False, creation_source=self.instance_name)
