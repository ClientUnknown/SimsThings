from weakref import WeakSetfrom element_utils import soft_sleep_foreverfrom interactions.priority import PriorityExtendedfrom interactions.utils.loot import LootActions, LootOperationListfrom objects.components import Component, types, componentmethodfrom objects.components.utils.footprint_toggle_mixin import FootprintToggleMixinfrom routing.object_routing.object_routing_behavior import ObjectRoutingBehaviorfrom sims.master_controller import WorkRequestfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableMapping, TunableReference, OptionalTunable, TunableTuple, TunableListfrom singletons import UNSETimport servicesimport sims4.resourcesfrom event_testing.resolver import SingleObjectResolver
class ObjectRoutingComponent(FootprintToggleMixin, Component, HasTunableFactory, AutoFactoryInit, component_name=types.OBJECT_ROUTING_COMPONENT):
    FACTORY_TUNABLES = {'routing_behavior_map': TunableMapping(description='\n            A mapping of states to behavior. When the object enters a state, its\n            corresponding routing behavior is started.\n            ', key_type=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue'), value_type=OptionalTunable(tunable=ObjectRoutingBehavior.TunableReference(), enabled_by_default=True, enabled_name='Start_Behavior', disabled_name='Stop_All_Behavior', disabled_value=UNSET)), 'privacy_rules': OptionalTunable(description='\n            If enabled, this object will care about privacy regions.\n            ', tunable=TunableTuple(description='\n                Privacy rules for this object.\n                ', on_enter=TunableTuple(description='\n                    Tuning for when this object is considered a violator of\n                    privacy.\n                    ', loot_list=TunableList(description='\n                        A list of loot operations to apply when the object\n                        enters a privacy region.\n                        ', tunable=LootActions.TunableReference(pack_safe=True)))))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._running_behavior = None
        self._idle_element = None
        self._previous_parent_ref = None
        self._pending_running_behavior = None
        self._privacy_violations = WeakSet()

    @property
    def previous_parent(self):
        if self._previous_parent_ref is not None:
            return self._previous_parent_ref()

    def _setup(self):
        master_controller = services.get_master_controller()
        master_controller.add_sim(self.owner)
        if self.privacy_rules:
            privacy_service = services.privacy_service()
            privacy_service.add_vehicle_to_monitor(self.owner)
        self.owner.routing_component.on_sim_added()
        self.add_callbacks()

    def on_add(self, *_, **__):
        zone = services.current_zone()
        if not zone.is_zone_loading:
            self._setup()

    def on_finalize_load(self):
        self._setup()

    def on_remove(self):
        self.remove_callbacks()
        self.owner.routing_component.on_sim_removed()
        master_controller = services.get_master_controller()
        master_controller.remove_sim(self.owner)
        if self.privacy_rules:
            privacy_service = services.privacy_service()
            privacy_service.remove_vehicle_to_monitor(self.owner)

    def add_callbacks(self):
        if self.privacy_rules:
            self.owner.register_on_location_changed(self._check_privacy)
        self.register_routing_event_callbacks()

    def remove_callbacks(self):
        if self.owner.is_on_location_changed_callback_registered(self._check_privacy):
            self.owner.unregister_on_location_changed(self._check_privacy)
        self.unregister_routing_event_callbacks()

    def handle_privacy_violation(self, privacy):
        if not self.privacy_rules:
            return
        resolver = SingleObjectResolver(self.owner)
        loots = LootOperationList(resolver, self.privacy_rules.on_enter.loot_list)
        loots.apply_operations()
        if privacy not in self._privacy_violations:
            self._privacy_violations.add(privacy)

    def violates_privacy(self, privacy):
        if not self.privacy_rules:
            return False
        elif not privacy.vehicle_violates_privacy(self.owner):
            return False
        return True

    def _check_privacy(self, _, old_location, new_location):
        if not self.privacy_rules:
            return
        for privacy in services.privacy_service().privacy_instances:
            new_violation = privacy not in self._privacy_violations
            violates_privacy = self.violates_privacy(privacy)
            if new_violation:
                if violates_privacy:
                    self.handle_privacy_violation(privacy)
                    if not violates_privacy:
                        self._privacy_violations.discard(privacy)
            elif not violates_privacy:
                self._privacy_violations.discard(privacy)

    def on_state_changed(self, state, old_value, new_value, from_init):
        if new_value is old_value:
            return
        if new_value not in self.routing_behavior_map:
            return
        self._stop_runnning_behavior()
        routing_behavior_type = self.routing_behavior_map[new_value]
        if routing_behavior_type is UNSET:
            return
        routing_behavior = routing_behavior_type(self.owner)
        self._running_behavior = routing_behavior
        self._cancel_idle_behavior()

    def on_location_changed(self, old_location):
        parent = self.owner.parent
        if parent is not None:
            self._previous_parent_ref = parent.ref()

    def component_reset(self, reset_reason):
        if self._running_behavior is not None:
            self._pending_running_behavior = type(self._running_behavior)
            self._running_behavior.trigger_hard_stop()
            self._running_behavior = None
        services.get_master_controller().on_reset_sim(self.owner, reset_reason)

    def post_component_reset(self):
        if self._pending_running_behavior is not None:
            self._running_behavior = self._pending_running_behavior(self.owner)
            self._pending_running_behavior = None
            self._cancel_idle_behavior()

    def _cancel_idle_behavior(self):
        if self._idle_element is not None:
            self._idle_element.trigger_soft_stop()
            self._idle_element = None

    @componentmethod
    def get_idle_element(self):
        self._idle_element = soft_sleep_forever()
        return (self._idle_element, self._cancel_idle_behavior)

    @componentmethod
    def get_next_work(self):
        if self._running_behavior is None or self.owner.has_work_locks:
            return WorkRequest()
        work_request = WorkRequest(work_element=self._running_behavior, required_sims=(self.owner,))
        return work_request

    @componentmethod
    def get_next_work_priority(self):
        return PriorityExtended.SubLow

    @componentmethod
    def on_requested_as_resource(self, other_work):
        if not any(resource.is_sim for resource in other_work.resources):
            return
        self.restart_running_behavior()

    def restart_running_behavior(self):
        routing_behavior_type = type(self._running_behavior) if self._running_behavior is not None else None
        self._stop_runnning_behavior()
        if routing_behavior_type is not None:
            routing_behavior = routing_behavior_type(self.owner)
            self._running_behavior = routing_behavior

    def _stop_runnning_behavior(self):
        if self._running_behavior is not None:
            self._running_behavior.trigger_soft_stop()
            self._running_behavior = None
