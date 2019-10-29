from sims.funds import _Fundsfrom sims4.tuning.dynamic_enum import DynamicEnumimport sims4.loglogger = sims4.log.Logger('Business', default_owner='trevor')
class BusinessFundsCategory(DynamicEnum):
    NONE = 0

class BusinessFunds(_Funds):

    def __init__(self, household_id, starting_funds, business_manager):
        super().__init__(household_id, starting_funds)
        self._business_manager = business_manager

    def _send_money_update_internal(self, household_id, vfx_amount, sim=None, reason=0):
        self._business_manager.send_business_funds_update()

    def send_money_update(self, vfx_amount, sim=None, reason=0):
        self._send_money_update_internal(self._business_manager.owner_household_id, vfx_amount, sim, reason)

    @property
    def funds_transfer_gain_reason(self):
        return self._business_manager.funds_transfer_gain_reason

    @property
    def funds_transfer_loss_reason(self):
        return self._business_manager.funds_transfer_loss_reason

    @property
    def allow_negative_funds(self):
        return True

    @property
    def allow_npcs(self):
        return True

    def try_remove(self, amount, reason, sim=None, require_full_amount=True, funds_category=None):
        return self.try_remove_amount(amount, reason, sim=sim, require_full_amount=require_full_amount, funds_category=funds_category) is not None

    def try_remove_amount(self, amount, *args, funds_category=None, **kwargs):
        result = super().try_remove_amount(amount, *args, **kwargs)
        if result and funds_category is not None and funds_category != BusinessFundsCategory.NONE:
            self._business_manager.add_to_funds_category(funds_category, amount)
        return result
