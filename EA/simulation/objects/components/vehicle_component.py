import weakreffrom animation.posture_manifest import PostureManifest, AnimationParticipant, SlotManifest, MATCH_ANY, PostureManifestEntryfrom interactions.aop import AffordanceObjectPairfrom interactions.constraints import Circle, Constraintfrom interactions.context import InteractionContext, QueueInsertStrategyfrom interactions.priority import Priorityfrom objects.components import Component, typesfrom objects.components.utils.footprint_toggle_mixin import FootprintToggleMixinfrom postures.posture_specs import PostureSpecVariablefrom postures.posture_state_spec import PostureStateSpecfrom routing import SurfaceTypefrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, Tunable, TunableEnumSet, TunableReference, TunableTuple, OptionalTunableimport interactions.utilsimport servicesimport sims4.loglogger = sims4.log.Logger('Vehicles', default_owner='rmccord')
class VehicleComponent(FootprintToggleMixin, Component, HasTunableFactory, AutoFactoryInit, component_name=types.VEHICLE_COMPONENT):
    FACTORY_TUNABLES = {'minimum_route_distance': Tunable(description="\n            The minimum distance we require for this vehicle to route. This is\n            also the distance threshold for when the vehicle delays it's\n            dismount. If the Sim attempts to get off of the vehicle to go\n            somewhere, they will defer that dismount and get closer to their\n            destination first.\n            ", tunable_type=float, default=3.0), 'ideal_route_radius': Tunable(description='\n            This is the tuning for the ideal radius used when trying to get\n            close to the destination if the destination is farther away than\n            the minimum_route_distance.\n            ', tunable_type=float, default=3.0), 'allowed_surfaces': TunableEnumSet(description='\n            The allowed surfaces for this vehicle. This is how we determine we\n            should use a vehicle in our inventory to get somewhere faster and\n            when we can do it.\n            \n            Also helps us dismount vehicles before we transition through\n            portals.\n            ', enum_type=SurfaceType, enum_default=SurfaceType.SURFACETYPE_WORLD, invalid_enums=(SurfaceType.SURFACETYPE_UNKNOWN,)), 'deploy_tuning': OptionalTunable(description=',\n            If enabled, a Sim may deploy this vehicle from their inventory.\n            ', tunable=TunableTuple(description='\n                Tuning for deploying this vehicle.\n                ', deploy_affordance=OptionalTunable(description='\n                    If enabled, we will override the deployment affordance to\n                    use something specific when deploying vehicles for speed.\n                    Otherwise we simply refer to the inventory item component\n                    affordances.\n                    ', tunable=TunableReference(description='\n                        The affordance a Sim will use to deploy the vehicle from\n                        inventory and drive it.\n                        ', manager=services.affordance_manager()), disabled_name='use_inventory_item_component_affordance', enabled_name='override'))), 'drive_affordance': TunableReference(description='\n            The affordance a Sim will use to drive this vehicle.\n            ', manager=services.affordance_manager()), 'retrieve_tuning': OptionalTunable(description='\n            If enabled, the Sim may attempt to retrieve this vehicle for their\n            inventory.\n            ', tunable=TunableTuple(description='\n                Tuning for retrieving this vehicle.\n                ', retrieve_affordance=OptionalTunable(description='\n                    If enabled, we will override the retrieval affordance to\n                    use something specific when retrieving vehicles after\n                    dismount. Otherwise, we simply refer to the inventory item\n                    component affordances.\n                    ', tunable=TunableReference(description='\n                        The affordance a Sim will use to deploy the vehicle from\n                        inventory and drive it.\n                        ', manager=services.affordance_manager()), disabled_name='use_inventory_item_component_affordance', enabled_name='override')))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._driver = None

    @property
    def driver(self):
        if self._driver is None:
            return
        return self._driver()

    def on_add(self):
        self.register_routing_event_callbacks()

    def on_remove(self):
        self.unregister_routing_event_callbacks()

    def _check_update_driver(self, child):
        self._driver = weakref.ref(child)

    def on_child_added(self, child, _):
        if self.driver is not None or not child.is_sim:
            return
        self._check_update_driver(child)

    def on_child_removed(self, child, new_parent=None):
        if child is self.driver:
            self._driver = None
        if new_parent is not None:
            self._check_update_driver(child)

    def on_added_to_inventory(self):
        owner_inventory = self.owner.get_inventory()
        if owner_inventory.owner.is_sim:
            owner_inventory.add_vehicle_object(self.owner)

    def on_removed_from_inventory(self):
        owner = self.owner.inventoryitem_component.last_inventory_owner
        if owner.is_sim:
            owner.inventory_component.remove_vehicle_object(self.owner)

    def push_drive_affordance(self, sim, depend_on_si=None):
        return self._push_affordance(sim, self.drive_affordance, self.owner, depend_on_si=depend_on_si)

    def _create_drive_posture_constraint(self, posture_type):
        posture_manifest = PostureManifest()
        entry = PostureManifestEntry(AnimationParticipant.ACTOR, posture_type.name, posture_type.family_name, MATCH_ANY, MATCH_ANY, MATCH_ANY, MATCH_ANY, None)
        posture_manifest.add(entry)
        posture_manifest = posture_manifest.intern()
        posture_state_spec = PostureStateSpec(posture_manifest, SlotManifest(), PostureSpecVariable.ANYTHING)
        return Constraint(posture_state_spec=posture_state_spec, debug_name='VehiclePostureConstraint')

    def push_dismount_affordance(self, sim, final_position, depend_on_si=None):
        if sim.posture.is_vehicle:
            posture_constraint = sim.posture_state.posture_constraint
        else:
            posture_constraint = self._create_drive_posture_constraint(self.drive_affordance.provided_posture_type)
        circle_constraint = Circle(final_position, self.minimum_route_distance*0.9, sim.routing_surface, ideal_radius=self.ideal_route_radius)
        constraint = circle_constraint.intersect(posture_constraint)
        return self._push_affordance(sim, interactions.utils.satisfy_constraint_interaction.SatisfyConstraintSuperInteraction, None, depend_on_si=depend_on_si, constraint_to_satisfy=constraint, name_override='DismountVehicle')

    def push_retrieve_vehicle_affordance(self, sim, depend_on_si=None):
        affordance = self.retrieve_tuning.retrieve_affordance or next(self.owner.inventoryitem_component.place_in_inventory_affordances_gen(), None)
        if affordance is None:
            return affordance
        return self._push_affordance(sim, affordance, self.owner, depend_on_si=depend_on_si)

    def push_deploy_vehicle_affordance(self, sim, depend_on_si=None):
        if self.deploy_tuning is not None:
            pass
        affordance = next(self.owner.inventoryitem_component.place_in_world_affordances_gen(), None)
        if affordance is None:
            return
        return self._push_affordance(sim, affordance, self.owner, depend_on_si=depend_on_si)

    def _push_affordance(self, sim, affordance, target, depend_on_si=None, constraint_to_satisfy=None, name_override=None):
        aop = AffordanceObjectPair(affordance, target, affordance, None, route_fail_on_transition_fail=False, name_override=name_override, constraint_to_satisfy=constraint_to_satisfy, allow_posture_changes=True, depended_on_si=depend_on_si)
        context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, Priority.High, insert_strategy=QueueInsertStrategy.FIRST, must_run_next=True, group_id=depend_on_si.group_id if depend_on_si is not None else None)
        return aop.test_and_execute(context)
