from weakref import WeakSetfrom event_testing.resolver import SingleSimResolver, SingleObjectResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.liability import Liabilityfrom interactions.priority import Priorityfrom interactions.utils.routing import FollowPathfrom objects.components.line_of_sight_component import LineOfSightfrom routing import FootprintTypefrom sims4.geometry import PolygonFootprintfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.resources import Typesfrom sims4.service_manager import Servicefrom sims4.tuning.geometric import TunableVector2from sims4.tuning.tunable import TunableFactory, Tunable, TunableReference, OptionalTunable, TunableTuple, TunableRange, TunableListfrom socials.jigs.jig_reserved_space import TunableReservedSpacefrom socials.jigs.jig_utils import _generate_single_poly_rectangle_pointsimport placementimport routingimport servicesimport sims4.geometryimport sims4.logimport snippetslogger = sims4.log.Logger('Privacy')
class PrivacyService(Service):

    def __init__(self):
        self._privacy_instances = WeakSet()
        self._potential_vehicles_to_check = WeakSet()

    @property
    def privacy_instances(self):
        return self._privacy_instances

    def check_for_late_violators(self, sim):
        for privacy in self.privacy_instances:
            if not sim in privacy.violators:
                if sim in privacy.late_violators:
                    pass
                elif privacy.is_sim_shoo_exempt(sim):
                    if not privacy.persistent_instance:
                        privacy.add_exempt_sim(sim)
                        if privacy.persistent_instance:
                            privacy.remove_sim_from_allowed_disallowed(sim)
                        if sim not in privacy.find_violating_sims():
                            pass
                        else:
                            privacy.handle_late_violator(sim)
                            return True
                else:
                    if privacy.persistent_instance:
                        privacy.remove_sim_from_allowed_disallowed(sim)
                    if sim not in privacy.find_violating_sims():
                        pass
                    else:
                        privacy.handle_late_violator(sim)
                        return True
        return False

    def add_instance(self, instance):
        self._privacy_instances.add(instance)

    def remove_instance(self, instance):
        self.privacy_instances.discard(instance)

    def stop(self):
        while self.privacy_instances:
            instance = self.privacy_instances.pop()
            instance.cleanup_privacy_instance()
        self._potential_vehicles_to_check.clear()

    def get_potential_vehicle_violators(self):
        return self._potential_vehicles_to_check

    def add_vehicle_to_monitor(self, vehicle):
        self._potential_vehicles_to_check.add(vehicle)

    def remove_vehicle_to_monitor(self, vehicle):
        self._potential_vehicles_to_check.discard(vehicle)

