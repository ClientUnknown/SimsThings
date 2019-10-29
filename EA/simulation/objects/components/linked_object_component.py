from _weakrefset import WeakSetimport operatorfrom objects.components import componentmethod_with_fallbackfrom objects.object_enums import ResetReasonfrom services.reset_and_delete_service import ResetRecordfrom sims4.tuning.geometric import TunableDistanceSquaredfrom sims4.tuning.tunable import HasTunableFactory, TunableEnumWithFilter, AutoFactoryInit, TunableRange, TunablePackSafeReference, OptionalTunableimport build_buyimport objects.components.typesimport servicesimport sims4.logimport sims4.resourcesimport taglogger = sims4.log.Logger('LinkedObjectComponent', default_owner='nabaker')
class LinkedObjectComponent(AutoFactoryInit, objects.components.Component, HasTunableFactory, allow_dynamic=True, component_name=objects.components.types.LINKED_OBJECT_COMPONENT):
    FACTORY_TUNABLES = {'_parent_state_value': OptionalTunable(description="\n            When enabled, this state will be applied to the parent when\n            it has children.\n            \n            For example, the default link state for the console is unlinked.\n            If you set this to the linked state, then when it becomes the\n            parent to a T.V. it'll change the console to the linked state.\n            When the T.V. is unlinked, the console will revert back to \n            the unlinked state.\n            ", tunable=TunablePackSafeReference(description='\n                state value to apply to parent objects.\n                Behaves as disabled if state not in installed data.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',))), '_child_state_value': OptionalTunable(description="\n            When enabled, this state will be applied to the children.\n\n            For example, the default link state for a T.V is unlinked.\n            If you set this to the linked state, then when it becomes the\n            child of a console. it'll change the T.V. to the linked state.\n            When the T.V. is unlinked, the T.V. will revert back to \n            the unlinked state.\n            ", tunable=TunablePackSafeReference(description='\n                state value to apply to child objects.\n                Behaves as disabled if state not in installed data.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',))), '_child_tag': TunableEnumWithFilter(description='\n            Tag that determines which objects can be linked.\n            ', tunable_type=tag.Tag, filter_prefixes=['func'], default=tag.Tag.INVALID, invalid_enums=(tag.Tag.INVALID,)), '_distance': TunableDistanceSquared(description='\n            Max distance from component owner and still be\n            linkable.\n            ', default=3), '_count': TunableRange(description='\n            Max number of children to link.\n            ', tunable_type=int, default=1, minimum=1)}

    def __init__(self, *args, parent=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._children = WeakSet()
        self._parent = self.owner
        self._return_state_value = None
        self._is_parent = parent

    def on_add(self):
        self._start()

    def on_remove(self):
        self._stop()

    def on_added_to_inventory(self):
        self._stop()

    def on_removed_from_inventory(self):
        self._start()
        if self._is_parent:
            self._add_all()

    def component_reset(self, reset_reason):
        if reset_reason != ResetReason.BEING_DESTROYED:
            self._relink(from_reset=True)
        elif self._is_parent:
            self.unlink_all_children()

    def on_finalize_load(self):
        self._relink()

    def on_post_load(self):
        if self._is_parent and self._children:
            self._return_state_value = None
            self.link(None, self._parent_state_value)

    def on_location_changed(self, old_location):
        if services.current_zone().is_zone_loading or self._parent is not self.owner:
            self._relink(update_others=not services.current_zone().is_in_build_buy)

    def on_reset_component_get_interdependent_reset_records(self, reset_reason, reset_records):
        owner_users = self.owner.get_users()
        for obj in self.get_linked_objects_gen():
            if self._has_active_link(owner_users, obj):
                reset_records.append(ResetRecord(obj, ResetReason.RESET_EXPECTED, self, 'Linked object reset'))

    def _start(self):
        self._parent = None
        if self._is_parent:
            build_buy.register_build_buy_exit_callback(self._relink)

    def _add_all(self):
        self._children = self._get_nearby_objects()
        for child in self._children:
            self._link_child(child)
        if self._children:
            self.link(None, self._parent_state_value)

    def _stop(self):
        if self._parent is self.owner:
            return
        old_parent = self._parent
        self._parent = self.owner
        if self._is_parent:
            build_buy.unregister_build_buy_exit_callback(self._relink)
            self.unlink_all_children()
        elif old_parent is not None:
            old_parent.linked_object_component.child_unlinked(self.owner)

    def unlink_all_children(self, update_others=False):
        for child in self._children:
            self._unlink(child)
        if update_others:
            self._update_others(self._children)
        self._children.clear()
        self.unlink_self()

    def _has_active_link(self, owner_users, severed_object):
        return owner_users & severed_object.get_users()

    def _relink(self, update_others=False, from_reset=False):
        if self._is_parent:
            if not self._children:
                self._add_all()
                return
            new_children = self._get_nearby_objects()
            removed_children = self._children - new_children
            if not from_reset:
                owner_users = self.owner.get_users()
                for child in removed_children:
                    if self._has_active_link(owner_users, child):
                        self.owner.reset(ResetReason.RESET_EXPECTED, None, 'Unlinking child')
                        return
            if not new_children:
                self.unlink_all_children(update_others=update_others)
                return
            for child in removed_children:
                self._unlink(child)
            for child in new_children - self._children:
                self._link_child(child)
            self._children = new_children
            if removed_children and update_others:
                self._update_others(removed_children)
        elif self._parent is not None:
            self._parent.linked_object_component.refresh(self.owner)

    def refresh(self, child):
        if self._is_parent:
            if child not in self._children:
                logger.error("Refreshing linked child: {} that isn't in parent {}", child, self.owner)
                return
            child.linked_object_component.link(self.owner, self._child_state_value)

    def unlink_self(self):
        if self._parent is not self.owner:
            self._parent = None
        if self._return_state_value is not None:
            self.owner.state_component.reset_state_to_default(self._return_state_value)
        self._return_state_value = None

    def _unlink(self, child):
        if child not in self._children:
            logger.error("Removing linked child: {} that isn't in parent {}", child, self.owner)
            return
        child.reset(ResetReason.RESET_EXPECTED, self.owner, 'Unlinking from parent')
        child.linked_object_component.unlink_self()
        child.remove_component(objects.components.types.LINKED_OBJECT_COMPONENT)

    def child_unlinked(self, child):
        if child not in self._children:
            logger.error("Removing linked child: {} that isn't in parent {}", child, self.owner)
            return
        self._relink()

    def _link_child(self, child):
        if child.linked_object_component is None:
            child.add_dynamic_component(objects.components.types.LINKED_OBJECT_COMPONENT, parent=False, _parent_state_value=None, _child_tag=None, _child_state_value=None, _count=None, _distance=None)
        child.linked_object_component.link(self.owner, self._child_state_value)

    def link(self, parent, state_value):
        self._parent = parent
        if state_value is not None:
            state_component = self.owner.state_component
            if state_component is not None:
                state = state_value.state
                if state_component.has_state(state):
                    self._return_state_value = state_component.get_state(state)
                state_component.set_state(state_value.state, state_value)

    @componentmethod_with_fallback(lambda : [])
    def get_linked_objects_gen(self):
        if self._is_parent:
            yield from self._children
        elif self._parent is not self.owner:
            yield self._parent
            for child in self._parent.linked_object_component.get_linked_objects_gen():
                if child is not self.owner:
                    yield child

    def _get_nearby_objects(self):
        if self.owner.is_hidden():
            return ()
        filtered_near_objects = []
        nearby_objects = services.object_manager().get_objects_with_tag_gen(self._child_tag)
        for test_object in nearby_objects:
            if self._is_valid_child(test_object):
                dist_square = (self.owner.position - test_object.position).magnitude_2d_squared()
                if dist_square < self._distance:
                    filtered_near_objects.append((dist_square, test_object))
        filtered_near_objects.sort(key=operator.itemgetter(0))
        return_list = set([x[1] for x in filtered_near_objects[:self._count]])
        return return_list

    def _is_valid_child(self, test_object):
        linked_object_component = test_object.linked_object_component
        if linked_object_component is not None:
            if linked_object_component._is_parent:
                return False
            if linked_object_component._parent is not self.owner and test_object.linked_object_component._parent is not None:
                return False
        if test_object.level != self.owner.level:
            return False
        elif test_object.is_hidden():
            return False
        return True

    def _update_others(self, new_children):
        owner = self.owner
        for obj in services.object_manager().get_valid_objects_gen():
            if obj.linked_object_component is not None and obj is not owner:
                new_children = obj.linked_object_component._try_add_links(new_children)
                if not new_children:
                    break

    def _try_add_links(self, new_children):
        if self.owner is self._parent:
            return new_children
        if len(self._children) == self._count:
            return new_children
        else:
            filtered_near_objects = []
            for test_object in new_children:
                if test_object.has_tag(self._child_tag) and test_object.level == self.owner.level:
                    dist_square = (self.owner.position - test_object.position).magnitude_2d_squared()
                    if dist_square < self._distance:
                        filtered_near_objects.append((dist_square, test_object))
            if filtered_near_objects:
                filtered_near_objects.sort(key=operator.itemgetter(0))
                new_set = set([x[1] for x in filtered_near_objects[:self._count - len(self._children)]])
                for child in new_set:
                    self._link_child(child)
                if not self._children:
                    self.link(None, self._parent_state_value)
                self._children |= new_set
                return new_children - new_set
        return new_children
