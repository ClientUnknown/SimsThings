from event_testing.resolver import SingleSimResolverfrom event_testing.results import TestResultfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom interactions.base.super_interaction import SuperInteractionfrom ui.ui_dialog import UiDialogOkCancelimport interactions
class GenericChooseBetweenTwoAffordancesSuperInteraction(ImmediateSuperInteraction):
    INSTANCE_TUNABLES = {'choice_dialog': UiDialogOkCancel.TunableFactory(description='\n            A Dialog that prompts the user with a two button dialog. The\n            chosen button will result in one of two affordances being chosen.\n            '), 'accept_affordance': SuperInteraction.TunablePackSafeReference(description='\n            The affordance to push on the sim if the user clicks on the \n            accept/ok button.\n            '), 'reject_affordance': SuperInteraction.TunablePackSafeReference(description='\n            The affordance to push on the Sim if the user chooses to click\n            on the reject/cancel button.\n            ')}

    @classmethod
    def _test(cls, target, context, **interaction_parameters):
        if cls.accept_affordance is None and cls.reject_affordance is None:
            return TestResult(False, 'The accept and reject affordances are unavailable with the currently installed packs.')
        return super()._test(target, context, **interaction_parameters)

    def _run_interaction_gen(self, timeline):
        context = self.context.clone_for_sim(self.sim, insert_strategy=interactions.context.QueueInsertStrategy.LAST)
        if self.accept_affordance is None or self.reject_affordance is None:
            affordance = self.accept_affordance or self.reject_affordance
            self.sim.push_super_affordance(affordance, target=self.target, context=context)
            return

        def _on_response(dialog):
            affordance = self.accept_affordance if dialog.accepted else self.reject_affordance
            self.sim.push_super_affordance(affordance, target=self.target, context=context)

        dialog = self.choice_dialog(self.sim, resolver=SingleSimResolver(self.sim))
        dialog.show_dialog(on_response=_on_response)
