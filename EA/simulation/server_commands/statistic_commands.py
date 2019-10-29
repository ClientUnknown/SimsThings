from collections import Counterimport collectionsimport randomimport weakreffrom autonomy.autonomy_request import AutonomyPostureBehaviorfrom interactions import priorityfrom interactions.aop import AffordanceObjectPairfrom interactions.context import InteractionContext, InteractionBucketTypefrom server_commands.argument_helpers import OptionalTargetParam, get_optional_target, TunableInstanceParam, OptionalSimInfoParamfrom sims.sim_info import SimInfofrom statistics.commodity import Commodityfrom statistics.continuous_statistic import ContinuousStatisticfrom statistics.skill import Skillimport autonomy.autonomy_modesimport autonomy.autonomy_modifierimport servicesimport sims4.commandsimport statistics.skilllogger = sims4.log.Logger('SimStatistics')
@sims4.commands.Command('stats.show_stats')
def show_statistics(display_skill_only=False, opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        for stat in sim.statistics_gen():
            if display_skill_only:
                if isinstance(stat, statistics.skill.Skill):
                    s = 'Statistic: {}, Value: {},  Level: {}.'.format(stat.__class__.__name__, stat.get_value(), stat.get_user_value())
                    sims4.commands.output(s, _connection)
            s = 'Statistic: {}, Value: {},  Level: {}.'.format(stat.__class__.__name__, stat.get_value(), stat.get_user_value())
            sims4.commands.output(s, _connection)

@sims4.commands.Command('stats.show_commodities', command_type=sims4.commands.CommandType.Automation)
def show_commodities(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None and sim and sim.statistic_tracker is not None:
        sim.commodity_tracker.debug_output_all(_connection)
        sim.statistic_tracker.debug_output_all(_connection)
    else:
        sims4.commands.output('No target for stats.show_commodities.', _connection)

@sims4.commands.Command('stats.show_static_commodities')
def show_static_commodities(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None and sim.static_commodity_tracker is not None:
        sim.static_commodity_tracker.debug_output_all(_connection)
    else:
        sims4.commands.output('No target for stats.show_static_commodities.', _connection)

@sims4.commands.Command('qa.stats.show_commodities', command_type=sims4.commands.CommandType.Automation)
def show_commodities_automation(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None and sim.commodity_tracker is not None:
        sim.commodity_tracker.debug_output_all_automation(_connection)
    sims4.commands.automation_output('CommodityInfo; Type:END', _connection)

@sims4.commands.Command('mood.show_active_mood_type')
def show_active_mood_type(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        mood_type = sim.get_mood()
        sims4.commands.output("{0}'s active mood type is {1}".format(sim, mood_type), _connection)
        return True
    else:
        sims4.commands.output('No target for mood.show_active_mood_type', _connection)
        return False

@sims4.commands.Command('stats.show_all_statistics')
def show_all_statistics(opt_sim:OptionalTargetParam=None, _connection=None):
    sim_or_obj = get_optional_target(opt_sim, _connection)
    if sim_or_obj is not None:
        show_commodities(opt_sim=opt_sim, _connection=_connection)
        if sim_or_obj.is_sim:
            show_statistics(opt_sim=opt_sim, _connection=_connection)

@sims4.commands.Command('stats.show_change')
def show_change(stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC, exact_match=True), opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None and stat_type is not None:
        tracker = sim.get_tracker(stat_type)
        stat = tracker.get_statistic(stat_type)
        if stat is None:
            sims4.commands.output("Couldn't find stat on sim: {}".format(stat_type), _connection)
            return
        if not isinstance(stat, ContinuousStatistic):
            sims4.commands.output('{} is not a continuous statistic'.format(stat), _connection)
            return
        sims4.commands.output('\tDecay: {}\n\tChange: {}\n\tTotal Delta: {}'.format(stat.get_decay_rate(), stat._get_change_rate_without_decay(), stat.get_change_rate()), _connection)
    else:
        sims4.commands.output('No sim or stat type for stats.show_change.', _connection)

@sims4.commands.Command('stats.fill_commodities', command_type=sims4.commands.CommandType.Cheat)
def set_commodities_to_best_values(opt_sim:OptionalTargetParam=None, visible_only:bool=True, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None:
        sims4.commands.output('Setting all motives on the current sim to full.', _connection)
        if sim.commodity_tracker is not None:
            sim.commodity_tracker.set_all_commodities_to_best_value(visible_only=visible_only)

@sims4.commands.Command('stats.fill_commodities_household', command_type=sims4.commands.CommandType.Cheat)
def set_commodities_to_best_values_household(visible_only:bool=True, _connection=None):
    tgt_client = services.client_manager().get(_connection)
    sims4.commands.output('Setting all motives on all household sims to full.', _connection)
    for sim_info in tgt_client.selectable_sims:
        if sim_info.commodity_tracker is not None:
            sim_info.commodity_tracker.set_all_commodities_to_best_value(visible_only=visible_only)

@sims4.commands.Command('stats.tank_commodities')
def tank_commodities(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is not None and sim.commodity_tracker is not None:
        sims4.commands.output('Setting all motives on the current sim to min.', _connection)
        sim.commodity_tracker.debug_set_all_to_min()

@sims4.commands.Command('stats.set_stat', 'stats.set_commodity', command_type=sims4.commands.CommandType.Cheat)
def set_statisitic(stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC, exact_match=True), value:float=None, opt_sim:OptionalSimInfoParam=None, _connection=None):
    if stat_type is None:
        sims4.commands.output('Invalid stat type used for stats.set_stat.', _connection)
        return
    if value is None:
        sims4.commands.output('Invalid value set for stats.set_stat.', _connection)
        return
    target_object = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection, notify_failure=False)
    if target_object is None:
        target_object = get_optional_target(OptionalTargetParam(str(opt_sim.target_id)), _connection=_connection, notify_failure=False)
    if target_object is not None:
        tracker = target_object.get_tracker(stat_type)
        tracker.set_value(stat_type, value)
    else:
        sims4.commands.output('No target found with ID:{} stats.set_stat.'.format(opt_sim.target_id), _connection)

@sims4.commands.Command('fillmotive', command_type=sims4.commands.CommandType.Cheat)
def fill_motive(stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC, exact_match=True), _connection=None):
    if stat_type is not None:
        tgt_client = services.client_manager().get(_connection)
        tracker = tgt_client.active_sim.get_tracker(stat_type)
        tracker.set_value(stat_type, stat_type.max_value)
        return True
    return False

@sims4.commands.Command('stats.add_to_stat', 'stats.add_to_commodity')
def add_value_to_statistic(stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC, exact_match=True), value:float=None, opt_target:OptionalTargetParam=None, _connection=None):
    target = get_optional_target(opt_target, _connection)
    if target is not None and stat_type is not None and value is not None:
        tracker = target.get_tracker(stat_type)
        tracker.add_value(stat_type, value)
    else:
        sims4.commands.output('No target for stats.add_to_stat. Params: stat_name, value, optional target', _connection)

@sims4.commands.Command('stats.add_stat_to_tracker', 'stats.add_commodity_to_tracker')
def add_statistic_to_tracker(stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC, exact_match=True), opt_target:OptionalTargetParam=None, _connection=None):
    target = get_optional_target(opt_target, _connection)
    if target is not None and stat_type is not None:
        tracker = target.get_tracker(stat_type)
        tracker.add_statistic(stat_type)
    else:
        sims4.commands.output('No target for stats.add_stat_to_tracker. Params: stat_name, optional target', _connection)

@sims4.commands.Command('stats.remove_stat', 'stats.remove_commodity')
def remove_statistic(stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC, exact_match=True), opt_target:OptionalTargetParam=None, _connection=None):
    target = get_optional_target(opt_target, _connection)
    if target is not None and stat_type is not None:
        tracker = target.get_tracker(stat_type)
        tracker.remove_statistic(stat_type)
    else:
        sims4.commands.output('No target for stats.remove_stat. Params: stat_name, optional target', _connection)

@sims4.commands.Command('stats.add_static_commodity_to_tracker')
def add_static_commodity_to_tracker(static_commodity:TunableInstanceParam(sims4.resources.Types.STATIC_COMMODITY), opt_target:OptionalTargetParam=None, _connection=None):
    target = get_optional_target(opt_target, _connection)
    if target is not None:
        tracker = target.get_tracker(static_commodity)
        tracker.add_statistic(static_commodity)
    else:
        sims4.commands.output('No target for stats.add_static_commodity_to_tracker. Params: stat_name, optional target', _connection)

@sims4.commands.Command('stats.remove_static_commodity_from_tracker')
def remove_static_commodity_from_tracker(static_commodity:TunableInstanceParam(sims4.resources.Types.STATIC_COMMODITY), opt_target:OptionalTargetParam=None, _connection=None):
    target = get_optional_target(opt_target, _connection)
    if target is not None:
        tracker = target.get_tracker(static_commodity)
        tracker.remove_statistic(static_commodity)
    else:
        sims4.commands.output('No target for stats.remove_static_commodity_from_tracker. Params: stat_name, optional target', _connection)

@sims4.commands.Command('stats.set_modifier', command_type=sims4.commands.CommandType.Live)
def set_modifier(stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC), level:float=None, opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None or stat_type is None or level is None:
        sims4.commands.output('Unable to set modifier - invalid arguments.', _connection)
        return
    stat = sim.get_statistic(stat_type)
    if stat is None:
        stat = sim.add_statistic(stat_type)
    stat.add_statistic_modifier(level)
    if isinstance(stat, Skill):
        sim.sim_info.current_skill_guid = stat.guid64

@sims4.commands.Command('stats.remove_modifier', command_type=sims4.commands.CommandType.Live)
def remove_modifier(stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC), level:float=None, opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None or stat_type is None or level is None:
        sims4.commands.output('Unable to remove modifier - invalid arguments.', _connection)
        return
    stat = sim.get_statistic(stat_type)
    if stat is None:
        return
    stat.remove_statistic_modifier(level)
    if sim.sim_info.current_skill_guid == stat.guid64:
        sim.sim_info.current_skill_guid = 0

def _set_skill_level(stat_type, level, sim, _connection):
    stat = sim.commodity_tracker.get_statistic(stat_type)
    if stat is None:
        stat = sim.commodity_tracker.add_statistic(stat_type)
        if stat is None:
            sims4.commands.output('Unable to add Skill due to entitlement restriction {}.'.format(stat_type), _connection)
            return
    if not isinstance(stat, statistics.skill.Skill):
        sims4.commands.output('Unable to set Skill level - statistic {} is a {}, not a skill.'.format(stat_type, type(stat)), _connection)
        return
    sims4.commands.output('Setting Skill {0} to level {1}'.format(stat_type, level), _connection)
    sim.commodity_tracker.set_user_value(stat_type, level)

@sims4.commands.Command('stats.set_skill_level', command_type=sims4.commands.CommandType.Cheat)
def set_skill_level(stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC), level:int=None, opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None or (stat_type is None or level is None) or sim.commodity_tracker is None:
        sims4.commands.output('Unable to set Skill level - invalid arguments or sim info has no commodity tracker.', _connection)
        return
    _set_skill_level(stat_type, level, sim, _connection)

@sims4.commands.Command('stats.set_all_skills_max', command_type=sims4.commands.CommandType.Automation)
def set_skills_to_max_level(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None or sim.commodity_tracker is None:
        sims4.commands.output('Unable to max skills - invalid sim or sim info has no commodity tracker.', _connection)
        return
    skill_types = set()
    skill_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
    for skill_type in skill_manager.get_ordered_types(only_subclasses_of=Skill):
        if skill_type.can_add(sim):
            skill_types.add(skill_type)
    while len(skill_types) != 0:
        new_skill_types = set()
        for skill_type in skill_types:
            _set_skill_level(skill_type, skill_type.max_level, sim, _connection)
            for unlockable_skill_type in skill_type.skill_unlocks_on_max:
                if sim.commodity_tracker.get_user_value(unlockable_skill_type) != skill_type.max_level:
                    new_skill_types.add(unlockable_skill_type)
        skill_types = new_skill_types

@sims4.commands.Command('stats.clear_skill')
def clear_skill(opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('Invalid Sim id: {}'.format(opt_sim), _connection)
        return
    tracker = sim.commodity_tracker
    if tracker is None:
        sims4.commands.output('Unable to clear_skill - sim info has no commodity tracker.', _connection)
        return
    statistics = list(tracker)
    stats_removed = []
    for stat in statistics:
        if stat.is_skill:
            stat_type = type(stat)
            stats_removed.append(stat_type)
            tracker.remove_statistic(stat_type)
    sims4.commands.output('Removed {} skills from {}'.format(len(stats_removed), sim), _connection)

@sims4.commands.Command('stats.solve_motive', command_type=sims4.commands.CommandType.Live)
def solve_motive(stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC, exact_match=True), opt_sim:OptionalTargetParam=None, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None or stat_type is None:
        sims4.commands.output('Unable to identify Sim or Motive - invalid arguments.', _connection)
        return
    if sim.commodity_tracker is None:
        sims4.commands.output('Unable to solve motive - sim info has no commodity tracker.', _connection)
        return
    stat = sim.commodity_tracker.get_statistic(stat_type)
    if stat is None:
        sims4.commands.output('Unable to solve motive {} on the Sim .'.format(stat_type), _connection)
        return
    if not sim.queue.can_queue_visible_interaction():
        sims4.commands.output('Interaction queue is full, cannot add anymore interactions.', _connection)
        return
    context = InteractionContext(sim, InteractionContext.SOURCE_AUTONOMY, priority.Priority.High, bucket=InteractionBucketType.DEFAULT)
    autonomy_request = autonomy.autonomy_request.AutonomyRequest(sim, autonomy_mode=autonomy.autonomy_modes.FullAutonomy, commodity_list=[stat], context=context, consider_scores_of_zero=True, posture_behavior=AutonomyPostureBehavior.IGNORE_SI_STATE, is_script_request=True, allow_opportunity_cost=False, autonomy_mode_label_override='AutoSolveMotive')
    selected_interaction = services.autonomy_service().find_best_action(autonomy_request)
    if selected_interaction is None:
        commodity_interaction = stat_type.commodity_autosolve_failure_interaction
        if commodity_interaction is None:
            return
        if not sim.queue.has_duplicate_super_affordance(commodity_interaction, sim, None):
            failure_aop = AffordanceObjectPair(commodity_interaction, None, commodity_interaction, None)
            failure_aop.test_and_execute(context)
        sims4.commands.output('Could not find a good interaction to solve {}.'.format(stat_type), _connection)
        return
    if sim.queue.has_duplicate_super_affordance(selected_interaction.affordance, sim, selected_interaction.target):
        sims4.commands.output('Duplicate Interaction in the queue.', _connection)
        return
    if not AffordanceObjectPair.execute_interaction(selected_interaction):
        sims4.commands.output('Failed to execute SI {}.'.format(selected_interaction), _connection)
        return
    sims4.commands.output('Successfully executed SI {}.'.format(selected_interaction), _connection)

def _randomize_motive(stat_type, sim, min_value, max_value):
    if min_value is None or min_value < stat_type.min_value:
        min_value = stat_type.min_value
    if max_value is None or max_value > stat_type.max_value:
        max_value = stat_type.max_value
    random_value = random.uniform(min_value, max_value)
    sim.set_stat_value(stat_type, random_value)

@sims4.commands.Command('stats.randomize_motives')
def randomize_motives(min_value:int=None, max_value:int=None, opt_sim:OptionalTargetParam=None, _connection=None):
    if opt_sim is not None:
        sim = get_optional_target(opt_sim, _connection)
        if sim is None:
            sims4.commands.output('Unable to identify Sim - invalid arguments.', _connection)
            return
    else:
        for sim in services.sim_info_manager().instanced_sims_gen():
            for stat_type in sim.sim_info.get_initial_commodities():
                _randomize_motive(stat_type, sim, min_value, max_value)

@sims4.commands.Command('stats.set_convergence')
def set_convergence(stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC, exact_match=True), convergence:float=None, opt_target:OptionalTargetParam=None, _connection=None):
    target = get_optional_target(opt_target, _connection)
    if target is not None and stat_type is not None and convergence is not None:
        tracker = target.get_tracker(stat_type)
        tracker.set_convergence(stat_type, convergence)
    else:
        sims4.commands.output('No target for stats.set_convergence.', _connection)

@sims4.commands.Command('stats.reset_convergence')
def reset_convergence(stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC, exact_match=True), opt_target:OptionalTargetParam=None, _connection=None):
    target = get_optional_target(opt_target, _connection)
    if target is not None and stat_type is not None:
        tracker = target.get_tracker(stat_type)
        tracker.reset_convergence(stat_type)
    else:
        sims4.commands.output('No target for stats.reset_convergence.', _connection)

def _set_stat_percent(stat, tracker, percent, _connection=0):
    stat_range = stat.max_value_tuning - stat.min_value_tuning
    stat_value = percent*stat_range + stat.min_value_tuning
    sims4.commands.output('Setting Statistic {0} to {1}'.format(stat.__name__, stat_value), _connection)
    tracker.set_value(stat, stat_value)

@sims4.commands.Command('stats.set_commodity_percent')
def set_commodity_percent(stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC, exact_match=True), value:float=None, opt_sim:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    tracker = sim_info.get_tracker(stat_type)
    if sim_info is not None and (stat_type is not None and value is not None) and tracker is not None:
        _set_stat_percent(stat_type, tracker, value, _connection=_connection)
    else:
        sims4.commands.output('Unable to set Commodity - invalid arguments or sim info has no commodity tracker.', _connection)

@sims4.commands.Command('stats.fill_all_sim_commodities_except')
def fill_all_sim_commodities_except(stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC, exact_match=True), opt_sim:OptionalTargetParam=None, _connection=None):
    if stat_type is not None:
        if opt_sim is not None:
            sim = get_optional_target(opt_sim, _connection)
            tracker = sim.get_tracker(stat_type)
            if sim is None or tracker is None:
                sims4.commands.output('No valid target for stats.fill_all_sim_commodities_except', _connection)
                return
            tracker.debug_set_all_to_max_except(stat_type)
        else:
            for sim in services.sim_info_manager().instanced_sims_gen():
                tracker = sim.get_tracker(stat_type)
                tracker.debug_set_all_to_max_except(stat_type)
    else:
        sims4.commands.output('Unable to set Commodity - commodity {} not found.'.format(stat_type.lower()), _connection)
