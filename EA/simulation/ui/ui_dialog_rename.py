from sims.pregnancy.pregnancy_offspring_data import PregnancyOffspringDatafrom ui.ui_dialog_generic import TEXT_INPUT_FIRST_NAME, TEXT_INPUT_LAST_NAMEimport element_utilsimport elementsimport services
class RenameDialogElement(elements.ParentElement):

    def __init__(self, dialog, offspring_data, additional_tokens=()):
        super().__init__()
        self._dialog = dialog
        self._offspring_data = offspring_data
        self._additional_tokens = additional_tokens
        self._result = None
        self.sleep_element = None

    def _on_response(self, dialog):
        if self._dialog is None:
            return
        first_name = dialog.text_input_responses.get(TEXT_INPUT_FIRST_NAME)
        last_name = dialog.text_input_responses.get(TEXT_INPUT_LAST_NAME) or self._offspring_data.last_name
        self._offspring_data.first_name = first_name
        self._offspring_data.last_name = last_name
        self._result = True
        if self.sleep_element is not None:
            self.sleep_element.trigger_soft_stop()

    def _run(self, timeline):
        additional_tokens = (self._offspring_data,)
        if self._additional_tokens is not None:
            additional_tokens = additional_tokens + self._additional_tokens
        if isinstance(self._offspring_data, PregnancyOffspringData):
            trait_overrides_for_baby = self._offspring_data.traits
            gender_overrides_for_baby = self._offspring_data.gender
        else:
            trait_overrides_for_baby = None
            gender_overrides_for_baby = None
        self._dialog.show_dialog(on_response=self._on_response, additional_tokens=additional_tokens, trait_overrides_for_baby=trait_overrides_for_baby, gender_overrides_for_baby=gender_overrides_for_baby)
        if self._result is None:
            self.sleep_element = element_utils.soft_sleep_forever()
            return timeline.run_child(self.sleep_element)
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
