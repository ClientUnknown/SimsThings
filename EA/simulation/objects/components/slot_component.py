from _collections import defaultdictfrom weakref import WeakKeyDictionaryfrom autonomy.autonomy_modifier import TunableAutonomyModifierfrom interactions import ParticipantTypefrom interactions.utils.tunable_provided_affordances import TunableProvidedAffordancesfrom objects.components import types, componentmethod, componentmethod_with_fallbackfrom objects.components.get_put_component_mixin import GetPutComponentMixinfrom objects.components.state import ObjectStateValuefrom objects.components.types import NativeComponentfrom objects.object_enums import ResetReasonfrom objects.slots import get_slot_type_set_from_key, DecorativeSlotTuning, RuntimeSlotfrom postures.stand import StandSuperInteractionfrom sims4 import hash_utilfrom sims4.tuning.tunable import TunableList, TunableSet, Tunablefrom singletons import EMPTY_SET, DEFAULTimport native.animationimport servicesimport sims4.callback_utilsimport sims4.loglogger = sims4.log.Logger('SlotComponent')_slot_types_cache = {}_deco_slot_hashes = {}
def purge_cache():
    _slot_types_cache.clear()
    _deco_slot_hashes.clear()
sims4.callback_utils.add_callbacks(sims4.callback_utils.CallbackEvent.TUNING_CODE_RELOAD, purge_cache)
class SlotComponent(GetPutComponentMixin, NativeComponent, component_name=types.SLOT_COMPONENT, key=787604481):
    FACTORY_TUNABLES = {'autonomy_modifiers': TunableList(description='\n            Objects parented to this object will have these autonomy modifiers\n            applied to them.\n            ', tunable=TunableAutonomyModifier(locked_args={'relationship_multipliers': None})), 'return_owned_objects': Tunable(description="\n            If enabled, child objects will return to their owner's inventory\n            when this object is destroyed in the specified item location.\n            \n            We first consider the closest instanced Sims, and finally move to\n            the household inventory if we can't move to a Sim's inventory.\n            ", tunable_type=bool, default=False), 'slot_provided_affordances': TunableProvidedAffordances(description='\n            Affordances provided on objects slotted into the owner of this\n            component.\n            ', class_restrictions=('SuperInteraction',), locked_args={'allow_self': False, 'target': ParticipantType.Object, 'carry_target': ParticipantType.Invalid, 'is_linked': False}), 'state_values': TunableSet(description='\n            Objects parented to this object will have these state values applied to\n            them.  The original value will be restored if the child is removed.\n            ', tunable=ObjectStateValue.TunableReference())}
    _handles = None
    _state_values = None

    def __init__(self, *args, autonomy_modifiers=DEFAULT, return_owned_objects=DEFAULT, slot_provided_affordances=DEFAULT, state_values=DEFAULT, **kwargs):
        super().__init__(*args, **kwargs)
        self.autonomy_modifiers = autonomy_modifiers if autonomy_modifiers is not DEFAULT else None
        self.return_owned_objects = return_owned_objects if return_owned_objects is not DEFAULT else None
        self.slot_provided_affordances = slot_provided_affordances if slot_provided_affordances is not DEFAULT else None
        self.state_values = state_values if state_values is not DEFAULT else None
        self._containment_slot_info_cache = None

    def component_reset(self, reset_reason):
        if not self.owner.is_on_active_lot():
            household_manager = services.household_manager()
            for child in list(self.owner.children_recursive_gen()):
                household_id = child.get_household_owner_id()
                if household_id is not None:
                    household = household_manager.get(household_id)
                    if household is not None:
                        household.move_object_to_sim_or_household_inventory(child, sort_by_distance=True)

    def on_child_added(self, child, location):
        if child.statistic_component is not None:
            if self._handles is None:
                self._handles = WeakKeyDictionary()
            if child not in self._handles:
                child.add_statistic_component()
                handles = []
                for modifier in self.autonomy_modifiers:
                    handles.append(child.add_statistic_modifier(modifier))
                self._handles[child] = handles
        if self.autonomy_modifiers and self.state_values:
            if self._state_values is None:
                self._state_values = WeakKeyDictionary()
            if child not in self._state_values:
                state_values = []
                for state_value in self.state_values:
                    state = state_value.state
                    if not child.has_state(state):
                        pass
                    else:
                        current_value = child.get_state(state)
                        if current_value != state_value:
                            state_values.append(current_value)
                            child.set_state(state, state_value)
                self._state_values[child] = state_values
        if self.slot_provided_affordances:
            flags = set()
            for provided_affordance_data in self.slot_provided_affordances:
                if not provided_affordance_data.object_filter.is_object_valid(child):
                    pass
                else:
                    flags |= provided_affordance_data.affordance.commodity_flags
            if flags and not child.is_prop:
                child.add_dynamic_commodity_flags(self, flags)
        child.on_placed_in_slot(self.owner)
        if child.display_component is not None:
            child.display_component.slotted_to_object(self.owner)
        if child.state_component and child.state_component.overlapping_slot_states:
            self.owner.register_for_on_children_changed_callback(child.state_component.handle_overlapping_slots)
            child.state_component.handle_overlapping_slots(child, location)

    def on_child_removed(self, child, new_parent=None):
        if child in self._handles:
            child.add_statistic_component()
            handles = self._handles.pop(child)
            for handle in handles:
                child.remove_statistic_modifier(handle)
        if child in self._state_values:
            state_values = self._state_values.pop(child)
            for state_value in state_values:
                child.set_state(state_value.state, state_value)
        if not (self._handles and self._state_values and child.is_prop):
            child.remove_dynamic_commodity_flags(self)
        child.on_removed_from_slot(self.owner)
        if child.display_component is not None:
            child.display_component.unslotted_from_object(self.owner)
        if child.state_component and child.state_component.overlapping_slot_states:
            self.owner.unregister_for_on_children_changed_callback(child.state_component.handle_overlapping_slots)

    @componentmethod
    def get_surface_access_constraint(self, sim, is_put, carry_target):
        return self._get_access_constraint(sim, is_put, carry_target)

    @componentmethod
    def get_surface_access_animation(self, put):
        return self._get_access_animation(put)

    @staticmethod
    def to_slot_hash(slot_name_or_hash):
        if slot_name_or_hash is None:
            return 0
        if isinstance(slot_name_or_hash, int):
            return slot_name_or_hash
        else:
            return hash_util.hash32(slot_name_or_hash)

    @componentmethod
    def get_slot_info(self, slot_name_or_hash=None, object_slots=None):
        slot_type_containment = sims4.ObjectSlots.SLOT_CONTAINMENT
        owner = self.owner
        if object_slots is None:
            object_slots = owner.slots_resource
        slot_name_hash = SlotComponent.to_slot_hash(slot_name_or_hash)
        if self.has_slot(slot_name_hash, object_slots):
            slot_transform = object_slots.get_slot_transform_by_hash(slot_type_containment, slot_name_hash)
            return (slot_name_hash, slot_transform)
        raise KeyError('Slot {} not found on owner object: {}'.format(slot_name_or_hash, owner))

    @componentmethod
    def has_slot(self, slot_name_or_hash, object_slots=None):
        owner = self.owner
        if object_slots is None:
            object_slots = owner.slots_resource
        return object_slots.has_slot(sims4.ObjectSlots.SLOT_CONTAINMENT, SlotComponent.to_slot_hash(slot_name_or_hash))

    @componentmethod
    def get_deco_slot_hashes(self, deco_slot_hash_index):
        if deco_slot_hash_index not in _deco_slot_hashes:
            self.get_containment_slot_infos()
        if deco_slot_hash_index in _deco_slot_hashes:
            return _deco_slot_hashes[deco_slot_hash_index]
        return frozenset()

    def get_containment_slot_infos(self):
        object_slots = self.owner.slots_resource
        if object_slots is None:
            logger.warn('Attempting to get slots from object {} with no slot', self.owner)
            return []
        if self._containment_slot_info_cache is None:
            self._containment_slot_info_cache = self.get_containment_slot_infos_static(object_slots, self.owner.rig, self.owner)
        return self._containment_slot_info_cache

    @staticmethod
    def get_containment_slot_infos_static(object_slots, rig, owner):
        subroot_index = owner.subroot_index if owner is not None and owner.is_part else None
        if (rig, subroot_index) in _deco_slot_hashes:
            deco_slot_hashes = None
        else:
            deco_slot_hashes = []
        containment_slot_infos = []
        for slot_index in range(object_slots.get_slot_count(sims4.ObjectSlots.SLOT_CONTAINMENT)):
            slot_hash = object_slots.get_slot_name_hash(sims4.ObjectSlots.SLOT_CONTAINMENT, slot_index)
            key = (rig, slot_index)
            if key in _slot_types_cache:
                slot_types = _slot_types_cache[key]
                if slot_types:
                    containment_slot_infos.append((slot_hash, slot_types))
                    slot_type_set_key = object_slots.get_containment_slot_type_set(slot_index)
                    deco_size = object_slots.get_containment_slot_deco_size(slot_index)
                    slot_types = set()
                    slot_type_set = get_slot_type_set_from_key(slot_type_set_key)
                    if slot_type_set is not None:
                        slot_types.update(slot_type_set.slot_types)
                    slot_types.update(DecorativeSlotTuning.get_slot_types_for_slot(deco_size))
                    if slot_types:
                        try:
                            native.animation.get_joint_transform_from_rig(rig, slot_hash)
                        except KeyError:
                            slot_name = sims4.hash_util.unhash_with_fallback(slot_hash)
                            rig_name = None
                            rig_name = rig_name or str(rig)
                            logger.error("Containment slot {} doesn't have matching bone in {}'s rig ({}). This slot cannot be used by gameplay systems.", slot_name, owner, rig_name)
                            slot_types = ()
                        except ValueError:
                            rig_name = None
                            rig_name = rig_name or str(rig)
                            logger.error('RigName: {} with rig key: {} does not exist for object {}.  ', rig_name, rig, owner)
                            slot_types = ()
                    if deco_slot_hashes is not None and DecorativeSlotTuning.slot_types_are_all_decorative(slot_types):
                        deco_slot_hashes.append(slot_hash)
                    slot_types = frozenset(slot_types)
                    _slot_types_cache[key] = slot_types
                    if slot_types:
                        containment_slot_infos.append((slot_hash, slot_types))
            else:
                slot_type_set_key = object_slots.get_containment_slot_type_set(slot_index)
                deco_size = object_slots.get_containment_slot_deco_size(slot_index)
                slot_types = set()
                slot_type_set = get_slot_type_set_from_key(slot_type_set_key)
                if slot_type_set is not None:
                    slot_types.update(slot_type_set.slot_types)
                slot_types.update(DecorativeSlotTuning.get_slot_types_for_slot(deco_size))
                if slot_types:
                    try:
                        native.animation.get_joint_transform_from_rig(rig, slot_hash)
                    except KeyError:
                        slot_name = sims4.hash_util.unhash_with_fallback(slot_hash)
                        rig_name = None
                        rig_name = rig_name or str(rig)
                        logger.error("Containment slot {} doesn't have matching bone in {}'s rig ({}). This slot cannot be used by gameplay systems.", slot_name, owner, rig_name)
                        slot_types = ()
                    except ValueError:
                        rig_name = None
                        rig_name = rig_name or str(rig)
                        logger.error('RigName: {} with rig key: {} does not exist for object {}.  ', rig_name, rig, owner)
                        slot_types = ()
                if deco_slot_hashes is not None and DecorativeSlotTuning.slot_types_are_all_decorative(slot_types):
                    deco_slot_hashes.append(slot_hash)
                slot_types = frozenset(slot_types)
                _slot_types_cache[key] = slot_types
                if slot_types:
                    containment_slot_infos.append((slot_hash, slot_types))
        if deco_slot_hashes:
            if owner is not None and owner.parts:
                part_deco_slot_lists = defaultdict(list)
                part_owner = owner.part_owner if owner.is_part else owner
                stand_body_posture_type = StandSuperInteraction.STAND_POSTURE_TYPE
                parts = tuple(p for p in part_owner.parts if p.supports_posture_type(stand_body_posture_type))
                if parts:
                    for deco_slot_hash in deco_slot_hashes:
                        closest_part = None
                        joint_transform = native.animation.get_joint_transform_from_rig(rig, deco_slot_hash)
                        location = sims4.math.Location(joint_transform, None, parent=owner, slot_hash=deco_slot_hash)
                        slot_position = location.transform.translation
                        closest_part = min(parts, key=lambda p: (p.get_joint_transform().translation - slot_position).magnitude_2d_squared())
                        deco_list = part_deco_slot_lists[closest_part]
                        deco_list.append(deco_slot_hash)
                        part_deco_slot_lists[closest_part] = deco_list
                else:
                    logger.error('Object {} has deco slots but none of its parts supports stand.', part_owner)
                _deco_slot_hashes[(rig, None)] = frozenset()
                for (part, deco_slot_list) in part_deco_slot_lists.items():
                    _deco_slot_hashes[(rig, (part.subroot_index, part.part_definition))] = frozenset(deco_slot_list)
            else:
                _deco_slot_hashes[(rig, None)] = frozenset(deco_slot_hashes)
        return containment_slot_infos

    @componentmethod_with_fallback(lambda part=None: EMPTY_SET)
    def get_provided_slot_types(self, part=None):
        result = set()
        for (_, slot_types) in (part or self).get_containment_slot_infos():
            result.update(slot_types)
        return result

    @componentmethod_with_fallback(lambda slot_types=None, bone_name_hash=None, owner_only=False: iter(()))
    def get_runtime_slots_gen(self, slot_types=None, bone_name_hash=None, owner_only=False):
        owner = self.owner
        parts = owner.parts
        for (slot_hash, slot_slot_types) in self.get_containment_slot_infos():
            if not slot_types is not None or not slot_types.intersection(slot_slot_types):
                pass
            elif not bone_name_hash is not None or slot_hash != bone_name_hash:
                pass
            else:
                if not parts:
                    yield RuntimeSlot(owner, slot_hash, slot_slot_types)
                elif owner_only:
                    pass
                else:
                    for p in parts:
                        if p.has_slot(slot_hash):
                            yield RuntimeSlot(p, slot_hash, slot_slot_types)
                            break
                    yield RuntimeSlot(owner, slot_hash, slot_slot_types)
                for p in parts:
                    if p.has_slot(slot_hash):
                        yield RuntimeSlot(p, slot_hash, slot_slot_types)
                        break
                yield RuntimeSlot(owner, slot_hash, slot_slot_types)

    @componentmethod_with_fallback(lambda parent_slot=None, slotting_object=None, target=None, object_to_ignore=None: False)
    def slot_object(self, parent_slot=None, slotting_object=None, target=None, objects_to_ignore=None):
        if target is None:
            target = self.owner
        if isinstance(parent_slot, str):
            runtime_slot = RuntimeSlot(self.owner, sims4.hash_util.hash32(parent_slot), EMPTY_SET)
            if runtime_slot is None:
                logger.warn('The target object {} does not have a slot {}', self.owner, parent_slot, owner='nbaker')
                return False
            if runtime_slot.is_valid_for_placement(obj=slotting_object, objects_to_ignore=objects_to_ignore):
                runtime_slot.add_child(slotting_object)
                return True
            logger.warn("The target object {} slot {} isn't valid for placement", self.owner, parent_slot, owner='nbaker')
        if parent_slot is not None:
            for runtime_slot in target.get_runtime_slots_gen(slot_types={parent_slot}, bone_name_hash=None):
                if runtime_slot.is_valid_for_placement(obj=slotting_object, objects_to_ignore=objects_to_ignore):
                    runtime_slot.add_child(slotting_object)
                    return True
            logger.warn('The created object {} cannot be placed in the slot {} on target object or part {}', slotting_object, parent_slot, target, owner='nbaker')
            return False

    @componentmethod_with_fallback(lambda *_, **__: iter(()))
    def child_provided_aops_gen(self, target, context, **kwargs):
        if self.slot_provided_affordances:
            for provided_affordance_data in self.slot_provided_affordances:
                if not provided_affordance_data.object_filter.is_object_valid(target):
                    pass
                else:
                    yield from provided_affordance_data.affordance.potential_interactions(target, context, **kwargs)

    def validate_definition(self):
        if self.owner.parts:
            invalid_runtime_slots = []
            for runtime_slot in self.get_runtime_slots_gen(owner_only=True):
                surface_slot_types = ', '.join(sorted(t.__name__ for t in runtime_slot.slot_types if t.is_surface))
                if surface_slot_types:
                    invalid_runtime_slots.append('{} ({})'.format(runtime_slot.slot_name_or_hash, surface_slot_types))
            if invalid_runtime_slots:
                part_tuning = []
                for part in sorted(self.owner.parts, key=lambda p: -1 if p.is_base_part else p.subroot_index):
                    part_name = 'Base Part' if part.is_base_part else 'Part {}'.format(part.subroot_index)
                    part_definition = part.part_definition
                    part_tuning.append('        {:<10} {}'.format(part_name + ':', part_definition.__name__))
                    if part_definition.subroot is not None:
                        part_tuning.append('          {}'.format(part_definition.subroot.__name__))
                        for bone_name in part_definition.subroot.bone_names:
                            part_tuning.append('            {}'.format(bone_name))
                part_tuning = '\n'.join(part_tuning)
                invalid_runtime_slots.sort()
                invalid_runtime_slots = '\n'.join('        ' + i for i in invalid_runtime_slots)
                error_message = '\n    This multi-part object has some surface slots that don\'t belong to any of\n    its parts. (Surface slots are slots that have a Slot Type Set or Deco Size\n    configured in Medator.) There are several possible causes of this error:\n    \n      * The slot isn\'t actually supposed to be a containment slot, and the slot\n        type set or deco size needs to be removed in Medator.\n    \n      * If there are decorative slots that aren\'t part of a subroot, the object\n        needs a "base part" -- a part with no subroot index to own the deco \n        slots. This needs to be added to the object\'s part tuning.\n      \n      * If these slots are normally part of a subroot, there may be a part\n        missing from the object\'s tuning, or one or more of the part types might\n        be wrong. This might mean the object tuning and catalog product don\'t\n        match, possibly because the person who assigned object tuning to the\n        catalog products thought two similar models could share exactly the same\n        tuning but they don\'t use the same rig.\n        \n      * There may be some bone names missing from one or more of the subroots\'\n        tuning files.\n        \n    Here are the names of the orphan slots (and the slot types tuned on them):\n{}\n\n    Here is the current part tuning for {}:\n{}'.format(invalid_runtime_slots, type(self.owner).__name__, part_tuning)
                raise ValueError(error_message)