with sims4.reload.protected(globals()):
    autonomy_handles = collections.defaultdict(weakref.WeakKeyDictionary)
@sims4.commands.Command('stats.enable_commodities', command_type=sims4.commands.CommandType.Cheat)
def enable_commodities(opt_sim:OptionalTargetParam=None, *stat_types, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No valid target for stats.enable_commodities', _connection)
        return
    for stat_type in stat_types:
        if sim in autonomy_handles[stat_type]:
            sim.remove_statistic_modifier(autonomy_handles[stat_type][sim])
            del autonomy_handles[stat_type][sim]

@sims4.commands.Command('stats.enable_all_commodities', command_type=sims4.commands.CommandType.Cheat)
def enable_all_commodities(opt_sim:OptionalTargetParam=None, _connection=None):
    if opt_sim is not None:
        sim = get_optional_target(opt_sim, _connection)
        if sim is None:
            sims4.commands.output('No valid target for stats.enable_all_commodities', _connection)
            return
        for sim_handle_dictionary in autonomy_handles.values():
            if sim in sim_handle_dictionary:
                sim.remove_statistic_modifier(sim_handle_dictionary[sim])
                del sim_handle_dictionary[sim]
    else:
        for sim_handle_dictionary in autonomy_handles.values():
            for (sim, handle) in sim_handle_dictionary.items():
                sim.remove_statistic_modifier(handle)
            sim_handle_dictionary.clear()

def _disable_commodities(sim, commodities_to_lock=[]):
    for commodity in commodities_to_lock:
        if sim in autonomy_handles[commodity]:
            return
        modifier = autonomy.autonomy_modifier.AutonomyModifier(decay_modifiers={commodity: 0})
        handle = sim.add_statistic_modifier(modifier)
        autonomy_handles[commodity][sim] = handle

@sims4.commands.Command('stats.disable_commodities', command_type=sims4.commands.CommandType.Cheat)
def disable_commodities(opt_sim:OptionalTargetParam=None, *stat_types, _connection=None):
    sim = get_optional_target(opt_sim, _connection)
    if sim is None:
        sims4.commands.output('No valid target for stats.disable_commodities', _connection)
        return
    _disable_commodities(sim, stat_types)

@sims4.commands.Command('stats.disable_all_commodities', command_type=sims4.commands.CommandType.Cheat)
def disable_all_commodities(opt_sim:OptionalTargetParam=None, _connection=None):
    if opt_sim is not None:
        sim = get_optional_target(opt_sim, _connection)
        if sim is None:
            sims4.commands.output('No valid target for stats.disable_sim_commodities', _connection)
            return
        _disable_commodities(sim, sim.sim_info.get_initial_commodities())
    else:
        for sim in services.sim_info_manager().instanced_sims_gen():
            _disable_commodities(sim, sim.sim_info.get_initial_commodities())

@sims4.commands.Command('stats.enable_autosatisfy_curves', command_type=sims4.commands.CommandType.Cheat)
def enable_autosatisfy_curves(_connection=None):
    Commodity.use_autosatisfy_curve = True

@sims4.commands.Command('stats.disable_autosatisfy_curves', command_type=sims4.commands.CommandType.Cheat)
def disable_autosatisfy_curves(_connection=None):
    Commodity.use_autosatisfy_curve = False

@sims4.commands.Command('stats.publish_ranked_stat_progress', command_type=sims4.commands.CommandType.Live)
def publish_ranked_stat_progress(opt_sim:OptionalSimInfoParam=None, stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC, exact_match=True)=None, _connection=None):
    sim = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim is None:
        sims4.commands.output('No Sim specified, you must specify a Sim to get the rank.', _connection)
        return
    if not hasattr(stat_type, 'rank_level'):
        sims4.commands.output('The specified statistic is not a Ranked Statistic and therefore has no Rank, please specify a Ranked Statistic.', _connection)
        return
    commodity_tracker = sim.commodity_tracker
    stat = commodity_tracker.get_statistic(stat_type)
    if stat is None:
        sims4.commands.output("Sim doesn't have the specified statistic.", _connection)
        return
    stat.create_and_send_commodity_update_msg(is_rate_change=False, allow_npc=True)

