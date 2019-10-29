from protocolbuffers import Dialog_pb2, Consts_pb2from audio.primitive import TunablePlayAudio, play_tunable_audiofrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import build_icon_info_msgfrom distributor.system import Distributorfrom interactions import ParticipantTypeSingleSim, ParticipantTypefrom interactions.utils.localization_tokens import LocalizationTokensfrom interactions.utils.tunable_icon import TunableIconVariantfrom sims4.callback_utils import CallableListfrom sims4.localization import TunableLocalizedStringFactory, TunableLocalizedStringFactoryVariantfrom sims4.tuning.tunable import TunableEnumEntry, HasTunableFactory, AutoFactoryInit, OptionalTunable, HasTunableSingletonFactory, TunableList, Tunable, TunableEnumFlags, TunableFactory, TunableTuple, TunableVariant, TunableSimMinutefrom singletons import DEFAULTfrom snippets import define_snippetfrom uid import unique_idimport enumimport pythonutilsimport servicesimport sims4.loglogger = sims4.log.Logger('Dialog')
class ButtonType(enum.Int):
    DIALOG_RESPONSE_CLOSED = -1
    DIALOG_RESPONSE_NO_RESPONSE = 10000
    DIALOG_RESPONSE_OK = 10001
    DIALOG_RESPONSE_CANCEL = 10002

class PhoneRingType(enum.Int):
    NO_RING = 0
    BUZZ = 1
    RING = 2
    ALARM = 3

def get_defualt_ui_dialog_response(**kwargs):
    return UiDialogResponse.TunableFactory(locked_args={'sort_order': 0, 'dialog_response_id': ButtonType.DIALOG_RESPONSE_NO_RESPONSE}, **kwargs)

class UiDialogOption(enum.IntFlags):
    DISABLE_CLOSE_BUTTON = 1
    SMALL_TITLE = 2
    DISABLE_PICKER_CLOSE_BUTTON = 8

class UiDialogStyle(enum.Int):
    DEFAULT = 0
    CHANCE_CARD = 1
    CELEBRATION = 2
    VET_CHECK_IN = 3
    LARGE_ICON = 4
    TRAIT_REASSIGNMENT = 5
    LIFESTYLE_BRAND = 6
    LARGE_ICON_TEXT_HORIZONTAL = 7

class UiDialogBGStyle(enum.Int):
    BG_DEFAULT = 0
    BG_CHANCE_CARD = 1
    BG_CELEBRATION = 2
    BG_LIFESTYLE_BRAND = 3
    BG_CELEBRATION_LARGE = 4

class CommandArgType(enum.Int):
    ARG_TYPE_BOOL = 0
    ARG_TYPE_STRING = 1
    ARG_TYPE_FLOAT = 2
    ARG_TYPE_INT = 3
    ARG_TYPE_SPECIAL = 4
    ARG_TYPE_RESOLVED = 5

class UiResponseParticipant(enum.LongFlags):
    Actor = ParticipantType.Actor
    Object = ParticipantType.Object
    TargetSim = ParticipantType.TargetSim

