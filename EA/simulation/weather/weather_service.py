from _collections import defaultdictimport mathimport randomimport timefrom protocolbuffers import DistributorOps_pb2, WeatherSeasons_pb2from build_buy import is_location_natural_groundfrom date_and_time import create_time_span, DateAndTime, DATE_AND_TIME_ZERO, TimeSpanfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom event_testing.resolver import GlobalResolver, SingleSimResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom interactions.utils.tunable_icon import TunableIconAllPacksfrom objects.definition_manager import TunableDefinitionListfrom objects.puddles.puddle import Puddlefrom objects.system import create_objectfrom placement import FGLSearchFlagfrom seasons.seasons_enums import SeasonType, SeasonSegmentfrom sims.outfits.outfit_enums import WeatherOutfitCategory, OutfitChangeReasonfrom sims4.common import Packfrom sims4.localization import TunableLocalizedStringfrom sims4.resources import Typesfrom sims4.service_manager import Servicefrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import Tunable, TunableList, TunableInterval, TunableTuple, TunableMapping, TunableReference, TunableEnumEntry, TunablePercent, TunablePackSafeReference, TunableRealSecond, TunableEnumSet, AutoFactoryInit, TunableVariant, HasTunableSingletonFactory, TunableSimMinute, TunableSingletonFactory, Tunable100ConvertRangefrom sims4.tuning.tunable_base import ExportModesfrom sims4.utils import classpropertyfrom weather.lightning import LightningStrikefrom weather.rainbow import SpawnRainbowfrom weather.weather_enums import WeatherType, PrecipitationType, WeatherOption, Temperature, WeatherTypeGroup, WeatherElementTuple, GroundCoverType, WeatherEffectTypefrom weather.weather_forecast import WeatherForecastfrom weather.weather_ops import WeatherEventOp, WeatherUpdateOp, WeatherForecastOpfrom weather.weather_tests import WeatherTestfrom world import regionfrom world.terrain_enums import TerrainTagimport alarmsimport date_and_timeimport persistence_error_typesimport placementimport routingimport servicesimport sims4.logimport sims4.randomimport tagimport terrainlogger = sims4.log.Logger('weather', default_owner='nabaker')
class ExclusiveWeatherTypeLeaf(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'weather_type': TunableEnumEntry(description='\n            The weather type.\n            ', tunable_type=WeatherType, default=WeatherType.UNDEFINED, invalid_enums=tuple(WeatherType))}

    def get_weather_type(self, resolver):
        return self.weather_type

    def enums_gen(self):
        yield self.weather_type
TunableExclusiveWeatherTypeLeaf = TunableSingletonFactory.create_auto_factory(ExclusiveWeatherTypeLeaf)
class TunableExclusiveWeatherTypeVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, tested=TunablePackSafeReference(manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('ExclusiveWeatherTypeBranch',)), single_entry=TunableExclusiveWeatherTypeLeaf(), default='single_entry', **kwargs)

class ExclusiveWeatherTypeBranch(metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.SNIPPET)):
    INSTANCE_TUNABLES = {'test': TunableTestSet(description='\n            If at least one of these passes the result_true branch will be\n            used. Otherwise the false branch will be.\n            '), 'result_true': TunableExclusiveWeatherTypeVariant(description='\n            Result to use if test passes.\n            '), 'result_false': TunableExclusiveWeatherTypeVariant(description='\n            Result to use if test fails.\n            ')}

    @classmethod
    def get_weather_type(cls, resolver):
        if cls.test.run_tests(resolver):
            if cls.result_true is None:
                return WeatherType.UNDEFINED
            return cls.result_true.get_weather_type(resolver)
        if cls.result_false is None:
            return WeatherType.UNDEFINED
        return cls.result_false.get_weather_type(resolver)

    @classmethod
    def enums_gen(cls):
        if cls.result_true is not None:
            yield from cls.result_true.enums_gen()
        if cls.result_false is not None:
            yield from cls.result_false.enums_gen()
with sims4.reload.protected(globals()):
    WEATHER_TYPE_THRESHOLDS = defaultdict(set)
