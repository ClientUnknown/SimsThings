from fishing.fishing_data import TunableFishingBaitReferencefrom interactions.constraints import ANYWHEREfrom objects.client_object_mixin import ObjectParentTypefrom objects.components.state import TunableStateValueReferencefrom objects.object_enums import ResetReasonfrom routing.route_enums import RoutingStageEventfrom sims4.math import vector3_almost_equal, quaternion_almost_equalfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, OptionalTunable, TunableTuple, TunableMapping, TunableInterval, TunableRange, TunableReferenceimport fishing.fishing_dataimport interactionsimport objects.components.stateimport objects.components.typesimport placementimport routingimport servicesimport sims4.tuningimport vfxfrom fishing.fishing_tuning import FishingTuninglogger = sims4.log.Logger('FishingLocationComponent')
class FishingLocationComponentSafeToFishTuning(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'constraints': sims4.tuning.tunable.TunableList(description='\n            A list of constraints that, when intersected, will be used to determine\n            if the area described relative to the object is safe to fish.  It is\n            safe if there is nothing blocking the area.\n            ', tunable=interactions.constraint_variants.TunableGeometricConstraintVariant(description='\n                An element of the final constraint to determine the area to test.\n                '), minlength=1), 'safe_states': sims4.tuning.tunable.TunableList(description='\n            List of states to set on the object when it tests safe.\n            ', tunable=objects.components.state.TunableStateValueReference()), 'unsafe_states': sims4.tuning.tunable.TunableList(description='\n            List of states to set on the object when it tests unsafe.\n            ', tunable=objects.components.state.TunableStateValueReference()), 'safe_while_moving': sims4.tuning.tunable.Tunable(description='\n            Declare if moving objects are safe to fish.\n            ', tunable_type=bool, default=False)}

