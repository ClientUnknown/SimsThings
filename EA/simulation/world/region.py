from fishing.fishing_data import TunableFishingDataSnippetfrom seasons.seasons_enums import SeasonType, SeasonParametersfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableMapping, TunableRegionDescription, TunableReference, TunableList, Tunable, TunableEnumEntry, TunableTuple, TunableRange, OptionalTunablefrom sims4.tuning.tunable_base import ExportModes, GroupNamesfrom tunable_time import TunableTimeOfDayfrom weather.weather_forecast import TunableWeatherSeasonalForecastsReferenceimport servicesimport sims4.logimport taglogger = sims4.log.Logger('Region')
@staticmethod
def verify_seasonal_parameters(instance_class, tunable_name, source, value, **kwargs):
    for (season_param_type, param_values) in value.items():
        timings = list((pv.season.value + pv.time_in_season) % len(SeasonType) for pv in param_values)
        sorted_timings = sorted(timings)
        start_idx = timings.index(sorted_timings[0])
        for (i, sorted_value) in enumerate(sorted_timings):
            idx_in_original = (start_idx + i) % len(timings)
            if timings[idx_in_original] != sorted_value:
                logger.error('Incorrect timing order detected! {} appears out of place for {}@{} in {} params.', param_values[idx_in_original].season, param_values[idx_in_original].time_in_season, str(instance_class), season_param_type)

