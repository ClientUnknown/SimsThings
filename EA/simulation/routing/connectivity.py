from animation import animation_constantsfrom interactions.constraints import Constraintfrom interactions.utils.routing import SlotGoalfrom native.routing.connectivity import Handle, HandleListfrom postures.posture_specs import PostureSpecVariablefrom routing import SurfaceTypefrom sims.sim_info_types import Age, SpeciesExtendedfrom sims4.collections import frozendictfrom sims4.utils import constpropertyfrom world.ocean_tuning import OceanTuningimport placementimport routingimport servicesimport sims4.mathVALID_GOAL_VALUES = (0, 1)
class RoutingHandle(Handle):

    def __init__(self, sim, constraint, geometry, los_reference_point=None, routing_surface_override=None, locked_params=frozendict(), target=None):
        if routing_surface_override is not None:
            self.routing_surface = routing_surface_override
        elif constraint.routing_surface is not None:
            self.routing_surface = constraint.routing_surface
        else:
            self.routing_surface = sim.routing_surface
        super().__init__(geometry.polygon, self.routing_surface)
        self.locked_params = locked_params
        self.sim = sim
        self.constraint = constraint
        self.geometry = geometry
        self.los_reference_point = los_reference_point
        self.target = target

    def clone(self, **overrides):
        kwargs = {}
        self._get_kwargs_for_clone(kwargs)
        kwargs.update(overrides)
        clone = type(self)(**kwargs)
        if hasattr(self, 'path'):
            clone.path = self.path
        if hasattr(self, 'var_map'):
            clone.var_map = self.var_map
        return clone

    def get_los_reference_point(self, routing_surface, force_multi_surface=False):
        if force_multi_surface or self.constraint.multi_surface:
            return
        return self.los_reference_point

    def _get_kwargs_for_clone(self, kwargs):
        kwargs.update(sim=self.sim, constraint=self.constraint, geometry=self.geometry, los_reference_point=self.los_reference_point, routing_surface_override=self.routing_surface, locked_params=self.locked_params)

    def get_goals(self, max_goals=None, relative_object=None, single_goal_only=False, for_carryable=False, for_source=False, goal_height_limit=None, target_reference_override=None, always_reject_invalid_goals=False, perform_los_check=True):
        force_multi_surface = relative_object is not None and (relative_object.force_multi_surface_constraints or relative_object.is_sim and relative_object.routing_surface != self.sim.routing_surface)
        if force_multi_surface or not (self.constraint.multi_surface and for_source):
            routing_surfaces = self.constraint.get_all_valid_routing_surfaces(force_multi_surface=force_multi_surface)
        else:
            routing_surfaces = {self.routing_surface}
        if max_goals is None:
            max_goals = self.constraint.ROUTE_GOAL_COUNT_FOR_SCORING_FUNC
        orientation_restrictions = self.geometry.restrictions
        objects_to_ignore = set(self.constraint._objects_to_ignore or ())
        if relative_object is not None and not relative_object.is_sim:
            objects_to_ignore.add(relative_object.id)
        objects_to_ignore.add(self.sim.id)
        posture = getattr(self.sim, 'posture', None)
        if posture is not None and posture.target is not None:
            objects_to_ignore.add(posture.target.id)
        if hasattr(self, 'var_map'):
            carry_target = self.var_map[PostureSpecVariable.CARRY_TARGET]
            if carry_target is not None and getattr(carry_target, 'is_sim', False):
                objects_to_ignore.add(carry_target.id)
        provided_points = self.constraint.get_provided_points_for_goals()
        min_water_depth = self.constraint.get_min_water_depth()
        max_water_depth = self.constraint.get_max_water_depth()
        terrain_tags = self.constraint.get_terrain_tags()
        wading_interval = OceanTuning.get_actor_wading_interval(self.sim)
        all_blocking_edges_block_los = self.los_reference_point is not None and (single_goal_only and (not for_carryable and self.for_slot_constraint))
        los_routing_context = None
        if relative_object is not None:
            try:
                if relative_object.is_sim or relative_object.is_part and relative_object.part_owner is None:
                    return []
                los_routing_context = relative_object.raycast_context(for_carryable=for_carryable)
            except AttributeError as exc:
                raise AttributeError('\n    Relative object for sim: {}\n    for constraint: {}\n    with head interaction: {}\n    has no raycast context\n {}'.format(self.sim, self.constraint, self.sim.queue.get_head(), exc))
        sim_is_big_dog = self.sim.is_sim and (self.sim.extended_species is SpeciesExtended.DOG and self.sim.age > Age.CHILD)
        if los_routing_context is not None and all_blocking_edges_block_los and (self.sim.extended_species is SpeciesExtended.HUMAN or sim_is_big_dog):
            los_routing_context.set_key_mask(los_routing_context.get_key_mask() | routing.FOOTPRINT_KEY_REQUIRE_LARGE_HEIGHT)
        generated_goals = []
        surface_costs = {}
        for routing_surface in routing_surfaces:
            if routing_surface is None:
                pass
            else:
                los_reference_pt = None
                if perform_los_check:
                    los_reference_pt = self.get_los_reference_point(routing_surface, force_multi_surface=force_multi_surface)
                (surface_min_water_depth, surface_max_water_depth) = OceanTuning.make_depth_bounds_safe_for_surface(routing_surface, wading_interval=wading_interval, min_water_depth=min_water_depth, max_water_depth=max_water_depth)
                goals = placement.generate_routing_goals_for_polygon(self.sim, self.geometry.polygon, routing_surface, orientation_restrictions, objects_to_ignore, flush_planner=self.constraint._flush_planner, los_reference_pt=los_reference_pt, max_points=max_goals, ignore_outer_penalty_amount=self.constraint._ignore_outer_penalty_threshold, single_goal_only=single_goal_only, los_routing_context=los_routing_context, all_blocking_edges_block_los=all_blocking_edges_block_los, provided_points=provided_points, min_water_depth=surface_min_water_depth, max_water_depth=surface_max_water_depth, terrain_tags=terrain_tags)
                if not goals:
                    pass
                else:
                    surface_costs[routing_surface.type] = self.sim.get_additional_scoring_for_surface(routing_surface.type)
                    generated_goals.extend(goals)
        if not generated_goals:
            return []
        minimum_router_cost = self._get_minimum_router_cost()
        target_obj = self.target.part_owner if self.target is not None and self.target.is_part else self.target
        target_height = None
        height_obj = target_obj if target_reference_override is None else target_reference_override
        if height_obj.is_valid_for_height_checks:
            parent_obj = height_obj.parent
            if parent_obj is not None:
                target_height = parent_obj.position.y
            else:
                target_height = height_obj.position.y
        is_line_obj = goal_height_limit is not None and height_obj is not None and target_obj is not None and target_obj.waiting_line_component is not None
        is_single_point = self._is_geometry_single_point()
        goal_list = []
        water_constraint_cache = dict()
        max_goal_height = self.sim.position.y
        for (tag, (location, cost, validation)) in enumerate(generated_goals):
            invalid_goal = not (for_source or validation in VALID_GOAL_VALUES)
            if always_reject_invalid_goals and invalid_goal:
                pass
            elif invalid_goal and (sim_is_big_dog or is_line_obj or relative_object is not None and is_single_point):
                pass
            elif not self._is_generated_goal_location_valid(location, goal_height_limit, target_height):
                pass
            else:
                if invalid_goal:
                    if location.routing_surface in water_constraint_cache:
                        water_constraint = water_constraint_cache[location.routing_surface]
                    else:
                        (surface_min_water_depth, surface_max_water_depth) = OceanTuning.make_depth_bounds_safe_for_surface(location.routing_surface, wading_interval=wading_interval, min_water_depth=min_water_depth, max_water_depth=max_water_depth)
                        water_constraint = self.constraint.intersect(Constraint(min_water_depth=surface_min_water_depth, max_water_depth=surface_max_water_depth))
                        water_constraint_cache[location.routing_surface] = water_constraint
                    if not water_constraint.is_location_water_depth_valid(location):
                        pass
                    elif not self.constraint.is_location_terrain_tags_valid(location):
                        pass
                    else:
                        if cost > sims4.math.EPSILON:
                            cost = max(cost, minimum_router_cost)
                        full_cost = self._get_location_cost(location.position, location.orientation, location.routing_surface, cost)
                        full_cost += surface_costs[location.routing_surface.type]
                        if minimum_router_cost is not None and self.constraint.enables_height_scoring:
                            full_cost += max_goal_height - location.position.y
                        goal = self.create_goal(location, full_cost, tag)
                        goal_list.append(goal)
                if cost > sims4.math.EPSILON:
                    cost = max(cost, minimum_router_cost)
                full_cost = self._get_location_cost(location.position, location.orientation, location.routing_surface, cost)
                full_cost += surface_costs[location.routing_surface.type]
                if minimum_router_cost is not None and self.constraint.enables_height_scoring:
                    full_cost += max_goal_height - location.position.y
                goal = self.create_goal(location, full_cost, tag)
                goal_list.append(goal)
        return goal_list

    def create_goal(self, location, full_cost, tag):
        return routing.Goal(location, cost=full_cost, tag=tag, requires_los_check=self.los_reference_point is not None, connectivity_handle=self)

    def _is_generated_goal_location_valid(self, location, goal_height_limit=None, target_height=None):
        if goal_height_limit is None or target_height is None:
            return True
        else:
            goal_y = location.position.y
            y_delta = abs(goal_y - target_height)
            if y_delta > goal_height_limit:
                return False
        return True

    def _get_location_cost(self, position, orientation, routing_surface, router_cost):
        return router_cost + sum(cost_fn.constraint_cost(position, orientation, routing_surface) for cost_fn in self.constraint._scoring_functions)

    def _is_geometry_single_point(self):
        if len(self.geometry.polygon) == 1 and len(self.geometry.polygon[0]) == 1:
            return True
        return False

    def _get_minimum_router_cost(self):
        pass

    @constproperty
    def for_slot_constraint():
        return False

