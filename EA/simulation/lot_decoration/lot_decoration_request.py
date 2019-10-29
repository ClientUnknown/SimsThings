from lot_decoration.decoration_provider import DEFAULT_DECORATION_TYPE
class LotDecorationPriority(enum.Int, export=False):
    DEFAULT = 0
    PRE_HOLIDAY = ...
    HOLIDAY = ...

class LotDecorationRequestBase:

    @property
    def priority(self):
        raise NotImplementedError

    @property
    def provider(self):
        raise NotImplementedError

class EverydayDecorationRequest:

    @property
    def priority(self):
        return LotDecorationPriority.DEFAULT

    @property
    def provided_type(self):
        return LOT_DECORATION_DEFAULT_ID

class HolidayDecorationRequest:

    def __init__(self, holiday_drama_node):
        self._drama_node = holiday_drama_node

    @property
    def priority(self):
        if not self._drama_node.is_running:
            return LotDecorationPriority.PRE_HOLIDAY
        if self._drama_node.holiday is services.active_household().holiday_tracker.active_holiday_id:
            return LotDecorationPriority.HOLIDAY
        return LotDecorationPriority.PRE_HOLIDAY

    @property
    def provided_type(self):
        return self._drama_node.holiday_id
