from sims4.commands import CommandTypefrom venues.secret_lab_venue.secret_lab_zone_director import SecretLabCommandimport servicesimport sims4.commands
@sims4.commands.Command('secret_lab.reveal_next_section', command_type=sims4.commands.CommandType.Automation)
def reveal_next_section(_connection=None):
    zone_director = services.venue_service().get_zone_director()
    zone_director.handle_command(SecretLabCommand.RevealNextSection)

@sims4.commands.Command('secret_lab.reveal_all_sections', command_type=sims4.commands.CommandType.Automation)
def reveal_all_sections(_connection=None):
    zone_director = services.venue_service().get_zone_director()
    zone_director.handle_command(SecretLabCommand.RevealAllSections)

@sims4.commands.Command('secret_lab.reset_lab', command_type=sims4.commands.CommandType.Automation)
def reset_lab(_connection=None):
    zone_director = services.venue_service().get_zone_director()
    zone_director.handle_command(SecretLabCommand.ResetLab)
