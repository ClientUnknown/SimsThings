from event_testing.resolver import RESOLVER_PARTICIPANTfrom event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import cached_testfrom interactions import ParticipantTypeSingleSimfrom sims4.tuning.tunable import TunableEnumEntry, HasTunableSingletonFactory, AutoFactoryInit, TunableVariantfrom vet.vet_clinic_utils import get_vet_clinic_zone_director
class AssignedToParticipantTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            When this test runs, it checks against this participant\n            for the test.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor)}

    def required_participant(self):
        return (self.participant,)

    def test_target(self, target, resolver, tooltip=None):
        vet_zone_director = get_vet_clinic_zone_director()
        if not vet_zone_director:
            return TestResult(False, 'No vet zone director running.')
        participant = resolver.get_participant(self.participant)
        if not vet_zone_director.is_assigned_to_vet(target.sim_id, participant.sim_id):
            return TestResult(False, '{} is not assigned to {}'.format(target, participant), tooltip=tooltip)
        return TestResult.TRUE

class VetPatientAssignedToAnyoneTest:

    def __init__(self, invert=False):
        self._invert = invert

    def required_participant(self):
        return ()

    def test_target(self, target, resolver, tooltip=None):
        vet_zone_director = get_vet_clinic_zone_director()
        if not vet_zone_director:
            return TestResult(False, 'No vet zone director running.')
        if vet_zone_director.is_assigned_to_vet(target.sim_id, None):
            if self._invert:
                return TestResult(False, '{} is assigned to someone'.format(target), tooltip=tooltip)
            return TestResult.TRUE
        if not self._invert:
            return TestResult(False, '{} not assigned to anyone'.format(target), tooltip=tooltip)
        return TestResult.TRUE

class VetPatientWaitingForServicesTest:

    def required_participant(self):
        return ()

    def test_target(self, target, resolver, tooltip=None):
        vet_zone_director = get_vet_clinic_zone_director()
        if not vet_zone_director:
            return TestResult(False, 'No vet zone director running.')
        if vet_zone_director.is_waiting_for_services(target.sim_id):
            return TestResult.TRUE
        return TestResult(False, '{} not waiting for services'.format(target), tooltip=tooltip)

class VetAttendingToAnyoneTest:

    def __init__(self, invert=False):
        self._invert = invert

    def required_participant(self):
        return ()

    def test_target(self, target, resolver, tooltip=None):
        vet_zone_director = get_vet_clinic_zone_director()
        if not vet_zone_director:
            return TestResult(False, 'No vet zone director running.')
        if vet_zone_director.is_vet_attending_any_customers(target.sim_id):
            if self._invert:
                return TestResult(False, '{} is assigned to someone'.format(target), tooltip=tooltip)
            return TestResult.TRUE
        if not self._invert:
            return TestResult(False, '{} not assigned to anyone'.format(target), tooltip=tooltip)
        return TestResult.TRUE

class VetTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            When this test runs, it checks against this participant\n            for the test.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.TargetSim), 'test_to_perform': TunableVariant(description='\n            The test to perform.\n            ', assigned_to_participant=AssignedToParticipantTest.TunableFactory(description='\n                Checks if the target has been assigned to a specific participant as a patient.\n                '), locked_args={'patient_waiting_for_services': VetPatientWaitingForServicesTest(), 'patient_assigned_to_anyone': VetPatientAssignedToAnyoneTest(), 'patient_not_assigned_to_anyone': VetPatientAssignedToAnyoneTest(invert=True), 'vet_assigned_to_anyone': VetAttendingToAnyoneTest(), 'vet_not_assigned_to_anyone': VetAttendingToAnyoneTest(invert=True)}, default='patient_not_assigned_to_anyone')}

    def get_expected_args(self):
        return {'resolver': RESOLVER_PARTICIPANT, 'targets': self.target}

    @cached_test
    def __call__(self, targets, resolver):
        target_sim = next(iter(targets), None)
        if target_sim is None:
            return TestResult(False, 'Target is None.', tooltip=self.tooltip)
        return self.test_to_perform.test_target(target_sim, resolver, tooltip=self.tooltip)
