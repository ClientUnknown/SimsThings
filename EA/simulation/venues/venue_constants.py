from sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import TunableReferenceimport enumimport servicesimport sims4.resources
class ZoneDirectorRequestType(enum.Int, export=False):
    CAREER_EVENT = ...
    GO_DANCING = ...
    DRAMA_SCHEDULER = ...
    AMBIENT_VENUE = ...

class NPCSummoningPurpose(DynamicEnum):
    DEFAULT = 0
    PLAYER_BECOMES_GREETED = 1
    BRING_PLAYER_SIM_TO_LOT = 2
    ZONE_FIXUP = 3

class VenueTuning:
    RESIDENTIAL_VENUE_TYPE = TunableReference(description='\n        The residential venue type.\n        ', manager=services.get_instance_manager(sims4.resources.Types.VENUE))
