from protocolbuffers import UI_pb2, DistributorOps_pb2from distributor.ops import GenericProtocolBufferOpfrom distributor.system import Distributorfrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom sims4.tuning.tunable import TunableReference, TunableThreshold, TunableTuplefrom socials.group import SocialGroupimport enumimport servicesimport sims4
class InterrogationUpdateType(enum.Int, export=False):
    TYPE_START = 0
    TYPE_UPDATE = 1
    TYPE_STOP = 2

class InterrogationGroup(SocialGroup):
    INSTANCE_TUNABLES = {'interrogation_statistic': TunableReference(description='\n            Statistic to listen to display on the interrogation\n            progress.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), 'interrogation_end_interaction_data': TunableTuple(description='\n            Tunable information corresponding at the interaction that \n            will be pushed when the interrogation is done. \n            All these tunables are required.\n            ', interrogation_statistic_threshold=TunableThreshold(description='\n                The threshold that the interrogation stat value will be\n                compared to.  If the threshold returns true then the\n                interrogation end interaction will be pushed from the interrogation\n                actor to its interrogation target.\n                '), interrogation_end_interaction=TunableReference(description='\n                The affordance to push on from the officer (Actor of interaction)\n                to the suspect (TargetSim of interaction).\n                ', manager=services.affordance_manager()))}

    def __init__(self, *args, **kwargs):
        self._interrogation_callback = None
        super().__init__(*args, **kwargs)

    def pre_add(self, *_, **__):
        stat_tracker = self._initiating_sim.get_tracker(self.interrogation_statistic)
        stat_tracker.add_statistic(self.interrogation_statistic)
        op = self._get_interrogation_op(InterrogationUpdateType.TYPE_START)
        Distributor.instance().add_op(self._initiating_sim, op)

    def _interrogation_statistic_callback(self, stat_type, old_value, new_value):
        if self.interrogation_statistic is not stat_type:
            return
        op = self._get_interrogation_op(InterrogationUpdateType.TYPE_UPDATE)
        Distributor.instance().add_op(self._initiating_sim, op)
        if self._initiating_sim is not None and self._target_sim is not None and self.interrogation_end_interaction_data.interrogation_statistic_threshold.compare(new_value):
            context = InteractionContext(self._initiating_sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
            self._initiating_sim.push_super_affordance(self.interrogation_end_interaction_data.interrogation_end_interaction, self._target_sim, context)

    def _get_interrogation_op(self, msg_type):
        if self._target_sim is None or self._initiating_sim is None:
            return
        if self._interrogation_callback is None:
            self._initialize_interrogate_group()
        stat_tracker = self._initiating_sim.get_tracker(self.interrogation_statistic)
        stat_instance = stat_tracker.get_statistic(self.interrogation_statistic)
        if stat_instance is None:
            decay_rate = 0
            stat_value = 0
        else:
            decay_rate = stat_instance.get_change_rate()
            stat_value = stat_instance._value
        interrogation_update = UI_pb2.InterrogationProgressUpdate()
        interrogation_update.type = msg_type
        interrogation_update.target_id = self._target_sim.id
        interrogation_update.value = stat_value
        interrogation_update.decay_rate = decay_rate
        return GenericProtocolBufferOp(DistributorOps_pb2.Operation.INTERROGATION_PROGRESS_UPDATE, interrogation_update)

    def _initialize_interrogate_group(self):
        stat_tracker = self._initiating_sim.get_tracker(self.interrogation_statistic)
        if self._interrogation_callback is None:
            self._interrogation_callback = stat_tracker.add_watcher(self._interrogation_statistic_callback)

    def shutdown(self, finishing_type):
        if self._initiating_sim:
            stat_tracker = self._initiating_sim.get_tracker(self.interrogation_statistic)
            if stat_tracker.has_watcher(self._interrogation_callback):
                stat_tracker.remove_watcher(self._interrogation_callback)
            op = self._get_interrogation_op(InterrogationUpdateType.TYPE_STOP)
            Distributor.instance().add_op(self._initiating_sim, op)
        super().shutdown(finishing_type)
