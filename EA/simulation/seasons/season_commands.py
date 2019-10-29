from seasons.season_ops import SeasonInterpolationOpfrom seasons.seasons_enums import SeasonType, SeasonLength, SeasonSetSourcefrom sims4.common import Packimport servicesimport sims4.commands
@sims4.commands.Command('seasons.set_season', pack=Pack.EP05, command_type=sims4.commands.CommandType.Cheat)
def set_season(season:SeasonType, interp_time:int=None, _connection=None):
    services.season_service().reset_region_season_params()
    services.season_service().set_season(season, SeasonSetSource.CHEAT, interp_time)
    if interp_time is None:
        services.weather_service().reset_forecasts()
    return True

@sims4.commands.Command('seasons.advance_season', pack=Pack.EP05, command_type=sims4.commands.CommandType.Cheat)
def advance_season(_connection=None):
    services.season_service().reset_region_season_params()
    services.season_service().advance_season(SeasonSetSource.CHEAT)
    services.weather_service().reset_forecasts()
    return True

@sims4.commands.Command('seasons.set_season_length', pack=Pack.EP05, command_type=sims4.commands.CommandType.Live)
def set_season_length(length:SeasonLength, _connection=None):
    services.season_service().reset_region_season_params()
    services.season_service().set_season_length(length)
    services.weather_service().reset_forecasts()
    services.season_service().handle_season_content_updated()
    return True

@sims4.commands.Command('seasons.shift_season_by_weeks', pack=Pack.EP05, command_type=sims4.commands.CommandType.Automation)
def shift_season_by_weeks(weeks:int, _connection=None):
    services.season_service().reset_region_season_params()
    services.season_service().shift_season_by_weeks(weeks)
    services.weather_service().reset_forecasts()
    services.season_service().handle_season_content_updated()
    return True

@sims4.commands.Command('seasons.get_season_info', pack=Pack.EP05)
def get_season_info(_connection=None):
    content = services.season_service().season_content
    sims4.commands.output('Season: {}'.format(services.season_service().season), _connection)
    sims4.commands.output('GameClock Progress: {}'.format(content.get_progress(services.game_clock_service().now())), _connection)
    sims4.commands.output('Simulation Progress: {}'.format(content.get_progress(services.time_service().sim_now)), _connection)
    sims4.commands.output(content.info, _connection)
    return True

@sims4.commands.Command('seasons.generate_season_interpolation_ops', pack=Pack.EP05)
def generate_season_interpolation_ops(num_seasons:int=1, _connection=None):
    season_service = services.season_service()
    for (season, content) in season_service.get_seasons(num_seasons):
        sims4.commands.output('Season: {}'.format(season), _connection)
        sims4.commands.output('Time: {} -> {}'.format(repr(content.start_time), repr(content.end_time)), _connection)
        op = SeasonInterpolationOp(season, content, mid_season_op=False)
        sims4.commands.output('\nBegin {}@{}:\n{}'.format(season.name, repr(content.start_time), op.content), _connection)
        op = SeasonInterpolationOp(season, content, mid_season_op=True)
        sims4.commands.output('\nMid-{}@{}:\n{}'.format(season.name, repr(content.midpoint_time), op.content), _connection)

@sims4.commands.Command('seasons.get_timeline_element_info', pack=Pack.EP05)
def get_season_timeline_element_infos(_connection=None):
    season_service = services.season_service()
    for timeline_element_info in season_service.get_timeline_element_infos():
        sims4.commands.output('Element: {}'.format(timeline_element_info), _connection)
