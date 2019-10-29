import timefrom clock import ClockSpeedModefrom date_and_time import MILLISECONDS_PER_SECONDfrom simulate_to_time import SimulateToTimefrom zone import set_debug_lagimport areaopsimport elementsimport servicesimport sims4.commandsimport sims4.sim_irq_serviceEVAL_LOCALS = {}
@sims4.commands.Command('debug.attach')
def attach(host='localhost', port:int=5678, suspend:bool=False):
    import debugger
    debugger.attach(host, port=port, suspend=suspend)

@sims4.commands.Command('debug.show_path')
def show_path(_connection=None):
    output = sims4.commands.Output(_connection)
    import sys
    for path in sys.path:
        output(path)

@sims4.commands.Command('debug.set_recursion_limit')
def set_recursion_limit(limit:int=200, _connection=None):
    import sys
    output = sims4.commands.Output(_connection)
    output('Previous limit: {}\nCurrent limit: {}'.format(sys.getrecursionlimit(), limit))
    sys.setrecursionlimit(limit)
    return True

@sims4.commands.Command('debug.force_exception')
def force_exception(_connection=None):
    try:
        raise ValueError("FORCED EXCEPTION: This ValueError exception was forced via the debug cheat 'debug.force_exception'.")
    except:
        sims4.log.Logger('FORCED_EXCEPTION').exception('Forced Exception')

@sims4.commands.Command('debug.force_error')
def force_error(_connection=None):
    sims4.log.Logger('FORCED_ERROR').error("This logger error was forced via the debug cheat 'debug.force_error'.")

@sims4.commands.Command('debug.force_assert')
def force_assert(_connection=None):
    areaops.trigger_native_assert()
    return True

@sims4.commands.Command('debug.eval')
def eval_command(cmd:str, _connection=None):
    output = sims4.commands.Output(_connection)
    EVAL_LOCALS['output'] = output
    result = eval(cmd, globals(), EVAL_LOCALS)
    try:
        output(repr(result))
    finally:
        del EVAL_LOCALS['output']

@sims4.commands.Command('debug.exec')
def exec_command(cmd:str, _connection=None):
    output = sims4.commands.Output(_connection)
    EVAL_LOCALS['output'] = output
    cmd = cmd.replace('|', '\n')
    try:
        exec(cmd, globals(), EVAL_LOCALS)
    finally:
        del EVAL_LOCALS['output']

@sims4.commands.Command('debug.clear_eval_locals')
def clear_eval_locals_command(_connection=None):
    EVAL_LOCALS.clear()

@sims4.commands.Command('debug.hang')
def force_hang(duration:int=10000, _connection=None):
    duration /= MILLISECONDS_PER_SECOND
    output = sims4.commands.Output(_connection)
    output('Simulation hanging for {0:.2f} seconds...'.format(duration))
    time.sleep(duration)
    output('Simulation resuming.'.format(duration))
    return True

@sims4.commands.Command('debug.hang_with_irq')
def force_hang_with_irq(duration:int=10000, irq_interval=100, _connection=None):
    duration /= MILLISECONDS_PER_SECOND
    interval = irq_interval/MILLISECONDS_PER_SECOND
    yield_to_irq = sims4.sim_irq_service.yield_to_irq

    def do_hang_fn(_):
        nonlocal duration
        output = sims4.commands.Output(_connection)
        output('Simulation hanging for {0:.2f} seconds with irq interval of {1:.2f}'.format(duration, interval))
        while duration > 0:
            sleep_time = max(0.001, min(duration, interval))
            time.sleep(sleep_time)
            duration -= sleep_time
            yield_to_irq()
        output('Simulation resuming.'.format(duration))

    services.time_service().wall_clock_timeline.schedule(elements.FunctionElement(do_hang_fn))
    return True

@sims4.commands.Command('debug.lag')
def force_lag(duration:int=500, _connection=None):
    output = sims4.commands.Output(_connection)
    if duration:
        output('Simulation lagging for {} milliseconds every tick.'.format(duration))
    else:
        output('Simulation no longer artificially lagging.')
    set_debug_lag(duration)
    return True

@sims4.commands.Command('debug.simulate_to_time', command_type=sims4.commands.CommandType.Automation)
def simulate_to_time(target_hours:int=None, target_minutes:int=None, days_ahead:int=None, target_speed:ClockSpeedMode=None, _connection=None):
    SimulateToTime().start(target_hours, target_minutes, days_ahead, target_speed, output_fn=lambda s: sims4.commands.output(s, _connection))
