from _math import Vector3from interactions.constraints import Nowhere, create_constraint_set, OceanStartLocationConstraint, WaterDepthIntervals, WaterDepthIntervalConstraint, Circle, Constraintfrom objects.pools import pool_utilsfrom routing.waypoints.waypoint_generator import _WaypointGeneratorBasefrom sims4.color import Colorfrom sims4.geometry import CompoundPolygonfrom sims4.tuning.tunable import TunableRange, Tunable, TunableTuple, OptionalTunableimport build_buyimport debugvisimport randomimport routingimport sims4.loglogger = sims4.log.Logger('WaypointGeneratorPool')
class _WaypointGeneratorPool(_WaypointGeneratorBase):
    FACTORY_TUNABLES = {'constraint_width': TunableRange(description='\n            The width of the constraint created around the edge of the pool.\n            ', tunable_type=float, default=1.5, minimum=0), 'ocean_constraint_radius': TunableRange(description='\n            When in the ocean, the radius of the area around the nearest swim\n            portal to generate waypoints.\n            ', tunable_type=float, default=30, minimum=0, maximum=1000), 'ocean_constraint_distance_past_swim_portal': TunableRange(description='\n            When in the ocean, an offset away from the nearest swim portal to\n            center the area to generate waypoints.\n            ', tunable_type=float, default=0, minimum=0), 'ocean_unique_goal_count': TunableRange(description='\n            When in the ocean, the number of unique waypoints to generate.\n            ', tunable_type=int, default=10, minimum=0), 'shuffle_waypoints': Tunable(description='\n            If true, pool edge waypoint constraints will be shuffled and traversed in a random order.\n            If false, pool edge waypoint constraints will be traversed in counter-clockwise order.        \n            ', tunable_type=bool, default=True), 'keep_away_from_edges': OptionalTunable(description='\n            If enabled, turns on a constraint that forces sims away from the pool edges by a tuned distance.\n            ', tunable=Tunable(description='\n                The distance from the pool edge.\n                ', tunable_type=float, default=0.25))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sim = self._context.sim
        self._routing_surface = routing.SurfaceIdentifier(self._routing_surface.primary_id, self._routing_surface.secondary_id, routing.SurfaceType.SURFACETYPE_POOL)
        position = self._target.position if self._target is not None else sim.position
        level = self._routing_surface.secondary_id
        self._start_constraint = None
        self._master_depth_constraint = None
        self._waypoint_constraints = []
        self.keep_away_constraint = None
        self._location_is_pool = build_buy.is_location_pool(sim.zone_id, position, level)
        if self._location_is_pool:
            pool_block_id = build_buy.get_block_id(sim.zone_id, position, level - 1)
            pool = pool_utils.get_pool_by_block_id(pool_block_id)
            if pool is not None:
                pool_edge_constraints = pool.get_edge_constraint(constraint_width=self.constraint_width, inward_dir=True, return_constraint_list=True)
                pool_edge_constraints = [constraint.generate_geometry_only_constraint() for constraint in pool_edge_constraints]
                if self.keep_away_from_edges is not None:
                    bb_polys = build_buy.get_pool_polys(pool_block_id, sim.zone_id, level - 1)
                    if len(bb_polys) > 0:
                        bb_poly = bb_polys[0]
                        _WaypointGeneratorPool._push_poly_inward(bb_poly, self.keep_away_from_edges)
                        bb_poly.reverse()
                        keep_away_geom = sims4.geometry.RestrictedPolygon(sims4.geometry.Polygon(bb_poly), ())
                        self.keep_away_constraint = Constraint(routing_surface=pool.provided_routing_surface, geometry=keep_away_geom)
                    else:
                        logger.error(f'Pool Waypoint Generator: Pool polygon data unexpectedly empty while ${sim} was routing on a pool with id ${pool_block_id}.', owner='jmorrow')
                    for i in range(len(pool_edge_constraints)):
                        pool_edge_constraints[i] = pool_edge_constraints[i].intersect(self.keep_away_constraint)
                self._start_constraint = create_constraint_set(pool_edge_constraints)
                self._waypoint_constraints = pool_edge_constraints

    def get_start_constraint(self):
        if self._start_constraint is not None:
            return self._start_constraint
        sim = self._context.sim
        position = self._target.position if self._target is not None else sim.position
        relative_offset_vector = Vector3(0, 0, self.ocean_constraint_distance_past_swim_portal)
        if self._target is not None and self._target.routing_surface is not None:
            routing_surface = self._target.routing_surface
        else:
            routing_surface = sim.routing_surface
        if routing_surface.type != routing.SurfaceType.SURFACETYPE_POOL:
            self._start_constraint = OceanStartLocationConstraint.create_simple_constraint(WaterDepthIntervals.SWIM, self.ocean_constraint_radius, sim, self._target, position, ideal_radius=self.constraint_width, ideal_radius_width=self.constraint_width, relative_offset_vector=relative_offset_vector)
        else:
            self._start_constraint = Circle(position, self.ocean_constraint_radius, routing_surface=self._routing_surface)
        self._master_depth_constraint = WaterDepthIntervalConstraint.create_water_depth_interval_constraint(sim, WaterDepthIntervals.SWIM)
        self._start_constraint = self._start_constraint.intersect(self._master_depth_constraint)
        return self._start_constraint

    def get_waypoint_constraints_gen(self, routing_agent, waypoint_count):
        if self._start_constraint is None:
            self.get_start_constraint()
        goals = []
        handles = self._start_constraint.get_connectivity_handles(routing_agent)
        for handle in handles:
            goals.extend(handle.get_goals(always_reject_invalid_goals=True))
        agent_radius = routing_agent.routing_component.pathplan_context.agent_radius
        ocean_goal_count = min(len(goals), self.ocean_unique_goal_count)
        for _ in range(ocean_goal_count):
            goal = random.choice(goals)
            break
            goals.remove(goal)
            constraint = Circle(goal.position, agent_radius, routing_surface=self._routing_surface)
            self._waypoint_constraints.append(constraint.intersect(self._master_depth_constraint))
        available_waypoint_count = len(self._waypoint_constraints)
        if self._start_constraint is not None and (self._waypoint_constraints or goals and available_waypoint_count == 0):
            return
        use_pool_debug_visualizer = False and (routing.waypoints.waypoint_generator.enable_waypoint_visualization and self._location_is_pool)
        polygon_metadata = {}
        for i in range(waypoint_count):
            if not i % available_waypoint_count == 0 or self.shuffle_waypoints:
                random.shuffle(self._waypoint_constraints)
            yield self._waypoint_constraints[i % available_waypoint_count]
            if use_pool_debug_visualizer:
                self._build_polygon_metadata_dictionary(polygon_metadata, self._waypoint_constraints[i % available_waypoint_count], i)
        if use_pool_debug_visualizer and use_pool_debug_visualizer:
            self._draw_pool_debugvis(polygon_metadata)

    def _draw_pool_debugvis(self, polygon_metadata):
        color_palette = [Color.WHITE, Color.BLUE, Color.GREEN, Color.MAGENTA]
        if routing.waypoints.waypoint_generator.enable_waypoint_visualization:
            with debugvis.Context(routing.waypoints.waypoint_generator.DEBUGVIS_WAYPOINT_LAYER_NAME) as layer:
                for entry in polygon_metadata.values():
                    position = entry[0]
                    waypoint_indices = entry[1]
                    layer.add_text_world(position, {waypoint_indices})
                for (index, constraint) in enumerate(self._waypoint_constraints):
                    polygon = constraint.geometry.polygon
                    layer.add_polygon(polygon, color=color_palette[index % 4], altitude=0.1)
                if self.keep_away_from_edges is not None:
                    polygon = self.keep_away_constraint.geometry.polygon
                    layer.add_polygon(polygon, color=Color.BLACK, altitude=0.1)

    def _build_polygon_metadata_dictionary(self, polygon_metadata, constraint, waypoint_index):
        compound_polygon = constraint.geometry.polygon
        if isinstance(compound_polygon, CompoundPolygon):
            for polygon in compound_polygon:
                if len(polygon) > 0:
                    key = polygon
                    if key not in polygon_metadata:
                        center = sum(polygon, Vector3.ZERO())/len(polygon)
                        polygon_metadata[key] = (center, [])
                    waypoint_indices = polygon_metadata[key][1]
                    waypoint_indices.append(waypoint_index)
                else:
                    sim = self._context.sim
                    logger.error(f'Pool Waypoint Generator: Polygon unexpectedly contains no vertices while drawing debug visuals of ${sim}'s route', owner='jmorrow')
        else:
            sim = self._context.sim
            logger.error(f'Pool Waypoint Generator: Constraint geometry in unexpected format while drawing debug visuals of ${sim}'s route.', owner='jmorrow')

    @staticmethod
    def _push_poly_inward(verts, amt):
        for i in range(1, len(verts)):
            _WaypointGeneratorPool._push_edge_inward(verts, i - 1, i, amt)
        _WaypointGeneratorPool._push_edge_inward(verts, i, 0, amt)

    @staticmethod
    def _push_edge_inward(verts, start, stop, amt):
        along = amt*sims4.math.vector_normalize(verts[stop] - verts[start])
        inward = sims4.math.vector3_rotate_axis_angle(along, sims4.math.PI/2, sims4.math.Vector3.Y_AXIS())
        verts[start] += inward
        verts[stop] += inward
