import enum
class PaymentInfo:

    def __init__(self, amount, resolver):
        self.amount = amount
        self.resolver = resolver

class BusinessPaymentInfo(PaymentInfo):

    def __init__(self, *args, revenue_type, **kwargs):
        super().__init__(*args, **kwargs)
        self.revenue_type = revenue_type

class PaymentBusinessRevenueType(enum.Int):
    ITEM_SOLD = 0
    SEED_MONEY = 1
