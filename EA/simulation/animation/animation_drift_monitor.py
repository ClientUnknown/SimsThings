from _collections import dequefrom datetime import datetime, timedeltaimport itertoolsfrom date_and_time import TICKS_PER_REAL_WORLD_SECOND, TimeSpanfrom element_utils import build_critical_section_with_finally, build_elementfrom gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims.master_controller import _RunWorkGenElementfrom sims4.gsi.schema import GsiGridSchemaimport servicesimport sims4.logimport sims4.reloadlogger = sims4.log.Logger('Animation')with sims4.reload.protected(globals()):
    _animation_drift_monitor_records = deque(maxlen=4096)
def _get_now_time():
    return datetime.now()

def _get_simulation_now_time():
    return services.time_service().sim_now

def _format_datetime(dt):
    if isinstance(dt, datetime):
        return dt.strftime('%H:%M:%S.%f')
    return '{0:h}:{0:m}:{0:s}'.format(dt)

def _format_interval(interval):
    if isinstance(interval, timedelta):
        interval = interval.total_seconds()
    if isinstance(interval, TimeSpan):
        interval = interval.in_ticks()/TICKS_PER_REAL_WORLD_SECOND
    return '{0:.3f}'.format(interval)

class _AnimationDriftMonitorRecord:

    def __init__(self, animation_sleep_element):
        self.record_id = id(animation_sleep_element)
        self.record_name = None
        self.timestamp_sleep_start = None
        self.timestamp_sleep_end = None
        self.timestamp_sleep_sim_start = None
        self.timestamps_client_started = {arb.network_id: None for arb in animation_sleep_element.arbs}
        self.timestamps_client_completed = {arb.network_id: None for arb in animation_sleep_element.arbs}
        game_clock_service = services.game_clock_service()
        self.duration_multiplier = game_clock_service.current_clock_speed_scale() or 1
        self.duration_expected = animation_sleep_element._duration_must_run/self.duration_multiplier
        self.durations_client = {arb.network_id: None for arb in animation_sleep_element.arbs}
        self.durations_offset_client = {arb.network_id: None for arb in animation_sleep_element.arbs}
        self.client_timeline_contents = {arb.network_id: None for arb in animation_sleep_element.arbs}
        self.arb_contents_as_strings = {arb.network_id: arb.get_contents_as_string() for arb in animation_sleep_element.arbs}
        self._actor_ids = frozenset(itertools.chain.from_iterable(arb._actors(True) for arb in animation_sleep_element.arbs))
        self.additional_actor_debt = None
        self.resource_ids = ()
        parent_element = animation_sleep_element
        while parent_element is not None:
            required_resources = getattr(parent_element, '_required_sims_threading', None)
            if isinstance(parent_element, _RunWorkGenElement):
                required_resources = parent_element._work_entry.resources
                self.record_name = parent_element._work_entry._debug_name
            if required_resources is None and required_resources is not None:
                if self.record_name is None:
                    self.record_name = str(parent_element)
                self.resource_ids = tuple(r.id for r in required_resources)
                break
            parent_handle = parent_element._parent_handle
            parent_element = parent_handle.element if parent_handle is not None else None

    @property
    def arb_network_ids(self):
        return tuple(self.timestamps_client_completed)

    @property
    def duration_client(self):
        return sum(self.durations_client.values())

    @property
    def duration_offset_client(self):
        return sum(self.durations_offset_client.values())

    @property
    def duration_drift_server(self):
        duration_effective = self.timestamp_sleep_end - self.timestamp_sleep_start
        return self.duration_expected - duration_effective.total_seconds()

    @property
    def timestamp_client_completed(self):
        return max(self.timestamps_client_completed.values())

    @property
    def timestamp_client_started(self):
        return max(self.timestamps_client_started.values())

    def get_relevant_objects(self):
        object_manager = services.object_manager()
        relevant_objects = set()
        for actor_id in self._actor_ids:
            actor = object_manager.get(actor_id)
            if actor is not None and actor.is_sim:
                relevant_objects.add(actor)
        return relevant_objects

    def _on_arb_container_event(self, arb_network_id, container, *, fn):
        if arb_network_id in container:
            container[arb_network_id] = fn()

    def on_arb_complete(self, arb_network_id, arb_client_duration, arb_client_playback_delay, timeline_contents):
        self._on_arb_container_event(arb_network_id, self.timestamps_client_completed, fn=_get_now_time)
        self._on_arb_container_event(arb_network_id, self.durations_client, fn=lambda : arb_client_duration/self.duration_multiplier)
        self._on_arb_container_event(arb_network_id, self.durations_offset_client, fn=lambda : arb_client_playback_delay/self.duration_multiplier)
        self._on_arb_container_event(arb_network_id, self.client_timeline_contents, fn=lambda : timeline_contents)

    def on_arb_client_started(self, arb_network_id):
        self._on_arb_container_event(arb_network_id, self.timestamps_client_started, fn=_get_simulation_now_time)
