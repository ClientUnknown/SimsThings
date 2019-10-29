import functoolsfrom animation.arb_element import distribute_arb_elementfrom build_buy import HouseholdInventoryFlagsfrom carry.carry_utils import hide_held_props, SCRIPT_EVENT_ID_STOP_CARRY, PARAM_CARRY_TRACK, SCRIPT_EVENT_ID_START_CARRY, set_carry_track_paramfrom interactions.utils.sim_focus import with_sim_focus, SimFocusfrom objects import VisibilityStatefrom objects.slots import get_surface_height_parameter_for_object, get_surface_height_parameter_for_heightfrom placement import FGLSearchFlagsDefaultForSim, FGLSearchFlagsDefaultfrom postures.posture_animation_data import AnimationDataUniversal, AnimationDataByActorSpeciesfrom postures.posture_specs import PostureSpecVariable, SURFACE_INDEX, SURFACE_TARGET_INDEXfrom routing import SurfaceTypefrom sims.sim_info_types import Speciesfrom sims4.collections import frozendictfrom sims4.log import StackVarfrom sims4.math import vector3_anglefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethod, classproperty, constpropertyimport animationimport animation.arbimport build_buyimport placementimport postures.postureimport routingimport servicesimport sims4.logimport sims4.mathlogger = sims4.log.Logger('Carry')
class CarrySystemTarget:

    def __init__(self, obj, put):
        self._obj = obj
        self._put = put

    @property
    def _route_target(self):
        return self._obj

    def get_constraint(self, sim, **kwargs):
        return self._obj.get_carry_transition_constraint(sim, self._route_target.position, self._route_target.routing_surface, **kwargs)

    @property
    def surface_height(self) -> str:
        return get_surface_height_parameter_for_object(self._obj)

    @property
    def has_custom_animation(self) -> bool:
        raise NotImplementedError()

    def append_custom_animation_to_arb(self, arb, carry_posture, normal_carry_callback):
        raise NotImplementedError()

    def carry_event_callback(self, *_, **__):
        raise NotImplementedError()

class CarrySystemTransientTarget(CarrySystemTarget):

    def __init__(self, obj, put):
        super().__init__(obj, put)

    @property
    def surface_height(self) -> str:
        return 'discard'

    @property
    def has_custom_animation(self) -> bool:
        return False

    def carry_event_callback(self, *_, **__):
        self._obj.remove_from_client()

class CarrySystemTerrainTarget(CarrySystemTarget):

    def __init__(self, sim, obj, put, transform, routing_surface=None, custom_event_callback=None):
        super().__init__(obj, put)
        self._sim = sim
        self._transform = sims4.math.Transform(translation=transform.translation, orientation=transform.orientation)
        if put:
            put_down_strategy = obj.get_put_down_strategy(parent=sim)
            if put_down_strategy.put_down_on_terrain_facing_sim:
                angle = sims4.math.yaw_quaternion_to_angle(transform.orientation) + sims4.math.PI
                self._transform.orientation = sims4.math.angle_to_yaw_quaternion(angle)
            else:
                angle = vector3_angle(transform.orientation.transform_vector(sims4.math.Vector3.X_AXIS()))
                self._transform.orientation = sims4.math.angle_to_yaw_quaternion(angle)
        self._routing_surface = routing_surface
        self._custom_event_callback = custom_event_callback

    @property
    def transform(self):
        return self._transform

    @property
    def surface_height(self) -> str:
        routing_surface = self._routing_surface or self._obj.routing_surface
        surface_height = services.terrain_service.terrain_object().get_routing_surface_height_at(self.transform.translation.x, self.transform.translation.z, routing_surface)
        terrain_height = services.terrain_service.terrain_object().get_routing_surface_height_at(self._sim.position.x, self._sim.position.z, self._sim.routing_surface)
        return get_surface_height_parameter_for_height(surface_height - terrain_height)

    @property
    def has_custom_animation(self) -> bool:
        return False

    def carry_event_callback(self, *args, **kwargs):
        if self._put:
            CarryingObject.snap_to_good_location_on_floor(self._obj, starting_transform=self._transform, starting_routing_surface=self._routing_surface)
        if self._custom_event_callback is not None:
            self._custom_event_callback(*args, **kwargs)

    def get_constraint(self, sim, **kwargs):
        constraint = self._obj.get_pick_up_constraint(sim)
        if constraint is not None:
            return constraint
        return super().get_constraint(sim, **kwargs)

