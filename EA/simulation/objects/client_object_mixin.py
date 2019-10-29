from _collections import defaultdictfrom _weakrefset import WeakSetfrom collections import Counterfrom contextlib import contextmanagerfrom math import floorfrom protocolbuffers import UI_pb2 as ui_protocolsfrom animation.arb_element import ArbElementfrom animation.awareness.awareness_ops import SetAwarenessSourceOpfrom build_buy import get_object_decosize, get_object_slotsetfrom distributor.system import Distributorfrom event_testing import test_eventsfrom objects import VisibilityState, MaterialStatefrom objects.components import forward_to_components, forward_to_components_genfrom objects.components.censor_grid_component import CensorStatefrom objects.components.types import CARRYABLE_COMPONENTfrom objects.definition import Definitionfrom objects.game_object_properties import GameObjectPropertyfrom objects.hovertip import TooltipFieldsCompletefrom objects.object_enums import ResetReasonfrom objects.slots import RuntimeSlot, DecorativeSlotTuning, get_slot_type_set_from_keyfrom services.reset_and_delete_service import ResetRecordfrom sims4.callback_utils import CallableListfrom sims4.tuning.tunable import TunablePercent, TunableSimMinutefrom singletons import EMPTY_SET, DEFAULT, UNSETimport animation.arbimport assertionsimport cachesimport distributor.opsimport distributor.sparseimport enumimport native.animationimport objects.definitionimport routingimport servicesimport sims4.logimport uidlogger = sims4.log.Logger('Objects', default_owner='PI')with sims4.reload.protected(globals()):
    lockout_visualization = False
class ObjectParentType(enum.Int, export=False):
    PARENT_NONE = 0
    PARENT_OBJECT = 1
    PARENT_COLUMN = 2
    PARENT_WALL = 3
    PARENT_FENCE = 4
    PARENT_POST = 5

class ChildrenType(enum.Int, export=False):
    DEFAULT = ...
    BB_ONLY = ...

