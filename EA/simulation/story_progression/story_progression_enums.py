from collections import namedtupleCullImmunityInfo = namedtuple('CullImmunityInfo', ('telemetry_hook', 'gsi_reason'))
class CullingReasons:
    PLAYER = CullImmunityInfo('imsp', 'Player SimInfo')
    LIVES_IN_WORLD = CullImmunityInfo('imsw', 'Resident of some world')
    TRAIT_IMMUNE = CullImmunityInfo('imsa', 'Possess an immune trait')
    INSTANCED = CullImmunityInfo('imsn', 'Instanced in the game')
    IN_TRAVEL_GROUP = CullImmunityInfo('imst', 'Part of some travel group')
    ALL_CULLING_REASONS = [PLAYER, LIVES_IN_WORLD, TRAIT_IMMUNE, INSTANCED, IN_TRAVEL_GROUP]
