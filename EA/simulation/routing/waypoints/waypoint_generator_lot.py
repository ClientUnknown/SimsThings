from _collections import defaultdictimport itertoolsimport mathfrom build_buy import get_all_block_polygons, get_block_idfrom interactions.constraints import Anywhere, Circlefrom plex import plex_enumsfrom routing.waypoints.waypoint_generator import _WaypointGeneratorBase, WaypointContextfrom routing.waypoints.waypoint_generator_tags import _WaypointGeneratorMultipleObjectByTagfrom sims4.geometry import CompoundPolygon, random_uniform_points_in_compound_polygon, Polygonfrom sims4.math import MAX_INT32from sims4.tuning.tunable import TunableRange, OptionalTunableimport routingimport services
class _WaypointGeneratorLotPoints(_WaypointGeneratorBase):
    FACTORY_TUNABLES = {'constraint_radius': TunableRange(description='\n            The radius, in meters, for each of the generated waypoint\n            constraints.\n            ', tunable_type=float, default=2, minimum=0), 'object_tag_generator': OptionalTunable(description='\n            If enabled, in addition to generating random points on the lot, this\n            generator also ensures that all constraints that would be generated\n            by the Tag generator are also hit.\n            \n            This gets you a very specific behavior: apparent randomness but the\n            guarantee that all objects with specific tags are route to.\n            ', tunable=_WaypointGeneratorMultipleObjectByTag.TunableFactory())}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim = self._context.sim

    def get_start_constraint(self):
        return self.get_water_constraint()

    def _get_polygons_for_lot(self):
        lot = services.active_lot()
        return [(CompoundPolygon(Polygon(list(reversed(lot.corners)))), self._routing_surface)]

    def _get_waypoint_constraints_from_polygons(self, polygons, object_constraints, waypoint_count):
        object_constraints = dict(object_constraints)
        total_area = sum(p.area() for (p, _) in itertools.chain.from_iterable(polygons.values()))
        sim_location = self._sim.routing_location
        sim_routing_context = self._sim.get_routing_context()
        restriction = None
        if self.object_tag_generator is not None:
            restriction = self.object_tag_generator.placement_restriction
        final_constraints = []
        for (block_id, block_data) in polygons.items():
            block_object_constraints = object_constraints.pop(block_id, ())
            if restriction is not None:
                if restriction and block_id == 0:
                    pass
                elif restriction or block_id != 0:
                    pass
                else:
                    for (polygon, routing_surface) in block_data:
                        polygon_waypoint_count = math.ceil(waypoint_count*(polygon.area()/total_area))
                        for position in random_uniform_points_in_compound_polygon(polygon, num=int(polygon_waypoint_count)):
                            if not routing.test_connectivity_pt_pt(sim_location, routing.Location(position, routing_surface=self._routing_surface), sim_routing_context):
                                pass
                            else:
                                position_constraint = Circle(position, self.constraint_radius, routing_surface=routing_surface)
                                for block_object_constraint in tuple(block_object_constraints):
                                    intersection = block_object_constraint.intersect(position_constraint)
                                    if intersection.valid:
                                        block_object_constraints.remove(block_object_constraint)
                                final_constraints.append(position_constraint)
                    final_constraints.extend(block_object_constraints)
            else:
                for (polygon, routing_surface) in block_data:
                    polygon_waypoint_count = math.ceil(waypoint_count*(polygon.area()/total_area))
                    for position in random_uniform_points_in_compound_polygon(polygon, num=int(polygon_waypoint_count)):
                        if not routing.test_connectivity_pt_pt(sim_location, routing.Location(position, routing_surface=self._routing_surface), sim_routing_context):
                            pass
                        else:
                            position_constraint = Circle(position, self.constraint_radius, routing_surface=routing_surface)
                            for block_object_constraint in tuple(block_object_constraints):
                                intersection = block_object_constraint.intersect(position_constraint)
                                if intersection.valid:
                                    block_object_constraints.remove(block_object_constraint)
                            final_constraints.append(position_constraint)
                final_constraints.extend(block_object_constraints)
        final_constraints.extend(itertools.chain.from_iterable(object_constraints.values()))
        return final_constraints

    def get_waypoint_constraints_gen(self, routing_agent, waypoint_count):
        zone_id = services.current_zone_id()
        object_constraints = defaultdict(list)
        if self.object_tag_generator is not None:
            object_tag_generator = self.object_tag_generator(WaypointContext(self._sim), None)
            for constraint in itertools.chain((object_tag_generator.get_start_constraint(),), object_tag_generator.get_waypoint_constraints_gen(routing_agent, MAX_INT32)):
                level = constraint.routing_surface.secondary_id
                block_id = get_block_id(zone_id, constraint.average_position, level)
                object_constraints[block_id].append(constraint)
        plex_id = services.get_plex_service().get_active_zone_plex_id() or plex_enums.INVALID_PLEX_ID
        block_data = get_all_block_polygons(services.current_zone_id(), plex_id)
        polygons = defaultdict(list)
        if self._routing_surface.secondary_id == 0:
            polygons[0] = self._get_polygons_for_lot()
        for (block_id, (polys, level)) in block_data.items():
            if level != self._routing_surface.secondary_id:
                pass
            else:
                polygon = CompoundPolygon([Polygon(list(reversed(p))) for p in polys])
                if not polygon.area():
                    pass
                else:
                    polygons[block_id].append((polygon, self._routing_surface))
        if not polygons:
            return False
        final_constraints = self._get_waypoint_constraints_from_polygons(polygons, object_constraints, waypoint_count)
        final_constraints = self.apply_water_constraint(final_constraints)
        yield from final_constraints