class CarrySystemCustomAnimationTarget(CarrySystemTarget):
    _custom_constraint = None
    _custom_animation = None

    def get_constraint(self, sim, **kwargs):
        if self._custom_constraint is not None:
            return self._custom_constraint
        return super().get_constraint(sim, **kwargs)

    @property
    def has_custom_animation(self) -> bool:
        return self._custom_animation is not None

    def append_custom_animation_to_arb(self, arb, carry_posture, normal_carry_callback):
        custom_carry_event_callback = self.carry_event_callback

        def _carry_event_callback(*_, **__):
            custom_carry_event_callback()
            normal_carry_callback()

        self.carry_event_callback = _carry_event_callback
        self._custom_animation(arb, carry_posture.sim, carry_posture.target, carry_posture.track, carry_posture.animation_context, self.surface_height)

class CarrySystemRuntimeSlotTarget(CarrySystemCustomAnimationTarget):

    def __init__(self, sim, obj, put, runtime_slot):
        super().__init__(obj, put)
        if runtime_slot is None:
            raise RuntimeError('Attempt to create a CarrySystemRuntimeSlotTarget with no runtime slot!')
        self._runtime_slot = runtime_slot
        if not runtime_slot.owner.is_sim:
            self._custom_constraint = runtime_slot.owner.get_surface_access_constraint(sim, put, obj)
            self._custom_animation = runtime_slot.owner.get_surface_access_animation(put)
        self._sim = sim

    @property
    def _route_target(self):
        return self._runtime_slot

    @property
    def surface_height(self) -> str:
        (_, surface_height) = self._runtime_slot.get_slot_height_and_parameter(self._sim)
        return surface_height

    def carry_event_callback(self, *_, **__):
        if self._put:
            self._runtime_slot.add_child(self._obj)

    def get_constraint(self, sim, **kwargs):
        constraint = self._obj.get_pick_up_constraint(sim)
        if constraint is not None:
            return constraint
        return super().get_constraint(sim, **kwargs)

class CarrySystemInventoryTarget(CarrySystemCustomAnimationTarget):

    def __init__(self, sim, obj, is_put, inventory_owner):
        super().__init__(obj, is_put)
        self._inventory_owner = inventory_owner
        self._custom_constraint = inventory_owner.get_inventory_access_constraint(sim, is_put, obj)
        self._custom_animation = inventory_owner.get_inventory_access_animation(is_put)

    @property
    def surface_height(self) -> str:
        if self._inventory_owner.is_sim:
            return 'inventory'
        return 'high'

    def carry_event_callback(self, *_, **__):
        if self._put:
            self._inventory_owner.inventory_component.system_add_object(self._obj)

class CarrySystemDestroyTarget(CarrySystemCustomAnimationTarget):

    @property
    def surface_height(self) -> str:
        return 'high'

    def carry_event_callback(self, *_, **__):
        self._obj.remove_from_client()

