from server_commands.argument_helpers import OptionalSimInfoParam, get_optional_targetfrom sims4.commands import CommandTypeimport servicesimport sims4.commands
@sims4.commands.Command('adoption.remove_sim_info', command_type=CommandType.Live)
def remove_sim_info(opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        return False
    adoption_service = services.get_adoption_service()
    adoption_service.remove_sim_info(sim_info)
    return True
