import weakreffrom protocolbuffers import FileSerialization_pb2, UI_pb2 as ui_protocolsfrom build_buy import ObjectOriginLocationfrom distributor.system import Distributorfrom event_testing.resolver import SingleObjectResolverfrom objects.components import Component, types, componentmethodfrom objects.components.inventory_storage import InventoryStoragefrom objects.components.inventory_type_tuning import InventoryTypeTuningfrom objects.object_enums import ResetReasonfrom placement import create_fgl_context_for_object, create_fgl_context_for_object_off_lot, create_starting_location, find_good_locationfrom services.reset_and_delete_service import ResetRecordfrom sims4.localization import LocalizationHelperTuningfrom singletons import DEFAULTfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport build_buyimport objects.systemimport servicesimport sims4.loglogger = sims4.log.Logger(types.INVENTORY_COMPONENT.class_attr, default_owner='tingyul')TELEMETRY_GROUP_INVENTORY = 'INVT'TELEMETRY_HOOK_ADD_TO_INV = 'IADD'TELEMETRY_HOOK_REMOVE_FROM_INV = 'IREM'TELEMETRY_HOOK_TOGGLE_LOCK = 'LOCK'TELEMETRY_FIELD_ID = 'guid'TELEMETRY_FIELD_INV_TYPE = 'type'TELEMETRY_FIELD_IS_LOCKED = 'ison'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_INVENTORY)
class InventoryComponent(Component):
    PARENTED_OBJECT_MOVED_TO_HOUSEHOLD_INVENTORY_NOTIFICATION = TunableUiDialogNotificationSnippet(description='\n        If an object with children is moved to an inventory, display this\n        notification to communicate that some of its children have been moved to\n        the Household inventory.\n        ')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._storage = None
        self._hidden_storage = None
        self._published_to_client = False
        self._inventory_state_triggers = []
        self._forwarded_affordances_objects = None

    def __len__(self):
        return sum(obj.stack_count() for obj in self._storage)

    def __iter__(self):
        yield from self._storage
        yield from self._hidden_storage

    def __contains__(self, obj):
        return obj.id in self._storage or obj.id in self._hidden_storage

    @property
    def inventory_type(self):
        raise NotImplementedError

    @property
    def default_item_location(self):
        raise NotImplementedError

    @componentmethod
    def get_inventory_access_constraint(self, sim, is_put, carry_target, use_owner_as_target_for_resolver=False):
        raise NotImplementedError

    @componentmethod
    def get_inventory_access_animation(self, *args, **kwargs):
        raise NotImplementedError

    @property
    def should_score_contained_objects_for_autonomy(self):
        return True

    @property
    def use_top_item_tooltip(self):
        return False

    @property
    def visible_storage(self):
        return self._storage

    @property
    def hidden_storage(self):
        return self._hidden_storage

    def _get_inventory_count_statistic(self):
        pass

    def _get_inventory_object(self):
        return self.owner

    def on_object_inserted(self, obj, send_ui=True, object_with_inventory=None):
        for state_trigger in self._inventory_state_triggers:
            state_trigger.on_object_added(obj)
        self._update_inventory_count()
        self.owner.on_object_added_to_inventory(obj)
        self._update_tooltip()

    def on_object_removed(self, obj, send_ui=True, on_manager_remove=False):
        for state_trigger in self._inventory_state_triggers:
            state_trigger.on_obj_removed(obj)
        self._update_inventory_count()
        self.owner.on_object_removed_from_inventory(obj)
        self._update_tooltip()

    def on_object_id_changed(self, obj, old_obj_id, old_stack_count):
        self._update_inventory_count()
        self.owner.on_object_stack_id_updated(obj, old_obj_id, old_stack_count)

    def add_state_trigger(self, state_trigger):
        self._inventory_state_triggers.append(state_trigger)

    def object_state_update_callback(self, old_state, new_state):
        for state_trigger in self._inventory_state_triggers:
            state_trigger.obj_state_changed(old_state, new_state)
        self._update_tooltip()

    def _update_inventory_count(self):
        stat = self._get_inventory_count_statistic()
        if stat is None:
            return
        tracker = self.owner.get_tracker(stat)
        if tracker is not None:
            tracker.set_value(stat, len(self))

    def on_add(self):
        lot = services.active_lot()
        if self.is_shared_inventory:
            shared_inventory = lot.get_object_inventories(self.inventory_type)[0]
            self._storage = shared_inventory._storage
            self._hidden_storage = shared_inventory._hidden_storage
            self._update_inventory_count()
            for obj in self._storage:
                for state_trigger in self._inventory_state_triggers:
                    state_trigger.on_object_added(obj)
        else:
            self._storage = InventoryStorage(self.inventory_type, self.default_item_location, max_size=InventoryTypeTuning.get_max_inventory_size_for_inventory_type(self.inventory_type), allow_ui=self.allow_ui)
            self._hidden_storage = InventoryStorage(self.inventory_type, self.default_item_location, allow_compaction=False, allow_ui=False, hidden_storage=True)
            lot.inventory_owners[self.inventory_type].add(self.owner)
        self._update_inventory_count()
        self._storage.register(self)

    @property
    def allow_ui(self):
        return True

    def on_remove(self):
        self._storage.unregister(self)
        if not self.is_shared_inventory:
            self.purge_inventory()

    @property
    def is_shared_inventory(self):
        return InventoryTypeTuning.is_shared_between_objects(self.inventory_type)

    @property
    def inventory_value(self):
        return sum(obj.current_value*obj.stack_count() for obj in self)

    @property
    def has_owning_object(self):
        return self._storage.has_owners()

    def owning_objects_gen(self):
        yield from (owning_component.owner for owning_component in self._storage.get_owners())

    def can_add(self, obj, hidden=False):
        if obj.inventoryitem_component is None:
            return False
        hidden = hidden or not obj.inventoryitem_component.visible
        storage = self._hidden_storage if hidden else self._storage
        return storage.can_insert(obj)

    def player_try_add_object(self, obj, hidden=False):
        if not self.can_add(obj):
            return False
        self._insert_item(obj, force_add_to_hidden_inventory=hidden)
        return True

    def system_add_object(self, obj):
        if not self.can_add(obj):
            logger.error('Attempt to add object ({}) which failed the common test.', obj)
            obj.destroy(source=self.owner, cause='Failed attempt to add object to an inventory using system_add_object(). Object was destroyed.')
            return
        self._insert_item(obj)

    def add_from_load(self, obj, hidden=False):
        self._insert_item(obj, force_add_to_hidden_inventory=hidden, compact=False)

    def _insert_item(self, obj, force_add_to_hidden_inventory=False, compact=True):
        self._handle_parented_objects(obj)
        hidden = force_add_to_hidden_inventory or not obj.inventoryitem_component.visible
        storage = self._hidden_storage if hidden else self._storage
        storage.insert(obj, inventory_object=self._get_inventory_object(), compact=compact)
        return True

    def update_object_stack_by_id(self, obj_id, new_stack_id):
        storage = None
        if obj_id in self._storage:
            storage = self._storage
        elif obj_id in self._hidden_storage:
            storage = self._hidden_storage
        if storage is None:
            return False
        storage.update_object_stack_by_id(obj_id, new_stack_id)
        return True

    def try_remove_object_by_id(self, obj_id, count=1, on_manager_remove=False):
        storage = None
        if obj_id in self._storage:
            storage = self._storage
        elif obj_id in self._hidden_storage:
            storage = self._hidden_storage
        if storage is None:
            return False
        obj = storage[obj_id]
        storage.remove(obj, count=count, move_to_object_manager=not on_manager_remove)
        return True

    def _allow_destruction_on_inventory_transfer(self, obj):
        if obj.consumable_component is not None and obj.consumable_component.allow_destruction_on_inventory_transfer:
            return True
        if obj.has_servings_statistic():
            return True
        elif obj.inventoryitem_component is not None and obj.inventoryitem_component.always_destroy_on_inventory_transfer:
            return True
        return False

    def _handle_parented_objects(self, obj):
        objects_in_household_inventory = []
        for child_obj in tuple(obj.children):
            if self._allow_destruction_on_inventory_transfer(child_obj):
                child_obj.destroy(source=self.owner, cause='Parent is being inventoried.')
            elif self.player_try_add_object(child_obj):
                pass
            elif build_buy.move_object_to_household_inventory(child_obj):
                objects_in_household_inventory.append(child_obj)
            else:
                world_obj = self.owner
                fgl_context_fn = create_fgl_context_for_object if world_obj.is_on_active_lot() else create_fgl_context_for_object_off_lot
                fgl_starting_location = create_starting_location(position=world_obj.position)
                (translation, orientation) = find_good_location(fgl_context_fn(fgl_starting_location, child_obj))
                if translation is not None and orientation is not None:
                    child_obj.set_parent(None, transform=sims4.math.Transform(translation, orientation), routing_surface=world_obj.routing_surface)
                else:
                    child_obj.destroy(source=self.owner, cause="Parent is being inventoried and object can't be placed anywhere.")
        if objects_in_household_inventory and self.PARENTED_OBJECT_MOVED_TO_HOUSEHOLD_INVENTORY_NOTIFICATION is not None:
            sim_info = self.owner.sim_info if self.owner.is_sim else services.active_sim_info()
            notification = self.PARENTED_OBJECT_MOVED_TO_HOUSEHOLD_INVENTORY_NOTIFICATION(sim_info, resolver=SingleObjectResolver(obj))
            notification.show_dialog(additional_tokens=(LocalizationHelperTuning.get_bulleted_list((None,), (LocalizationHelperTuning.get_object_name(obj) for obj in objects_in_household_inventory)),))

    def purge_inventory(self):
        for obj in tuple(self):
            obj.destroy(source=self.owner, cause='inventory purge')

    def try_destroy_object_by_definition(self, obj_def, source=None, cause=None):
        obj = self.get_item_with_definition(obj_def)
        if obj is not None and self.try_remove_object_by_id(obj.id):
            if obj.in_use:
                obj.transient = True
            else:
                obj.destroy(source=source, cause=cause)
            return True
        return False

    def try_destroy_object(self, obj, count=1, source=None, cause=None):
        if self.try_remove_object_by_id(obj.id, count=count):
            obj.destroy(source=source, cause=cause)
            return True
        return False

    def try_move_object_to_hidden_inventory(self, obj, count=1):
        if obj.id not in self._storage:
            logger.warn("Tried moving item, {}, to hidden inventory, but item was not found in the Sim's, {}, inventory.", obj, self.owner)
            return False
        self._storage.remove(obj, count=count)
        self._hidden_storage.insert(obj, self.owner)
        return True

    def try_move_hidden_object_to_inventory(self, obj, count=1):
        if obj.id not in self._hidden_storage:
            logger.error("Tried removing object from hidden inventory, {}, but it couldn't be found.", obj)
            return False
        self._hidden_storage.remove(obj, count=count)
        self._storage.insert(obj, self.owner)
        return True

    def is_object_hidden(self, obj):
        return obj.id in self._hidden_storage

    def get_items_for_autonomy_gen(self, motives=DEFAULT):
        for obj in tuple(self._storage):
            if motives is DEFAULT or obj.commodity_flags & motives:
                yield obj

    def get_items_with_definition_gen(self, obj_def, ignore_hidden=False):
        yield from (obj for obj in self._storage if obj.definition is obj_def)
        if not ignore_hidden:
            yield from (obj for obj in self._hidden_storage if obj.definition is obj_def)

    def get_item_with_definition(self, obj_def, ignore_hidden=False):
        for obj in self.get_items_with_definition_gen(obj_def, ignore_hidden):
            return obj

    def has_item_with_definition(self, obj_def):
        return any(obj.definition is obj_def for obj in self)

    def get_count(self, obj_def):
        return sum(obj.stack_count() for obj in self if obj.definition is obj_def)

    def get_count_by_tag(self, obj_tag):
        return sum(obj.stack_count() for obj in self if obj.has_tag(obj_tag))

    def get_objects_by_tag(self, obj_tag):
        return [obj for obj in self if obj.has_tag(obj_tag)]

    def get_item_quantity_by_definition(self, obj_def):
        return sum(obj.stack_count() for obj in self.get_items_with_definition_gen(obj_def))

    def get_stack_items(self, stack_id):
        items = []
        for obj in self:
            obj_stack_id = obj.inventoryitem_component.get_stack_id()
            if obj_stack_id == stack_id:
                items.append(obj)
        items.sort(key=lambda item: item.get_stack_sort_order())
        return items

    def get_item_update_ops_gen(self):
        yield from self._storage.get_item_update_ops_gen()

    @componentmethod
    def inventory_view_update(self):
        for obj in self._storage:
            if obj.new_in_inventory:
                obj.new_in_inventory = False
                self._storage.distribute_inventory_update_message(obj)

    def publish_inventory_items(self, items_own_ops=False):
        if not self.allow_ui:
            return
        if self._published_to_client:
            logger.error("{}'s inventory has already been published to client. You may see duplicate entries!", self.owner)
            return
        distributor = Distributor.instance()
        if items_own_ops:
            for (obj, message_op) in self.get_item_update_ops_gen():
                distributor.add_op(obj, message_op)
        else:
            for (_, message_op) in self.get_item_update_ops_gen():
                distributor.add_op_with_no_owner(message_op)
        self._published_to_client = True

    def push_inventory_item_update_msg(self, obj):
        if obj.id in self._storage:
            self._storage.distribute_inventory_update_message(obj)

    def open_ui_panel(self):
        self._storage.open_ui_panel(self.owner)

    def _on_save_items(self, object_list):
        pass

    def save_items(self):
        if self.is_shared_inventory:
            return
        object_list = FileSerialization_pb2.ObjectList()
        for obj in self:
            obj.save_object(object_list.objects, item_location=self.default_item_location, container_id=self.owner.id)
        self._on_save_items(object_list)
        return object_list

    def _on_load_items(self):
        pass

    def _load_item(self, definition_id, obj_data):
        self._create_inventory_object(definition_id, obj_data)

    def load_items(self, object_list):
        if self.is_shared_inventory:
            return
        if not object_list.objects:
            return
        zone_id = services.current_zone_id()
        for obj_data in object_list.objects:
            def_id = build_buy.get_vetted_object_defn_guid(zone_id, obj_data.object_id, obj_data.guid or obj_data.type)
            if def_id is not None:
                self._load_item(def_id, obj_data)
        self._on_load_items()

    def _create_inventory_object(self, definition_id, obj_data):
        objects.system.create_object(definition_id, obj_id=obj_data.object_id, loc_type=obj_data.loc_type, post_add=lambda o: self._post_create_object(o, obj_data))

    def _post_create_object(self, obj, obj_data):
        try:
            obj.load_object(obj_data)
            if obj not in self:
                if self.can_add(obj):
                    self.add_from_load(obj)
                else:
                    logger.error("{} can't go into {}'s inventory. Destroying it.", obj, self.owner)
                    obj.destroy(source=self.owner, cause='Inventory load failed')
        except:
            logger.exception('Exception thrown while loading an object in an inventory. \nObject: {} Owner: {}', obj, self.owner)
            self._storage.discard_object_id(obj.id)
            self._hidden_storage.discard_object_id(obj.id)
            obj.destroy(source=self.owner, cause='Inventory load failed')

    def push_items_to_household_inventory(self):
        client = services.client_manager().get_first_client()
        for obj in list(self._storage):
            if obj in client.live_drag_objects:
                client.cancel_live_drag(obj)
            if self._allow_destruction_on_inventory_transfer(obj):
                pass
            else:
                try:
                    if self.try_remove_object_by_id(obj.id, count=obj.stack_count()) and not build_buy.move_object_to_household_inventory(obj, object_location_type=ObjectOriginLocation.SIM_INVENTORY):
                        logger.error('{} failed to push object from inventory to household inventory', obj)
                except Exception:
                    logger.exception('{} failed to push object from inventory to household inventory', obj)

    def on_reset_component_get_interdependent_reset_records(self, reset_reason, reset_records):
        if self.is_shared_inventory:
            return
        if reset_reason == ResetReason.BEING_DESTROYED:
            for obj in self:
                reset_records.append(ResetRecord(obj, reset_reason, self, 'In inventory'))
            self._storage.discard_all_objects()
            self._hidden_storage.discard_all_objects()

    def _update_tooltip(self):
        if not self.use_top_item_tooltip:
            return
        inventory_object = self.owner
        top_item = self._get_top_item()
        if top_item:
            inventory_object.hover_tip = top_item.hover_tip
        else:
            inventory_object.hover_tip = ui_protocols.UiObjectMetadata.HOVER_TIP_DISABLED
        inventory_object.update_object_tooltip()

    def _get_top_item(self):
        if self._storage:
            return list(self._storage)[0]

    @componentmethod
    def get_tooltip_override(self):
        if self.use_top_item_tooltip and self._storage:
            return self._get_top_item()

    @componentmethod
    def get_component_potential_interactions_gen(self, context, get_interaction_parameters, **kwargs):
        if self._forwarded_affordances_objects is not None:
            for inv_obj in self._forwarded_affordances_objects:
                yield from inv_obj.potential_interactions(context, get_interaction_parameters, from_inventory_to_owner=True, **kwargs)

    def add_forwarded_object(self, obj):
        if self._forwarded_affordances_objects is None:
            self._forwarded_affordances_objects = weakref.WeakSet()
        self._forwarded_affordances_objects.add(obj)

    def remove_forwarded_object(self, obj):
        if self._forwarded_affordances_objects is not None:
            self._forwarded_affordances_objects.remove(obj)
            if not self._forwarded_affordances_objects:
                self._forwarded_affordances_objects = None
