from event_testing.resolver import SingleObjectResolverfrom objects.components import Component, typesfrom objects.components.state import TunableStateValueReferencefrom objects.object_tests import CraftTaggedItemFactory, InventoryTestfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, Tunable, TunableList, TunableTupleimport services
class DisplayComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=types.DISPLAY_COMPONENT):
    DISPLAY_STATE = TunableStateValueReference(description='\n        The state a display object will be set to when it is parented to a\n        Display Parent.\n        ')
    DEFAULT_STATE = TunableStateValueReference(description='\n        The default state a display object will be set to when it is unparented\n        from a Display Parent.\n        ')
    FACTORY_TUNABLES = {'display_parent': CraftTaggedItemFactory(description='\n            If an object matches the tag(s), it will be considered a Display\n            Parent for this display object. All display objects with a Display\n            Component MUST have a Display Parent tuned, otherwise there is no\n            need in the Display Component.\n            '), 'use_display_state': Tunable(description="\n            If enabled, this object will change to the Display State when it is\n            parented to a Display Parent. The Display State is tuned in the\n            objects.components.display_component module tuning. NOTICE: If you\n            are only tuning this and not tuning any Inventory State Triggers,\n            it's recommended that you use the Slot Component in the Native\n            Components section of the parent object.\n            ", tunable_type=bool, default=True), 'inventory_state_triggers': TunableList(description='\n            Change states on the owning object based on tests applied to the\n            inventory of the Display Parent. Tests will be done in order and\n            will stop at the first success.\n            ', tunable=TunableTuple(inventory_test=InventoryTest.TunableFactory(), set_state=TunableStateValueReference()))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.inventory_state_triggers:
            services.get_event_manager().register_tests(self, (self.inventory_state_triggers[0].inventory_test,))

    @property
    def _is_on_display_parent(self):
        parent = self.owner.parent
        if parent is None:
            return False
        return self.display_parent(crafted_object=parent, skill=None) is not None

    def handle_event(self, sim_info, event, resolver):
        if sim_info is not None:
            return
        if not self._is_on_display_parent:
            return
        self._handle_inventory_changed()

    def _handle_inventory_changed(self):
        obj_resolver = SingleObjectResolver(self.owner)
        for trigger in self.inventory_state_triggers:
            if obj_resolver(trigger.inventory_test):
                if self.owner.has_state(trigger.set_state.state):
                    self.owner.set_state(trigger.set_state.state, trigger.set_state)
                break

    def slotted_to_object(self, parent):
        if self._should_change_display_state(parent) and self.owner.has_state(self.DISPLAY_STATE.state):
            self.owner.set_state(self.DISPLAY_STATE.state, self.DISPLAY_STATE)
        self._handle_inventory_changed()

    def unslotted_from_object(self, parent):
        if self._should_change_display_state(parent) and self.owner.has_state(self.DEFAULT_STATE.state):
            self.owner.set_state(self.DEFAULT_STATE.state, self.DEFAULT_STATE)

    def _should_change_display_state(self, parent):
        if not self.use_display_state:
            return False
        return self.display_parent(crafted_object=parent, skill=None)
