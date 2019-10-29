from event_testing import test_basefrom event_testing.results import TestResultfrom objects.components.types import GARDENING_COMPONENTfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInitimport services
class LotHasGardenTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):

    def get_expected_args(self):
        return {}

    def __call__(self):
        gardening_objects = services.object_manager().get_all_objects_with_component_gen(GARDENING_COMPONENT)
        if gardening_objects is not None:
            for gardening_obj in gardening_objects:
                if gardening_obj.is_on_active_lot() and not gardening_obj.is_in_inventory():
                    return TestResult.TRUE
        return TestResult(False, 'Active lot has no gardening plants.', tooltip=self.tooltip)
