from _sims4_collections import frozendictfrom interactions.constraints import TunableFacing, TunableLineOfSight, TunableCone, TunableCircle, TunableSpawnPoint, RelativeCircleConstraint, CurrentPosition, TunablePosition, PostureConstraintFactory, TunableWelcomeConstraint, TunableFrontDoorConstraint, JigConstraint, ObjectPlacementConstraint, TunableFireOrLotFacingConstraint, create_constraint_set, WaterDepthConstraint, TerrainMaterialConstraint, WaterDepthIntervalConstraint, TunableOceanStartLocationConstraint, PortalConstraintfrom interactions.utils.animation_reference import TunableAnimationConstraint, TunableRoutingSlotConstraintfrom plex.plex_constraint import PlexConstraintfrom sims4.tuning.tunable import TunableVariant, TunableList, HasTunableSingletonFactory, AutoFactoryInit, TunableFactoryimport sims4.math
class TunableGeometricConstraintVariant(TunableVariant):

    def __init__(self, constraint_locked_args=frozendict(), circle_locked_args=frozendict(), disabled_constraints=(), default='circle', **kwargs):
        if not circle_locked_args:
            circle_locked_args = constraint_locked_args
        else:
            circle_locked_args.update(constraint_locked_args)
        available_constraints = {'facing': TunableFacing(description='\n                Existential tunable that requires the sim to face the object.\n                '), 'line_of_sight': TunableLineOfSight(description='\n                Existential tunable that creates a line of sight constraint.\n                ', locked_args=constraint_locked_args), 'cone': TunableCone(description='\n                The relative cone geometry required for a sim/posture to use the object.\n                ', min_radius=0, max_radius=1, angle=sims4.math.PI, locked_args=constraint_locked_args), 'circle': TunableCircle(description='\n                The relative circle geometry required for a sim/posture to use the object.', radius=1, locked_args=circle_locked_args), 'spawn_points': TunableSpawnPoint(description='\n                A constraint that represents all of the spawn locations on the lot.\n                '), 'relative_circle': RelativeCircleConstraint.TunableFactory(locked_args=constraint_locked_args), 'current_position': CurrentPosition.TunableFactory(), 'portal': PortalConstraint.TunableFactory(), 'position': TunablePosition(description='\n                The relative position geometry required for a sim/posture to use the object.\n                ', relative_position=sims4.math.Vector3(0, 0, 0)), 'water_depth': WaterDepthConstraint.TunableFactory(), 'water_depth_interval': WaterDepthIntervalConstraint.TunableFactory(), 'terrain_material': TerrainMaterialConstraint.TunableFactory(), 'ocean_loc': TunableOceanStartLocationConstraint(description='\n                The circle geometry relative to the nearest ocean locator.', radius=1, locked_args=circle_locked_args), 'default': default}
        for disabled_name in disabled_constraints:
            if disabled_name in available_constraints:
                del available_constraints[disabled_name]
        kwargs.update(available_constraints)
        super().__init__(**kwargs)

class TunedConstraintSet(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {}

    @TunableFactory.factory_option
    def constraints_override(disabled_constraints, default):
        return {'constraints': TunableList(description='\n                A set of constraints, of which one must be valid for this set\n                to be valid.\n                ', minlength=1, tunable=TunableGeometricConstraintVariant(disabled_constraints=disabled_constraints, default=default))}

    def create_constraint(self, sim, target=None, **kwargs):
        constraint_list = map(lambda c: c.create_constraint(sim, target=target, **kwargs), self.constraints)
        return create_constraint_set(constraint_list)

class TunableConstraintVariant(TunableGeometricConstraintVariant):

    def __init__(self, disabled_constraints=frozenset(), default='circle', **kwargs):
        super().__init__(posture=PostureConstraintFactory.TunableFactory(), welcome=TunableWelcomeConstraint(description='\n                A constraint that requires the sim be at the object with the highest scoring Welcome Component\n                ', radius=1), front_door=TunableFrontDoorConstraint(), jig=JigConstraint.TunableFactory(), animation=TunableAnimationConstraint(), routing_slot=TunableRoutingSlotConstraint(), object_placement=ObjectPlacementConstraint.TunableFactory(), fire_or_lot_facing=TunableFireOrLotFacingConstraint(), plex=PlexConstraint.TunableFactory(), constraint_set=TunedConstraintSet.TunableFactory(constraints_override=(disabled_constraints, default)), disabled_constraints=disabled_constraints, default=default, **kwargs)