class SlotRoutingHandle(RoutingHandle):

    def __init__(self, *args, reference_transform=None, entry=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._entry = entry
        self._reference_transform = reference_transform

    def _get_kwargs_for_clone(self, kwargs):
        super()._get_kwargs_for_clone(kwargs)
        kwargs.update(reference_transform=self._reference_transform, entry=self._entry)

    def create_goal(self, location, full_cost, tag):
        reference_transform = self._reference_transform
        if reference_transform is None:
            reference_transform = self.constraint.containment_transform if self._entry else self.constraint.containment_transform_exit
        initial_transform = location.transform if self._entry else reference_transform
        target_transform = reference_transform if self._entry else location.transform
        if self._entry:
            target_orientation = target_transform.orientation
        else:
            v = target_transform.translation - initial_transform.translation
            target_orientation = sims4.math.angle_to_yaw_quaternion(sims4.math.vector3_angle(v))
        locked_params = dict(self.locked_params)
        locked_params[('InitialTranslation', 'x')] = initial_transform.translation
        locked_params[('InitialOrientation', 'x')] = initial_transform.orientation
        locked_params[(animation_constants.ASM_TARGET_TRANSLATION, 'x')] = target_transform.translation
        locked_params[(animation_constants.ASM_TARGET_ORIENTATION, 'x')] = target_orientation
        locked_params = frozendict(locked_params)
        if location.orientation == sims4.math.Quaternion.ZERO():
            goal_location = routing.Location(location.position, orientation=target_orientation, routing_surface=location.routing_surface)
        else:
            goal_location = location
        return SlotGoal(goal_location, containment_transform=self.constraint.containment_transform, cost=full_cost, tag=tag, requires_los_check=self.los_reference_point is not None, connectivity_handle=self, slot_params=locked_params)

    def _get_location_cost(self, position, orientation, routing_surface, router_cost):
        transform = self.constraint.containment_transform
        return super()._get_location_cost(transform.translation, transform.orientation, routing_surface, router_cost)

    def _get_minimum_router_cost(self):
        if self._is_geometry_single_point():
            return 1

    @constproperty
    def for_slot_constraint():
        return True

class UniversalSlotRoutingHandle(SlotRoutingHandle):

    def __init__(self, *args, cost_functions_override=None, posture=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._cost_functions_override = cost_functions_override
        self._posture = posture

    def _get_kwargs_for_clone(self, kwargs):
        super()._get_kwargs_for_clone(kwargs)
        kwargs.update(cost_functions_override=self._cost_functions_override, posture=self._posture)

    def get_los_reference_point(self, routing_surface, force_multi_surface=False):
        if routing_surface.type == routing.SurfaceType.SURFACETYPE_WORLD:
            return self.los_reference_point

    def _is_generated_goal_location_valid(self, location, goal_height_limit=None, target_height=None):
        if not self._validate_y_delta(location):
            return False
        elif not self._validate_raycast(location):
            return False
        return True

    def _validate_y_delta(self, location):
        universal_data = self._get_universal_data()
        if universal_data is None or universal_data.y_delta_interval is None:
            return True
        else:
            y_start = location.position.y
            y_end = self.constraint.containment_transform.translation.y
            y_delta = y_end - y_start
            if y_delta not in universal_data.y_delta_interval:
                return False
        return True

    def _validate_raycast(self, location):
        universal_data = self._get_universal_data()
        if universal_data is None or universal_data.raycast_test is None:
            return True
        start_pos = location.position
        end_pos = self.constraint.containment_transform.translation
        target = self.target if self._entry else self.sim.posture.target
        if location.routing_surface.type == routing.SurfaceType.SURFACETYPE_OBJECT:
            footprint_polygon = target.footprint_polygon if target is not None else None
            if footprint_polygon and footprint_polygon.contains(sims4.math.Vector2(start_pos.x, start_pos.z)):
                return True
            else:
                offset = sims4.math.vector_normalize_2d(end_pos - start_pos)
                offset *= universal_data.raycast_test.horizontal_offset
                offset.y = universal_data.raycast_test.vertical_offset
                end_pos_offsetted = end_pos + offset
                if placement.ray_intersects_placement_3d(services.current_zone_id(), start_pos, end_pos_offsetted, objects_to_ignore=[target.id]):
                    return False
        offset = sims4.math.vector_normalize_2d(end_pos - start_pos)
        offset *= universal_data.raycast_test.horizontal_offset
        offset.y = universal_data.raycast_test.vertical_offset
        end_pos_offsetted = end_pos + offset
        if placement.ray_intersects_placement_3d(services.current_zone_id(), start_pos, end_pos_offsetted, objects_to_ignore=[target.id]):
            return False
        return True

    def _get_universal_data(self):
        if self._posture is None:
            return
        return self._posture.universal

    def _get_location_cost(self, position, orientation, routing_surface, router_cost):
        if self._cost_functions_override is None:
            return super()._get_location_cost(position, orientation, routing_surface, router_cost)
        return router_cost + sum(cost_fn.constraint_cost(position, orientation, routing_surface) for cost_fn in self._cost_functions_override)