animation_drift_archive_schema = GsiGridSchema(label='Animation Drift Monitor', sim_specific=True)animation_drift_archive_schema.add_field('record_name', label='Name', width=20)animation_drift_archive_schema.add_field('timestamp_sleep_start', label='Sleep Started (Real / Simulated)', width=10)animation_drift_archive_schema.add_field('timestamp_sleep_end', label='Sleep Ended', width=10)animation_drift_archive_schema.add_field('timestamp_client_completed', label='Client Completed', width=10)animation_drift_archive_schema.add_field('duration_expected', label='Expected Duration', width=5)animation_drift_archive_schema.add_field('duration_sleep', label='Server Duration', width=5)animation_drift_archive_schema.add_field('duration_client', label='Client Duration (Actual / Offset)', width=10)animation_drift_archive_schema.add_field('duration_drift_server', label='Server Sleep Drift', width=5)animation_drift_archive_schema.add_field('duration_drift', label='Client Drift', width=5)with animation_drift_archive_schema.add_has_many('Resources', GsiGridSchema) as sub_schema:
    sub_schema.add_field('resource_name', label='Name', width=20)
    sub_schema.add_field('resource_animation_properties', label='Animation Status', width=35)
    sub_schema.add_field('resource_master_controller_properties', label='Master Controller Status', width=20)
    sub_schema.add_field('resource_time_debt', label='Time Debt', width=20)
    sub_schema.add_field('resource_added_time_debt', label='Added Time Debt', width=20)with animation_drift_archive_schema.add_has_many('ARBs', GsiGridSchema) as sub_schema:
    sub_schema.add_field('arb', label='Contents', width=20)
    sub_schema.add_field('timeline_contents', label='Client Timeline Contents', width=20)
    sub_schema.add_field('timestamp_client_completed', label='Client Completed', width=35)
    sub_schema.add_field('duration_client', label='Client Duration', width=35)archiver = GameplayArchiver('animation_drift_archive', animation_drift_archive_schema, add_to_archive_enable_functions=True)
def is_archive_enabled():
    return archiver.enabled

