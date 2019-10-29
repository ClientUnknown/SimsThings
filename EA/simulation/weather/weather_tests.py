from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import cached_testfrom weather.weather_forecast import TunableWeatherSeasonalForecastsReferencefrom weather.weather_enums import WeatherType, PrecipitationType, Temperature, GroundCoverType, CloudType, WeatherEffectTypefrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableEnumSet, OptionalTunable, TunableTuple, Tunable, TunableEnumEntry, TunableInterval, Tunable100ConvertRangefrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport services
class WeatherTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):

    class TunableWeatherTestTuple(TunableTuple):

        def __init__(self, minimum_range=0, **kwargs):
            super().__init__(range=TunableInterval(description='\n                    Range to return true.\n                    ', tunable_type=Tunable100ConvertRange, minimum=minimum_range, maximum=100, default_lower=0, default_upper=100), zero_is_true=Tunable(description='\n                    If checked, will return True if amount is 0.\n                    If unchecked, will return False if amount is 0.\n                    \n                    Even if inside (or outside) specified range.\n                    ', tunable_type=bool, default=False), **kwargs)

    FACTORY_TUNABLES = {'temperature': OptionalTunable(TunableTuple(temperature=TunableEnumSet(description='\n                    The temperature(s) we must be in to pass the test\n                    ', minlength=1, enum_type=Temperature), invert=Tunable(description='\n                    If checked must NOT be one of the specified temperatures\n                    ', tunable_type=bool, default=False))), 'precipitation': OptionalTunable(TunableWeatherTestTuple(description='\n                Specify amount and type of precipitation\n                ', precipitation_type=TunableEnumEntry(description='\n                    The type of precipitation we are testing\n                    ', tunable_type=PrecipitationType, default=PrecipitationType.RAIN))), 'lightning': OptionalTunable(Tunable(description='\n                If checked must be lightning.\n                If unchecked must not be.\n                ', tunable_type=bool, default=True)), 'thunder': OptionalTunable(Tunable(description='\n                If checked must be thundering.\n                If unchecked must not be.\n                ', tunable_type=bool, default=True)), 'water_freeze': OptionalTunable(TunableWeatherTestTuple(description='\n                Specify amount water (ponds, etc.) is frozen\n                ')), 'wind': OptionalTunable(TunableWeatherTestTuple(description='\n                Specify amount of wind.\n                ')), 'cloud_state': OptionalTunable(TunableTuple(whitelist=TunableEnumSet(description='\n                    If any are specified, the value of one must be > the\n                    whitelist threshold for the test to pass.\n                    \n                    If weather_service is not running, test will pass if\n                    partly_cloudy is in white list (or whitelist is empty) but \n                    not black list.\n                    ', enum_type=CloudType), whitelist_threshold=Tunable100ConvertRange(description='\n                    The value of a whitelist cloudtype must be above this \n                    threshold to pass.\n                    ', default=0, minimum=0, maximum=100), blacklist=TunableEnumSet(description='\n                    If any are specified, the value of all must be <= the\n                    blacklist threshold for the test to pass.\n                    \n                    If weather_service is not running, test will pass if\n                    partly_cloudy is in white list (or whitelist is empty) but \n                    not black list.\n                    ', enum_type=CloudType), blacklist_threshold=Tunable100ConvertRange(description='\n                    The maximum value for each of the blacklist cloud types for \n                    the test to pass.\n                    ', default=0, minimum=0, maximum=100))), 'ground_cover': OptionalTunable(TunableWeatherTestTuple(description='\n                Specify amount and type of ground cover\n                ', minimum_range=-100, cover_type=TunableEnumEntry(description='\n                    The type of precipitation we are testing\n                    ', tunable_type=GroundCoverType, default=GroundCoverType.RAIN_ACCUMULATION)))}

    def get_expected_args(self):
        return {}

    def _get_processed_weather_element_value(self, element_type, service, time):
        if service is not None:
            return service.get_weather_element_value(element_type, time=time)
        return 0

    @cached_test
    def __call__(self):
        weather_service = services.weather_service()
        time = services.time_service().sim_now
        if self.temperature is not None:
            if weather_service is not None:
                current_temp = Temperature(weather_service.get_weather_element_value(WeatherEffectType.TEMPERATURE, time=time, default=Temperature.WARM))
            else:
                current_temp = Temperature.WARM
            if self.temperature.invert:
                if current_temp in self.temperature.temperature:
                    return TestResult(False, 'Temperature ({}) is an invalid temperature', current_temp, tooltip=self.tooltip)
            elif current_temp not in self.temperature.temperature:
                return TestResult(False, 'Temperature ({}) is not a valid temperature', current_temp, tooltip=self.tooltip)
        if self.cloud_state is not None:
            if weather_service is None:
                if self.cloud_state.whitelist and CloudType.PARTLY_CLOUDY not in self.cloud_state.whitelist:
                    return TestResult(False, "Whitelist specified and CloudType.PARTLY_CLOUDY isn't in it", tooltip=self.tooltip)
                if CloudType.PARTLY_CLOUDY in self.cloud_state.blacklist:
                    return TestResult(False, 'Current cloud type CloudType.PARTLY_CLOUDY is in blacklist', tooltip=self.tooltip)
            else:
                if self.cloud_state.whitelist:
                    threshold = self.cloud_state.whitelist_threshold
                    for cloud_type in self.cloud_state.whitelist:
                        if weather_service.get_weather_element_value(cloud_type, time=time) > threshold:
                            break
                    return TestResult(False, 'Whitelist specified and no specified cloud type is above the threshold', tooltip=self.tooltip)
                threshold = self.cloud_state.blacklist_threshold
                for cloud_type in self.cloud_state.blacklist:
                    if weather_service.get_weather_element_value(cloud_type, time=time) > threshold:
                        return TestResult(False, 'Cloud type {} is in the blacklist and above the threshold', cloud_type, tooltip=self.tooltip)
        if self.precipitation is not None:
            precip = self._get_processed_weather_element_value(self.precipitation.precipitation_type, weather_service, time)
            if precip == 0:
                if not self.precipitation.zero_is_true:
                    return TestResult(False, 'Must not be 0 precipitation', tooltip=self.tooltip)
            elif precip not in self.precipitation.range:
                return TestResult(False, 'Precipitation outside acceptable range, currently: {}', precip, tooltip=self.tooltip)
        if self.lightning is not None:
            lightning = self._get_processed_weather_element_value(WeatherEffectType.LIGHTNING, weather_service, time)
            if lightning == 0:
                if self.lightning:
                    return TestResult(False, 'Must not be 0 lightning', tooltip=self.tooltip)
            elif not self.lightning:
                return TestResult(False, 'Must be 0 lightning', tooltip=self.tooltip)
        if self.thunder is not None:
            thunder = self._get_processed_weather_element_value(WeatherEffectType.THUNDER, weather_service, time)
            if thunder == 0:
                if self.thunder:
                    return TestResult(False, 'Must not be 0 thundering', tooltip=self.tooltip)
            elif not self.thunder:
                return TestResult(False, 'Must be 0 thundering', tooltip=self.tooltip)
        if self.water_freeze is not None:
            freeze = self._get_processed_weather_element_value(WeatherEffectType.WATER_FROZEN, weather_service, time)
            if freeze == 0:
                if not self.water_freeze.zero_is_true:
                    return TestResult(False, 'Must not be 0 water freeze', tooltip=self.tooltip)
            elif freeze not in self.water_freeze.range:
                return TestResult(False, 'Water Freeze outside acceptable range, currently: {}', freeze, tooltip=self.tooltip)
        if self.wind is not None:
            wind = self._get_processed_weather_element_value(WeatherEffectType.WIND, weather_service, time)
            if wind == 0:
                if not self.wind.zero_is_true:
                    return TestResult(False, 'Must not be 0 wind', tooltip=self.tooltip)
            elif wind not in self.wind.range:
                return TestResult(False, 'Wind outside acceptable range, currently: {}', wind, tooltip=self.tooltip)
        if self.ground_cover is not None:
            cover = self._get_processed_weather_element_value(self.ground_cover.cover_type, weather_service, time)
            if cover == 0:
                if not self.ground_cover.zero_is_true:
                    return TestResult(False, 'Must not be 0 ground cover', tooltip=self.tooltip)
            elif cover not in self.ground_cover.range:
                return TestResult(False, 'Ground cover outside acceptable range, currently: {}', cover, tooltip=self.tooltip)
        return TestResult.TRUE

class WeatherTypeTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'weather_types': TunableEnumSet(description="\n            The weather types we are testing.  Passes test if any current\n            weather type matches any tuned here.\n            \n            If seasons pack is not installed, weather type will be UNDEFINED.\n            So with EP5 not installed:\n            Test will always pass if UNDEFINED is in the set if not inverted,\n            and fail if it isn't in the set.\n            Test will always fail if UNDEFINED is in the set if inverted,\n            and pass if it isn't in the set.\n            \n            i.e. to test out swimming in freezing weather only and always allow\n            it with seasons uninstalled, set would only have WeatherType.Freezing\n            and be inverted.\n            \n            To allow playing in puddles in hot weather or if weather pack isn't\n            installed, set would have both WeatherType.Hot and UNDEFINED, and not\n            be inverted .\n            ", minlength=1, enum_default=WeatherType.UNDEFINED, enum_type=WeatherType), 'invert': Tunable(description='\n            If checked must NOT be the specified weather type.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {}

    @cached_test
    def __call__(self):
        weather_service = services.weather_service()
        if weather_service is None:
            if WeatherType.UNDEFINED in self.weather_types:
                if self.invert:
                    return TestResult(False, 'No WeatherService: UNDEFINED WeatherType {} is prohibited', tooltip=self.tooltip)
                    if not self.invert:
                        return TestResult(False, "No WeatherService: WeatherType must be UNDEFINED and isn't", tooltip=self.tooltip)
            elif not self.invert:
                return TestResult(False, "No WeatherService: WeatherType must be UNDEFINED and isn't", tooltip=self.tooltip)
        elif weather_service.has_any_weather_type(self.weather_types):
            if self.invert:
                return TestResult(False, 'Prohibited weather type found', tooltip=self.tooltip)
        elif not self.invert:
            return TestResult(False, 'Required weather type not found.', tooltip=self.tooltip)
        return TestResult.TRUE

class WeatherForecastOverrideTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'weather_forecasts': TunableWhiteBlackList(description='\n            Black/White lists of the forecasts to test against\n            ', tunable=TunableWeatherSeasonalForecastsReference())}

    def get_expected_args(self):
        return {}

    @cached_test
    def __call__(self):
        weather_service = services.weather_service()
        if weather_service is not None:
            override_forecast = weather_service.get_override_forecast()
        else:
            override_forecast = None
        if not self.weather_forecasts.test_item(override_forecast):
            return TestResult(False, "Current override forecast {} doesn't pass white/black list", override_forecast, tooltip=self.tooltip)
        return TestResult.TRUE
