import enumimport servicesimport sims4.math
class PickType(enum.Int):
    PICK_NONE = 0
    PICK_UNKNOWN = 1
    PICK_OBJECT = 2
    PICK_SIM = 3
    PICK_WALL = 4
    PICK_FLOOR = 5
    PICK_TERRAIN = 6
    PICK_STAIRS = 7
    PICK_ROOF = 8
    PICK_MISC = 9
    PICK_PORTRAIT = 10
    PICK_SKEWER = 11
    PICK_FOUNDATION = 12
    PICK_WATER_TERRAIN = 13
    PICK_POOL_TRIM = 14
    PICK_POOL_SURFACE = 15
    PICK_POOL_EDGE = 16
    PICK_FOUNTAIN = 17
    PICK_CLUB_PANEL = 18
    PICK_MANAGE_OUTFITS = -2
PICK_TRAVEL = frozenset([PickType.PICK_TERRAIN, PickType.PICK_FLOOR, PickType.PICK_UNKNOWN, PickType.PICK_STAIRS, PickType.PICK_FOUNDATION, PickType.PICK_POOL_SURFACE, PickType.PICK_POOL_TRIM, PickType.PICK_POOL_EDGE, PickType.PICK_FOUNTAIN])PICK_UNGREETED = frozenset([PickType.PICK_ROOF, PickType.PICK_WALL, PickType.PICK_FLOOR, PickType.PICK_STAIRS, PickType.PICK_FOUNDATION])PICK_USE_TERRAIN_OBJECT = frozenset(PICK_TRAVEL | PICK_UNGREETED)PICK_NEVER_USE_POOL = frozenset([PickType.PICK_STAIRS, PickType.PICK_POOL_EDGE])
class PickTerrainType(enum.Int):
    ANYWHERE = 0
    ON_LOT = 1
    OFF_LOT = 2
    NO_LOT = 3
    ON_OTHER_LOT = 4
    IN_STREET = 5
    OFF_STREET = 6
    IS_OUTSIDE = 7

class PickInfo:
    __slots__ = ('_location', '_lot_id', '_level', '_routing_surface', '_type', '_target', '_modifiers', '_ignore_neighborhood_id')

    class PickModifiers:
        __slots__ = ('_alt', '_control', '_shift')

        def __init__(self, alt=False, control=False, shift=False):
            self._alt = alt
            self._control = control
            self._shift = shift

        @property
        def alt(self):
            return self._alt

        @property
        def control(self):
            return self._control

        @property
        def shift(self):
            return self._shift

    def __init__(self, pick_type=PickType.PICK_UNKNOWN, target=None, location=sims4.math.Vector3.ZERO(), routing_surface=None, lot_id=None, level=0, alt=False, control=False, shift=False, ignore_neighborhood_id=False):
        self._type = pick_type
        self._target = target.ref() if target is not None else None
        self._location = location
        self._routing_surface = routing_surface
        self._lot_id = lot_id
        self._level = level
        self._modifiers = PickInfo.PickModifiers(alt, control, shift)
        self._ignore_neighborhood_id = ignore_neighborhood_id

    @property
    def pick_type(self):
        return self._type

    @property
    def target(self):
        if self._target is not None:
            return self._target()

    @property
    def location(self):
        return self._location

    @property
    def routing_surface(self):
        return self._routing_surface

    @property
    def lot_id(self):
        return self._lot_id

    @property
    def level(self):
        return self._level

    @property
    def modifiers(self):
        return self._modifiers

    @property
    def ignore_neighborhood_id(self):
        return self._ignore_neighborhood_id

    def get_zone_id_from_pick_location(self):
        lot_id = self.lot_id
        if lot_id is None:
            return
        plex_service = services.get_plex_service()
        if services.active_lot_id() == lot_id and plex_service.is_active_zone_a_plex():
            return plex_service.get_plex_zone_at_position(self.location, self.level)
        persistence_service = services.get_persistence_service()
        return persistence_service.resolve_lot_id_into_zone_id(lot_id, ignore_neighborhood_id=self._ignore_neighborhood_id)
