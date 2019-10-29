import collectionsimport gcimport osimport sysimport timefrom sims4.commands import CommandTypefrom sims4.utils import create_csvimport alarmsimport clockimport game_servicesimport servicesimport sims4.commandsimport sims4.core_servicesimport sims4.gsi.archiveimport sims4.reloadimport sizeofwith sims4.reload.protected(globals()):
    g_log_python_memory_alarm = None
def _get_objects():
    gc.collect()
    if hasattr(sys, 'getobjects'):
        return sys.getobjects(sys.maxsize)
    return gc.get_objects()

def _find_object(obj_id):
    for obj in _get_objects():
        if obj_id == id(obj):
            return obj

def _truncate(s, max_len, cont='...'):
    if len(s) < max_len:
        return s
    return s[:max_len - len(cont)] + cont

def _print_object_info(obj, output, max_len=100, predicate=None):
    if predicate is not None and not predicate(obj):
        return False
    info_str = '{0:#010x}:\t{1}\t{2}\t{3}'.format(id(obj), obj.__class__.__name__, _truncate(repr(obj), max_len), type(obj))
    if hasattr(obj, 'zone_id'):
        zone_id = getattr(obj, 'zone_id')
        info_str += '\t{:#018x}'.format(zone_id)
    output(info_str)
    return True

@sims4.commands.Command('mem.get_objects')
def get_objects(type_name=None, exact:bool=False, limit:int=1000, _connection=None):
    predicate = None
    if type_name == '*':
        type_name = None
    if type_name is not None:
        if exact:

            def predicate(obj):
                return obj.__class__.__name__ == type_name

        else:

            def predicate(obj):
                return type_name in obj.__class__.__name__

    output = sims4.commands.Output(_connection)
    count = 0
    for obj in _get_objects():
        if _print_object_info(obj, output, predicate=predicate):
            count += 1
        if limit >= 0 and count >= limit:
            output("Terminating search after {} results (increase 'limit' to see more)".format(limit))
            break
    output('Found {} results'.format(count))
    return True

@sims4.commands.Command('mem.get_object_categories')
def get_object_categories(_connection=None):
    output = sims4.commands.Output(_connection)
    output('get_object_catagories is not supported in optimized python builds.')

    @sims4.commands.Command('mem.set_object_categories_checkpoint')
    def set_object_categories_checkpoints(_connection=None):
        global _previous_categories
        categories = collections.Counter(obj.__class__ for obj in gc.get_objects())
        _previous_categories = dict(categories)
        return True

@sims4.commands.Command('mem.get_game_object')
def get_game_object(obj_id:int, _connection=None):
    output = sims4.commands.Output(_connection)
    manager = services.object_manager()
    if obj_id in manager:
        obj = manager.get(obj_id)
    else:
        output('Object with id {} cannot be found.'.format(obj_id))
    _print_object_info(obj, output)
    return True

@sims4.commands.Command('mem.get_referents')
def get_referents(python_id:int, _connection=None):
    output = sims4.commands.Output(_connection)
    obj = _find_object(python_id)
    if obj is None:
        output('Object with id {0:#08x} cannot be found'.format(python_id))
        return False
    _print_object_info(obj, output)
    obj_list = gc.get_referents(obj)
    for ref_obj in obj_list:
        _print_object_info(ref_obj, output)
    output('Found {} results'.format(len(obj_list)))
    return True

@sims4.commands.Command('mem.get_referrers')
def get_referrers(python_id:int, _connection=None):
    output = sims4.commands.Output(_connection)
    obj = _find_object(python_id)
    if obj is None:
        output('Object with id {0:#08x} cannot be found'.format(python_id))
        return False
    _print_object_info(obj, output)
    obj_list = gc.get_referrers(obj)
    for ref_obj in obj_list:
        _print_object_info(ref_obj, output)
    output('Found {} results'.format(len(obj_list)))
    return True

