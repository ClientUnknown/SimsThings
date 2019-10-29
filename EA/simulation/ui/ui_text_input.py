from sims4.localization import TunableLocalizedStringFactory, TunableLocalizedStringFactoryVariantfrom sims4.tuning.tunable import TunableTuple, OptionalTunable, TunableRange, Tunable, AutoFactoryInit, HasTunableSingletonFactory, TunableVariantfrom sims.sim_spawner_enums import SimNameType
class _TextInputLengthFixed(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'min_length': OptionalTunable(description="\n             If enabled, specify the minimum length of input text the player has\n             to enter before he/she can hit the 'OK' button.\n             ", tunable=TunableTuple(length=TunableRange(description='\n                     Minimum amount of characters the user must enter in to the\n                     text box before he/she can click on the OK button.\n                     ', tunable_type=int, minimum=1, default=1), tooltip=OptionalTunable(description='\n                     If enabled, allows specification of a tooltip to display if\n                     the user has entered text length less than min_length.\n                     ', tunable=TunableLocalizedStringFactory()))), 'max_length': Tunable(description='\n             Max amount of characters the user can enter into the text box.\n             ', tunable_type=int, default=20)}

    def build_msg(self, dialog, msg, *additional_tokens):
        msg.max_length = self.max_length
        if self.min_length is not None:
            msg.min_length = self.min_length.length
            if self.min_length.tooltip is not None:
                msg.input_too_short_tooltip = dialog._build_localized_string_msg(self.min_length.tooltip, additional_tokens)

class _TextInputLengthName(HasTunableSingletonFactory, AutoFactoryInit):
    min_length = 0

    def build_msg(self, dialog, msg, *additional_tokens):
        msg.max_length = 14

class _TextInputLengthNameFirst(_TextInputLengthName):

    def build_msg(self, dialog, msg, *additional_tokens):
        super().build_msg(dialog, msg, additional_tokens)
        msg.min_length = 1

class _TextInputLengthNameLast(_TextInputLengthName):

    def build_msg(self, dialog, msg, *additional_tokens):
        super().build_msg(dialog, msg, additional_tokens)
        sim_info = dialog.get_text_input_reference_sim()
        from sims.sim_spawner import SimSpawner
        if sim_info.extended_species in SimSpawner.SPECIES_TO_NAME_TYPE:
            name_type = SimSpawner.SPECIES_TO_NAME_TYPE[sim_info.extended_species]
        else:
            name_type = SimNameType.DEFAULT
        if name_type in SimSpawner.NAME_TYPES_WITH_OPTIONAL_NAMES:
            msg.min_length = 0
        else:
            msg.min_length = 1

class _TunableTextInputLengthVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, fixed=_TextInputLengthFixed.TunableFactory(), cas_first_name=_TextInputLengthNameFirst.TunableFactory(), cas_last_name=_TextInputLengthNameLast.TunableFactory(), default='fixed', **kwargs)

class UiTextInput(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'default_text': OptionalTunable(description="\n            Default text that will show up when the text box is not in focus if\n            the user hasn't entered anything in the text box yet.\n            \n            If only default text is set, the text box will be blank when the\n            user puts it in focus.\n            ", tunable=TunableLocalizedStringFactory()), 'initial_value': OptionalTunable(description='\n            The initial value of the text in the textbox. This is different from\n            default text because the initial value stays regardless of if the\n            text box is in focus.\n            ', tunable=TunableLocalizedStringFactoryVariant()), 'title': OptionalTunable(description='\n             Text that will be shown with the text input to describe what that\n             user is inputing.\n             ', tunable=TunableLocalizedStringFactory()), 'length_restriction': _TunableTextInputLengthVariant(), 'restricted_characters': OptionalTunable(description='\n             A string containing the character set regex to determine restricted\n             characters in the text input.\n             ', tunable=TunableLocalizedStringFactory())}

    def __init__(self, *args, sort_order, **kwargs):
        super().__init__(*args, **kwargs)
        self.sort_order = sort_order

    @property
    def min_length(self):
        return self.length_restriction.min_length

    def build_msg(self, dialog, msg, name, text_input_overrides=None, additional_tokens=()):
        initial_value = self.initial_value
        if text_input_overrides is not None:
            if name not in text_input_overrides:
                return
            initial_value = text_input_overrides[name] or self.initial_value
        text_input_msg = msg.text_input.add()
        text_input_msg.text_input_name = name
        if initial_value is not None:
            text_input_msg.initial_value = dialog._build_localized_string_msg(initial_value, additional_tokens)
        if self.default_text is not None:
            text_input_msg.default_text = dialog._build_localized_string_msg(self.default_text, additional_tokens)
        if self.title:
            text_input_msg.title = dialog._build_localized_string_msg(self.title, additional_tokens)
        if self.restricted_characters is not None:
            text_input_msg.restricted_characters = dialog._build_localized_string_msg(self.restricted_characters, additional_tokens)
        self.length_restriction.build_msg(dialog, text_input_msg, additional_tokens)
