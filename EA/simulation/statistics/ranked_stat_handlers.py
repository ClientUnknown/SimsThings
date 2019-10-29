from gsi_handlers.gsi_utils import parse_filter_to_list
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