@sims4.commands.Command('stats.set_rank', command_type=sims4.commands.CommandType.Live)
def ranked_stat_set_rank(opt_sim:OptionalSimInfoParam=None, stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC, exact_match=True)=None, rank:int=1, _connection=None):
    sim = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim is None:
        sims4.commands.output('No Sim specified, you must specify a Sim to set the rank on.', _connection)
        return
    if not hasattr(stat_type, 'rank_level'):
        sims4.commands.output('The specified statistic is not a Ranked Statistic and therefore has no Rank, please specify a Ranked Statistic.', _connection)
        return
    commodity_tracker = sim.commodity_tracker
    stat = commodity_tracker.get_statistic(stat_type)
    if stat.rank_level == rank:
        return
    stat.set_value(stat.points_to_rank(rank))
    if stat.rank_level == rank:
        sims4.commands.output('Success.', _connection)
    else:
        sims4.commands.output('Failure, sim is now set to rank {}'.format(stat.rank_level), _connection)

@sims4.commands.Command('stats.get_rank', command_type=sims4.commands.CommandType.Automation)
def ranked_stat_get_rank(opt_sim:OptionalSimInfoParam=None, stat_type:TunableInstanceParam(sims4.resources.Types.STATISTIC, exact_match=True)=None, _connection=None):
    sim = get_optional_target(opt_sim, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim is None:
        sims4.commands.output('No Sim specified, you must specify a Sim.', _connection)
        sims4.commands.automation_output('RankedStat; Status:Failed', _connection)
        return
    if not hasattr(stat_type, 'rank_level'):
        sims4.commands.output('The specified statistic is not a Ranked Statistic and therefore has no Rank, please specify a Ranked Statistic.', _connection)
        sims4.commands.automation_output('RankedStat; Status:Failed', _connection)
        return
    commodity_tracker = sim.commodity_tracker
    stat = commodity_tracker.get_statistic(stat_type)
    sims4.commands.automation_output('RankedStat; Status:Success, RankLevel:{}'.format(stat.rank_level), _connection)

@sims4.commands.Command('stats.count_commodities')
def count_commodities(_connection=None):
    counter = Counter()
    sim_info_manager = services.sim_info_manager()
    for sim_info in sim_info_manager.values():
        commodity_tracker = sim_info.commodity_tracker
        for commodity in commodity_tracker:
            counter[commodity.stat_type] += 1
    sorted_counter = list(counter.items())
    sorted_counter.sort(key=lambda item: item[1])
    for (commodity_type, count) in sorted_counter:
        sims4.commands.output('Commodity Type: {} : Count: {}'.format(commodity_type, count), _connection)
