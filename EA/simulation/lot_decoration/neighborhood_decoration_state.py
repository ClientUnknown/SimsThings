from lot_decoration.decoratable_lot import DecoratableLot
class NeighborhoodDecorationState:

    def __init__(self, world_id, zone_datas):
        self._zone_to_lot_decoration_data = {}
        self._world_id = world_id
        for lot_info in zone_datas:
            self._zone_to_lot_decoration_data[lot_info.zone_id] = DecoratableLot(lot_info)

    @property
    def lots(self):
        return self._zone_to_lot_decoration_data.values()

    @property
    def world_id(self):
        return self._world_id

    def get_deco_lot_by_zone_id(self, zone_id):
        return self._zone_to_lot_decoration_data[zone_id]
