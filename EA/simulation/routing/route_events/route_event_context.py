from _collections import defaultdictfrom random import shuffle, random, uniformimport operatorimport weakreffrom event_testing.resolver import SingleSimResolver, SingleObjectResolverfrom routing.portals.portal_tuning import PortalTypefrom routing.route_enums import RouteEventTypefrom routing.route_events.route_event_mixins import RouteEventBasefrom routing.route_events.route_event_utils import RouteEventSchedulePreferenceimport gsi_handlersimport objectsimport sims4.logimport sims4.mathlogger = sims4.log.Logger('RouteEvents', default_owner='rmccord')DURATION_SCALING_FOR_FAKE_STRAIGHT_ROUTE_EVENT = 0.25
class _RouteDurationBucket:

    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time

    def __repr__(self):
        return '<{} - {}>'.format(self.start_time, self.end_time)

    def __eq__(self, other):
        return self.start_time == other.start_time and self.end_time == other.end_time

    def __contains__(self, time):
        return self.start_time <= time <= self.end_time

    @property
    def duration(self):
        return self.end_time - self.start_time

class _RouteDuration:
    MINIMUM_BUCKET_SIZE = 0.1

    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time
        self.buckets = [_RouteDurationBucket(start_time, end_time)]

    def add_event(self, route_event, time):
        end_time = time + route_event.duration
        bucket = None
        for (idx, bucket) in enumerate(self.buckets):
            if time in bucket:
                break
        return
        next_bucket = _RouteDurationBucket(end_time, bucket.end_time)
        bucket.end_time = time
        kept = 1
        if bucket.start_time >= bucket.end_time:
            kept = 0
            self.buckets.remove(bucket)
        if next_bucket.start_time < next_bucket.end_time:
            self.buckets.insert(idx + kept, next_bucket)

    def fill_with_route_events(self, route_event_timing):
        num_filled = 0
        if self.buckets:
            for (route_event, time) in route_event_timing:
                if time < self.buckets[0].start_time:
                    pass
                else:
                    self.add_event(route_event, time)
                    num_filled += 1
        return num_filled

    def _get_start_time_for_straight_path_event(self, path, bucket, duration, offset_time, straight_duration, earliest_time, schedule_preference, specific_time=None):
        adjusted_bucket_start = max(bucket.start_time, earliest_time)
        start_index = max(0, path.node_at_time(bucket.start_time).index - 1)
        end_index = max(start_index, path.node_at_time(bucket.end_time).index)
        indices = list(range(start_index + 1, end_index + 1))
        if schedule_preference == RouteEventSchedulePreference.RANDOM:
            shuffle(indices)
        for index in indices:
            cur_node = path.nodes[index]
            prev_node = path.nodes[index - 1]
            start_time = max(adjusted_bucket_start, prev_node.time)
            end_time = min(bucket.end_time, cur_node.time)
            segment_time = end_time - start_time
            if segment_time < straight_duration:
                pass
            else:
                straight_path_earliest_start = start_time
                if start_time - offset_time < adjusted_bucket_start:
                    straight_path_earliest_start = adjusted_bucket_start + offset_time
                straight_path_latest_start = end_time - straight_duration
                duration_after_straight_path_start = duration - offset_time
                if straight_path_latest_start + duration_after_straight_path_start > bucket.end_time:
                    straight_path_latest_start = bucket.end_time - duration_after_straight_path_start
                if straight_path_latest_start < straight_path_earliest_start:
                    pass
                else:
                    if specific_time is not None:
                        specific_straight_path_start = specific_time + offset_time
                        if specific_straight_path_start >= straight_path_earliest_start and specific_straight_path_start <= straight_path_latest_start:
                            return specific_time
                            return straight_path_start - offset_time
                    elif schedule_preference == RouteEventSchedulePreference.RANDOM:
                        straight_path_start = uniform(straight_path_earliest_start, straight_path_latest_start)
                    else:
                        straight_path_start = straight_path_earliest_start
                    return straight_path_start - offset_time

    def fill_and_get_start_time_for_route_event(self, route_event, path, repeat_event=False, schedule_preference=RouteEventSchedulePreference.BEGINNING):
        if not route_event.event_data.is_valid_for_scheduling(path.sim, path):
            return
        duration = route_event.duration
        time = route_event.time
        earliest_time = route_event.earliest_repeat_time if repeat_event else 0
        if route_event.scheduling_override is not None:
            schedule_preference = route_event.scheduling_override
        if repeat_event or schedule_preference == RouteEventSchedulePreference.BEGINNING:
            buckets = sorted(self.buckets, key=operator.attrgetter('start_time'))
        elif schedule_preference == RouteEventSchedulePreference.END:
            buckets = sorted(self.buckets, key=operator.attrgetter('start_time'), reverse=True)
        elif schedule_preference == RouteEventSchedulePreference.RANDOM:
            buckets = list(self.buckets)
            shuffle(buckets)
        straight_path_tuning = route_event.prefer_straight_paths
        if straight_path_tuning is not None:
            straight_percentage = straight_path_tuning.straight_path_percentage
            straight_duration = duration*straight_percentage
            if straight_path_tuning.straight_path_offset is not None:
                offset_time = duration*route_event.prefer_straight_paths.straight_path_offset
            else:
                offset_time = duration*(0.5 - straight_percentage*0.5)
        for (idx, bucket) in enumerate(buckets):
            if bucket.duration < duration:
                pass
            elif bucket.end_time - duration < earliest_time:
                pass
            elif not (time is not None and bucket.start_time > time):
                if bucket.end_time - duration < time:
                    pass
                elif straight_path_tuning is None:
                    if time is not None:
                        break
                    if schedule_preference == RouteEventSchedulePreference.BEGINNING:
                        time = max(bucket.start_time, earliest_time)
                    elif schedule_preference == RouteEventSchedulePreference.END:
                        time = bucket.end_time - duration
                    else:
                        start_time = max(bucket.start_time, earliest_time)
                        time = uniform(start_time, bucket.end_time - duration)
                    break
                else:
                    time = self._get_start_time_for_straight_path_event(path, bucket, duration, offset_time, straight_duration, earliest_time, schedule_preference, specific_time=time)
                    if time is not None:
                        break
        return
        end_time = time + duration
        if time - bucket.start_time < _RouteDuration.MINIMUM_BUCKET_SIZE:
            bucket.start_time = end_time
        elif bucket.end_time - end_time < _RouteDuration.MINIMUM_BUCKET_SIZE:
            bucket.end_time = time
        else:
            next_bucket = _RouteDurationBucket(end_time, bucket.end_time)
            bucket.end_time = time
            self.buckets.insert(idx + 1, next_bucket)
        return time