class CarryPosture(postures.posture.Posture):
    INSTANCE_SUBCLASSES_ONLY = True
    _XEVT_ID = None
    IS_BODY_POSTURE = False

    @constproperty
    def mobile():
        return True

    @classmethod
    def post_load(cls, manager):
        species_to_provided_postures = {}
        for (species, provided_postures, _) in cls._animation_data.get_supported_postures_gen():
            species_to_provided_postures[species] = provided_postures
        cls._provided_postures = frozendict(species_to_provided_postures)

    @classmethod
    def _tuning_loaded_callback(cls):
        services.get_instance_manager(sims4.resources.Types.POSTURE).add_on_load_complete(cls.post_load)

    @flexmethod
    def get_provided_postures(cls, inst, *args, species=Species.HUMAN, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        return inst_or_cls._provided_postures[species]

    def _event_handler_start_pose(self, *args, **kwargs):
        arb = animation.arb.Arb()
        self.asm.request(self._state_name, arb)
        distribute_arb_element(arb)

    def append_transition_to_arb(self, arb, source_posture, in_xevt_handler=False, **kwargs):
        self.asm.context.register_custom_event_handler(functools.partial(hide_held_props, self.sim), None, 0, allow_stub_creation=True)
        super().append_transition_to_arb(arb, source_posture, **kwargs)
        if in_xevt_handler:
            self.asm.request(self._state_name, arb)
        else:
            arb.register_event_handler(self._event_handler_start_pose, animation.ClipEventType.Script, self._XEVT_ID)

    @property
    def slot_constraint(self):
        pass

class CarryingNothing(CarryPosture):
    _XEVT_ID = SCRIPT_EVENT_ID_STOP_CARRY
    INSTANCE_TUNABLES = {'_animation_data': AnimationDataUniversal.TunableFactory(animation_data_options={'locked_args': {'_idle_animation': None}}, tuning_group=GroupNames.ANIMATION)}

    def _setup_asm_carry_parameter(self, asm, target):
        if not asm.set_parameter(PARAM_CARRY_TRACK, self.track.name.lower()):
            logger.warn('Failed to set {} on {}.', PARAM_CARRY_TRACK, asm.name)

    @property
    def source_interaction(self):
        pass

    @source_interaction.setter
    def source_interaction(self, value):
        pass

    def append_transition_to_arb(self, arb, source_posture, in_xevt_handler=False, locked_params=frozendict(), **kwargs):
        if source_posture is not None:
            target = source_posture.target
            if target is not None:
                target_anim_overrides = target.get_anim_overrides(source_posture.get_target_name())
                locked_params += target_anim_overrides.params
                self.asm.set_actor(source_posture.get_target_name(), source_posture.target)
        objects_to_find = []
        for object_id in arb.actor_ids:
            object_found = services.object_manager().get(object_id)
            if object_found is not None and object_found.carryable_component is not None:
                objects_to_find.append(object_found)
        for object_found in objects_to_find:
            if in_xevt_handler:
                object_found.carryable_component.on_object_uncarry(self.sim)
            else:
                arb.register_event_handler(lambda *args, **kwargs: object_found.carryable_component.on_object_uncarry(self.sim, *args, **kwargs), animation.ClipEventType.Script, SCRIPT_EVENT_ID_STOP_CARRY)
        super().append_transition_to_arb(arb, source_posture, locked_params=locked_params, in_xevt_handler=in_xevt_handler, **kwargs)

    def _update_non_body_posture_asm(self):
        pass

class CarryingObject(CarryPosture):
    _XEVT_ID = SCRIPT_EVENT_ID_START_CARRY
    INSTANCE_TUNABLES = {'_animation_data': AnimationDataByActorSpecies.TunableFactory(animation_data_options={'locked_args': {'_idle_animation': None}}, tuning_group=GroupNames.ANIMATION)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.holster_count = 0
        self.carry_system_target = None

    @property
    def is_two_handed_carry(self):
        return False

    @property
    def holstered(self):
        if self.holster_count:
            return True
        return False

    def _setup_asm_carry_parameter(self, asm, target):
        set_carry_track_param(asm, self.get_target_name(target=target), target, self.track)
        f1 = self.sim.forward
        f2 = -target.forward
        angle = sims4.math.vector3_angle(f1) - sims4.math.vector3_angle(f2)
        if angle > sims4.math.PI:
            angle = angle - sims4.math.TWO_PI
        elif angle < -sims4.math.PI:
            angle = sims4.math.TWO_PI + angle
        angle = sims4.math.rad_to_deg(angle)
        asm.set_parameter('RelativePickUpAngle', angle)

    def add_transition_extras(self, sequence, **kwargs):
        return with_sim_focus(self.sim, self.sim, self.target, SimFocus.LAYER_INTERACTION, sequence)

    @property
    def target_is_transient(self) -> bool:
        if self.target is not None:
            return self.target.transient
        return False

    SNAP_TO_GOOD_LOCATION_SEARCH_FLAGS = placement.FGLSearchFlagsDefault | placement.FGLSearchFlag.SHOULD_TEST_BUILDBUY

    @staticmethod
    def get_good_location_on_floor(target, *, starting_transform, starting_routing_surface, additional_search_flags=0):
        starting_location = placement.create_starting_location(transform=starting_transform, routing_surface=starting_routing_surface)
        if target.is_sim:
            search_flags = FGLSearchFlagsDefaultForSim
            fgl_context_fn = placement.create_fgl_context_for_sim
        else:
            search_flags = FGLSearchFlagsDefault
            fgl_context_fn = placement.create_fgl_context_for_object
        search_flags |= additional_search_flags
        fgl_context = fgl_context_fn(starting_location, target, search_flags=search_flags)
        (translation, orientation) = placement.find_good_location(fgl_context)
        return (translation, orientation)

    @staticmethod
    def snap_to_good_location_on_floor(target, *args, starting_transform=None, starting_routing_surface=None, **kwargs):
        target.visibility = VisibilityState(True, True, True)
        parent = target.get_parenting_root()
        if starting_transform is None:
            starting_transform = parent.transform
            starting_transform = sims4.math.Transform(parent.position + parent.forward*parent.object_radius, starting_transform.orientation)
        if starting_routing_surface is None:
            starting_routing_surface = parent.routing_surface
        translation = None
        orientation = None
        is_lot_clearing = services.current_zone().is_active_lot_clearing
        if not is_lot_clearing:
            (translation, orientation) = CarryingObject.get_good_location_on_floor(target, *args, starting_transform=starting_transform, starting_routing_surface=starting_routing_surface, **kwargs)
        if translation is not None:
            target.clear_parent(sims4.math.Transform(translation, orientation), starting_routing_surface)
            return True
        logger.debug('snap_to_good_location_on_floor could not find good location for {}.', target)
        clear_transform = starting_transform
        clear_routing_surface = starting_routing_surface
        if not (is_lot_clearing or build_buy.has_floor_at_location(services.current_zone_id(), starting_transform.translation, starting_routing_surface.secondary_id)):
            clear_routing_surface = routing.SurfaceIdentifier(services.current_zone_id(), 0, routing.SurfaceType.SURFACETYPE_WORLD)
            ground_position = sims4.math.Vector3(starting_transform.translation.x, starting_transform.translation.y, starting_transform.translation.z)
            ground_position.y = services.terrain_service.terrain_object().get_routing_surface_height_at(starting_transform.translation.x, starting_transform.translation.z, clear_routing_surface)
            clear_transform = sims4.math.Transform(ground_position, starting_transform.orientation)
        target.clear_parent(clear_transform, clear_routing_surface)
        return False

    def setup_asm_posture(self, asm, sim, target, **kwargs):
        result = super().setup_asm_posture(asm, sim, target, **kwargs)
        if result and ('locked_params' not in kwargs or 'surfaceHeight' not in kwargs['locked_params']):
            surface_height = get_surface_height_parameter_for_object(target, sim=sim)
            self.asm.set_parameter('surfaceHeight', surface_height)
        return result

    def append_transition_to_arb(self, arb, source_posture, in_xevt_handler=False, locked_params=frozendict(), posture_spec=None, **kwargs):
        if in_xevt_handler:
            locked_params += {'surfaceHeight': 'from_xevt'}
            super().append_transition_to_arb(arb, source_posture, locked_params=locked_params, in_xevt_handler=in_xevt_handler, **kwargs)
            if self.target.carryable_component is not None:
                self.target.carryable_component.on_object_carry(self.sim)
            return
        carry_system_target = CarrySystemTerrainTarget(self.sim, self.target, False, self.target.transform)
        if self.target.is_in_inventory():
            if self.target.is_in_sim_inventory():
                obj_with_inventory = self.target.get_inventory().owner
            elif posture_spec is not None:
                surface = posture_spec[SURFACE_INDEX]
                obj_with_inventory = surface[SURFACE_TARGET_INDEX]
            else:
                obj_with_inventory = None
            if obj_with_inventory is None:
                obj_with_inventory = self.target.get_inventory().owner
            carry_system_target = CarrySystemInventoryTarget(self.sim, self.target, False, obj_with_inventory)
        else:
            runtime_slot = self.target.parent_slot
            if runtime_slot is not None:
                carry_system_target = CarrySystemRuntimeSlotTarget(self.sim, self.target, False, runtime_slot)
            else:
                target_routing_surface = self.target.routing_surface
                if target_routing_surface.type == SurfaceType.SURFACETYPE_OBJECT:
                    locked_params += {'surfaceHeight': carry_system_target.surface_height}
            if self.target.parent is not None:
                self.asm.set_actor('surface', self.target.parent)
        call_super = True
        if carry_system_target.has_custom_animation:

            def normal_carry_callback():
                arb = animation.arb.Arb()
                self.append_transition_to_arb(arb, source_posture, locked_params=locked_params, in_xevt_handler=True)
                distribute_arb_element(arb)

            carry_system_target.append_custom_animation_to_arb(arb, self, normal_carry_callback)
            call_super = False
        if self.target.carryable_component is not None:
            arb.register_event_handler(lambda *args, **kwargs: self.target.carryable_component.on_object_carry(self.sim, *args, **kwargs), animation.ClipEventType.Script, SCRIPT_EVENT_ID_START_CARRY)
        arb.register_event_handler(carry_system_target.carry_event_callback, animation.ClipEventType.Script, SCRIPT_EVENT_ID_START_CARRY)
        if call_super:
            super().append_transition_to_arb(arb, source_posture, locked_params=locked_params, in_xevt_handler=in_xevt_handler, **kwargs)

    def append_exit_to_arb(self, arb, dest_state, dest_posture, var_map, exit_while_holding=False, **kwargs):
        if exit_while_holding:
            self.asm.set_parameter('surfaceHeight', 'from_xevt')
            if self.target_is_transient:
                self.target.remove_from_client()
            if not self.holstered:
                super().append_exit_to_arb(arb, dest_state, dest_posture, var_map, **kwargs)
            return
        if self.carry_system_target is None:
            (surface, slot_var) = dest_state.get_slot_info()
            has_slot_surface = surface is not None and slot_var is not None
            if self.target_is_transient and not has_slot_surface:
                self.carry_system_target = CarrySystemTransientTarget(self.target, True)
            else:
                if slot_var is None:
                    self.sim.schedule_reset_asap(cause='slot_var is None in append_exit_to_arb where we expect to be putting an object down in a slot')
                    logger.error('slot_var is None in append_exit_to_arb: arb: {} dest_state: {} dest_posture: {} var_map: {} for sim: {} and target: {}', arb, dest_state, dest_posture, var_map, self.sim, self.target, owner='bosee')
                    return
                self.asm.set_actor('surface', surface)
                if slot_var not in var_map:
                    stack_var = StackVar(('slot_var', 'var_map', '_interaction', 'dest_state'))
                    raise RuntimeError('Unable to retrieve slot variable: {}'.format(stack_var))
                slot_manifest = var_map[slot_var]
                var_map += {PostureSpecVariable.SURFACE_TARGET: surface}
                slot_manifest = slot_manifest.apply_actor_map(var_map.get)
                runtime_slot = slot_manifest.runtime_slot
                if runtime_slot is None:
                    raise RuntimeError('Attempt to create a CarrySystemRuntimeSlotTarget with no valid runtime slot: {}'.format(slot_manifest))
                self.carry_system_target = CarrySystemRuntimeSlotTarget(self.sim, self.target, True, runtime_slot)
        arb.register_event_handler(self.carry_system_target.carry_event_callback, animation.ClipEventType.Script, SCRIPT_EVENT_ID_STOP_CARRY)
        if self.carry_system_target.has_custom_animation:

            def normal_carry_callback():
                arb = animation.arb.Arb()
                self.append_exit_to_arb(arb, dest_state, dest_posture, var_map, exit_while_holding=True)
                distribute_arb_element(arb)

            self.carry_system_target.append_custom_animation_to_arb(arb, self, normal_carry_callback)
            return
        self.asm.set_parameter('surfaceHeight', self.carry_system_target.surface_height)
        super().append_exit_to_arb(arb, dest_state, dest_posture, var_map, **kwargs)

    def _drop_carried_object(self):
        if self.target is None:
            return
        if self.target.is_sim:
            return
        if self.target_is_transient or self.target.parent is not self.sim:
            return
        if self.snap_to_good_location_on_floor(self.target):
            return
        if self.sim.household.id is self.target.get_household_owner_id() and self.sim.inventory_component.player_try_add_object(self.target):
            return
        placement_flags = build_buy.get_object_placement_flags(self.target.definition.id)
        if placement_flags & build_buy.PlacementFlags.NON_DELETEABLE and placement_flags & build_buy.PlacementFlags.NON_INVENTORYABLE:
            logger.error("Failed to find a location to place {}, which cannot be deleted or moved to the household inventory.                           Object will be placed at the Sim's feet, but this is unsafe and will probably result in the object being                           destroyed on load.", self.target, owner='tastle')
            return
        if placement_flags & build_buy.PlacementFlags.NON_INVENTORYABLE:
            self.target.destroy(source=self.sim, cause='Failed to find location to drop non inventoryable object.')
        elif not build_buy.move_object_to_household_inventory(self.target, failure_flags=HouseholdInventoryFlags.DESTROY_OBJECT):
            logger.warn('Failed to drop carried object {}, which cannot be placed in the household inventory. This object will be destroyed.', self.target, owner='rmccord')

    def _on_reset(self):
        super()._on_reset()
        self._drop_carried_object()