class Region(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.region_manager()):
    REGION_DESCRIPTION_TUNING_MAP = TunableMapping(description='\n        A mapping between Catalog region description and tuning instance. This\n        way we can find out what region description the current zone belongs to\n        at runtime then grab its tuning instance.\n        ', key_type=TunableRegionDescription(description='\n            Catalog-side Region Description.\n            ', pack_safe=True, export_modes=ExportModes.All), value_type=TunableReference(description="\n            Region Tuning instance. This is retrieved at runtime based on what\n            the active zone's region description is.\n            ", pack_safe=True, manager=services.region_manager(), export_modes=ExportModes.All), key_name='RegionDescription', value_name='Region', tuple_name='RegionDescriptionMappingTuple', export_modes=ExportModes.All)
    INSTANCE_TUNABLES = {'gallery_download_venue_map': TunableMapping(description='\n            A map from gallery venue to instanced venue. We need to be able to\n            convert gallery venues into other venues that are only compatible\n            with that region.\n            ', key_type=TunableReference(description='\n                A venue type that exists in the gallery.\n                ', manager=services.venue_manager(), export_modes=ExportModes.All), value_type=TunableReference(description='\n                The venue type that the gallery venue will become when it is\n                downloaded into this region.\n                ', manager=services.venue_manager(), export_modes=ExportModes.All, pack_safe=True), key_name='gallery_venue_type', value_name='region_venue_type', tuple_name='GalleryDownloadVenueMappingTuple', export_modes=ExportModes.All), 'compatible_venues': TunableList(description='\n            A list of venues that are allowed to be set by the player in this\n            region.\n            ', tunable=TunableReference(description='\n                A venue that the player can set in this region.\n                ', manager=services.venue_manager(), export_modes=ExportModes.All, pack_safe=True), export_modes=ExportModes.All), 'tags': TunableList(description='\n            Tags that are used to group regions. Destination Regions will\n            likely have individual tags, but Home/Residential Regions will\n            share a tag.\n            ', tunable=TunableEnumEntry(description='\n                A Tag used to group this region. Destination Regions will\n                likely have individual tags, but Home/Residential Regions will\n                share a tag.\n                ', tunable_type=tag.Tag, default=tag.Tag.INVALID, pack_safe=True)), 'region_buffs': TunableList(description='\n            A list of buffs that are added on Sims while they are instanced in\n            this region.\n            ', tunable=TunableReference(description='\n                A buff that exists on Sims while they are instanced in this\n                region.\n                ', manager=services.buff_manager(), pack_safe=True)), 'store_travel_group_placed_objects': Tunable(description='\n            If checked, any placed objects while in a travel group will be returned to household inventory once\n            travel group is disbanded.\n            ', tunable_type=bool, default=False), 'travel_group_build_disabled_tooltip': TunableLocalizedString(description='\n            The string that will appear in the tooltip of the grayed out build\n            mode button if build is being disabled because of a travel group in\n            this region.\n            ', allow_none=True, export_modes=ExportModes.All), 'sunrise_time': TunableTimeOfDay(description='\n            The time, in Sim-time, the sun rises in this region.\n            ', default_hour=6, tuning_group=GroupNames.TIME), 'seasonal_sunrise_time': TunableMapping(description='\n            A mapping between season and sunrise time.  If the current season\n            is not found then we will default to the tuned sunrise time.\n            ', key_type=TunableEnumEntry(description='\n                The season.\n                ', tunable_type=SeasonType, default=SeasonType.SUMMER), value_type=TunableTimeOfDay(description='\n                The time, in Sim-time, the sun rises in this region, in this\n                season.\n                ', default_hour=6, tuning_group=GroupNames.TIME)), 'sunset_time': TunableTimeOfDay(description='\n            The time, in Sim-time, the sun sets in this region.\n            ', default_hour=20, tuning_group=GroupNames.TIME), 'seasonal_sunset_time': TunableMapping(description='\n            A mapping between season and sunset time.  If the current season\n            is not found then we will default to the tuned sunset time.\n            ', key_type=TunableEnumEntry(description='\n                The season.\n                ', tunable_type=SeasonType, default=SeasonType.SUMMER), value_type=TunableTimeOfDay(description='\n                The time, in Sim-time, the sun sets in this region, in this\n                season.\n                ', default_hour=20, tuning_group=GroupNames.TIME)), 'provides_sunlight': Tunable(description='\n            If enabled, this region provides sunlight between the tuned Sunrise\n            Time and Sunset Time. This is used for gameplay effect (i.e.\n            Vampires).\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.TIME), 'weather': TunableMapping(description='\n            Forecasts for this region for the various seasons\n            ', key_type=TunableEnumEntry(description='\n                The Season.\n                ', tunable_type=SeasonType, default=SeasonType.SPRING), value_type=TunableWeatherSeasonalForecastsReference(description='\n                The forecasts for the season by part of season\n                ', pack_safe=True)), 'weather_supports_fresh_snow': Tunable(description='\n            If enabled, this region supports fresh snow.\n            ', tunable_type=bool, default=True), 'seasonal_parameters': TunableMapping(description='\n            ', key_type=TunableEnumEntry(description='\n                The parameter that we wish to change.\n                ', tunable_type=SeasonParameters, default=SeasonParameters.LEAF_ACCUMULATION), value_type=TunableList(description='\n                A list of the different seasonal parameter changes that we want to\n                send over the course of a year.\n                ', tunable=TunableTuple(season=TunableEnumEntry(description='\n                        The Season that this change is in.\n                        ', tunable_type=SeasonType, default=SeasonType.SPRING), time_in_season=TunableRange(description='\n                        The time within the season that this will occur.\n                        ', tunable_type=float, minimum=0.0, maximum=1.0, default=0.0), value=Tunable(description='\n                        The value that we will set this parameter to in the\n                        season\n                        ', tunable_type=float, default=0.0))), verify_tunable_callback=verify_seasonal_parameters), 'fishing_data': OptionalTunable(description='\n            If enabled, define all of the data for fishing locations in this region.\n            Only used if objects are tuned to use region fishing data.\n            ', tunable=TunableFishingDataSnippet())}

    @classmethod
    def _cls_repr(cls):
        return "Region: <class '{}.{}'>".format(cls.__module__, cls.__name__)

    @classmethod
    def is_region_compatible(cls, region_instance):
        if region_instance is cls or region_instance is None:
            return True
        for tag in cls.tags:
            if tag in region_instance.tags:
                return True
        return False

    @classmethod
    def is_sim_info_compatible(cls, sim_info):
        other_region = get_region_instance_from_zone_id(sim_info.zone_id)
        if cls.is_region_compatible(other_region):
            return True
        else:
            travel_group_id = sim_info.travel_group_id
            if travel_group_id:
                travel_group = services.travel_group_manager().get(travel_group_id)
                if travel_group is not None and not travel_group.played:
                    return True
        return False

    @classmethod
    def get_sunrise_time(cls):
        season_service = services.season_service()
        if season_service is None:
            return cls.sunrise_time
        return cls.seasonal_sunrise_time.get(season_service.season, cls.sunrise_time)

    @classmethod
    def get_sunset_time(cls):
        season_service = services.season_service()
        if season_service is None:
            return cls.sunset_time
        return cls.seasonal_sunset_time.get(season_service.season, cls.sunset_time)

def get_region_instance_from_zone_id(zone_id):
    region_description_id = get_region_description_id_from_zone_id(zone_id)
    if region_description_id is None:
        return
    region_instance = Region.REGION_DESCRIPTION_TUNING_MAP.get(region_description_id)
    return region_instance

def get_region_description_id_from_zone_id(zone_id):
    neighborhood_proto = services.get_persistence_service().get_neighborhood_proto_buf_from_zone_id(zone_id)
    if neighborhood_proto is None:
        return
    return neighborhood_proto.region_id

def get_region_instance_from_world_id(world_id):
    for zone_pb in services.get_persistence_service().zone_proto_buffs_gen():
        if zone_pb.world_id == world_id:
            return get_region_instance_from_zone_id(zone_pb.zone_id)
