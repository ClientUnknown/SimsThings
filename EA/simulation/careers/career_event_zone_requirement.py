from sims4.random import weighted_random_itemfrom sims4.tuning.tunable import AutoFactoryInit, TunableLotDescription, TunableVariant, HasTunableSingletonFactory, TunableReference, TunableList, TunableTuple, Tunable, TunableRange, TunableHouseDescription, OptionalTunablefrom world.lot import get_lot_id_from_instance_id, Lotimport build_buyimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('CareerEventZone')
class RequiredCareerEventZoneTunableVariant(TunableVariant):
    __slots__ = ()

    def __init__(self, **kwargs):
        super().__init__(any=RequiredCareerEventZoneAny.TunableFactory(), home_zone=RequiredCareerEventZoneHome.TunableFactory(), lot_description=RequiredCareerEventZoneLotDescription.TunableFactory(), random_lot=RequiredCareerEventZoneRandom.TunableFactory(), default='any', **kwargs)

class RequiredCareerEventZone(HasTunableSingletonFactory, AutoFactoryInit):

    def get_required_zone_id(self, sim_info):
        raise NotImplementedError

    def is_zone_id_valid(self, zone_id):
        return self.get_required_zone_id() == zone_id

class RequiredCareerEventZoneAny(RequiredCareerEventZone):

    def get_required_zone_id(self, sim_info):
        pass

    def is_zone_id_valid(self, zone_id):
        return True

class RequiredCareerEventZoneHome(RequiredCareerEventZone):

    def get_required_zone_id(self, sim_info):
        return sim_info.household.home_zone_id

class RequiredCareerEventZoneLotDescription(RequiredCareerEventZone):
    FACTORY_TUNABLES = {'lot_description': TunableLotDescription(description='\n            Lot description of required zone.\n            '), 'house_description': OptionalTunable(description='\n            If tuned, this house description will be used for this career event.\n            For example, for the acting career loads into the same lot but different\n            houses (studio sets). \n            ', tunable=TunableHouseDescription(description='\n                House description used for this career event.\n                '))}

    def get_required_zone_id(self, sim_info):
        lot_id = get_lot_id_from_instance_id(self.lot_description)
        if self.house_description is not None:
            for zone_proto in services.get_persistence_service().zone_proto_buffs_gen():
                if zone_proto.lot_description_id == self.lot_description:
                    zone_proto.pending_house_desc_id = self.house_description
                    break
        zone_id = services.get_persistence_service().resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=True)
        return zone_id

class ZoneTestNpc(HasTunableSingletonFactory):

    def is_valid_zone(self, zone_proto):
        household = services.household_manager().get(zone_proto.household_id)
        return household is not None and not household.is_player_household

class ZoneTestActivePlayer(HasTunableSingletonFactory):

    def is_valid_zone(self, zone_proto):
        return zone_proto.household_id == services.active_household_id()

class ZoneTestOwnedByHousehold(HasTunableSingletonFactory):

    def is_valid_zone(self, zone_proto):
        return zone_proto.household_id != 0

class ZoneTestActiveZone(HasTunableSingletonFactory):

    def is_valid_zone(self, zone_proto):
        return zone_proto.zone_id == services.current_zone_id()

class ZoneTestIsPlex(HasTunableSingletonFactory):

    def is_valid_zone(self, zone_proto):
        return services.get_plex_service().is_zone_a_plex(zone_proto.zone_id)

class ZoneTestVenueType(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'venue_types': TunableList(description='\n            If the venue type is in this list, the test passes.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.VENUE), pack_safe=True))}

    def is_valid_zone(self, zone_proto):
        venue_type_id = build_buy.get_current_venue(zone_proto.zone_id)
        return venue_type_id in (venue.guid64 for venue in self.venue_types)

class RequiredCareerEventZoneRandom(RequiredCareerEventZone):
    FORBIDDEN = 'FORBIDDEN'
    FACTORY_TUNABLES = {'random_weight_terms': TunableList(description='\n            A list of tests to use and the weights to add for each test.\n            By default, zones start with a weight of 1.0 and this can be\n            increased through these tests.\n            ', tunable=TunableTuple(test=TunableVariant(belongs_to_active_player=ZoneTestActivePlayer.TunableFactory(), is_owned_by_any_household=ZoneTestOwnedByHousehold.TunableFactory(), is_npc_household=ZoneTestNpc.TunableFactory(), venue_type=ZoneTestVenueType.TunableFactory(), is_active_zone=ZoneTestActiveZone.TunableFactory(), is_plex=ZoneTestIsPlex.TunableFactory(), default='venue_type'), weight=TunableVariant(add_weight=TunableRange(description='\n                        The amount of extra weight to add to the probability of zones\n                        that pass this test.\n                        ', tunable_type=float, default=1.0, minimum=0.0), locked_args={'forbid': FORBIDDEN}, default='add_weight'), negate=Tunable(description='\n                    If checked, extra weight will be applied to zones that do NOT\n                    pass this test, instead of zones that do pass.\n                    ', tunable_type=bool, default=False)))}

    def _get_random_weight(self, zone_proto):
        weight = 1.0
        for random_weight_term in self.random_weight_terms:
            if random_weight_term.negate ^ random_weight_term.test.is_valid_zone(zone_proto):
                if random_weight_term.weight == self.FORBIDDEN:
                    return 0.0
                weight += random_weight_term.weight
        return weight

    def get_required_zone_id(self, sim_info):
        zone_ids = [(self._get_random_weight(zone_proto), zone_proto.zone_id) for zone_proto in services.get_persistence_service().zone_proto_buffs_gen()]
        zone_id = weighted_random_item(zone_ids)
        if zone_id is None:
            logger.warn('Failed to find any zones that were not forbidden for career event travel with terms: {}', self.random_weight_terms, owner='bhill')
            return
        return zone_id
