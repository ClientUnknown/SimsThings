from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom lot_decoration.lot_decoration_mixins import HolidayOrEverydayDecorationMixinfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableVariant, HasTunableSingletonFactoryimport services
class _LotDecorationHasDecorationsAvailableTest(HolidayOrEverydayDecorationMixin, HasTunableFactory, AutoFactoryInit):

    def perform_test(self, tooltip):
        lot_decoration_service = services.lot_decoration_service()
        if lot_decoration_service is None:
            return TestResult(False, 'Lot decoration service not available.', tooltip=tooltip)
        custom_decorations_test = _LotDecorationHasCustomDecorationsTest(_decoration_occasion=self._decoration_occasion)
        result = custom_decorations_test.perform_test(tooltip)
        if not result:
            holiday_decorations_test = _LotDecorationDecoratableHolidayTest(_decoration_occasion=self._decoration_occasion)
            result = holiday_decorations_test.perform_test(tooltip)
        return result

class _LotDecorationDecoratableHolidayTest(HolidayOrEverydayDecorationMixin, HasTunableFactory, AutoFactoryInit):

    def perform_test(self, tooltip):
        holiday_service = services.holiday_service()
        if holiday_service is None:
            return TestResult(False, 'Lot decoration service not available.', tooltip=tooltip)
        holiday_id = self.occasion()
        if holiday_id is None:
            return TestResult(False, 'Could not find an applicable holiday for test. {}', self, tooltip=tooltip)
        if holiday_service.get_decoration_preset(holiday_id) is None:
            return TestResult(False, 'Holiday with id {} has no decorations.', self.occasion(), tooltip=tooltip)
        return TestResult.TRUE

class _LotDecorationHasCustomDecorationsTest(HolidayOrEverydayDecorationMixin, HasTunableFactory, AutoFactoryInit):

    def perform_test(self, tooltip):
        lot_decoration_service = services.lot_decoration_service()
        if lot_decoration_service is None:
            return TestResult(False, 'Lot decoration service not available.', tooltip=tooltip)
        deco_type_id = self.occasion()
        if deco_type_id is None:
            if self._decoration_occasion is not None:
                return TestResult(False, 'Testing for holiday decorations when there is no current or upcoming holiday.', tooltip=tooltip)
            deco_type_id = 0
        if not lot_decoration_service.does_lot_have_custom_decorations(deco_type_id):
            return TestResult(False, 'Lot has no custom decorations for id {}.', self.occasion(), tooltip=tooltip)
        return TestResult.TRUE

class _ActiveLotIsDecoratedForSomeOccasionTest(HasTunableFactory, AutoFactoryInit):

    def perform_test(self, tooltip):
        lot_decoration_service = services.lot_decoration_service()
        if lot_decoration_service is None:
            return TestResult(False, 'Lot decoration service not available.', tooltip=tooltip)
        deco_type_id = lot_decoration_service.get_active_lot_decoration_type_id()
        if deco_type_id is None:
            return TestResult(False, 'Could not find data for lot with zone id.', services.current_zone_id(), tooltip=tooltip)
        if deco_type_id == 0:
            return TestResult(False, 'Lot is set to everyday decorations. zone_id {}', services.current_zone_id(), tooltip=tooltip)
        return TestResult.TRUE

class LotDecorationTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'test': TunableVariant(description='\n            The test we want to run.\n            ', decorations_available=_LotDecorationHasDecorationsAvailableTest.TunableFactory(), holiday_decoratable=_LotDecorationDecoratableHolidayTest.TunableFactory(), custom_decorations=_LotDecorationHasCustomDecorationsTest.TunableFactory(), active_lot_decorated_for_occasion=_ActiveLotIsDecoratedForSomeOccasionTest.TunableFactory(), default='decorations_available')}

    def get_expected_args(self):
        return {}

    def __call__(self):
        return self.test().perform_test(self.tooltip)
