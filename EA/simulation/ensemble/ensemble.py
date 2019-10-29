from _collections import defaultdictfrom _weakrefset import WeakSetfrom math import sqrtfrom caches import cachedfrom distributor.ops import EndEnsemble, StartEnsemble, UpdateEnsemblefrom distributor.system import Distributorfrom ensemble.ensemble_interactions import EnsembleConstraintProxyInteractionfrom event_testing.resolver import SingleSimResolverfrom interactions.constraints import Circle, ANYWHEREfrom sims import sim_info_utilsfrom sims.sim_info_types import Speciesfrom sims4.tuning.geometric import TunableDistanceSquaredfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import TunableRange, Tunable, TunableList, TunableReference, OptionalTunable, TunableSet, TunableEnumEntryfrom tunable_multiplier import TunableMultiplierimport id_generatorimport routingimport servicesimport sims4.mathlogger = sims4.log.Logger('Ensembles')
class Ensemble(metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.ENSEMBLE)):
    ENSEMBLE_PRIORITIES = TunableList(description='\n        A list of ensembles by priority.  Those with higher guids will be\n        considered more important than those with lower guids.\n        \n        IMPORTANT: All ensemble types must be referenced in this list.\n        ', tunable=TunableReference(description='\n            A single ensemble.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ENSEMBLE), pack_safe=True))

    @staticmethod
    def get_ensemble_priority(ensemble_type):
        index = 0
        for ensemble in Ensemble.ENSEMBLE_PRIORITIES:
            if ensemble is ensemble_type:
                return index
            index += 1
        logger.error('Ensemble of type {} not found in Ensemble Priorities.  Please add the ensemble to ensemble.ensemble.', ensemble_type)

    INSTANCE_TUNABLES = {'max_ensemble_radius': TunableDistanceSquared(description="\n            The maximum distance away from the center of mass that Sims will\n            receive an autonomy bonus for.\n            \n            If Sims are beyond this distance from the ensemble's center of mass,\n            then they will autonomously consider to run any interaction from\n            ensemble_autonomous_interactions.\n            \n            Any such interaction will have an additional constraint that is a\n            circle whose radius is this value.\n            ", default=1.0), 'ensemble_autonomy_bonus_multiplier': TunableRange(description='\n            The autonomy multiplier that will be applied for objects within the\n            autonomy center of mass.\n            ', tunable_type=float, default=2.0, minimum=1.0), 'ensemble_autonomous_interactions': TunableSet(description="\n            This is a set of self interactions that are generated for Sims part \n            of this ensemble.\n            \n            The interactions don't target anything and have an additional\n            constraint equivalent to the circle defined by the ensemble's center\n            of mass and radius.\n            ", tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True)), 'visible': Tunable(description='\n            If this ensemble is visible and displays to the UI.\n            ', tunable_type=bool, default=True), 'rally': Tunable(description='\n            If this is True then this ensemble will offer rallying behavior.\n            ', tunable_type=bool, default=True), 'center_of_mass_multiplier': TunableMultiplier.TunableFactory(description="\n            Define multipliers that control the weight that a Sim has when\n            determining the ensemble's center of mass.\n            "), 'max_limit': OptionalTunable(description='\n            If enabled this ensemble will have a maximum number of Sims that\n            can be a part of it.\n            ', tunable=TunableRange(description='\n                The maximum number of Sims that can be in this ensemble.\n                ', tunable_type=int, default=8, minimum=2)), 'prohibited_species': TunableSet(description='\n            A set of species that cannot be added to this type of ensemble.\n            ', tunable=TunableEnumEntry(description='\n                A species that cannot be added to this type of ensemble.\n                ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)))}

    def __init__(self):
        self._guid = None
        self._sims = WeakSet()

    def __iter__(self):
        yield from self._sims

    def __len__(self):
        return len(self._sims)

    @property
    def guid(self):
        return self._guid

    @classmethod
    def can_add_sim_to_ensemble(cls, sim):
        if sim.species in cls.prohibited_species:
            return False
        return True

    def add_sim_to_ensemble(self, sim):
        if sim in self._sims:
            return
        self._sims.add(sim)
        if self.ensemble_autonomous_interactions:
            sim_info_utils.apply_super_affordance_commodity_flags(sim, self, self.ensemble_autonomous_interactions)
        if self.visible:
            op = UpdateEnsemble(self._guid, sim.id, True)
            Distributor.instance().add_op_with_no_owner(op)

    def remove_sim_from_ensemble(self, sim):
        self._sims.remove(sim)
        if self.ensemble_autonomous_interactions:
            sim_info_utils.remove_super_affordance_commodity_flags(sim, self)
        if self.visible:
            op = UpdateEnsemble(self._guid, sim.id, False)
            Distributor.instance().add_op_with_no_owner(op)

    def is_sim_in_ensemble(self, sim):
        return sim in self._sims

    def start_ensemble(self):
        self._guid = id_generator.generate_object_id()
        if self.visible:
            op = StartEnsemble(self._guid)
            Distributor.instance().add_op_with_no_owner(op)

    def end_ensemble(self):
        if self.ensemble_autonomous_interactions:
            for sim in self._sims:
                sim_info_utils.remove_super_affordance_commodity_flags(sim, self)
        self._sims.clear()
        if self.visible:
            op = EndEnsemble(self._guid)
            Distributor.instance().add_op_with_no_owner(op)

    @cached
    def _get_sim_weight(self, sim):
        return self.center_of_mass_multiplier.get_multiplier(SingleSimResolver(sim.sim_info))

    @cached
    def calculate_level_and_center_of_mass(self):
        sims_per_level = defaultdict(list)
        for sim in self._sims:
            sims_per_level[sim.level].append(sim)
        best_level = max(sims_per_level, key=lambda level: (len(sims_per_level[level]), -level))
        best_sims = sims_per_level[best_level]
        center_of_mass = sum((sim.position*self._get_sim_weight(sim) for sim in best_sims), sims4.math.Vector3.ZERO())/sum(self._get_sim_weight(sim) for sim in best_sims)
        return (best_level, center_of_mass)

    def is_within_ensemble_radius(self, obj):
        (level, center_of_mass) = self.calculate_level_and_center_of_mass()
        if obj.level != level:
            return False
        else:
            distance = (obj.position - center_of_mass).magnitude_squared()
            if distance > self.max_ensemble_radius:
                return False
        return True

    @cached
    def get_ensemble_multiplier(self, target):
        if self.is_within_ensemble_radius(target):
            return self.ensemble_autonomy_bonus_multiplier
        return 1

    def get_center_of_mass_constraint(self):
        if not self:
            logger.warn('No Sims in ensemble when trying to construct constraint.')
            return ANYWHERE
        (level, position) = self.calculate_level_and_center_of_mass()
        routing_surface = routing.SurfaceIdentifier(services.current_zone_id(), level, routing.SurfaceType.SURFACETYPE_WORLD)
        return Circle(position, sqrt(self.max_ensemble_radius), routing_surface)

    def get_ensemble_autonomous_interactions_gen(self, context, **interaction_parameters):
        if self.is_within_ensemble_radius(context.sim):
            return
        for ensemble_affordance in self.ensemble_autonomous_interactions:
            affordance = EnsembleConstraintProxyInteraction.generate(ensemble_affordance, self)
            yield from affordance.potential_interactions(context.sim, context, **interaction_parameters)