def _animation_drift_monitor_archive(record):
    object_manager = services.object_manager()
    relevant_objects = record.get_relevant_objects()
    all_resources = set(relevant_objects)
    for resource_id in record.resource_ids:
        resource = object_manager.get(resource_id)
        if resource is not None and resource.is_sim:
            all_resources.add(resource)
    if record.record_name is not None:
        for relevant_object in relevant_objects:
            if relevant_object.id not in record.resource_ids:
                logger.warn('{}: {} animates on the normal timeline, but is not a required resource.', record.record_name, relevant_object)
    arb_accumulator_service = services.current_zone().arb_accumulator_service
    archive_data = {'record_name': record.record_name, 'timestamp_sleep_start': '{} / {}'.format(_format_datetime(record.timestamp_sleep_start), _format_datetime(record.timestamp_sleep_sim_start)), 'timestamp_sleep_end': _format_datetime(record.timestamp_sleep_end), 'timestamp_client_completed': _format_datetime(record.timestamp_client_completed), 'duration_expected': _format_interval(record.duration_expected), 'duration_sleep': _format_interval(record.timestamp_sleep_end - record.timestamp_sleep_start), 'duration_client': '{} / {}'.format(_format_interval(record.duration_client - record.duration_offset_client), _format_interval(record.duration_offset_client)), 'duration_drift_server': _format_interval(record.duration_drift_server), 'duration_drift': _format_interval(record.timestamp_client_started - record.timestamp_sleep_sim_start), 'Resources': [{'resource_name': str(resource), 'resource_animation_properties': 'Blocker' if resource in relevant_objects else 'Non-blocker', 'resource_master_controller_properties': 'Required' if resource.id in record.resource_ids else 'Not required', 'resource_time_debt': _format_interval(arb_accumulator_service.get_time_debt((resource,))), 'resource_added_time_debt': _format_interval(record.additional_actor_debt if resource in relevant_objects else 0)} for resource in all_resources], 'ARBs': [{'arb': record.arb_contents_as_strings[arb_network_id], 'timeline_contents': record.client_timeline_contents[arb_network_id], 'timestamp_client_completed': _format_datetime(record.timestamps_client_completed[arb_network_id]), 'duration_client': _format_interval(record.durations_client[arb_network_id])} for arb_network_id in record.arb_network_ids]}
    for obj in relevant_objects:
        archiver.archive(archive_data, object_id=obj.id)

def _remove_completed_records():
    completed_records = []
    for record in _animation_drift_monitor_records:
        if any(t is None for t in record.timestamps_client_started.values()):
            pass
        else:
            completed_records.append(record)
    arb_accumulator_service = services.current_zone().arb_accumulator_service
    for completed_record in completed_records:
        _animation_drift_monitor_records.remove(completed_record)
        duration_client_drift = (completed_record.timestamp_client_started - completed_record.timestamp_sleep_sim_start).in_ticks()
        duration_client_drift /= TICKS_PER_REAL_WORLD_SECOND
        completed_record.additional_actor_debt = max(0, duration_client_drift - arb_accumulator_service.MAXIMUM_TIME_DEBT)
        for actor in completed_record.get_relevant_objects():
            arb_accumulator_service.set_time_debt((actor,), completed_record.additional_actor_debt)

def _animation_drift_monitor_start_sleep_element(animation_sleep_element):
    record = _AnimationDriftMonitorRecord(animation_sleep_element)
    record.timestamp_sleep_start = _get_now_time()
    record.timestamp_sleep_sim_start = _get_simulation_now_time()
    _animation_drift_monitor_records.append(record)

def _animation_drift_monitor_end_sleep_element(animation_sleep_element):
    for record in _animation_drift_monitor_records:
        if record.record_id == id(animation_sleep_element):
            record.timestamp_sleep_end = _get_now_time()
            break
    _remove_completed_records()

def build_animation_drift_monitor_sequence(animation_sleep_element, sleep_element):
    sequence = build_element((lambda _: _animation_drift_monitor_start_sleep_element(animation_sleep_element), sleep_element))
    return sequence

def animation_drift_monitor_on_arb_client_completed(arb_network_id, arb_client_duration, arb_client_playback_delay, timeline_contents):
    for record in _animation_drift_monitor_records:
        record.on_arb_complete(arb_network_id, arb_client_duration, arb_client_playback_delay, timeline_contents)
    _remove_completed_records()

def animation_drift_monitor_on_arb_client_started(arb_network_id):
    for record in _animation_drift_monitor_records:
        record.on_arb_client_started(arb_network_id)
    _remove_completed_records()

def animation_drift_monitor_on_zone_shutdown():
    _animation_drift_monitor_records.clear()
