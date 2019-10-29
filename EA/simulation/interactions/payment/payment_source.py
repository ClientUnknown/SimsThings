from protocolbuffers import Consts_pb2from business.business_funds import BusinessFundsCategoryfrom interactions import ParticipantTypefrom sims.funds import FundsSource, get_funds_for_sourcefrom sims4.tuning.tunable import TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, TunableReference, Tunableimport servicesimport sims4.loglogger = sims4.log.Logger('Payment', default_owner='rmccord')
def get_tunable_payment_source_variant(*args, **kwargs):
    kwargs['household'] = _PaymentSourceHousehold.TunableFactory()
    kwargs['business'] = _PaymentSourceBusiness.TunableFactory()
    kwargs['statistic'] = _PaymentSourceStatistic.TunableFactory()
    return TunableVariant(*args, default='household', **kwargs)

class _PaymentSource(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'require_full_amount': Tunable(description='\n            If False, the payment element will subtract whatever funds are \n            available if there are not enough funds.\n            ', tunable_type=bool, default=True)}

    @property
    def funds_source(self):
        raise NotImplementedError

    def try_remove_funds(self, sim, amount, resolver=None):
        funds = get_funds_for_source(self.funds_source, sim=sim)
        return funds.try_remove_amount(amount, Consts_pb2.TELEMETRY_INTERACTION_COST, sim, self.require_full_amount)

class _PaymentSourceHousehold(_PaymentSource):

    @property
    def funds_source(self):
        return FundsSource.HOUSEHOLD

class _PaymentSourceBusiness(_PaymentSourceHousehold):
    FACTORY_TUNABLES = {'funds_category': TunableEnumEntry(description='\n            If defined, this expense is categorized and can be displayed in the\n            Retail finance dialog.\n            ', tunable_type=BusinessFundsCategory, default=BusinessFundsCategory.NONE, invalid_enums=(BusinessFundsCategory.NONE,))}

    @property
    def funds_source(self):
        business_funds = get_funds_for_source(FundsSource.BUSINESS, sim=None)
        if business_funds is None:
            return super().funds_source
        return FundsSource.BUSINESS

    def try_remove_funds(self, sim, amount, resolver=None):
        business_funds = get_funds_for_source(FundsSource.BUSINESS, sim=sim)
        if business_funds is None:
            return super().try_remove_funds(sim, amount, resolver=None)
        return business_funds.try_remove_amount(amount, Consts_pb2.TELEMETRY_INTERACTION_COST, sim, funds_category=self.funds_category, require_full_amount=self.require_full_amount)

class _PaymentSourceStatistic(_PaymentSource):
    FACTORY_TUNABLES = {'statistic': TunableReference(description='\n            The statistic that should be used to pay.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), 'participant': TunableEnumEntry(description='\n            The participant whose statistic should be used to pay\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor)}

    @property
    def funds_source(self):
        return FundsSource.STATISTIC

    def try_remove_funds(self, sim, amount, resolver=None):
        if resolver is not None:
            target = resolver.get_participant(self.participant)
            if target is not None:
                tracker = target.get_tracker(self.statistic)
                if tracker is not None:
                    stat = tracker.get_statistic(self.statistic)
                    current_value = stat.get_value()
                    if amount > current_value:
                        if not self.require_full_amount:
                            amount = current_value
                        else:
                            return
                    else:
                        stat.set_value(stat.get_value() - amount)
                        return amount
