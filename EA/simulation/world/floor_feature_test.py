from build_buy import FloorFeatureTypefrom event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import cached_testfrom interactions import ParticipantTypefrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.geometric import TunableDistanceSquaredfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntryimport build_buyimport servicesimport simsimport sims4logger = sims4.log.Logger('FloorFeatureTest')
class NearbyFloorFeatureTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'floor_feature': TunableEnumEntry(description="\n            The floor feature type that is required to be inside the radius_actor's\n            radius.\n            ", tunable_type=FloorFeatureType, default=FloorFeatureType.BURNT), 'radius': TunableDistanceSquared(description="\n            The radius, with the radius actor's position, that defines the area\n            within which the floor feature is valid.\n            ", default=5.0), 'radius_actor': TunableEnumEntry(description='\n            The Actor within whose radius the tuned floor feature must be in\n            for consideration.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor)}

    def floor_feature_exists_in_object_radius(self, radius_actors):
        zone_id = services.current_zone_id()
        floor_features = build_buy.list_floor_features(zone_id, self.floor_feature)
        for actor in radius_actors:
            for (ff_position, _) in floor_features:
                delta = ff_position - actor.position
                if delta.magnitude_squared() < self.radius:
                    return True
        return False

    def get_expected_args(self):
        return {'radius_actors': self.radius_actor}

    @cached_test
    def __call__(self, radius_actors=()):
        radius_objects = []
        SimInfo = sims.sim_info.SimInfo
        for radius_actor in radius_actors:
            if isinstance(radius_actor, SimInfo):
                radius_actor_object = radius_actor.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                if radius_actor_object is None:
                    logger.error('{} has a None value and cannot be used to determine a nearby floor feature test.', radius_actor)
                else:
                    radius_objects.append(radius_actor_object)
                    radius_objects.append(radius_actor)
            else:
                radius_objects.append(radius_actor)
        result = self.floor_feature_exists_in_object_radius(radius_objects)
        if not result:
            return TestResult(False, 'No Found Floor Features', tooltip=self.tooltip)
        return TestResult.TRUE
