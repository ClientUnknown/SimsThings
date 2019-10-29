import enum
class CASPaintPose(enum.Int):
    NONE = 0
    SIT = 1
    BACK = 2
    SIT_UP = 3
    STAND = 4

class CASMode(enum.Int):
    BODY = 0
    FACE = 1
    FACE_DETAIL = 2
    NOACTION = 3

class RandomizationMode(enum.Int):
    SELECTIVE_RANDOMIZATION = 1
    MENU_RANDOMIZATION = 2
    CAREER_OUTFIT_RANDOMIZATION = 3
    CLUB_OUTFIT_RANDOMIZATION_ALL = 4
    CLUB_OUTFIT_RANDOMIZATION_SINGLE = 5
    TEMPLATE_RANDOMIZATION = 6

class CASMenuState:

    class MenuType(enum.Int):
        NONE = 0
        MENU = 4194304
        SUBMENU = 8388608
        MENUITEM = 12582912

    class MenuMode(enum.Int):
        NONE = 0
        PROFILE = 262144
        CLOTHING = 524288
        OUTFITS = 786432
        ACCESSORIES = 1048576
        FEATURED = 1310720

    class MenuSection(enum.Int):
        NONE = 0
        HEAD = 1024
        BODY = 2048
        UPPERBODY = 3072
        LOWERBODY = 4096
        HAIR = 6144
        ACCESSORIES = 7168
        FACE = 8192
        GENERIC_PELTS = 9216
        GENERIC_BREEDS = 10240

    class MenuItem(enum.Int):
        NONE = 0
        GENDER = 1
        AGE = 2
        VOICE = 3
        TRAITS = 4
        SKIN_DETAILS = 5
        TATTOOS = 6
        WHOLEHEADS = 7
        EYES = 8
        NOSE = 9
        CHEEK = 10
        MOUTH = 11
        JAW = 12
        CHIN = 13
        EARS = 14
        EYEBROWS = 15
        FOREHEAD = 16
        LOOKS = 17
        OWNED = 18
        BODY = 19
        SKINDETAIL_BROW = 20
        SKINDETAIL_CHEEKS = 21
        SKINDETAIL_EYEBAGS = 22
        SKINDETAIL_EYESOCKET = 23
        SKINDETAIL_MOUTH = 24
        TEETH = 25
        FACE_PRESETS = 26
        TAIL = 27
        HAIRSTYLE = 30
        FACIALHAIR = 31
        HATS = 32
        PIERCINGS = 33
        EARRINGS = 34
        GLASSES = 35
        MAKEUP = 36
        CONTACTS = 37
        MAKEUP_EYES = 40
        MAKEUP_CHEEKS = 41
        MAKEUP_LIPS = 42
        MAKEUP_FACEPAINT = 43
        MAKEUP_EYELINER = 44
        TOPS = 50
        BRACELETS = 51
        NECKLACES = 52
        RINGS = 53
        GLOVES = 54
        BOTTOMS = 70
        SHOES = 71
        STOCKINGS = 72
        SOCKS = 73
        TIGHTS = 74
        FULLBODY = 93
        OUTFIT_EVERYDAY = 100
        OUTFIT_FORMAL = 101
        OUTFIT_ATHLETIC = 102
        OUTFIT_MISC = 103
        OUTFIT_PARTY = 104
        OUTFIT_SLEEP = 105
        OUTFIT_WORK = 106
        PELT = 200
        BREED = 201
        FUR = 202

class CASRandomizeFlag(enum.Int):
    PROFILE_GENDER = 1
    PROFILE_BODYSHAPE = 2
    PROFILE_FACE = 8
    PROFILE_SKINTONE = 16
    PROFILE_HAIR = 32
    PROFILE_FACIALHAIR = 64
    PROFILE_VOICE = 128
    PROFILE_CLOTHING = 256
    PROFILE_ASPIRATION = 512
    PROFILE_TRAITS = 2048
    OCCULT_SKINDETAIL = 4096
    OCCULT_TAIL = 8192
    PROFILE_BREEDSIZE = 16384
    CLOTHING_HAT = 32768
    CLOTHING_TOP = 65536
    CLOTHING_BOTTOM = 131072
    CLOTHING_SHOES = 262144
    CLOTHING_MAKEUP = 524288
    CLOTHING_HAIR = 1048576
    CLOTHING_FACIAL_HAIR = 2097152
    CLOTHING_ACCESSORIES = 4194304
    CLOTHING_FULLBODY = 8388608
    RANDOMIZE_BY_MENUSTATE = 2147483648

class SimRegion(enum.Int):
    EYES = 0
    NOSE = 1
    MOUTH = 2
    MUZZLE = MOUTH
    CHEEKS = 3
    CHIN = 4
    JAW = 5
    FOREHEAD = 6
    BROWS = 8
    EARS = 9
    HEAD = 10
    FULLFACE = 12
    CHEST = 14
    UPPERCHEST = 15
    NECK = 16
    SHOULDERS = 17
    UPPERARM = 18
    LOWERARM = 19
    HANDS = 20
    FRONTFEET = HANDS
    WAIST = 21
    HIPS = 22
    BELLY = 23
    BUTT = 24
    THIGHS = 25
    LOWERLEG = 26
    FEET = 27
    BACKFEET = FEET
    BODY = 28
    UPPERBODY = 29
    LOWERBODY = 30
    TAIL = 31
    FUR = 32
    FORELEGS = 33
    HINDLEGS = 34
    INVALID = 64