class ClientObjectMixin:
    INITIAL_DEPRECIATION = TunablePercent(20, description='Amount (0%%-100%%) of depreciation to apply to an object after purchase. An item worth 10 in the catalog if tuned at 20%% will be worth 8 after purchase.')
    FADE_DURATION = TunableSimMinute(1.2, description='Default fade time (in sim minutes) for objects.')
    VISIBLE_TO_AUTOMATION = True
    _get_next_ui_metadata_handle = uid.UniqueIdGenerator(min_uid=1)
    HOVERTIP_HANDLE = 0
    ui_metadata = distributor.sparse.SparseField(ui_protocols.UiObjectMetadata, distributor.ops.SetUiObjectMetadata)
    _generic_ui_metadata_setters = {}
    FORWARD_OFFSET = 0.04

    def __init__(self, definition, **kwargs):
        super().__init__(definition, **kwargs)
        if definition is not None:
            self.apply_definition(definition, **kwargs)
        self._ui_metadata_stack = None
        self._ui_metadata_handles = None
        self._ui_metadata_cache = None
        self.primitives = distributor.ops.DistributionSet(self)
        zone_id = services.current_zone_id()
        self._location = sims4.math.Location(sims4.math.Transform(), routing.SurfaceIdentifier(zone_id, 0, routing.SurfaceType.SURFACETYPE_WORLD))
        self._children_objects = None
        self._scale = 1
        self._parent_type = ObjectParentType.PARENT_NONE
        self._parent_location = 0
        self._build_buy_lockout = False
        self._build_buy_lockout_alarm_handler = None
        self._tint = None
        self._opacity = None
        self._censor_state = None
        self._geometry_state = None
        self._geometry_state_overrides = None
        self._standin_model = None
        self._visibility = None
        self._visibility_flags = None
        self._material_state = None
        self._reference_arb = None
        self._audio_effects = None
        self._video_playlist = None
        self._painting_state = None
        self.custom_name = None
        self.custom_description = None
        self._multicolor = None
        self._display_number = None
        self._awareness_scores = None
        self._scratched = False
        self._base_value = definition.price
        self._needs_post_bb_fixup = False
        self._needs_depreciation = False
        self._swapping_to_parent = None
        self._swapping_from_parent = None
        self._on_children_changed = None

    def get_create_op(self, *args, **kwargs):
        additional_ops = list(self.get_additional_create_ops_gen())
        return distributor.ops.ObjectCreate(self, *args, additional_ops=additional_ops, **kwargs)

    @forward_to_components_gen
    def get_additional_create_ops_gen(self):
        pass

    def get_create_after_objs(self):
        parent = self.parent_object(child_type=ChildrenType.BB_ONLY)
        if parent is not None:
            return (parent,)
        return ()

    def get_delete_op(self, fade_duration=0):
        return distributor.ops.ObjectDelete(fade_duration=fade_duration)

    @forward_to_components
    def apply_definition(self, definition, obj_state=0):
        if not isinstance(definition, objects.definition.Definition):
            definition = services.definition_manager().get(definition)
        self._model = definition.get_model(obj_state)
        self._material_variant = definition.material_variant
        self._rig = definition.get_rig(obj_state)
        self._slot = definition.get_slot(obj_state)
        self._slots_resource = definition.get_slots_resource(obj_state)
        self._state_index = obj_state

    def set_definition(self, definition_id, ignore_rig_footprint=False):
        new_definition = services.definition_manager().get(definition_id)
        (result, error) = self.definition.is_similar(new_definition, ignore_rig_footprint=ignore_rig_footprint)
        if not result:
            logger.error('Trying to set the definition {} to an incompatible definition {}.\n {}', self.definition.id, definition_id, error, owner='nbaker')
            return False
        services.definition_manager().unregister_definition(self.definition.id, self)
        self.apply_definition(new_definition, self._state_index)
        self.definition = new_definition
        services.definition_manager().register_definition(new_definition.id, self)
        self.resend_model_with_material_variant()
        self.resend_slot()
        self.resend_state_index()
        op = distributor.ops.SetObjectDefinitionId(definition_id)
        distributor.system.Distributor.instance().add_op(self, op)
        return True

    @property
    def hover_tip(self):
        if self._ui_metadata_stack is None or ClientObjectMixin.HOVERTIP_HANDLE not in self._ui_metadata_handles:
            return
        (_, _, value) = self._ui_metadata_handles[ClientObjectMixin.HOVERTIP_HANDLE]
        return value

    @hover_tip.setter
    def hover_tip(self, value):
        if value is not None:
            if self._ui_metadata_stack is None:
                self._ui_metadata_stack = []
                self._ui_metadata_handles = {}
                self._ui_metadata_cache = {}
            data = self._ui_metadata_handles.get(ClientObjectMixin.HOVERTIP_HANDLE)
            if data is not None:
                self._ui_metadata_stack.remove(data)
            data = (ClientObjectMixin.HOVERTIP_HANDLE, 'hover_tip', value)
            self._ui_metadata_stack.append(data)
            self._ui_metadata_handles[ClientObjectMixin.HOVERTIP_HANDLE] = data

    def add_ui_metadata(self, name, value):
        if self._ui_metadata_stack is None:
            self._ui_metadata_stack = []
            self._ui_metadata_handles = {}
            self._ui_metadata_cache = {}
        if name not in self._ui_metadata_cache:
            default_value = type(self).ui_metadata.generic_getter(name)(self)
            self._ui_metadata_cache[name] = default_value
        handle = self._get_next_ui_metadata_handle()
        data = (handle, name, value)
        self._ui_metadata_stack.append(data)
        self._ui_metadata_handles[handle] = data
        return handle

    def get_ui_metadata(self, handle):
        return self._ui_metadata_handles[handle]

    def remove_ui_metadata(self, handle):
        if self._ui_metadata_stack is not None:
            self._ui_metadata_stack.remove(self._ui_metadata_handles[handle])

    def update_ui_metadata(self, use_cache=True):
        if self._ui_metadata_stack is None:
            return
        ui_metadata = {}
        for (_, name, value) in self._ui_metadata_stack:
            ui_metadata[name] = value
        for (name, value) in ui_metadata.items():
            if name in self._ui_metadata_cache and self._ui_metadata_cache[name] == value and use_cache:
                pass
            else:
                if name in self._generic_ui_metadata_setters:
                    setter = self._generic_ui_metadata_setters[name]
                else:
                    setter = type(self).ui_metadata.generic_setter(name)
                    self._generic_ui_metadata_setters[name] = setter
                try:
                    setter(self, value)
                except (ValueError, TypeError):
                    logger.error('Error trying to set field {} to value {} in object {}.', name, value, self, owner='camilogarcia')
        self._ui_metadata_cache = ui_metadata

    @property
    def swapping_to_parent(self):
        return self._swapping_to_parent

    @property
    def swapping_from_parent(self):
        return self._swapping_from_parent

    @contextmanager
    def _swapping_parents(self, old_parent, new_parent):
        self._swapping_from_parent = old_parent
        self._swapping_to_parent = new_parent
        try:
            yield None
        finally:
            self._swapping_from_parent = None
            self._swapping_to_parent = None

    @property
    def location(self):
        return self._location

    @distributor.fields.Field(op=distributor.ops.SetLocation)
    def _location_field_internal(self):
        return self

    resend_location = _location_field_internal.get_resend()

    @location.setter
    def location(self, new_location):
        self.set_location_without_distribution(new_location)
        self.resend_location()

    def set_location_without_distribution(self, new_location):
        if not isinstance(new_location, sims4.math.Location):
            raise TypeError()
        if not (new_location == self._location and (self.parts is not None and new_location.parent is not None) and new_location.parent.parts is not None):
            return
        old_location = self._location
        events = [(self, old_location)]
        for child in self.get_all_children_recursive_gen():
            events.append((child, child._location))
        if new_location.parent != old_location.parent:
            self.pre_parent_change(new_location.parent)
            with self._swapping_parents(old_location.parent, new_location.parent):
                if old_location.parent is not None:
                    old_location.parent._remove_child(self, new_parent=new_location.parent)
                if new_location.parent is not None:
                    new_location.parent._add_child(self, new_location)
            visibility_state = self.visibility or VisibilityState()
            if new_location.parent is not None and new_location.parent._disable_child_footprint_and_shadow:
                visibility_state.enable_drop_shadow = False
            else:
                visibility_state.enable_drop_shadow = True
            self.visibility = visibility_state
        if new_location.parent is not None:
            current_inventory = self.get_inventory()
            if current_inventory is not None and not current_inventory.try_remove_object_by_id(self.id):
                raise RuntimeError('Unable to remove object: {} from the inventory: {}, parenting request will be ignored.'.format(self, current_inventory))
        posture_graph_service = services.current_zone().posture_graph_service
        with posture_graph_service.object_moving(self):
            self._location = new_location
            if self.parts:
                for part in self.parts:
                    part.on_owner_location_changed()
        if new_location.parent != old_location.parent:
            self.on_parent_change(new_location.parent)
        for (obj, old_value) in events:
            if obj is not self:
                new_location = obj.location.clone()
                obj._location = new_location
            obj.on_location_changed(old_value)

    def set_location(self, location):
        self.location = location

    def move_to(self, **overrides):
        self.location = self._location.clone(**overrides)

    @distributor.fields.Field(op=distributor.ops.SetAudioEffects)
    def audio_effects(self):
        return self._audio_effects

    resend_audio_effects = audio_effects.get_resend()

    def append_audio_effect(self, key, audio_effect_data):
        if self._audio_effects is None:
            self._audio_effects = {}
        self._audio_effects[key] = audio_effect_data
        self.resend_audio_effects()

    def remove_audio_effect(self, key):
        if self._audio_effects is None:
            logger.error('Found audio effects is None while trying to remove audio effect with key {} on {}', key, self, owner='jdimailig')
            return
        if key in self._audio_effects:
            del self._audio_effects[key]
        if not self._audio_effects:
            self._audio_effects = None
        self.resend_audio_effects()

    @forward_to_components
    def on_location_changed(self, old_location):
        pass

    @property
    def transform(self):
        return self._location.world_transform

    @transform.setter
    def transform(self, transform):
        if self.parent is not None:
            self.move_to(transform=transform, parent=None, routing_surface=self.parent.routing_surface)
            return
        self.move_to(transform=transform)

    @property
    def position(self):
        return self.transform.translation

    @property
    def position_with_forward_offset(self):
        return self.position + self.forward*ClientObjectMixin.FORWARD_OFFSET

    @property
    def intended_position_with_forward_offset(self):
        return self.intended_position + self.intended_forward*ClientObjectMixin.FORWARD_OFFSET

    @property
    def orientation(self):
        return self.transform.orientation

    @property
    def forward(self):
        return self.orientation.transform_vector(self.forward_direction_for_picking)

    @property
    def routing_surface(self):
        return self._location.world_routing_surface

    @property
    def level(self):
        routing_surface = self.routing_surface
        if routing_surface is None:
            return
        return routing_surface.secondary_id

    @property
    def routing_location(self):
        return self.get_routing_location_for_transform(self.transform)

    def get_routing_location_for_transform(self, transform, routing_surface=DEFAULT):
        routing_surface = self.routing_surface if routing_surface is DEFAULT else routing_surface
        return routing.Location(transform.translation, transform.orientation, routing_surface)

    @property
    def intended_transform(self):
        return self.transform

    @property
    def intended_position(self):
        return self.intended_transform.translation

    @property
    def intended_forward(self):
        return self.intended_transform.orientation.transform_vector(self.forward_direction_for_picking)

    @property
    def intended_routing_surface(self):
        return self.routing_surface

    @property
    def parent(self):
        parent = self._location.parent
        parent = self.attempt_to_remap_parent(parent)
        if parent is not None:
            children = parent.children
            if not (self not in children and self.is_part and self.part_owner in children):
                return
        return parent

    @property
    def bb_parent(self):
        return self._location.parent

    def attempt_to_remap_parent(self, parent):
        if self.is_part and parent is not None and parent.parts is not None:
            distance = None
            found_part = None
            for part in parent.parts:
                dot = sims4.math.vector_dot(self.forward, part.forward)
                if dot < -0.98:
                    new_distance = (part.position - self.position).magnitude_squared()
                    if not distance is None:
                        if new_distance <= distance:
                            if new_distance == distance and found_part.subroot_index is not None:
                                pass
                            else:
                                distance = new_distance
                                found_part = part
                    if new_distance == distance and found_part.subroot_index is not None:
                        pass
                    else:
                        distance = new_distance
                        found_part = part
            return found_part
        return parent

    def parent_object(self, child_type=ChildrenType.DEFAULT):
        if child_type is ChildrenType.BB_ONLY:
            parent = self.bb_parent
        else:
            parent = self.parent
        if parent.is_part:
            parent = parent.part_owner
        return parent

    @property
    def parent_slot(self):
        parent = self._location.parent
        if parent is None:
            return
        bone_name_hash = self._location.joint_name_or_hash or self._location.slot_hash
        result = None
        for runtime_slot in parent.get_runtime_slots_gen(bone_name_hash=bone_name_hash):
            if result is not None:
                raise AssertionError('Multiple slots!')
            result = runtime_slot
        if result is None:
            result = RuntimeSlot(parent, bone_name_hash, frozenset())
        return result

    def get_parenting_root(self):
        result = self
        next_parent = result.parent
        while next_parent is not None:
            result = next_parent
            next_parent = result.parent
        return result

    @property
    def children(self):
        if self._children_objects is not None:
            return self._children_objects[ChildrenType.DEFAULT]
        return ()

    def children_recursive_gen(self, include_self=False):
        if include_self:
            yield self
        for child in self.children:
            yield child
            for grandchild in child.children_recursive_gen():
                yield grandchild

    @assertions.hot_path
    def _children_recursive_fast_gen(self):
        yield self
        for child in self.children:
            yield from child._children_recursive_fast_gen()

    def get_all_children_gen(self):
        if self._children_objects is not None:
            for children in self._children_objects.values():
                yield from children

    def get_all_children_recursive_gen(self):
        for child in self.get_all_children_gen():
            yield child
            yield from child.get_all_children_recursive_gen()

    def clear_default_children(self):
        if self._children_objects is not None:
            self._children_objects[ChildrenType.DEFAULT].clear()

    @assertions.hot_path
    def parenting_hierarchy_gen(self):
        self_parent = self.parent
        if self_parent is not None:
            master_parent = self_parent
            master_parent_parent = master_parent.parent
            while master_parent_parent is not None:
                master_parent = master_parent_parent
                master_parent_parent = master_parent.parent
            yield from master_parent._children_recursive_fast_gen()
        else:
            yield from self._children_recursive_fast_gen()

    def on_reset_send_op(self, reset_reason):
        super().on_reset_send_op(reset_reason)
        if reset_reason != ResetReason.BEING_DESTROYED or self.vehicle_component is not None:
            try:
                reset_op = distributor.ops.ResetObject(self.id)
                dist = Distributor.instance()
                dist.add_op(self, reset_op)
            except:
                logger.exception('Exception thrown sending reset op for {}', self)

    def on_reset_internal_state(self, reset_reason):
        if self.valid_for_distribution and reset_reason != ResetReason.BEING_DESTROYED:
            self.geometry_state = None
            self.material_state = None
            self.resend_location()
        self._reset_reference_arb()
        super().on_reset_internal_state(reset_reason)

    def on_reset_get_interdependent_reset_records(self, reset_reason, reset_records):
        super().on_reset_get_interdependent_reset_records(reset_reason, reset_records)
        for child in set(self.get_all_children_gen()):
            reset_records.append(ResetRecord(child, ResetReason.RESET_EXPECTED, self, 'Child'))

    @property
    def slot_hash(self):
        return self._location.slot_hash

    @slot_hash.setter
    def slot_hash(self, value):
        if self._location.slot_hash != value:
            self.location = self._location.clone(slot_hash=value)

    @property
    def bone_name_hash(self):
        return self._location.joint_name_or_hash or self._location.slot_hash

    @property
    def part_suffix(self) -> str:
        pass

    @distributor.fields.Field(op=distributor.ops.SetModel)
    def model_with_material_variant(self):
        return (self._model, self._material_variant)

    resend_model_with_material_variant = model_with_material_variant.get_resend()

    @model_with_material_variant.setter
    def model_with_material_variant(self, value):
        (self._model, self._material_variant) = value

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, value):
        model_res_key = None
        if isinstance(value, sims4.resources.Key):
            model_res_key = value
        elif isinstance(value, Definition):
            model_res_key = value.get_model(index=0)
            self.set_definition(value.id, ignore_rig_footprint=True)
        else:
            if value is not None:
                logger.error('Trying to set the model of object {} to the invalid value of {}.                                The object will revert to its default model instead.', self, value, owner='tastle')
            model_res_key = self.definition.get_model(self._state_index)
        self.model_with_material_variant = (model_res_key, self._material_variant)

    @property
    def material_variant(self):
        return self._material_variant

    @material_variant.setter
    def material_variant(self, value):
        if value is None:
            self.model_with_material_variant = (self._model, None)
        else:
            if not isinstance(value, str):
                raise TypeError('Model variant value must be a string')
            if not value:
                self.model_with_material_variant = (self._model, None)
            else:
                try:
                    variant_value = int(value)
                except ValueError:
                    variant_value = sims4.hash_util.hash32(value)
                self.model_with_material_variant = (self._model, variant_value)

    @distributor.fields.Field(op=distributor.ops.SetStandInModel)
    def standin_model(self):
        return self._standin_model

    @standin_model.setter
    def standin_model(self, value):
        self._standin_model = value

    @distributor.fields.Field(op=distributor.ops.SetObjectDefStateIndex, default=0)
    def state_index(self):
        return self._state_index

    resend_state_index = state_index.get_resend()

    @distributor.fields.Field(op=distributor.ops.SetRig, priority=distributor.fields.Field.Priority.HIGH)
    def rig(self):
        return self._rig

    @rig.setter
    def rig(self, value):
        if not isinstance(value, sims4.resources.Key):
            raise TypeError
        self._rig = value

    @distributor.fields.Field(op=distributor.ops.SetSlot)
    def slot(self):
        return self._slot

    resend_slot = slot.get_resend()

    @property
    def slots_resource(self):
        return self._slots_resource

    @distributor.fields.Field(op=distributor.ops.SetScale, default=1)
    def _client_scale(self):
        scale_value = self.scale
        for modifier in self.scale_modifiers_gen():
            scale_value *= modifier
        return scale_value

    _resend_client_scale = _client_scale.get_resend()

    @property
    def scale(self):
        return self._scale

    @forward_to_components_gen
    def scale_modifiers_gen(self):
        pass

    @scale.setter
    def scale(self, value):
        self._scale = value
        self._resend_client_scale()

    @property
    def parent_type(self):
        return self._parent_type

    @parent_type.setter
    def parent_type(self, value):
        self._parent_type = value
        self._resend_parent_type_info()

    @distributor.fields.Field(op=distributor.ops.SetParentType, default=None)
    def parent_type_info(self):
        return (self._parent_type, self._parent_location)

    @parent_type_info.setter
    def parent_type_info(self, value):
        (self._parent_type, self._parent_location) = value

    _resend_parent_type_info = parent_type_info.get_resend()

    @property
    def build_buy_lockout(self):
        return self._build_buy_lockout

    @distributor.fields.Field(op=distributor.ops.SetTint, default=None)
    def tint(self):
        if self.build_buy_lockout and lockout_visualization:
            return sims4.color.ColorARGB32(23782)
        return self._tint

    @tint.setter
    def tint(self, tint_color):
        value = getattr(tint_color, 'value', tint_color)
        if value and not isinstance(value, sims4.color.ColorARGB32):
            raise TypeError('Tint value must be a Color')
        if value == sims4.color.Color.WHITE:
            self._tint = None
        else:
            self._tint = value

    resend_tint = tint.get_resend()

    @distributor.fields.Field(op=distributor.ops.SetMulticolor, default=None)
    def multicolor(self):
        return self._multicolor

    @multicolor.setter
    def multicolor(self, value):
        self._multicolor = value

    resend_multicolor = multicolor.get_resend()

    @distributor.fields.Field(op=distributor.ops.SetDisplayNumber, default=None)
    def display_number(self):
        return self._display_number

    @display_number.setter
    def display_number(self, value):
        self._display_number = value

    resend_display_number = display_number.get_resend()

    def update_display_number(self, display_number=None):
        if display_number is not None:
            self.display_number = display_number
            return
        if hasattr(self, 'get_display_number'):
            self.display_number = self.get_display_number()

    @distributor.fields.Field(op=distributor.ops.SetOpacity, default=None)
    def opacity(self):
        return self._opacity

    @opacity.setter
    def opacity(self, value):
        self._opacity = self._clamp_opacity(value)

    def _clamp_opacity(self, value):
        if value is None:
            return
        try:
            value = float(value)
        except:
            raise TypeError('Opacity value must be a float')
        return sims4.math.clamp(0.0, value, 1.0)

    @distributor.fields.Field(op=SetAwarenessSourceOp)
    def awareness_scores(self):
        return self._awareness_scores

    resend_awareness_scores = awareness_scores.get_resend()

    def add_awareness_scores(self, awareness_sources):
        if self._awareness_scores is None:
            self._awareness_scores = Counter()
        self._awareness_scores.update(awareness_sources)
        self.resend_awareness_scores()

    def remove_awareness_scores(self, awareness_sources):
        if self._awareness_scores is None:
            return
        self._awareness_scores.subtract(awareness_sources)
        for awareness_channel in tuple(self.awareness_scores):
            if not self._awareness_scores[awareness_channel]:
                del self._awareness_scores[awareness_channel]
        if not self._awareness_scores:
            self._awareness_scores = None
        self.resend_awareness_scores()

    def add_geometry_state_override(self, original_geometry_state, override_geometry_state):
        if self._geometry_state_overrides is None:
            self._geometry_state_overrides = {}
        original_state_hash = sims4.hash_util.hash32(original_geometry_state)
        override_state_hash = sims4.hash_util.hash32(override_geometry_state)
        logger.assert_raise(original_state_hash not in self._geometry_state_overrides, 'add_geometry_state_override does not support multiple overrides per state')
        self._geometry_state_overrides[original_state_hash] = override_state_hash
        self.geometry_state = self.geometry_state

    def remove_geometry_state_override(self, original_geometry_state):
        state_hash = sims4.hash_util.hash32(original_geometry_state)
        if state_hash in self._geometry_state_overrides:
            del self._geometry_state_overrides[state_hash]
        if not self._geometry_state_overrides:
            self._geometry_state_overrides = None

    @distributor.fields.Field(op=distributor.ops.SetGeometryState, default=None)
    def geometry_state(self):
        return self._geometry_state

    @geometry_state.setter
    def geometry_state(self, value):
        self._geometry_state = self._get_geometry_state_for_value(value)

    def _get_geometry_state_for_value(self, value):
        if not value:
            return
        if isinstance(value, str):
            state_hash = sims4.hash_util.hash32(value)
        elif isinstance(value, int):
            state_hash = value
        if state_hash in self._geometry_state_overrides:
            state_hash = self._geometry_state_overrides[state_hash]
        return state_hash

    @distributor.fields.Field(op=distributor.ops.SetCensorState, default=None)
    def censor_state(self):
        return self._censor_state

    @censor_state.setter
    def censor_state(self, value):
        try:
            value = CensorState(value)
        except:
            raise TypeError('Censor State value must be an int')
        self._censor_state = value

    @distributor.fields.Field(op=distributor.ops.SetVisibility, default=None)
    def visibility(self):
        return self._visibility

    @visibility.setter
    def visibility(self, value):
        if not isinstance(value, VisibilityState):
            raise TypeError('Visibility must be set to value of type VisibilityState')
        self._visibility = value
        if value.enable_drop_shadow is False:
            self._visibility = None

    @distributor.fields.Field(op=distributor.ops.SetVisibilityFlags)
    def visibility_flags(self):
        return self._visibility_flags

    @visibility_flags.setter
    def visibility_flags(self, value):
        self._visibility_flags = value

    @distributor.fields.Field(op=distributor.ops.SetMaterialState, default=None)
    def material_state(self):
        return self._material_state

    @material_state.setter
    def material_state(self, value):
        if value is None:
            self._material_state = None
        else:
            if not isinstance(value, MaterialState):
                raise TypeError('Material State must be set to value of type MaterialState')
            if value.state_name_hash == 0:
                self._material_state = None
            else:
                self._material_state = value

    @property
    def material_hash(self):
        if self.material_state is None:
            return 0
        else:
            return self.material_state.state_name_hash

    @distributor.fields.Field(op=distributor.ops.StartArb, default=None)
    def reference_arb(self):
        return self._reference_arb

    def update_reference_arb(self, arb):
        if self._reference_arb is None:
            self._reference_arb = animation.arb.Arb()
        native.animation.update_post_condition_arb(self._reference_arb, arb)

    def _reset_reference_arb(self):
        if self._reference_arb is not None:
            reset_arb_element = ArbElement(animation.arb.Arb())
            reset_arb_element.add_object_to_reset(self)
            reset_arb_element.distribute()
            reset_arb_element.cleanup()
        self._reference_arb = None

    _NO_SLOTS = EMPTY_SET

    @property
    def deco_slot_size(self):
        return get_object_decosize(self.definition.id)

    @property
    def deco_slot_types(self):
        return DecorativeSlotTuning.get_slot_types_for_object(self.deco_slot_size)

    @property
    def slot_type_set(self):
        key = get_object_slotset(self.definition.id)
        return get_slot_type_set_from_key(key)

    @property
    def slot_types(self):
        slot_type_set = self.slot_type_set
        if slot_type_set is not None:
            return slot_type_set.slot_types
        return self._NO_SLOTS

    @property
    def ideal_slot_types(self):
        carryable = self.get_component(CARRYABLE_COMPONENT)
        if carryable is not None:
            slot_type_set = carryable.ideal_slot_type_set
            if slot_type_set is not None:
                return slot_type_set.slot_types & (self.slot_types | self.deco_slot_types)
        return self._NO_SLOTS

    @property
    def all_valid_slot_types(self):
        return self.deco_slot_types | self.slot_types

    def _add_child(self, child, location):
        if self._children_objects is None:
            self._children_objects = defaultdict(WeakSet)
        if not isinstance(self.children, (WeakSet, set)):
            raise TypeError("self.children is not a WeakSet or a set, it's {}".format(self.children))
        bone_name_hash = location.joint_name_or_hash or location.slot_hash
        found_runtime_slot = None
        for runtime_slot in location.parent.get_runtime_slots_gen(bone_name_hash=bone_name_hash):
            if found_runtime_slot is not None:
                raise AssertionError('Multiple slots found for {}'.format(location.parent))
            found_runtime_slot = runtime_slot
        if found_runtime_slot is not None:
            for slot_type in found_runtime_slot.slot_types:
                if not slot_type.bb_only:
                    self._children_objects[ChildrenType.DEFAULT].add(child)
                    break
            self._children_objects[ChildrenType.BB_ONLY].add(child)
        else:
            self._children_objects[ChildrenType.DEFAULT].add(child)
        if self.parts:
            for part in self.parts:
                part.on_children_changed()
        self.on_child_added(child, location)

    def _remove_child(self, child, new_parent=None):
        if not isinstance(self.children, (WeakSet, set)):
            raise TypeError("self.children is not a WeakSet or a set, it's {}".format(self.children))
        for (_, weak_obj_set) in self._children_objects.items():
            if child in weak_obj_set:
                weak_obj_set.discard(child)
                break
        if self.parts:
            for part in self.parts:
                part.on_children_changed()
        self.on_child_removed(child, new_parent=new_parent)

    @forward_to_components
    def on_remove_from_client(self):
        super().on_remove_from_client()
        for primitive in tuple(self.primitives):
            primitive.detach(self)

    def post_remove(self):
        super().post_remove()
        for primitive in tuple(self.primitives):
            primitive.detach(self)
        self.primitives = None

    @forward_to_components
    def on_child_added(self, child, location):
        if self._on_children_changed is None:
            return
        self._on_children_changed(child, location=location)

    @forward_to_components
    def on_child_removed(self, child, new_parent=None):
        if self._on_children_changed is None:
            return
        self._on_children_changed(child, new_parent=new_parent)

    @forward_to_components
    def pre_parent_change(self, parent):
        pass

    @forward_to_components
    def on_parent_change(self, parent):
        caches.clear_all_caches()
        if parent is None:
            self.parent_type = ObjectParentType.PARENT_NONE
        else:
            self.parent_type = ObjectParentType.PARENT_OBJECT

    def create_parent_location(self, parent, transform=sims4.math.Transform.IDENTITY(), joint_name_or_hash=None, slot_hash=0, routing_surface=None):
        if parent is not None:
            if self in parent.ancestry_gen():
                raise ValueError('Invalid parent value (parent chain is circular)')
            if joint_name_or_hash:
                native.animation.get_joint_transform_from_rig(parent.rig, joint_name_or_hash)
            if slot_hash and not parent.has_slot(slot_hash):
                raise KeyError('Could not slot {}/{} in slot {} on {}/{}'.format(self, self.definition, hex(slot_hash), parent, parent.definition))
        part_joint_name = joint_name_or_hash or slot_hash
        if parent.parts:
            for part in parent.parts:
                if part.has_slot(part_joint_name):
                    parent = part
                    break
        new_location = self._location.clone(transform=transform, joint_name_or_hash=joint_name_or_hash, slot_hash=slot_hash, parent=parent, routing_surface=routing_surface)
        return new_location

    def set_parent(self, *args, **kwargs):
        new_location = self.create_parent_location(*args, **kwargs)
        self.location = new_location

    def clear_parent(self, transform, routing_surface):
        return self.set_parent(None, transform=transform, routing_surface=routing_surface)

    def remove_reference_from_parent(self):
        parent = self.bb_parent
        if parent is not None:
            parent._remove_child(self, new_parent=UNSET)

    @distributor.fields.Field(op=distributor.ops.VideoSetPlaylistOp, default=None)
    def video_playlist(self):
        return self._video_playlist

    @video_playlist.setter
    def video_playlist(self, playlist):
        self._video_playlist = playlist

    _resend_video_playlist = video_playlist.get_resend()

    def fade_opacity(self, opacity:float, duration:float):
        opacity = self._clamp_opacity(opacity)
        if opacity != self._opacity:
            self._opacity = opacity
            fade_op = distributor.ops.FadeOpacity(opacity, duration)
            distributor.ops.record(self, fade_op)

    def fade_in(self, fade_duration=None):
        if fade_duration is None:
            fade_duration = ClientObjectMixin.FADE_DURATION
        if not self.visibility.visibility:
            self.visibility = VisibilityState()
            self.opacity = 0
        self.fade_opacity(1, fade_duration)

    def fade_out(self, fade_duration=None):
        if fade_duration is None:
            fade_duration = ClientObjectMixin.FADE_DURATION
        self.fade_opacity(0, fade_duration)

    @distributor.fields.Field(op=distributor.ops.SetValue, default=None)
    def current_value(self):
        new_value = self._base_value
        statistic_component = self.statistic_component
        if statistic_component is not None:
            new_value += statistic_component.get_added_monetary_value()
        state_component = self.state_component
        if state_component is not None:
            return max(round(new_value*state_component.state_based_value_mod), 0)
        return max(new_value, 0)

    @current_value.setter
    def current_value(self, value):
        state_component = self.state_component
        if state_component is not None:
            self.base_value = value/state_component.state_based_value_mod
        else:
            self.base_value = value

    _resend_current_value = current_value.get_resend()

    def update_current_value(self, update_tooltip=True):
        self._resend_current_value()
        if update_tooltip:
            self.update_tooltip_field(TooltipFieldsComplete.simoleon_value, self.current_value)

    @property
    def base_value(self):
        return self._base_value

    @base_value.setter
    def base_value(self, value):
        self._base_value = round(max(value, 0))
        update_tooltip = self.get_tooltip_field(TooltipFieldsComplete.simoleon_value) is not None
        self.update_current_value(update_tooltip=update_tooltip)

    @property
    def depreciated_value(self):
        if not self.definition.get_can_depreciate():
            return self.catalog_value
        return self.catalog_value*(1 - self.INITIAL_DEPRECIATION)

    @property
    def catalog_value(self):
        return self.get_object_property(GameObjectProperty.CATALOG_PRICE)

    @property
    def depreciated(self):
        return not self._needs_depreciation

    def set_post_bb_fixup_needed(self):
        self._needs_post_bb_fixup = True
        self._needs_depreciation = True

    def try_post_bb_fixup(self, force_fixup=False, active_household_id=0):
        if force_fixup or self._needs_depreciation:
            if force_fixup:
                self._needs_depreciation = True
            self._on_try_depreciation(active_household_id=active_household_id)
        if force_fixup or self._needs_post_bb_fixup:
            self._needs_post_bb_fixup = False
            self.on_post_bb_fixup()

    @forward_to_components
    def on_post_bb_fixup(self):
        services.get_event_manager().process_events_for_household(test_events.TestEvent.ObjectAdd, services.household_manager().get(self._household_owner_id), obj=self)

    def _on_try_depreciation(self, active_household_id=0):
        if self._household_owner_id != active_household_id:
            return
        self._needs_depreciation = False
        if not self.definition.get_can_depreciate():
            return
        self.base_value = floor(self._base_value*(1 - self.INITIAL_DEPRECIATION))

    def register_for_on_children_changed_callback(self, callback):
        if self._on_children_changed is None:
            self._on_children_changed = CallableList()
        if callback not in self._on_children_changed:
            self._on_children_changed.append(callback)

    def unregister_for_on_children_changed_callback(self, callback):
        if self._on_children_changed is not None:
            if callback in self._on_children_changed:
                self._on_children_changed.remove(callback)
            if not self._on_children_changed:
                self._on_children_changed = None

    @distributor.fields.Field(op=distributor.ops.SetScratched, default=False)
    def scratched(self):
        return self._scratched

    @scratched.setter
    def scratched(self, scratched):
        self._scratched = scratched
