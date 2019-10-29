from _math import Vector3from animation.posture_manifest_constants import STAND_OR_SIT_CONSTRAINT, STAND_OR_MOVING_STAND_CONSTRAINT, STAND_AT_NONE_CONSTRAINTfrom event_testing.results import TestResultfrom interactions import ParticipantTypefrom interactions.base.super_interaction import SuperInteractionfrom interactions.base.tuningless_interaction import create_tuningless_superinteractionfrom interactions.constraints import Constraint, build_weighted_cone, WaterDepthIntervals, OceanStartLocationConstraint, ANYWHERE, Nowherefrom interactions.utils.routing import PlanRoutefrom objects.pools import pool_utilsfrom sims4.collections import frozendictfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.utils import flexmethod, classpropertyfrom singletons import DEFAULTimport element_utilsimport interactionsimport routingimport servicesimport sims4.geometryimport sims4.logimport sims4.mathlogger = sims4.log.Logger('SatisfyConstraintInteraction')PRIVACY_MIN_DISTANCE = 1
class SitOrStandSuperInteraction(SuperInteraction):

    @classmethod
    def _is_linked_to(cls, super_affordance):
        return True

    @classmethod
    def _test(cls, target, context, allow_posture_changes=False, **kwargs):
        if context.sim.posture.mobile or not allow_posture_changes:
            return TestResult(False, 'Sims can only satisfy constraints when they are mobile.')
        if context.sim.is_dying:
            return TestResult(False, 'Sims cannot satisfy constraints when they are dying.')
        return super()._test(target, context, **kwargs)

    @classproperty
    def super_affordance_can_share_target(cls):
        return True

    def is_adjustment_interaction(self):
        return self._is_adjustment_interaction

    def __init__(self, *args, constraint_to_satisfy=DEFAULT, run_element=None, is_adjustment_interaction=False, **kwargs):
        super().__init__(*args, **kwargs)
        if constraint_to_satisfy is DEFAULT:
            constraint_to_satisfy = STAND_OR_SIT_CONSTRAINT
        self._constraint_to_satisfy = constraint_to_satisfy
        self._run_element = run_element
        self._is_adjustment_interaction = is_adjustment_interaction

    @flexmethod
    def constraint_intersection(cls, inst, sim=DEFAULT, participant_type=ParticipantType.Actor, **kwargs):
        if inst is None or participant_type != ParticipantType.Actor or inst._constraint_to_satisfy is None:
            return ANYWHERE
        if inst._constraint_to_satisfy is not DEFAULT:
            return inst._constraint_to_satisfy
        if sim is DEFAULT:
            sim = inst.get_participant(participant_type)
        return sim.si_state.get_total_constraint(to_exclude=inst)

    def _run_interaction_gen(self, timeline):
        self.sim.routing_component.on_slot = None
        result = yield from super()._run_interaction_gen(timeline)
        if not result:
            return False
        elif self._run_element is not None:
            result = yield from element_utils.run_child(timeline, self._run_element)
            return result
        return True
lock_instance_tunables(SitOrStandSuperInteraction, _constraints=frozendict(), _constraints_actor=ParticipantType.Object)
class SatisfyConstraintSuperInteraction(SitOrStandSuperInteraction):
    INSTANCE_SUBCLASSES_ONLY = True
create_tuningless_superinteraction(SatisfyConstraintSuperInteraction)
class ForceSatisfyConstraintSuperInteraction(SatisfyConstraintSuperInteraction):
    INSTANCE_SUBCLASSES_ONLY = True

    @classmethod
    def is_adjustment_interaction(cls):
        return False
