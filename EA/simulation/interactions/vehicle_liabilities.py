from interactions import ParticipantTypeObject, ParticipantType, ParticipantTypeSinglefrom interactions.aop import AffordanceObjectPairfrom interactions.base.interaction_constants import InteractionQueuePreparationStatusfrom interactions.constraint_variants import TunableGeometricConstraintVariantfrom interactions.constraints import Circle, Position, Nowhere, ANYWHEREfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.interaction_finisher import FinishingTypefrom interactions.liability import PreparationLiabilityfrom interactions.priority import Priorityfrom interactions.utils.object_definition_or_tags import ObjectDefinitonsOrTagsVariantfrom interactions.utils.routing import PlanRoutefrom sims4.tuning.tunable import TunableEnumEntry, TunableVariant, AutoFactoryInit, HasTunableSingletonFactory, OptionalTunable, HasTunableFactory, Tunable, TunableReference, TunablePackSafeReference, TunableTuplefrom singletons import DEFAULTfrom vehicles.vehicle_constants import VehicleTransitionStateimport element_utilsimport routingimport servicesimport sims4.loglogger = sims4.log.Logger('Vehicles', default_owner='rmccord')
class FindVehicleVariant(TunableVariant):

    class VehicleFromParticipant(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'vehicle_participant': TunableEnumEntry(description='\n                The participant to use as the vehicle.\n                ', tunable_type=ParticipantTypeObject, default=ParticipantTypeObject.Object)}

        def __call__(self, resolver):
            vehicle = resolver.get_participant(self.vehicle_participant)
            if vehicle is not None and vehicle.vehicle_component is None:
                logger.error('{} has no vehicle component. {}', vehicle, resolver)
                return
            return vehicle

    class VehicleFromInventory(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'obj_filter': OptionalTunable(description="\n                If enabled, we will use this filter on vehicles in the Actor\n                Sim's inventory.\n                ", tunable=ObjectDefinitonsOrTagsVariant(description="\n                    The filter we want to use on the vehicles in the actor's\n                    inventory.\n                    "))}

        def __call__(self, resolver):
            sim = resolver.get_participant(ParticipantType.Actor)
            if sim.is_sim:
                sim = sim.sim_info.get_sim_instance()
            if sim is not None and sim is not None:
                for vehicle in sim.inventory_component.vehicle_objects_gen():
                    if not self.obj_filter is None:
                        if self.obj_filter.matches(vehicle):
                            return vehicle
                    return vehicle

    def __init__(self, *args, **kwargs):
        super().__init__(*args, from_participant=FindVehicleVariant.VehicleFromParticipant.TunableFactory(), from_inventory=FindVehicleVariant.VehicleFromInventory.TunableFactory(), **kwargs)

