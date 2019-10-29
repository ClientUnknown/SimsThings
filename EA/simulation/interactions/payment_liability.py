from interactions.liability import Liability
class PaymentLiability(Liability):
    LIABILITY_TOKEN = 'PaymentLiability'

    def __init__(self, amount, payment_destinations, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.amount = amount
        self.payment_destinations = payment_destinations
