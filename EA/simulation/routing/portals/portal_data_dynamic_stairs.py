from routing import Locationfrom routing.portals import portal_locationfrom routing.portals.portal_data_stairs import _PortalTypeDataStairsfrom routing.portals.portal_tuning import PortalFlagsfrom sims4.tuning.tunable import TunableList, TunableTuple, TunableRange
class _PortalTypeDataDynamicStairs(_PortalTypeDataStairs):
    FACTORY_TUNABLES = {'lanes': TunableList(description='\n            The bones that describe each set of lanes (up and down).\n            ', tunable=TunableTuple(description='\n                Groups of bones that represent the up and down routes for this\n                lane.\n                ', up_begin=portal_location._PortalBoneLocation.TunableFactory(description='\n                    The bone for the beginning of the path up the stairs.\n                    '), up_end=portal_location._PortalBoneLocation.TunableFactory(description='\n                    The bone for the end of the path up the stairs.\n                    '), down_begin=portal_location._PortalBoneLocation.TunableFactory(description='\n                    The bone for the beginning of the path down the stairs.\n                    '), down_end=portal_location._PortalBoneLocation.TunableFactory(description='\n                    The bone for the end of the path down the stairs.\n                    '))), 'stair_count': TunableRange(description='\n            The number of stairs the Sim will traverse for this portal.\n            ', tunable_type=int, default=8, minimum=1)}

    def get_stair_count(self, _):
        return self.stair_count

    def get_portal_locations(self, obj):
        locations = []
        for lane in self.lanes:
            up_start = lane.up_begin(obj)
            up_end = lane.up_end(obj)
            down_start = lane.down_begin(obj)
            down_end = lane.down_end(obj)
            locations.append((Location(up_start.position, routing_surface=up_start.routing_surface), Location(up_end.position, routing_surface=up_end.routing_surface), Location(down_start.position, routing_surface=down_start.routing_surface), Location(down_end.position, routing_surface=down_end.routing_surface), PortalFlags.STAIRS_PORTAL_LONG))
        return locations