class VehicleLiability(HasTunableFactory, AutoFactoryInit, PreparationLiability):
    LIABILITY_TOKEN = 'VehicleLiability'
    SOURCE_CONNECTIVITY_HANDLE_RADIUS = 10.0
    GET_CLOSE_AFFORDANCE = TunableReference(description='\n        The affordance that Vehicle Liabilities use to get close to the\n        deployment area. Can be overridden on the liability.\n        ', manager=services.affordance_manager())
    FACTORY_TUNABLES = {'vehicle': FindVehicleVariant(), 'transfer_to_continuations': Tunable(description='\n            If enabled, we will transfer this liability to continuations and\n            ensure that the Sim attempts to re-deploy their vehicle.\n            ', tunable_type=bool, default=False), 'get_close_affordance': OptionalTunable(description='\n            If enabled, we will override the default get close affordance for\n            vehicle liabilities. This affordance is pushed to get close to the\n            deployment zone.\n            ', tunable=TunablePackSafeReference(description='\n                The affordance we want to push to get close to the deployment\n                zone. We will be passing constraints to satisfy to this\n                affordance.\n                ', manager=services.affordance_manager()), enabled_name='override', disabled_name='default_affordance'), 'deploy_constraints': OptionalTunable(description="\n            If enabled, we will use this set of constraints to find out where\n            the Sim actually intends on going to use their vehicle. Without\n            this we don't really know where they want to deploy it.\n            \n            We can't use the interaction constraints because that's most likely\n            not where the sim will want to be.\n            ", tunable=TunableTuple(description='\n                An object and constraints to generate relative to it.\n                ', constraints=TunableGeometricConstraintVariant(description='\n                    The constraint we want to use to get close to our deployment zone.\n                    \n                    Note: This is NOT where the Sim will be when they run the\n                    interaction. We need to get them to deploy the vehicle before the\n                    interaction actually runs. This constraint gives us an idea of\n                    where to look.\n                    ', disabled_constraints=('spawn_points',)), target=TunableEnumEntry(description='\n                    The object we want to generate the deploy constraint\n                    relative to.\n                    ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object))), 'max_vehicle_state': TunableEnumEntry(description='\n            The maximum progress we want to make on riding our vehicle.\n            ', tunable_type=VehicleTransitionState, default=VehicleTransitionState.DEPLOYING, invalid_enums=(VehicleTransitionState.NO_STATE,))}

    def __init__(self, interaction, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._vehicle_transition_state = VehicleTransitionState.NO_STATE
        self._vehicle = None
        self._interaction = interaction
        self._deploy_constraint = None

    def should_transfer(self, _):
        return self.transfer_to_continuations

    def on_add(self, interaction):
        super().on_add(interaction)
        resolver = interaction.get_resolver()
        vehicle = self.vehicle(resolver)
        if vehicle is None:
            logger.warn("Attempting to deploy a vehicle that we don't have. {}", interaction)
            return
        self._vehicle = vehicle

    def _get_deployment_constraint(self):
        if self._deploy_constraint is not None and self._deploy_constraint.valid:
            return self._deploy_constraint
        sim = self._interaction.sim
        deploy_constraints = self.deploy_constraints
        if deploy_constraints is not None:
            constraint_target = self._interaction.get_participant(deploy_constraints.target)
            self._deploy_constraint = ANYWHERE
            self._deploy_constraint = self._deploy_constraint.intersect(deploy_constraints.constraints.create_constraint(sim, target=constraint_target, target_position=constraint_target.position if constraint_target is not None else DEFAULT))
            return self._deploy_constraint
        target = self._interaction.target
        constraint = self._interaction.constraint_intersection(sim, target, participant_type=ParticipantType.Actor, posture_state=None)
        constraint = constraint.generate_geometry_only_constraint()
        return constraint

    def _get_close_to_deploy(self, timeline, vehicle):
        sim = self._interaction.sim
        constraint = self._get_deployment_constraint()
        if not constraint.valid:
            return InteractionQueuePreparationStatus.FAILURE
        handles = constraint.get_connectivity_handles(sim)
        goals = []
        for handle in handles:
            goals.extend(handle.get_goals(single_goal_only=True))
        if not goals:
            return InteractionQueuePreparationStatus.FAILURE
        if sim.posture.unconstrained:
            source_constraint = Position(sim.position, routing_surface=sim.routing_surface)
        else:
            source_constraint = Circle(sim.position, self.SOURCE_CONNECTIVITY_HANDLE_RADIUS, sim.routing_surface)
        source_handles = source_constraint.get_connectivity_handles(sim)
        if not source_handles:
            return InteractionQueuePreparationStatus.FAILURE
        source_goals = source_handles[0].get_goals(single_goal_only=True)
        if not source_goals:
            return InteractionQueuePreparationStatus.FAILURE
        source_goal = source_goals[0]
        route = routing.Route(source_goal.location, goals, routing_context=sim.routing_context)
        plan_primitive = PlanRoute(route, sim, interaction=self._interaction)
        result = yield from element_utils.run_child(timeline, plan_primitive)
        if result or plan_primitive.path.nodes or not plan_primitive.path.nodes.plan_success:
            return InteractionQueuePreparationStatus.FAILURE
        cur_path = plan_primitive.path
        has_portal = False
        while cur_path.next_path is not None:
            has_portal = True
            cur_path = cur_path.next_path
        if not cur_path.nodes:
            return InteractionQueuePreparationStatus.FAILURE
        start_location = cur_path.start_location
        if has_portal or (start_location.position - source_goal.location.position).magnitude_squared() < vehicle.vehicle_component.minimum_route_distance:
            return InteractionQueuePreparationStatus.SUCCESS
        deploy_constraint = Position(start_location.position, routing_surface=start_location.routing_surface)
        depended_on_si = self._interaction
        affordance = self.get_close_affordance if self.get_close_affordance is not None else VehicleLiability.GET_CLOSE_AFFORDANCE
        aop = AffordanceObjectPair(affordance, None, affordance, None, route_fail_on_transition_fail=False, constraint_to_satisfy=deploy_constraint, allow_posture_changes=True, depended_on_si=depended_on_si)
        context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.FIRST, must_run_next=True, group_id=depended_on_si.group_id)
        if not aop.test_and_execute(context):
            return InteractionQueuePreparationStatus.FAILURE
        return InteractionQueuePreparationStatus.NEEDS_DERAIL

    def _prepare_gen(self, timeline, *args, **kwargs):
        if self._vehicle is None:
            return InteractionQueuePreparationStatus.FAILURE
        sim = self._interaction.sim
        vehicle_component = self._vehicle.vehicle_component
        if self._vehicle_transition_state == VehicleTransitionState.NO_STATE:
            path_result = yield from self._get_close_to_deploy(timeline, self._vehicle)
            if path_result != InteractionQueuePreparationStatus.SUCCESS:
                return path_result
            result = vehicle_component.push_deploy_vehicle_affordance(sim, depend_on_si=self._interaction)
            if not result:
                self._interaction.cancel(FinishingType.TRANSITION_FAILURE, cancel_reason_msg='Failed to Deploy Vehicle')
                return InteractionQueuePreparationStatus.FAILURE
            self._vehicle_transition_state = VehicleTransitionState.DEPLOYING
            return InteractionQueuePreparationStatus.NEEDS_DERAIL
        elif self._vehicle_transition_state == VehicleTransitionState.DEPLOYING and self.max_vehicle_state == VehicleTransitionState.MOUNTING:
            result = vehicle_component.push_drive_affordance(sim)
            if not result:
                self._interaction.cancel(FinishingType.TRANSITION_FAILURE, cancel_reason_msg='Failed to Drive Vehicle')
                return InteractionQueuePreparationStatus.FAILURE
            self._vehicle_transition_state = VehicleTransitionState.MOUNTING
            return InteractionQueuePreparationStatus.NEEDS_DERAIL
        return InteractionQueuePreparationStatus.SUCCESS
