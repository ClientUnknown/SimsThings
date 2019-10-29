from _sims4_collections import frozendictfrom sims.sim_dialogs import SimPersonalityAssignmentDialogfrom sims4.tuning.tunable import HasTunableFactory, TunableVariantfrom ui.ui_dialog import UiDialogOkCancelimport element_utilsimport elementsimport services
class UiDialogElement(HasTunableFactory, elements.ParentElement):
    FACTORY_TUNABLES = {'dialog': TunableVariant(description='\n            The dialog to prompt the user with.\n            ', ok_cancel=UiDialogOkCancel.TunableFactory(), personality_assignment=SimPersonalityAssignmentDialog.TunableFactory(), default='ok_cancel')}

    def __init__(self, *args, dialog=None, on_response=None, additional_tokens=(), dialog_kwargs=frozendict(), **kwargs):
        super().__init__(**kwargs)
        merged_kwargs = dialog_kwargs.copy()
        merged_kwargs.update(kwargs)
        self._dialog = dialog(*args, **merged_kwargs)
        self._dialog.add_listener(self._on_response)
        self._result = None
        self._on_response = on_response
        self._additional_tokens = additional_tokens

    def _on_response(self, dialog):
        if self._dialog is None:
            return
        if self._on_response is not None:
            self._result = self._on_response(dialog)
        else:
            self._result = dialog.accepted
        self.trigger_soft_stop()

    def _run(self, timeline):
        self._dialog.show_dialog(additional_tokens=self._additional_tokens)
        if self._result is None:
            return timeline.run_child(element_utils.soft_sleep_forever())
        return self._result

    def _resume(self, timeline, child_result):
        if self._result is not None:
            return self._result
        return False

    def _hard_stop(self):
        super()._hard_stop()
        if self._dialog is not None:
            services.ui_dialog_service().dialog_cancel(self._dialog.dialog_id)
        self._dialog = None

    def _soft_stop(self):
        super()._soft_stop()
        self._dialog = None