def populate_all_referants(cur_obj, referer_dict):
    referrants = gc.get_referents(cur_obj)
    for referrant in referrants:
        if id(referrant) not in referer_dict:
            referer_dict[id(referrant)] = referrant
            populate_all_referants(referrant, referer_dict)

@sims4.commands.Command('mem.gc_dump')
def garbage_collector_dump(_connection):
    gc.collect()
    all_gc_objects = gc.get_objects()
    all_objects = {}
    for obj in all_gc_objects:
        all_objects[id(obj)] = obj
        populate_all_referants(obj, all_objects)
    index = 0
    file_name = 'python_mem_dump.txt'
    while os.path.exists(file_name):
        index += 1
        file_name = 'python_mem_dump{}.txt'.format(index)
    with open(file_name, 'w') as output_file:
        output_file.write('Index,Address,Size,Name,Repr\n')
        cur_index = 0
        for key in sorted(all_objects.keys()):
            cur_index += 1
            try:
                key_str = str(key)
            except:
                key_str = 'FAILED'
            try:
                if hasattr(all_objects[key], '__name__'):
                    name_str = '{}::{}'.format(type(all_objects[key]), all_objects[key].__name__)
                else:
                    name_str = '{}'.format(type(all_objects[key]))
            except:
                name_str = 'FAILED'
            try:
                obj_size = str(sys.getsizeof(all_objects[key]))
            except:
                obj_size = 'FAILED'
            try:
                repr_str = str(all_objects[key])
                repr_str = ''.join(repr_str.split())
                repr_str = ''.join(repr_str.split(','))
            except:
                obj_size = 'FAILED'
            try:
                output_file.write('{},{},{},{},{}\n'.format(cur_index, key_str, obj_size, name_str, repr_str))
            except Exception as e:
                while e is EnvironmentError:
                    break
    sims4.commands.output('Memory Output Complete', _connection)

