from _sims4_collections import frozendictfrom postures.posture_specs import PostureOperationfrom sims.sim_info_types import Speciesfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, Tunable, TunableVariant, TunableMapping, TunableEnumEntry
class _PostureCost(HasTunableSingletonFactory, AutoFactoryInit):

    def _create_costs(self, default_cost, costs=()):
        costs = dict(costs)
        costs[PostureOperation.DEFAULT_COST_KEY] = default_cost
        return frozendict(costs)

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self):
        return hash(self.__dict__)

class _PostureCostDefault(_PostureCost):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.costs_none = self._create_costs(0)
        self.costs_standard = self._create_costs(PostureOperation.COST_STANDARD)

    def get_cost(self, source_posture, destination_posture):
        if source_posture is destination_posture:
            return self.costs_none
        return self.costs_standard

class _PostureCostCustom(_PostureCost):
    FACTORY_TUNABLES = {'cost': Tunable(description='\n            The cost to transition between the two postures.\n            ', tunable_type=float, default=1)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.costs = self._create_costs(self.cost)

    def get_cost(self, source_posture, destination_posture):
        return self.costs

class _PostureCostSpecies(_PostureCost):
    FACTORY_TUNABLES = {'default_cost': Tunable(description='\n            The cost to transition between the two postures for a species\n            without any specific tuning.\n            ', tunable_type=float, default=1), 'species_cost': TunableMapping(description='\n            For each species, define the cost to transition between the two\n            postures.\n            ', key_type=TunableEnumEntry(description='\n                The species this cost applies to.\n                ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), value_type=Tunable(description='\n                For this species, the cost to transition between the two\n                postures.\n                ', tunable_type=float, default=1))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.costs = self._create_costs(self.default_cost, self.species_cost)

    def get_cost(self, source_posture, destination_posture):
        return self.costs

class TunablePostureCostVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, default_cost=_PostureCostDefault.TunableFactory(), custom_cost=_PostureCostCustom.TunableFactory(), per_species_cost=_PostureCostSpecies.TunableFactory(), default='default_cost', **kwargs)
