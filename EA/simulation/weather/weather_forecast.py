import operatorfrom interactions.utils.tunable_icon import TunableIconfrom seasons.seasons_enums import SeasonSegmentfrom sims4 import randomfrom sims4.localization import TunableLocalizedStringfrom sims4.resources import Typesfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, OptionalTunable, TunableTuple, TunableMapping, TunableEnumEntry, TunableInterval, Tunable, TunableListfrom sims4.tuning.tunable_base import ExportModes, GroupNamesfrom snippets import define_snippetfrom weather.weather_enums import PrecipitationType, WeatherOption, WeatherType, WeatherTypeGroupfrom weather.weather_event import WeatherEventimport services
class WeatherForecast(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(Types.WEATHER_FORECAST)):
    INSTANCE_TUNABLES = {'calendar_icon': TunableIcon(description='\n            The small icon for this forecast.\n            ', export_modes=ExportModes.All), 'calendar_icon_large': TunableIcon(description='\n            The large icon for this forecast.\n            ', export_modes=ExportModes.All), 'calendar_icon_mascot': TunableIcon(description='\n            Optional icon to use as the forecast mascot in the calendar.\n            ', allow_none=True, export_modes=ExportModes.All), 'forecast_description': TunableLocalizedString(description='\n            The description for this forecast.\n            ', export_modes=ExportModes.All), 'forecast_name': TunableLocalizedString(description='\n            The name for this forecast.\n            ', export_modes=ExportModes.All), 'prescribed_weather_type': OptionalTunable(description='\n            The types of prescribed weather this forecast counts as\n            ', tunable=TunableTuple(rain=Tunable(description='\n                    If checked this forecast will be unavailable if rain is disabled\n                    ', tunable_type=bool, default=False), storm=Tunable(description='\n                    If checked this forecast will be unavailable if storm is disabled\n                    ', tunable_type=bool, default=False), snow=Tunable(description='\n                    If checked this forecast will be unavailable if snow is disabled\n                    ', tunable_type=bool, default=False), blizzard=Tunable(description='\n                    If checked this forecast will be unavailable if blizzard is disabled\n                    ', tunable_type=bool, default=False))), 'weather_event_time_blocks': TunableMapping(description='\n            The weather events that make up this forecast.  Key is hour of day\n            that event would start, value is a list of potential events\n            ', key_type=Tunable(tunable_type=int, default=0), value_type=TunableList(description='\n                List of the weather events that can occur in this time block\n                ', tunable=TunableTuple(description='\n                    A tuple of information for the weather event.\n                    ', weather_event=WeatherEvent.TunableReference(description='\n                        The weather event.\n                        ', pack_safe=True), duration=TunableInterval(description='\n                        Minimum and maximum time, in sim hours, this event can last.\n                        ', tunable_type=float, default_lower=1, default_upper=4), weight=Tunable(description='\n                        Weight of this event being selected.\n                        ', tunable_type=int, default=1)))), 'weather_ui_override': TunableMapping(description='\n            If set, this overrides the weather type that is shown for the\n            specified group.\n            ', key_type=TunableEnumEntry(tunable_type=WeatherTypeGroup, default=WeatherTypeGroup.UNGROUPED, invalid_enums=(WeatherTypeGroup.UNGROUPED,)), value_type=TunableEnumEntry(tunable_type=WeatherType, default=WeatherType.UNDEFINED, invalid_enums=(WeatherType.UNDEFINED,)), tuning_group=GroupNames.SPECIAL_CASES)}

    @classmethod
    def get_weather_event(cls):
        weather_schedule = []
        for (beginning_hour, event_list) in cls.weather_event_time_blocks.items():
            weather_schedule.append((beginning_hour, event_list))
        weather_schedule.sort(key=operator.itemgetter(0))
        time_of_day = services.time_service().sim_now
        hour_of_day = time_of_day.hour()
        entry = weather_schedule[-1]
        weather_events = entry[1]
        for entry in weather_schedule:
            if entry[0] <= hour_of_day:
                weather_events = entry[1]
            else:
                break
        weighted_events = [(weather_event.weight, weather_event) for weather_event in weather_events]
        chosen_weather_event = random.weighted_random_item(weighted_events)
        return (chosen_weather_event.weather_event, chosen_weather_event.duration.random_float())

    @classmethod
    def is_snowy(cls):
        if cls.prescribed_weather_type is None:
            return False
        return cls.prescribed_weather_type.snow or cls.prescribed_weather_type.blizzard

    @classmethod
    def is_rainy(cls):
        if cls.prescribed_weather_type is None:
            return False
        return cls.prescribed_weather_type.rain or cls.prescribed_weather_type.storm

    @classmethod
    def is_forecast_supported(cls, options, snow_safe, rain_safe):
        prescribed_weather_type = cls.prescribed_weather_type
        if prescribed_weather_type is None:
            return True
        if prescribed_weather_type.rain and rain_safe and options[PrecipitationType.RAIN] == WeatherOption.WEATHER_DISABLED:
            return False
        if prescribed_weather_type.snow and snow_safe and options[PrecipitationType.SNOW] == WeatherOption.WEATHER_DISABLED:
            return False
        if prescribed_weather_type.storm and rain_safe and options[PrecipitationType.RAIN] == WeatherOption.DISABLE_STORMS:
            return False
        elif prescribed_weather_type.blizzard and snow_safe and options[PrecipitationType.SNOW] == WeatherOption.DISABLE_STORMS:
            return False
        return True
(TunableWeatherForecastListReference, TunableWeatherForecastListSnippet) = define_snippet('weather_forcast_list', TunableList(tunable=TunableTuple(description='\n            A tuple of forecast and weight.\n            ', forecast=WeatherForecast.TunableReference(description='\n                The weather forecast.\n                ', pack_safe=True), weight=Tunable(description='\n                Weight of this forecast being selected.\n                ', tunable_type=int, default=1))))(TunableWeatherSeasonalForecastsReference, TunableWeatherSeasonalForecastsSnippet) = define_snippet('weather_seasonal_forecasts', TunableMapping(key_type=TunableEnumEntry(description='\n            The part of the season.\n            ', tunable_type=SeasonSegment, default=SeasonSegment.MID), value_type=TunableWeatherForecastListReference(description='\n            Potential forecasts for this part of the season.\n            ', pack_safe=True)))