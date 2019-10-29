from animation.animation_drift_monitor import animation_drift_monitor_on_arb_client_completed, animation_drift_monitor_on_arb_client_startedfrom animation.arb_accumulator import ArbAccumulatorServicefrom date_and_time import TICKS_PER_REAL_WORLD_SECONDfrom sims4.commands import CommandTypeimport animation.animation_constantsimport animation.asmimport servicesimport sims4.commandsimport sims4.loglogger = sims4.log.Logger('Animation', default_owner='rmccord')
@sims4.commands.Command('animation.asm_describe')
def asm_describe(name, _connection=None):
    asm = animation.asm.create_asm(name, None)
    sims4.commands.output('ASM is {0}'.format(str(asm.state_machine_name)), _connection)
    sims4.commands.output('  Public States:', _connection)
    public_states = asm.public_states
    if public_states is not None:
        for s in public_states:
            sims4.commands.output('     {0}'.format(s), _connection)
    else:
        sims4.commands.output('     (no public states)', _connection)
    sims4.commands.output('  Actors:', _connection)
    actors = asm.actors
    if actors is not None:
        for s in actors:
            sims4.commands.output('     {0}'.format(s), _connection)
            sims4.commands.output('       {0}'.format(asm.get_actor_definition(s)), _connection)
    else:
        sims4.commands.output('     (no actors)', _connection)
    sims4.commands.output('  Parameters:', _connection)
    parameters = asm.parameters
    if parameters is not None:
        for s in parameters:
            sims4.commands.output('     {0}'.format(s), _connection)
    else:
        sims4.commands.output('     (no parameters)', _connection)

@sims4.commands.Command('animation.set_parent')
def set_parent(parent_id:int, child_id:int, joint_name=None, use_offset:int=0, _connection=None):
    manager = services.object_manager()
    parent = None
    if parent_id in manager:
        parent = manager.get(parent_id)
    child = None
    if parent_id != 0 and child_id != 0:
        if child_id in manager:
            child = manager.get(child_id)
        else:
            sims4.commands.output('SET_PARENT: Child not in manager.', _connection)
    if child is None:
        sims4.commands.output('SET_PARENT: Invalid child.', _connection)
        return
    if parent is None:
        sims4.commands.output('SET_PARENT: No parent found.', _connection)
        return
    transform = sims4.math.Transform.IDENTITY()
    if use_offset == 1:
        transform = sims4.math.Transform(sims4.math.Vector3(1.0, 2.0, 3.0), sims4.math.Quaternion.IDENTITY())
    sims4.commands.output('SET_PARENT:Adding Parent', _connection)
    child.set_parent(parent, transform, joint_name_or_hash=joint_name)

@sims4.commands.Command('animation.arb_log.enable')
def enable_arb_log(_connection=None):
    animation.animation_constants._log_arb_contents = True

@sims4.commands.Command('animation.arb_log.disable')
def disable_arb_log(_connection=None):
    animation.animation_constants._log_arb_contents = False

@sims4.commands.Command('animation.boundary_condition.add_log')
def add_boundary_condition_log(pattern:str='', _connection=None):
    animation.asm.add_boundary_condition_logging(pattern)
    return True

@sims4.commands.Command('animation.boundary_condition.clear_log')
def clear_boundary_condition_log(_connection=None):
    animation.asm.clear_boundary_condition_logging()
    return True

@sims4.commands.Command('animation.list_parameter_sequences')
def list_asm_parameter_sequences(name, target_state, src_state='entry', _connection=None):
    asm = animation.asm.create_asm(name, None)
    param_sequence_list = asm._get_param_sequences(0, target_state, src_state, None)
    for x in param_sequence_list:
        sims4.commands.output('{0}'.format(x), _connection)

@sims4.commands.Command('animation.list_asm_params')
def list_asm_params(name, _connection=None):
    asm = animation.asm.create_asm(name, None)
    param_sequence_list = asm._get_params()
    for x in param_sequence_list:
        sims4.commands.output('{0}'.format(x), _connection)

@sims4.commands.Command('animation.set_shave_time')
def set_shave_time(shave_time:float, _connection=None):
    ArbAccumulatorService.SHAVE_TIME = shave_time

@sims4.commands.Command('animation.arb_started', command_type=CommandType.Live)
def on_arb_started(arb_network_id:int, _connection=None):
    animation_drift_monitor_on_arb_client_started(arb_network_id)

@sims4.commands.Command('animation.arb_complete')
def on_arb_complete(arb_network_id:int, arb_client_duration:int, arb_client_playback_delay:int, *timeline_contents, _connection=None):
    timeline_contents = ''.join(timeline_contents)
    timeline_contents = timeline_contents.replace('\r', '\n')
    timeline_contents = timeline_contents.replace('"', '')
    arb_client_duration /= TICKS_PER_REAL_WORLD_SECOND
    arb_client_playback_delay /= TICKS_PER_REAL_WORLD_SECOND
    if not timeline_contents:
        timeline_contents = 'Unavailable - Compile using ENABLE_DURATION_TRACKING'
    animation_drift_monitor_on_arb_client_completed(arb_network_id, arb_client_duration, arb_client_playback_delay, timeline_contents)

@sims4.commands.Command('animation.route_complete', command_type=CommandType.Live)
def route_complete(sim_id:int=None, path_id:int=None, _connection=None):
    if sim_id is None or path_id is None:
        return False
    current_zone = services.current_zone()
    sim = current_zone.find_object(sim_id)
    if sim is None:
        return False
    sim.route_finished(path_id)
    return True

@sims4.commands.Command('animation.route_time_update', command_type=CommandType.Live)
def route_time_update(sim_id:int=None, path_id:int=None, current_time:float=None, _connection=None):
    if sim_id is None or path_id is None or current_time is None:
        return False
    current_zone = services.current_zone()
    sim = current_zone.find_object(sim_id)
    if sim is None:
        return False
    sim.route_time_update(path_id, current_time)
    return True

@sims4.commands.Command('animation.toggle_asm_name_into_callstack', command_type=CommandType.Automation)
def toggle_asm_name_into_callstack(_connection=None):
    value = animation.asm.inject_asm_name_in_callstack
    value = not value
    animation.asm.inject_asm_name_in_callstack = value

@sims4.commands.Command('animation.route_event_executed', command_type=CommandType.Live)
def route_event_executed(obj_id:int=None, path_id:int=None, event_id:int=None, _connection=None):
    if obj_id is None or event_id is None or path_id is None:
        return
    obj = services.object_manager().get(obj_id)
    if obj is None:
        logger.warn('Invalid object {} executed route event.', obj_id, owner='rmccord')
        return
    obj.routing_component.route_event_executed(event_id)

@sims4.commands.Command('animation.route_event_skipped', command_type=CommandType.Live)
def route_event_skipped(sim_id:int=None, path_id:int=None, event_id:int=None, _connection=None):
    if sim_id is None or event_id is None or path_id is None:
        return
    sim = services.object_manager().get(sim_id)
    if sim is None:
        logger.warn('Invalid sim {} skipped route event.', sim, owner='rmccord')
        return
    sim.routing_component.route_event_skipped(event_id)
