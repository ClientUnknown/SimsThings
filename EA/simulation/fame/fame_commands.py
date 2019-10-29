from bucks.bucks_utils import BucksUtilsfrom careers.career_interactions import set_force_fame_momentfrom fame.fame_tuning import FameTunablesfrom server_commands.argument_helpers import OptionalTargetParam, get_optional_targetimport servicesimport sims4.commandslogger = sims4.log.Logger('Fame', default_owner='rfleig')
@sims4.commands.Command('fame.set_start_all_sims_opted_out_of_fame', command_type=sims4.commands.CommandType.Live)
def set_start_all_sims_opted_out_of_fame(start_opted_out:bool, _connection=None):
    services.sim_info_manager().set_start_all_sims_opted_out_of_fame(start_opted_out)
    return True

@sims4.commands.Command('fame.set_freeze_fame', command_type=sims4.commands.CommandType.Cheat)
def set_freeze_fame(freeze_fame:bool, opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No target Sim to freeze the fame of.', _connection)
        return False
    if not sim.allow_fame:
        if freeze_fame:
            sims4.commands.output('Cannot freeze fame on a sim with disabled fame.', _connection)
        else:
            sims4.commands.output('Fame is already unfrozen for sims with disabled fame.', _connection)
        return False
    sim.set_freeze_fame(freeze_fame)
    sims4.commands.output("{}'s fame frozen setting is now set to {}.".format(sim, freeze_fame), _connection)
    return True

@sims4.commands.Command('fame.set_allow_fame', command_type=sims4.commands.CommandType.Live)
def set_allow_fame(allow_fame:bool, opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No target Sim to manipulate the fame of.', _connection)
        return False
    sim.force_allow_fame(allow_fame)
    sims4.commands.output("{}'s allow_fame setting is set to {}".format(sim, sim.allow_fame), _connection)
    return True

@sims4.commands.Command('fame.show_allow_fame', command_type=sims4.commands.CommandType.Automation)
def show_allow_fame(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No target Sim to get the value of allow_fame from.', _connection)
        return False
    sims4.commands.output("{}'s allow_fame setting is set to {}".format(sim, sim.allow_fame), _connection)
    return True

@sims4.commands.Command('famepoints', command_type=sims4.commands.CommandType.Cheat)
def add_fame_points(points:int=0, opt_sim:OptionalTargetParam=None, _connection=None):
    if FameTunables.FAME_PERKS_BUCKS_TYPE is None:
        sims4.commands.output('The DLC that is necessary for this cheat is not loaded.', _connection)
        return
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No Target Sim to add the fame points too.', _connection)
    bucks_tracker = BucksUtils.get_tracker_for_bucks_type(FameTunables.FAME_PERKS_BUCKS_TYPE, sim.id, add_if_none=True)
    bucks_tracker.try_modify_bucks(FameTunables.FAME_PERKS_BUCKS_TYPE, points)
    sims4.commands.output('{} Fame Points have been added to {}'.format(points, sim), _connection)

@sims4.commands.Command('fame.add_sim_to_squad', command_type=sims4.commands.CommandType.Automation)
def add_sim_to_squad(sim_with_squad:int=None, sim_to_add:int=None, _connection=None):
    object_manager = services.object_manager()
    sim = object_manager.get(sim_with_squad)
    if sim is None:
        sims4.commands.output('Sim with the squad does not exist, please specify an existing sim id.', _connection)
        return
    target = object_manager.get(sim_to_add)
    if target is None:
        sims4.commands.output('Sim to add to the squad does not exist, please specify an existing sim id.', _connection)
        return
    sim.sim_info.add_sim_info_id_to_squad(target.sim_info.id)

@sims4.commands.Command('fame.remove_sim_from_squad', command_type=sims4.commands.CommandType.Automation)
def remove_sim_from_squad(sim_with_squad:int=None, sim_to_add:int=None, _connection=None):
    object_manager = services.object_manager()
    sim = object_manager.get(sim_with_squad)
    if sim is None:
        sims4.commands.output('Sim with the squad does not exist, please specify an existing sim id.', _connection)
        return
    target = object_manager.get(sim_to_add)
    if target is None:
        sims4.commands.output('Sim to remove from the squad does not exist, please specify an existing sim id.', _connection)
        return
    sim.sim_info.remove_sim_info_id_from_squad(target.sim_info.id)

@sims4.commands.Command('fame.turn_off_lifestyle_brand', command_type=sims4.commands.CommandType.Live)
def turn_off_lifestyle_brand(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No target Sim to turn the lifestyle brand off for.', _connection)
        return False
    tracker = sim.sim_info.lifestyle_brand_tracker
    if tracker is None:
        sims4.commands.output("{} doesn't have a lifestyle brand tracker, something is seriously wrong. Get GPE help please.".format(sim))
        return False
    tracker.clear_brand()
    return True

@sims4.commands.Command('fame.award_parent_fame_bonus', command_type=sims4.commands.CommandType.Live)
def award_parent_fame_bonus(child_sim_id:int, _connection=None):
    if FameTunables.FAME_RANKED_STATISTIC is None:
        return False
    sim_info_manager = services.sim_info_manager()
    child_sim = sim_info_manager.get(child_sim_id)
    if child_sim is None:
        logger.error('Calling award_parent_fame_bonus passing in an invalid sim id {}. Sim not found', child_sim_id)
    child_fame = child_sim.commodity_tracker.get_statistic(FameTunables.FAME_RANKED_STATISTIC, add=True)
    child_fame_rank = child_fame.rank_level
    max_parent_rank = 0
    genealogy = child_sim.sim_info.genealogy
    for parent_id in genealogy.get_parent_sim_ids_gen():
        parent = sim_info_manager.get(parent_id)
        if parent is None:
            pass
        else:
            fame = parent.commodity_tracker.get_statistic(FameTunables.FAME_RANKED_STATISTIC)
            if fame is None:
                pass
            else:
                fame_rank = fame.rank_level
                if fame_rank > max_parent_rank:
                    max_parent_rank = fame_rank
    difference = max(0, max_parent_rank - child_fame_rank)
    bonus = FameTunables.PARENT_FAME_AGE_UP_BONUS.get(difference, 0)
    child_fame.add_value(bonus)
    return True

@sims4.commands.Command('fame.force_fame_moments', command_type=sims4.commands.CommandType.Cheat)
def force_fame_moments(enable:bool=True, _connection=None):
    set_force_fame_moment(enable)
    sims4.commands.output('Force Fame Moment Cheat: {}.'.format(enable), _connection)
