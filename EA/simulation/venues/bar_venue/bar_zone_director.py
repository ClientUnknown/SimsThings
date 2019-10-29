from scheduler import SituationWeeklySchedulefrom situations.complex.bowling_venue import BowlingVenueMixinfrom situations.situation_guest_list import SituationGuestListfrom venues.scheduling_zone_director import SchedulingZoneDirectorimport services
class BarZoneDirector(BowlingVenueMixin, SchedulingZoneDirector):
    INSTANCE_TUNABLES = {'special_bar_schedule': SituationWeeklySchedule.TunableFactory(description='\n            The schedule to trigger the different special bar scheduled events.\n            ', schedule_entry_data={'pack_safe': True})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._special_bar_schedule = None

    def on_loading_screen_animation_finished(self):
        super().on_loading_screen_animation_finished()
        self._special_bar_schedule = self.special_bar_schedule(start_callback=self._start_special_bar_event)

    def _start_special_bar_event(self, scheduler, alarm_data, extra_data):
        situation = alarm_data.entry.situation
        if not situation.situation_meets_starting_requirements():
            return
        situation_manager = services.get_zone_situation_manager()
        if any(situation is type(running_situation) for running_situation in situation_manager.running_situations()):
            return
        guest_list = SituationGuestList(invite_only=True)
        situation_manager.create_situation(situation, guest_list=guest_list, user_facing=False, scoring_enabled=False, creation_source=self.instance_name)
