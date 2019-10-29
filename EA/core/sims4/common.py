import _common_typesimport enum
class Pack(enum.Int):
    try:
        BASE_GAME = _common_types.BASE_GAME
        SP01 = _common_types.SP01
        GP01 = _common_types.GP01
        EP01 = _common_types.EP01
        FP01 = _common_types.FP01
        SP02 = _common_types.SP02
        GP02 = _common_types.GP02
        SP03 = _common_types.SP03
        SP04 = _common_types.SP04
        EP02 = _common_types.EP02
        GP03 = _common_types.GP03
        SP05 = _common_types.SP05
        SP06 = _common_types.SP06
        SP07 = _common_types.SP07
        SP08 = _common_types.SP08
        SP09 = _common_types.SP09
        SP10 = _common_types.SP10
        GP04 = _common_types.GP04
        GP05 = _common_types.GP05
        GP06 = _common_types.GP06
        GP07 = _common_types.GP07
        GP08 = _common_types.GP08
        GP09 = _common_types.GP09
        GP10 = _common_types.GP10
        EP03 = _common_types.EP03
        EP04 = _common_types.EP04
        EP05 = _common_types.EP05
        EP06 = _common_types.EP06
        EP07 = _common_types.EP07
        EP08 = _common_types.EP08
        EP09 = _common_types.EP09
        EP10 = _common_types.EP10
        SP11 = _common_types.SP11
        SP12 = _common_types.SP12
        SP13 = _common_types.SP13
        SP14 = _common_types.SP14
        SP15 = _common_types.SP15
        SP16 = _common_types.SP16
        SP17 = _common_types.SP17
        SP18 = _common_types.SP18
        SP19 = _common_types.SP19
        SP20 = _common_types.SP20
    except:
        pass
try:
    import _zone
except ImportError:
    available_packs = set(Pack)

    def is_available_pack(pack):
        return pack in available_packs
is_available_pack = _zone.is_available_packavailable_packs = {pack for pack in Pack if is_available_pack(pack)}
class UnavailablePackError(ValueError):
    pass

def get_available_packs():
    return tuple(pack for pack in Pack if is_available_pack(pack))

def get_pack_name(value) -> str:
    try:
        return str(Pack(value))
    except:
        return '<Unknown Pack>'

def get_pack_enum(folder_name) -> Pack:
    try:
        pack_enum_name = 'Pack.{}'.format(folder_name[2:]).lower()
        for pack in Pack:
            if str(pack).lower() == pack_enum_name:
                return pack
        return Pack.BASE_GAME
    except:
        return Pack.BASE_GAME
