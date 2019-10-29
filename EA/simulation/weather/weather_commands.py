from server_commands.argument_helpers import TunableInstanceParam, OptionalTargetParam, get_optional_targetfrom sims4.common import Packfrom weather.lightning import LightningStrikefrom weather.weather_enums import PrecipitationType, WeatherOption, WeatherTypeimport servicesimport sims4.commands
@sims4.commands.Command('weather.set_weather_option', pack=Pack.EP05, command_type=sims4.commands.CommandType.Live)
def set_weather_option(precipitation_type:PrecipitationType, weather_option:WeatherOption, _connection=None):
    services.weather_service().set_weather_option(precipitation_type, weather_option)
    return True

@sims4.commands.Command('weather.set_temperature_effects_enabled', pack=Pack.EP05, command_type=sims4.commands.CommandType.Live)
def set_temperature_effects_enabled(enabled:bool=True, _connection=None):
    services.weather_service().set_temperature_effects_enabled(enabled)
    return True

@sims4.commands.Command('weather.start_weather_event', pack=Pack.EP05, command_type=sims4.commands.CommandType.Automation)
def start_weather_event(weather_event:TunableInstanceParam(sims4.resources.Types.WEATHER_EVENT), hours:float=None, _connection=None):
    services.weather_service().start_weather_event(weather_event, hours)
    return True

@sims4.commands.Command('weather.request_forecast', pack=Pack.EP05, command_type=sims4.commands.CommandType.Live)
def request_weather_forecast(num_days:int=1, _connection=None):
    services.weather_service().populate_forecasts(num_days)
    return True

@sims4.commands.Command('weather.is_any_rain', pack=Pack.EP05, command_type=sims4.commands.CommandType.Automation)
def is_any_rain(_connection=None):
    if services.weather_service().has_weather_type(WeatherType.AnyRain):
        sims4.commands.output('True, it is raining', _connection)
        sims4.commands.automation_output('IsAnyRain; Status:True', _connection)
        return True
    sims4.commands.output('False, it is not raining', _connection)
    sims4.commands.automation_output('IsAnyRain; Status:False', _connection)
    return False

@sims4.commands.Command('weather.lightning_strike_here', pack=Pack.EP05, command_type=sims4.commands.CommandType.Cheat)
def lighning_strike_here(x:float=0.0, y:float=0.0, z:float=0.0, _connection=None):
    sims4.commands.output('You beckon Zeus to strike the ground.', _connection)
    if sims4.math.vector3_almost_equal(sims4.math.Vector3(x, y, z), sims4.math.Vector3.ZERO()):
        sims4.commands.output('You can enter x y z coordinates to hit a specific location on the terrain.', _connection)
        LightningStrike.strike_terrain()
    else:
        position = sims4.math.Vector3(x, y, z)
        LightningStrike.strike_terrain(position)
    return True

@sims4.commands.Command('weather.lightning_strike_object', pack=Pack.EP05, command_type=sims4.commands.CommandType.Cheat)
def lightning_strike_object(opt_target:OptionalTargetParam=None, _connection=None):
    sims4.commands.output('You beckon Zeus to smite something.', _connection)
    obj = get_optional_target(opt_target, _connection) if opt_target is not None else None
    if obj is not None and obj.is_sim:
        LightningStrike.strike_sim(sim_to_strike=obj)
    else:
        LightningStrike.strike_object(obj_to_strike=obj)
    return True

@sims4.commands.Command('weather.summon_lightning_strike', pack=Pack.EP05, command_type=sims4.commands.CommandType.Cheat)
def summon_lightning_strike(_connection=None):
    sims4.commands.output('You beckon Zeus to smite something.', _connection)
    LightningStrike.perform_active_lightning_strike()
    return True
