from collections import namedtuplefrom timeit import itertoolsimport functoolsfrom animation.posture_manifest import AnimationParticipant, resolve_variables_and_objects, logger, SlotManifest, MATCH_ANY, _NOT_SPECIFIC_ACTORfrom objects.components.types import CARRYABLE_COMPONENTfrom objects.definition import Definitionfrom postures.posture_specs import PostureSpecVariable, PostureSpec, PostureAspectBody, PostureAspectCarry, PostureAspectSurface, PostureOperation, variables_matchfrom sims4.collections import frozendictimport servicesANIMATION_PARTICIPANT_TO_POSTURE_SPEC_VARIABLE_MAP = {AnimationParticipant.TARGET: PostureSpecVariable.INTERACTION_TARGET, AnimationParticipant.CONTAINER: PostureSpecVariable.INTERACTION_TARGET}POSTURE_SPEC_MANIFEST_INDEX = 0POSTURE_SPEC_SLOT_MANIFEST_INDEX = 1POSTURE_SPEC_BODY_TARGET_INDEX = 2_PostureStateSpec = namedtuple('_PostureStateSpec', ('posture_manifest', 'slot_manifest', 'body_target'))
class PostureStateSpec(_PostureStateSpec):
    __slots__ = ()

    def __new__(cls, posture_manifest, slot_manifest, body_target):
        posture_manifest = posture_manifest.get_constraint_version().frozen_copy()
        return _PostureStateSpec.__new__(cls, posture_manifest, slot_manifest.frozen_copy(), body_target)

    def __str__(self):
        items = ', '.join(str(i) for i in self)
        return '[' + items + ']'

    def get_concrete_version(self, target_resolver, posture_state=None):
        posture_manifest = self.posture_manifest.apply_actor_map(target_resolver)
        slot_manifest = self.slot_manifest.apply_actor_map(target_resolver)
        if posture_state is not None and (self.body_target is PostureSpecVariable.ANYTHING or self.body_target is PostureSpecVariable.BODY_TARGET_FILTERED) and posture_state.body.target is not None:
            body_target = posture_state.body.target
        else:
            body_target = target_resolver(self.body_target, self.body_target)
        if posture_manifest:
            posture_types = []
            for posture_manifest_entry in posture_manifest:
                if posture_manifest_entry.posture_type_specific:
                    is_specific = True
                    posture_type = posture_manifest_entry.posture_type_specific
                    posture_types.append((posture_type, is_specific))
                elif posture_manifest_entry.posture_type_family:
                    is_specific = False
                    posture_type = posture_manifest_entry.posture_type_family
                    posture_types.append((posture_type, is_specific))
                surface_target = posture_manifest_entry.surface_target
                allow_surface = posture_manifest_entry.allow_surface
            if slot_manifest:
                for slot_manifest_entry in slot_manifest:
                    if isinstance(slot_manifest_entry.actor, str):
                        pass
                    else:
                        slotted_object = slot_manifest_entry.actor
                        break
                slotted_object = None
                if slotted_object.carryable_component is None:
                    surface_target = None
                    slotted_object_or_parent = slotted_object
                    while slotted_object_or_parent is not None:
                        if slotted_object_or_parent.is_surface(include_parts=True, ignore_deco_slots=True):
                            surface_target = slotted_object_or_parent
                            break
                        slotted_object_or_parent = slotted_object_or_parent.parent
                    if surface_target is not None:

                        def get_surface(participant, default):
                            if participant in (AnimationParticipant.SURFACE, PostureSpecVariable.SURFACE_TARGET):
                                return surface_target
                            return default

                        posture_manifest = posture_manifest.apply_actor_map(get_surface)
                        slot_manifest = slot_manifest.apply_actor_map(get_surface)
            if not isinstance(surface_target, (AnimationParticipant, PostureSpecVariable, str)):
                slot_manifest = slot_manifest.apply_actor_map({PostureSpecVariable.ANYTHING: surface_target}.get)
            if allow_surface and slot_manifest and surface_target is not None and body_target == PostureSpecVariable.ANYTHING and posture_types:
                if not isinstance(surface_target, (AnimationParticipant, PostureSpecVariable, str)):
                    if all(posture_type.mobile for (posture_type, _) in posture_types):
                        body_target = surface_target
                    else:
                        for child in surface_target.children:
                            if child.parent is not surface_target:
                                pass
                            elif all(child.supports_posture_type(posture_type, is_specific=is_specific) for (posture_type, is_specific) in posture_types):
                                body_target = child
                                break
                        if all(surface_target.supports_posture_type(posture_type, is_specific=is_specific) for (posture_type, is_specific) in posture_types):
                            body_target = surface_target
            elif surface_target is None or isinstance(surface_target, (AnimationParticipant, PostureSpecVariable, str)):
                surface_target = None
                body_target_or_parent = body_target
                while body_target_or_parent is not None:
                    if body_target_or_parent.is_surface(include_parts=True, ignore_deco_slots=True):
                        surface_target = body_target_or_parent
                        break
                    body_target_or_parent = body_target_or_parent.parent
                if surface_target is not None:

                    def get_surface(participant, default):
                        if participant in (AnimationParticipant.SURFACE, PostureSpecVariable.SURFACE_TARGET):
                            return surface_target
                        return default

                    posture_manifest = posture_manifest.apply_actor_map(get_surface)
                    slot_manifest = slot_manifest.apply_actor_map(get_surface)
        return PostureStateSpec(posture_manifest, slot_manifest, body_target)

    def get_holster_version(self):
        return PostureStateSpec(self.posture_manifest.get_holster_version(), self.slot_manifest, self.body_target)

    def get_posture_specs_gen(self, interaction=None):
        for posture_manifest_entry in self.posture_manifest:
            var_map = {}
            (hand, carry_target) = posture_manifest_entry.carry_hand_and_target
            if hand is not None:
                allowed_hands = None
                if posture_manifest_entry.actor in _NOT_SPECIFIC_ACTOR:
                    carry_actor = interaction.sim if interaction is not None else None
                else:
                    carry_actor = posture_manifest_entry.actor
                if isinstance(carry_target, (str, Definition)) or carry_target == AnimationParticipant.CREATE_TARGET:
                    carry = PostureAspectCarry((PostureSpecVariable.POSTURE_TYPE_CARRY_NOTHING, None, PostureSpecVariable.HAND))
                    allowed_hands = carry_target.get_allowed_hands(carry_actor)
                else:
                    carry = PostureAspectCarry((PostureSpecVariable.POSTURE_TYPE_CARRY_OBJECT, PostureSpecVariable.CARRY_TARGET, PostureSpecVariable.HAND))
                    allowed_hands = carry_target.get_allowed_hands(carry_actor)
                    var_map[PostureSpecVariable.CARRY_TARGET] = carry_target
                if not allowed_hands is not None or hand not in allowed_hands:
                    pass
                else:
                    var_map[PostureSpecVariable.HAND] = hand
                    surface_target = posture_manifest_entry.surface_target
                    if surface_target is not None:
                        surface_target = ANIMATION_PARTICIPANT_TO_POSTURE_SPEC_VARIABLE_MAP.get(surface_target, PostureSpecVariable.SURFACE_TARGET)
                    elif posture_manifest_entry.allow_surface:
                        surface_target = PostureSpecVariable.ANYTHING
                    else:
                        surface_target = None
                    carryable_surfaces = []
                    other_surfaces = []
                    for slot_manifest_entry in self.slot_manifest:
                        slot_var_map = {}
                        slot_var_map[PostureSpecVariable.SLOT] = slot_manifest_entry
                        slot_type = PostureSpecVariable.SLOT
                        slot_child = slot_manifest_entry.actor
                        slot_parent = slot_manifest_entry.target
                        slot_child_is_carryable = False
                        slot_target = None
                        if isinstance(slot_child, str):
                            slot_target = None
                        elif isinstance(slot_child, Definition) or slot_child == AnimationParticipant.CREATE_TARGET:
                            slot_target = None
                            slot_var_map[PostureSpecVariable.SLOT_TEST_DEFINITION] = slot_child
                        elif hasattr(slot_child, 'manager'):
                            included_sis = []
                            if interaction.transition is not None:
                                included_sis = interaction.transition.get_included_sis().union((interaction,))
                            else:
                                included_sis = (interaction,)
                            slot_child_is_carryable = True if interaction is not None and slot_child.has_component(CARRYABLE_COMPONENT) else False
                            if slot_child_is_carryable and any(included_si.carry_target is slot_child for included_si in included_sis):
                                slot_var_map[PostureSpecVariable.CARRY_TARGET] = slot_child
                                slot_target = ANIMATION_PARTICIPANT_TO_POSTURE_SPEC_VARIABLE_MAP.get(slot_child, PostureSpecVariable.CARRY_TARGET)
                            elif any(included_si.target is slot_child for included_si in included_sis):
                                slot_var_map[PostureSpecVariable.SLOT_TARGET] = slot_child
                                slot_target = ANIMATION_PARTICIPANT_TO_POSTURE_SPEC_VARIABLE_MAP.get(slot_child, PostureSpecVariable.SLOT_TARGET)
                            else:
                                logger.error("Interaction {} has a slot_manifest_entry {} with a slot_child {} that doesn't appear to be a carry target or an interaction target. Please grab Tom Astle and show this to him.", interaction, slot_manifest_entry, slot_child, owner='tastle')
                        if not variables_match(surface_target, slot_parent):
                            logger.error("One of the slotting requirements for this posture_state_spec has a target different from the posture manifest's surface target.  This probably won't work: {} vs {} in {}", surface_target, slot_parent, posture_manifest_entry, owner='jpollak')
                        surface = PostureAspectSurface((slot_parent, slot_type, slot_target))
                        if slot_child_is_carryable:
                            carryable_surfaces.append((surface, slot_var_map))
                        else:
                            other_surfaces.append((surface, slot_var_map))
                    surface = None
                    first_list_with_surfaces = carryable_surfaces or other_surfaces
                    if first_list_with_surfaces:
                        (surface, slot_var_map) = first_list_with_surfaces.pop()
                        if carryable_surfaces:
                            logger.error('Multiple slot requirements for carryable targets, arbitrarily choosing one to manipulate in transition: {}', posture_manifest_entry, owner='jpollak')
                            other_surfaces.extend(carryable_surfaces)
                        var_map.update(slot_var_map)
                        var_map[PostureSpecVariable.DESTINATION_FILTER] = functools.partial(self._destination_filter, other_surfaces)
                    elif surface_target == PostureSpecVariable.ANYTHING:
                        surface = None
                    elif surface_target == None:
                        surface = PostureAspectSurface((None, None, None))
                    else:
                        surface = PostureAspectSurface((surface_target, None, None))
                    if not posture_manifest_entry.posture_types:
                        spec = PostureSpec((None, carry, surface))
                        yield (spec, frozendict(var_map))
                    else:
                        if posture_manifest_entry.specific:
                            posture_types = posture_manifest_entry.posture_types
                        elif posture_manifest_entry.family:
                            posture_types = [posture_type for posture_type in services.posture_manager().types.values() if posture_type.family_name == posture_manifest_entry.family]
                        else:
                            logger.error('Posture manifest entry has neither specific nor family.', owner='bhill')
                        for posture_type in posture_types:
                            target_object_filters = [x.target_object_filter for x in self.posture_manifest if x.target_object_filter is not MATCH_ANY]
                            if target_object_filters:
                                body = PostureAspectBody((posture_type, PostureSpecVariable.BODY_TARGET_FILTERED))
                                var_map[PostureSpecVariable.BODY_TARGET_FILTERED] = tuple(target_object_filters)
                            else:
                                body = PostureAspectBody((posture_type, self.body_target))
                            spec = PostureSpec((body, carry, surface))
                            yield (spec, frozendict(var_map))
            else:
                carry = None
            surface_target = posture_manifest_entry.surface_target
            if surface_target is not None:
                surface_target = ANIMATION_PARTICIPANT_TO_POSTURE_SPEC_VARIABLE_MAP.get(surface_target, PostureSpecVariable.SURFACE_TARGET)
            elif posture_manifest_entry.allow_surface:
                surface_target = PostureSpecVariable.ANYTHING
            else:
                surface_target = None
            carryable_surfaces = []
            other_surfaces = []
            for slot_manifest_entry in self.slot_manifest:
                slot_var_map = {}
                slot_var_map[PostureSpecVariable.SLOT] = slot_manifest_entry
                slot_type = PostureSpecVariable.SLOT
                slot_child = slot_manifest_entry.actor
                slot_parent = slot_manifest_entry.target
                slot_child_is_carryable = False
                slot_target = None
                if isinstance(slot_child, str):
                    slot_target = None
                elif isinstance(slot_child, Definition) or slot_child == AnimationParticipant.CREATE_TARGET:
                    slot_target = None
                    slot_var_map[PostureSpecVariable.SLOT_TEST_DEFINITION] = slot_child
                elif hasattr(slot_child, 'manager'):
                    included_sis = []
                    if interaction.transition is not None:
                        included_sis = interaction.transition.get_included_sis().union((interaction,))
                    else:
                        included_sis = (interaction,)
                    slot_child_is_carryable = True if interaction is not None and slot_child.has_component(CARRYABLE_COMPONENT) else False
                    if slot_child_is_carryable and any(included_si.carry_target is slot_child for included_si in included_sis):
                        slot_var_map[PostureSpecVariable.CARRY_TARGET] = slot_child
                        slot_target = ANIMATION_PARTICIPANT_TO_POSTURE_SPEC_VARIABLE_MAP.get(slot_child, PostureSpecVariable.CARRY_TARGET)
                    elif any(included_si.target is slot_child for included_si in included_sis):
                        slot_var_map[PostureSpecVariable.SLOT_TARGET] = slot_child
                        slot_target = ANIMATION_PARTICIPANT_TO_POSTURE_SPEC_VARIABLE_MAP.get(slot_child, PostureSpecVariable.SLOT_TARGET)
                    else:
                        logger.error("Interaction {} has a slot_manifest_entry {} with a slot_child {} that doesn't appear to be a carry target or an interaction target. Please grab Tom Astle and show this to him.", interaction, slot_manifest_entry, slot_child, owner='tastle')
                if not variables_match(surface_target, slot_parent):
                    logger.error("One of the slotting requirements for this posture_state_spec has a target different from the posture manifest's surface target.  This probably won't work: {} vs {} in {}", surface_target, slot_parent, posture_manifest_entry, owner='jpollak')
                surface = PostureAspectSurface((slot_parent, slot_type, slot_target))
                if slot_child_is_carryable:
                    carryable_surfaces.append((surface, slot_var_map))
                else:
                    other_surfaces.append((surface, slot_var_map))
            surface = None
            first_list_with_surfaces = carryable_surfaces or other_surfaces
            if first_list_with_surfaces:
                (surface, slot_var_map) = first_list_with_surfaces.pop()
                if carryable_surfaces:
                    logger.error('Multiple slot requirements for carryable targets, arbitrarily choosing one to manipulate in transition: {}', posture_manifest_entry, owner='jpollak')
                    other_surfaces.extend(carryable_surfaces)
                var_map.update(slot_var_map)
                var_map[PostureSpecVariable.DESTINATION_FILTER] = functools.partial(self._destination_filter, other_surfaces)
            elif surface_target == PostureSpecVariable.ANYTHING:
                surface = None
            elif surface_target == None:
                surface = PostureAspectSurface((None, None, None))
            else:
                surface = PostureAspectSurface((surface_target, None, None))
            if not posture_manifest_entry.posture_types:
                spec = PostureSpec((None, carry, surface))
                yield (spec, frozendict(var_map))
            else:
                if posture_manifest_entry.specific:
                    posture_types = posture_manifest_entry.posture_types
                elif posture_manifest_entry.family:
                    posture_types = [posture_type for posture_type in services.posture_manager().types.values() if posture_type.family_name == posture_manifest_entry.family]
                else:
                    logger.error('Posture manifest entry has neither specific nor family.', owner='bhill')
                for posture_type in posture_types:
                    target_object_filters = [x.target_object_filter for x in self.posture_manifest if x.target_object_filter is not MATCH_ANY]
                    if target_object_filters:
                        body = PostureAspectBody((posture_type, PostureSpecVariable.BODY_TARGET_FILTERED))
                        var_map[PostureSpecVariable.BODY_TARGET_FILTERED] = tuple(target_object_filters)
                    else:
                        body = PostureAspectBody((posture_type, self.body_target))
                    spec = PostureSpec((body, carry, surface))
                    yield (spec, frozendict(var_map))

    @staticmethod
    def _destination_filter(surfaces_and_var_maps, dest_spec, var_map):
        for (surface, slot_var_map) in surfaces_and_var_maps:
            combo_var_map = frozendict(var_map, slot_var_map)
            if PostureSpecVariable.SURFACE_TARGET in combo_var_map:
                surface = combo_var_map[PostureSpecVariable.SURFACE_TARGET]
            else:
                slot_child = combo_var_map[PostureSpecVariable.CARRY_TARGET]
                surface = slot_child.parent
            op = PostureOperation.TargetAlreadyInSlot(PostureSpecVariable.CARRY_TARGET, surface, PostureSpecVariable.SLOT)
            if not op.validate(None, None, combo_var_map):
                return False
        return True

    @property
    def supported_postures(self):
        return self.posture_manifest

    @staticmethod
    def _intersect_attr(this_constraint, other_constraint, attr_name, resolve_fn):
        value0 = getattr(this_constraint, attr_name)
        value1 = getattr(other_constraint, attr_name)
        if value0 is not None:
            if value1 is not None and value0 != value1:
                return resolve_fn(value0, value1)
            return (None, value0)
        else:
            return (None, value1)

    @staticmethod
    def _intersect_attr_len(this_constraint, other_constraint, attr_name, resolve_fn):
        value0 = getattr(this_constraint, attr_name)
        value1 = getattr(other_constraint, attr_name)
        if value0:
            if value1 and value0 != value1:
                return resolve_fn(value0, value1)
            return (None, value0)
        else:
            return (None, value1)

    def intersection(self, other):
        (early_out, posture_manifest) = self._intersect_attr_len(self, other, 'posture_manifest', self._resolve_unequal_manifest)
        if early_out is not None:
            return early_out
        (early_out, slot_manifest) = self._intersect_attr_len(self, other, 'slot_manifest', self._resolve_unequal_manifest)
        if early_out is not None:
            return early_out
        (early_out, body_target) = self._intersect_attr(self, other, 'body_target', resolve_variables_and_objects)
        if early_out is not None:
            return early_out
        return PostureStateSpec(posture_manifest, slot_manifest, body_target)

    def _resolve_unequal_manifest(self, value0, value1):
        result = value0.intersection(value1)
        if result is not None:
            return (None, result)
        return (False, None)

    def references_object(self, obj):
        (posture_manifest, slot_manifest, body_target) = self
        for posture_manifest_entry in posture_manifest:
            if posture_manifest_entry.references_object(obj):
                return True
        for slot_manifest_entry in slot_manifest:
            if slot_manifest_entry.references_object(obj):
                return True
        if body_target is obj:
            return True
        return False

    def is_filtered_target(self):
        (posture_manifest, *_) = self
        for posture_manifest_entry in posture_manifest:
            if posture_manifest_entry.target_object_filter is not MATCH_ANY:
                return True
        return False

    def is_vehicle_only_spec(self):
        if not self.posture_manifest:
            return False
        for posture_manifest_entry in self.posture_manifest:
            for posture in posture_manifest_entry.posture_types:
                if not posture.is_vehicle:
                    return False
        return True

def create_body_posture_state_spec(posture_manifest, body_target=PostureSpecVariable.ANYTHING):
    return PostureStateSpec(posture_manifest, SlotManifest().intern(), body_target)
