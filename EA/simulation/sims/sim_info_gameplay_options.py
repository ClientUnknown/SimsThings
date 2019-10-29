from _sims4_collections import frozendictfrom sims4.common import Pack, is_available_packimport enum
class SimInfoGameplayOptions(enum.IntFlags):
    ALLOW_FAME = 1
    ALLOW_REPUTATION = 2
    FORCE_CURRENT_ALLOW_FAME_SETTING = 4
    FREEZE_FAME = 8
REQUIRED_PACK_BY_OPTION = frozendict({SimInfoGameplayOptions.FREEZE_FAME: Pack.EP06, SimInfoGameplayOptions.FORCE_CURRENT_ALLOW_FAME_SETTING: Pack.EP06, SimInfoGameplayOptions.ALLOW_REPUTATION: Pack.EP06, SimInfoGameplayOptions.ALLOW_FAME: Pack.EP06})
def is_required_pack_installed(sim_info_gameplay_option):
    pack = REQUIRED_PACK_BY_OPTION.get(sim_info_gameplay_option, None)
    if pack is None:
        return True
    return is_available_pack(pack)