create_tuningless_superinteraction(ForceSatisfyConstraintSuperInteraction)
class ExitMobilePostureSuperInteraction(SuperInteraction):
    PERIMETER_WIDTH = 2.0

    def __init__(self, *args, run_element=None, is_adjustment_interaction=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._run_element = run_element
        self._is_adjustment_interaction = is_adjustment_interaction

    @classmethod
    def _is_linked_to(cls, super_affordance):
        return True

    @classproperty
    def super_affordance_can_share_target(cls):
        return True

    @classmethod
    def _get_exit_mobile_posture_constraint(cls, sim, participant_type=ParticipantType.Actor):
        posture_graph_service = services.current_zone().posture_graph_service
        posture_obj = posture_graph_service.get_compatible_mobile_posture_target(sim)
        if posture_obj is not None:
            return posture_obj.get_edge_constraint(sim=sim)
        else:
            return STAND_AT_NONE_CONSTRAINT

    @flexmethod
    def constraint_intersection(cls, inst, sim=DEFAULT, participant_type=ParticipantType.Actor, **kwargs):
        if participant_type != ParticipantType.Actor:
            return ANYWHERE
        inst_or_cls = inst if inst is not None else cls
        if sim is DEFAULT:
            sim = inst_or_cls.get_participant(participant_type)
        exit_posture_constraint = inst_or_cls._get_exit_mobile_posture_constraint(sim, participant_type=participant_type)
        return exit_posture_constraint

    def is_adjustment_interaction(self):
        return self._is_adjustment_interaction

    def _run_interaction_gen(self, timeline):
        self.sim.routing_component.on_slot = None
        result = yield from super()._run_interaction_gen(timeline)
        if not result:
            return False
        elif self._run_element is not None:
            result = yield from element_utils.run_child(timeline, self._run_element)
            return result
        return True

class BuildAndForceSatisfyShooConstraintInteraction(SuperInteraction):
    INSTANCE_SUBCLASSES_ONLY = True
    TRIVIAL_SHOO_RADIUS = 0.5
    PLEX_LOT_CORNER_ADJUSTMENT = 2.0

    def __init__(self, *args, privacy_inst=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._must_run_instance = True
        self._privacy = privacy_inst

    def _run_interaction_gen(self, timeline):
        result = yield from super()._run_interaction_gen(timeline)
        if not result:
            return False
        if self._privacy is not None:
            constraint_to_satisfy = yield from self._create_constraint_set(self.context.sim, timeline)
            if not constraint_to_satisfy.valid:
                constraint_to_satisfy = Nowhere('BuildAndForceSatisfyShooConstraintInteraction._run_interaction_gen, constraint_to_satisfy({}) is not valid, SI: {}', constraint_to_satisfy, self)
                logger.warn('Failed to generate a valid Shoo constraint. Defaulting to Nowhere().')
        else:
            logger.error('Trying to create a BuildAndForceSatisfyShooConstraintInteraction without a valid privacy instance.', owner='tastle')
            constraint_to_satisfy = Nowhere('BuildAndForceSatisfyShooConstraintInteraction._run_interaction_gen, SI has no valid privacy instance: {}', self)
        context = self.context.clone_for_continuation(self)
        constraint_to_satisfy = constraint_to_satisfy.intersect(STAND_OR_MOVING_STAND_CONSTRAINT)
        result = self.sim.push_super_affordance(ForceSatisfyConstraintSuperInteraction, None, context, allow_posture_changes=True, constraint_to_satisfy=constraint_to_satisfy, name_override='ShooFromPrivacy')
        if not result:
            logger.debug('Failed to push ForceSatisfyConstraintSuperInteraction on Sim {} to route them out of a privacy area.  Result: {}', self.sim, result, owner='tastle')
        return result

    def _find_close_position(self, p1, p2):
        found_new_position = False
        invalid_pos = False
        valid_pos = False
        while not found_new_position:
            p3 = sims4.math.Vector3((p1.x + p2.x)/2, p1.y, (p1.z + p2.z)/2)
            if (p1 - p3).magnitude_2d() <= PRIVACY_MIN_DISTANCE:
                return p1
            if not sims4.geometry.test_point_in_compound_polygon(p3, self._privacy.constraint.geometry.polygon):
                valid_pos = True
                p1 = p3
                if valid_pos:
                    found_new_position = True
                    if valid_pos:
                        invalid_pos = True
                    p2 = p3
            else:
                if valid_pos:
                    invalid_pos = True
                p2 = p3
        return p3

    def _create_constraint_set(self, sim, timeline):
        orient = sims4.math.Quaternion.IDENTITY()
        positions = services.current_zone().lot.corners
        position = positions[0]
        routing_surface = self._privacy.constraint.get_world_routing_surface(force_world=True)
        if self._privacy._routing_surface_only:
            routing_surfaces = (routing_surface,)
        else:
            routing_surfaces = self._privacy.constraint.get_all_valid_routing_surfaces()
        goals = []
        center_pos = services.current_zone().lot.position
        for pos in positions:
            plex_service = services.get_plex_service()
            if plex_service.is_active_zone_a_plex():
                towards_center_vec = sims4.math.vector_normalize(center_pos - pos)
                pos = pos + towards_center_vec*self.PLEX_LOT_CORNER_ADJUSTMENT
                pos.y = services.terrain_service.terrain_object().get_routing_surface_height_at(pos.x, pos.z, routing_surface)
            if not sims4.geometry.test_point_in_compound_polygon(pos, self._privacy.constraint.geometry.polygon):
                for surface in routing_surfaces:
                    goals.append(routing.Goal(routing.Location(pos, orient, surface)))
        obj_pos = self._privacy.central_object.position
        for offset in self._privacy.additional_exit_offsets:
            goals.append(routing.Goal(routing.Location(obj_pos + Vector3(offset.x, 0, offset.y), orient, surface)))
        if not goals:
            return Nowhere('BuildAndForceSatisfyShooConstraintInteraction, Could not generate goals to exit a privacy region, Sim: {} Privacy Region: {}', sim, self._privacy.constraint.geometry.polygon)
        route = routing.Route(sim.routing_location, goals, routing_context=sim.routing_context)
        plan_primitive = PlanRoute(route, sim, reserve_final_location=False, interaction=self)
        yield from element_utils.run_child(timeline, plan_primitive)
        max_distance = self._privacy._max_line_of_sight_radius*self._privacy._max_line_of_sight_radius*4
        nodes = []
        path = plan_primitive.path
        while path is not None:
            nodes.extend(path.nodes)
            path = path.next_path
        if nodes:
            previous_node = nodes[0]
            for node in nodes:
                node_vector = sims4.math.Vector3(node.position[0], node.position[1], node.position[2])
                if not sims4.geometry.test_point_in_compound_polygon(node_vector, self._privacy.constraint.geometry.polygon):
                    position = node_vector
                    if node.portal_id != 0:
                        pass
                    else:
                        circle_constraint = interactions.constraints.Circle(position, self.TRIVIAL_SHOO_RADIUS, node.routing_surface_id)
                        if circle_constraint.intersect(self._privacy.constraint).valid:
                            pass
                        else:
                            break
                            previous_node = node
                previous_node = node
            position2 = sims4.math.Vector3(previous_node.position[0], previous_node.position[1], previous_node.position[2])
            if (position - position2).magnitude_2d_squared() > max_distance:
                position = self._find_close_position(position, position2)
        elif (position - sim.position).magnitude_2d_squared() > max_distance:
            position = self._find_close_position(position, sim.position)
        p1 = position
        p2 = self._privacy.central_object.position
        forward = sims4.math.vector_normalize(p1 - p2)
        radius_min = 0
        radius_max = self._privacy.shoo_constraint_radius
        angle = sims4.math.PI
        (cone_geometry, cost_functions) = build_weighted_cone(position, forward, radius_min, radius_max, angle, ideal_radius_min=0, ideal_radius_max=0, ideal_angle=1)
        subtracted_cone_polygon_list = []
        for cone_polygon in cone_geometry.polygon:
            for privacy_polygon in self._privacy.constraint.geometry.polygon:
                subtracted_cone_polygons = cone_polygon.subtract(privacy_polygon)
                if subtracted_cone_polygons:
                    subtracted_cone_polygon_list.extend(subtracted_cone_polygons)
        compound_subtracted_cone_polygon = sims4.geometry.CompoundPolygon(subtracted_cone_polygon_list)
        subtracted_cone_geometry = sims4.geometry.RestrictedPolygon(compound_subtracted_cone_polygon, [])
        subtracted_cone_constraint = Constraint(geometry=subtracted_cone_geometry, scoring_functions=cost_functions, routing_surface=routing_surface, debug_name='ShooedSimsCone', multi_surface=True, los_reference_point=position)
        point_cost = 5
        point_constraint = interactions.constraints.Position(position, routing_surface=routing_surface, multi_surface=True)
        point_constraint = point_constraint.generate_constraint_with_cost(point_cost)
        constraints = (subtracted_cone_constraint, point_constraint)
        return interactions.constraints.create_constraint_set(constraints, debug_name='ShooPositions')

    @classmethod
    def _is_linked_to(cls, super_affordance):
        return True
create_tuningless_superinteraction(BuildAndForceSatisfyShooConstraintInteraction)