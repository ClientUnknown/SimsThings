from _weakrefset import WeakSetfrom protocolbuffers import GameplaySaveData_pb2from date_and_time import create_time_span, date_and_time_from_week_time, TimeSpan, DateAndTimefrom distributor.system import Distributorfrom element_utils import build_elementfrom elements import GeneratorElementfrom event_testing.test_events import TestEventfrom objects.components.types import SEASON_AWARE_COMPONENTfrom scheduling import Timelinefrom seasons.season_ops import SeasonInterpolationOp, SeasonUpdateOp, SeasonParameterUpdateOp, CrossSeasonInterpolationOpfrom seasons.seasons_enums import SeasonLength, SeasonType, SeasonParameters, SeasonSetSourcefrom seasons.seasons_tuning import SeasonsTuningfrom sims4.common import Packfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import Tunablefrom sims4.utils import classpropertyimport build_buyimport date_and_timeimport elementsimport persistence_error_typesimport servicesimport sims4.loglogger = sims4.log.Logger('seasons', default_owner='jdimailig')
class SeasonService(Service):
    MAX_TIME_SLICE_MILLISECONDS = Tunable(description='\n        The maximum alloted time for the script-side time slice in milliseconds.\n        ', tunable_type=int, default=50)
    MAX_WRAPPING_SEASONAL_PARAMETER_VALUE = 1.0
    MIN_WRAPPING_SEASONAL_PARAMETER_VALUE = -1.0
    WRAPPING_SEASONAL_PARAMETER_RANGE = MAX_WRAPPING_SEASONAL_PARAMETER_VALUE - MIN_WRAPPING_SEASONAL_PARAMETER_VALUE
    HALF_WRAPPING_SEASONAL_PARAMETER_RANGE = WRAPPING_SEASONAL_PARAMETER_RANGE/2.0

    def __init__(self, *_, **__):
        self._season = None
        self._preferred_initial_season = None
        self._season_content = None
        self._start_of_season = None
        self._season_length_span = None
        self._season_length_selected = None
        self._season_timeline = None
        self._season_change_handler = None
        self._client_interpolation_handler = None
        self._season_aware_object_handler = None
        self._season_screen_slam_handler = None
        self._regional_seasonal_parameters_index = {}
        self._regional_seasonal_parameters_handles = {}

    @classproperty
    def required_packs(cls):
        return (Pack.EP05,)

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_SEASON_SERVICE

    def setup(self, save_slot_data=None, **__):
        if save_slot_data.gameplay_data.HasField('season_service'):
            persisted_season_service = save_slot_data.gameplay_data.season_service
            self._restore_season_data(persisted_season_service.current_season, persisted_season_service.season_start_time)

    def save(self, save_slot_data=None, **__):
        if self._season is None:
            return
        seasons_proto = GameplaySaveData_pb2.PersistableSeasonService()
        seasons_proto.current_season = self._season.value
        seasons_proto.season_start_time = self._season_content.start_time
        save_slot_data.gameplay_data.season_service = seasons_proto

    def load_options(self, options_proto):
        self._season_length_selected = SeasonLength(options_proto.season_length)
        self._season_length_span = SeasonsTuning.SEASON_LENGTH_OPTIONS[self._season_length_selected]()
        if options_proto.HasField('initial_season'):
            self._preferred_initial_season = SeasonType(options_proto.initial_season)

    def save_options(self, options_proto):
        options_proto.season_length = self._season_length_selected.value

    def on_zone_load(self):
        if self._season is None:
            self._set_initial_season()
        now = services.time_service().sim_now
        if self._season_timeline is None:
            self._season_timeline = Timeline(now)
        self.set_season_length(self._season_length_selected)
        self._schedule_season_change()
        self._send_interpolation_update(mid_season_op=now >= self._season_content.midpoint_time)
        self.reset_region_season_params()
        self._setup_regional_seasonal_changes()
        self._send_season_ui_update()

    @property
    def season(self):
        return self._season

    @property
    def season_content(self):
        return self._season_content

    @property
    def season_length(self):
        return self._season_length_span

    @property
    def season_length_option(self):
        return self._season_length_selected

    @property
    def next_season(self):
        return SeasonType((self._season.value + 1) % len(SeasonType))

    def get_four_seasons(self):
        return self.get_seasons(len(SeasonType))

    def get_seasons(self, num_seasons):
        season_data = []
        if num_seasons < 1:
            return season_data
        season = self._season
        content = self._season_content
        season_data.append((season, content))
        for _ in range(1, num_seasons):
            (season, content) = self.get_next_season(season, content)
            season_data.append((season, content))
        return season_data

    def get_next_season(self, season_type, season_content):
        next_season = SeasonType((season_type.value + 1) % len(SeasonType))
        next_content = SeasonsTuning.SEASON_TYPE_MAPPING[next_season](season_content.end_time)
        next_content.set_length_option(self._season_length_selected)
        return (next_season, next_content)

    def get_seasons_gen(self):
        season = self._season
        content = self._season_content
        yield (season, content)
        while True:
            (season, content) = self.get_next_season(season, content)
            yield (season, content)

    def get_season_and_segments(self, start_time, days, max_seasons=4):
        season_segment_list = []
        day_time_span = create_time_span(days=1)
        for (season, season_content) in self.get_seasons_gen():
            while start_time in season_content:
                segment = season_content.get_segment(start_time)
                season_segment_list.append((season, segment))
                days = days - 1
                if days == 0:
                    return season_segment_list
                start_time = start_time + day_time_span
            max_seasons = max_seasons - 1
            if max_seasons == 0:
                break
        return season_segment_list

    def get_timeline_element_infos(self):
        scheduled_handles = tuple(handle for handle in self._season_timeline.heap if handle.is_scheduled)
        return tuple((str(handle.when), handle.element) for handle in scheduled_handles)

    def _add_secondary_forward_wraparound_interp(self, seasonal_parameter, start_time, start_value, end_time, end_value, force_loop, sync_end_time=None):
        target_value = None
        new_end_value = end_value
        if end_value < start_value:
            if end_value == SeasonService.MIN_WRAPPING_SEASONAL_PARAMETER_VALUE:
                new_end_value = SeasonService.MAX_WRAPPING_SEASONAL_PARAMETER_VALUE
            elif start_value == SeasonService.MAX_WRAPPING_SEASONAL_PARAMETER_VALUE:
                start_value = SeasonService.MIN_WRAPPING_SEASONAL_PARAMETER_VALUE
            else:
                target_value = SeasonService.MAX_WRAPPING_SEASONAL_PARAMETER_VALUE
        elif force_loop:
            if end_value == SeasonService.MIN_WRAPPING_SEASONAL_PARAMETER_VALUE:
                new_end_value = SeasonService.MAX_WRAPPING_SEASONAL_PARAMETER_VALUE
            else:
                target_value = SeasonService.MAX_WRAPPING_SEASONAL_PARAMETER_VALUE
        if target_value is not None:
            if sync_end_time is None:
                delta = start_value - end_value
                total_dist = SeasonService.WRAPPING_SEASONAL_PARAMETER_RANGE - delta
                percent_of_interp = (SeasonService.MAX_WRAPPING_SEASONAL_PARAMETER_VALUE - start_value)/total_dist
                new_end_time = start_time + (end_time - start_time)*percent_of_interp
            else:
                new_end_time = sync_end_time

            def _regional_set_season_interp():
                self._send_regional_season_change_update(seasonal_parameter, -target_value, new_end_time, end_value, end_time)

            if seasonal_parameter in self._regional_seasonal_parameters_handles:
                self._regional_seasonal_parameters_handles[seasonal_parameter].trigger_hard_stop()
            self._regional_seasonal_parameters_handles[seasonal_parameter] = self._season_timeline.schedule(build_element((lambda _: _regional_set_season_interp(),)), new_end_time)
            new_end_value = target_value
        elif sync_end_time is not None:
            new_end_time = sync_end_time
        else:
            new_end_time = end_time
        return (start_value, new_end_value, new_end_time)

    def set_season(self, season_type, source, interp_time=None):
        if self._season == season_type:
            return
        previous = self._season
        next_season = season_type
        if interp_time is None:
            self._season = season_type
            natural_progression = source == SeasonSetSource.PROGRESSION
            self._set_season_start_time(services.time_service().sim_now.start_of_week(), reset_region_params=not natural_progression)
            self.handle_season_content_updated(setup_regional_params=not natural_progression)
            self._handle_season_screen_slam(source)
        else:
            start_time = services.time_service().sim_now
            end_time = start_time + create_time_span(minutes=interp_time)
            new_season_start_time = services.time_service().sim_now.start_of_week()
            elapsed_time_into = start_time - self._season_content.start_time
            percent_into_start_season = float(elapsed_time_into.in_ticks())/float(self._season_length_span.in_ticks())
            elapsed_time_into = end_time - new_season_start_time
            percent_into_end_season = float(elapsed_time_into.in_ticks())/float(self._season_length_span.in_ticks())
            op = CrossSeasonInterpolationOp(previous, percent_into_start_season, start_time, next_season, percent_into_end_season, end_time)
            force_loop = op.is_over_half
            Distributor.instance().add_op_with_no_owner(op)
            if services.weather_service().adjust_weather_for_set_season(interp_time):
                start_time = start_time + create_time_span(minutes=interp_time/2)
            param_to_start_value = {}
            region = services.current_region()
            if region is not None:
                for seasonal_parameter in region.seasonal_parameters.keys():
                    (start_value, _, _, _) = self._get_regional_season_change_values(seasonal_parameter, start_time, region)
                    param_to_start_value[seasonal_parameter] = start_value
            self._season = season_type
            self._set_season_start_time(new_season_start_time)
            self.handle_season_content_updated(delay=True)
            self._handle_season_screen_slam(source)

            def _send_update():
                sync_end_time = None
                for seasonal_parameter in SeasonParameters:
                    if seasonal_parameter not in param_to_start_value:
                        pass
                    else:
                        start_value = param_to_start_value[seasonal_parameter]
                        new_end_time = end_time
                        (end_value, _, _, _) = self._get_regional_season_change_values(seasonal_parameter, end_time, region)
                        if seasonal_parameter == SeasonParameters.FOLIAGE_REDUCTION:
                            (start_value, end_value, new_end_time) = self._add_secondary_forward_wraparound_interp(seasonal_parameter, start_time, start_value, end_time, end_value, force_loop)
                            if end_time != new_end_time:
                                sync_end_time = new_end_time
                        if SeasonParameters.FOLIAGE_REDUCTION in param_to_start_value:
                            (start_value, end_value, new_end_time) = self._add_secondary_forward_wraparound_interp(seasonal_parameter, start_time, start_value, end_time, end_value, force_loop, sync_end_time=sync_end_time)
                        if seasonal_parameter == SeasonParameters.FOLIAGE_COLORSHIFT and end_value != start_value:
                            self._send_regional_season_change_update(seasonal_parameter, start_value, start_time, end_value, new_end_time)
                if self._season_change_handler is not None and not self._season_change_handler.is_active:
                    self._season_change_handler.trigger_hard_stop()
                self._season_change_handler = self._season_timeline.schedule(build_element((lambda _: self._handle_season_content_delayed(trigger_weather=True),)), end_time)

            self._season_change_handler = self._season_timeline.schedule(build_element((lambda _: _send_update(),)), start_time)
        self._schedule_season_aware_object_updates()
        services.get_event_manager().process_event(TestEvent.SeasonChangedNoSim, previous_season=previous, current_season=next_season)
        services.get_event_manager().process_events_for_household(TestEvent.SeasonChanged, services.active_household(), previous_season=previous, current_season=next_season)

    def advance_season(self, source):
        self.set_season(self.next_season, source)

    def set_season_length(self, season_length):
        self._season_length_selected = season_length
        self._season_content.set_length_option(self._season_length_selected)
        self._adjust_season_for_length_change()

    def shift_season_by_weeks(self, num_weeks):
        self._set_season_start_time(date_and_time_from_week_time(num_weeks, self._season_content.start_time))

    def reset_region_season_params(self):
        self._regional_seasonal_parameters_index.clear()

    def update(self):
        if self._season_timeline is None:
            self._season_timeline = Timeline(services.time_service().sim_now)
        self._season_timeline.simulate(services.time_service().sim_now, max_time_ms=self.MAX_TIME_SLICE_MILLISECONDS)

    def _schedule_season_aware_object_updates(self):
        if self._season_aware_object_handler is not None:
            self._season_aware_object_handler.trigger_hard_stop()
        self._season_aware_object_handler = self._season_timeline.schedule(GeneratorElement(self._update_season_aware_objects_gen))

    def _update_season_aware_objects_gen(self, timeline):
        for season_aware_object in WeakSet(services.object_manager().get_all_objects_with_component_gen(SEASON_AWARE_COMPONENT)):
            yield timeline.run_child(elements.SleepElement(TimeSpan.ZERO))
            season_aware_object.season_aware_component.on_season_set(self.season)

    def _set_initial_season(self):
        now = services.time_service().sim_now
        if self._preferred_initial_season is not None:
            self._season = self._preferred_initial_season
        else:
            starting_season = SeasonsTuning.STARTING_SEASON
            if self._season_length_selected == SeasonLength.NORMAL and now.time_since_beginning_of_week() >= starting_season.alternate_season.threshold():
                self._season = starting_season.alternate_season.season
            else:
                self._season = starting_season.default_season
        self._season_content = SeasonsTuning.SEASON_TYPE_MAPPING[self._season](now.start_of_week())

    def _restore_season_data(self, persisted_season_type, persisted_season_start):
        self._season = SeasonType(persisted_season_type)
        self._set_season_start_time(DateAndTime(persisted_season_start))

    def _set_season_start_time(self, start_time, reset_region_params=True):
        self._season_content = SeasonsTuning.SEASON_TYPE_MAPPING[self._season](start_time)
        if self._client_interpolation_handler is not None:
            self._client_interpolation_handler.trigger_hard_stop()
            self._client_interpolation_handler = None
        if reset_region_params:
            for seasonal_parameter_handler in self._regional_seasonal_parameters_handles.values():
                seasonal_parameter_handler.trigger_hard_stop()
            self._regional_seasonal_parameters_handles.clear()
        if self._season_length_selected is not None:
            self._season_content.set_length_option(self._season_length_selected)

    def _handle_season_content_delayed(self, setup_regional_params=True, trigger_weather=False):
        self._schedule_season_change()
        self._send_interpolation_update(mid_season_op=services.time_service().sim_now >= self._season_content.midpoint_time)
        if setup_regional_params:
            self._setup_regional_seasonal_changes()
        if trigger_weather:
            services.weather_service().reset_forecasts()

    def handle_season_content_updated(self, setup_regional_params=True, delay=False):
        services.holiday_service().on_season_content_changed()
        if not delay:
            self._handle_season_content_delayed(setup_regional_params=setup_regional_params)
        self._send_season_ui_update()

    def _schedule_season_change(self):
        if self._season_change_handler is not None and not self._season_change_handler.is_active:
            self._season_change_handler.trigger_hard_stop()
        self._season_change_handler = self._season_timeline.schedule(build_element((lambda _: self.advance_season(SeasonSetSource.PROGRESSION),)), self._season_content.end_time)

    def _handle_season_screen_slam(self, source):
        if source == SeasonSetSource.PROGRESSION:
            self._schedule_season_screen_slam()
        else:
            self._send_screen_slam_message()

    def _schedule_season_screen_slam(self):
        if self._season_screen_slam_handler is not None:
            self._season_screen_slam_handler.trigger_hard_stop()
        scheduled_time = self._season_content.get_screen_slam_trigger_time()
        if scheduled_time is None:
            return
        self._season_screen_slam_handler = self._season_timeline.schedule(build_element((lambda _: self._send_screen_slam_message(),)), scheduled_time)

    def _send_screen_slam_message(self):
        screen_slam = None if self._season_content.screen_slam is None else self._season_content.screen_slam.slam
        if screen_slam is not None:
            screen_slam.send_screen_slam_message(services.active_sim_info())

    def _schedule_mid_season_interpolation_update(self):
        if self._client_interpolation_handler is not None:
            self._client_interpolation_handler.trigger_hard_stop()
        self._client_interpolation_handler = self._season_timeline.schedule(build_element((lambda _: self._send_interpolation_update(mid_season_op=True),)), self._season_content.midpoint_time)

    def _send_interpolation_update(self, mid_season_op=False):
        season_service = services.season_service()
        season = season_service.season
        content = season_service.season_content
        op = SeasonInterpolationOp(season, content, mid_season_op)
        Distributor.instance().add_op_with_no_owner(op)
        if not mid_season_op:
            self._schedule_mid_season_interpolation_update()

    def _get_wrapped_value(self, seasonal_parameter, current_value, next_value):
        if seasonal_parameter == SeasonParameters.FOLIAGE_REDUCTION or seasonal_parameter == SeasonParameters.FOLIAGE_COLORSHIFT:
            if abs(next_value) == abs(current_value) and abs(current_value) == SeasonService.MAX_WRAPPING_SEASONAL_PARAMETER_VALUE:
                return next_value
            if next_value < 0.0 and current_value > 0.0:
                logger.error('Seasonal Parameter {} frame values going backwards from positive to negative.  Perhaps should wrap the other way.  This is safely handled when both frame values are 1 or -1', seasonal_parameter, owner='nabaker')
        return current_value

    def _get_regional_season_change_values(self, seasonal_parameter, time, region):
        seasons = self.get_four_seasons()
        lowest_time = None
        next_index = 0
        index = 0
        next_season_to_use = None
        changes = region.seasonal_parameters.get(seasonal_parameter)
        for frame in changes:
            for (season_type, season_instance) in seasons:
                if frame.season == season_type:
                    time_for_frame = season_instance.get_date_at_season_progress(frame.time_in_season)
                    break
            time_till_frame = time_for_frame - time
            if time_till_frame < TimeSpan.ZERO:
                time_till_frame += self._season_length_span*len(SeasonType)
            if lowest_time is None or time_till_frame < lowest_time:
                lowest_time = time_till_frame
                next_index = index
                next_season_to_use = season_instance
            index += 1
        next_frame = changes[next_index]
        end_time = next_season_to_use.get_date_at_season_progress(next_frame.time_in_season)
        previous_frame = changes[next_index - 1]
        previous_value = previous_frame.value
        next_value = next_frame.value
        current_value = self._get_wrapped_value(seasonal_parameter, previous_value, next_value)
        if current_value != next_value:
            if previous_frame.season == self.season:
                previous_frame_start = self.season_content.get_date_at_season_progress(previous_frame.time_in_season)
            else:
                seasons_difference = int(previous_frame.season) - int(next_frame.season)
                if seasons_difference > 0:
                    seasons_difference -= len(SeasonType)
                previous_frame_start = self._season_content.start_time + self._season_length_span*seasons_difference + self._season_length_span*previous_frame.time_in_season
            difference_between_times = end_time.absolute_ticks() - previous_frame_start.absolute_ticks()
            percent_between_times = 0 if difference_between_times == 0 else (time.absolute_ticks() - previous_frame_start.absolute_ticks())/difference_between_times
            current_value = percent_between_times*(next_value - previous_value) + previous_value
        return (current_value, next_frame, end_time, next_index)

    def _send_regional_season_change_update(self, seasonal_parameter, start_value, start_time, end_value, end_time):
        op = SeasonParameterUpdateOp(seasonal_parameter, start_value, start_time, end_value, end_time)
        Distributor.instance().add_op_with_no_owner(op)
        if seasonal_parameter == SeasonParameters.LEAF_ACCUMULATION:
            build_buy.request_season_weather_interpolation(services.current_zone_id(), seasonal_parameter, int(start_time/date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND), int(end_time/date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND), start_value, end_value)

    def _process_regional_season_change_update(self, seasonal_parameter):
        region = services.current_region()
        if region is None:
            return
        current_index = self._regional_seasonal_parameters_index.get(seasonal_parameter)
        start_time = services.time_service().sim_now
        if current_index is None:
            (current_value, next_frame, end_time, next_index) = self._get_regional_season_change_values(seasonal_parameter, start_time, region)
        else:
            changes = region.seasonal_parameters.get(seasonal_parameter)
            current_frame = changes[current_index]
            current_value = current_frame.value
            next_index = (current_index + 1) % len(changes)
            next_frame = changes[next_index]
            current_value = self._get_wrapped_value(seasonal_parameter, current_value, next_frame.value)
            for (season_type, season_instance) in self.get_seasons_gen():
                if season_type == next_frame.season:
                    next_season_to_use = season_instance
                    break
            end_time = next_season_to_use.get_date_at_season_progress(next_frame.time_in_season)
            if end_time < start_time:
                end_time = start_time
        self._regional_seasonal_parameters_index[seasonal_parameter] = next_index
        self._send_regional_season_change_update(seasonal_parameter, current_value, start_time, next_frame.value, end_time)
        self._regional_seasonal_parameters_handles[seasonal_parameter] = self._season_timeline.schedule(build_element((lambda _: self._process_regional_season_change_update(seasonal_parameter),)), end_time)

    def _setup_regional_seasonal_changes(self):
        region = services.current_region()
        if region is None:
            return
        for param_handler in self._regional_seasonal_parameters_handles.values():
            param_handler.trigger_hard_stop()
        self._regional_seasonal_parameters_handles.clear()
        for seasonal_parameter in region.seasonal_parameters.keys():
            self._process_regional_season_change_update(seasonal_parameter)

    def _adjust_season_for_length_change(self):
        now = services.time_service().sim_now
        if now in self._season_content:
            return
        shift_unit = 1 if now > self._season_content.end_time else -1
        while now not in self._season_content:
            self.shift_season_by_weeks(shift_unit)

    def _send_season_ui_update(self):
        season_service = services.season_service()
        season = season_service.season
        content = season_service.season_content
        op = SeasonUpdateOp(season, content)
        Distributor.instance().add_op_with_no_owner(op)