class FishingLocationComponent(objects.components.Component, sims4.tuning.tunable.HasTunableFactory, component_name=objects.components.types.FISHING_LOCATION_COMPONENT):

    class _FishVfxLiteral(AutoFactoryInit, HasTunableSingletonFactory):
        FACTORY_TUNABLES = {'effect_name': sims4.tuning.tunable.Tunable(description='\n                The name of the effect to play.\n                ', tunable_type=str, default='')}

        def get_effects(self, fishing_data, is_fishing_hole):
            return (self.effect_name,)

    class _FishVfxFromFishingData(HasTunableSingletonFactory):

        def get_effects(self, fishing_data, is_fishing_hole):
            if fishing_data is None:
                return ()
            effect_names = []
            for fish in fishing_data.get_possible_fish_gen():
                if is_fishing_hole:
                    location_vfx = fish.fish.cls.fishing_hole_vfx
                else:
                    location_vfx = fish.fish.cls.fishing_spot_vfx
                if location_vfx is not None:
                    effect_names.append(location_vfx)
            return effect_names

    VFX_SLOT_HASH = sims4.hash_util.hash32('_FX_')
    USE_REGION_TUNING = 1
    FACTORY_TUNABLES = {'fishing_data': sims4.tuning.tunable.TunableVariant(tuned=fishing.fishing_data.TunableFishingDataSnippet(), default='tuned', locked_args={'region': USE_REGION_TUNING}), 'fishing_vfx': sims4.tuning.tunable.TunableVariant(description='\n            A variant that defines the fish vfx to show on this object.\n            ', from_fishing_data=_FishVfxFromFishingData.TunableFactory(), literal=_FishVfxLiteral.TunableFactory(), default='from_fishing_data'), 'is_fishing_hole': sims4.tuning.tunable.Tunable(description='\n            If this is a Fishing Hole, check the box.\n            If this is a Fishing Spot, do not check the box.\n            ', tunable_type=bool, default=False), 'safe_to_fish_test': sims4.tuning.tunable.OptionalTunable(description='\n            If enabled, a test for when it is safe to fish will be performed\n            and the results used to trigger a state change.\n            ', tunable=FishingLocationComponentSafeToFishTuning.TunableFactory()), 'fishing_trap_data': OptionalTunable(description='\n            When enabled, the owner of this component can be used as a fishing\n            trap. This tunable will then hold the corresponding data for the \n            trap.\n            \n            Range - The range of outcomes that can occur depending on the state\n            that the trap is in when being emptied.\n            \n            Bait Modifers - A dictionary of bait -> modifers to apply to either\n            the min or the max values of the range when the bait is used in the\n            trap.\n            \n            Trap Object State - The state to use to look up the \n            ObjectStateValue being used to identify that state of the trap.\n            ', tunable=TunableTuple(description='\n                The data required to figure out how many items to catch.\n                ', range=TunableMapping(description='\n                    This is a mapping of the current object state value -> a range\n                    of items that can be caught.\n                    ', key_name='Object State', key_type=TunableStateValueReference(description='\n                        The state value that is associated with a specific range\n                        of items to be caught.\n                        '), value_name='Reward Range', value_type=TunableInterval(description='\n                        Tuning for the min and max number of items to catch.\n                        ', tunable_type=int, default_lower=1, default_upper=2, minimum=0)), bait_modifiers=TunableMapping(description='\n                    The modifiers to apply to the range of things being caught\n                    based on what type of bait is being used.\n                    ', key_name='Bait Type', key_type=TunableFishingBaitReference(description='\n                        The type of bait that will modify the range of items\n                        that are caught by a trap.\n                        '), value_name='Modifiers', value_type=TunableTuple(description='\n                        The modifiers to the min and max for items caught at a \n                        time.\n                        ', min_modifier=TunableRange(description='\n                            The multiplier to apply to the minimum number of\n                            items caught.\n                            ', tunable_type=float, minimum=0, default=1), max_modifier=TunableRange(description='\n                            The multiplier to apply to the maximum number of\n                            items caught.\n                            ', tunable_type=float, minimum=0, default=1))), trap_object_state=TunableReference(description='\n                    The Object State to use to know what the current state of the trap is.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectState',))))}

    def __init__(self, owner, fishing_data, fishing_vfx, is_fishing_hole, safe_to_fish_test, fishing_trap_data):
        super().__init__(owner)
        self._fishing_data = fishing_data
        self._fishing_vfx = fishing_vfx
        self._is_fishing_hole = is_fishing_hole
        self._safe_to_fish_test = safe_to_fish_test
        self._fish_vfx = []
        self._moving = False
        self._safe_to_fish_test_in_use_cache = None
        self._fishing_trap_data = fishing_trap_data

    def _on_add(self):
        for effect_name in self._fishing_vfx.get_effects(self.fishing_data, self._is_fishing_hole):
            fish_vfx = vfx.PlayEffect(self.owner, effect_name, self.VFX_SLOT_HASH)
            fish_vfx.start()
            self._fish_vfx.append(fish_vfx)
        if self.safe_to_fish_test_in_use:
            if self.owner.routing_component is not None:
                self.owner.routing_component.register_routing_stage_event(RoutingStageEvent.ROUTE_START, self._on_routing_stage_event_start)
                self.owner.routing_component.register_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_routing_stage_event_end)
            self.owner.register_on_location_changed(self._on_location_changed)

    def _on_remove(self):
        for fish_vfx in self._fish_vfx:
            fish_vfx.stop()
            fish_vfx = None
        self._fish_vfx = []
        if self.fishing_data is not None:
            if self.owner.routing_component is not None:
                self.owner.routing_component.unregister_routing_stage_event(RoutingStageEvent.ROUTE_START, self._on_routing_stage_event_start)
                self.owner.routing_component.unregister_routing_stage_event(RoutingStageEvent.ROUTE_END, self._on_routing_stage_event_end)
            if self.owner.is_on_location_changed_callback_registered(self._on_location_changed):
                self.owner.unregister_on_location_changed(self._on_location_changed)
            self._moving = False
            for state_value in self._safe_to_fish_test.unsafe_states:
                self.owner.state_component.set_state(state_value.state, state_value)

    def on_add(self, *_, **__):
        self._on_add()

    def on_remove(self, *_, **__):
        self._on_remove()

    def on_added_to_inventory(self):
        self._on_remove()

    def on_removed_from_inventory(self):
        self._on_add()

    def on_child_added(self, *_, **__):
        if self.safe_to_fish_test_in_use:
            self._test_safe_to_fish()

    def on_child_removed(self, *_, **__):
        if self.safe_to_fish_test_in_use:
            self._test_safe_to_fish()

    def on_parent_change(self, parent):
        if self.safe_to_fish_test_in_use:
            if parent is None:
                self._on_add()
            else:
                self._on_remove()

    def on_buildbuy_exit(self):
        if self.safe_to_fish_test_in_use:
            self._test_safe_to_fish()

    def component_reset(self, reset_reason):
        if reset_reason != ResetReason.BEING_DESTROYED and self.safe_to_fish_test_in_use:
            self._moving = False
            self._test_safe_to_fish()

    def on_finalize_load(self):
        if self.safe_to_fish_test_in_use:
            self._test_safe_to_fish()

    @property
    def fishing_data(self):
        if self._fishing_data is self.USE_REGION_TUNING:
            current_region = services.current_region()
            if current_region is not None:
                return current_region.fishing_data
            return
        return self._fishing_data

    @property
    def safe_to_fish_test_in_use(self):
        if self._safe_to_fish_test_in_use_cache is None:
            self._safe_to_fish_test_in_use_cache = self._safe_to_fish_test is not None and self.owner.state_component is not None
        return self._safe_to_fish_test_in_use_cache

    def _test_safe_to_fish(self):
        safe = True
        if self.owner.is_in_inventory() or self.owner.parent_type != ObjectParentType.PARENT_NONE or self.owner.location.routing_surface is None:
            safe = False
        elif self._moving:
            safe = self._safe_to_fish_test.safe_while_moving
        elif self._safe_to_fish_test.constraints is not None:
            sim = self.owner if self.owner.is_sim else None
            ignored_object_ids = [self.owner.id]
            if self.owner.vehicle_component:
                for child in self.owner.children:
                    if child.is_sim:
                        sim = child
                        ignored_object_ids.append(child.id)
                        break
            constraint_total = ANYWHERE
            for constraint_factory in self._safe_to_fish_test.constraints:
                constraint = constraint_factory.create_constraint(sim, sim, target_position=self.owner.location.transform.translation, target_forward=self.owner.location.transform.transform_vector(sims4.math.FORWARD_AXIS), routing_surface=self.owner.location.routing_surface)
                constraint_total = constraint_total.intersect(constraint)
            if sim is None and constraint_total.valid and constraint_total.geometry is not None:
                start_location = routing.Location(self.owner.location.transform.translation, self.owner.location.transform.orientation, self.owner.location.routing_surface)
                polygons = [constraint_total.geometry]

                def find_polygon_to_convert():
                    for polygon in polygons:
                        if not isinstance(polygon, sims4.geometry.Polygon):
                            return polygon

                polygon = find_polygon_to_convert()
                if polygon is not None:
                    if isinstance(polygon, sims4.geometry.RestrictedPolygon):
                        polygons.extend(polygon.polygon)
                    elif isinstance(polygon, sims4.geometry.CompoundPolygon):
                        polygons.extend(polygon)
                    polygons.remove(polygon)
                    polygon = find_polygon_to_convert()
                facing_angle = sims4.math.yaw_quaternion_to_angle(self.owner.location.transform.orientation)
                interval = sims4.geometry.interval_from_facing_angle(facing_angle, 0)
                abs_facing_range = sims4.geometry.AbsoluteOrientationRange(interval)
                fgl_context = placement.FindGoodLocationContext(start_location, object_polygons=polygons, restrictions=(abs_facing_range,), ignored_object_ids=ignored_object_ids, max_distance=0, terrain_tags=constraint_total.get_terrain_tags(), min_water_depth=constraint_total.get_min_water_depth(), max_water_depth=constraint_total.get_max_water_depth())
                (position, orientation) = placement.find_good_location(fgl_context)
                safe = position is not None and (orientation is not None and (vector3_almost_equal(start_location.position, position) and quaternion_almost_equal(start_location.orientation, orientation)))
            else:
                logger.warning('Safe to Fish Test Constraint did not describe anything testable for {}'.format(self.owner))
        if safe:
            for state_value in self._safe_to_fish_test.safe_states:
                self.owner.state_component.set_state(state_value.state, state_value)
        else:
            for state_value in self._safe_to_fish_test.unsafe_states:
                self.owner.state_component.set_state(state_value.state, state_value)

    def _on_routing_stage_event_start(self, owner, routing_event, **kwargs):
        self._moving = True
        self._test_safe_to_fish()

    def _on_routing_stage_event_end(self, owner, routing_event, **kwargs):
        self._moving = False
        self._test_safe_to_fish()

    def _on_location_changed(self, owner, old_location, new_location):
        if services.current_zone().is_zone_loading:
            return
        if not self._moving:
            self._test_safe_to_fish()

    def get_trap_range_of_outcomes(self, bait=None):
        if self._fishing_trap_data is None:
            logger.error("Trying to access fishing trap data on an object that isn't setup to be a fishing trap. {}", self.owner)
            return (0, 0)
        state_component = self.owner.state_component
        if state_component is None:
            logger.error("Trying to check a trap that doesn't have a state component for how many items to catch. Needs to have State component and the {} state", self._fishing_trap_data.trap_object_state)
            return (0, 0)
        fishing_trap_data = self._fishing_trap_data
        state_value = state_component.get_state(fishing_trap_data.trap_object_state)
        if state_value not in fishing_trap_data.range:
            return (0, 0)
        outcome_range = fishing_trap_data.range[state_value]
        minimum = outcome_range.lower_bound
        maximum = outcome_range.upper_bound
        if bait is not None:
            min_multiplier = 1
            max_multiplier = 1
            for (tag, bait_data) in FishingTuning.BAIT_TAG_DATA_MAP.items():
                if bait.has_tag(tag) and bait_data in fishing_trap_data.bait_modifiers:
                    min_multiplier *= fishing_trap_data.bait_modifiers[bait_data].min_modifier
                    max_multiplier *= fishing_trap_data.bait_modifiers[bait_data].max_modifier
            minimum *= min_multiplier
            maximum *= max_multiplier
        if minimum > maximum:
            logger.error('The maximum for number of fish to catch with a trap is lower than the minimum. Please fix the tuning of the min, max and bait multipliers to fix this issue. {}', self.owner)
            return (0, 0)
        return (int(minimum), int(maximum))