@sims4.commands.Command('mem.py_tree_dump', command_type=sims4.commands.CommandType.Automation)
def py_tree_dump(file_name=None, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    labeled_roots = get_labeled_roots()
    labeled_roots.insert(0, ('Integers', list(range(-5, 257))))
    labeled_roots.insert(0, ('Floats', float.get_interned()))
    file_name = write_out_py_tree_dump(labeled_roots, file_name, 'python_tree_dump', None, bfs=True, include_cycles=False)
    output_str = "Wrote Python heap tree: '{}'".format(file_name)
    output(output_str)

@sims4.commands.Command('mem.py_garbage_dump', command_type=sims4.commands.CommandType.Automation)
def py_gc_collect_dump(file_name=None, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    old_flags = gc.get_debug()
    try:
        gc.set_debug(gc.DEBUG_SAVEALL)
        gc.collect()
    finally:
        gc.set_debug(old_flags)
    labeled_roots = [('garbage', gc.garbage)]
    allowed_ids = set(id(obj) for obj in gc.garbage)
    allowed_ids.add(id(gc.garbage))
    for obj in gc.garbage:
        allowed_ids.add(id(type(obj)))
    file_name = write_out_py_tree_dump(labeled_roots, file_name, 'python_garbage_dump', allowed_ids, bfs=False, include_cycles=True)
    output_str = "Wrote Python gc dump: '{}'".format(file_name)
    output(output_str)
    gc.garbage.clear()

def write_out_py_tree_dump(labeled_roots, file_name, default_name_base, allowed_ids, bfs=True, include_cycles=False):
    if file_name is None:
        current_time = time.strftime('%Y-%m-%d-%H-%M-%S', time.gmtime())
        file_name = '{}-{}.mem'.format(default_name_base, current_time)
    try:
        sims4.log.Logger.suppress = True
        root = sizeof.get_object_tree(labeled_roots, allowed_ids=allowed_ids, bfs=bfs, include_cycles=include_cycles)
    finally:
        sims4.log.Logger.suppress = False
    with open(file_name, 'wb') as fd:
        sizeof.write_object_tree(root, fd)
    del root
    gc.collect()
    return file_name

def get_labeled_roots(reverse_entries=False):
    labeled_roots = []
    from objects.definition_manager import DefinitionManager
    from sims4.tuning.instance_manager import InstanceManager
    from indexed_manager import IndexedManager
    from postures.posture_graph import PostureGraphService
    SERVICE_GROUPS = [(DefinitionManager, 'DefinitionManager'), (InstanceManager, 'TuningManager'), (IndexedManager, 'IndexedManager'), (PostureGraphService, 'PostureGraph'), (object, 'Other')]
    direction_iter = reversed if reverse_entries else iter
    zone = services.current_zone()
    service_sources = []
    zone_services = [source for service in zone.service_manager.services for source in service.get_buckets_for_memory_tracking()]
    service_sources.append((zone_services, 'ZoneService/'))
    game_service_list = [source for service in game_services.service_manager.services for source in service.get_buckets_for_memory_tracking()]
    service_sources.append((game_service_list, 'GameService/'))
    core_services = [source for service in sims4.core_services.service_manager.services for source in service.get_buckets_for_memory_tracking()]
    service_sources.append((core_services, 'CoreService/'))
    for (source, source_name) in service_sources:
        for service in direction_iter(source):
            group = source_name + _first_applicable_match(service, SERVICE_GROUPS)
            labeled_roots.append(('{1}/{0}'.format(service, group), service))
    for (name, module) in direction_iter(sorted(sys.modules.items())):
        path_root = 'Other'
        if hasattr(module, '__file__'):
            matching_paths = [path for path in sys.path if module.__file__.startswith(path)]
            if matching_paths:
                path_root = os.path.split(next(iter(matching_paths)))[-1]
                path_root = path_root.capitalize()
        group = 'Module/{}'.format(path_root)
        labeled_roots.append(('{1}/{0}'.format(name, group), module))
    labeled_roots.append(('GSI/Archivers/', sims4.gsi.archive.archive_data))
    return labeled_roots

def generate_summary_report(skip_atomic, reverse_entries):
    labeled_roots = get_labeled_roots(reverse_entries=reverse_entries)
    report = sizeof.report(labeled_roots, skip_atomic=skip_atomic)
    return report

def _first_applicable_match(obj, groups):
    for (t, group) in groups:
        if isinstance(obj, t):
            return group
    raise TypeError('No group for obj {}'.format(obj))

@sims4.commands.Command('mem.py_summary', command_type=sims4.commands.CommandType.Automation)
def print_summary(skip_atomic:bool=False, reverse_entries:bool=False, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    report = generate_summary_report(skip_atomic, reverse_entries)
    for (name, size) in sorted(report.items()):
        output('{},{}'.format(name, size))

@sims4.commands.Command('mem.py_summary_file', command_type=sims4.commands.CommandType.Automation)
def log_summary(skip_atomic:bool=False, reverse_entries:bool=False, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    automation_output = sims4.commands.AutomationOutput(_connection)
    current_time = time.strftime('%Y-%m-%d-%H-%M-%S', time.gmtime())
    file_name = 'python_mem_summary-{}.csv'.format(current_time)
    with open(file_name, 'w') as fd:
        fd.write('Category,Group,System,Size\n')
        report = generate_summary_report(skip_atomic, reverse_entries)
        for (name, size) in sorted(report.items()):
            (category, group, system) = name.split('/')
            fd.write('{},{},{},{}\n'.format(category, group, system, size))
    output_str = "Wrote Python memory summary to: '{}'".format(file_name)
    output(output_str)
    automation_output('MemPySummaryFile; FileName:%s' % file_name)

@sims4.commands.Command('mem.clear_merged_tuning_manager')
def clear_merged_tuning_manager(_connection=None):
    output = sims4.commands.Output(_connection)
    from sims4.tuning.merged_tuning_manager import get_manager
    get_manager().clear()
    output('Merged tuning manager cleared.  WARNING: Tuning reload may break.')

@sims4.commands.Command('mem.print_leak_chain')
def print_leak_chain(obj_address:int, recursion_depth:int=10, _connection=None):
    obj = _find_object(obj_address)
    if obj is None:
        obj = services.object_manager().get(obj_address)
    if obj is not None:
        from sims4.leak_detector import find_object_refs
        termination_points = set(services._zone_manager)
        termination_points.update(services.client_object_managers())
        find_object_refs(obj, termination_points=termination_points, recursion_depth=recursion_depth)

def _size_of_slots(n):
    if n == 0:
        return 8
    return 24 + 4*n

def _size_of_tuple(n):
    return 28 + 4*n

@sims4.commands.Command('mem.analyze_slots', command_type=sims4.commands.CommandType.Automation)
def analyze_slots(verbose:bool=False, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    if verbose:
        output('Collecting GC')
    gc.collect()
    if verbose:
        output('Gathering objects')
    pending = collections.deque(gc.get_objects())
    all_objects = {id(obj): obj for obj in pending}
    while pending:
        obj = pending.pop()
        referents = gc.get_referents(obj)
        for child in referents:
            if id(child) not in all_objects:
                all_objects[id(child)] = child
                pending.append(child)
                if verbose and not len(all_objects) % 1000000:
                    output('...{} pending: {}'.format(len(all_objects), len(pending)))
    if verbose:
        output('Collating types')
    type_map = collections.defaultdict(list)
    for obj in all_objects.values():
        tp = type(obj)
        type_map[tp.__module__ + '.' + tp.__qualname__].append(obj)
    del all_objects

    def write_to_file(file):
        file.write('Type,Count,Size,Each,SlotSize,SlotEach,Attribs,SlotSavings,SlotSavings(MB),__slots__\n')
        for type_name in sorted(type_map.keys()):
            objects = type_map[type_name]
            if not hasattr(objects[0], '__dict__'):
                pass
            else:
                size = 0
                attribs = set()
                if isinstance(objects[0], tuple):
                    for obj in objects:
                        attribs |= set(str(name) for name in vars(obj))
                        size += sys.getsizeof(obj)
                else:
                    for obj in objects:
                        attribs |= set(str(name) for name in vars(obj))
                        size += sys.getsizeof(obj) + sys.getsizeof(obj.__dict__)
                inst_size = size/len(objects)
                slot_inst_size = _size_of_slots(len(attribs))
                slot_size = slot_inst_size*len(objects)
                slot_savings = size - slot_size
                slots_string = str(tuple(attribs)).replace(',', '') if len(attribs) < 50 else '(...)'
                file.write('{},{},{},{:0.2f},{},{},{},{},{:0.2f},{}\n'.format(type_name, len(objects), size, inst_size, slot_size, slot_inst_size, len(attribs), slot_savings, slot_savings/1048576, slots_string))

    filename = 'PyOpt_AnalyzeSlots'
    create_csv(filename, callback=write_to_file, connection=_connection)

@sims4.commands.Command('mem.record_python_memory.start', command_type=CommandType.Automation)
def record_python_memory_start(start_time:int=150, frequency:int=120, _connection=None):
    global g_log_python_memory_alarm
    record_python_memory_stop(_connection=_connection)
    output = sims4.commands.CheatOutput(_connection)
    repeating_time_span = clock.interval_in_sim_minutes(frequency)

    def record_callback(_):
        sims4.commands.client_cheat('|memory_dump', _connection)
        sims4.commands.client_cheat('|py.heapcheckpoint', _connection)
        output('Recording python memory. Next attempt in {}.'.format(repeating_time_span))

    time_span = clock.interval_in_sim_minutes(start_time)
    g_log_python_memory_alarm = alarms.add_alarm(record_python_memory_start, time_span, record_callback, repeating=True, repeating_time_span=repeating_time_span)
    output('Recording python memory. First record will occur in {}.'.format(time_span))

@sims4.commands.Command('mem.record_python_memory.stop', command_type=CommandType.Automation)
def record_python_memory_stop(_connection=None):
    global g_log_python_memory_alarm
    if g_log_python_memory_alarm is not None:
        alarms.cancel_alarm(g_log_python_memory_alarm)
        g_log_python_memory_alarm = None
