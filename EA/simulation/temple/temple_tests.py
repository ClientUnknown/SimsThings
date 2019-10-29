from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import cached_testfrom interactions import ParticipantTypeObject, ParticipantTypeSinglefrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, TunableReference, Tunablefrom temple.temple_utils import TempleUtilsimport build_buyimport servicesimport sims4.resources
class IsTriggerInteractionTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'trap_object': TunableEnumEntry(description='\n            The trap object to test against. For the room this object is in, if\n            the tuned affordance on this object is the trigger interaction, the\n            test will Pass. Otherwise, the test will Fail.\n            ', tunable_type=ParticipantTypeObject, default=ParticipantTypeObject.Object), 'affordance_to_test': TunableReference(description='\n            The affordance to test against. For the room the tuned object is in,\n            if this affordance for the tuned object is the trigger interaction,\n            the test will pass. Otherwise it will fail.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',)), 'negate': Tunable(description="\n            If checked, the outcome of this test will be negated. The test will\n            still fail, regardless of this check box, if this isn't a temple\n            zone or if the tuned trap_object participant doesn't exist.\n            ", tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'trap_objects': self.trap_object}

    def __call__(self, trap_objects=()):
        trap = next(iter(trap_objects), None)
        if trap is None:
            return TestResult(False, 'No trap object found. Check the participant type {}.', self.trap_object, tooltip=self.tooltip)
        zone_director = TempleUtils.get_temple_zone_director()
        if zone_director is None:
            return TestResult(False, 'Not in a temple zone.', tooltip=self.tooltip)
        result = self._get_result(zone_director, trap)
        if self.negate:
            if result:
                return TestResult(False, 'Test passed but negate is checked.', tooltip=self.tooltip)
            else:
                return TestResult.TRUE
        return result

    def _get_result(self, zone_director, trap):
        plex_id = build_buy.get_location_plex_id(trap.zone_id, trap.position, trap.level)
        if plex_id != zone_director.current_room:
            return TestResult(False, 'The trap is not in the current temple room.')
        room_data = zone_director.room_data[plex_id]
        trap_object = trap
        if trap.is_part:
            trap_object = trap_object.part_owner
        if trap_object is not room_data.trigger_object:
            return TestResult(False, 'Not the correct trigger object.', tooltip=self.tooltip)
        if self.affordance_to_test is not room_data.trigger_interaction:
            return TestResult(False, 'This is the correct object but not the correct interaction.', tooltip=self.tooltip)
        return TestResult.TRUE

class IsInCurrentTempleRoomTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description="\n            The subject whose position will be used to determine if they are\n            inside the current temple room. Test will pass if they are, and fail\n            if they aren't.\n            ", tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), 'negate': Tunable(description="\n            If checked, the outcome of this test will be negated. The test will\n            still fail, regardless of this check box, if this isn't a temple\n            zone or if the tuned trap_object participant doesn't exist.\n            ", tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'subjects': self.subject}

    def __call__(self, subjects=()):
        subject = next(iter(subjects), None)
        if subject is None:
            return TestResult(False, 'Subject not found. Check participant type {}.', self.subject, tooltip=self.tooltip)
        zone_director = TempleUtils.get_temple_zone_director()
        if zone_director is None:
            return TestResult(False, 'Not in a temple zone.', tooltip=self.tooltip)
        return self._get_result(zone_director, subject)

    def _get_result(self, zone_director, subject):
        plex_id = build_buy.get_location_plex_id(services.current_zone_id(), subject.position, subject.level)
        if plex_id != zone_director.current_room:
            if self.negate:
                return TestResult.TRUE
            return TestResult(False, 'Failed current room check. Current room: {}, subject room: {}', zone_director.current_room, plex_id, tooltip=self.tooltip)
        if self.negate:
            return TestResult(False, 'Test passed but negate is checked.', tooltip=self.tooltip)
        return TestResult.TRUE