class RouteEventContext:
    ROUTE_TRIM_START = 0.25
    ROUTE_TRIM_END = 0
    ROUTE_TRIM_DURATION = ROUTE_TRIM_START + ROUTE_TRIM_END
    ROUTE_EVENT_SCHEDULED_CAP = 50
    ROUTE_EVENT_CAPPED_COOLDOWN_THRESHOLD = 25

    class _RouteEventSchedulingData(RouteEventBase):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.prefer_straight_paths = False
            self.scheduling_override = None
            self.earliest_repeat_time = 0

        def copy_from(self, other):
            super().copy_from(other)
            self.scheduling_override = other.scheduling_override
            self.prefer_straight_paths = other.prefer_straight_paths

    def __init__(self):
        self._route_events_to_schedule = defaultdict(list)
        self._scheduled_events = []
        self._events_already_considered = defaultdict(set)
        self._has_hit_cap = False

    def has_pending_events_to_process(self):
        return any(not route_event.processed for (route_event, _) in self._scheduled_events)

    def add_route_event(self, route_event_type, route_event):
        logger.debug('ADDED: {}', route_event)
        self._route_events_to_schedule[route_event_type].append(route_event)

    def remove_route_event(self, route_event, time):
        self._scheduled_events.remove((route_event, time))

    def clear_route_events(self):
        self._route_events_to_schedule.clear()
        self._scheduled_events.clear()
        self._events_already_considered.clear()
        self._has_hit_cap = False

    def has_scheduled_events(self):
        if self._scheduled_events:
            return True
        return False

    def handle_route_event_executed(self, event_id, actor, path=None):
        for (route_event, time) in self._scheduled_events:
            if route_event.id == event_id:
                route_event.on_executed(actor, path=path)
                break
        return
        if path is not None and gsi_handlers.route_event_handlers.archiver.enabled:
            gsi_handlers.route_event_handlers.gsi_route_event_executed(path, actor, route_event)
        if route_event.event_data.should_remove_on_execute():
            self.remove_route_event(route_event, time)

    def handle_route_event_skipped(self, event_id, actor, path=None):
        for (route_event, time) in self._scheduled_events:
            if route_event.id == event_id:
                self.remove_route_event(route_event, time)
                return

    def remove_route_event_by_data(self, event_data):
        for (route_event, time) in self._scheduled_events:
            if route_event.event_data is event_data:
                self.remove_route_event(route_event, time)
                return

    def route_event_already_scheduled(self, route_event_cls, time=None, provider=None):
        for (route_event, event_time) in self._scheduled_events:
            if route_event_cls is type(route_event) and route_event.provider is provider:
                if time is not None and not sims4.math.almost_equal(time, event_time, epsilon=route_event.duration):
                    pass
                else:
                    return True
        return False

    def route_event_of_data_type_gen(self, route_event_data_cls):
        for (route_event, _) in self._scheduled_events:
            if route_event_data_cls is type(route_event.event_data):
                yield route_event

    def route_event_already_fully_considered(self, route_event_cls, provider):
        provider_ref = weakref.ref(provider)
        if provider_ref not in self._events_already_considered:
            return False
        return route_event_cls in self._events_already_considered[provider_ref]

    def prune_stale_events_and_get_failed_types(self, actor, path, current_time):
        self._route_events_to_schedule.clear()
        failed_events = []
        failed_event_types = set()
        if actor.is_sim:
            resolver = SingleSimResolver(actor.sim_info)
        else:
            resolver = SingleObjectResolver(actor)
        for (route_event, time) in self._scheduled_events:
            if type(route_event) in failed_event_types or not route_event.test(resolver, from_update=True):
                failed_events.append((route_event, time))
                failed_event_types.add(type(route_event))
            elif not route_event.is_route_event_valid(route_event, time, actor, path):
                failed_events.append((route_event, time))
        gsi_path_log = None
        if gsi_handlers.route_event_handlers.archiver.enabled:
            gsi_path_log = gsi_handlers.route_event_handlers.get_path_route_events_log(path)
        for (route_event, time) in failed_events:
            if gsi_path_log is not None:
                gsi_event_data = {'status': 'Removed'}
                gsi_handlers.route_event_handlers.gsi_fill_route_event_data(route_event, gsi_path_log, gsi_event_data)
            self.remove_route_event(route_event, time)
        return (failed_events, failed_event_types)

    def _test_gathered_events_for_chance(self, actor):
        if actor.is_sim:
            resolver = SingleSimResolver(actor.sim_info)
        else:
            resolver = SingleObjectResolver(actor)
        for (route_event_type, route_events) in self._route_events_to_schedule.items():
            for route_event in tuple(route_events):
                self._events_already_considered[route_event.provider_ref].add(type(route_event))
                if route_event_type != RouteEventType.LOW_REPEAT and random() > route_event.chance.get_chance(resolver):
                    route_events.remove(route_event)

    def schedule_route_events(self, actor, path, failed_event_types=None, start_time=0):
        total_duration = path.duration()
        if total_duration <= RouteEventContext.ROUTE_TRIM_DURATION:
            return
        num_route_events = 0
        added_events = []
        start_time = start_time + RouteEventContext.ROUTE_TRIM_START
        end_time = total_duration - RouteEventContext.ROUTE_TRIM_END
        time_buckets = _RouteDuration(start_time, end_time)
        num_route_events += time_buckets.fill_with_route_events(self._scheduled_events)
        self._test_gathered_events_for_chance(actor)

        def _schedule_route_events(route_event_priority, schedule_preference=RouteEventSchedulePreference.BEGINNING):
            nonlocal num_route_events
            for route_event in self._route_events_to_schedule[route_event_priority]:
                if failed_event_types is not None and type(route_event) in failed_event_types:
                    pass
                else:
                    route_event.prepare_route_event(actor)
                    time = time_buckets.fill_and_get_start_time_for_route_event(route_event, path=path, schedule_preference=schedule_preference)
                    if time is not None:
                        route_event.time = time
                        added_events.append((route_event, time))
                        num_route_events += 1

        if actor.is_sim:
            resolver = SingleSimResolver(actor.sim_info)
        else:
            resolver = SingleObjectResolver(actor)
        for route_event_type in reversed(RouteEventType):
            if route_event_type == RouteEventType.FIRST_OUTDOOR:
                _schedule_route_events(route_event_type)
            elif route_event_type == RouteEventType.LAST_OUTDOOR:
                _schedule_route_events(route_event_type)
            elif route_event_type == RouteEventType.INTERACTION_PRE:
                _schedule_route_events(route_event_type, schedule_preference=RouteEventSchedulePreference.END)
            elif route_event_type == RouteEventType.INTERACTION_POST:
                _schedule_route_events(route_event_type)
            elif route_event_type == RouteEventType.BROADCASTER:
                _schedule_route_events(route_event_type)
            elif route_event_type == RouteEventType.LOW_SINGLE:
                shuffle(self._route_events_to_schedule[route_event_type])
                _schedule_route_events(route_event_type, schedule_preference=RouteEventSchedulePreference.RANDOM)
            elif route_event_type == RouteEventType.LOW_REPEAT:
                if num_route_events > self.ROUTE_EVENT_CAPPED_COOLDOWN_THRESHOLD:
                    for route_event in self._route_events_to_schedule[RouteEventType.LOW_REPEAT]:
                        self._events_already_considered[route_event.provider_ref].remove(type(route_event))
                    break
                repeat_route_events = self._route_events_to_schedule[route_event_type]
                repeat_scheduling_data = []
                for route_event in repeat_route_events:
                    route_event.prepare_route_event(actor)
                    if not route_event.event_data.is_valid_for_scheduling(actor, path):
                        pass
                    elif route_event.duration <= 0:
                        logger.error('route event {} with 0 duration is being used as repeating. This would cause an infinite loop.', type(route_event))
                    else:
                        event_data = self._RouteEventSchedulingData()
                        event_data.copy_from(route_event)
                        repeat_scheduling_data.append((event_data, route_event.provider_ref, type(route_event), route_event.route_event_parameters))
                shuffle(repeat_scheduling_data)
                while self._has_hit_cap and len(repeat_scheduling_data) > 0:
                    if num_route_events > self.ROUTE_EVENT_SCHEDULED_CAP:
                        for (_, provider, route_event_cls, _) in repeat_scheduling_data:
                            self._events_already_considered[provider].remove(route_event_cls)
                            self._has_hit_cap = True
                        break
                    valid_scheduling_data = []
                    for (scheduling_data, provider, route_event_cls, kwargs) in repeat_scheduling_data:
                        if random() < route_event_cls.chance.get_chance(resolver):
                            schedule_preference = RouteEventSchedulePreference.RANDOM if scheduling_data.prefer_straight_paths else RouteEventSchedulePreference.BEGINNING
                            time = time_buckets.fill_and_get_start_time_for_route_event(scheduling_data, path=path, repeat_event=True, schedule_preference=schedule_preference)
                            if time is not None:
                                if schedule_preference == RouteEventSchedulePreference.BEGINNING:
                                    scheduling_data.earliest_repeat_time = time + scheduling_data.duration
                                route_event = route_event_cls(time=time, **kwargs)
                                route_event.prepare_route_event(actor)
                                added_events.append((route_event, time))
                                num_route_events += 1
                                if scheduling_data.earliest_repeat_time + scheduling_data.duration < time_buckets.end_time:
                                    valid_scheduling_data.append((scheduling_data, provider, route_event_cls, kwargs))
                        else:
                            scheduling_data.earliest_repeat_time += scheduling_data.duration*random()
                            if scheduling_data.earliest_repeat_time + scheduling_data.duration < time_buckets.end_time:
                                valid_scheduling_data.append((scheduling_data, provider, route_event_cls, kwargs))
                    repeat_scheduling_data = valid_scheduling_data
        portal_events = []
        for (route_event, time) in added_events:
            portal_event = None
            if not route_event.allowed_at_animated_portal:
                start_index = path.node_at_time(time).index - 1
                start_index = 0 if start_index < 0 else start_index
                end_index = path.node_at_time(time + route_event.duration).index
                end_index = start_index if end_index < start_index else end_index
                event_nodes = [path.nodes[index] for index in range(start_index, end_index)]
                for node in event_nodes:
                    if node.portal_id and node.portal_object_id:
                        portal_object = objects.system.find_object(node.portal_object_id)
                        if portal_object is not None and portal_object.get_portal_type(node.portal_id) != PortalType.PortalType_Walk:
                            portal_event = (route_event, time)
                            break
            if route_event.duration and portal_event is not None:
                portal_events.append(portal_event)
        for portal_event in portal_events:
            added_events.remove(portal_event)
        self.gsi_update_route_events(path, added_events, start_time)
        self._scheduled_events.extend(added_events)
        logger.debug('{} scheduled {} of {} route events.', actor, len(self._scheduled_events), len(self._route_events_to_schedule.values()))

    def gsi_update_route_events(self, path, added_events, start_time):
        gsi_path_log = None
        if gsi_handlers.route_event_handlers.archiver.enabled:
            gsi_path_log = gsi_handlers.route_event_handlers.get_path_route_events_log(path)
        if gsi_path_log is not None:
            for (route_event, time) in self._scheduled_events:
                gsi_event_data = {}
                if time <= start_time:
                    gsi_event_data['status'] = 'Past'
                else:
                    gsi_event_data['status'] = 'Persisted'
                gsi_handlers.route_event_handlers.gsi_fill_route_event_data(route_event, gsi_path_log, gsi_event_data)
            for (route_event, time) in added_events:
                gsi_event_data = {'status': 'Added', 'executed': False}
                gsi_handlers.route_event_handlers.gsi_fill_route_event_data(route_event, gsi_path_log, gsi_event_data)

    def process_route_events(self, actor):
        for (route_event, time) in self._scheduled_events:
            route_event.process(actor, time)

    def append_route_events_to_route_msg(self, route_msg):
        for (route_event, time) in self._scheduled_events:
            route_event.build_route_event_msg(route_msg, time)
