from protocolbuffers import Consts_pb2from interactions import ParticipantTypefrom interactions.payment.payment_info import PaymentBusinessRevenueType, BusinessPaymentInfofrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableEnumEntry, TunableReferenceimport enumimport servicesimport sims4.loglogger = sims4.log.Logger('Payment', default_owner='rmccord')
class PaymentDestTuningFlags(enum.IntFlags):
    NO_DEST = 0
    ACTIVE_HOUSEHOLD = 1
    PARTICIPANT_HOUSEHOLD = 2
    BUSINESS = 4
    STATISTIC = 8
    ALL = NO_DEST | ACTIVE_HOUSEHOLD | PARTICIPANT_HOUSEHOLD | BUSINESS | STATISTIC

class _PaymentDest(HasTunableSingletonFactory, AutoFactoryInit):

    def give_payment(self, cost_info):
        raise NotImplementedError
        return False

class PaymentDestNone(_PaymentDest):

    def give_payment(self):
        return True

class PaymentDestActiveHousehold(_PaymentDest):

    def give_payment(self, cost_info):
        household = services.active_household()
        if household is not None:
            amount = cost_info.amount
            if amount > 0:
                household.funds.add(amount, Consts_pb2.FUNDS_INTERACTION_REWARD)
            return True
        return False

class PaymentDestParticipantHousehold(_PaymentDest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description="\n            The participant whose household will accept the payment. If the\n            participant is not a Sim, we will use the participant's owning\n            household.\n            ", tunable_type=ParticipantType, default=ParticipantType.Actor)}

    def give_payment(self, cost_info):
        household = self._get_household(cost_info.resolver)
        if household is not None:
            amount = cost_info.amount
            if amount > 0:
                household.funds.add(amount, Consts_pb2.FUNDS_INTERACTION_REWARD)
            return True
        return False

    def _get_household(self, resolver):
        participant = resolver.get_participant(self.participant)
        household = None
        if participant is not None:
            if participant.is_sim:
                household = participant.household
            else:
                household_owner_id = participant.get_household_owner_id()
                household = services.household_manager().get(household_owner_id)
        return household

class PaymentDestBusiness(_PaymentDest):

    def give_payment(self, cost_info):
        if not isinstance(cost_info, BusinessPaymentInfo):
            revenue_type = None
        else:
            revenue_type = cost_info.revenue_type
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is not None:
            business_manager.modify_funds(cost_info.amount, from_item_sold=revenue_type == PaymentBusinessRevenueType.ITEM_SOLD)
            return True
        return False

class PaymentDestStatistic(_PaymentDest):
    FACTORY_TUNABLES = {'statistic': TunableReference(description='\n            The statistic that should accept the payment.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), 'participant': TunableEnumEntry(description='\n            The participant whose statistic will accept the payment.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor)}

    def give_payment(self, cost_info):
        participant = cost_info.resolver.get_participant(self.participant)
        stat = None
        if participant is not None:
            tracker = participant.get_tracker(self.statistic)
            if tracker is not None:
                stat = tracker.get_statistic(self.statistic)
        if stat is not None:
            stat.add_value(cost_info.amount)
            return True
        return False