class Privacy(LineOfSight):
    _PRIVACY_SURFACE_BLOCKING_FOOTPRINT_COST = 100000
    _PRIVACY_DISCOURAGEMENT_COST = routing.get_default_discouragement_cost()
    _SHOO_CONSTRAINT_RADIUS = Tunable(description='\n        The radius of the constraint a Shooed Sim will attempt to route to.\n        ', tunable_type=float, default=2.5)
    _UNAVAILABLE_TOOLTIP = TunableLocalizedStringFactory(description='\n        Tooltip displayed when an object is not accessible due to being inside\n        a privacy region.\n        ')
    _EMBARRASSED_AFFORDANCE = TunableReference(description='\n        The affordance a Sim will play when getting embarrassed by walking in\n        on a privacy situation.\n        ', manager=services.get_instance_manager(Types.INTERACTION))

    def __init__(self, *, interaction=None, tests=None, shoo_exempt_tests=None, max_line_of_sight_radius=None, map_divisions=None, simplification_ratio=None, boundary_epsilon=None, facing_offset=None, routing_surface_only=None, shoo_constraint_radius=None, unavailable_tooltip=None, embarrassed_affordance=None, reserved_surface_space=None, vehicle_tests=None, central_object=None, post_route_affordance=None, add_to_privacy_service=True, privacy_cost_override=None, additional_exit_offsets=None, persistent_instance=False):
        super().__init__(max_line_of_sight_radius, map_divisions, simplification_ratio, boundary_epsilon)
        logger.assert_raise(bool(interaction) != bool(central_object), 'Privacy must define either one of interaction or central object, and never both.')
        self._max_line_of_sight_radius = max_line_of_sight_radius
        self._interaction = interaction
        self._tests = tests
        self._shoo_exempt_tests = shoo_exempt_tests
        self._privacy_constraints = []
        self._allowed_sims = WeakSet()
        self._disallowed_sims = WeakSet()
        self._violators = WeakSet()
        self._late_violators = WeakSet()
        self._exempt_sims = WeakSet()
        self.is_active = False
        self.has_shooed = False
        self.central_object = central_object
        self.additional_exit_offsets = additional_exit_offsets
        self._multi_surface = True
        self.persistent_instance = persistent_instance
        self._routing_surface_only = routing_surface_only
        self._shoo_constraint_radius = shoo_constraint_radius
        self._unavailable_tooltip = unavailable_tooltip
        self._embarrassed_affordance = embarrassed_affordance
        self._reserved_surface_space = reserved_surface_space
        self._post_route_affordance = post_route_affordance
        self._privacy_cost_override = privacy_cost_override
        self._vehicle_tests = vehicle_tests
        self._pushed_interactions = []
        if add_to_privacy_service:
            self.add_privacy()

    @property
    def shoo_constraint_radius(self):
        return self._shoo_constraint_radius or self._SHOO_CONSTRAINT_RADIUS

    @property
    def unavailable_tooltip(self):
        return self._unavailable_toolip or self._UNAVAILABLE_TOOLTIP

    @property
    def embarrassed_affordance(self):
        return self._embarrassed_affordance or self._EMBARRASSED_AFFORDANCE

    @property
    def privacy_discouragement_cost(self):
        return self._privacy_cost_override or self._PRIVACY_DISCOURAGEMENT_COST

    @property
    def interaction(self):
        return self._interaction

    @property
    def is_active(self) -> bool:
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        self._is_active = value

    def _is_sim_allowed(self, sim):
        if self._tests:
            resolver = SingleSimResolver(sim.sim_info) if self._interaction is None else self._interaction.get_resolver(target=sim)
            if self._tests and self._tests.run_tests(resolver):
                return True
            elif self._interaction is not None and self._interaction.can_sim_violate_privacy(sim):
                return True
        if self._interaction is not None and self._interaction.can_sim_violate_privacy(sim):
            return True
        return False

    def evaluate_sim(self, sim):
        if self._is_sim_allowed(sim):
            self._allowed_sims.add(sim)
            return True
        self._disallowed_sims.add(sim)
        return False

    def build_privacy(self, target=None):
        self.is_active = True
        if self.central_object is None:
            target_object = self._interaction.get_participant(ParticipantType.Object)
            target_object = None if target_object.is_sim else target_object
            self.central_object = target_object or (target or self._interaction.sim)
        if self._routing_surface_only:
            allow_object_routing_surface = True
            routing_surface = self.central_object.provided_routing_surface
            if routing_surface is None:
                return False
        else:
            allow_object_routing_surface = False
            routing_surface = self.central_object.routing_surface
        self.generate(self.central_object.position, routing_surface, allow_object_routing_surface=allow_object_routing_surface)
        for poly in self.constraint.geometry.polygon:
            self._privacy_constraints.append(PolygonFootprint(poly, routing_surface=routing_surface, cost=self.privacy_discouragement_cost, footprint_type=FootprintType.FOOTPRINT_TYPE_PATH, enabled=True))
        if self._reserved_surface_space is not None and target is not None:
            reserved_space = self._reserved_surface_space.reserved_space
            polygon = _generate_single_poly_rectangle_points(target.position, target.part_owner.orientation.transform_vector(sims4.math.Vector3.Z_AXIS()), target.part_owner.orientation.transform_vector(sims4.math.Vector3.X_AXIS()), reserved_space.left, reserved_space.right, reserved_space.front, reserved_space.back)
            routing_surface = self.central_object.provided_routing_surface
            if routing_surface is None:
                routing_surface = target.routing_surface
            footprint_cost = self.privacy_discouragement_cost if self._reserved_surface_space.allow_routing else self._PRIVACY_SURFACE_BLOCKING_FOOTPRINT_COST
            self._privacy_constraints.append(PolygonFootprint(polygon, routing_surface=routing_surface, cost=footprint_cost, footprint_type=FootprintType.FOOTPRINT_TYPE_PATH, enabled=True))
        if self._interaction is not None:
            self._allowed_sims.update(self._interaction.get_participants(ParticipantType.AllSims))
        for sim in services.sim_info_manager().instanced_sims_gen():
            if sim not in self._allowed_sims:
                self.evaluate_sim(sim)
        violating_sims = self.find_violating_sims()
        self._exempt_sims = set([s for s in violating_sims if self.is_sim_shoo_exempt(s)])
        self._cancel_unavailable_interactions(violating_sims)
        self._add_overrides_and_constraints_if_needed(violating_sims)
        violating_vehicles = self.find_violating_vehicles()
        for vehicle in violating_vehicles:
            vehicle.objectrouting_component.handle_privacy_violation(self)
        return True

    def cleanup_privacy_instance(self):
        if self.is_active:
            self.is_active = False
            for sim in self._allowed_sims:
                self.remove_override_for_sim(sim)
            for sim in self._late_violators:
                self.remove_override_for_sim(sim)
            del self._privacy_constraints[:]
            self._allowed_sims.clear()
            self._disallowed_sims.clear()
            self._violators.clear()
            self._late_violators.clear()
            self._exempt_sims.clear()
            self._cancel_pushed_interactions()

    def add_privacy(self):
        services.privacy_service().add_instance(self)

    def remove_privacy(self):
        self.cleanup_privacy_instance()
        services.privacy_service().remove_instance(self)

    def intersects_with_object(self, obj):
        if obj.routing_surface != self.central_object.routing_surface:
            return False
        delta = obj.position - self.central_object.position
        distance = delta.magnitude_2d_squared()
        if distance > self.max_line_of_sight_radius*self.max_line_of_sight_radius:
            return False
        object_footprint = obj.footprint_polygon
        if object_footprint is None:
            object_footprint = sims4.geometry.CompoundPolygon([sims4.geometry.Polygon([obj.position])])
        return self.constraint.geometry.polygon.intersects(object_footprint)

    def vehicle_violates_privacy(self, vehicle):
        if vehicle.objectrouting_component is None:
            return False
        if self._vehicle_tests is not None:
            resolver = SingleObjectResolver(vehicle)
            if self._vehicle_tests.run_tests(resolver):
                return False
            elif not self.intersects_with_object(vehicle):
                return False
        elif not self.intersects_with_object(vehicle):
            return False
        return True

    def find_violating_vehicles(self):
        violators = []
        privacy_service = services.privacy_service()
        for vehicle in privacy_service.get_potential_vehicle_violators():
            if self.vehicle_violates_privacy(vehicle):
                violators.append(vehicle)
        return violators

    def find_violating_sims(self, consider_exempt=True):
        if not self.is_active:
            return []
        check_all_surfaces_on_level = not self._routing_surface_only
        nearby_sims = placement.get_nearby_sims_gen(self.central_object.position, self._routing_surface, radius=self.max_line_of_sight_radius, exclude=self._allowed_sims, only_sim_position=True, check_all_surfaces_on_level=check_all_surfaces_on_level)
        violators = []
        for sim in nearby_sims:
            if consider_exempt and sim in self._exempt_sims:
                pass
            elif any(sim_primitive.is_traversing_portal() for sim_primitive in sim.primitives if isinstance(sim_primitive, FollowPath)):
                pass
            elif sim not in self._disallowed_sims and self.evaluate_sim(sim):
                pass
            elif sims4.geometry.test_point_in_compound_polygon(sim.position, self.constraint.geometry.polygon):
                violators.append(sim)
        return violators

    def is_sim_shoo_exempt(self, sim):
        if sim in self._exempt_sims:
            return True
        if self.central_object.provided_routing_surface == sim.location.routing_surface:
            return False
        elif self._shoo_exempt_tests:
            resolver = SingleSimResolver(sim.sim_info)
            if self._shoo_exempt_tests.run_tests(resolver):
                return True
        return False

    def add_exempt_sim(self, sim):
        self._exempt_sims.add(sim)

    def _add_overrides_and_constraints_if_needed(self, violating_sims):
        for sim in self._allowed_sims:
            self.add_override_for_sim(sim)
        for sim in violating_sims:
            self._violators.add(sim)
            if sim in self._exempt_sims:
                pass
            else:
                liabilities = ((SHOO_LIABILITY, ShooLiability(self, sim)),)
                result = self._route_sim_away(sim, liabilities=liabilities)
                if result:
                    self._pushed_interactions.append(result.interaction)

    def _cancel_unavailable_interactions(self, violating_sims):
        for sim in violating_sims:
            if sim in self._exempt_sims:
                pass
            else:
                interactions_to_cancel = set()
                if sim.queue.running is not None:
                    interactions_to_cancel.add(sim.queue.running)
                for interaction in sim.si_state:
                    if interaction.is_super and interaction.target is not None and sim.locked_from_obj_by_privacy(interaction.target):
                        interactions_to_cancel.add(interaction)
                for interaction in sim.queue:
                    if interaction.target is not None and sim.locked_from_obj_by_privacy(interaction.target):
                        interactions_to_cancel.add(interaction)
                    elif interaction.target is not None:
                        break
                for interaction in interactions_to_cancel:
                    interaction.cancel(FinishingType.INTERACTION_INCOMPATIBILITY, cancel_reason_msg='Canceled due to incompatibility with privacy instance.')

    def _route_sim_away(self, sim, liabilities=()):
        context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
        from interactions.utils.satisfy_constraint_interaction import BuildAndForceSatisfyShooConstraintInteraction
        result = sim.push_super_affordance(BuildAndForceSatisfyShooConstraintInteraction, None, context, liabilities=liabilities, privacy_inst=self, name_override='BuildShooFromPrivacy')
        if result:
            if self._post_route_affordance is not None:

                def route_away_callback(_):
                    post_route_context = context.clone_for_continuation(result.interaction)
                    sim.push_super_affordance(self._post_route_affordance, None, post_route_context)

                result.interaction.register_on_finishing_callback(route_away_callback)
        else:
            logger.debug('Failed to push BuildAndForceSatisfyShooConstraintInteraction on Sim {} to route them out of a privacy area.  Result: {}', sim, result, owner='tastle')
            if self.interaction is not None:
                self.interaction.cancel(FinishingType.TRANSITION_FAILURE, cancel_reason_msg='Failed to shoo Sims away.')
        return result

    def _cancel_pushed_interactions(self):
        for interaction in self._pushed_interactions:
            interaction.cancel(FinishingType.AUTO_EXIT, cancel_reason_msg='Privacy finished and is cleaning up.')
        self._pushed_interactions.clear()

    def handle_late_violator(self, sim):
        self._cancel_unavailable_interactions((sim,))
        self.add_override_for_sim(sim)
        liabilities = ((LATE_SHOO_LIABILITY, LateShooLiability(self, sim)),)
        result = self._route_sim_away(sim, liabilities=liabilities)
        if not result:
            return
        if not self._violators:
            context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.NEXT)
            if self.interaction is None:
                result = sim.push_super_affordance(self.embarrassed_affordance, sim, context)
            else:
                result = sim.push_super_affordance(self.embarrassed_affordance, self.interaction.get_participant(ParticipantType.Actor), context)
            if result or not services.sim_spawner_service().sim_is_leaving(sim):
                logger.warn('Failed to push the embarrassed affordance on Sim {}. Interaction {}. Result {}. Context {} ', sim, self.interaction, result, context, owner='tastle')
                return
        self._late_violators.add(sim)

    def add_override_for_sim(self, sim):
        for footprint in self._privacy_constraints:
            sim.routing_context.ignore_footprint_contour(footprint.footprint_id)

    def remove_override_for_sim(self, sim):
        for footprint in self._privacy_constraints:
            sim.routing_context.remove_footprint_contour_override(footprint.footprint_id)

    @property
    def allowed_sims(self):
        return self._allowed_sims

    @property
    def disallowed_sims(self):
        return self._disallowed_sims

    def remove_sim_from_allowed_disallowed(self, sim):
        if sim in self._allowed_sims:
            self._allowed_sims.remove(sim)
        if sim in self._disallowed_sims:
            self._disallowed_sims.remove(sim)

    @property
    def violators(self):
        return self._violators

    def remove_violator(self, sim):
        self.remove_override_for_sim(sim)
        self._violators.discard(sim)

    @property
    def late_violators(self):
        return self._late_violators

    def remove_late_violator(self, sim):
        self.remove_override_for_sim(sim)
        self._late_violators.discard(sim)