class UiResponseParticipantId(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant to resolve for this response argument.\n            The value sent will be the id of the specified participant.\n            If more than one participant is found, it will only send the id of the first participant found.\n            ', tunable_type=UiResponseParticipant, default=UiResponseParticipant.Actor)}

    @property
    def arg_type(self):
        return CommandArgType.ARG_TYPE_RESOLVED

    def resolve_response_arg(self, resolver=None):
        if resolver is None:
            return (None, None)
        participant = resolver.get_participant(self.participant)
        if participant is None:
            logger.error('Participant not {} found in resolver {}', self.participant, resolver, owner='jdimailig')
            return (None, None)
        if participant.is_sim:
            return (CommandArgType.ARG_TYPE_INT, participant.sim_id)
        return (CommandArgType.ARG_TYPE_INT, participant.id)

class _UiResponseCommand(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'command': Tunable(description='The command.', tunable_type=str, default=''), 'arguments': TunableList(description='\n            The arguments for this command. Arguments will be added after the\n            command.\n            ', tunable=TunableVariant(description='\n                An argument being passed to the command.\n                ', boolean=TunableTuple(description='\n                    A boolean value.\n                    ', arg_value=Tunable(tunable_type=bool, default=False), locked_args={'arg_type': CommandArgType.ARG_TYPE_BOOL}), string=TunableTuple(description='\n                    A string.\n                    ', arg_value=Tunable(tunable_type=str, default=''), locked_args={'arg_type': CommandArgType.ARG_TYPE_STRING}), floating_point=TunableTuple(description='\n                    A floating point number.\n                    ', arg_value=Tunable(tunable_type=float, default=0.0), locked_args={'arg_type': CommandArgType.ARG_TYPE_FLOAT}), integer=TunableTuple(description='\n                    An integer number.\n                    ', arg_value=Tunable(tunable_type=int, default=0), locked_args={'arg_type': CommandArgType.ARG_TYPE_INT}), participant_id=UiResponseParticipantId.TunableFactory(), special_command_data=TunableTuple(description='\n                    This will use the data passed into the show_dialog()\n                    function. This must be supported with GPE work, so\n                    only use this if you have talked to a GPE.\n                    ', locked_args={'arg_type': CommandArgType.ARG_TYPE_SPECIAL})))}
(_, TunableUiResponseCommandSnippet) = define_snippet('u_i_response_command', _UiResponseCommand.TunableFactory())
class UiDialogResponse(HasTunableSingletonFactory, AutoFactoryInit):

    class UiDialogUiRequest(enum.Int):
        NO_REQUEST = 0
        SHOW_LESSONS = 1
        SHOW_ACHIEVEMENTS = 2
        SHOW_GALLERY = 3
        SHOW_FAMILY_INVENTORY = 4
        SHOW_SKILL_PANEL = 5
        SHOW_SUMMARY_PANEL = 6
        SHOW_ASPIRATION_PANEL = 7
        SHOW_ASPIRATION_UI = 8
        SHOW_EVENT_UI = 9
        SHOW_CAREER_PANEL = 10
        SHOW_RELATIONSHIP_PANEL = 11
        SHOW_SIM_INVENTORY = 12
        SHOW_REWARD_STORE = 13
        SHOW_MOTIVE_PANEL = 14
        SHOW_STATS = 15
        SHOW_COLLECTIBLES = 16
        SHOW_CAREER_UI = 17
        TRANSITION_TO_NEIGHBORHOOD_SAVE = 18
        TRANSITION_TO_MAIN_MENU_NO_SAVE = 19
        SHOW_SHARE_PLAYER_PROFILE = 20
        SHOW_ASPIRATION_SELECTOR = 21
        SHOW_NOTEBOOK = 23
        SEND_COMMAND = 24
        CAREER_GO_TO_WORK = 25
        CAREER_WORK_FROM_HOME = 26
        CAREER_TAKE_PTO = 27
        CAREER_CALL_IN_SICK = 28
        SHOW_OCCULT_POWERS_PANEL = 29
        SHOW_FAME_PERKS_PANEL = 30

    @TunableFactory.factory_option
    def show_text(_):
        return {'text': TunableLocalizedStringFactory(description="\n                The prompt's text.\n                ")}

    FACTORY_TUNABLES = {'sort_order': Tunable(description='\n            The sorting order of the response button.  If the items of the\n            same order will be placed in the order that they are added.\n            ', tunable_type=int, default=0), 'dialog_response_id': TunableEnumEntry(description='\n            ', tunable_type=ButtonType, default=ButtonType.DIALOG_RESPONSE_NO_RESPONSE), 'ui_request': TunableEnumEntry(description="\n            This prompt's associated UI action.\n            ", tunable_type=UiDialogUiRequest, default=UiDialogUiRequest.NO_REQUEST), 'response_command': OptionalTunable(description='\n            If enabled, specifies a command to be called by the client.\n            ', tunable=TunableUiResponseCommandSnippet())}

    def __init__(self, sort_order=0, dialog_response_id=ButtonType.DIALOG_RESPONSE_NO_RESPONSE, text=None, subtext=None, ui_request=UiDialogUiRequest.NO_REQUEST, response_command=None, disabled_text=None):
        self.text = text
        self.subtext = subtext
        self.disabled_text = disabled_text
        super().__init__(sort_order=sort_order, dialog_response_id=dialog_response_id, ui_request=ui_request, response_command=response_command)

@unique_id('dialog_id', 1)
class UiDialogBase:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.response = None
        self._listeners = CallableList()

    def add_listener(self, listener_callback):
        self._listeners.append(listener_callback)

    def distribute_dialog(self, dialog_type, dialog_msg, immediate=False):
        distributor = Distributor.instance()
        distributor.add_event(dialog_type, dialog_msg, immediate=immediate)

    def get_phone_ring_type(self):
        return PhoneRingType.NO_RING

    @property
    def responses(self):
        return tuple()

    def has_responses(self):
        return self.responses or self._additional_responses

    def on_response_received(self):
        pass

    def respond(self, response:int) -> bool:
        try:
            self.response = response
            self._listeners(self)
            return True
        finally:
            self.on_response_received()
        return False

    def show_dialog(self, on_response=None, **kwargs):
        if on_response is not None:
            self.add_listener(on_response)
        pythonutils.try_highwater_gc()
        services.ui_dialog_service().dialog_show(self, self.get_phone_ring_type(), **kwargs)

    def do_auto_respond(self, auto_response=DEFAULT):
        if auto_response is not DEFAULT:
            response = auto_response
        elif ButtonType.DIALOG_RESPONSE_CANCEL in self.responses:
            response = ButtonType.DIALOG_RESPONSE_CANCEL
        elif ButtonType.DIALOG_RESPONSE_OK in self.responses:
            response = ButtonType.DIALOG_RESPONSE_OK
        else:
            response = ButtonType.DIALOG_RESPONSE_CLOSED
        services.ui_dialog_service().dialog_respond(self.dialog_id, response)

class UiDialog(UiDialogBase, HasTunableFactory, AutoFactoryInit):
    DIALOG_MSG_TYPE = Consts_pb2.MSG_UI_DIALOG_SHOW
    FACTORY_TUNABLES = {'title': OptionalTunable(description='\n            If enabled, this dialog will include title text.\n            ', tunable=TunableLocalizedStringFactory(description="\n                The dialog's title.\n                ")), 'text': TunableLocalizedStringFactoryVariant(description="\n            The dialog's text.\n            "), 'text_tokens': OptionalTunable(description='\n            If enabled, define text tokens to be used to localized text.\n            ', tunable=LocalizationTokens.TunableFactory(description='\n                Define the text tokens that are available to all text fields in\n                the dialog, such as title, text, responses, default and initial\n                text values, tooltips, etc.\n                '), disabled_value=DEFAULT), 'icon': OptionalTunable(description='\n            If enabled, specify an icon to be displayed.\n            ', tunable=TunableIconVariant()), 'secondary_icon': OptionalTunable(description='\n            If enabled, specify a secondary icon to be displayed. Only certain\n            dialog types may support this field.\n            ', tunable=TunableIconVariant()), 'phone_ring_type': TunableEnumEntry(description='\n             The phone ring type of this dialog.  If tuned to anything other\n             than None this dialog will only appear after clicking on the phone.\n             ', tunable_type=PhoneRingType, default=PhoneRingType.NO_RING), 'audio_sting': OptionalTunable(description='\n            If enabled, play an audio sting when the dialog is shown.\n            ', tunable=TunablePlayAudio()), 'ui_responses': TunableList(description='\n            A list of buttons that are mapped to UI commands.\n            ', tunable=get_defualt_ui_dialog_response(show_text=True)), 'dialog_style': TunableEnumEntry(description='\n            The style layout to apply to this dialog.\n            ', tunable_type=UiDialogStyle, default=UiDialogStyle.DEFAULT), 'dialog_bg_style': TunableEnumEntry(description='\n            The style background to apply to this dialog.\n            ', tunable_type=UiDialogBGStyle, default=UiDialogBGStyle.BG_DEFAULT), 'dialog_options': TunableEnumFlags(description='\n            Options to apply to the dialog.\n            ', enum_type=UiDialogOption, allow_no_flags=True, default=UiDialogOption.DISABLE_CLOSE_BUTTON), 'timeout_duration': OptionalTunable(description='\n            If enabled, override the timeout duration for this dialog in game\n            time.\n            ', tunable=TunableSimMinute(description='\n                The time, in sim minutes, that this dialog should time out.\n                ', default=5, minimum=5)), 'icon_override_participant': OptionalTunable(description='\n            If enabled, allows a different participant to be considered the\n            owner of this dialog. Typically, this will only affect the Sim\n            portrait used at the top of the dialog, but there could be other\n            adverse affects so be sure to talk to your UI partner before tuning\n            this.\n            ', tunable=TunableEnumEntry(description="\n                The participant to be used as the owner of this dialog. If this\n                participant doesn't exist, the default owner will be used\n                instead.\n                ", tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Invalid, invalid_enums=ParticipantTypeSingleSim.Invalid))}

    def __init__(self, owner, resolver=None, target_sim_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner = owner.ref() if owner is not None else None
        self._resolver = resolver
        self._additional_responses = {}
        self._timestamp = None
        self._target_sim_id = target_sim_id

    @property
    def accepted(self) -> bool:
        return self.response is not None and self.response != ButtonType.DIALOG_RESPONSE_CLOSED

    @property
    def closed(self) -> bool:
        return self.response == ButtonType.DIALOG_RESPONSE_CLOSED

    @property
    def owner(self):
        if self._owner is not None:
            return self._owner()

    @property
    def dialog_type(self):
        return self._dialog_type

    def set_responses(self, responses):
        self._additional_responses = tuple(responses)

    def _get_responses_gen(self):
        yield from self.responses
        yield from self._additional_responses
        yield from self.ui_responses

    def get_phone_ring_type(self):
        return self.phone_ring_type

    def update(self) -> bool:
        return True

    def show_dialog(self, **kwargs):
        if self.audio_sting is not None:
            play_tunable_audio(self.audio_sting, None)
        if self.phone_ring_type == PhoneRingType.ALARM:
            return super().show_dialog(caller_id=self._owner().id, **kwargs)
        return super().show_dialog(caller_id=self._target_sim_id, **kwargs)

    def _build_localized_string_msg(self, string, *additional_tokens):
        if string is None:
            logger.callstack('_build_localized_string_msg received None for the string to build. This is probably not intended.', owner='tingyul')
            return
        tokens = ()
        if self._resolver is not None:
            if self.text_tokens is DEFAULT:
                tokens = self._resolver.get_localization_tokens()
            elif self.text_tokens is not None:
                tokens = self.text_tokens.get_tokens(self._resolver)
        return string(*tokens + additional_tokens)

    def _build_response_arg(self, response, response_msg, tutorial_id=None, additional_tokens=(), response_command_tuple=None, **kwargs):
        response_msg.choice_id = response.dialog_response_id
        response_msg.ui_request = response.ui_request
        if response.text is not None:
            response_msg.text = self._build_localized_string_msg(response.text, additional_tokens)
        if response.subtext is not None:
            response_msg.subtext = response.subtext
        if response.disabled_text is not None:
            response_msg.disabled_text = response.disabled_text
        if tutorial_id is not None:
            response_msg.tutorial_args.tutorial_id = tutorial_id
        if response.response_command:
            response_msg.command_with_args.command_name = response.response_command.command
            for argument in response.response_command.arguments:
                with ProtocolBufferRollback(response_msg.command_with_args.command_remote_args.args) as entry:
                    if argument.arg_type == CommandArgType.ARG_TYPE_SPECIAL:
                        arg_type = response_command_tuple[0]
                        arg_value = response_command_tuple[1]
                    elif argument.arg_type == CommandArgType.ARG_TYPE_RESOLVED:
                        (arg_type, arg_value) = argument.resolve_response_arg(self._resolver)
                    else:
                        arg_type = argument.arg_type
                        arg_value = argument.arg_value
                    if arg_type == CommandArgType.ARG_TYPE_BOOL:
                        entry.bool = arg_value
                    elif arg_type == CommandArgType.ARG_TYPE_STRING:
                        entry.string = arg_value
                    elif arg_type == CommandArgType.ARG_TYPE_FLOAT:
                        entry.float = arg_value
                    elif arg_type == CommandArgType.ARG_TYPE_INT:
                        entry.int64 = arg_value

    def build_msg(self, additional_tokens=(), icon_override=DEFAULT, secondary_icon_override=DEFAULT, text_override=DEFAULT, **kwargs):
        msg = Dialog_pb2.UiDialogMessage()
        msg.dialog_id = self.dialog_id
        msg.owner_id = self.owner.id if self.owner is not None else 0
        msg.dialog_type = Dialog_pb2.UiDialogMessage.DEFAULT
        msg.dialog_style = self.dialog_style
        msg.dialog_bg_style = self.dialog_bg_style
        if self._target_sim_id is not None:
            msg.target_id = self._target_sim_id
        if self.title is not None:
            msg.title = self._build_localized_string_msg(self.title, additional_tokens)
        if text_override is DEFAULT:
            msg.text = self._build_localized_string_msg(self.text, additional_tokens)
        else:
            msg.text = self._build_localized_string_msg(text_override, additional_tokens)
        if self.timeout_duration is not None:
            msg.timeout_duration = self.timeout_duration
        if icon_override is DEFAULT:
            if self.icon is not None:
                icon_info = self.icon(self._resolver)
                key = icon_info[0]
                if key is not None:
                    msg.icon.type = key.type
                    msg.icon.group = key.group
                    msg.icon.instance = key.instance
                build_icon_info_msg(icon_info, None, msg.icon_info)
        elif icon_override is not None:
            build_icon_info_msg(icon_override, None, msg.icon_info)
        if secondary_icon_override is DEFAULT:
            if self.secondary_icon is not None:
                icon_info = self.secondary_icon(self._resolver)
                build_icon_info_msg(icon_info, None, msg.secondary_icon_info)
        elif secondary_icon_override is not None:
            build_icon_info_msg(secondary_icon_override, None, msg.secondary_icon_info)
        if self.icon_override_participant is not None:
            msg.override_sim_icon_id = self._resolver.get_participants(self.icon_override_participant)[0].id
        msg.dialog_options = self.dialog_options
        responses = []
        responses.extend(self._get_responses_gen())
        responses.sort(key=lambda response: response.sort_order)
        for response in responses:
            response_msg = msg.choices.add()
            self._build_response_arg(response, response_msg, additional_tokens=additional_tokens, **kwargs)
        return msg

class UiDialogOk(UiDialog):
    FACTORY_TUNABLES = {'text_ok': TunableLocalizedStringFactory(description='\n            The OK button text.\n            ', default=3648501874), 'is_special_dialog': Tunable(description='\n            If checked, UI will treat this as a special ok or ok/cancel dialog \n            and represent the ok or ok/cancel options in a special way. \n            They will use the text as a tooltip for ok or ok/cancel options \n            and use particular icons for the buttons.\n            ', tunable_type=bool, default=False)}

    def build_msg(self, **kwargs):
        msg = super().build_msg(**kwargs)
        msg.is_special_dialog = self.is_special_dialog
        if self.is_special_dialog:
            msg.dialog_type = Dialog_pb2.UiDialogMessage.OK_CANCEL_ICONS
        return msg

    @property
    def accepted(self) -> bool:
        return self.response == ButtonType.DIALOG_RESPONSE_OK

    @property
    def responses(self):
        return (UiDialogResponse(dialog_response_id=ButtonType.DIALOG_RESPONSE_OK, text=self.text_ok, ui_request=UiDialogResponse.UiDialogUiRequest.NO_REQUEST),)

class UiDialogOkCancel(UiDialogOk):
    FACTORY_TUNABLES = {'text_cancel': TunableLocalizedStringFactory(description='\n            The Cancel button text.\n            ', default=3497542682)}

    @property
    def responses(self):
        return (UiDialogResponse(dialog_response_id=ButtonType.DIALOG_RESPONSE_OK, text=self.text_ok, ui_request=UiDialogResponse.UiDialogUiRequest.NO_REQUEST), UiDialogResponse(dialog_response_id=ButtonType.DIALOG_RESPONSE_CANCEL, text=self.text_cancel, ui_request=UiDialogResponse.UiDialogUiRequest.NO_REQUEST))
