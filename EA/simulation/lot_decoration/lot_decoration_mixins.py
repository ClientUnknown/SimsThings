from sims4.tuning.tunable import OptionalTunablefrom holidays.holiday_tunables import TunableHolidayVariant
class HolidayOrEverydayDecorationMixin:
    FACTORY_TUNABLES = {'_decoration_occasion': OptionalTunable(description='\n            The holiday this applies to.\n            If disabled, applies only to everyday decorations.\n            ', tunable=TunableHolidayVariant(default='active_or_upcoming'), enabled_by_default=True, enabled_name='Holiday', disabled_name='Everyday')}

    def occasion(self):
        if self._decoration_occasion is None:
            return
        return self._decoration_occasion()
