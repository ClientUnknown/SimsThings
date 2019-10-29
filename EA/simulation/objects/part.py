from _weakrefset import WeakSetfrom animation.animation_utils import AnimationOverridesfrom animation.arb_element import ArbElementfrom build_buy import is_location_poolfrom caches import cachedfrom event_testing.resolver import DoubleObjectResolverfrom interactions.utils.routing import RouteTargetTypefrom native.animation import get_joint_transform_from_rigfrom objects.components.slot_component import SlotComponentfrom objects.proxy import ProxyObjectfrom objects.slots import RuntimeSlotfrom postures.posture import TunablePostureTypeListSnippetfrom postures.posture_specs import BODY_INDEX, BODY_POSTURE_TYPE_INDEXfrom reservation.reservation_mixin import ReservationMixinfrom routing.portals.portal_data import TunablePortalReferencefrom sims4.hash_util import hash32from sims4.math import Transformfrom sims4.tuning.instances import TunedInstanceMetaclassfrom sims4.tuning.tunable import TunableList, TunableReference, Tunable, TunableTuple, TunableSet, HasTunableReference, TunableEnumEntry, TunableVariant, HasTunableSingletonFactory, AutoFactoryInitfrom sims4.tuning.tunable_hash import TunableStringHash32from sims4.utils import Result, constpropertyfrom singletons import DEFAULTfrom snippets import TunableAffordanceFilterSnippetfrom terrain import get_water_depthfrom traits.traits import Traitfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport routingimport servicesimport sims4.callback_utilsimport sims4.loglogger = sims4.log.Logger('Parts')
def purge_cache():
    ObjectPart._bone_name_hashes_for_part_suffices = None
sims4.callback_utils.add_callbacks(sims4.callback_utils.CallbackEvent.TUNING_CODE_RELOAD, purge_cache)
class _OverrideSurfaceType(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'override_surface_type': TunableEnumEntry(description="\n            The override for the surface type. If used, part owner's \n            surface type will be ignored.\n            ", tunable_type=routing.SurfaceType, default=routing.SurfaceType.SURFACETYPE_WORLD)}

    def get_surface_type(self, part, **kwargs):
        return self.override_surface_type

class _PartOwnerSurfaceType(HasTunableSingletonFactory, AutoFactoryInit):

    def get_surface_type(self, part, transform=None):
        owner = part.part_owner
        if owner.routing_surface is None:
            return
        return owner.routing_surface.type

