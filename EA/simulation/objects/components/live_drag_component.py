from objects.components.types import NativeComponent, LIVE_DRAG_COMPONENTfrom objects.object_enums import ResetReasonfrom server.live_drag_operations import LiveDragStateOpfrom server.live_drag_tuning import LiveDragState, LiveDragLocation, LiveDragPermissionfrom sims4.tuning.tunable import HasTunableFactoryimport distributor.fieldsimport distributor.opsimport gsi_handlersimport servicesimport sims4.loglogger = sims4.log.Logger('LiveDragComponent', default_owner='rmccord')with sims4.reload.protected(globals()):
    force_live_drag_enable = False
class LiveDragComponent(NativeComponent, HasTunableFactory, component_name=LIVE_DRAG_COMPONENT, key=2125782609):
    FACTORY_TUNABLES = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._can_live_drag = True
        self._live_drag_user = None
        self._reservation_handler = None
        self._start_system = LiveDragLocation.INVALID
        self._live_drag_state = LiveDragState.NOT_LIVE_DRAGGING
        self._permissions = {}
        self._permissions = {p: True for p in LiveDragPermission}
        self._live_drag_state_ops = {}

    @property
    def live_drag_state(self):
        return self._live_drag_state

    @distributor.fields.ComponentField(op=distributor.ops.SetCanLiveDrag, default=None)
    def can_live_drag(self):
        return self._can_live_drag

    _resend_live_draggable = can_live_drag.get_resend()

    @property
    def active_household_has_sell_permission(self):
        owning_household_id = self.owner.get_household_owner_id()
        active_household_id = services.active_household_id()
        return owning_household_id == active_household_id

    def get_permission(self, permission_type):
        return self._permissions[permission_type]

    def update_permission(self, permission_type, has_permission):
        permission_changed = has_permission != self.get_permission(permission_type)
        if permission_changed:
            self._permissions[permission_type] = has_permission
            all_permissions = all(self._permissions.values()) or force_live_drag_enable and self.get_permission(LiveDragPermission.NOT_IN_USE)
            self._set_can_live_drag(all_permissions)

    def _set_can_live_drag(self, can_drag):
        if self.can_live_drag == can_drag:
            return
        self._can_live_drag = can_drag
        self._resend_live_draggable()
        self.log_can_live_drag()
        inventoryitem_component = self.owner.inventoryitem_component
        if inventoryitem_component is not None:
            inventory = inventoryitem_component.get_inventory()
            if inventory is not None:
                inventory.push_inventory_item_update_msg(self.owner)

    def component_reset(self, reset_reason):
        if self.live_drag_state == LiveDragState.NOT_LIVE_DRAGGING:
            return
        if reset_reason == ResetReason.BEING_DESTROYED:
            self._live_drag_user.cancel_live_drag(self.owner, LiveDragLocation.GAMEPLAY_SCRIPT)

    def on_add(self):
        self.owner.register_on_use_list_changed(self._on_owner_in_use_list_changed)

    def on_remove(self):
        self.owner.unregister_on_use_list_changed(self._on_owner_in_use_list_changed)

    def on_remove_from_client(self):
        self._set_can_live_drag(False)

    def on_post_load(self):
        self.resolve_live_drag_household_permission()

    def log_can_live_drag(self):
        if gsi_handlers.live_drag_handlers.live_drag_archiver.enabled:
            gsi_handlers.live_drag_handlers.archive_live_drag('Can Live Drag', 'Operation', LiveDragLocation.GAMEPLAY_SCRIPT, 'Client', live_drag_object=self.owner, live_drag_object_id=self.owner.id)

    def _on_owner_in_use_list_changed(self, user, added):
        if added and user is not self._live_drag_user:
            self.update_permission(LiveDragPermission.NOT_IN_USE, False)
            if self._live_drag_state == LiveDragState.LIVE_DRAGGING:
                self._live_drag_user.send_live_drag_cancel(self.owner.id, live_drag_end_system=LiveDragLocation.GAMEPLAY_SCRIPT)
        elif added or not any(user is not self._live_drag_user for user in self.owner.get_users()):
            self.update_permission(LiveDragPermission.NOT_IN_USE, True)

    def is_valid_drop_target(self, test_obj):
        owning_household_id = self.owner.get_household_owner_id()
        if test_obj.is_sim and owning_household_id is not None and owning_household_id != test_obj.household_id:
            return False
        elif test_obj.live_drag_target_component is not None:
            return test_obj.live_drag_target_component.can_add(self.owner)
        return False

    def get_valid_drop_object_ids(self):
        drop_target_ids = []
        for test_obj in services.object_manager().values():
            if test_obj.is_hidden() or self.is_valid_drop_target(test_obj):
                drop_target_ids.append(test_obj.id)
        if self.owner.inventoryitem_component is not None:
            return (drop_target_ids, self.owner.inventoryitem_component.get_stack_id())
        else:
            return (drop_target_ids, None)

    def start_live_dragging(self, reserver, start_system):
        if self.owner.in_use and not self.owner.in_use_by(self._live_drag_user):
            return False
        self._live_drag_user = reserver
        self._live_drag_state = LiveDragState.LIVE_DRAGGING
        self._reservation_handler = self.owner.get_reservation_handler(reserver)
        self._reservation_handler.begin_reservation()
        return True

    def cancel_live_dragging(self, should_reset=True):
        if self._reservation_handler is not None:
            self._reservation_handler.end_reservation()
            self._reservation_handler = None
        if should_reset:
            self.owner.reset(ResetReason.RESET_EXPECTED, self, 'cancel live drag.')
        self._live_drag_user = None
        self._live_drag_state = LiveDragState.NOT_LIVE_DRAGGING

    def resolve_live_drag_household_permission(self):
        owning_household_id = self.owner.get_household_owner_id()
        active_household_id = services.active_household_id()
        if active_household_id is not None and owning_household_id is not None and owning_household_id != active_household_id:
            self.update_permission(LiveDragPermission.HOUSEHOLD, False)
        else:
            self.update_permission(LiveDragPermission.HOUSEHOLD, True)

    def get_state_op_owners(self):
        return tuple(owner for (owner, op) in self._live_drag_state_ops.items() if op == LiveDragStateOp.LIVE_DRAG_OP_DISABLE)

    def resolve_live_drag_state_ops(self):
        permission = True
        for op in self._live_drag_state_ops.values():
            if op == LiveDragStateOp.LIVE_DRAG_OP_DISABLE and permission:
                permission = False
        self.update_permission(LiveDragPermission.STATE, permission)

    def add_live_drag_state_op(self, op_owner, op):
        self._live_drag_state_ops[op_owner] = op
        self.resolve_live_drag_state_ops()

    def remove_live_drag_state_op(self, op_owner):
        if op_owner not in self._live_drag_state_ops:
            logger.error('{} does not have a live drag state op in ops list on object {}', op_owner, self.owner)
        del self._live_drag_state_ops[op_owner]
        self.resolve_live_drag_state_ops()
