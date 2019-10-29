import servicesimport sims4.commands
@sims4.commands.Command('zone_director.print_situation_shifts')
def print_situation_shifts(_connection=None):
    zone_director = services.venue_service().get_zone_director()
    if not hasattr(zone_director, 'situation_shifts'):
        sims4.commands.output('{} has no schedule'.format(zone_director), _connection)
        return

    def output(s):
        sims4.commands.output(s, _connection)

    for shift in zone_director.situation_shifts:
        shift.shift_curve.debug_output_schedule(output)
