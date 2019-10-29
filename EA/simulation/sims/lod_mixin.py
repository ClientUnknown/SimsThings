from sims.sim_info_lod import SimInfoLODLevelfrom sims4.tuning.tunable import TunableEnumEntry
class HasTunableLodMixin:
    INSTANCE_TUNABLES = {'min_lod_value': TunableEnumEntry(description='\n            The minimum Sim info LOD necessary for this information to persist\n            on the sim info. e.g. A statistic tuned to FULL will not persist on\n            sims that are BASE or lower.\n            ', tunable_type=SimInfoLODLevel, default=SimInfoLODLevel.BASE, invalid_enums=(SimInfoLODLevel.ACTIVE,))}
