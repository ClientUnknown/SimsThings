from date_and_time import create_time_span, DATE_AND_TIME_ZEROfrom sims4.resources import Typesfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, OptionalTunable, TunableTuple, TunableEnumEntry, TunableInterval, TunableSimMinute, TunableRange, Tunable100ConvertRange, TunableMappingfrom weather.weather_enums import PrecipitationType, Temperature, CloudType, WeatherElementTuple, WeatherEffectTypeimport servicesimport sims4.loglogger = sims4.log.Logger('weather', default_owner='nabaker')
class WeatherEvent(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(Types.WEATHER_EVENT)):

    class TunableWeatherElementTuple(TunableTuple):

        def __init__(self, default_lower=40, default_upper=60, **kwargs):
            super().__init__(start_delay=TunableSimMinute(description='\n                    Delay in sim minutes before change starts.  Used if new weather is more\n                    severe than existing weather.\n                    ', default=1, minimum=0), start_rate=Tunable100ConvertRange(description='\n                    Rate at which ramp up occurs.  Used if new weather is more\n                    severe than existing weather.\n                    ', default=3.3, minimum=0), end_delay=TunableSimMinute(description='\n                    Delay in sim minutes before element ends.  Used if existing weather is more\n                    severe than new weather.\n                    ', default=1, minimum=0), end_rate=Tunable100ConvertRange(description='\n                    Rate at which ramp doown occurs.  Used if existing weather is more\n                    severe than new weather.\n                    ', default=3.3, minimum=0), range=TunableInterval(description='\n                    Range.\n                    ', tunable_type=Tunable100ConvertRange, minimum=0, maximum=100, default_lower=default_lower, default_upper=default_upper), **kwargs)

    INSTANCE_TUNABLES = {'precipitation': OptionalTunable(description='\n            The amount/type of precipitation for this weather event.\n            ', tunable=TunableWeatherElementTuple(precipitation_type=TunableEnumEntry(description='\n                    The type of precipitation.\n                    ', tunable_type=PrecipitationType, default=PrecipitationType.RAIN))), 'cloud_states': TunableMapping(description='\n            The types of clouds for this weather event.\n            ', key_type=TunableEnumEntry(description='\n                The type of clouds.\n                ', tunable_type=CloudType, default=CloudType.PARTLY_CLOUDY, invalid_enums=(CloudType.STRANGE, CloudType.VERY_STRANGE)), value_type=TunableWeatherElementTuple(default_lower=100, default_upper=100), minlength=1), 'wind': OptionalTunable(description='\n            The amount of wind for this weather event.\n            ', tunable=TunableWeatherElementTuple()), 'temperature': TunableEnumEntry(description='\n            The temperature.\n            ', tunable_type=Temperature, default=Temperature.WARM), 'thunder': OptionalTunable(description='\n            The amount of thunder for this weather event.\n            ', tunable=TunableWeatherElementTuple()), 'lightning': OptionalTunable(description='\n            The amount of lightning for this weather event.\n            ', tunable=TunableWeatherElementTuple())}
    FALLBACK_TRANSITION_TIME = 30

    @classmethod
    def get_transition_data(cls, previous_event, old_transition_data, duration):
        transition_data = {}
        now = services.time_service().sim_now
        if previous_event is None:
            key = int(WeatherEffectType.TEMPERATURE)
            transition_data[key] = WeatherElementTuple(cls.temperature, now, cls.temperature, now)
            if cls.precipitation is not None:
                key = int(cls.precipitation.precipitation_type)
                value = cls.precipitation.range.random_float()
                transition_data[key] = WeatherElementTuple(value, now, value, now)
            for (key, value) in cls.cloud_states.items():
                tuple_key = int(key)
                tuple_value = value.range.random_float()
                transition_data[tuple_key] = WeatherElementTuple(tuple_value, now, tuple_value, now)
            if cls.wind is not None:
                key = int(WeatherEffectType.WIND)
                value = cls.wind.range.random_float()
                transition_data[key] = WeatherElementTuple(value, now, value, now)
            if cls.thunder is not None:
                key = int(WeatherEffectType.THUNDER)
                value = cls.thunder.range.random_float()
                transition_data[key] = WeatherElementTuple(value, now, value, now)
            if cls.lightning is not None:
                key = int(WeatherEffectType.LIGHTNING)
                value = cls.lightning.range.random_float()
                transition_data[key] = WeatherElementTuple(value, now, value, now)
        else:
            key = int(WeatherEffectType.TEMPERATURE)
            transition_data[key] = WeatherElementTuple(cls.temperature, now, cls.temperature, now)
            clouds_use_new_delay = None
            key = int(WeatherEffectType.WIND)
            clouds_use_new_delay = cls._create_weather_transition_element(now, transition_data, old_transition_data, key, cls.wind, previous_event.wind, clouds_use_new_delay)
            key = int(WeatherEffectType.THUNDER)
            clouds_use_new_delay = cls._create_weather_transition_element(now, transition_data, old_transition_data, key, cls.thunder, previous_event.thunder, clouds_use_new_delay)
            key = int(WeatherEffectType.LIGHTNING)
            clouds_use_new_delay = cls._create_weather_transition_element(now, transition_data, old_transition_data, key, cls.lightning, previous_event.lightning, clouds_use_new_delay)
            for precip_type in PrecipitationType:
                event_element = cls.precipitation
                previous_event_element = previous_event.precipitation
                key = int(precip_type)
                if event_element.precipitation_type != key:
                    event_element = None
                if previous_event_element.precipitation_type != key:
                    previous_event_element = None
                clouds_use_new_delay = cls._create_weather_transition_element(now, transition_data, old_transition_data, key, event_element, previous_event_element, clouds_use_new_delay)
            old_cloud_set = set(previous_event.cloud_states.keys())
            new_cloud_set = set(cls.cloud_states.keys())
            followup_cloud_set = old_cloud_set - new_cloud_set
            longest_end_time = now
            for (key, data) in cls.cloud_states.items():
                new_cloud_type = int(key)
                if clouds_use_new_delay or key not in old_cloud_set:
                    start_time = now + create_time_span(minutes=data.start_delay)
                    rate = data.start_rate
                else:
                    old_data = previous_event.cloud_states[key]
                    start_time = now + create_time_span(minutes=old_data.end_delay)
                    rate = old_data.end_rate
                start_value = services.weather_service().get_weather_element_value(new_cloud_type, now)
                end_value = data.range.random_float()
                transition_duration = abs(end_value - start_value)/rate
                if followup_cloud_set:
                    transition_duration = transition_duration/2
                end_time = start_time + create_time_span(minutes=transition_duration)
                if end_time > longest_end_time:
                    longest_end_time = end_time
                transition_data[new_cloud_type] = WeatherElementTuple(start_value, start_time, end_value, end_time)
            for cloudtype in followup_cloud_set:
                data = previous_event.cloud_states[cloudtype]
                old_cloud_type = int(cloudtype)
                start_value = services.weather_service().get_weather_element_value(old_cloud_type, now)
                transition_duration = (start_value - 0)/data.end_rate/2
                end_time = longest_end_time + create_time_span(minutes=transition_duration)
                transition_data[old_cloud_type] = WeatherElementTuple(start_value, longest_end_time, 0.0, end_time)
            for cloudtype in CloudType:
                old_data = old_transition_data.get(int(cloudtype))
                if old_data.end_value != 0.0:
                    logger.error("Obsolete cloud transition that doesn't end at 0")
                    start_value = services.weather_service().get_weather_element_value(cloudtype, now)
                    end_time = longest_end_time + create_time_span(minutes=cls.FALLBACK_TRANSITION_TIME)
                    transition_data[int(cloudtype)] = WeatherElementTuple(start_value, longest_end_time, 0.0, end_time)
                elif old_data.end_time >= now:
                    transition_data[int(cloudtype)] = old_data
        if duration is None:
            next_time = DATE_AND_TIME_ZERO
        else:
            last_time = now
            for data in transition_data.values():
                if last_time is None:
                    last_time = data.end_time
                elif data.end_time > last_time:
                    last_time = data.end_time
            next_time = last_time + create_time_span(hours=duration)
        return (transition_data, next_time)

    @classmethod
    def _create_weather_transition_element(cls, time, new_transition_data, old_transition_data, key, event_element, previous_event_element, using_new_delay):
        if event_element is None:
            value = 0.0
            start_time = time
            rate = 0
        else:
            value = event_element.range.random_float()
            start_time = time + create_time_span(minutes=event_element.start_delay)
            rate = event_element.start_rate
        start_value = services.weather_service().get_weather_element_value(key, time)
        if value == 0.0 and start_value == 0.0:
            return using_new_delay
        if rate != 0:
            using_new_delay = True
        old_data = old_transition_data.get(key, None)
        if old_data is not None and old_data.end_value > value:
            if previous_event_element is not None:
                using_new_delay = False
                start_time = time + create_time_span(minutes=previous_event_element.end_delay)
                rate = previous_event_element.end_rate
            else:
                logger.error('Weather transition element: old data end value greater than new value for key {}, but there is no old element\nOld data:{}\nOld event:{}\nNew Event:{}', key, old_data, services.weather_service()._current_event, cls)
        if rate == 0:
            if old_transition_data[key].end_value != 0.0:
                logger.error("Weather transition element unable to calculate rate, and final destination of existing transition isn't 0")
                end_time = time + create_time_span(minutes=cls.FALLBACK_TRANSITION_TIME)
                new_transition_data[key] = WeatherElementTuple(start_value, time, 0.0, end_time)
            else:
                new_transition_data[key] = old_transition_data[key]
            return using_new_delay
        transition_duration = abs(start_value - value)/rate
        end_time = start_time + create_time_span(minutes=transition_duration)
        new_transition_data[key] = WeatherElementTuple(start_value, start_time, value, end_time)
        return using_new_delay
