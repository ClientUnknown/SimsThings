from clock import ClockSpeedMode, GameSpeedChangeSourcefrom sims4.commands import CommandTypeimport clockimport servicesimport sims4.commandsimport sims4.logimport telemetry_helperlogger = sims4.log.Logger('Clock Commands')TELEMETRY_GROUP_CLOCK = 'CLCK'TELEMETRY_HOOK_CHANGE_SPEED_GAME = 'CHSG'TELEMETRY_FIELD_CLOCK_SPEED = 'clsp'clock_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_CLOCK)
def _get_speed_source(handle):
    if handle in ('Layout Manager Set Modal Visible', 'Dialog Manager Set Dialog Visible'):
        return GameSpeedChangeSource.UI_MODAL
    return GameSpeedChangeSource.GAMEPLAY

@sims4.commands.Command('clock.request_pause', 'clock.pause', command_type=CommandType.Live)
def request_pause(pause_handle_name='From Command', _connection=None):
    logger.debug('clock.pause {}', pause_handle_name)
    game_clock_service = services.game_clock_service()
    game_clock_service.push_speed(ClockSpeedMode.PAUSED, source=_get_speed_source(pause_handle_name), reason=pause_handle_name, immediate=True)
    send_clock_telemetry_data(_connection)
    return False

@sims4.commands.Command('clock.unrequest_pause', 'clock.unpause', command_type=CommandType.Live)
def unrequest_pause(pause_handle_name='From Command', _connection=None):
    logger.debug('clock.unpause {}', pause_handle_name)
    game_clock_service = services.game_clock_service()
    game_clock_service.pop_speed(ClockSpeedMode.PAUSED, source=_get_speed_source(pause_handle_name), reason=pause_handle_name, immediate=True)
    send_clock_telemetry_data(_connection)
    return False

@sims4.commands.Command('clock.toggle_pause_unpause', command_type=CommandType.Live)
def toggle_pause_unpause(pause_handle_name='From Command', _connection=None):
    logger.debug('clock.toggle_pause_unpause')
    if services.game_clock_service().clock_speed == ClockSpeedMode.PAUSED:
        unrequest_pause(pause_handle_name=pause_handle_name)
    else:
        request_pause(pause_handle_name=pause_handle_name)

@sims4.commands.Command('clock.setanimspeed')
def set_anim_speed(scale:float=1, _connection=None):
    output = sims4.commands.Output(_connection)
    if scale > 0.05:
        sims4.commands.execute('qa.broadcast animation.anim_speed {}'.format(scale), _connection)
        output('Setting scale to {}'.format(scale))
    else:
        output('Scale has to be more than 0.05')

@sims4.commands.Command('clock.setspeed', command_type=CommandType.Live)
def set_speed(speed='one', handle_name='From Command', _connection=None):
    logger.debug('clock.setspeed {}', speed)
    output = sims4.commands.Output(_connection)
    if services.current_zone().is_in_build_buy:
        output('Cannot set game speed while in build/buy mode.')
        logger.error('Attempt to set game speed while in build/buy mode.', owner='bhill')
        return
    game_clock_service = services.game_clock_service()
    speed = speed.lower()
    if speed == 'zero' or speed == 'paused':
        speed = ClockSpeedMode.PAUSED
    elif speed == 'one':
        speed = ClockSpeedMode.NORMAL
    elif speed == 'two':
        speed = ClockSpeedMode.SPEED2
    elif speed == 'three':
        speed = ClockSpeedMode.SPEED3
    else:
        output('Clock Set Speed Failed. Unrecognized speed {}.'.format(speed))
    game_clock_service.set_clock_speed(speed, source=_get_speed_source(handle_name), reason=handle_name, immediate=True)
    send_clock_telemetry_data(_connection)

@sims4.commands.Command('clock.setgametime')
def set_game_time(hours:int=0, minutes:int=0, seconds:int=0, _connection=None):
    previous_time = services.time_service().sim_now
    services.game_clock_service().set_game_time(hours, minutes, seconds)
    new_time = services.time_service().sim_now
    services.sim_info_manager().auto_satisfy_sim_motives()
    output = sims4.commands.Output(_connection)
    output('previous time = {}'.format(previous_time))
    output('new time = {}'.format(new_time))

@sims4.commands.Command('clock.now')
def now(_connection=None):
    output = sims4.commands.Output(_connection)
    game_clock_ticks = services.time_service().sim_now.absolute_ticks()
    server_ticks = services.server_clock_service().ticks()
    output('Gameclock ticks: {} Server Ticks: {}'.format(game_clock_ticks, server_ticks))
    timeline_now = services.time_service().sim_now
    game_clock_now = services.game_clock_service().now()
    output('Sim timeline now: {}'.format(timeline_now))
    output('Game clock now: {}'.format(game_clock_now))

