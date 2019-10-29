import collectionsfrom protocolbuffers import GameplaySaveData_pb2from distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimResolverfrom global_policies.global_policy_effects import ScheduleUtilityShutOfffrom global_policies.global_policy_enums import GlobalPolicyProgressEnumfrom sims4.service_manager import Servicefrom sims4.utils import classpropertyimport date_and_timeimport elementsimport persistence_error_typesimport servicesimport sims4
class GlobalPolicyService(Service):

    def __init__(self):
        self._global_policies = {}
        self._bill_reductions = collections.Counter()
        self._utility_effects = {}

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_GLOBAL_POLICY_SERVICE

    def save(self, save_slot_data=None, **__):
        global_policy_service_proto = GameplaySaveData_pb2.PersistableGlobalPolicyService()
        for global_policy in self._global_policies.values():
            with ProtocolBufferRollback(global_policy_service_proto.global_policies) as global_policy_proto:
                global_policy_proto.progress_state = global_policy.progress_state
                global_policy_proto.progress_value = global_policy.progress_value
                if global_policy.decay_handler is not None:
                    global_policy_proto.decay_days = global_policy.decay_handler.when
                global_policy_proto.snippet = global_policy.guid64
        for (bill_reduction_reason, bill_reduction_amt) in self._bill_reductions.items():
            with ProtocolBufferRollback(global_policy_service_proto.bill_reductions) as global_policy_bill_reduction:
                global_policy_bill_reduction.bill_reduction_reason = bill_reduction_reason
                global_policy_bill_reduction.bill_reduction_amount = bill_reduction_amt
        for effect_global_policy_id in self._utility_effects.keys():
            with ProtocolBufferRollback(global_policy_service_proto.utility_effects) as global_policy_utility:
                global_policy_utility.global_policy_snippet_guid64 = effect_global_policy_id
        save_slot_data.gameplay_data.global_policy_service = global_policy_service_proto

    def setup(self, save_slot_data=None, **__):
        global_policy_service_proto = save_slot_data.gameplay_data.global_policy_service
        global_policy_tuning_manager = services.get_instance_manager(sims4.resources.Types.SNIPPET)
        for global_policy_data in global_policy_service_proto.global_policies:
            global_policy_snippet = global_policy_tuning_manager.get(global_policy_data.snippet)
            if global_policy_snippet is None:
                pass
            else:
                global_policy_instance = global_policy_snippet()
                global_policy_instance.pre_load(global_policy_data)
                self._global_policies[global_policy_instance.resource_key] = global_policy_instance
        for bill_reduction_data in global_policy_service_proto.bill_reductions:
            self.add_bill_reduction(bill_reduction_data.bill_reduction_reason, bill_reduction_data.bill_reduction_amount)
        for utility_effect_data in global_policy_service_proto.utility_effects:
            effect_global_policy_id = global_policy_tuning_manager.get(utility_effect_data.global_policy_snippet_guid64)
            active_effect_policy = self._global_policies.get(effect_global_policy_id.resource_key)
            for effect in active_effect_policy.global_policy_effects:
                if type(effect) is ScheduleUtilityShutOff:
                    self.add_utility_effect(active_effect_policy.guid64, effect)

    def load(self, **_):
        decaying_policy_gen = (policy for policy in self._global_policies.values() if policy.end_time_from_load != 0)
        for policy in decaying_policy_gen:
            self.set_up_decay_handler(policy, end_time_from_load=policy.end_time_from_load)
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        if not save_slot_data_msg.gameplay_data.HasField('global_policy_service'):
            return
        for (active_policy_id, effects) in self._utility_effects.items():
            for effect in effects:
                effect.turn_on(active_policy_id, from_load=True)

    def get_global_policies(self):
        return self._global_policies.values()

    def get_enacted_global_policies(self):
        return [policy for policy in self._global_policies.values() if policy.progress_state == GlobalPolicyProgressEnum.COMPLETE]

    def create_global_policy(self, global_policy_class):
        global_policy = global_policy_class()
        self._global_policies[global_policy_class.resource_key] = global_policy
        return global_policy

    def get_global_policy(self, global_policy_class, create=True):
        global_policy = self._global_policies.get(global_policy_class.resource_key)
        if global_policy is None and create:
            return self.create_global_policy(global_policy_class)
        else:
            return global_policy

    def add_global_policy_progress(self, global_policy_class, amount, resolver=None):
        global_policy = self.get_global_policy(global_policy_class)
        if amount > 0 and (global_policy.progress_state == GlobalPolicyProgressEnum.COMPLETE or global_policy.decay_handler is not None):
            return
        if resolver is None:
            resolver = SingleSimResolver(services.active_sim_info())
        new_value = global_policy.progress_value + amount
        self.set_global_policy_progress(global_policy, new_value, resolver)

    def set_global_policy_progress(self, global_policy, new_value, resolver=None):
        with services.conditional_layer_service().defer_conditional_layer_event_processing():
            old_state = global_policy.progress_state
            new_state = global_policy.set_progress_value(new_value)
            if new_state != old_state and new_state == GlobalPolicyProgressEnum.COMPLETE:
                self.set_up_decay_handler(global_policy)
                global_policy.apply_policy_loot_to_active_sim(global_policy.loot_on_complete, resolver)

    def set_up_decay_handler(self, global_policy, end_time_from_load=None):
        if global_policy.decay_handler is None:
            timeline = services.time_service().sim_timeline
            start_time = services.time_service().sim_now
            if end_time_from_load:
                end_time = date_and_time.DateAndTime(end_time_from_load)
            else:
                end_time = start_time + date_and_time.create_time_span(days=global_policy.decay_days)
            global_policy.decay_handler = timeline.schedule(elements.GeneratorElement(global_policy.decay_policy), end_time)

    def add_bill_reduction(self, reduction_reason, reduction):
        bill_reduction = self._bill_reductions.get(reduction_reason)
        if bill_reduction:
            self._bill_reductions[reduction_reason] *= reduction
        else:
            self._bill_reductions[reduction_reason] = reduction

    def remove_bill_reduction(self, reduction_reason):
        if self._bill_reductions.get(reduction_reason):
            del self._bill_reductions[reduction_reason]

    def get_bill_reductions(self):
        return self._bill_reductions

    def add_utility_effect(self, global_policy_id, utility_effect):
        if global_policy_id not in self._utility_effects:
            self._utility_effects[global_policy_id] = []
        self._utility_effects[global_policy_id].append(utility_effect)

    def remove_utility_effect(self, global_policy_id):
        if self._utility_effects.get(global_policy_id):
            del self._utility_effects[global_policy_id]
