from protocolbuffers import Consts_pb2, Dialog_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom distributor.ops import GenericProtocolBufferOpfrom distributor.shared_messages import IconInfoDatafrom distributor.system import Distributorfrom interactions import ParticipantTypefrom sims4.tuning.tunable import TunableEnumEntry, OptionalTunablefrom singletons import DEFAULTfrom snippets import define_snippetfrom ui.ui_dialog import UiDialog, get_defualt_ui_dialog_responseimport enum
class UiDialogNotification(UiDialog):
    DIALOG_MSG_TYPE = Consts_pb2.MSG_UI_NOTIFICATION_SHOW

    class UiDialogNotificationExpandBehavior(enum.Int):
        USER_SETTING = 0
        FORCE_EXPAND = 1

    class UiDialogNotificationUrgency(enum.Int):
        DEFAULT = 0
        URGENT = 1

    class UiDialogNotificationLevel(enum.Int):
        PLAYER = 0
        SIM = 1

    class UiDialogNotificationVisualType(enum.Int):
        INFORMATION = 0
        SPEECH = 1
        SPECIAL_MOMENT = 2

    FACTORY_TUNABLES = {'expand_behavior': TunableEnumEntry(description="\n            Specify the notification's expand behavior.\n            ", tunable_type=UiDialogNotificationExpandBehavior, default=UiDialogNotificationExpandBehavior.USER_SETTING), 'urgency': TunableEnumEntry(description="\n            Specify the notification's urgency.\n            ", tunable_type=UiDialogNotificationUrgency, default=UiDialogNotificationUrgency.DEFAULT), 'information_level': TunableEnumEntry(description="\n            Specify the notification's information level.\n            ", tunable_type=UiDialogNotificationLevel, default=UiDialogNotificationLevel.SIM), 'visual_type': TunableEnumEntry(description="\n            Specify the notification's visual treatment.\n            ", tunable_type=UiDialogNotificationVisualType, default=UiDialogNotificationVisualType.INFORMATION), 'primary_icon_response': OptionalTunable(description='\n            If enabled, associate a response to clicking the primary icon.\n            ', tunable=get_defualt_ui_dialog_response(description='\n                The response associated to the primary icon.\n                ')), 'secondary_icon_response': OptionalTunable(description='\n            If enabled, associate a response to clicking the secondary icon.\n            ', tunable=get_defualt_ui_dialog_response(description='\n                The response associated to the secondary icon.\n                ')), 'participant': OptionalTunable(description="\n            This field is deprecated. Please use 'icon' instead.\n            ", tunable=TunableEnumEntry(tunable_type=ParticipantType, default=ParticipantType.TargetSim), deprecated=True)}

    def distribute_dialog(self, dialog_type, dialog_msg, **kwargs):
        distributor = Distributor.instance()
        notification_op = GenericProtocolBufferOp(Operation.UI_NOTIFICATION_SHOW, dialog_msg)
        owner = self.owner
        if owner is not None and owner.valid_for_distribution:
            distributor.add_op(owner, notification_op)
        else:
            distributor.add_op_with_no_owner(notification_op)

    def build_msg(self, additional_tokens=(), icon_override=DEFAULT, event_id=None, career_args=None, **kwargs):
        if self.participant is not None:
            participant = self._resolver.get_participant(self.participant)
            if participant is not None:
                icon_override = IconInfoData(obj_instance=participant)
        msg = super().build_msg(icon_override=icon_override, additional_tokens=additional_tokens, **kwargs)
        msg.dialog_type = Dialog_pb2.UiDialogMessage.NOTIFICATION
        notification_msg = msg.Extensions[Dialog_pb2.UiDialogNotification.dialog]
        notification_msg.expand_behavior = self.expand_behavior
        notification_msg.criticality = self.urgency
        notification_msg.information_level = self.information_level
        notification_msg.visual_type = self.visual_type
        if icon_override is DEFAULT and career_args is not None:
            notification_msg.career_args = career_args
        if self.primary_icon_response is not None:
            self._build_response_arg(self.primary_icon_response, notification_msg.primary_icon_response, **kwargs)
        if self.secondary_icon_response is not None:
            self._build_response_arg(self.secondary_icon_response, notification_msg.secondary_icon_response, **kwargs)
        return msg
(TunableUiDialogNotificationReference, TunableUiDialogNotificationSnippet) = define_snippet('Notification', UiDialogNotification.TunableFactory())