class TunablePrivacy(TunableFactory):
    FACTORY_TYPE = Privacy
    OPTIONAL_TUNABLE_DISABLED_NAME = 'Use_Default'

    @staticmethod
    def verify_tunable_callback(instance_class, tunable_name, source, *, additional_exit_offsets=None, max_line_of_sight_radius=None, **kwargs):
        if additional_exit_offsets:
            for offset in additional_exit_offsets:
                if offset.magnitude() < max_line_of_sight_radius:
                    logger.error('{} has a tuned additional exit offset {} that is within the max line of sight radius {}.', instance_class, offset, max_line_of_sight_radius)

    def __init__(self, description='Generate a privacy region for this object', callback=None, **kwargs):
        super().__init__(tests=TunableTestSet(description='\n                Any Sim who passes these tests will be allowed to violate the\n                privacy region.\n                '), shoo_exempt_tests=TunableTestSet(description='\n                Any violator who passes these tests will still be considered a\n                violator, but ill be exempt from being shooed.\n                i.e. A cat will get shooed when it breaks a privacy region, but\n                cats will ignore the shoo behavior.\n                '), max_line_of_sight_radius=Tunable(description='\n                The maximum possible distance from this object than an\n                interaction can reach.\n                ', tunable_type=float, default=5), map_divisions=Tunable(description='\n                The number of points around the object to check collision from.\n                More points means higher accuracy.\n                ', tunable_type=int, default=30), simplification_ratio=Tunable(description='\n                A factor determining how much to combine edges in the line of\n                sight polygon.\n                ', tunable_type=float, default=0.25), boundary_epsilon=Tunable(description='\n                The LOS origin is allowed to be outside of the boundary by this\n                amount.\n                ', tunable_type=float, default=0.01), facing_offset=Tunable(description='\n                The LOS origin is offset from the object origin by this amount\n                (mainly to avoid intersecting walls).\n                ', tunable_type=float, default=0.1), routing_surface_only=Tunable(description="\n                If this is checked, then the privacy constraint is generated on\n                the surface defined by the interaction's target. If the\n                interaction has no target or the target does not provide a\n                routable surface, no privacy is generated.\n                \n                Furthermore, privacy that is exclusive to routing surface will\n                only shoo Sims that are on the routable surface.\n                \n                e.g. A Sim cleaning a counter needs to shoo cats on the counter.\n                \n                The default behavior is for privacy to be generated on the\n                surface the Sim is on, and for it to apply to Sims on all\n                surfaces.\n                \n                e.g. A Sim using the toilet would shoo cats within the privacy\n                region that happen to be on routable surfaces, such as counters.\n                ", tunable_type=bool, default=False), shoo_constraint_radius=OptionalTunable(description='\n                If enabled, you can tune a specific radius for the shoo\n                constraint. If disabled, the values tuned in the Privacy module\n                tuning will be used.\n                ', tunable=Tunable(description='\n                    The radius of the constraint a Shooed Sim will attempt to\n                    route to.\n                    ', tunable_type=float, default=2.5), disabled_name=self.OPTIONAL_TUNABLE_DISABLED_NAME), unavailable_tooltip=OptionalTunable(description='\n                If enabled, allows a custom tool tip to be displayed when the\n                player tries to run an interaction on an object inside the\n                privacy region. If disabled, the values tuned in the Privacy\n                module tuning will be used.\n                ', tunable=TunableLocalizedStringFactory(description='\n                    Tool tip displayed when an object is not accessible due to\n                    being inside a privacy region.\n                    '), disabled_name=self.OPTIONAL_TUNABLE_DISABLED_NAME), embarrassed_affordance=OptionalTunable(description='\n                If enabled, a specific affordance can be tuned for a Sim to\n                play when walking into the privacy region. If disabled, the\n                values tuned in the Privacy module tuning will be used.\n                ', tunable=TunableReference(description='\n                    The affordance a Sim will play when getting embarrassed by\n                    walking in on a privacy situation.\n                    ', manager=services.get_instance_manager(Types.INTERACTION)), disabled_name=self.OPTIONAL_TUNABLE_DISABLED_NAME), post_route_affordance=OptionalTunable(description='\n                Optionally define an interaction that will run after the Sim\n                routes away.\n                ', tunable=TunableReference(description='\n                    The affordance a Sim will play when getting embarrassed by\n                    walking in on a privacy situation.\n                    ', manager=services.get_instance_manager(Types.INTERACTION))), privacy_cost_override=OptionalTunable(description='\n                If set, override the cost of the privacy region.\n                ', tunable=TunableRange(tunable_type=int, default=20, minimum=1), disabled_name=self.OPTIONAL_TUNABLE_DISABLED_NAME), additional_exit_offsets=TunableList(description="\n                If set, adds additional exit goals to add to the satisfy shoo\n                constraint.  For most cases this isn't needed, since most\n                privacy situations may kick a player out of a room through\n                a door and there are few exit options. \n                However for open-space privacy areas, default behavior\n                (using zone's corners) can cause a Sim to always attempt to exit \n                the privacy area in a consistent and often not optimal route, \n                (e.g. an open cross-shaped hall with 4 ways out, with default\n                behavior the Sim could consistently choose to exit using \n                the same route even though other routes would yield \n                a shorter distance out of the privacy region)\n                ", tunable=TunableVector2(default=TunableVector2.DEFAULT_ZERO)), reserved_surface_space=OptionalTunable(description='\n                If enabled privacy will generate an additional footprint around\n                the target object surface (if  routing_surface_only is enabled\n                then this will happen on the object routable surface). \n                This footprint will affect any Sim from routing through for the \n                duration of the interaction.\n                ', tunable=TunableTuple(description='\n                    Reserved space and blocking options for the created\n                    footprint.\n                    ', allow_routing=Tunable(description='\n                        If True, then the footprint will only discourage \n                        routing, instead of blocking the whole area from\n                        being used.\n                        ', tunable_type=bool, default=True), reserved_space=TunableReservedSpace(description='\n                        Defined space to generate the Jig that will block the \n                        routable surface space..\n                        ')), enabled_name='define_blocking_area'), vehicle_tests=OptionalTunable(description='\n                If enabled, vehicles that pass through this privacy region will\n                be tested to see if the vehicle is allowed in the privacy\n                region. Otherwise, the vehicle will always be affected by\n                privacy.\n                Note: The Object Routing Component specifies what happens when\n                the drone enters a privacy region.\n                ', tunable=TunableTestSet(description='\n                    The tests that the vehicle must pass to be allowed in the\n                    privacy region. \n                    Note: The Object Routing Component specifies what happens\n                    when the drone enters a privacy region.\n                    ')), verify_tunable_callback=TunablePrivacy.verify_tunable_callback, description=description, **kwargs)
