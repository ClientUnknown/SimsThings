from event_testing.test_events import TestEventfrom narrative.narrative_open_street_director_mixin import NarrativeOpenStreetDirectorMixinfrom open_street_director.open_street_director import OpenStreetDirectorBase, OpenStreetDirectorPriorityfrom scheduler import ObjectLayerWeeklySchedulefrom seasons.seasons_enums import SeasonTypefrom sims4.tuning.tunable import TunableMapping, TunableEnumEntryfrom sims4.utils import classpropertyfrom venues.scheduling_zone_director import SchedulingZoneDirectorMixinimport alarmsimport date_and_timeimport servicesimport sims4.loglogger = sims4.log.Logger('SchedulingOpenStreetDirector', default_owner='rmccord')
class SchedulingOpenStreetDirector(SchedulingZoneDirectorMixin, NarrativeOpenStreetDirectorMixin, OpenStreetDirectorBase):
    INSTANCE_TUNABLES = {'object_layer_schedule': ObjectLayerWeeklySchedule.TunableFactory(description='\n            The default object layer schedule for this open street director,\n            when no season is specified. (e.g. EP05 is not installed, or season not tuned.)\n            ', schedule_entry_data={'pack_safe': True}), 'seasonal_object_layer_schedule_mapping': TunableMapping(description='\n            A mapping of the season type to the object layer schedule for an\n            open street director.\n            ', key_type=TunableEnumEntry(description='\n                The season.\n                ', tunable_type=SeasonType, default=SeasonType.SUMMER), value_type=ObjectLayerWeeklySchedule.TunableFactory(description='\n                The object layer schedule for this open street director.\n                ', schedule_entry_data={'pack_safe': True}))}

    @classproperty
    def priority(cls):
        return OpenStreetDirectorPriority.CART

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._object_layer_schedule = None
        self._current_layers = {}
        self._destruction_alarms = {}
        self._layers_in_destruction = []
        if services.season_service() is not None:
            services.get_event_manager().register_single_event(self, TestEvent.SeasonChangedNoSim)

    def _create_new_object_layer_schedule(self, start_callback, init_only):
        season_service = services.season_service()
        if season_service is not None:
            season_object_layer_schedule = self.seasonal_object_layer_schedule_mapping.get(season_service.season, None)
            if season_object_layer_schedule is not None:
                return season_object_layer_schedule(start_callback=start_callback, init_only=init_only)
        return self.object_layer_schedule(start_callback=start_callback, init_only=init_only)

    def create_layer_schedule(self):
        if self._object_layer_schedule is None:
            self._object_layer_schedule = self._create_new_object_layer_schedule(self._setup_object_layer, True)
            now = services.time_service().sim_now
            (time_span, best_work_data) = self._object_layer_schedule.time_until_next_scheduled_event(now, schedule_immediate=True)
            if time_span == date_and_time.TimeSpan.ZERO:
                for alarm_data in best_work_data:
                    self._setup_object_layer(self._object_layer_schedule, alarm_data, None)
            self._object_layer_schedule.schedule_next_alarm(schedule_immediate=False)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.SeasonChangedNoSim:
            self._on_season_changed()
            return
        super().handle_event(sim_info, event, resolver)

    def _on_season_changed(self):
        self._remove_object_layer_schedule(all_layers=False)
        self.create_layer_schedule()

    def on_startup(self):
        super().on_startup()
        self.create_layer_schedule()

    def on_shutdown(self):
        self._remove_object_layer_schedule()
        if services.season_service() is not None:
            services.get_event_manager().unregister_single_event(self, TestEvent.SeasonChangedNoSim)
        super().on_shutdown()

    def _remove_object_layer_schedule(self, all_layers=True):
        if self._object_layer_schedule is None:
            return
        self._object_layer_schedule.destroy()
        self._object_layer_schedule = None
        layers_to_remove = tuple(self._loaded_layers) if all_layers else tuple(self._current_layers.keys())
        self._remove_layer_objects(layers_to_remove)
        self._current_layers.clear()
        for (alarm, _) in self._destruction_alarms.items():
            alarm.cancel()
        self._destruction_alarms.clear()

    def _clean_up(self):
        self.run_lot_cleanup()
        self._remove_object_layer_schedule()
        super()._clean_up()
        if not self._loaded_layers:
            self._ready_for_destruction = True
            self.request.on_open_director_shutdown()

    def _preroll(self, preroll_time):
        super()._preroll(preroll_time)
        self.create_layer_schedule()

    def create_situations_during_zone_spin_up(self):
        super().create_situations_during_zone_spin_up()

    def _prune_stale_situations(self, situation_ids):
        situation_manager = services.get_zone_situation_manager()
        return [situation_id for situation_id in situation_ids if situation_id in situation_manager]

    def on_layer_loaded(self, conditional_layer):
        super().on_layer_loaded(conditional_layer)
        if conditional_layer in self._current_layers:
            self._update_destruction_alarm(conditional_layer)

    def on_layer_objects_destroyed(self, conditional_layer):
        super().on_layer_objects_destroyed(conditional_layer)
        if self._being_cleaned_up:
            self._layers_in_destruction.remove(conditional_layer)
            if self._layers_in_destruction:
                return
            self._ready_for_destruction = True
            self.request.on_open_director_shutdown()
            return
        if self._prerolling:
            return
        if conditional_layer in self._layers_in_destruction:
            self._layers_in_destruction.remove(conditional_layer)
            if conditional_layer not in self._layers_in_destruction:
                layer_data = self._current_layers.get(conditional_layer)
                if layer_data is not None:
                    self._create_layer(conditional_layer, layer_data)

    def _setup_object_layer(self, scheduler, alarm_data, extra_data):
        if self._being_cleaned_up:
            logger.error('{} trying to setup a layer when being cleaned up', self)
            return
        conditional_layer = alarm_data.entry.conditional_layer
        if conditional_layer is not None:
            if conditional_layer not in self._current_layers:
                now = services.time_service().sim_now
                start_time = now + now.time_till_timespan_of_week(alarm_data.start_time, optional_end_time=alarm_data.end_time)
                end_time = now + now.time_till_timespan_of_week(alarm_data.end_time)
                self._create_layer(conditional_layer, start_time, end_time)
            else:
                (start_time, end_time, end_handle) = self._current_layers[conditional_layer]
                now = services.time_service().sim_now
                if end_time - now < alarm_data.end_time - now:
                    self._update_destruction_alarm(conditional_layer, alarm_data.end_time)
        else:
            logger.warn('An object layer schedule entry for {} has been tuned with no layer name.', self)

    def _update_destruction_alarm(self, conditional_layer, end_time=None):
        layer_data = self._current_layers.get(conditional_layer)
        (start_time, current_end_time, end_alarm_handle) = layer_data
        if end_alarm_handle is not None:
            end_alarm_handle.cancel()
        end_time = end_time or current_end_time
        timespan = end_time - services.time_service().sim_now
        end_alarm_handle = alarms.add_alarm(self, timespan, self._handle_destroy_layer_alarm)
        self._current_layers[conditional_layer] = (start_time, end_time, end_alarm_handle)
        self._destruction_alarms[end_alarm_handle] = conditional_layer

    def _create_layer(self, conditional_layer, start_time, end_time, end_alarm_handle=None):
        if self._prerolling:
            if conditional_layer in self._loaded_layers:
                self._update_destruction_alarm(conditional_layer, end_time)
            else:
                self._current_layers[conditional_layer] = (start_time, end_time, end_alarm_handle)
                self.load_layer_immediately(conditional_layer)
        else:
            self._current_layers[conditional_layer] = (start_time, end_time, end_alarm_handle)
            if conditional_layer not in self._layers_in_destruction:
                self.load_layer_gradually(conditional_layer)

    def _handle_destroy_layer_alarm(self, alarm_handle):
        conditional_layer = self._destruction_alarms.pop(alarm_handle)
        if conditional_layer is not None and conditional_layer in self._loaded_layers:
            self._destroy_layer(conditional_layer)
        else:
            logger.error('Trying to destroy a loaded object layer that no longer exists.')

    def _remove_layer_objects(self, layers):
        for conditional_layer in layers:
            self._destroy_layer(conditional_layer)

    def _destroy_layer(self, conditional_layer):
        self._layers_in_destruction.append(conditional_layer)
        if conditional_layer in self._current_layers:
            del self._current_layers[conditional_layer]
        self.remove_layer_objects(conditional_layer)

    def _load_custom_open_street_director(self, street_director_proto, reader):
        self._load_situation_shifts(street_director_proto, reader)
        super(SchedulingOpenStreetDirector, self)._load_custom_open_street_director(street_director_proto, reader)

    def _save_custom_open_street_director(self, street_director_proto, writer):
        self._save_situation_shifts(street_director_proto, writer)
        super(SchedulingOpenStreetDirector, self)._save_custom_open_street_director(street_director_proto, writer)
