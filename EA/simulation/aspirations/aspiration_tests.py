from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import TestEvent, cached_testfrom interactions import ParticipantTypeSingleSimfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableFactory, TunableEnumEntry, TunablePackSafeReference, Tunable, TunableList, TunableReference, TunableVariantimport servicesimport sims4.loglogger = sims4.log.Logger('AspirationTests', default_owner='nsavalani')
class SelectedAspirationTrackTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    test_events = (TestEvent.AspirationTrackSelected,)

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'who': TunableEnumEntry(description='\n                    Who or what to apply this test to.\n                    ', tunable_type=participant_type_enum, default=participant_type_default)}

    FACTORY_TUNABLES = {'who': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'aspiration_track': TunablePackSafeReference(description='\n            The mood that must be active (or must not be active, if disallow is True).\n            ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION_TRACK))}

    def __init__(self, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)

    def get_expected_args(self):
        return {'test_targets': self.who}

    @cached_test
    def __call__(self, test_targets=()):
        for target in test_targets:
            if target is None:
                logger.error('Trying to call SelectedAspirationTrackTest with a None value in the sims iterable.')
            else:
                if self.aspiration_track is None:
                    return TestResult(False, '{} failed SelectedAspirationTrackTest check. Aspiration Track is None', target, tooltip=self.tooltip)
                if target._primary_aspiration is not self.aspiration_track:
                    return TestResult(False, '{} failed SelectedAspirationTrackTest check. Track guids: {} is not {}', target, target._primary_aspiration, self.aspiration_track.guid64, tooltip=self.tooltip)
        return TestResult.TRUE

class SelectedAspirationTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'who': TunableEnumEntry(description='\n                    Who or what to apply this test to', tunable_type=participant_type_enum, default=participant_type_default)}

    FACTORY_TUNABLES = {'who': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'aspiration': TunablePackSafeReference(description='\n            The aspiration that must be active.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION))}

    def __init__(self, **kwargs):
        super().__init__(safe_to_skip=True, **kwargs)

    def get_expected_args(self):
        return {'test_targets': self.who}

    @cached_test
    def __call__(self, test_targets=()):
        for target in test_targets:
            if target is None:
                logger.error('Trying to call SelectedAspirationTest with a None value in the sims iterable.')
            else:
                if self.aspiration is None:
                    return TestResult(False, '{} failed SelectedAspirationTest check. Aspiration is None', target, tooltip=self.tooltip)
                if target.aspiration_tracker is None:
                    return TestResult(False, '{} failed SelectedAspirationTest check. Has no aspiration tracker', target, tooltip=self.tooltip)
                if target.aspiration_tracker._active_aspiration is not self.aspiration:
                    return TestResult(False, '{} failed SelectedAspirationTest check. Active Aspiration {} is not {}', target, target.aspiration_tracker._active_aspiration, self.aspiration, tooltip=self.tooltip)
        return TestResult.TRUE

class HasAnyTimedAspirationTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'invert': Tunable(description='\n            If checked, the test will pass if a Sim has no timed aspirations.\n            ', tunable_type=bool, default=False)}

    def _run_test(self, target, tooltip=None):
        if target.aspiration_tracker._timed_aspirations:
            if self.invert:
                return TestResult(False, '{} has timed aspirations.'.format(target), tooltip=tooltip)
        elif not self.invert:
            return TestResult(False, '{} has no timed aspirations.'.format(target), tooltip=tooltip)
        return TestResult.TRUE

class HasSpecificTimedAspirationTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'timed_aspirations': TunableList(description='\n            The specific timed aspirations to test.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='TimedAspiration', pack_safe=True), minlength=1, unique_entries=True), 'invert': Tunable(description='\n            If checked, the test will pass if a Sim has none of the specific\n            timed aspirations.\n            ', tunable_type=bool, default=False)}

    def _run_test(self, target, tooltip=None):
        has_aspiration = any(aspiration for aspiration in self.timed_aspirations if aspiration in target.aspiration_tracker._timed_aspirations)
        if has_aspiration:
            if self.invert:
                return TestResult(False, '{} has one of the specified timed aspirations.'.format(target), tooltip=tooltip)
        elif not self.invert:
            return TestResult(False, '{} has none of the specified timed aspirations.'.format(target), tooltip=tooltip)
        return TestResult.TRUE

class HasTimedAspirationTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'test_behavior': TunableVariant(description='\n            The type of test to run.\n            ', has_any_timed_aspiration=HasAnyTimedAspirationTest.TunableFactory(), has_specific_timed_aspiration=HasSpecificTimedAspirationTest.TunableFactory(), default='has_any_timed_aspiration')}

    def get_expected_args(self):
        return {'targets': self.target}

    @cached_test
    def __call__(self, targets):
        target_sim = next(iter(targets), None)
        if target_sim is None:
            return TestResult(False, 'Target is None.', tooltip=self.tooltip)
        return self.test_behavior._run_test(target_sim, tooltip=self.tooltip)
