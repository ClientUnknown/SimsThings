from sims4.commands import CommandTypeimport gsi_handlersimport sims4.commands
@sims4.commands.Command('route_events.toggle_gsi_update_log', command_type=CommandType.DebugOnly)
def route_events_toggle_gsi_update_log(_connection=None):
    enabled = not gsi_handlers.route_event_handlers.update_log_enabled
    gsi_handlers.route_event_handlers.update_log_enabled = enabled
    if enabled:
        sims4.commands.output('Route Event Update Log: Enabled', _connection)
    else:
        sims4.commands.output('Route Event Update Log: Disabled', _connection)
    return True
