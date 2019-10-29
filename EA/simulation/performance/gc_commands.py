import gcimport mathfrom date_and_time import TimeSpan, TICKS_PER_REAL_WORLD_SECOND, create_time_spanfrom sims4.commands import CommandTypefrom sims4.utils import create_csvimport alarmsimport servicesimport sims4.commandsimport zonewith sims4.reload.protected(globals()):
    gc_alarm_handle = None
    gc_object_counts = None
    gc_inc_window_size = 0
    gc_inc_window_collected = 0
    gc_inc_window_current = 0
@sims4.commands.Command('mem.gc.collect', command_type=sims4.commands.CommandType.Automation)
def gc_collect(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    n = gc.collect()
    output('Collected {} objects.'.format(n))
    return True

@sims4.commands.Command('mem.gc.enable', command_type=sims4.commands.CommandType.Automation)
def gc_enable(_connection=None):
    output = sims4.commands.Output(_connection)
    gc.enable()
    output('GC enabled!')
    return True

@sims4.commands.Command('mem.gc.disable', command_type=sims4.commands.CommandType.Automation)
def gc_disable(_connection=None):
    output = sims4.commands.Output(_connection)
    gc.disable()
    output('GC disabled!')
    return True

@sims4.commands.Command('mem.gc.inc_debug', command_type=CommandType.Automation)
def mem_gc_inc_debug_stats(_connection=None):
    old_flags = gc.get_debug()
    if old_flags & gc.DEBUG_STATSINC:
        gc.set_debug(old_flags & ~gc.DEBUG_STATSINC)
    else:
        gc.set_debug(old_flags | gc.DEBUG_STATSINC)

@sims4.commands.Command('mem.gc.set_max_roots_per_pass', command_type=CommandType.Automation)
def mem_gc_set_max_roots_per_pass(n:int, _connection=None):
    gc.set_max_roots_per_pass(n)

@sims4.commands.Command('mem.gc.set_max_nodes_per_root', command_type=CommandType.Automation)
def mem_gc_set_max_nodes_per_root(n:int, _connection=None):
    gc.set_max_nodes_per_root(n)

@sims4.commands.Command('mem.gc.set_max_traversal', command_type=CommandType.Automation)
def mem_gc_set_max_traversal(n:int, _connection=None):
    gc.set_max_traversal(n)

@sims4.commands.Command('mem.gc.inc_collect', command_type=CommandType.Automation)
def mem_gc_inc_collect(count:int=1, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    total_collected = 0
    for i in range(count):
        collected = gc.collect_incremental()
        if collected > 0:
            output('{}: {}'.format(i, collected))
            total_collected += collected
    output('Total Collected: {}'.format(total_collected))

@sims4.commands.Command('mem.gc.garbage_dump', command_type=CommandType.Automation)
def mem_garbage_dump(_connection=None):
    old_flags = gc.get_debug()
    gc.set_debug(gc.DEBUG_SAVEALL)
    gc.collect()

    def write_to_file(file):
        garbage_ids = set(id(i) for i in gc.garbage)
        for o in gc.garbage:
            referents = tuple(r for r in gc.get_referents(o) if id(r) in garbage_ids)
            try:
                orepr = repr(o)
            except:
                orepr = '<exc>'
            file.write('{};{};{}{};{}\n'.format(len(referents), id(o), ''.join('{};'.format(id(r)) for r in referents), type(o).__name__, orepr))

    output = sims4.commands.CheatOutput(_connection)
    output('Garbage count: {}'.format(len(gc.garbage)))
    filename = 'garbage_graph'
    create_csv(filename, callback=write_to_file, connection=_connection)
    gc.garbage.clear()
    gc.set_debug(old_flags)

def gc_output(format_str, *format_args):
    client_id = services.client_manager().get_first_client_id()
    output = sims4.commands.CheatOutput(client_id)
    output(format_str.format(*format_args))

def gc_collect_log_callback(phase, info):
    if phase != 'stop':
        return
    if gc.get_debug() & gc.DEBUG_SAVEALL == gc.DEBUG_SAVEALL:
        return
    generation = info['generation']
    if generation == 2 or generation == 4:
        now = services.time_service().sim_now
        gc_output('***** GC-{} [{}]: collected {}. Alive: {} *****', generation, now, info['collected'], gc.get_num_objects())

def get_garbage_count():
    old_flags = gc.get_debug()
    gc.set_debug(gc.DEBUG_SAVEALL)
    gc.collect()
    garbage_count = len(gc.garbage)
    gc.garbage.clear()
    gc.set_debug(old_flags)
    return garbage_count

@sims4.commands.Command('mem.gc.collect_log', command_type=CommandType.Automation)
def gc_collect_log(enable:bool=None, _connection=None):
    if enable is None:
        enable = gc_collect_log_callback not in gc.callbacks
    if enable:
        gc_output('gc callback registered')
        if gc_collect_log_callback not in gc.callbacks:
            gc.callbacks.append(gc_collect_log_callback)
    else:
        if gc_collect_log_callback in gc.callbacks:
            gc.callbacks.remove(gc_collect_log_callback)
        gc_output('gc callback unregistered')

def garbage_sample_handle(_):
    timestamp = services.time_service().sim_now
    total_count = gc.get_num_objects()
    garbage_count = get_garbage_count()
    gc_output('GC-3 [{}]: Garbage {}, Total {}', timestamp, garbage_count, total_count)

@sims4.commands.Command('mem.gc.sample_log', command_type=CommandType.Automation)
def gc_sample_log(rate:int=30, real_time:bool=False, _connection=None):
    global gc_alarm_handle
    if gc_alarm_handle is None:
        gc_output('Enabled sample logging.')
        if real_time:
            ticks = rate*TICKS_PER_REAL_WORLD_SECOND
            gc_alarm_handle = alarms.add_alarm_real_time(services.current_zone(), TimeSpan(ticks), garbage_sample_handle, repeating=True, use_sleep_time=False)
        else:
            gc_alarm_handle = alarms.add_alarm(services.current_zone(), create_time_span(minutes=rate), garbage_sample_handle, repeating=True)
    else:
        gc_output('Disabling sample logging.')
        gc_alarm_handle.cancel()
        gc_alarm_handle = None

@sims4.commands.Command('mem.gc.print_garbage_count', command_type=CommandType.Automation)
def print_garbage_count(_connection=None):
    garbage_count = get_garbage_count()
    total_count = gc.get_num_objects()
    gc_output('Garbage: {}/{}', garbage_count, total_count)

@sims4.commands.Command('mem.gc.print_object_count', command_type=CommandType.Automation)
def print_object_count(_connection=None):
    total_count = gc.get_num_objects()
    freeze_count = gc.get_freeze_count()
    gc_output('Object count: {}, Freeze count: {}', total_count, freeze_count)

@sims4.commands.Command('mem.gc.zone_gc_count_log_start', command_type=sims4.commands.CommandType.Automation)
def zone_gc_count_log_start(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output('Zone gc count logging enabled')
    if zone.gc_count_log is None:
        zone.gc_count_log = []

@sims4.commands.Command('mem.gc.zone_gc_count_log_stop', command_type=sims4.commands.CommandType.Automation)
def zone_gc_count_log_stop(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output('Zone gc count logging disabled')
    zone.gc_count_log = None

@sims4.commands.Command('mem.gc.zone_gc_count_log_dump', command_type=sims4.commands.CommandType.Automation)
def zone_gc_count_log_dump(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    if zone.gc_count_log is None:
        output('Zone gc count logging is disabled. Enable with |mem.gc.zone_gc_count_log_start')
        return

    def callback(file):
        file.write('zone_id, count, time\n')
        for (zone_id, count, time) in zone.gc_count_log:
            file.write('{:016x},{},{}\n'.format(zone_id, count, time))
        current_zone = services.current_zone()
        now = services.time_service().sim_now
        time_in_zone = now - current_zone._time_of_zone_spin_up
        minutes_in_zone = math.floor(time_in_zone.in_minutes())
        file.write('{:016x},{},{}\n'.format(current_zone.id, current_zone._gc_full_count, minutes_in_zone))

    create_csv('zone_gc_counts', callback=callback, connection=_connection)

def object_count_log_callback(phase, info):
    global gc_inc_window_current, gc_inc_window_collected
    if info['generation'] == 3:
        gc_inc_window_current += 1
        gc_inc_window_collected += info['collected']
        if gc_inc_window_current >= gc_inc_window_size:
            time_service = services.time_service()
            timestamp = time_service.sim_now.absolute_hours() if time_service is not None else None
            gc_object_counts.append((gc.get_num_objects(), timestamp, gc_inc_window_collected))
            gc_inc_window_collected = 0
            gc_inc_window_current = 0

@sims4.commands.Command('mem.gc.object_count_log_start', command_type=sims4.commands.CommandType.Automation)
def object_count_log_start(window_size:int=30, _connection=None):
    global gc_object_counts, gc_inc_window_current, gc_inc_window_collected, gc_inc_window_size
    output = sims4.commands.CheatOutput(_connection)
    output('Python object count logging enabled')
    if gc_object_counts is None:
        gc_object_counts = []
        gc_inc_window_current = 0
        gc_inc_window_collected = 0
        gc_inc_window_size = window_size
        gc.callbacks.append(object_count_log_callback)

@sims4.commands.Command('mem.gc.object_count_log_stop', command_type=sims4.commands.CommandType.Automation)
def object_count_log_stop(_connection=None):
    global gc_object_counts
    output = sims4.commands.CheatOutput(_connection)
    output('Python object count logging disabled')
    if gc_object_counts is not None:
        gc.callbacks.remove(object_count_log_callback)
        gc_object_counts = None

@sims4.commands.Command('mem.gc.object_count_log_dump', command_type=sims4.commands.CommandType.Automation)
def object_count_log_dump(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    if gc_object_counts is None:
        output('Object count logging is disabled. Enable with |mem.gc.object_count_log_start')
        return

    def callback(file):
        file.write('minutes,count,collected\n')
        for (count, timestamp, collected) in gc_object_counts:
            file.write('{},{},{}\n'.format(timestamp, count, collected))

    create_csv('gc_object_counts', callback=callback, connection=_connection)
