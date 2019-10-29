from server_commands.argument_helpers import TunableInstanceParam, OptionalTargetParam, get_optional_targetimport sims4.commandsimport services
@sims4.commands.Command('whims.print_whimsets')
def print_whimsets(_connection=None):
    output = sims4.commands.output
    aspiration_service = services.get_instance_manager(sims4.resources.Types.ASPIRATION)
    whim_sets = aspiration_service.all_whim_sets_gen()
    for whim_set in whim_sets:
        output('Whim Set: {}'.format(whim_set), _connection)
        for whim in whim_set.whims:
            output('{}'.format(whim), _connection)
        output('', _connection)
    return True

@sims4.commands.Command('whims.activate_whimset')
def activate_whimset(whimset:TunableInstanceParam(sims4.resources.Types.ASPIRATION), sim_id:OptionalTargetParam=None, chained:bool=False, _connection=None):
    if whimset is None:
        sims4.commands.output('Invalid whimset given when trying to activate whimset.', _connection)
        return False
    sim = get_optional_target(sim_id, _connection)
    if sim is None:
        sims4.commands.output('No sim given when trying to activate whimset.', _connection)
        return False
    if sim.sim_info.whim_tracker is None:
        sims4.commands.output('The Sim specified ({}) does not have a whims tracker. Likely because they are in a LOD level without a whims tracker.'.format(sim.sim_info))
        return False
    sim.sim_info.whim_tracker.debug_activate_whimset(whimset, chained)
    return True

@sims4.commands.Command('whims.give_whim')
def give_whim(whim:TunableInstanceParam(sims4.resources.Types.SITUATION_GOAL), sim_id:OptionalTargetParam=None, _connection=None):
    if whim is None:
        sims4.commands.output('Invalid whim given when trying to give whim.', _connection)
        return False
    sim = get_optional_target(sim_id, _connection)
    if sim is None:
        sims4.commands.output('No sim given when trying to give whim.', _connection)
        return False
    if sim.sim_info.whim_tracker is None:
        sims4.commands.output('The Sim specified ({}) does not have a whims tracker. Likely because they are in a LOD level without a whims tracker.'.format(sim.sim_info))
        return False
    sim.sim_info.whim_tracker.debug_activate_whim(whim)
    return True

@sims4.commands.Command('whims.refresh', command_type=sims4.commands.CommandType.Live)
def refresh(whim:TunableInstanceParam(sims4.resources.Types.SITUATION_GOAL), sim_id:OptionalTargetParam=None, _connection=None):
    if whim is None:
        sims4.commands.output('Invalid whim given when trying to refresh whims.', _connection)
        return False
    sim = get_optional_target(sim_id, _connection)
    if sim is None:
        sims4.commands.output('No sim given when trying to refresh whims.', _connection)
        return False
    if sim.sim_info.whim_tracker is None:
        sims4.commands.output('The Sim specified ({}) does not have a whims tracker. Likely because they are in a LOD level without a whims tracker.'.format(sim.sim_info))
        return False
    sim.sim_info.whim_tracker.refresh_whim(whim)
    return True

@sims4.commands.Command('whims.toggle_lock', command_type=sims4.commands.CommandType.Live)
def toggle_lock(whim:TunableInstanceParam(sims4.resources.Types.SITUATION_GOAL), sim_id:OptionalTargetParam=None, _connection=None):
    if whim is None:
        sims4.commands.output('Invalid whim given when trying to toggle lock for whims.', _connection)
        return False
    sim = get_optional_target(sim_id, _connection)
    if sim is None:
        sims4.commands.output('No Sim given when trying to toggle lock for whims.', _connection)
        return False
    if sim.sim_info.whim_tracker is None:
        sims4.commands.output('The Sim specified ({}) does not have a whims tracker. Likely because they are in a LOD level without a whims tracker.'.format(sim.sim_info))
        return False
    sim.sim_info.whim_tracker.toggle_whim_lock(whim)
    return True

@sims4.commands.Command('whims.give_whim_from_whimset', command_type=sims4.commands.CommandType.Live)
def whims_give_from_whimset(whimset:TunableInstanceParam(sims4.resources.Types.ASPIRATION), opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        if sim.sim_info.whim_tracker is None:
            sims4.commands.output('The Sim specified ({}) does not have a whims tracker. Likely because they are in a LOD level without a whims tracker.'.format(sim.sim_info))
            return False
        else:
            sim.sim_info.whim_tracker.debug_offer_whim_from_whimset(whimset)
            return True
    return False

@sims4.commands.Command('whims.offer_whims')
def offer_whims(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        return False
    if sim.sim_info.whim_tracker is None:
        return
    sim.sim_info.whim_tracker.start_whims_tracker()
