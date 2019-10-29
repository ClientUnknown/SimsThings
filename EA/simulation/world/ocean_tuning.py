from animation.animation_utils import StubActorfrom routing import SurfaceTypefrom sims.outfits.outfit_enums import OutfitChangeReasonfrom sims.sim_info_types import Age, SpeciesExtendedfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, TunableTuple, TunableInterval, TunableRange, TunableList, TunableEnumSet, TunableReference, OptionalTunablefrom tag import TunableTagimport services
class OceanTuning:
    BEACH_LOCATOR_TAG = TunableTag(description='\n        The tag we can use to get the beach locator definition.\n        ')
    OCEAN_DATA = TunableMapping(description='\n        The species-age mapping to ocean data. This defines what\n        ages and species can wade in the water and what the water level\n        restrictions are as well as beach portal access objects.\n        ', key_name='species', key_type=TunableEnumEntry(description='\n            The extended species that this data is for.\n            ', tunable_type=SpeciesExtended, default=SpeciesExtended.HUMAN), value_name='age_data', value_type=TunableList(description='\n            The ages and their data.\n            ', tunable=TunableTuple(description='\n                The ages and their ocean data.\n                ', ages=TunableEnumSet(description='\n                    The age of the actor.\n                    ', enum_type=Age), ocean_data=TunableTuple(description='\n                    The ocean data for this Age.\n                    ', wading_interval=TunableInterval(description='\n                        The wading interval for Sims at this age and species. The lower\n                        bound indicates the minimum water height required to apply the\n                        wading walkstyle, and the upper bound indicates the maximum\n                        height we can walk into the water until we can potentially\n                        swim.\n                        ', tunable_type=float, default_lower=0.1, default_upper=1.0, minimum=0.01), beach_portal_data=OptionalTunable(description='\n                        An optional portal definition to allow sims to swim in\n                        the ocean. Without this, Sims at this age and species\n                        cannot swim in the ocean.\n                        ', tunable=TunableReference(description='\n                            The portals this age/species will use to swim in the ocean.\n                            ', manager=services.snippet_manager(), class_restrictions=('PortalData',), pack_safe=True)), water_depth_error=TunableRange(description='\n                        The error, in meters, that we allow for the swimming beach\n                        portals.\n                        ', tunable_type=float, default=0.05, minimum=0.01), swimwear_change_water_depth=TunableRange(description="\n                        If a Sim's path includes water where the depth is at\n                        least the tuned value, in meters, they will switch into\n                        the outfit based on the outfit change reasonat the \n                        start of the path.\n                        ", tunable_type=float, default=0.1, minimum=0), swimwear_change_outfit_reason=OptionalTunable(description='\n                        If enabled, the outfit change reason that determines which outfit\n                        category a Sim automatically changes into when \n                        entering water.\n                        ', tunable=TunableEnumEntry(tunable_type=OutfitChangeReason, default=OutfitChangeReason.Invalid, invalid_enums=(OutfitChangeReason.Invalid,)))))))
    beach_locator_definition = None

    @staticmethod
    def get_beach_locator_definition():
        if OceanTuning.beach_locator_definition is None:
            for definition in services.definition_manager().get_definitions_for_tags_gen((OceanTuning.BEACH_LOCATOR_TAG,)):
                OceanTuning.beach_locator_definition = definition
                break
        return OceanTuning.beach_locator_definition

    @staticmethod
    def get_actor_ocean_data(actor):
        if actor.is_sim or not isinstance(actor, StubActor):
            return
        species_data = OceanTuning.OCEAN_DATA.get(actor.extended_species, None)
        if species_data is None:
            return
        actor_age = actor.age
        for age_data in species_data:
            if actor_age in age_data.ages:
                return age_data.ocean_data

    @staticmethod
    def get_actor_wading_interval(actor):
        ocean_data = OceanTuning.get_actor_ocean_data(actor)
        if ocean_data is not None:
            return ocean_data.wading_interval
        else:
            interval_actor = actor
            if actor.vehicle_component is not None:
                drivers = actor.get_users(sims_only=True)
                for driver in drivers:
                    if driver.posture.is_vehicle and driver.posture.target is actor:
                        interval_actor = driver
                        break
            ocean_data = OceanTuning.get_actor_ocean_data(interval_actor)
            if isinstance(actor, StubActor) or ocean_data is not None:
                return ocean_data.wading_interval

    @staticmethod
    def get_actor_swimwear_change_info(actor):
        ocean_data = OceanTuning.get_actor_ocean_data(actor)
        if ocean_data is not None:
            return (ocean_data.swimwear_change_water_depth, ocean_data.swimwear_change_outfit_reason)
        return (None, None)

    @staticmethod
    def make_depth_bounds_safe_for_surface_and_sim(routing_surface, sim, min_water_depth=None, max_water_depth=None):
        interval = OceanTuning.get_actor_wading_interval(sim)
        return OceanTuning.make_depth_bounds_safe_for_surface(routing_surface, wading_interval=interval, min_water_depth=min_water_depth, max_water_depth=max_water_depth)

    @staticmethod
    def make_depth_bounds_safe_for_surface(routing_surface, wading_interval=None, min_water_depth=None, max_water_depth=None):
        if routing_surface.type == SurfaceType.SURFACETYPE_WORLD:
            surface_min_water_depth = min_water_depth
            if wading_interval is not None:
                if max_water_depth is None:
                    surface_max_water_depth = wading_interval.upper_bound
                else:
                    surface_max_water_depth = min(wading_interval.upper_bound, max_water_depth)
                    surface_max_water_depth = 0
            else:
                surface_max_water_depth = 0
        elif routing_surface.type == SurfaceType.SURFACETYPE_POOL:
            if wading_interval is not None:
                if min_water_depth is None:
                    surface_min_water_depth = wading_interval.upper_bound
                else:
                    surface_min_water_depth = max(wading_interval.upper_bound, min_water_depth)
            else:
                surface_min_water_depth = min_water_depth
            surface_max_water_depth = max_water_depth
        else:
            surface_min_water_depth = min_water_depth
            surface_max_water_depth = max_water_depth
        return (surface_min_water_depth, surface_max_water_depth)
