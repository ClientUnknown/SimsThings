from gsi_handlers.gsi_utils import parse_filter_to_listfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersfrom statistics.ranked_statistic import RankedStatisticimport servicesimport sims4.resourcesranked_stat_schema = GsiGridSchema(label='Ranked Stat')ranked_stat_schema.add_field('sim', label='Sim', width=2)ranked_stat_schema.add_field('ranked_stat', label='Ranked Stat Name')ranked_stat_schema.add_field('rank', label='Rank', width=2)ranked_stat_schema.add_field('points_to_next_rank', label='Points Till Next Rank', width=2)ranked_stat_schema.add_field('decaying', label='Decaying', width=2)ranked_stat_schema.add_field('decay_rate', label='Decay Rate')
@GsiHandler('ranked_stat', ranked_stat_schema)
def generate_ranked_stat_data(*args, zone_id:int=None, filter=None, **kwargs):
    fame_data = []
    for sim_info in services.sim_info_manager().get_all():
        commodity_tracker = sim_info.commodity_tracker
        if commodity_tracker is None:
            pass
        else:
            for commodity in commodity_tracker:
                if issubclass(type(commodity), RankedStatistic):
                    points_to_rank = commodity.points_to_rank(commodity.rank_level + 1) - commodity.get_value()
                    entry = {'sim': str(sim_info), 'ranked_stat': str(type(commodity)), 'rank': str(commodity.rank_level), 'points_to_next_rank': str(points_to_rank), 'decaying': str(commodity.decay_enabled), 'decay_rate': str(commodity.get_decay_rate())}
                    fame_data.append(entry)
    return fame_data
sim_ranked_statistics_schema = GsiGridSchema(label='Statistics/Ranked Stat', sim_specific=True)sim_ranked_statistics_schema.add_field('sim_id', label='Sim ID', hidden=True)sim_ranked_statistics_schema.add_field('skill_guid', label='Skill ID', hidden=True, unique_field=True)sim_ranked_statistics_schema.add_field('skill_name', label='Name')sim_ranked_statistics_schema.add_field('skill_value', label='Value Points', type=GsiFieldVisualizers.FLOAT)sim_ranked_statistics_schema.add_field('event_level', label='Level', type=GsiFieldVisualizers.INT)sim_ranked_statistics_schema.add_field('rank_level', label='Rank', type=GsiFieldVisualizers.INT)sim_ranked_statistics_schema.add_field('next_level', label='Points till Next Level', type=GsiFieldVisualizers.INT)sim_ranked_statistics_schema.add_field('next_rank', label='Points till Next Rank', type=GsiFieldVisualizers.INT)sim_ranked_statistics_schema.add_field('time_till_decay_starts', label='Time Till Decay Starts')
def _get_sim_info_by_id(sim_id):
    sim_info_manager = services.sim_info_manager()
    sim_info = None
    if sim_info_manager is not None:
        sim_info = sim_info_manager.get(sim_id)
    return sim_info

@GsiHandler('ranked_stat_view', sim_ranked_statistics_schema)
def generate_sim_ranked_stat_view_data(sim_id:int=None):
    skill_data = []
    cur_sim_info = _get_sim_info_by_id(sim_id)
    if cur_sim_info.static_commodity_tracker is not None:
        for statistic in list(cur_sim_info.commodity_tracker):
            if not issubclass(type(statistic), RankedStatistic):
                pass
            else:
                levels = statistic.get_level_list()
                event_level = statistic.get_user_value()
                value = statistic.get_value()
                next_level = sum(levels[i] for i in range(min(len(levels), event_level + 1)))
                next_rank_level = statistic.get_next_rank_level()
                next_rank = sum(levels[i] for i in range(next_rank_level))
                time_till_decay_starts = statistic.get_time_till_decay_starts()
                entry = {'simId': str(sim_id), 'skill_guid': str(statistic.guid64), 'skill_name': type(statistic).__name__, 'skill_value': statistic.get_value(), 'event_level': event_level, 'rank_level': statistic.rank_level, 'next_level': next_level - value, 'next_rank': next_rank - value, 'time_till_decay_starts': str(time_till_decay_starts)}
                skill_data.append(entry)
    return skill_data
