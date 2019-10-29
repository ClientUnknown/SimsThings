import sims4.commandsfrom server_commands.argument_helpers import OptionalTargetParam, get_optional_targetfrom vet.vet_clinic_utils import get_vet_clinic_zone_director
@sims4.commands.Command('vet.bill_owner_for_treatment', command_type=sims4.commands.CommandType.Live)
def bill_owner_for_treatment(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output("Sim {} doesn't exist.".format(opt_sim), _connection)
        return False
    zone_director = get_vet_clinic_zone_director()
    if zone_director is None:
        sims4.commands.Command('Not currently on a vet clinic lot.', _connection)
        return False
    zone_director.bill_owner_for_treatment(sim)
    return True