(_, TunablePrivacySnippet) = snippets.define_snippet('Privacy', TunablePrivacy())SHOO_LIABILITY = 'ShooLiability'
class ShooLiability(Liability):

    def __init__(self, privacy, sim, **kwargs):
        super().__init__(**kwargs)
        self._privacy = privacy
        self._sim = sim

    def release(self):
        if self._privacy.is_active:
            if self._privacy.interaction is not None and self._sim in self._privacy.find_violating_sims():
                self._privacy.interaction.cancel(FinishingType.LIABILITY, cancel_reason_msg='Shoo. Failed to route away from privacy region.')
            else:
                self._privacy.remove_violator(self._sim)
LATE_SHOO_LIABILITY = 'LateShooLiability'
class LateShooLiability(Liability):

    def __init__(self, privacy, sim, **kwargs):
        super().__init__(**kwargs)
        self._privacy = privacy
        self._sim = sim

    def release(self):
        if self._privacy.is_active:
            if self._privacy.interaction is not None and self._sim in self._privacy.find_violating_sims():
                self._privacy.interaction.cancel(FinishingType.LIABILITY, cancel_reason_msg='Late Shoo. Failed to route away from privacy region.')
            else:
                self._privacy.remove_late_violator(self._sim)

    def on_reset(self):
        self.release()

    def transfer(self, interaction):
        if not self._privacy.is_active:
            interaction.cancel(FinishingType.LIABILITY, cancel_reason_msg='Late Shoo. Continuation canceled.')
