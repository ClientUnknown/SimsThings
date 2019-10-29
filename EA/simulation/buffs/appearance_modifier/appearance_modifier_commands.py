from server_commands.argument_helpers import OptionalSimInfoParam, get_optional_targetfrom sims4.commands import CommandTypefrom tag import Tagimport sims4.commands
@sims4.commands.Command('appearance_modifier.make_permanent', command_type=CommandType.Live)
def make_active_appearance_modifier_permanent(opt_sim:OptionalSimInfoParam=None, tag:Tag=Tag.INVALID, _connection=None):
    sim_info = get_optional_target(opt_sim, _connection, target_type=OptionalSimInfoParam)
    if sim_info is None:
        sims4.commands.output('Failed to find SimInfo.', _connection)
        return False
    appearance_modifier_made_permanent = sim_info.appearance_tracker.make_active_appearance_modifier_permanent(tag)
    if appearance_modifier_made_permanent:
        sims4.commands.output('Appearance modifiers tagged with {} made permanent.'.format(tag), _connection)
    else:
        sims4.commands.output('No appearance modifiers tagged with {} found.'.format(tag), _connection)
    return True
