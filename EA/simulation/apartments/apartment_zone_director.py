from alarms import add_alarmfrom date_and_time import create_time_span, DateAndTimefrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.tunable import TunableTuple, TunableList, TunableMapping, TunableReference, TunableSimMinutefrom situations.service_npcs.modify_lot_items_tuning import ModifyAllLotItemsfrom situations.situation_guest_list import SituationGuestListfrom tunable_time import TunableTimeOfDayfrom venues.scheduling_zone_director import SchedulingZoneDirectorMixinfrom venues.zone_director_residential import ZoneDirectorResidentialPlayer, ZoneDirectorResidentialNPCimport servicesimport sims4.loglogger = sims4.log.Logger('Apartments', default_owner='rmccord')
class ApartmentZoneDirectorMixin(SchedulingZoneDirectorMixin):
    COMMON_AREA_CLEANUP = TunableTuple(description='\n        Tuning to clear out objects from the common area to prevent trash\n        and what not from accumulating.\n        ', actions=ModifyAllLotItems.TunableFactory(description='\n            Modifications to make to objects on the common area of apartments.\n            '), time_of_day=TunableTimeOfDay(description='\n            Time of day to run cleanup.\n            ', default_hour=4))
    NEW_TENANT_CLEANUP = ModifyAllLotItems.TunableFactory(description='\n        Modifications to make to objects when a new tenant moves in.\n        Example: We want to fix and reset all apartment problems when new\n        tenants move in.\n        ')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._common_area_cleanup_alarm_handle = None

    @property
    def forward_ungreeted_front_door_interactions_to_terrain(self):
        return False

    def on_startup(self):
        super().on_startup()
        now = services.time_service().sim_now
        time_span = now.time_till_next_day_time(ApartmentZoneDirectorMixin.COMMON_AREA_CLEANUP.time_of_day)
        repeating_time_span = create_time_span(days=1)
        handle = add_alarm(self, time_span, lambda _: self._run_common_area_cleanup(), repeating=True, repeating_time_span=repeating_time_span)
        self._common_area_cleanup_alarm_handle = handle

    def on_shutdown(self):
        self._common_area_cleanup_alarm_handle.cancel()
        self._common_area_cleanup_alarm_handle = None
        super().on_shutdown()

    def on_cleanup_zone_objects(self):
        super().on_cleanup_zone_objects()
        persistence_service = services.get_persistence_service()
        plex_service = services.get_plex_service()
        plex_zone_ids = plex_service.get_plex_zones_in_group(services.current_zone_id())
        last_save_ticks = None
        for zone_id in plex_zone_ids:
            zone_data = persistence_service.get_zone_proto_buff(zone_id)
            gameplay_zone_data = zone_data.gameplay_zone_data
            if not gameplay_zone_data.HasField('game_time'):
                pass
            else:
                if not last_save_ticks is None:
                    if last_save_ticks < gameplay_zone_data.game_time:
                        last_save_ticks = gameplay_zone_data.game_time
                last_save_ticks = gameplay_zone_data.game_time
        if last_save_ticks is not None:
            last_save_time = DateAndTime(last_save_ticks)
            next_cleanup_time = last_save_time.time_of_next_day_time(ApartmentZoneDirectorMixin.COMMON_AREA_CLEANUP.time_of_day)
            if next_cleanup_time < services.time_service().sim_now:
                self._run_common_area_cleanup()
        owning_household = services.owning_household_of_active_lot()
        if owning_household is not None and not owning_household.has_home_zone_been_active():
            self._run_new_tenant_cleanup()

    def _run_new_tenant_cleanup(self):
        actions = ApartmentZoneDirectorMixin.NEW_TENANT_CLEANUP()
        actions.modify_objects()

    def _run_common_area_cleanup(self):
        actions = ApartmentZoneDirectorMixin.COMMON_AREA_CLEANUP.actions()
        plex_service = services.get_plex_service()

        def object_criteria(obj):
            return plex_service.get_plex_zone_at_position(obj.position, obj.level) is None

        actions.modify_objects(object_criteria=object_criteria)
ASPIRATION_TIMEOUTS = 'aspiration_timeouts'
class ApartmentZoneDirectorPlayer(ApartmentZoneDirectorMixin, ZoneDirectorResidentialPlayer):
    INSTANCE_TUNABLES = {'neighbor_reaction_events': TunableMapping(description='\n            A map of different neighbor reaction event listeners that we want\n            to keep active on the Sims while this zone director is running and\n            the situations to create when those event listeners are completed.\n            ', key_type=TunableReference(description='\n                The aspiration that we will register on all of the active\n                household Sims that when completed will then trigger the\n                appropriate situation.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='ZoneDirectorEventListener'), value_type=TunableTuple(description='\n                Extra data for this specific aspiration.\n                ', timeout=TunableSimMinute(description='\n                    The amount of time in Sim Minutes that will pass from the\n                    completion of the aspiration before we will start the\n                    situation again.\n                    ', minimum=0, default=60), situation=TunableReference(description='\n                    The Situation that we want to start on the completion of\n                    this aspiration.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION))))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._aspiration_timeouts = {}

    def _save_custom_zone_director(self, zone_director_proto, writer):
        aspiration_timeouts = []
        for (aspiration, timeout) in self._aspiration_timeouts.items():
            aspiration_timeouts.append(aspiration.guid64)
            aspiration_timeouts.append(timeout.absolute_ticks())
        writer.write_uint64s(ASPIRATION_TIMEOUTS, aspiration_timeouts)
        super()._save_custom_zone_director(zone_director_proto, writer)

    def _load_custom_zone_director(self, zone_director_proto, reader):
        if reader is not None:
            aspiration_timeouts = reader.read_uint64s(ASPIRATION_TIMEOUTS, [])
            aspiration_manager = services.get_instance_manager(sims4.resources.Types.ASPIRATION)
            self._aspiration_timeouts = {aspiration_manager.get(aspiration_id): DateAndTime(timeout) for (aspiration_id, timeout) in zip(aspiration_timeouts[::2], aspiration_timeouts[1::2])}
        super()._load_custom_zone_director(zone_director_proto, reader)

    def on_sim_added_to_skewer(self, sim_info):
        self._register_zone_aspriations_for_sim(sim_info)

    def on_spawn_sim_for_zone_spin_up_completed(self):
        for sim_info in services.active_household():
            self._register_zone_aspriations_for_sim(sim_info)

    def _register_zone_aspriations_for_sim(self, sim_info):
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            return
        for aspiration in self.neighbor_reaction_events.keys():
            sim_info.aspiration_tracker.reset_milestone(aspiration)
            aspiration.register_callbacks()
            sim_info.aspiration_tracker.process_test_events_for_aspiration(aspiration)

    def on_zone_director_aspiration_completed(self, completed_aspiration, sim_info):
        sim_info.aspiration_tracker.reset_milestone(completed_aspiration)
        now = services.time_service().sim_now
        if completed_aspiration in self._aspiration_timeouts and now < self._aspiration_timeouts[completed_aspiration]:
            return
        aspiration_data = self.neighbor_reaction_events[completed_aspiration]
        self._aspiration_timeouts[completed_aspiration] = now + create_time_span(minutes=aspiration_data.timeout)
        guest_list = aspiration_data.situation.get_predefined_guest_list()
        if guest_list is None:
            guest_list = SituationGuestList(invite_only=True)
        services.get_zone_situation_manager().create_situation(aspiration_data.situation, guest_list=guest_list, user_facing=False, creation_source=self.instance_name)

class ApartmentZoneDirectorNPC(ApartmentZoneDirectorMixin, ZoneDirectorResidentialNPC):
    pass
