from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import cached_testfrom interactions import ParticipantType, ParticipantTypeSim, ParticipantTypeSingleSimfrom sickness import loggerfrom sims4.resources import Typesfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, Tunable, TunableEnumEntry, TunableReference, TunableVariantimport servicesfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListfrom tag import TunableTags
class _DiagnosticTestBase:

    @property
    def requires_sick_sim(self):
        return True

    def test_result(self, affordance, target, invert, tooltip):
        if self.requires_sick_sim and not target.is_sick():
            return TestResult(False, 'DiagnosticTest is invalid on non-Sick Sim {}', target, tooltip=tooltip)
        test_evaluation = self._evaluate(affordance, target)
        result_with_invert = invert != test_evaluation
        if result_with_invert:
            return TestResult.TRUE
        else:
            return TestResult(False, '{} for {} on {} returned {}', str(type(self)), affordance, target, test_evaluation, tooltip=tooltip)

    def _evaluate(self, affordance, target):
        raise NotImplementedError('Implement in subclasses.')

class _PerformedExamTest(_DiagnosticTestBase):

    @property
    def requires_sick_sim(self):
        return False

    def _evaluate(self, affordance, target):
        return target.was_exam_performed(affordance)

class _PerformedTreatmentTest(_DiagnosticTestBase):

    def _evaluate(self, affordance, target):
        return target.was_treatment_performed(affordance)

class _RuledOutTreatmentTest(_DiagnosticTestBase):

    def _evaluate(self, affordance, target):
        return target.was_treatment_ruled_out(affordance)

class _TreatmentAvailabilityTest(_DiagnosticTestBase):

    def _evaluate(self, affordance, target):
        return target.current_sickness.is_available_treatment(affordance)

class _CorrectTreatmentTest(_DiagnosticTestBase):

    def _evaluate(self, affordance, target):
        return target.current_sickness.is_correct_treatment(affordance)

class _DiscoveredSicknessTest(_DiagnosticTestBase):

    def _evaluate(self, affordance, target):
        return target.sickness_tracker.has_discovered_sickness

class DiagnosticActionTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            When this test runs, it checks against this participant\n            for sickness information.  If the affordance is targeting \n            a patient, it will typically be TargetSim.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSim.TargetSim), 'test': TunableVariant(description='\n            Type of test we are performing against the affordance that\n            runs or will run this test.\n            ', default='performed_exam', locked_args={'performed_exam': _PerformedExamTest(), 'performed_treatment': _PerformedTreatmentTest(), 'ruled_out_treatment': _RuledOutTreatmentTest(), 'is_treatment_available': _TreatmentAvailabilityTest(), 'is_correct_treatment': _CorrectTreatmentTest(), 'is_sickness_known': _DiscoveredSicknessTest()}), 'invert': Tunable(description='\n            Whether or not to invert the results of this test.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'affordance': ParticipantType.Affordance, 'targets': self.target}

    @cached_test
    def __call__(self, affordance, targets):
        if affordance is None:
            logger.error('DiagnositicActionTest: affordance is None')
            return TestResult(False, 'affordance was found to be None.', tooltip=self.tooltip)
        target_sim = next(iter(targets), None)
        if target_sim is None:
            return TestResult(False, 'Target is None.', tooltip=self.tooltip)
        return self.test.test_result(affordance, target_sim, self.invert, self.tooltip)

class _SicknessTagTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'tags': TunableTags(description='\n            Only sickness that share any of the tags specified pass. \n            ', filter_prefixes=('Sickness',))}

    def test_item(self, item):
        if item is None:
            return False
        return self.tags & item.sickness_tags

    def test_collection(self, collection):
        return any(self.test_item(item) for item in collection)

class SicknessTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            When this test runs, it checks against this participant\n            for sickness information.  If the affordance is targeting \n            a patient, it will typically be TargetSim.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSim.TargetSim), 'sickness': TunableVariant(description='\n            Optionally specify sickness to test against.\n            \n            If disabled, will check if the sick is sick with any sickness. \n            ', locked_args={'any_sickness': None}, white_blacklist=TunableWhiteBlackList(tunable=TunableReference(manager=services.get_instance_manager(Types.SICKNESS), class_restrictions=('Sickness',), pack_safe=True)), by_tag=_SicknessTagTest.TunableFactory(), default='any_sickness'), 'check_history': Tunable(description='\n            Whether or not to check sickness history.\n            \n            If False, we only check if they are currently sick\n            with the specified sickness.\n            ', tunable_type=bool, default=False), 'invert': Tunable(description='\n            Whether or not to invert the results of this test.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'targets': self.target}

    @cached_test
    def __call__(self, targets):
        target_sim = next(iter(targets), None)
        if target_sim is None:
            return TestResult(False, 'Target is None.', tooltip=self.tooltip)
        test_value = False
        if self.check_history:
            test_value = len(target_sim.sickness_tracker.previous_sicknesses) > 0 if self.sickness is None else bool(self.sickness.test_collection(target_sim.sickness_tracker.previous_sicknesses))
            result_value = self.invert != test_value
            if result_value:
                return TestResult.TRUE
            return TestResult(False, 'Failed previous sickness test. target={}, previous_sicknesses={}, {}'.format(target_sim, target_sim.sickness_tracker.previous_sicknesses, self))
        else:
            test_value = target_sim.is_sick() if self.sickness is None else bool(self.sickness.test_item(target_sim.current_sickness))
            result_value = self.invert != test_value
            if result_value:
                return TestResult.TRUE
            else:
                return TestResult(False, 'Failed sickness test. target={}, current_sickness={}, {}'.format(target_sim, target_sim.current_sickness, self))
