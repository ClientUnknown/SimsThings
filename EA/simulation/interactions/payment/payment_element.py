from interactions.payment.tunable_payment import TunablePaymentSnippetfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom sims4.tuning.tunable import Tunable, TunableTuple, OptionalTunablefrom singletons import DEFAULTfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport sims4.loglogger = sims4.log.Logger('Payment', default_owner='rmccord')
class PaymentElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'payment': TunablePaymentSnippet(), 'display_only': Tunable(description="\n            A PaymentElement marked as display_only will affect an affordance's\n            display name (by appending the Simoleon cost in parentheses), but\n            will not deduct funds when run.\n            ", tunable_type=bool, default=False), 'include_in_total': Tunable(description="\n            This should normally be set, but in cases where multiple payment\n            elements are tuned in separate outcomes, they will be all be summed\n            up to tally up the total cost of the interaction.\n            \n            In those cases, only set this to True for the 'definitive' cost.\n            ", tunable_type=bool, default=True), 'insufficient_funds_behavior': TunableTuple(description="\n            The behavior to define if we can succeed the payment if the\n            household doesn't have enough money.\n            ", allow_payment_succeed=Tunable(description='\n                If True, the payment element will still return True if there is\n                not enough fund. Otherwise return False.\n                ', tunable_type=bool, default=False), notification=OptionalTunable(description="\n                The notification about what the game will do if household\n                doesn't have enough fund.\n                ", tunable=TunableUiDialogNotificationSnippet()))}

    @classmethod
    def on_affordance_loaded_callback(cls, affordance, payment_element, object_tuning_id=DEFAULT):
        if not payment_element.include_in_total:
            return

        def get_simoleon_delta(interaction, target=DEFAULT, context=DEFAULT, **interaction_parameters):
            interaction_resolver = interaction.get_resolver(target=target, context=context, **interaction_parameters)
            return payment_element.payment.get_simoleon_delta(interaction_resolver)

        affordance.register_simoleon_delta_callback(get_simoleon_delta, object_tuning_id=object_tuning_id)

    def _do_behavior(self):
        if self.display_only:
            return True
        sim = self.interaction.sim
        resolver = self.interaction.get_resolver()
        if self.payment.try_deduct_payment(resolver, sim, self.try_show_insufficient_funds_notification):
            return True
        return self.insufficient_funds_behavior.allow_payment_succeed

    def try_show_insufficient_funds_notification(self):
        if self.insufficient_funds_behavior.notification is not None:
            sim = self.interaction.sim
            resolver = self.interaction.get_resolver()
            dialog = self.insufficient_funds_behavior.notification(sim, resolver)
            dialog.show_dialog()
