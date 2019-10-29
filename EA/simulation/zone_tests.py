from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import TestEventfrom interactions import ParticipantTypeSingleSim, ParticipantTypefrom plex.plex_enums import PlexBuildingTypefrom sims4.tuning.tunable import TunableVariant, TunableTuple, TunableEnumEntry, OptionalTunable, Tunable, TunableReference, HasTunableSingletonFactory, AutoFactoryInit, TunableWorldDescriptionfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport build_buyimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('ZoneTests', default_owner='rmccord')
class ActiveZone(HasTunableSingletonFactory, AutoFactoryInit):

    def get_expected_args(self):
        return {}

    def get_zone_id(self):
        return services.current_zone_id()

class ParticipantHomeZone(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description="\n            Test against the participant's home zone. Townies' home zone will\n            be None.\n            ", tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor)}

    def get_expected_args(self):
        return {'subjects': self.participant}

    def get_zone_id(self, *, subjects):
        if not subjects:
            logger.error('Failed to resolve participant {}.', self.participant)
            return
        participant = subjects[0]
        return participant.household.home_zone_id

class PickInfoZone(HasTunableSingletonFactory, AutoFactoryInit):

    def get_expected_args(self):
        return {'context': ParticipantType.InteractionContext}

    def get_zone_id(self, *, context):
        if context is None or context.pick is None:
            logger.error('Zone Test failed to get interaction pick info.')
            return
        return context.pick.get_zone_id_from_pick_location()

class PickedZoneIds(HasTunableSingletonFactory, AutoFactoryInit):

    def get_expected_args(self):
        return {'picked_zone_ids': ParticipantType.PickedZoneId}

    def get_zone_id(self, *, picked_zone_ids):
        if not picked_zone_ids:
            logger.error('Zone Test could not find a picked zone id.')
            return
        return picked_zone_ids[0]

class _IsBusinessTest(HasTunableSingletonFactory):

    def __call__(self, zone_id):
        business_manager = services.business_service().get_business_manager_for_zone(zone_id=zone_id)
        return business_manager is not None

class _IsBusinessOpenTest(HasTunableSingletonFactory):

    def __call__(self, zone_id):
        business_manager = services.business_service().get_business_manager_for_zone(zone_id=zone_id)
        if business_manager is not None:
            return business_manager.is_open
        return False

class ZoneTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    test_events = (TestEvent.SimTravel,)
    FACTORY_TUNABLES = {'zone_source': TunableVariant(description='\n            Which zone we want to test.\n            ', use_current_zone=ActiveZone.TunableFactory(), use_pick_info=PickInfoZone.TunableFactory(), use_picked_zone_ids=PickedZoneIds.TunableFactory(), use_participant_home_zone=ParticipantHomeZone.TunableFactory(), default='use_current_zone'), 'zone_tests': TunableTuple(description='\n            The tests we wish to run on the zone in question.\n            ', venue_type=OptionalTunable(description="\n                If checked, will verify the zone's venue type is allowed or\n                disallowed.\n                ", disabled_name="Don't_Test", tunable=TunableWhiteBlackList(description="\n                    The zone's venue type must pass the whitelist and blacklist\n                    to pass the test.\n                    ", tunable=TunableReference(description='\n                        Allowed and disallowed venue types.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.VENUE), pack_safe=True))), is_apartment=OptionalTunable(description='\n                If checked, test will pass if the zone is an apartment. If\n                unchecked, test passes if the zone is NOT an apartment. Useful\n                 in aspiration tuning, to discriminate between property\n                types in tests of lot value. Allows "Own a House worth X" and\n                "Own an Apartment worth X"\n                ', disabled_name="Don't_Test", enabled_name='Is_or_is_not_apartment_zone', tunable=TunableTuple(description='\n                    Test whether the zone is an apartment or not.\n                    ', is_apartment=Tunable(description='\n                        If checked, test will pass if the zone is an apartment.\n                        If unchecked, test passes if the zone is NOT an\n                        apartment.\n                        ', tunable_type=bool, default=True), consider_penthouse_an_apartment=Tunable(description='\n                        If enabled, we will consider penthouses to be\n                        apartments when testing them against the apartment\n                        check.\n                        ', tunable_type=bool, default=True))), is_penthouse=OptionalTunable(description='\n                If enabled, test whether or not the current zone is a penthouse.\n                ', tunable=Tunable(description='\n                    If checked, the zone must be a penthouse. If unchecked, the\n                    zone cannot be a penthouse.\n                    ', tunable_type=bool, default=True)), zone_modifiers=OptionalTunable(description='\n                if enabled, we test the zone modifiers allowed or disallowed.\n                ', disabled_name="Don't_Test", tunable=TunableWhiteBlackList(description="\n                    The zone's modifiers must pass this whitelist and blacklist for the\n                    test to pass.\n                    ", tunable=TunableReference(description='\n                        Allowed and disallowed zone modifiers.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.ZONE_MODIFIER), pack_safe=True))), world_tests=OptionalTunable(description='\n                If enabled, we test if specified zone is or is not in the specified world(s)\n                ', tunable=TunableWhiteBlackList(description='\n                    Pass if zone is in one of the worlds in the whitelist,\n                    or fail if it is any of the worlds in the blacklist.\n                    ', tunable=TunableWorldDescription(description='\n                        World to check against.\n                        ', pack_safe=True))), business_tests=OptionalTunable(description='\n                If enabled, test if the specified zone is a business or not.\n                ', disabled_name="Don't_Test", tunable=TunableVariant(description='\n                    Test if the zone is a business, an open business, or a\n                    closed business.\n                    ', is_business=_IsBusinessTest.TunableFactory(), is_business_open=_IsBusinessOpenTest.TunableFactory(), default='is_business')))}

    def get_expected_args(self):
        return self.zone_source.get_expected_args()

    def __call__(self, *args, **kwargs):
        zone_id = self.zone_source.get_zone_id(**kwargs)
        if zone_id is None:
            return TestResult(False, "ZoneTest couldn't find a zone to test.", tooltip=self.tooltip)
        if self.zone_tests.venue_type is not None:
            venue_type_id = build_buy.get_current_venue(zone_id)
            venue_manager = services.venue_manager()
            venue_type = venue_manager.get(venue_type_id, None)
            venues = (venue_type,) if venue_type is not None else ()
            if not self.zone_tests.venue_type.test_collection(venues):
                return TestResult(False, 'Zone failed venue type white or black list {}', venue_type, tooltip=self.tooltip)
        if self.zone_tests.is_apartment is not None:
            plex_service = services.get_plex_service()
            if self.zone_tests.is_apartment.is_apartment != plex_service.is_zone_an_apartment(zone_id, consider_penthouse_an_apartment=self.zone_tests.is_apartment.consider_penthouse_an_apartment):
                return TestResult(False, 'Zone failed apartment test', tooltip=self.tooltip)
        if self.zone_tests.is_penthouse is not None:
            plex_service = services.get_plex_service()
            is_penthouse = plex_service.get_plex_building_type(zone_id) == PlexBuildingType.PENTHOUSE_PLEX
            if is_penthouse != self.zone_tests.is_penthouse:
                return TestResult(False, 'Zone failed penthouse test', tooltip=self.tooltip)
        if self.zone_tests.zone_modifiers is not None:
            zone_modifier_service = services.get_zone_modifier_service()
            zone_modifiers = zone_modifier_service.get_zone_modifiers(zone_id)
            if not self.zone_tests.zone_modifiers.test_collection(zone_modifiers):
                return TestResult(False, 'Zone failed to meet whitelist/blacklist for zone modifiers. ZoneId: {}, Mods: {}', zone_id, zone_modifiers, tooltip=self.tooltip)
        if self.zone_tests.world_tests is not None:
            world_id = services.get_persistence_service().get_world_id_from_zone(zone_id)
            world_desc_id = services.get_world_description_id(world_id)
            if world_desc_id == 0:
                return TestResult(False, 'Unable to determine world for Zone {}', zone_id)
            if not self.zone_tests.world_tests.test_item(world_desc_id):
                return TestResult(False, 'Zone {} failed to meet world requirements, is in {}, fails tests for {}', zone_id, world_desc_id, self.zone_tests.world_tests, tooltip=self.tooltip)
        if self.zone_tests.business_tests is not None:
            return self.zone_tests.business_tests(zone_id)
        return TestResult.TRUE
