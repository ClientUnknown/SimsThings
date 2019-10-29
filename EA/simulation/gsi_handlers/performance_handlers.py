from collections import Counterimport timefrom gsi_handlers.gameplay_archiver import GameplayArchiverfrom objects import ALL_HIDDEN_REASONSfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersfrom sims4.tuning.tunable import TunableSet, TunableEnumEntryfrom tag import Tagimport alarmsimport clockimport performance.performance_constants as constsimport servicesimport sims4performance_archive_schema = GsiGridSchema(label='Performance Metrics Log')performance_archive_schema.add_field('autonomy_queue_time', label='Autonomy Q Time', type=GsiFieldVisualizers.INT, width=2)performance_archive_schema.add_field('autonomy_queue_length', label='Autonomy Q Len', type=GsiFieldVisualizers.INT, width=2)performance_archive_schema.add_field('ticks_per_sec', label='Ticks Per Sec', type=GsiFieldVisualizers.FLOAT, width=2)performance_archive_schema.add_field('num_sims', label='#Sims', type=GsiFieldVisualizers.INT)performance_archive_schema.add_field('num_sim_infos', label='#SimInfos', type=GsiFieldVisualizers.INT)performance_archive_schema.add_field('num_objects_active_lot', label='#Obj(ActiveLot)', type=GsiFieldVisualizers.INT, width=3)performance_archive_schema.add_field('num_objects_open_street', label='#Objects(OpenStreet)', type=GsiFieldVisualizers.INT, width=3)performance_archive_schema.add_field('num_props', label='#Props', type=GsiFieldVisualizers.INT)performance_archive_schema.add_field('total_objects_props', label='Total Objs&Props', type=GsiFieldVisualizers.INT, width=2)with performance_archive_schema.add_has_many('AdditionalMetrics', GsiGridSchema) as sub_schema:
    sub_schema.add_field('metric', label='Metric')
    sub_schema.add_field('count', label='Count', type=GsiFieldVisualizers.INT)for name in consts.OBJECT_CLASSIFICATIONS:
    with performance_archive_schema.add_has_many(name, GsiGridSchema) as sub_schema:
        sub_schema.add_field('name', label='Name')
        sub_schema.add_field('location', label='Location')
        sub_schema.add_field('frequency', label='Frequency', type=GsiFieldVisualizers.INT)with sims4.reload.protected(globals()):
    performance_log_alarm = None
    previous_log_time_stamp = 0
    previous_log_time_ticks = 0SECONDS_BETWEEN_LOGGING = 60performance_metrics = []archive_data = {'autonomy_queue_time': 0, 'autonomy_queue_length': 0, 'ticks_per_sec': 0, 'num_sims': 0, 'num_sim_infos': 0, 'num_objects_active_lot': 0, 'num_objects_open_street': 0, 'num_props': 0, 'total_objects_props': 0}
def enable_performance_logging(*args, enableLog=False, **kwargs):
    global previous_log_time_stamp, previous_log_time_ticks, performance_log_alarm
    if enableLog:

        def alarm_callback(_):
            global previous_log_time_stamp, previous_log_time_ticks
            generate_statistics()
            _log_performance_metrics()
            previous_log_time_stamp = time.time()
            previous_log_time_ticks = services.server_clock_service().now().absolute_ticks()

        previous_log_time_stamp = time.time()
        previous_log_time_ticks = services.server_clock_service().now().absolute_ticks()
        set_gsi_performance_metric('ticks_per_sec', 'N/A')
        _log_performance_metrics()
        current_zone = services.current_zone()
        if performance_log_alarm is not None:
            alarms.cancel_alarm(performance_log_alarm)
        performance_log_alarm = alarms.add_alarm_real_time(current_zone, clock.interval_in_real_seconds(SECONDS_BETWEEN_LOGGING), alarm_callback, repeating=True, use_sleep_time=False)
    elif performance_log_alarm is not None:
        alarms.cancel_alarm(performance_log_alarm)
        performance_log_alarm = None
        previous_log_time_stamp = 0
        set_gsi_performance_metric('ticks_per_sec', 'N/A')

