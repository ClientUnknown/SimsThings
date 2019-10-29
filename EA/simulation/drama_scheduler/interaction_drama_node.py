from drama_scheduler.drama_node import BaseDramaNode, CooldownOptionfrom drama_scheduler.drama_node_types import DramaNodeTypefrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReferencefrom sims4.utils import classpropertyfrom ui.ui_dialog import UiDialogOkCancelimport interactionsimport servicesimport sims4.resources
class RunAffordanceDramaNode(BaseDramaNode):
    INSTANCE_TUNABLES = {'dialog': UiDialogOkCancel.TunableFactory(description='\n            The ok cancel dialog that will display to the user.\n            '), 'affordance': TunableReference(description="\n            The affordance that will be pushed on the receiving Sim once the\n            dialog is accepted.  This affordance will be pushed at high\n            priority next in the Sim's queue.  The sending Sim will be placed\n            in the picked Sims.\n            ", manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions='SuperInteraction')}

    @classproperty
    def drama_node_type(cls):
        return DramaNodeType.INTERACTION

    def _push_affordance(self, dialog):
        if not dialog.accepted:
            services.drama_scheduler_service().complete_node(self.uid)
            return
        sim = self._receiver_sim_info.get_sim_instance()
        if sim is None:
            services.drama_scheduler_service().complete_node(self.uid)
            return
        context = interactions.context.InteractionContext(sim, interactions.context.InteractionContext.SOURCE_SCRIPT_WITH_USER_INTENT, interactions.priority.Priority.High, insert_strategy=interactions.context.QueueInsertStrategy.NEXT, bucket=interactions.context.InteractionBucketType.DEFAULT)
        if self._sender_sim_info is not None:
            picked_sim_ids = (self._sender_sim_info.id,)
        else:
            picked_sim_ids = tuple()
        sim.push_super_affordance(self.affordance, sim, context, picked_item_ids=picked_sim_ids)
        services.drama_scheduler_service().complete_node(self.uid)

    def _run(self):
        resolver = self._get_resolver()
        target_sim_id = self._sender_sim_info.id if self._sender_sim_info is not None else None
        dialog = self.dialog(self._receiver_sim_info, target_sim_id=target_sim_id, resolver=resolver)
        dialog.show_dialog(on_response=self._push_affordance)
        return False
lock_instance_tunables(RunAffordanceDramaNode, cooldown_option=CooldownOption.ON_RUN)