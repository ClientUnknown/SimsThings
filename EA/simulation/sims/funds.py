from protocolbuffers import Consts_pb2from event_testing import test_eventsfrom event_testing.event_data_const import SimoleonDatafrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableRange, TunableMapping, TunableEnumEntryimport distributor.opsimport enumimport servicesimport sims4.logimport sims4.telemetryimport telemetry_helperlogger = sims4.log.Logger('Family Funds', default_owner='trevor')TELEMETRY_GROUP_FUNDS = 'FUND'TELEMETRY_HOOK_POCKET = 'POKT'TELEMETRY_HOOK_FUNDS_CHANGE = 'FMOD'TELEMETRY_AMOUNT = 'amnt'TELEMETRY_REASON = 'resn'TELEMETRY_FUND_AMOUNT = 'fund'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_FUNDS)
class FundsSource(enum.Int):
    HOUSEHOLD = 0
    RETAIL = 1
    BUSINESS = 2
    STATISTIC = 3

class FundsTuning:
    UNAFFORDABLE_TOOLTIPS = TunableMapping(description='\n        A mapping of tooltips for each of the funds sources when an interaction\n        cannot be performed due to lack of such funds. Each tooltip takes the\n        same tokens as the interaction.\n        ', key_type=TunableEnumEntry(description='\n            The funds source.\n            ', tunable_type=FundsSource, default=FundsSource.HOUSEHOLD), value_type=TunableLocalizedStringFactory(description='\n            The tooltip to display when a Sim cannot run the specified\n            interaction due to lack of funds.\n            '))

def get_funds_for_source(funds_source, *, sim):
    if funds_source == FundsSource.HOUSEHOLD:
        return sim.family_funds
    if funds_source == FundsSource.BUSINESS:
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is None:
            return
        return business_manager.funds
    if funds_source == FundsSource.STATISTIC:
        return
    raise NotImplementedError

def transfer_funds(amount, *, from_funds, to_funds):
    if not from_funds.try_remove(amount, reason=from_funds.funds_transfer_loss_reason):
        return False
    to_funds.add(amount, reason=to_funds.funds_transfer_gain_reason)
    return True

class _Funds:
    __slots__ = ('_household_id', '_funds')
    MAX_FUNDS = TunableRange(int, 99999999, 0, sims4.math.MAX_INT32, description='Max Funds a household can have.')

    def __init__(self, household_id, starting_amount):
        self._household_id = household_id
        self._funds = starting_amount

    @property
    def money(self):
        return self._funds

    @property
    def funds_transfer_gain_reason(self):
        raise NotImplementedError

    @property
    def funds_transfer_loss_reason(self):
        raise NotImplementedError

    @property
    def allow_negative_funds(self):
        return False

    @property
    def allow_npcs(self):
        return False

    def set_household_id(self, household_id):
        self._household_id = household_id

    def _get_household(self):
        return services.household_manager().get(self._household_id)

    def send_money_update(self, vfx_amount, sim=None, reason=0):
        raise NotImplementedError

    def _send_money_update_internal(self, household_id, vfx_amount, sim=None, reason=0):
        op = distributor.ops.SetMoney(self.money, vfx_amount, sim, reason)
        household = services.household_manager().get(household_id)
        if household is not None:
            distributor.ops.record(household, op)
        else:
            logger.error('Failed to get household with id: {}', household_id, owner='tingyul')

    def can_afford(self, amount):
        return self.allow_negative_funds or self.money >= amount

    def add(self, amount, reason, sim=None, tags=None, count_as_earnings=True):
        amount = round(amount)
        if amount < 0:
            logger.error('Attempt to add negative amount of money to Family Funds.')
            return
        self._update_money(amount, reason, sim=sim, tags=tags, count_as_earnings=count_as_earnings)

    def try_remove(self, amount, reason, sim=None, require_full_amount=True):
        return self.try_remove_amount(amount, reason, sim, require_full_amount) is not None

    def try_remove_amount(self, amount, reason, sim=None, require_full_amount=True):
        amount = round(amount)
        if amount < 0:
            logger.error('Attempt to remove negative amount of money from Family Funds.')
            return
        if self.allow_npcs or sim is not None and sim.is_npc:
            return amount
        if require_full_amount == False and amount > self._funds and not self.allow_negative_funds:
            amount = self._funds
        elif amount > self._funds and not self.allow_negative_funds:
            return
        self._update_money(-amount, reason, sim)
        return amount

    def _update_money(self, amount, reason, sim=None, tags=None, count_as_earnings=True, show_fx=True):
        if amount == 0:
            return
        self._funds = min(self._funds + amount, self.MAX_FUNDS)
        if not self.allow_negative_funds:
            logger.error('Negative funds amount ({}) not supported', self._funds)
            self._funds = 0
        vfx_amount = amount if self._funds < 0 and show_fx else 0
        self.send_money_update(vfx_amount=vfx_amount, sim=sim, reason=reason)
        with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_FUNDS_CHANGE, sim=sim) as hook:
            hook.write_int(TELEMETRY_AMOUNT, amount)
            hook.write_int(TELEMETRY_REASON, reason)
            hook.write_int(TELEMETRY_FUND_AMOUNT, self._funds)
        if count_as_earnings and amount > 0:
            if sim is None:
                services.get_event_manager().process_events_for_household(test_events.TestEvent.SimoleonsEarned, self._get_household(), simoleon_data_type=SimoleonData.TotalMoneyEarned, amount=amount, skill_used=None, tags=tags)
            else:
                services.get_event_manager().process_event(test_events.TestEvent.SimoleonsEarned, sim_info=sim.sim_info, simoleon_data_type=SimoleonData.TotalMoneyEarned, amount=amount, skill_used=None, tags=tags)
                services.get_event_manager().process_events_for_household(test_events.TestEvent.SimoleonsEarned, self._get_household(), simoleon_data_type=SimoleonData.TotalMoneyEarned, amount=0, skill_used=None, tags=frozenset(), exclude_sim=sim.sim_info)

class FamilyFunds(_Funds):
    __slots__ = set()

    @property
    def funds_transfer_gain_reason(self):
        return Consts_pb2.FUNDS_HOUSEHOLD_TRANSFER_GAIN

    @property
    def funds_transfer_loss_reason(self):
        return Consts_pb2.FUNDS_HOUSEHOLD_TRANSFER_LOSS

    def send_money_update(self, vfx_amount, sim=None, reason=0):
        self._send_money_update_internal(self._household_id, vfx_amount, sim, reason)