def generate_statistics():
    now_ticks = services.server_clock_service().now().absolute_ticks()
    ticks_elapsed = now_ticks - previous_log_time_ticks
    now_time = time.time()
    time_elapsed = now_time - previous_log_time_stamp
    ticks_per_sec = 0
    if time_elapsed != 0:
        ticks_per_sec = ticks_elapsed/time_elapsed
    else:
        ticks_per_sec = 'Zero time elapsed. ticks elapsed = {}'.format(ticks_elapsed)
    num_sim_infos = 0
    num_sims = 0
    for sim_info in services.sim_info_manager().objects:
        num_sim_infos += 1
        if sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
            num_sims += 1
    all_props = []
    if services.prop_manager():
        all_props = list(services.prop_manager().objects)
    all_objects = list(services.object_manager().objects)
    all_inventory_objects = list(services.current_zone().inventory_manager.objects)
    objects_active_lot_interactive = []
    objects_active_lot_decorative = []
    objects_open_street_interactive = []
    objects_open_street_decorative = []
    for obj in all_objects:
        if obj.is_on_active_lot():
            if obj.definition.has_build_buy_tag(*PerformanceHandlerTuning.DECORATIVE_OBJECT_TAGS_ACTIVE_LOT):
                objects_active_lot_decorative.append(obj)
            else:
                objects_active_lot_interactive.append(obj)
        elif obj.definition.has_build_buy_tag(*PerformanceHandlerTuning.DECORATIVE_OBJECT_TAGS_OPEN_STREET):
            objects_open_street_decorative.append(obj)
        else:
            objects_open_street_interactive.append(obj)
    objects_active_lot_autonomous = []
    objects_open_street_autonomous = []
    objects_active_lot_user_directed = []
    objects_open_street_user_directed = []
    autonomous_counter = Counter()
    user_directed_counter = Counter()

    def process_interactive_objects(objects, autonomous_list, user_directed_list, autonomous_counter, user_directed_counter, location='undefined'):
        for obj in objects:
            in_autonomous_list = False
            in_user_directed_list = False
            in_user_directed_counter = (obj.definition.name, location) in user_directed_counter
            for sa in obj.super_affordances():
                if sa.allow_autonomous:
                    autonomous_counter.update({(sa, location): 1})
                    if not in_autonomous_list:
                        in_autonomous_list = True
                        autonomous_list.append(obj)
                if not in_user_directed_counter:
                    user_directed_counter.update({(obj.definition.name, location): 1})
                if not (sa.allow_user_directed and in_user_directed_list):
                    in_user_directed_list = True
                    user_directed_list.append(obj)

    process_interactive_objects(objects_active_lot_interactive, objects_active_lot_autonomous, objects_active_lot_user_directed, autonomous_counter, user_directed_counter, location='active_lot')
    process_interactive_objects(objects_open_street_interactive, objects_open_street_autonomous, objects_open_street_user_directed, autonomous_counter, user_directed_counter, location='open_street')
    performance_metrics.clear()
    set_gsi_performance_metric('num_sims', num_sims)
    set_gsi_performance_metric('num_sim_infos', num_sim_infos)
    set_gsi_performance_metric('num_objects_active_lot', len(objects_active_lot_interactive) + len(objects_active_lot_decorative))
    set_gsi_performance_metric('num_objects_open_street', len(objects_open_street_interactive) + len(objects_open_street_decorative))
    set_gsi_performance_metric('num_props', len(all_props))
    set_gsi_performance_metric('total_objects_props', len(all_props) + len(all_objects))
    set_gsi_performance_metric(consts.TICKS_PER_SECOND, ticks_per_sec)
    metrics = [(consts.OBJS_ACTIVE_LOT_INTERACTIVE, lambda : len(objects_active_lot_interactive)), (consts.OBJS_ACTIVE_LOT_DECORATIVE, lambda : len(objects_active_lot_decorative)), (consts.OBJS_OPEN_STREET_INTERACTIVE, lambda : len(objects_open_street_interactive)), (consts.OBJS_OPEN_STREET_DECORATIVE, lambda : len(objects_open_street_decorative)), (consts.OBJS_TOTAL, lambda : len(all_objects)), (consts.PROPS_TOTAL, lambda : len(all_props)), (consts.OBJS_INVENTORY_TOTAL, lambda : len(all_inventory_objects)), (consts.OBJS_GRAND_TOTAL, lambda : len(all_props) + len(all_objects) + len(all_inventory_objects)), (consts.OBJS_ACTIVE_LOT_AUTONOMOUS_AFFORDANCE, lambda : len(objects_active_lot_autonomous)), (consts.OBJS_OPEN_STREET_AUTONOMOUS_AFFORDANCE, lambda : len(objects_open_street_autonomous)), (consts.OBJS_AUTONOMOUS_AFFORDANCE, lambda : sum(autonomous_counter.values()))]
    details = list()
    for (name, func) in metrics:
        entry = {'metric': name, 'count': func()}
        details.append(entry)
    set_gsi_performance_metric('AdditionalMetrics', details)

    def generate_histogram(name, objects, fill_gsi_func, histogram_counter=None, object_name_func=None):
        if histogram_counter is None:
            histogram_counter = Counter(objects)
        histogram = list()
        for (obj, freq) in histogram_counter.most_common():
            entry = fill_gsi_func(obj, freq, object_name_func=object_name_func)
            histogram.append(entry)
        set_gsi_performance_metric(name, histogram)

    def fill_gsi_object_location_histogram_entry(object_location_pair, frequency, object_name_func=None):
        obj_name = object_name_func(object_location_pair[0]) if object_name_func is not None else object_location_pair[0]
        return {'name': obj_name, 'location': object_location_pair[1], 'frequency': frequency}

    def combine_object_location_lists(active_lot_list, open_street_list):
        all_objects = [(active_lot_obj.definition.name, 'active_lot') for active_lot_obj in active_lot_list]
        all_objects.extend([(open_street_obj.definition.name, 'open_street') for open_street_obj in open_street_list])
        return all_objects

    all_objects_locations_interactive = combine_object_location_lists(objects_active_lot_interactive, objects_open_street_interactive)
    all_objects_locations_decorative = combine_object_location_lists(objects_active_lot_decorative, objects_open_street_decorative)
    all_objects_locations_autonomous = combine_object_location_lists(objects_active_lot_autonomous, objects_open_street_autonomous)
    sa_name_func = lambda x: x.__name__
    generate_histogram(consts.OBJECT_CLASSIFICATIONS[0], all_objects_locations_interactive, fill_gsi_object_location_histogram_entry)
    generate_histogram(consts.OBJECT_CLASSIFICATIONS[1], all_objects_locations_decorative, fill_gsi_object_location_histogram_entry)
    generate_histogram(consts.OBJECT_CLASSIFICATIONS[2], all_objects_locations_autonomous, fill_gsi_object_location_histogram_entry)
    generate_histogram(consts.OBJECT_CLASSIFICATIONS[3], [], fill_gsi_object_location_histogram_entry, autonomous_counter, sa_name_func)
    generate_histogram(consts.OBJECT_CLASSIFICATIONS[4], [], fill_gsi_object_location_histogram_entry, user_directed_counter)
    return performance_metrics
archiver = GameplayArchiver('performance_metrics', performance_archive_schema, custom_enable_fn=enable_performance_logging)
def set_gsi_performance_metric(performance_metric_id:str, value):
    if performance_metric_id == 'AdditionalMetrics':
        for v in value:
            performance_metrics.append((str(v['metric']), str(v['count'])))
    else:
        performance_metrics.append((performance_metric_id, str(value)))
    archive_data[performance_metric_id] = value

def _log_performance_metrics():
    archiver.archive(data=archive_data)

class PerformanceHandlerTuning:
    DECORATIVE_OBJECT_TAGS_ACTIVE_LOT = TunableSet(description="\n            Tags that will be used by GSI's performance metric view \n            to classify active lot objects as decorative.\n            ", tunable=TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID))
    DECORATIVE_OBJECT_TAGS_OPEN_STREET = TunableSet(description="\n            Tags that will be used by GSI's performance metric view \n            to classify open street objects as decorative.\n            ", tunable=TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID))
