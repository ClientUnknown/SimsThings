from drama_scheduler.drama_node import BaseDramaNode, CooldownOptionfrom drama_scheduler.drama_node_types import DramaNodeTypefrom sims4.tuning.tunable import TunableVariant, TunableList, TunableReference, HasTunableSingletonFactory, AutoFactoryInitfrom sims4.utils import classpropertyfrom ui.ui_dialog import UiDialogOk, UiDialogOkCancel, ButtonTypefrom ui.ui_dialog_notification import UiDialogNotificationimport servicesimport sims4.resources
class _dialog_and_loot(HasTunableSingletonFactory, AutoFactoryInit):

    def on_node_run(self, drama_node):
        raise NotImplementedError

class _notification_and_loot(_dialog_and_loot):
    FACTORY_TUNABLES = {'notification': UiDialogNotification.TunableFactory(description='\n            The notification that will display to the drama node.\n            '), 'loot_list': TunableList(description='\n            A list of loot operations to apply when this notification is given.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))}

    def on_node_run(self, drama_node):
        resolver = drama_node._get_resolver()
        target_sim_id = drama_node._sender_sim_info.id if drama_node._sender_sim_info is not None else None
        dialog = self.notification(drama_node._receiver_sim_info, target_sim_id=target_sim_id, resolver=resolver)
        dialog.show_dialog()
        for loot_action in self.loot_list:
            loot_action.apply_to_resolver(resolver)

class _dialog_ok_and_loot(_dialog_and_loot):
    FACTORY_TUNABLES = {'dialog': UiDialogOk.TunableFactory(description='\n            The dialog with an ok button that we will display to the user.\n            '), 'on_dialog_complete_loot_list': TunableList(description='\n            A list of loot that will be applied when the player responds to the\n            dialog or, if the dialog is a phone ring or text message, when the\n            dialog times out due to the player ignoring it for too long.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), 'on_dialog_seen_loot_list': TunableList(description='\n            A list of loot that will be applied when player responds to the\n            message.  If the dialog is a phone ring or text message then this\n            loot will not be triggered when the dialog times out due to the\n            player ignoring it for too long.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))}

    def on_node_run(self, drama_node):
        resolver = drama_node._get_resolver()
        target_sim_id = drama_node._sender_sim_info.id if drama_node._sender_sim_info is not None else None
        dialog = self.dialog(drama_node._receiver_sim_info, target_sim_id=target_sim_id, resolver=resolver)

        def response(dialog):
            for loot_action in self.on_dialog_complete_loot_list:
                loot_action.apply_to_resolver(resolver)
            if dialog.response != ButtonType.DIALOG_RESPONSE_NO_RESPONSE:
                for loot_action in self.on_dialog_seen_loot_list:
                    loot_action.apply_to_resolver(resolver)
            DialogDramaNode.apply_cooldown_on_response(drama_node)

        dialog.show_dialog(on_response=response)

class _dialog_ok_cancel_and_loot(_dialog_and_loot):
    FACTORY_TUNABLES = {'dialog': UiDialogOkCancel.TunableFactory(description='\n            The ok cancel dialog that will display to the user.\n            '), 'on_dialog_complete_loot_list': TunableList(description='\n            A list of loot that will be applied when the player responds to the\n            dialog or, if the dialog is a phone ring or text message, when the\n            dialog times out due to the player ignoring it for too long.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), 'on_dialog_accetped_loot_list': TunableList(description='\n            A list of loot operations to apply when the player chooses ok.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), 'on_dialog_canceled_loot_list': TunableList(description='\n            A list of loot operations to apply when the player chooses cancel.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True))}

    def on_node_run(self, drama_node):
        resolver = drama_node._get_resolver()
        target_sim_id = drama_node._sender_sim_info.id if drama_node._sender_sim_info is not None else None
        dialog = self.dialog(drama_node._receiver_sim_info, target_sim_id=target_sim_id, resolver=resolver)

        def response(dialog):
            for loot_action in self.on_dialog_complete_loot_list:
                loot_action.apply_to_resolver(resolver)
            if dialog.response is not None:
                if dialog.response == ButtonType.DIALOG_RESPONSE_OK:
                    for loot_action in self.on_dialog_accetped_loot_list:
                        loot_action.apply_to_resolver(resolver)
                elif dialog.response == ButtonType.DIALOG_RESPONSE_CANCEL:
                    for loot_action in self.on_dialog_canceled_loot_list:
                        loot_action.apply_to_resolver(resolver)
            DialogDramaNode.apply_cooldown_on_response(drama_node)

        dialog.show_dialog(on_response=response)

class DialogDramaNode(BaseDramaNode):
    INSTANCE_TUNABLES = {'dialog_and_loot': TunableVariant(description='\n            The type of dialog and loot that will be applied.\n            ', notification=_notification_and_loot.TunableFactory(), dialog_ok=_dialog_ok_and_loot.TunableFactory(), dialog_ok_cancel=_dialog_ok_cancel_and_loot.TunableFactory(), default='notification')}

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.DIALOG

    def _run(self):
        self.dialog_and_loot.on_node_run(self)
        return True

    @classmethod
    def apply_cooldown_on_response(cls, drama_node):
        if drama_node.cooldown_option == CooldownOption.ON_DIALOG_RESPONSE:
            services.drama_scheduler_service().start_cooldown(drama_node)