class WeatherService(Service):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        for enum in WeatherService.WEATHER_TYPE_UI_INFO:
            if enum in WeatherService.WEATHER_TYPE_MULTIPLE_TEST:
                logger.error('This key {} is in both WEATHER_TYPE_UI_INFO and WEATHER_TYPE_MULTIPLE_TEST.', enum)
        if WeatherService.WEATHER_TYPE_EXCLUSIVE_TEST is not None:
            for enum in WeatherService.WEATHER_TYPE_EXCLUSIVE_TEST.enums_gen():
                if enum not in WeatherService.WEATHER_TYPE_UI_INFO:
                    logger.error('leaf {} in WEATHER_TYPE_EXCLUSIVE_TEST is not in WEATHER_TYPE_UI_INFO', enum)

    @staticmethod
    def _verify_puddle_callback(instance_class, tunable_name, source, value):
        for definition in value:
            if not issubclass(definition.cls, Puddle):
                logger.error('definition {} in weather service puddle list is not a puddle', definition)

    @staticmethod
    def _verify_weather_test_callback(instance_class, tunable_name, source, value):
        outfit_change_reason_count = {}
        for outfit_change_tuple in value:
            for outfit_change_reason in outfit_change_tuple.outfit_change_reasons:
                if outfit_change_reason in outfit_change_reason_count:
                    outfit_change_reason_count[outfit_change_reason] += 1
                else:
                    outfit_change_reason_count[outfit_change_reason] = 1
        for (reason, count) in outfit_change_reason_count.items():
            if count > 1:
                logger.error('outfit change reason {} is tuned more than once in WEATHER_OUTFIT_TESTS', reason)

    @staticmethod
    def _populate_weather_type_thresholds(*args):
        for test_set_list in WeatherService.WEATHER_TYPE_MULTIPLE_TEST.values():
            for test_set in test_set_list:
                for test in test_set:
                    if isinstance(test, WeatherTest):
                        if test.ground_cover is None:
                            pass
                        else:
                            cover_type = test.ground_cover.cover_type
                            cover_range = test.ground_cover.range
                            for threshold in (cover_range.lower_bound, cover_range.upper_bound):
                                WEATHER_TYPE_THRESHOLDS[cover_type].add(threshold)

    class TunableWeatherAutonomyPenalties(TunableList):

        def __init__(self, description='Default', **kwargs):
            super().__init__(description=description, tunable=TunableTuple(description='\n                    A tuple of precipitation range to modifier.\n                    ', value_range=TunableInterval(description='\n                        Precipitation range within which this penalty is applied\n                        ', tunable_type=Tunable100ConvertRange, minimum=0, maximum=100, default_lower=0, default_upper=100), modifier=Tunable(description='\n                        Multiplier to autonomy score by.\n                        ', tunable_type=float, default=1.0)), **kwargs)

    class TunableWeatherAutonomyPenaltyReductions(TunableMapping):

        def __init__(self, description='Default', **kwargs):
            super().__init__(description=description, key_type=TunableReference(description='\n                    The trait the receives this modifier.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT), pack_safe=True), value_type=Tunable(description='\n                    Multiplier to modify penalty by.\n                    ', tunable_type=float, default=1.0), **kwargs)

    class TunableTemperatureTuple(TunableTuple):

        def __init__(self, description='Default', freezing=1.0, **kwargs):
            super().__init__(description=description, burning=Tunable100ConvertRange(default=10.0), hot=Tunable100ConvertRange(default=9.0), warm=Tunable100ConvertRange(default=5.0), cool=Tunable100ConvertRange(default=3.0), cold=Tunable100ConvertRange(default=1.0), freezing=Tunable100ConvertRange(default=freezing), **kwargs)

    OUTDOOR_AUTONOMY_RAIN_PENALTIES = TunableWeatherAutonomyPenalties(description="\n        A list of penalties modifiers for outside autonomy when it is raining.\n        score = score - score * modifier\n        \n        i.e. is sims score outside interactions at 10% of normal when it's\n        80-100 precipitation, then range would be 80-100, modifier would be 0.9\n        ")
    OUTDOOR_AUTONOMY_RAIN_PENALTY_REDUCTIONS = TunableWeatherAutonomyPenaltyReductions(description='\n        A mapping of traits to penalty modifiers for rain.\n        score = score - score * modifier * penalty reduction modifier\n        \n        i.e. if sim with the likes the outdoors trait is only half as affected\n        by the precipitation, key would be the likes the outdoors trait, value\n        would be 0.5\n        ')
    OUTDOOR_AUTONOMY_SNOW_PENALTIES = TunableWeatherAutonomyPenalties(description="\n        A list of penalties for outside autonomy when it is snowing.\n        score = score - score*modifier\n        \n        i.e. is sims score outside interactions at 10% of normal when it's\n        80-100 precipitation, then range would be 80-100, modifier would be 0.9\n        ")
    OUTDOOR_AUTONOMY_SNOW_PENALTY_REDUCTIONS = TunableWeatherAutonomyPenaltyReductions(description='\n        score = score - score * modifier * penalty reduction modifier\n        \n        i.e. if sim with the likes the outdoors trait is only half as affected\n        by the precipitation, key would be the likes the outdoors trait, value\n        would be 0.5\n        ')
    SNOW_ACCUMULATION_RATE = Tunable(description='\n        Rate per minute per target precipitation amount that snow accumulates.\n        i.e. 0.03 means ~30 minutes to 100 coverage in 100 snow.\n        ', tunable_type=float, default=0.03)
    SNOW_FRESHNESS_ACCUMULATION_RATE = Tunable(description="\n        Rate per minute per target precipitation amount that snow freshness \n        accumulates.\n        \n        Snow freshness decay rate is subtracted from this to get the final\n        decay/accumulation rate.\n        \n        i.e. 0.02 here with 1.0 freshness decay means it'll take 100 minutes to\n        accumulate to full at 100 snow.  (100 * 0.02 = 2.0 rate. 2.0 accumulation\n        rate - 1.0 decay rate = final rate 1.0.\n        \n        And at 50 precipitation the two rates will precisely cancel out.\n        ", tunable_type=float, default=0.02)
    SNOW_FRESHNESS_DECAY_RATE = Tunable100ConvertRange(description="\n        Rate per minute that snow freshness decays.\n        \n        This is subtracted from the calculated accumulation rate to get the\n        final decay/accumulation rate.\n        \n        At 1 this means it'll take 100 minutes to go from full freshness to\n        full decay.\n        ", default=1)
    SNOW_MELT_RATE = TunableTemperatureTuple(description='\n        Rate per minute at each temperature that snow melts.\n        Negative means it accumulates (i.e. frost) up to the frost limit\n        ', freezing=-0.03)
    WATER_ACCUMULATION_RATE = Tunable(description='\n        Rate per minute per target precipitation amount that water accumulates.\n        i.e. 0.03 means ~30 minutes to 100 coverage in 100 rain.\n        ', tunable_type=float, default=0.03)
    WATER_EVAPORATION_RATE = TunableTemperatureTuple(description='\n        Rate per minute at each temperature that water evaporates.\n        ')
    FROST_GROUND_ACCUMULATION_MAX = Tunable100ConvertRange(description='\n        Maximum amount of accumulation for ground frost.\n        ', default=10, minimum=0, maximum=100)
    FROST_WINDOW_MELT_RATE = TunableTemperatureTuple(description='\n        Rate per minute at each temperature that window frost melts.\n        Negative means it accumulates.\n        ', freezing=-0.1)
    WATER_THAW_RATE = TunableTemperatureTuple(description='\n        Rate per minute at each temperature that water thaws.\n        Negative means it freezes.\n        ', freezing=-0.1)
    WEATHER_TYPE_EXCLUSIVE_TEST = TunableExclusiveWeatherTypeVariant(description='\n        Tests that specify the exclusive weather type based on the current\n        weather.\n        ')
    WEATHER_TYPE_MULTIPLE_TEST = TunableMapping(description='\n        Tests that specify which non-exclusive weather types are true based\n        on the current weather.\n        ', key_type=TunableEnumEntry(description='\n            The weather type enum.\n            ', tunable_type=WeatherType, default=WeatherType.UNDEFINED, invalid_enums=tuple(WeatherType)), value_type=TunableTestSet(description='\n            At least one of these must pass for weather type to be true based\n            on the current weather.\n            \n            When test is true:\n            WeatherEnumTest will return true for that enum.\n            That enum will be sent to any objects with a weatheraware component\n            listening for that enum.\n            '), key_name='WeatherTypeKey', value_name='WeatherTypeTest', callback=_populate_weather_type_thresholds)
    WEATHER_TYPE_UI_INFO = TunableMapping(description='\n        Mapping of weather type enum to weather information. The information\n        includes the list of tests for the weather type, the type of weather \n        information and the corresponding UI information.\n        ', key_type=TunableEnumEntry(description='\n            The weather type enum.\n            ', tunable_type=WeatherType, default=WeatherType.UNDEFINED), value_type=TunableTuple(description='\n            Test and UI information for this weather type.\n            ', display_information=TunableTuple(icon=TunableIconAllPacks(description='\n                    The icon of the weather type.\n                    '), icon_large=TunableIconAllPacks(description='\n                    Large icon of the weather type, used on the weather tooltip.\n                    '), name=TunableLocalizedString(description='\n                    The name of the weather type.\n                    '), export_class_name='WeatherDisplayInformation', export_modes=ExportModes.All), weather_group_type=TunableEnumEntry(description='\n                What this weather type actually is. \n                Weather VS temperature VS lightning state etc...\n                ', tunable_type=WeatherTypeGroup, default=WeatherTypeGroup.UNGROUPED, export_modes=ExportModes.All), export_class_name='WeatherTypeValueTuple'), key_name='WeatherTypeKey', value_name='WeatherTypeValue', tuple_name='WeatherTypeTuple', verify_tunable_callback=_verify_tunable_callback)
    PUDDLES = TunableTuple(description='\n        Puddle information\n        ', tag=tag.TunableTags(description='\n            The set of tags that are used to determine which objects are treated as\n            rain-based puddles.\n            '), unnatural_terrain_definitions=TunableDefinitionList(description='\n            Definitions for which puddles to be created on unnatural terrain.\n            i.e. water puddles.\n            ', pack_safe=True, verify_tunable_callback=_verify_puddle_callback), natural_terrain_definitions=TunableDefinitionList(description='\n            Definitions for which puddles to be created on natural terrain.\n            i.e. mud puddles\n            ', pack_safe=True, verify_tunable_callback=_verify_puddle_callback), max=Tunable(description='\n            Maximum number of rain-based puddles to exist at one time.\n            ', tunable_type=int, default=10), creation_metrics=TunableList(description='\n            metrics for determining how puddles are created at differing\n            precipitation ranges.\n            ', tunable=TunableTuple(description='\n                A tuple of precipitation range to metrics.\n                ', value_range=TunableInterval(description='\n                    Precipitation range within which this metric is applied\n                    ', tunable_type=Tunable100ConvertRange, minimum=0, maximum=100, default_lower=0, default_upper=100), interval=TunableInterval(description='\n                    Range of minutes between creation checks at this amount\n                    of precipitation.\n                    ', tunable_type=int, default_lower=10, default_upper=20), chance=TunablePercent(description='\n                    Chance of spawning puddle each check.\n                    ', default=10.0))))
    SNOW_DRIFT = TunableTuple(description='\n        Snow drift information\n        ', tag=tag.TunableTags(description='\n            The set of tags that are used to determine which objects are treated as\n            snow drifts.\n            '), definitions=TunableDefinitionList(description='\n            Definitions for which objects to be created as snow drifts\n            ', pack_safe=True), max=Tunable(description='\n            Maximum number of snow drifts to exist at one time.\n            ', tunable_type=int, default=10), creation_metrics=TunableList(description='\n            metrics for determining how drifts are created at differing\n            precipitation ranges.\n            ', tunable=TunableTuple(description='\n                A tuple of precipitation range to metrics.\n                ', value_range=TunableInterval(description='\n                    Precipitation range within which this metric is applied\n                    ', tunable_type=Tunable100ConvertRange, minimum=0, maximum=100, default_lower=0, default_upper=100), interval=TunableInterval(description='\n                    Range of minutes between creation checks at this amount\n                    of precipitation.\n                    ', tunable_type=int, default_lower=10, default_upper=20), chance=TunablePercent(description='\n                    Chance of spawning drift each check.\n                    ', default=10.0))))
    ACTIVE_LIGHTNING = TunableTuple(description='\n        Lightning information for active strikes.\n        ', creation_metrics=TunableList(description='\n            Metrics for determining how bolts are created at differing\n            ambient lightning ranges.\n            ', tunable=TunableTuple(description='\n                A tuple of ambient lightning range to metrics.\n                ', value_range=TunableInterval(description='\n                    Ambient lightning range within which this metric is applied\n                    ', tunable_type=Tunable100ConvertRange, minimum=0, maximum=100, default_lower=0, default_upper=100), interval=TunableInterval(description='\n                    Range of minutes between creation checks at this amount\n                    of ambient lightning.\n                    ', tunable_type=TunableSimMinute, default_lower=10, default_upper=20), chance=TunablePercent(description='\n                    Chance of spawning active lightning each check.\n                    ', default=10.0))))
    WEATHER_ENDING_EVENT = TunableMapping(description='\n        Tuning information on event that can happen when a specific weather \n        is done.\n        ', key_type=TunableEnumEntry(description='\n            Weather type that when completed will trigger additional \n            functionality.\n            ', tunable_type=WeatherType, default=WeatherType.UNDEFINED, invalid_enums=(WeatherType.UNDEFINED,)), value_type=TunableTuple(description='\n            Information about event that should happen when the specified\n            weather ends. \n            ', trigger_chance=TunablePercent(description='\n                Chance of spawning drift each check.\n                ', default=10.0), event_type=TunableVariant(description='\n                Possible ingredient mapping by object definition of by \n                catalog object Tag.\n                ', spawn_rainbow=SpawnRainbow.TunableFactory())))
    TEMPERATURE_CONTROL_BUFF = TunablePackSafeReference(description='\n        If the enable temperature effects on Sims option is disabled,\n        this buff is applied to Sims. \n        ', manager=services.get_instance_manager(Types.BUFF), allow_none=True)
    WEATHER_AWARE_TIME_SLICE_SECONDS = TunableRealSecond(description='\n        The maximum alloted time for updating weather aware objects between time slices in seconds.\n        ', default=0.1)
    EXTREME_HEAT_WEATHER_TYPE = TunableEnumEntry(description='\n        The weather type enum that is for extreme heat.\n        UI needs this tuning.\n        ', tunable_type=WeatherType, default=WeatherType.UNDEFINED, invalid_enums=(WeatherType.UNDEFINED,), export_modes=ExportModes.ClientBinary)
    EXTREME_COLD_WEATHER_TYPE = TunableEnumEntry(description='\n        The weather type enum that is for extreme cold.\n        UI needs this tuning.\n        ', tunable_type=WeatherType, default=WeatherType.UNDEFINED, invalid_enums=(WeatherType.UNDEFINED,), export_modes=ExportModes.ClientBinary)
    WEATHER_OUTFIT_TESTS = TunableTuple(description='\n        A default weather outfit test and a list of tests to use instead of the\n        default test for specific outfit change reasons.\n        ', default_outfit_change_tests=TunableMapping(description='\n            A map of outfit category to test set. If the test set passes\n            a Sim will change outfit to the corresponding outfit category.\n            This is the default set of tests that is run to determine outfit\n            change behavior based on weather.\n            ', key_type=TunableEnumEntry(description='\n                The outfit category to set if the test set passes\n                ', tunable_type=WeatherOutfitCategory, default=WeatherOutfitCategory.HOTWEATHER), value_type=TunableTestSet()), outfit_change_reason_tests=TunableList(description='\n            The tests to run insted of the default test for specific outfit \n            change reasons.\n            ', tunable=TunableTuple(outfit_change_tests=TunableMapping(description='\n                    A map of outfit category to test set. If the test set passes\n                    a Sim will change outfit to the corresponding outfit category.\n                    ', key_type=TunableEnumEntry(description='\n                        The outfit category to set if the test set passes\n                        ', tunable_type=WeatherOutfitCategory, default=WeatherOutfitCategory.HOTWEATHER), value_type=TunableTestSet()), outfit_change_reasons=TunableEnumSet(description='\n                    The list of outfit change reasons for which we use the\n                    specific tests instead of the default test.\n                    ', enum_type=OutfitChangeReason, enum_default=OutfitChangeReason.Invalid, invalid_enums=(OutfitChangeReason.Invalid,))), verify_tunable_callback=_verify_weather_test_callback))
    WEATHER_OUFTIT_CHANGE_REASONS_TO_IGNORE = TunableEnumSet(description='\n        A list of outfit change reasons that are exempt from testing for\n        weather.\n        ', enum_type=OutfitChangeReason, enum_default=OutfitChangeReason.Invalid, invalid_enums=(OutfitChangeReason.Invalid,))
    FALLBACK_FORECAST = WeatherForecast.TunablePackSafeReference(description='\n        The weather forecast to use if no valid forecast is found.\n        ')
    COUNTS_AS_SHADE = TunableEnumSet(description='\n        A set of WeatherTypes that count as shade as far as is sun out\n        is concerned.\n        ', enum_type=WeatherType, enum_default=WeatherType.UNDEFINED, invalid_enums=(WeatherType.UNDEFINED,))

    @classmethod
    def get_weather_category_for_type(cls, weather_type):
        if weather_type not in cls.WEATHER_TYPE_UI_INFO:
            return
        return cls.WEATHER_TYPE_UI_INFO[weather_type].weather_group_type

    class RegionWeatherInfo:

        def __init__(self):
            self._forecasts = []
            self._current_event = None
            self._last_op = WeatherSeasons_pb2.SeasonWeatherInterpolations()
            self._next_weather_event_time = DATE_AND_TIME_ZERO
            self._forecast_time = DATE_AND_TIME_ZERO
            self._override_forecast = None
            self._override_forecast_season = None
            self._cross_season_override = False

        def clear(self):
            self._forecasts.clear()
            self._next_weather_event_time = DATE_AND_TIME_ZERO

    def __init__(self):
        self._weather_info = defaultdict(WeatherService.RegionWeatherInfo)
        self._trans_info = {}
        self._key_times = []
        self._region_id = None
        self._current_weather_types = set()
        self._weather_option = {PrecipitationType.SNOW: None, PrecipitationType.RAIN: None}
        self._temperature_effects_option = None
        self._weather_aware_objects = defaultdict(set)
        temperature_set = set()
        for temperature in Temperature:
            self._weather_aware_objects[WeatherType(temperature)] = temperature_set
        self._weather_update_pending = False
        self._add_weather_types = set()
        self._remove_weather_types = set()
        self._add_message_objects = set()
        self._remove_message_objects = set()
        self._snow_drift_alarm = None
        self._puddle_alarm = None
        self._lightning_alarm = None
        self._lightning_collectible_alarm = None

    @property
    def _forecasts(self):
        logger.assert_raise(self._region_id is not None, 'Weather Service trying to use region based property when region_id is None')
        return self._weather_info[self._region_id]._forecasts

    @property
    def _current_event(self):
        logger.assert_raise(self._region_id is not None, 'Weather Service trying to use region based property when region_id is None')
        return self._weather_info[self._region_id]._current_event

    @_current_event.setter
    def _current_event(self, value):
        logger.assert_raise(self._region_id is not None, 'Weather Service trying to use region based property when region_id is None')
        self._weather_info[self._region_id]._current_event = value

    @property
    def _last_op(self):
        logger.assert_raise(self._region_id is not None, 'Weather Service trying to use region based property when region_id is None')
        return self._weather_info[self._region_id]._last_op

    @_last_op.setter
    def _last_op(self, value):
        logger.assert_raise(self._region_id is not None, 'Weather Service trying to use region based property when region_id is None')
        self._weather_info[self._region_id]._last_op = value

    @property
    def _next_weather_event_time(self):
        logger.assert_raise(self._region_id is not None, 'Weather Service trying to use region based property when region_id is None')
        return self._weather_info[self._region_id]._next_weather_event_time

    @_next_weather_event_time.setter
    def _next_weather_event_time(self, value):
        logger.assert_raise(self._region_id is not None, 'Weather Service trying to use region based property when region_id is None')
        self._weather_info[self._region_id]._next_weather_event_time = value

    @property
    def _forecast_time(self):
        logger.assert_raise(self._region_id is not None, 'Weather Service trying to use region based property when region_id is None')
        return self._weather_info[self._region_id]._forecast_time

    @_forecast_time.setter
    def _forecast_time(self, value):
        logger.assert_raise(self._region_id is not None, 'Weather Service trying to use region based property when region_id is None')
        self._weather_info[self._region_id]._forecast_time = value

    @property
    def _override_forecast(self):
        logger.assert_raise(self._region_id is not None, 'Weather Service trying to use region based property when region_id is None')
        return self._weather_info[self._region_id]._override_forecast

    @_override_forecast.setter
    def _override_forecast(self, value):
        logger.assert_raise(self._region_id is not None, 'Weather Service trying to use region based property when region_id is None')
        self._weather_info[self._region_id]._override_forecast = value

    @property
    def _override_forecast_season(self):
        logger.assert_raise(self._region_id is not None, 'Weather Service trying to use region based property when region_id is None')
        return self._weather_info[self._region_id]._override_forecast_season

    @_override_forecast_season.setter
    def _override_forecast_season(self, value):
        logger.assert_raise(self._region_id is not None, 'Weather Service trying to use region based property when region_id is None')
        self._weather_info[self._region_id]._override_forecast_season = value

    @property
    def cross_season_override(self):
        logger.assert_raise(self._region_id is not None, 'Weather Service trying to use region based property when region_id is None')
        return self._weather_info[self._region_id]._cross_season_override

    @cross_season_override.setter
    def cross_season_override(self, value):
        logger.assert_raise(self._region_id is not None, 'Weather Service trying to use region based property when region_id is None')
        self._weather_info[self._region_id]._cross_season_override = value

    @classproperty
    def required_packs(cls):
        return (Pack.BASE_GAME, Pack.EP05)

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_WEATHER_SERVICE

    def save(self, save_slot_data=None, **kwargs):
        weather_service_data = WeatherSeasons_pb2.PersistableWeatherService()
        for (region_id, data) in self._weather_info.items():
            with ProtocolBufferRollback(weather_service_data.region_weathers) as region_weather:
                region_weather.region = region_id
                region_weather.weather = data._last_op
                if data._current_event is not None:
                    region_weather.weather_event = data._current_event.guid64
                else:
                    region_weather.weather_event = 0
                region_weather.forecast_time_stamp = data._forecast_time
                region_weather.next_weather_event_time = data._next_weather_event_time
                for forecast in data._forecasts:
                    region_weather.forecasts.append(forecast.guid64 if forecast is not None else 0)
                if data._override_forecast is not None:
                    region_weather.override_forecast = data._override_forecast.guid64
                    region_weather.override_forecast_season_stamp = data._override_forecast_season
        save_slot_data.gameplay_data.weather_service = weather_service_data

    def load(self, **_):
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        weather_service_data = save_slot_data_msg.gameplay_data.weather_service
        forecast_manager = services.get_instance_manager(sims4.resources.Types.WEATHER_FORECAST)
        event_manager = services.get_instance_manager(sims4.resources.Types.WEATHER_EVENT)
        snippet_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
        for region_weather in weather_service_data.region_weathers:
            data = WeatherService.RegionWeatherInfo()
            self._weather_info[region_weather.region] = data
            data._last_op.MergeFrom(region_weather.weather)
            data._current_event = event_manager.get(region_weather.weather_event)
            data._forecast_time = DateAndTime(region_weather.forecast_time_stamp)
            data._next_weather_event_time = DateAndTime(region_weather.next_weather_event_time)
            data._forecasts = [forecast_manager.get(forecast_guid) for forecast_guid in region_weather.forecasts]
            if None in data._forecasts:
                data._forecasts.clear()
            data._override_forecast = snippet_manager.get(region_weather.override_forecast)
            if data._override_forecast is not None:
                if region_weather.override_forecast_season_stamp in SeasonType:
                    data._override_forecast_season = SeasonType(region_weather.override_forecast_season_stamp)
                else:
                    data._override_forecast = None
                    data._current_event = None
                    data._forecasts.clear()

    def load_options(self, options_proto):
        self._temperature_effects_option = options_proto.temperature_effects_enabled
        self._weather_option[PrecipitationType.RAIN] = WeatherOption(options_proto.rain_options)
        self._weather_option[PrecipitationType.SNOW] = WeatherOption(options_proto.snow_options)

    def save_options(self, options_proto):
        options_proto.temperature_effects_enabled = self._temperature_effects_option
        options_proto.rain_options = self._weather_option[PrecipitationType.RAIN].value
        options_proto.snow_options = self._weather_option[PrecipitationType.SNOW].value

    def on_zone_load(self):
        self._region_id = region.get_region_description_id_from_zone_id(services.current_zone_id())
        self._current_weather_types = set()
        current_time = services.time_service().sim_now
        if self._next_weather_event_time == DATE_AND_TIME_ZERO or current_time > self._next_weather_event_time:
            self._current_event = None
        if self._forecast_time != DATE_AND_TIME_ZERO:
            now_days = int(current_time.absolute_days())
            day_time_span = create_time_span(days=1)
            while now_days > int(self._forecast_time.absolute_days()) and self._forecasts:
                del self._forecasts[0]
                self._forecast_time = self._forecast_time + day_time_span
        if self._current_event is None:
            self._update_trans_info()
            self._send_new_weather_event()
        else:
            self._send_existing_weather_event()
        self.update_weather_type(during_load=True)

    def on_zone_unload(self):
        self._current_weather_types.clear()
        for entry in self._weather_aware_objects.values():
            entry.clear()
        self._add_message_objects.clear()
        self._remove_message_objects.clear()
        self._key_times.clear()
        self._remove_snow_drift_alarm()
        self._remove_puddle_alarm()
        if self._lightning_collectible_alarm is not None:
            alarms.cancel_alarm(self._lightning_collectible_alarm)
            self._lightning_collectible_alarm = None

    def _send_new_weather_event(self):
        self.populate_forecasts(1)
        current_region_forecasts = self._forecasts
        if current_region_forecasts:
            forecast = current_region_forecasts[0]
            if forecast is not None:
                (weather_event, duration) = forecast.get_weather_event()
                self.start_weather_event(weather_event, duration)

    def _send_existing_weather_event(self):
        op = WeatherEventOp(self._last_op)
        Distributor.instance().add_op_with_no_owner(op)
        self._update_trans_info()
        self._update_keytimes()

    def _update_trans_info(self):
        self._trans_info.clear()
        for weather_interop in self._last_op.season_weather_interlops:
            if not weather_interop.start_value != 0:
                if weather_interop.end_value != 0:
                    self._trans_info[int(weather_interop.message_type)] = WeatherElementTuple(weather_interop.start_value, DateAndTime(weather_interop.start_time*date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND), weather_interop.end_value, DateAndTime(weather_interop.end_time*date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND))
            self._trans_info[int(weather_interop.message_type)] = WeatherElementTuple(weather_interop.start_value, DateAndTime(weather_interop.start_time*date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND), weather_interop.end_value, DateAndTime(weather_interop.end_time*date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND))

    def set_weather_option(self, precipitation_type, weather_option):
        old_value = self._weather_option[precipitation_type]
        if old_value == weather_option:
            return
        self._weather_option[precipitation_type] = weather_option
        self.reset_forecasts()

    def reset_forecasts(self, all_regions=True):
        if all_regions:
            for region_data in self._weather_info.values():
                region_data.clear()
        else:
            self._forecasts.clear()
        self._send_new_weather_event()

    def set_temperature_effects_enabled(self, enabled):
        if self._temperature_effects_option == enabled:
            return
        self._temperature_effects_option = enabled
        sim_infos = services.sim_info_manager().values()
        if self.TEMPERATURE_CONTROL_BUFF is None:
            logger.error('TEMPERATURE_CONTROL_BUFF is None, meaning this code path has been entered outside of EP05')
            return
        for sim_info in sim_infos:
            self.apply_weather_option_buffs(sim_info)

    def apply_weather_option_buffs(self, sim_or_sim_info):
        if self.TEMPERATURE_CONTROL_BUFF is None:
            logger.error('TEMPERATURE_CONTROL_BUFF is None, meaning this code path has been entered outside of EP05')
            return
        if self._temperature_effects_option == False:
            sim_or_sim_info.add_buff_from_op(self.TEMPERATURE_CONTROL_BUFF)
        else:
            sim_or_sim_info.remove_buff_by_type(self.TEMPERATURE_CONTROL_BUFF)

    def force_start_weather_event(self, weather_event, duration):
        for weather_element in self._trans_info:
            self._trans_info[weather_element] = WeatherElementTuple(0, 0, 0, 0)
        self._current_event = None
        self._send_weather_event_op()
        self.start_weather_event(weather_event, duration)

    def start_weather_event(self, weather_event, duration):
        (new_trans_info, next_time) = weather_event.get_transition_data(self._current_event, self._trans_info, duration)
        if self._current_event is None:
            self._next_weather_event_time = self._create_secondary_weather_elements(new_trans_info, next_time)
        else:
            self._next_weather_event_time = self._update_secondary_weather_elements(new_trans_info, next_time)
        self._current_event = weather_event
        self._trans_info = new_trans_info
        self._send_weather_event_op()

    def _send_weather_event_op(self):
        if self._trans_info:
            messages_to_remove = []
            self._last_op = WeatherSeasons_pb2.SeasonWeatherInterpolations()
            op = WeatherEventOp(self._last_op)
            for (message_type, data) in self._trans_info.items():
                op.populate_op(message_type, data.start_value, data.start_time, data.end_value, data.end_time)
                if data.start_value == data.end_value and data.end_value == 0.0:
                    messages_to_remove.append(message_type)
            Distributor.instance().add_op_with_no_owner(op)
            for message_type in messages_to_remove:
                del self._trans_info[message_type]
        self._update_keytimes()

    def _get_element_interpolation(self, start_time, rate, start_value, target_value):
        if rate == 0:
            return WeatherElementTuple(start_value, start_time, start_value, start_time)
        delta = start_value - target_value
        minutes = abs(delta/rate)
        end_time = start_time + create_time_span(minutes=minutes)
        return WeatherElementTuple(start_value, start_time, target_value, end_time)

    def _add_secondary_element_decay(self, new_trans_info, temp, element_type, tuning, time, current_value=None):
        if current_value is None:
            current_value = self.get_weather_element_value(element_type, default=None)
        if temp == Temperature.BURNING:
            rate = tuning.burning
        elif temp == Temperature.HOT:
            rate = tuning.hot
        elif temp == Temperature.WARM:
            rate = tuning.warm
        elif temp == Temperature.COOL:
            rate = tuning.cool
        elif temp == Temperature.COLD:
            rate = tuning.cold
        elif temp == Temperature.FREEZING:
            rate = tuning.freezing
        else:
            logger.error('No secondary element decay rate handled for this temperature: {}', Temperature(temp))
            rate = 0
        if rate >= 0:
            if current_value is None:
                return
            if current_value <= 0.0 or rate == 0:
                new_trans_info[int(element_type)] = WeatherElementTuple(current_value, time, current_value, time)
            else:
                new_trans_info[int(element_type)] = self._get_element_interpolation(time, rate, current_value, 0.0)
        else:
            if current_value is None:
                current_value = 0.0
            if current_value >= 1.0:
                new_trans_info[int(element_type)] = WeatherElementTuple(current_value, time, current_value, time)
            else:
                new_trans_info[int(element_type)] = self._get_element_interpolation(time, rate, current_value, 1.0)

    def _add_snow_accumulation_decay(self, new_trans_info, temp, time, current_value=None):
        key = int(GroundCoverType.SNOW_ACCUMULATION)
        if current_value is None:
            current_value = self.get_weather_element_value(key)
        if temp == Temperature.FREEZING and services.season_service().season == SeasonType.WINTER:
            rate = self.SNOW_MELT_RATE.freezing
            if rate != 0 and current_value >= 0 and current_value < self.FROST_GROUND_ACCUMULATION_MAX:
                new_trans_info[key] = self._get_element_interpolation(time, rate, current_value, self.FROST_GROUND_ACCUMULATION_MAX)
            else:
                new_trans_info[key] = WeatherElementTuple(current_value, time, current_value, time)
            return
        if current_value == 1.0:
            current_value = -1.0
        elif current_value > 0:
            logger.warn("Melting accumulating (>0) snow that isn't at 1")
        if current_value == 0.0:
            return
        if temp == Temperature.BURNING:
            rate = self.SNOW_MELT_RATE.burning
        elif temp == Temperature.HOT:
            rate = self.SNOW_MELT_RATE.hot
        elif temp == Temperature.WARM:
            rate = self.SNOW_MELT_RATE.warm
        elif temp == Temperature.COOL:
            rate = self.SNOW_MELT_RATE.cool
        elif temp == Temperature.COLD:
            rate = self.SNOW_MELT_RATE.cold
        elif temp == Temperature.FREEZING:
            rate = 0
        else:
            logger.error('No snow accumulation rate handled for this temperature: {}', Temperature(temp))
            rate = 0
        new_trans_info[key] = self._get_element_interpolation(time, rate, current_value, 0.0)

    def _add_precipitation_accumulation(self, precip_key, accumulate_key, rate, new_trans_info, time, current_value=None):
        data = new_trans_info.get(int(precip_key), None)
        if data is None:
            start_time = time
            target = 0.0
        else:
            start_time = data.start_time
            target = data.end_value
        if target == 0.0:
            return (start_time, True)
        else:
            rate = rate*target
            if current_value is None:
                current_value = self.get_weather_element_value(int(accumulate_key), time)
            if current_value < 0.0:
                logger.warn('Accumulation type {} is trying to accumulate when negative, accumulating to -1 instead.', PrecipitationType(precip_key))
                target_value = -1
            else:
                target_value = 1
            new_trans_info[int(accumulate_key)] = self._get_element_interpolation(start_time, rate, current_value, target_value)
            return (start_time, False)

    def _get_snow_freshness_rate(self, snow_amount):
        region_instance = region.get_region_instance_from_zone_id(services.current_zone_id())
        if region_instance.weather_supports_fresh_snow:
            increase_rate = snow_amount*self.SNOW_FRESHNESS_ACCUMULATION_RATE
            return increase_rate - self.SNOW_FRESHNESS_DECAY_RATE
        return 0

    def _validate_event_end_time_for_snow(self, new_trans_info, end_time):
        max_snow_accumulation_time = new_trans_info[int(GroundCoverType.SNOW_ACCUMULATION)].end_time
        if end_time != DATE_AND_TIME_ZERO:
            end_time = max_snow_accumulation_time
        return end_time

    def _fake_snow_accumulation_for_snow(self, new_trans_info, next_time, time, snow_value):
        static_max_weather_element = WeatherElementTuple(1.0, time, 1.0, time)
        if self._get_snow_freshness_rate(snow_value) > 0.0:
            new_trans_info[int(WeatherEffectType.SNOW_FRESHNESS)] = static_max_weather_element
            new_trans_info[int(GroundCoverType.SNOW_ACCUMULATION)] = static_max_weather_element
            return next_time
        season_service = services.season_service()
        if season_service.season_content.get_segment(time) != SeasonSegment.EARLY:
            new_trans_info[int(GroundCoverType.SNOW_ACCUMULATION)] = static_max_weather_element
            return next_time
        old_time = self._next_weather_event_time
        if old_time == DATE_AND_TIME_ZERO or old_time not in season_service.season_content:
            start_value = random.random()
        else:
            old_value = self._trans_info.get(int(GroundCoverType.SNOW_ACCUMULATION), None)
            if old_value is None or old_value.end_value == 0:
                start_value = self.FROST_GROUND_ACCUMULATION_MAX + random.random()*(1 - self.FROST_GROUND_ACCUMULATION_MAX)/2
            else:
                start_value = 1.0
        self._add_precipitation_accumulation(PrecipitationType.SNOW, GroundCoverType.SNOW_ACCUMULATION, self.SNOW_ACCUMULATION_RATE, new_trans_info, time, current_value=start_value)
        return self._validate_event_end_time_for_snow(new_trans_info, next_time)

    def _create_secondary_weather_elements(self, new_trans_info, next_time):
        time = services.time_service().sim_now
        static_max_weather_element = WeatherElementTuple(1.0, time, 1.0, time)
        rain = new_trans_info.get(int(PrecipitationType.RAIN), None)
        if rain is not None:
            new_trans_info[int(GroundCoverType.RAIN_ACCUMULATION)] = static_max_weather_element
        else:
            temp_interpolate = new_trans_info.get(int(WeatherEffectType.TEMPERATURE), None)
            if temp_interpolate is not None:
                if temp_interpolate.start_value == Temperature.FREEZING:
                    season_service = services.season_service()
                    if season_service is None:
                        logger.error('Somehow creating secondary weather elements without season service in freezing temps')
                        season = None
                    else:
                        season = season_service.season
                    if season != SeasonType.WINTER:
                        start_value = random.random()
                        self._add_secondary_element_decay(new_trans_info, Temperature.FREEZING, WeatherEffectType.WATER_FROZEN, self.WATER_THAW_RATE, time, current_value=start_value)
                        self._add_secondary_element_decay(new_trans_info, Temperature.FREEZING, WeatherEffectType.WINDOW_FROST, self.FROST_WINDOW_MELT_RATE, time, current_value=start_value)
                    else:
                        new_trans_info[int(WeatherEffectType.WATER_FROZEN)] = static_max_weather_element
                        new_trans_info[int(WeatherEffectType.WINDOW_FROST)] = static_max_weather_element
                        snow = new_trans_info.get(int(PrecipitationType.SNOW), None)
                        if snow is not None:
                            next_time = self._fake_snow_accumulation_for_snow(new_trans_info, next_time, time, snow.end_value)
                        else:
                            old_time = self._next_weather_event_time
                            if old_time == DATE_AND_TIME_ZERO or old_time not in season_service.season_content:
                                season_segment = season_service.season_content.get_segment(time)
                                if self.get_forecast(season, season_segment).is_snowy() or self.get_forecast(season, season_segment).is_snowy():
                                    start_value = 1
                                else:
                                    start_value = 0
                            else:
                                old_value = self._trans_info.get(int(GroundCoverType.SNOW_ACCUMULATION), None)
                                if not old_value is None:
                                    if -1 < old_value.end_value and old_value.end_value <= 0:
                                        if not self._forecasts[0].is_snowy():
                                            start_value = 0
                                        else:
                                            start_value = 1
                                    else:
                                        start_value = 1
                                elif not self._forecasts[0].is_snowy():
                                    start_value = 0
                                else:
                                    start_value = 1
                                start_value = 1
                            start_value = max(start_value, self.FROST_GROUND_ACCUMULATION_MAX)
                            new_trans_info[int(GroundCoverType.SNOW_ACCUMULATION)] = WeatherElementTuple(start_value, time, start_value, time)
                elif temp_interpolate.start_value == Temperature.COLD:
                    season_service = services.season_service()
                    if season_service is None:
                        logger.error('Somehow creating secondary weather elements without season service in cold temps')
                        season = None
                    else:
                        season = season_service.season
                    if season == SeasonType.WINTER:
                        old_time = self._next_weather_event_time
                        if old_time == DATE_AND_TIME_ZERO or old_time not in season_service.season_content:
                            return next_time
                        old_value = self._trans_info.get(int(GroundCoverType.SNOW_ACCUMULATION), None)
                        if old_value.end_value == -1 or old_value.end_value > 0:
                            new_trans_info[int(GroundCoverType.SNOW_ACCUMULATION)] = WeatherElementTuple(1.0, time, 1.0, time)
        return next_time

    def _update_secondary_weather_elements(self, new_trans_info, next_time):
        time = services.time_service().sim_now
        temp = new_trans_info.get(int(WeatherEffectType.TEMPERATURE), None)
        if temp is None:
            temp = Temperature.WARM
        else:
            temp = temp.start_value
        self._add_secondary_element_decay(new_trans_info, temp, WeatherEffectType.WATER_FROZEN, self.WATER_THAW_RATE, time)
        self._add_secondary_element_decay(new_trans_info, temp, WeatherEffectType.WINDOW_FROST, self.FROST_WINDOW_MELT_RATE, time)
        (start_time, decay) = self._add_precipitation_accumulation(PrecipitationType.RAIN, GroundCoverType.RAIN_ACCUMULATION, self.WATER_ACCUMULATION_RATE, new_trans_info, time)
        if decay:
            self._add_secondary_element_decay(new_trans_info, temp, GroundCoverType.RAIN_ACCUMULATION, self.WATER_EVAPORATION_RATE, start_time)
        else:
            snow_value = self.get_weather_element_value(int(GroundCoverType.SNOW_ACCUMULATION), time)
            if snow_value != 0:
                logger.warn('Starting to accumulate rain while there is snow.  Melting existing snow in time.')
                new_trans_info[int(GroundCoverType.SNOW_ACCUMULATION)] = WeatherElementTuple(snow_value, time, 0.0, start_time)
        start_time = time
        decay = True
        if temp == Temperature.FREEZING:
            season_service = services.season_service()
            if season_service is None:
                logger.error('Somehow updating secondary weather elements in freezing temperature without season service')
            elif season_service.season == SeasonType.WINTER:
                (start_time, decay) = self._add_precipitation_accumulation(PrecipitationType.SNOW, GroundCoverType.SNOW_ACCUMULATION, self.SNOW_ACCUMULATION_RATE, new_trans_info, time)
        if decay:
            if new_trans_info.get(int(GroundCoverType.SNOW_ACCUMULATION), None) is None:
                self._add_snow_accumulation_decay(new_trans_info, temp, start_time)
        else:
            water_value = self.get_weather_element_value(int(GroundCoverType.RAIN_ACCUMULATION), time)
            if water_value != 0:
                logger.warn('Starting to accumulate snow while there is water.  Evaporating existing water in time.')
                new_trans_info[int(GroundCoverType.RAIN_ACCUMULATION)] = WeatherElementTuple(water_value, time, 0.0, start_time)
            next_time = self._validate_event_end_time_for_snow(new_trans_info, next_time)
        snow = new_trans_info.get(int(PrecipitationType.SNOW), None)
        if snow is None or new_trans_info.get(int(GroundCoverType.SNOW_ACCUMULATION), None) is None:
            freshness_rate = self._get_snow_freshness_rate(0.0)
        else:
            freshness_rate = self._get_snow_freshness_rate(snow.end_value)
        if freshness_rate <= 0.0:
            target_fresh_value = 0.0
            freshness_data = self._trans_info.get(int(WeatherEffectType.SNOW_FRESHNESS), None)
            if freshness_data is None:
                start_fresh_value = None
            else:
                start_fresh_value = self.get_weather_element_value(int(WeatherEffectType.SNOW_FRESHNESS), time)
                if time > freshness_data.end_time:
                    start_fresh_value = None
        else:
            target_fresh_value = 1.0
            start_fresh_value = self.get_weather_element_value(int(WeatherEffectType.SNOW_FRESHNESS), time)
        if start_fresh_value is not None:
            if snow is not None:
                start_time = snow.end_time
            else:
                start_time = time
            new_trans_info[int(WeatherEffectType.SNOW_FRESHNESS)] = self._get_element_interpolation(start_time, freshness_rate, start_fresh_value, target_fresh_value)
        return next_time

    def _update_keytimes(self):
        self._key_times.clear()
        for data in self._trans_info.values():
            self._key_times.extend((data.start_time, data.end_time))
        for ground_cover_type in GroundCoverType:
            if not ground_cover_type not in self._trans_info:
                if ground_cover_type not in WEATHER_TYPE_THRESHOLDS:
                    pass
                else:
                    trans_info = self._trans_info[ground_cover_type]
                    trans_lower_value = min(trans_info.start_value, trans_info.end_value)
                    trans_upper_value = max(trans_info.start_value, trans_info.end_value)
                    for threshold in WEATHER_TYPE_THRESHOLDS[ground_cover_type]:
                        if threshold > trans_lower_value and threshold < trans_upper_value:
                            percent_of_change = (threshold - trans_info.start_value)/(trans_info.end_value - trans_info.start_value)
                            key_time = trans_info.start_time + TimeSpan(percent_of_change*(trans_info.end_time - trans_info.start_time).in_ticks())
                            self._key_times.append(key_time)
        self._key_times.sort()

    def set_override_forecast(self, forecast):
        self._override_forecast = forecast
        if forecast is None:
            self._override_forecast_season = None
        else:
            self._override_forecast_season = services.season_service().season
        self.reset_forecasts(all_regions=False)

    def get_override_forecast(self, season=None):
        override_forecast = self._override_forecast
        if season is None:
            season = services.season_service().season
        if override_forecast is not None and self._override_forecast_season == season or self.cross_season_override:
            return override_forecast

    def get_forecast(self, season, season_segment, snow_safe=True, rain_safe=True):
        region_instance = region.get_region_instance_from_zone_id(services.current_zone_id())
        forecast_by_segment = self.get_override_forecast(season)
        if forecast_by_segment is None:
            forecast_by_segment = region_instance.weather.get(season, None)
        if forecast_by_segment is not None:
            forecast_list = forecast_by_segment.get(season_segment, None)
            if forecast_list is not None:
                weighted_forecasts = [(forecast.weight, forecast.forecast) for forecast in forecast_list if forecast.forecast.is_forecast_supported(self._weather_option, snow_safe, rain_safe)]
                forecast = sims4.random.weighted_random_item(weighted_forecasts)
                if forecast is not None:
                    return forecast
                forecast_tuple = sims4.random.random.choice(weighted_forecasts)
                if forecast_tuple is not None:
                    return forecast_tuple[1]
                logger.error('Failed to select a forecast\nWeighted forecasts: {}\nregion: {}\nseason: {}\nseason segment: {}', weighted_forecasts, region_instance, season, season_segment)
        return self.FALLBACK_FORECAST

    def _validate_override_forecasts(self):
        season = services.season_service().season
        for (_, regiondata) in self._weather_info.items():
            if regiondata._override_forecast is not None and regiondata._override_forecast_season != season:
                if regiondata._cross_season_override:
                    regiondata._override_forecast_season = season
                else:
                    regiondata._override_forecast = None
                    regiondata._override_forecast_season = None

    def populate_forecasts(self, num_days):
        season_service = services.season_service()
        if season_service is None:
            return
        existing_forecasts = self._forecasts
        existing_forecast_count = len(existing_forecasts)
        num_days = num_days - existing_forecast_count
        if num_days > 0:
            start_time = services.time_service().sim_now + create_time_span(days=existing_forecast_count)
            self._validate_override_forecasts()
            if existing_forecast_count == 0:
                self._forecast_time = start_time
                if self._current_event is not None:
                    snow_safe = self._trans_info.get(int(PrecipitationType.RAIN), None) is None and self._trans_info.get(int(GroundCoverType.RAIN_ACCUMULATION), None) is None
                    rain_safe = self._trans_info.get(int(PrecipitationType.SNOW), None) is None and self._trans_info.get(int(GroundCoverType.SNOW_ACCUMULATION), None) is None
                else:
                    snow_safe = True
                    rain_safe = True
            else:
                previous_forecast = existing_forecasts[-1]
                snow_safe = not previous_forecast.is_rainy()
                rain_safe = not previous_forecast.is_snowy()
            season_infos = season_service.get_season_and_segments(start_time, num_days)
            for (season, segment) in season_infos:
                existing_forecasts.append(self.get_forecast(season, segment, snow_safe, rain_safe))
        self._send_ui_weather_forecast()

    def get_weather_element_value(self, element_type, time=None, default=0.0):
        data = self._trans_info.get(int(element_type), None)
        if data is None:
            return default
        if time is None:
            time = services.time_service().sim_now
        start_value = data.start_value
        start_time = data.start_time
        end_value = data.end_value
        end_time = data.end_time
        if time <= start_time:
            return start_value
        if time >= end_time:
            return end_value
        numerator = float((time - start_time).in_ticks())
        denominator = float((end_time - start_time).in_ticks())
        return (end_value - start_value)*numerator/denominator + start_value

    def _will_be_any(self, key, time):
        data = self._trans_info.get(int(key), None)
        if time < data.start_time:
            if data.start_value > 0:
                return True
        elif time < data.end_time or data.end_value > 0:
            return True
        return False

    def update_weather_type(self, during_load=False):
        time = services.time_service().sim_now
        while self._key_times and time > self._key_times[0]:
            del self._key_times[0]
        if self._add_message_objects or self._remove_message_objects:
            self._weather_update_pending = True
            return
        self._weather_update_pending = False
        resolver = GlobalResolver()
        new_flags = set()
        if self.WEATHER_TYPE_EXCLUSIVE_TEST is not None:
            new_flags.add(self.WEATHER_TYPE_EXCLUSIVE_TEST.get_weather_type(resolver))
        else:
            logger.error('Somehow updating weather types without weather type exclusive tests.')
        for (key, value) in self.WEATHER_TYPE_MULTIPLE_TEST.items():
            if value.run_tests(resolver):
                new_flags.add(key)
        data = self._trans_info.get(int(WeatherEffectType.TEMPERATURE), None)
        if data is not None:
            new_flags.add(WeatherType(data.start_value))
        else:
            new_flags.add(WeatherType(0))
        if self._will_be_any(PrecipitationType.RAIN, time):
            new_flags.add(WeatherType.AnyRain)
        data = self._trans_info.get(int(GroundCoverType.RAIN_ACCUMULATION), None)
        if data is not None:
            if data.start_value == 1.0:
                if time < data.start_time or data.end_value == 1.0:
                    new_flags.add(WeatherType.Max_Rain_Accumulation)
            elif time >= data.end_time and data.end_value == 1.0:
                new_flags.add(WeatherType.Max_Rain_Accumulation)
            if new_flags.issuperset({WeatherType.Max_Rain_Accumulation, WeatherType.AnyRain}):
                self._add_puddle_alarm(time)
            else:
                self._remove_puddle_alarm()
        else:
            self._remove_puddle_alarm()
        if self._will_be_any(PrecipitationType.SNOW, time):
            new_flags.add(WeatherType.AnySnow)
        data = self._trans_info.get(int(GroundCoverType.SNOW_ACCUMULATION), None)
        if data is not None:
            start_value = abs(data.start_value)
            end_value = abs(data.end_value)
            if start_value == 1.0:
                if time < data.start_time or data.start_value == data.end_value:
                    new_flags.add(WeatherType.Max_Snow_Accumulation)
            elif time >= data.end_time and end_value == 1.0:
                new_flags.add(WeatherType.Max_Snow_Accumulation)
            if new_flags.issuperset({WeatherType.Max_Snow_Accumulation, WeatherType.AnySnow}):
                self._add_snow_drift_alarm(time)
            else:
                self._remove_snow_drift_alarm()
        else:
            self._remove_snow_drift_alarm()
        if self._will_be_any(WeatherEffectType.LIGHTNING, time):
            new_flags.add(WeatherType.AnyLightning)
            self._add_lightning_alarm(time)
        else:
            self._remove_lightning_alarm()
        self._add_weather_types = new_flags - self._current_weather_types
        self._remove_weather_types = self._current_weather_types - new_flags
        self._current_weather_types = new_flags
        self._add_message_objects.clear()
        self._remove_message_objects.clear()
        for weather_type in self._add_weather_types:
            self._add_message_objects.update(self._weather_aware_objects[weather_type])
        for weather_type in self._remove_weather_types:
            self._remove_message_objects.update(self._weather_aware_objects[weather_type])
            self._on_ending_weather_types(weather_type)
        self._send_ui_weather_message()
        if during_load:
            self._send_weather_aware_messages(timeslice=False)

    def has_weather_type(self, weather_type):
        return weather_type in self._current_weather_types

    def has_any_weather_type(self, weather_types):
        if weather_types & self._current_weather_types:
            return True
        return False

    def register_object(self, new_object, weather_types):
        for weather_type in weather_types:
            self._weather_aware_objects[weather_type].add(new_object)

    def _find_good_weather_object_location(self, obj):
        search_flags = FGLSearchFlag.SHOULD_TEST_BUILDBUY | FGLSearchFlag.CALCULATE_RESULT_TERRAIN_HEIGHTS | FGLSearchFlag.DONE_ON_MAX_RESULTS | FGLSearchFlag.STAY_OUTSIDE | FGLSearchFlag.STAY_IN_LOT
        active_lot = services.active_lot()
        pos = active_lot.get_random_point()
        routing_surface = routing.SurfaceIdentifier(services.current_zone_id(), 0, routing.SurfaceType.SURFACETYPE_WORLD)
        pos.y = services.terrain_service.terrain_object().get_routing_surface_height_at(pos.x, pos.z, routing_surface)
        starting_location = placement.create_starting_location(position=pos, routing_surface=routing_surface)
        fgl_context = placement.create_fgl_context_for_object(starting_location, obj, search_flags=search_flags, random_range_weighting=sims4.math.MAX_INT32)
        (position, orientation) = placement.find_good_location(fgl_context)
        return (position, orientation, routing_surface)

    def _on_ending_weather_types(self, weather_type):
        if weather_type not in self.WEATHER_ENDING_EVENT:
            return
        weather_event = self.WEATHER_ENDING_EVENT.get(weather_type)
        if random.random() < weather_event.trigger_chance:
            weather_event.event_type.apply_event()

    def _test_weather_object_creation(self, value, tuning):
        existing_objects = sum(1 for entity in self._weather_aware_objects[WeatherType.Hot] if entity.has_any_tag(tuning.tag))
        if existing_objects < tuning.max:
            for metric in tuning.creation_metrics:
                if value in metric.value_range:
                    if random.random() < metric.chance:
                        return True
                    return False
        return False

    def _create_tuning_based_alarm(self, value, tuning, callback):
        for metric in tuning.creation_metrics:
            if value in metric.value_range:
                return alarms.add_alarm(self, create_time_span(minutes=metric.interval.random_int()), callback)

    def _add_puddle_alarm(self, time):
        if self._puddle_alarm is None:
            value = self.get_weather_element_value(PrecipitationType.RAIN, time, default=None)
            if value is not None:
                self._puddle_alarm = self._create_tuning_based_alarm(value, self.PUDDLES, self._create_puddle)
            return value

    def _create_puddle(self, _):
        self._puddle_alarm = None
        rain_value = self._add_puddle_alarm(services.time_service().sim_now)
        if rain_value is not None and self._test_weather_object_creation(rain_value, self.PUDDLES):
            definition = random.choice(self.PUDDLES.natural_terrain_definitions)
            obj = create_object(definition)
            (position, orientation, routing_surface) = self._find_good_weather_object_location(obj)
            if position is not None:
                level = routing_surface.secondary_id
                if terrain.is_terrain_tag_at_position(position.x, position.z, (TerrainTag.SAND,), level=level):
                    obj.destroy()
                    return
                if not is_location_natural_ground(services.current_zone_id(), position, level):
                    obj.destroy()
                    definition = random.choice(self.PUDDLES.unnatural_terrain_definitions)
                    obj = create_object(definition)
                obj.place_puddle_at(position, orientation, routing_surface)
            else:
                obj.destroy()

    def _remove_puddle_alarm(self):
        if self._puddle_alarm is not None:
            alarms.cancel_alarm(self._puddle_alarm)
            self._puddle_alarm = None

    def _add_lightning_alarm(self, time):
        if self._lightning_alarm is None:
            value = self.get_weather_element_value(WeatherEffectType.LIGHTNING, time, default=None)
            if value is not None:
                self._lightning_alarm = self._create_tuning_based_alarm(value, self.ACTIVE_LIGHTNING, self._create_active_lightning)
            return value

    def _remove_lightning_alarm(self):
        if self._lightning_alarm is not None:
            alarms.cancel_alarm(self._lightning_alarm)
            self._lightning_alarm = None

    def _create_active_lightning(self, _):
        self._lightning_alarm = None
        lightning_value = self._add_lightning_alarm(services.time_service().sim_now)
        if lightning_value is not None:
            for metric in self.ACTIVE_LIGHTNING.creation_metrics:
                if lightning_value in metric.value_range and random.random() < metric.chance:
                    LightningStrike.perform_active_lightning_strike()
                    break

    def _add_snow_drift_alarm(self, time):
        if self._snow_drift_alarm is None:
            value = self.get_weather_element_value(PrecipitationType.SNOW, time, default=None)
            if value is not None:
                self._snow_drift_alarm = self._create_tuning_based_alarm(value, self.SNOW_DRIFT, self._create_snow_drift)
            return value

    def _create_snow_drift(self, _):
        self._snow_drift_alarm = None
        snow_value = self._add_snow_drift_alarm(services.time_service().sim_now)
        if snow_value is not None and self._test_weather_object_creation(snow_value, self.SNOW_DRIFT):
            definition = random.choice(self.SNOW_DRIFT.definitions)
            drift = create_object(definition)
            (position, orientation, routing_surface) = self._find_good_weather_object_location(drift)
            if position is not None:
                drift.move_to(translation=position, orientation=orientation, routing_surface=routing_surface)
                drift.fade_in()
            else:
                drift.destroy()

    def _remove_snow_drift_alarm(self):
        if self._snow_drift_alarm is not None:
            alarms.cancel_alarm(self._snow_drift_alarm)
            self._snow_drift_alarm = None

    def deregister_object(self, old_object, weather_types):
        for weather_type in weather_types:
            self._weather_aware_objects[weather_type].discard(old_object)

    def get_current_weather_types(self):
        return self._current_weather_types.copy()

    def _get_precipitation_autonomy_multiplier(self, sim, precipitation_type, penalties, reduction, time):
        amount = self.get_weather_element_value(precipitation_type, time)
        if amount != 0.0:
            amount = amount
            for autonomy_mod in penalties:
                if amount in autonomy_mod.value_range:
                    multiplier = autonomy_mod.modifier
                    break
            return 1.0
            for (trait, modifier) in reduction.items():
                if sim.has_trait(trait):
                    multiplier *= modifier
            return 1.0 - multiplier
        return 1.0

    def get_current_precipitation_autonomy_multiplier(self, sim):
        now = services.time_service().sim_now
        multiplier = self._get_precipitation_autonomy_multiplier(sim, PrecipitationType.RAIN, self.OUTDOOR_AUTONOMY_RAIN_PENALTIES, self.OUTDOOR_AUTONOMY_RAIN_PENALTY_REDUCTIONS, now)
        if multiplier != 1.0:
            return multiplier
        multiplier = self._get_precipitation_autonomy_multiplier(sim, PrecipitationType.SNOW, self.OUTDOOR_AUTONOMY_SNOW_PENALTIES, self.OUTDOOR_AUTONOMY_SNOW_PENALTY_REDUCTIONS, now)
        return multiplier

    def update(self):
        if self._region_id is None:
            return
        if self._add_message_objects or self._remove_message_objects:
            self._send_weather_aware_messages()
        now = services.time_service().sim_now
        if math.floor(now.absolute_days()) != math.floor(self._forecast_time.absolute_days()):
            self._forecast_time = now
            del self._forecasts[0]
            self.populate_forecasts(1)
        if self._next_weather_event_time != DATE_AND_TIME_ZERO and now > self._next_weather_event_time:
            self._send_new_weather_event()
        if self._key_times and now > self._key_times[0]:
            self.update_weather_type()

    def update_weather_aware_message(self, update_object):
        if update_object in self._remove_message_objects:
            self._remove_message_objects.remove(update_object)
            update_object.give_weather_loot(self._remove_weather_types, False)
        if update_object in self._add_message_objects:
            self._add_message_objects.remove(update_object)
            update_object.give_weather_loot(self._add_weather_types, True)

    def flush_weather_aware_message(self, update_object):
        self._remove_message_objects.discard(update_object)
        self._add_message_objects.discard(update_object)

    def _send_weather_aware_messages(self, timeslice=True):
        start_time = time.clock()
        while True:
            if timeslice and time.clock() - start_time < self.WEATHER_AWARE_TIME_SLICE_SECONDS:
                if self._remove_message_objects:
                    loot_object = self._remove_message_objects.pop()
                    loot_object.give_weather_loot(self._remove_weather_types, False)
                elif self._add_message_objects:
                    loot_object = self._add_message_objects.pop()
                    loot_object.give_weather_loot(self._add_weather_types, True)
                else:
                    if self._weather_update_pending:
                        self.update_weather_type()
                    return

    def _send_ui_weather_message(self):
        weather_types = self._current_weather_types
        weather_override_map = self._forecasts[0].weather_ui_override if self._forecasts else None
        if weather_override_map is not None:
            weather_types = [weather_type for weather_type in weather_types if self.get_weather_category_for_type(weather_type) not in weather_override_map]
            weather_types.extend(weather_override_map.values())
        op = WeatherUpdateOp(weather_types)
        Distributor.instance().add_op_with_no_owner(op)

    def _send_ui_weather_forecast(self):
        op = WeatherForecastOp(self._forecasts)
        Distributor.instance().add_op_with_no_owner(op)

    def get_weather_outfit_change(self, resolver, reason=None):
        if resolver is None:
            return
        sim_info = resolver.get_participant(ParticipantType.Actor)
        if sim_info is None:
            return
        weather_outfit_tests = self.WEATHER_OUTFIT_TESTS.default_outfit_change_tests
        if reason is not None:
            for outfit_change_reason_test in self.WEATHER_OUTFIT_TESTS.outfit_change_reason_tests:
                if reason in outfit_change_reason_test.outfit_change_reasons:
                    weather_outfit_tests = outfit_change_reason_test.outfit_change_tests
                    break
        current_outfit = sim_info.get_current_outfit()
        for (category, test_set) in weather_outfit_tests.items():
            if test_set.run_tests(resolver):
                if current_outfit[0] == category:
                    return current_outfit
                return sim_info.get_random_outfit(outfit_categories=(category,))

    def process_weather_outfit_change(self, sim_infos):
        for sim_info in sim_infos:
            resolver = SingleSimResolver(sim_info)
            weather_outfit_category_and_index = self.get_weather_outfit_change(resolver)
            if weather_outfit_category_and_index is not None:
                sim_info.set_current_outfit(weather_outfit_category_and_index)

    def is_shady(self):
        if self._current_weather_types & self.COUNTS_AS_SHADE:
            return True
        return False

    def adjust_weather_for_set_season(self, interp_time):
        self._forecasts.clear()
        self._next_weather_event_time = DATE_AND_TIME_ZERO
        self._last_op = WeatherSeasons_pb2.SeasonWeatherInterpolations()
        start_time = services.time_service().sim_now
        current_snow_accumulation = self.get_weather_element_value(GroundCoverType.SNOW_ACCUMULATION, time=start_time, default=None)
        if current_snow_accumulation is None:
            return False
        if current_snow_accumulation == 0:
            del self._trans_info[int(GroundCoverType.SNOW_ACCUMULATION)]
            op = WeatherEventOp(WeatherSeasons_pb2.SeasonWeatherInterpolations())
            op.populate_op(GroundCoverType.SNOW_ACCUMULATION, 0, start_time, 0, start_time)
            Distributor.instance().add_op_with_no_owner(op)
            return False
        if current_snow_accumulation == 1.0:
            current_snow_accumulation = -1.0
        end_time = start_time + create_time_span(minutes=interp_time/2)
        self._trans_info[int(GroundCoverType.SNOW_ACCUMULATION)] = WeatherElementTuple(current_snow_accumulation, start_time, 0, end_time)
        op = WeatherEventOp(WeatherSeasons_pb2.SeasonWeatherInterpolations())
        op.populate_op(GroundCoverType.SNOW_ACCUMULATION, current_snow_accumulation, start_time, 0, end_time)
        Distributor.instance().add_op_with_no_owner(op)
        return True

    def create_lightning_collectible_alarm(self, delay_time_span, location):
        if self._lightning_collectible_alarm is not None:
            return

        def create_lightning_collectible(location):
            LightningStrike.create_collectible_from_lightning_strike(location)
            self._lightning_collectible_alarm = None

        self._lightning_collectible_alarm = alarms.add_alarm(self, delay_time_span, lambda _: create_lightning_collectible(location))
