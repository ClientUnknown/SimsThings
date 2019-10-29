from server_commands.argument_helpers import TunableInstanceParamfrom sims4.commands import CommandTypeimport sims4.commandsimport services
@sims4.commands.Command('open_street.add_open_street_director')
def add_open_street_director(open_street_director_type:TunableInstanceParam(sims4.resources.Types.OPEN_STREET_DIRECTOR), _connection=None):
    zone_director = services.venue_service().get_zone_director()
    zone_director.set_open_street_director(open_street_director_type())
    sims4.commands.output('Open Street Director changed to {}.'.format(zone_director.open_street_director), _connection)

@sims4.commands.Command('open_street.remove_open_street_director', command_type=CommandType.Automation)
def remove_open_street_director(_connection=None):
    zone_director = services.venue_service().get_zone_director()
    zone_director.destroy_current_open_street_director()