class Part(ProxyObject, ReservationMixin):
    _unproxied_attributes = ProxyObject._unproxied_attributes | {'_data', '_reservation_handlers', '_joint_transform', '_routing_context', '_children_cache', '_is_surface', '_parts', '_part_location', '_containment_slot_info_cache'}

    def __init__(self, owner, data):
        super().__init__(owner)
        self._data = data
        self._reservation_handlers = ()
        self._joint_transform = None
        self._routing_context = None
        self._children_cache = None
        self._containment_slot_info_cache = None
        self._part_location = None
        self._is_surface = {}

    def __repr__(self):
        return '<part {0} on {1}>'.format(self.part_group_index, self.part_owner)

    def __str__(self):
        return '{}[{}]'.format(self.part_owner, self.part_group_index)

    @constproperty
    def is_part():
        return True

    @property
    def parts(self):
        pass

    @property
    def _parts(self):
        raise AttributeError()

    @property
    def part_owner(self):
        return self._proxied_obj

    @property
    def part_group_index(self):
        return self.part_owner.parts.index(self)

    @property
    def part_definition(self):
        return self._data.part_definition

    @property
    def disable_sim_aop_forwarding(self):
        return self._data.disable_sim_aop_forwarding

    @property
    def disable_child_aop_forwarding(self):
        return self._data.disable_child_aop_forwarding

    @property
    def forward_direction_for_picking(self):
        offset = self._data.forward_direction_for_picking
        return sims4.math.Vector3(offset.x, 0, offset.y)

    @property
    def transform(self):
        return self._part_location.world_transform

    @transform.setter
    def transform(self):
        raise AttributeError("A part's Transform should never be set by hand. Only the part owner's transform should be set.")

    def get_joint_transform(self):
        if self._joint_transform is None:
            if not self.is_base_part:
                target_root_joint = ArbElement._BASE_SUBROOT_STRING + str(self.subroot_index)
                try:
                    self._joint_transform = get_joint_transform_from_rig(self.rig, target_root_joint)
                except KeyError:
                    raise KeyError('Unable to find joint {} on {}'.format(target_root_joint, self))
                except ValueError:
                    raise ValueError('Unable to find rig for joint {} on {}'.format(self.rig, self))
            else:
                self._joint_transform = Transform.IDENTITY()
        return self._joint_transform

    def get_joint_transform_for_joint(self, joint_name):
        if isinstance(joint_name, str):
            joint_name = joint_name + str(self.subroot_index)
        else:
            joint_name = hash32(str(self.subroot_index), initial_hash=joint_name)
        transform = get_joint_transform_from_rig(self.rig, joint_name)
        transform = Transform.concatenate(transform, self.part_owner.transform)
        return transform

    @property
    def location(self):
        return self._part_location

    @property
    def routing_surface(self):
        return self._part_location.world_routing_surface

    def is_routing_surface_overlapped_at_position(self, position):
        return self.part_owner.is_routing_surface_overlapped_at_position(position)

    @property
    def provided_routing_surface(self):
        return self.part_owner.provided_routing_surface

    def on_children_changed(self):
        self._children_cache = None

    def _add_child(self, child, location):
        self.part_owner._add_child(child, location)
        self.on_children_changed()

    def _remove_child(self, child, new_parent=None):
        self.part_owner._remove_child(child, new_parent=new_parent)
        self.on_children_changed()

    @property
    def children(self):
        if self._children_cache is None:
            self._children_cache = WeakSet()
            for child in self.part_owner.children:
                if self.has_slot(child.location.slot_hash or child.location.joint_name_hash):
                    self._children_cache.add(child)
                elif self.part_owner.has_slot(child.location.slot_hash or child.location.joint_name_hash) and child.parts is not None:
                    for part in child.parts:
                        if part.attempt_to_remap_parent(part.location.parent) == self:
                            self._children_cache.add(part)
        return self._children_cache

    @property
    def routing_context(self):
        return self.part_owner.routing_context

    @property
    def supported_posture_types(self):
        return self.part_definition.supported_posture_types

    @property
    def _anim_overrides_internal(self):
        params = {}
        if any(p.in_use for p in self.part_owner.parts if p is not self and p.part_definition is self.part_definition):
            params['otherSimPresent'] = True
        overrides = super()._anim_overrides_internal
        if self._data.anim_overrides:
            overrides = overrides(self._data.anim_overrides())
        return AnimationOverrides(overrides=overrides, params=params)

    @property
    def can_reset(self):
        return False

    def reset(self, reset_reason):
        super().reset(reset_reason)
        self.part_owner.reset(reset_reason)

    def adjacent_parts_gen(self):
        if self._data.adjacent_parts is not None:
            parts = self.part_owner.parts
            for adjacent_part_index in self._data.adjacent_parts:
                yield parts[adjacent_part_index]
        else:
            index = self.part_group_index
            parts = self.part_owner.parts
            if index > 0:
                yield parts[index - 1]
            if index + 1 < len(parts):
                yield parts[index + 1]

    def has_adjacent_part(self, sim):
        for part in self.adjacent_parts_gen():
            if part.may_reserve(sim):
                return True
        return False

    def may_reserve(self, sim, *args, check_overlapping_parts=True, **kwargs):
        if check_overlapping_parts:
            for overlapping_part in self.get_overlapping_parts():
                if overlapping_part is self:
                    pass
                else:
                    reserve_result = overlapping_part.may_reserve(sim, check_overlapping_parts=False)
                    if not reserve_result:
                        return reserve_result
        return super().may_reserve(sim, *args, **kwargs)

    def is_mirrored(self, part=None):
        if part is None:
            return self._data.is_mirrored
        offset = part.position - self.position
        return sims4.math.vector_cross_2d(self.forward, offset) < 0

    @property
    def route_target(self):
        return (RouteTargetType.PARTS, (self,))

    @property
    def is_base_part(self):
        return self.subroot_index is None

    @property
    def subroot_index(self):
        if self._data is None:
            return
        return self._data.subroot_index

    @property
    def part_suffix(self) -> str:
        subroot_index = self.subroot_index
        if subroot_index is not None:
            return str(subroot_index)

    @cached(key=lambda p, a: (p.part_definition, a.affordance))
    def supports_affordance(self, affordance_or_aop):
        affordance = affordance_or_aop.affordance
        supported_affordance_data = self.part_definition.supported_affordance_data
        if affordance.is_super or not supported_affordance_data.consider_mixers:
            return True
        return supported_affordance_data.compatibility(affordance, allow_ignore_exclude_all=True)

    @cached(maxsize=512, key=lambda p, posture_type, *_, is_specific=True, **__: (p.part_definition, posture_type, is_specific))
    def supports_posture_type(self, posture_type, *_, is_specific=True, **__):
        if posture_type is None:
            return True
        part_supported_posture_types = {posture.posture_type for posture in self.part_definition.supported_posture_types}
        if not part_supported_posture_types:
            return True
        if is_specific:
            return posture_type in part_supported_posture_types
        return any(posture_type.family_name == supported_posture.family_name for supported_posture in part_supported_posture_types)

    def _supports_sim_buffs(self, sim):
        return not any(sim.has_buff(blacklisted_buff) for blacklisted_buff in self.part_definition.blacklisted_buffs)

    def _meets_trait_requirements(self, sim):
        if self.part_definition.trait_requirements is None:
            return True
        else:
            traits = sim.sim_info.get_traits()
            return self.part_definition.trait_requirements.test_collection(traits)

    def supports_posture_spec(self, posture_spec, interaction=None, sim=None):
        if interaction is not None and interaction.is_super:
            affordance = interaction.affordance
            if affordance.requires_target_support and not self.supports_affordance(affordance):
                return False
            is_sim_putdown = interaction.is_putdown and (interaction.carry_target is not None and interaction.carry_target.is_sim)
            test_sim = sim or interaction.sim
            if is_sim_putdown and interaction.carry_target is test_sim and not self._supports_sim_buffs(test_sim):
                return False
            if not self._meets_trait_requirements(test_sim):
                return False
        part_supported_posture_types = None
        if self.part_definition:
            part_supported_posture_types = self.part_definition.supported_posture_types
        if posture_spec[BODY_INDEX] is not None:
            for supported_posture_info in part_supported_posture_types:
                if posture_spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX] is supported_posture_info.posture_type:
                    posture_providing_interactions = [affordance for affordance in self.super_affordances() if affordance.provided_posture_type is posture_spec[BODY_INDEX][BODY_POSTURE_TYPE_INDEX]]
                    for interaction in posture_providing_interactions:
                        tests = self.affordancetuning_component.get_affordance_tests(interaction)
                        if tests is not None and not tests.run_tests(DoubleObjectResolver(sim, self.part_owner)):
                            return False
                    break
        return True

    @property
    def _bone_name_hashes(self):
        result = self.part_definition.get_bone_name_hashes_for_part_suffix(self.part_suffix)
        if self.part_owner.slot_component is not None:
            result |= self.get_deco_slot_hashes((self.part_owner.rig, (self.subroot_index, self.part_definition)))
        return result

    def get_provided_slot_types(self):
        return self.part_owner.get_provided_slot_types(part=self)

    def get_runtime_slots_gen(self, slot_types=None, bone_name_hash=None, owner_only=False):
        for (slot_hash, slot_slot_types) in self.get_containment_slot_infos():
            if not slot_types is not None or not slot_types.intersection(slot_slot_types):
                pass
            elif not bone_name_hash is not None or slot_hash != bone_name_hash:
                pass
            elif self.has_slot(slot_hash):
                yield RuntimeSlot(self, slot_hash, slot_slot_types)

    def slot_object(self, parent_slot=None, slotting_object=None, objects_to_ignore=None):
        return self.part_owner.slot_object(parent_slot=parent_slot, slotting_object=slotting_object, target=self, objects_to_ignore=objects_to_ignore)

    def get_containment_slot_infos(self):
        if self._containment_slot_info_cache is None:
            owner = self.part_owner
            object_slots = owner.slots_resource
            if object_slots is None:
                self._containment_slot_info_cache = ()
            else:
                result = SlotComponent.get_containment_slot_infos_static(object_slots, owner.rig, owner)
                bone_name_hashes = self._bone_name_hashes
                self._containment_slot_info_cache = tuple((slot_hash, slot_types) for (slot_hash, slot_types) in result if slot_hash in bone_name_hashes)
        return self._containment_slot_info_cache

    def is_valid_for_placement(self, *, obj=DEFAULT, definition=DEFAULT, objects_to_ignore=DEFAULT):
        result = Result.NO_RUNTIME_SLOTS
        for runtime_slot in self.get_runtime_slots_gen():
            result = runtime_slot.is_valid_for_placement(obj=obj, definition=definition, objects_to_ignore=objects_to_ignore)
            if result:
                break
        return result

    def has_slot(self, slot_hash):
        if slot_hash in self.part_definition.get_bone_name_hashes_for_part_suffix(self.part_suffix):
            return True
        elif slot_hash in self.get_deco_slot_hashes((self.part_owner.rig, (self.subroot_index, self.part_definition))):
            return True
        return False

    def get_overlapping_parts(self):
        if self._data.overlapping_parts is None:
            return []
        parts = self.part_owner.parts
        return [parts[overlapping_part_index] for overlapping_part_index in self._data.overlapping_parts]

    @property
    def footprint(self):
        return self.part_owner.footprint

    @property
    def footprint_polygon(self):
        return self.part_owner.footprint_polygon

    def on_leaf_child_changed(self):
        self.part_owner.on_leaf_child_changed()

    def on_owner_location_changed(self):
        owner = self.part_owner
        if owner.bb_parent is None:
            owner_transform = owner.transform
        else:
            owner_transform = owner.location.transform
        if self.subroot_index is None:
            transform = owner_transform
        else:
            transform = Transform.concatenate(self.get_joint_transform(), owner_transform)
        routing_surface = None
        surface_type = self.part_definition.part_surface.get_surface_type(self, transform=transform)
        if surface_type is not None:
            routing_surface = routing.SurfaceIdentifier(owner.zone_id, owner.level, surface_type)
        self._part_location = owner.location.clone(transform=transform, routing_surface=routing_surface)
        for child in self.children:
            if child.parts:
                for part in child.parts:
                    part.on_owner_location_changed()

