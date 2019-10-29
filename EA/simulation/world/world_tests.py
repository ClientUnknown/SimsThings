from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import TestEvent, cached_testfrom event_testing.test_variants import UseDefaultOfflotToleranceFactoryfrom interactions import ParticipantType, ParticipantTypeActorTargetSim, ParticipantTypeSinglefrom objects import ALL_HIDDEN_REASONSfrom routing import SurfaceTypefrom sims4.geometry import test_point_in_polygonfrom sims4.tuning.tunable import HasTunableSingletonFactory, TunableEnumEntry, TunableFactory, TunableTuple, OptionalTunable, Tunable, TunableReference, TunablePackSafeReference, TunableVariant, AutoFactoryInit, TunableThreshold, TunableRange, TunableList, TunableEnumSetfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListfrom world.terrain_enums import TerrainTagimport servicesimport simsimport sims4import terrainlogger = sims4.log.Logger('World Tests')
class LocationTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    test_events = (TestEvent.SimTravel,)
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            Who or what to apply this \n            test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor)}

    @TunableFactory.factory_option
    def location_tests(is_outside=True, is_natural_ground=True, is_in_slot=True, is_venue_type=True, is_on_active_lot=True, in_common_area=True, is_fire_allowed=True, is_on_level=True, has_terrain_tag=True, valid_surface_types=True):
        locked_args = {}
        if not is_outside:
            locked_args['is_outside'] = None
        if not is_natural_ground:
            locked_args['is_natural_ground'] = None
        if not is_in_slot:
            locked_args['is_in_slot'] = None
        if not is_venue_type:
            locked_args['is_venue_type'] = None
        if not is_on_active_lot:
            locked_args['is_on_active_lot'] = None
        if not in_common_area:
            locked_args['in_common_area'] = None
        if not is_fire_allowed:
            locked_args['is_fire_allowed'] = None
        if not is_on_level:
            locked_args['is_on_level'] = None
        if not has_terrain_tag:
            locked_args['has_terrain_tag'] = None
        if not valid_surface_types:
            locked_args['valid_surface_types'] = None
        return TunableTuple(is_outside=OptionalTunable(description='\n                If checked, will verify if the subject of the test is outside \n                (no roof over its head) \n                If unchecked, will verify the subject of the test is not \n                outside.\n                ', disabled_name="Don't_Test", tunable=Tunable(bool, True)), has_terrain_tag=OptionalTunable(description='\n                If checked, will verify the subject of the test is currently on\n                the tuned terrain tag.\n                ', disabled_name="Don't_Test", tunable=TunableTuple(description=',\n                    A set of terrain tags required for this test to pass.\n                    ', terrain_tags=TunableEnumSet(description='\n                        A set of terrain tags. Only one of these tags needs to be\n                        present at this location. Although it is not tunable, there\n                        is a threshold weight underneath which a terrain tag will\n                        not appear to be present.\n                        ', enum_type=TerrainTag, enum_default=TerrainTag.INVALID), negate=Tunable(description='\n                        If checked, the test will be inverted. In other words,\n                        the test will fail if at least one tag is detected at\n                        this location.\n                        ', tunable_type=bool, default=False))), is_natural_ground=OptionalTunable(description='\n                If checked, will verify the subject of the test is on natural \n                ground (no floor tiles are under him).\n                Otherwise, will verify the subject of the test is not on \n                natural ground.\n                ', disabled_name="Don't_Test", tunable=Tunable(bool, True)), is_in_slot=OptionalTunable(description='\n                If enabled will test if the object is attacked/deattached to\n                any of possible tuned slots.\n                If you tune a slot type set the test will test if the object \n                is slotted or not slotted into into any of those types. \n                ', disabled_name="Don't_Test", tunable=TunableTuple(description='\n                    Test if an object is current slotted in any of a possible\n                    list of slot types.\n                    Empty slot type set is allowed for testing for slotted or\n                    not slotted only.\n                    ', slot_test_type=TunableVariant(description='\n                        Strategy to test the slots:\n                        Any Slot - is the object in any slot\n                        Surface Slot - is object is in a surface slot\n                        Specific Slot - is the object in specific list of slots\n                        ', any_slot=SlotTestType.TunableFactory(), surface_slot=SurfaceSlotTest.TunableFactory(), specific_slot=SpecificSlotTest.TunableFactory(), default='any_slot'))), is_venue_type=OptionalTunable(description='\n                If checked, will verify if the subject is at a venue of the\n                specified type.\n                ', disabled_name="Don't_Test", tunable=TunableTuple(description='\n                    Venue type required for this test to pass.\n                    ', venue_type=TunablePackSafeReference(description='\n                        Venue type to test against.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.VENUE)), negate=Tunable(description='\n                        If enabled, the test will return true if the subject\n                        IS NOT at a venue of the specified type.\n                        ', tunable_type=bool, default=False))), is_on_active_lot=OptionalTunable(description='\n                If disabled the test will not be used.\n                If enabled and checked, the test will pass if the subject is\n                on the active lot. (their center is within the lot bounds)\n                If enabled and not checked, the test will pass if the subject is \n                outside of the active lot.\n                \n                For example, Ask To Leave is tuned with this enabled and checked\n                for the TargetSim. You can only ask someone to leave if they\n                are actually on the active lot, but not if they are wandering\n                around in the open streets.\n                ', disabled_name="Don't_Test", enabled_name='Is_or_is_not_on_active_lot', tunable=TunableTuple(is_or_is_not_on_active_lot=Tunable(description='\n                        If checked then the test will pass if the subject is on\n                        the active lot.\n                        ', tunable_type=bool, default=True), tolerance=TunableVariant(explicit=Tunable(description='\n                            The tolerance from the edge of the lot that the\n                            location test will use in order to determine if the\n                            test target is considered on lot or not.\n                            ', tunable_type=int, default=0), use_default_tolerance=UseDefaultOfflotToleranceFactory(description='\n                            Use the default tuned global offlot tolerance tuned\n                            in objects.components.statistic_component.Default Off Lot.\n                            '), default='explicit'), include_spawn_point=Tunable(description="\n                        If set to true, we will consider the lot's spawn point as part of the active lot.\n                        ", tunable_type=bool, default=False))), in_common_area=OptionalTunable(description='\n                If checked, will verify the subject is in the common area\n                of an apartment.  If unchecked will verify the subject is not.\n                ', disabled_name="Don't_Test", tunable=Tunable(tunable_type=bool, default=True)), is_fire_allowed=OptionalTunable(description="\n                If checked, will verify if fire is possible at the subject's position. \n                If unchecked, will pass if fire is not possible.\n                If not enabled, doesn't care either way.\n                ", disabled_name="Don't_Test", tunable=Tunable(tunable_type=bool, default=True)), is_on_level=OptionalTunable(description="\n                If enabled, we check the participant's current level against\n                the tuned threshold.  In the case of sims in pools, the effective\n                level will be that of the surface of the pool, not the bottom.\n                ", disabled_name="Don't_Test", tunable=TunableThreshold(value=Tunable(int, 0))), valid_surface_types=OptionalTunable(description='\n                If enabled, we will test the surface type of the subject\n                against prohibited or required surface types.\n                ', disabled_name="Don't_Test", enabled_name='Test_Surface_Types', tunable=TunableWhiteBlackList(description='    \n                    Required and Prohibited Surface Types. \n                    ', tunable=TunableEnumEntry(description='\n                        Surface Type the object is placed on.\n                        ', tunable_type=SurfaceType, default=SurfaceType.SURFACETYPE_WORLD, invalid_enums=(SurfaceType.SURFACETYPE_UNKNOWN,)))), locked_args=locked_args)

    def get_expected_args(self):
        return {'test_target': self.subject}

    @staticmethod
    def test_is_on_active_lot(test_data, target_pos):
        success = False
        current_zone = services.current_zone()
        if current_zone is None:
            return success
        want_target_on_lot = test_data.is_or_is_not_on_active_lot
        is_target_on_lot = current_zone.lot.is_position_on_lot(target_pos, test_data.tolerance)
        if test_data.include_spawn_point:
            arrival_spawn_point = current_zone.active_lot_arrival_spawn_point
            if arrival_spawn_point is not None:
                is_target_on_spawn_point = test_point_in_polygon(target_pos, arrival_spawn_point.get_footprint_polygon())
                is_target_on_lot |= is_target_on_spawn_point
        if want_target_on_lot == is_target_on_lot:
            success = True
        return success

    @cached_test
    def __call__(self, test_target=None):
        for target in test_target:
            if isinstance(target, sims.sim_info.SimInfo):
                target = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                if target is None:
                    return TestResult(False, 'Testing Location an uninstantiated Sim.', tooltip=self.tooltip)
            if self.location_tests.is_outside is not None:
                is_outside = not target.is_hidden() and target.is_outside
                if self.location_tests.is_outside != is_outside:
                    return TestResult(False, 'Object failed outside location test', tooltip=self.tooltip)
            if self.location_tests.is_natural_ground is not None and self.location_tests.is_natural_ground != target.is_on_natural_ground():
                return TestResult(False, 'Object failed natural ground location test.', tooltip=self.tooltip)
            if self.location_tests.is_in_slot is not None:
                (slot_test_passed, slot_test_reason) = self.location_tests.is_in_slot.slot_test_type.run_slot_test(target)
                if not slot_test_passed:
                    return TestResult(False, slot_test_reason, tooltip=self.tooltip)
            if self.location_tests.is_venue_type is not None:
                required_venue_type = self.location_tests.is_venue_type.venue_type
                venue_zone = services.get_zone(target.zone_id)
                if venue_zone is None:
                    return TestResult(False, 'Object is not in an active zone', tooltip=self.tooltip)
                venue = venue_zone.venue_service.venue
                if self.location_tests.is_venue_type.negate:
                    if required_venue_type is not None and isinstance(venue, required_venue_type):
                        return TestResult(False, 'Object failed venue type test.', tooltip=self.tooltip)
                elif required_venue_type is None or not isinstance(venue, self.location_tests.is_venue_type.venue_type):
                    return TestResult(False, 'Object failed venue type test.', tooltip=self.tooltip)
            if self.location_tests.is_on_active_lot is not None and not self.test_is_on_active_lot(self.location_tests.is_on_active_lot, target.position):
                return TestResult(False, 'Object failed on active lot test', tooltip=self.tooltip)
            if self.location_tests.is_fire_allowed is not None:
                fire_service = services.get_fire_service()
                allowed = fire_service.is_fire_allowed(target.transform, target.routing_surface)
                if self.location_tests.is_fire_allowed != allowed:
                    return TestResult(False, 'Object failed is_fire_allowed test', tooltip=self.tooltip)
            if self.location_tests.in_common_area is not None:
                plex_service = services.get_plex_service()
                if self.location_tests.in_common_area != plex_service.is_active_zone_a_plex() and plex_service.get_plex_zone_at_position(target.position, target.level) is None:
                    return TestResult(False, 'Object failed in common area test.', tooltip=self.tooltip)
            if self.location_tests.is_on_level is not None:
                level = target.level
                if target.in_pool:
                    level += 1
                if not (target.is_sim and self.location_tests.is_on_level.compare(level)):
                    return TestResult(False, 'Object not on required level.', tooltip=self.tooltip)
            if self.location_tests.has_terrain_tag is not None:
                position = target.position
                is_terrain_tag_at_position = terrain.is_terrain_tag_at_position(position.x, position.z, self.location_tests.has_terrain_tag.terrain_tags, level=target.routing_surface.secondary_id)
                if self.location_tests.has_terrain_tag.negate:
                    if is_terrain_tag_at_position:
                        return TestResult(False, 'Object on required terrain tag, but negate is checked', tooltip=self.tooltip)
                elif not is_terrain_tag_at_position:
                    return TestResult(False, 'Object not on required terrain tag.', tooltip=self.tooltip)
            if not target.routing_surface is None:
                if not self.location_tests.valid_surface_types.test_item(target.routing_surface.type):
                    return TestResult(False, 'Object routing surface is incorrect.', tooltip=self.tooltip)
            return TestResult(False, 'Object routing surface is incorrect.', tooltip=self.tooltip)
        return TestResult.TRUE

class SlotTestType(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'require_slotted': Tunable(description='\n            If checked, return success if the object is slotted\n            If unchecked, test the absense of slotting.\n            ', tunable_type=bool, default=True)}

    def run_slot_test(self, target):
        if target.parent is not None:
            return (self.require_slotted, 'Object failed slot test. Is in a slot.')
        return (not self.require_slotted, 'Object failed slot test. Is not in a slot.')

class SurfaceSlotTest(SlotTestType):

    def run_slot_test(self, target):
        if target.parent is not None:
            for slot in target.parent_slot.slot_types:
                if slot.is_surface:
                    return (self.require_slotted, 'Object failed surface slot test. Slot is a surface.')
        return (not self.require_slotted, 'Object failed surface slot test. Surface slot not found.')

class SpecificSlotTest(SlotTestType):
    FACTORY_TUNABLES = {'specific_slot_set': TunableReference(description='\n            Set of slots the object may be attached to.\n            ', manager=services.slot_type_set_manager())}

    def run_slot_test(self, target):
        if target.parent is not None:
            for specified_slot in self.specific_slot_set.slot_types:
                for parent_slot in target.parent_slot.slot_types:
                    if parent_slot is specified_slot:
                        return (self.require_slotted, 'Object failed specified slot test. Specified slot was found.')
        return (not self.require_slotted, 'Object failed specified slot test. Specified slot was not found.')

class DistanceTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'threshold': TunableThreshold(description='\n            The distance threshold for this test. The distance between the\n            subject and the target must satisfy this condition in order of the\n            test to pass.\n            '), 'level_modifier': TunableVariant(description='\n            Determine how difference in levels affects distance. A modifier of\n            10, for example, would mean that the distance between two objects is\n            increased by 10 meters for every floor between them.\n            ', specific=TunableRange(description='\n                A meter modifier to add to the distance multiplied by the number\n                of floors between subject and target.\n                ', tunable_type=float, minimum=0, default=8), locked_args={'no_modifier': 0, 'infinite': None}, default='no_modifier'), 'subject': TunableEnumEntry(description='\n            The subject of the test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'target': TunableEnumEntry(description='\n            The target of the test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object)}

    def get_expected_args(self):
        return {'subjects': self.subject, 'targets': self.target}

    @cached_test
    def __call__(self, subjects=(), targets=()):
        for subject in subjects:
            if subject.is_sim:
                subject = subject.get_sim_instance()
            for target in targets:
                if target.is_sim:
                    target = target.get_sim_instance()
                if subject is None or target is None:
                    distance = sims4.math.MAX_INT32
                else:
                    distance = (target.position - subject.position).magnitude()
                    level_difference = abs(subject.routing_surface.secondary_id - target.routing_surface.secondary_id)
                    if level_difference:
                        if self.level_modifier is None:
                            distance = sims4.math.MAX_INT32
                        else:
                            distance += level_difference*self.level_modifier
                if not self.threshold.compare(distance):
                    return TestResult(False, 'Distance test failed.', tooltip=self.tooltip)
        return TestResult.TRUE

    def validate_tuning_for_objective(self, objective):
        if self.threshold.value == 0:
            logger.error('Error in objective {} in DistanceTest. Threshold has value of 0.', objective)

class VenueAvailabilityTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    TEST_ANY_OWNERSHIP = 0
    TEST_SUBJECT_OWNERSHIP = 1
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            Who cares about the venues in the region. This paricipant will be\n            used to test for Region Compatibility if checked.\n            ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantType.Actor), 'venues': TunableList(description='\n            A list of venues that we want to be available. If there are no\n            venues in the world that match the types in this list, then this\n            test will Fail.\n            ', tunable=TunableReference(description='\n                A venue that we want to be available/unavailable.\n                ', manager=services.venue_manager(), pack_safe=True)), 'test_region_compatibility': Tunable(description="\n            If checked, venues in incompatible regions from the subjects'\n            region will be excluded and considered unavailable.\n            ", tunable_type=bool, default=False), 'ownership_test': OptionalTunable(description='\n            If enabled then when testing venue availability it will test the\n            ownership of the venue as tuned within.\n            \n            If disabled then no ownership test will be applied to the venue.\n            ', tunable=TunableVariant(description='\n                How to test the venue for ownership.\n                \n                If fail if owned by anyone is chosen then any lot owner will \n                cause that venue to be unavailable.\n                \n                If fail if owned by subject is chosen then any venue owned\n                by the subject will be considered unavailable.\n                ', fail_if_owned_by_anyone=TunableTuple(description='\n                    venues that are owned/lived-in by anyone will be excluded \n                    and considered unavailable.\n                    ', locked_args={'test_type': TEST_ANY_OWNERSHIP}), fail_if_owned_by_subject=TunableTuple(description='\n                    venues that are owned/lived in by the tuned subject will be \n                    excluded and considered unavailable.\n                    ', locked_args={'test_type': TEST_SUBJECT_OWNERSHIP}), default='fail_if_owned_by_anyone'), enabled_by_default=True)}

    def get_expected_args(self):
        return {'subjects': self.subject}

    @cached_test
    def __call__(self, subjects):
        import world
        current_region = world.region.get_region_instance_from_zone_id(subjects[0].zone_id)
        if self.test_region_compatibility and current_region is None:
            logger.error('VenueAvailabilityTest: Participant Type {} is not in a zone. Do you actually want to test region compatibility?', self.subject, owner='rmccord')
            return TestResult(False, 'Could not test for Region Compatibility.')
        venue_service = services.current_zone().venue_service
        persistence_service = services.get_persistence_service()
        travel_group_manager = services.travel_group_manager()
        subject_household_ids = set(subject.household_id for subject in subjects)
        for zone_id in venue_service.get_zones_for_venue_type_gen(*self.venues):
            zone_data = persistence_service.get_zone_proto_buff(zone_id)
            if zone_data is None:
                pass
            else:
                neighborhood_data = persistence_service.get_neighborhood_proto_buff(zone_data.neighborhood_id)
                if neighborhood_data is None:
                    pass
                else:
                    region_description_id = neighborhood_data.region_id
                    region_instance = world.region.Region.REGION_DESCRIPTION_TUNING_MAP.get(region_description_id)
                    if self.test_region_compatibility and not current_region.is_region_compatible(region_instance):
                        pass
                    elif self.ownership_test:
                        travel_group = travel_group_manager.get_travel_group_by_zone_id(zone_id)
                        if not (travel_group is not None and travel_group.played and self.ownership_test.test_type is self.TEST_ANY_OWNERSHIP):
                            if set(subjects).intersection(set(travel_group.sim_info_gen())):
                                pass
                            else:
                                lot_data = None
                                for lot_owner_data in neighborhood_data.lots:
                                    if zone_id == lot_owner_data.zone_instance_id:
                                        if self.ownership_test.test_type is self.TEST_SUBJECT_OWNERSHIP:
                                            owner_household_ids = set(x.household_id for x in lot_owner_data.lot_owner)
                                            if owner_household_ids.intersection(subject_household_ids):
                                                pass
                                            else:
                                                lot_data = lot_owner_data
                                                break
                                        else:
                                            lot_data = lot_owner_data
                                            break
                                if lot_data is not None and lot_data.lot_owner:
                                    pass
                                else:
                                    return TestResult.TRUE
                    else:
                        return TestResult.TRUE
        return TestResult(False, 'VenueAvailabilityTest: Venues are not available.', tooltip=self.tooltip)

class InHomeNeighborhoodTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant against which to run the HomeNeighborhood test.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeActorTargetSim.Actor)}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets):
        world_id = services.current_zone().open_street_id
        for participant in test_targets:
            home_world_id = participant.household.get_home_world_id()
            if home_world_id != world_id:
                return TestResult(False, 'Home world does not match the current world.', tooltip=self.tooltip)
        return TestResult.TRUE
