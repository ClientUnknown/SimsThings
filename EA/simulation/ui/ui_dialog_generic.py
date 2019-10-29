from sims4.tuning.tunable import TunableTuplefrom singletons import DEFAULTfrom ui.ui_dialog import UiDialog, UiDialogOkCancel, UiDialogOk, ButtonTypefrom ui.ui_text_input import UiTextInputimport servicesTEXT_INPUT_FIRST_NAME = 'first_name'TEXT_INPUT_LAST_NAME = 'last_name'
class UiDialogTextInput(UiDialog):
    FACTORY_TUNABLES = {'text_inputs': lambda *names: TunableTuple(**{name: UiTextInput.TunableFactory(locked_args={'sort_order': index}) for (index, name) in enumerate(names)})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text_input_responses = {}

    def get_text_input_reference_sim(self):
        return self.owner

    def on_text_input(self, text_input_name='', text_input=''):
        if hasattr(self.text_inputs, text_input_name):
            self.text_input_responses[text_input_name] = text_input
            return True
        return False

    def build_msg(self, text_input_overrides=None, additional_tokens=(), **kwargs):
        msg = super().build_msg(additional_tokens=additional_tokens, **kwargs)
        for (name, tuning) in sorted(self.text_inputs.items(), key=lambda t: t[1].sort_order):
            tuning.build_msg(self, msg, name, text_input_overrides=text_input_overrides, additional_tokens=additional_tokens)
        return msg

    def do_auto_respond(self, auto_response=DEFAULT):
        dialog_response_ids = set(r.dialog_response_id for r in self.responses)
        if auto_response is not DEFAULT:
            response = auto_response
        elif ButtonType.DIALOG_RESPONSE_CANCEL in dialog_response_ids:
            response = ButtonType.DIALOG_RESPONSE_CANCEL
        elif ButtonType.DIALOG_RESPONSE_OK in dialog_response_ids:
            for (text_input_name, text_input_tuning) in self.text_inputs.items():
                if text_input_tuning.min_length != 0:
                    text = '*'*text_input_tuning.min_length.length
                else:
                    text = '*'
                self.on_text_input(text_input_name, text)
            response = ButtonType.DIALOG_RESPONSE_OK
        else:
            response = ButtonType.DIALOG_RESPONSE_CLOSED
        services.ui_dialog_service().dialog_respond(self.dialog_id, response)

class UiDialogTextInputOkCancel(UiDialogOkCancel, UiDialogTextInput):
    pass

class UiDialogTextInputOk(UiDialogOk, UiDialogTextInput):
    pass