class ObjectPart(HasTunableReference, metaclass=TunedInstanceMetaclass, manager=services.object_part_manager()):
    INSTANCE_TUNABLES = {'supported_posture_types': TunablePostureTypeListSnippet(description='\n            The postures supported by this part. If empty, assumes all postures\n            are supported.\n            '), 'supported_affordance_data': TunableTuple(description='\n            Define affordance compatibility for this part.\n            ', compatibility=TunableAffordanceFilterSnippet(description='\n                Affordances supported by the part\n                '), consider_mixers=Tunable(description='\n                If checked, mixers are filtered through this compatibility\n                check. If unchecked, all mixers are assumed to be valid to run\n                on this part.\n                ', tunable_type=bool, default=False)), 'blacklisted_buffs': TunableList(description='\n            A list of buffs that will disable this part as a candidate to run an\n            interaction.\n            ', tunable=TunableReference(description='\n               Reference to a buff to disable the part.\n               ', manager=services.get_instance_manager(sims4.resources.Types.BUFF), pack_safe=True)), 'trait_requirements': TunableWhiteBlackList(description='\n            Trait blacklist and whitelist requirements to pick this part.\n            ', tunable=Trait.TunableReference(description='\n               Reference to the trait white/blacklists.\n               ', pack_safe=True)), 'subroot': TunableReference(description='\n            The reference of the subroot definition in the part.\n            ', manager=services.subroot_manager(), allow_none=True), 'portal_data': TunableSet(description='\n            If the object owning this part has a portal component tuned, the\n            specified portals will be created for each part of this type. The\n            root position of the part is the subroot position.\n            ', tunable=TunablePortalReference(pack_safe=True)), 'can_pick': Tunable(description='\n            If checked, this part can be picked (selected as target when\n            clicking on object.)  If unchecked, cannot be picked.\n            ', tunable_type=bool, default=True), 'part_surface': TunableVariant(description='\n            The rules to determine the surface type for this object.\n            ', part_owner=_PartOwnerSurfaceType.TunableFactory(), override_surface=_OverrideSurfaceType.TunableFactory(), default='part_owner')}
    _bone_name_hashes_for_part_suffices = None

    @classmethod
    def register_tuned_animation(cls, *_, **__):
        pass

    @classmethod
    def add_auto_constraint(cls, participant_type, tuned_constraint, **kwargs):
        pass

    @classmethod
    def get_bone_name_hashes_for_part_suffix(cls, part_suffix):
        if cls._bone_name_hashes_for_part_suffices is None:
            cls._bone_name_hashes_for_part_suffices = {}
        if part_suffix in cls._bone_name_hashes_for_part_suffices:
            return cls._bone_name_hashes_for_part_suffices[part_suffix]
        bone_name_hashes = set()
        if cls.subroot is not None:
            for bone_name_hash in cls.subroot.bone_names:
                if part_suffix is not None:
                    bone_name_hash = hash32(str(part_suffix), initial_hash=bone_name_hash)
                bone_name_hashes.add(bone_name_hash)
        cls._bone_name_hashes_for_part_suffices[part_suffix] = frozenset(bone_name_hashes)
        return cls._bone_name_hashes_for_part_suffices[part_suffix]

class Subroot(metaclass=TunedInstanceMetaclass, manager=services.subroot_manager()):
    INSTANCE_TUNABLES = {'bone_names': TunableSet(description='\n            The list of bone names that make up this subroot. Use this to\n            specify containment slots for the given part.\n            \n            If the part specifies a subroot, the bone name will be automatically\n            postfixed with the subroot index.\n            \n            For example, for part subroot 1:\n                _ctnm_eat_ -> _ctnm_eat_1\n            ', tunable=TunableStringHash32(default='_ctnm_XXX_'), minlength=1)}
