from interactions.utils.loot_basic_op import BaseLootOperationfrom seasons.seasons_enums import SeasonType, SeasonSetSourcefrom sims4.tuning.tunable import TunableInterval, OptionalTunable, TunableEnumEntry, TunableSimMinutefrom weather.weather_event import WeatherEventfrom weather.weather_forecast import TunableWeatherSeasonalForecastsReferenceimport services
class WeatherStartEventLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'weather_event': WeatherEvent.TunableReference(description='\n            The weather event to start.\n            '), 'duration': TunableInterval(description='\n            How long the event should last, in hours.\n            ', tunable_type=float, minimum=1.0, default_lower=1.0, default_upper=2.0)}

    def __init__(self, *args, weather_event, duration, **kwargs):
        super().__init__(*args, **kwargs)
        self.weather_event = weather_event
        self.duration = duration

    def _apply_to_subject_and_target(self, subject, target, resolver):
        weather_service = services.weather_service()
        if weather_service is not None:
            weather_service.start_weather_event(self.weather_event, self.duration.random_float())

class WeatherSetOverrideForecastLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'weather_forecast': OptionalTunable(description='\n            The forecast to use as override.\n            ', tunable=TunableWeatherSeasonalForecastsReference(), disabled_name='reset_to_default')}

    def __init__(self, *args, weather_forecast, **kwargs):
        super().__init__(*args, **kwargs)
        self.weather_forecast = weather_forecast

    def _apply_to_subject_and_target(self, subject, target, resolver):
        weather_service = services.weather_service()
        if weather_service is not None:
            weather_service.set_override_forecast(self.weather_forecast)

class WeatherSetSeasonLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'season': TunableEnumEntry(description='\n            The target season.\n            ', tunable_type=SeasonType, default=SeasonType.WINTER), 'interpolation_time': TunableSimMinute(description='\n            The time over which the interpolation to the new season should\n            occur.\n            ', default=20)}

    def __init__(self, *args, season, interpolation_time, **kwargs):
        super().__init__(*args, **kwargs)
        self.season = season
        self.interpolation_time = interpolation_time

    def _apply_to_subject_and_target(self, subject, target, resolver):
        season_service = services.season_service()
        if season_service is not None:
            season_service.reset_region_season_params()
            season_service.set_season(self.season, SeasonSetSource.LOOT, interp_time=self.interpolation_time)
