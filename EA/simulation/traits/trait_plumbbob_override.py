from sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableEnumEntryfrom sims4.tuning.tunable_hash import TunableStringHash64
class PlumbbobOverridePriority(DynamicEnum):
    INVALID = 0

class PlumbbobOverrideRequest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'active_sim_plumbbob': TunableStringHash64(description='\n            The plumbbob model to use when this is the active sim,\n            '), 'active_sim_club_leader_plumbbob': TunableStringHash64(description="\n            The plumbbob model to use when this is the active sim and they're\n            the leader of the club.\n            "), 'priority': TunableEnumEntry(description='\n            The requests priority.\n            ', tunable_type=PlumbbobOverridePriority, default=PlumbbobOverridePriority.INVALID, invalid_enums={PlumbbobOverridePriority.INVALID})}