@sims4.commands.Command('qa.clock.getgametime', command_type=sims4.commands.CommandType.Automation)
def qa_get_game_time(_connection=None):
    output = sims4.commands.AutomationOutput(_connection)
    game_clock_now = services.game_clock_service().now()
    timeline_now = services.time_service().sim_now
    results = 'GameTime;'
    results += ' GameHour:{}, GameMinute:{}, GameSecond:{}, GameDay:{}, GameWeek:{},'.format(game_clock_now.hour(), game_clock_now.minute(), game_clock_now.second(), game_clock_now.day(), game_clock_now.week())
    results += ' SimHour:{}, SimMinute:{}, SimSecond:{}, SimDay:{}, SimWeek:{},'.format(timeline_now.hour(), timeline_now.minute(), timeline_now.second(), timeline_now.day(), timeline_now.week())
    output(results)
    sims4.commands.output(results, _connection)

@sims4.commands.Command('clock.advance_game_time', command_type=sims4.commands.CommandType.Automation)
def advance_game_time(hours:int=0, minutes:int=0, seconds:int=0, _connection=None):
    previous_time = services.time_service().sim_now
    services.game_clock_service().advance_game_time(hours=hours, minutes=minutes, seconds=seconds)
    new_time = services.time_service().sim_now
    services.sim_info_manager().auto_satisfy_sim_motives()
    output = sims4.commands.Output(_connection)
    output('previous time = {}'.format(previous_time))
    output('new time = {}'.format(new_time))

@sims4.commands.Command('clock.restore_saved_clock_speed', command_type=CommandType.Live)
def restore_saved_clock_speed(_connection=None):
    services.current_zone().on_loading_screen_animation_finished()
previous_speed = None
def send_clock_telemetry_data(_connection):
    global previous_speed
    client = services.client_manager().get(_connection)
    if client is not None:
        new_speed = services.game_clock_service().clock_speed
        if new_speed != previous_speed:
            with telemetry_helper.begin_hook(clock_telemetry_writer, TELEMETRY_HOOK_CHANGE_SPEED_GAME, household=client.household) as hook:
                hook.write_int(TELEMETRY_FIELD_CLOCK_SPEED, new_speed)
            previous_speed = new_speed
BUILDBUY_PAUSE_HANDLE = 'Build Buy'
@sims4.commands.Command('clock.build_buy_pause_unpause', command_type=CommandType.Live)
def build_buy_pause_unpause(is_pause:bool=True, _connection=None):
    game_clock_service = services.game_clock_service()
    if is_pause:
        game_clock_service.push_speed(ClockSpeedMode.PAUSED, source=GameSpeedChangeSource.UI_MODAL, reason=BUILDBUY_PAUSE_HANDLE)
    else:
        game_clock_service.pop_speed(ClockSpeedMode.PAUSED, source=GameSpeedChangeSource.UI_MODAL, reason=BUILDBUY_PAUSE_HANDLE)
    return True

@sims4.commands.Command('clock.set_speed_multiplier_type', command_type=CommandType.Automation)
def set_speed_multipliers(speed_multiplier_type:clock.ClockSpeedMultiplierType, _connection=None):
    services.game_clock_service()._set_clock_speed_multiplier_type(speed_multiplier_type)

@sims4.commands.Command('clock.show_speed_info', command_type=CommandType.Automation)
def show_speed_info(_connection=None):
    game_clock = services.game_clock_service()
    output = sims4.commands.Output(_connection)
    output('-=-=-=-=-=-=-=-=-\nSPEED INFORMATION:')
    output('  Game Speed: {}'.format(game_clock.clock_speed))
    output('SPEED REQUESTS (highest priority to lowest):')
    for time_request in game_clock.game_speed_requests_gen():
        output('  {}\n'.format(time_request))
    output('-=-=-=-=-=-=-=-=-')

@sims4.commands.Command('clock.ignore_interaction_speed_change_requests', command_type=CommandType.Automation)
def ignore_interaction_speed_change_requests(value:bool=True, _connection=None):
    services.game_clock_service().ignore_game_speed_requests = value

@sims4.commands.Command('clock.clear_ui_speed_requests')
def clear_ui_speed_requests(_connection=None):
    clock_service = services.game_clock_service()
    while clock_service.pop_speed(source=GameSpeedChangeSource.UI_MODAL) is not None:
        pass
