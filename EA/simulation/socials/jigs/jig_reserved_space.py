from sims.sim_info_types import Speciesfrom sims4.tuning.tunable import TunableMapping, TunableEnumEntry, TunableTuple, Tunable
class TunableReservedSpacePerSpecies(TunableMapping):

    def __init__(self, **kwargs):
        super().__init__(key_type=TunableEnumEntry(description='\n                Species these reserved spaces are intended for.\n                ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), value_type=TunableReservedSpace(), **kwargs)

class TunableReservedSpace(TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(front=Tunable(description='\n                Space to be reserved in front of the actor.\n                ', tunable_type=float, default=1.0), back=Tunable(description='\n                Space to be reserved in back of the actor.\n                ', tunable_type=float, default=1.0), left=Tunable(description='\n                Space to be reserved to the left of the actor.\n                ', tunable_type=float, default=1.0), right=Tunable(description='\n                Space to be reserved to the right of the actor.\n                ', tunable_type=float, default=1.0), **kwargs)
