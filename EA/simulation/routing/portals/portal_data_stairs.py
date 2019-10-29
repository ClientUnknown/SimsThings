import mathfrom protocolbuffers import Routing_pb2 as routing_protocolsfrom objects.helpers.user_footprint_helper import UserFootprintHelperfrom routing import Location, SurfaceTypefrom routing.portals.portal_data_base import _PortalTypeDataBasefrom routing.portals.portal_tuning import PortalType, PortalFlagsfrom sims4 import hash_utilfrom sims4.geometry import Polygon, inflate_polygonfrom sims4.tuning.tunable import Tunableimport build_buyimport routingimport servicesimport sims4.logimport terrainlogger = sims4.log.Logger('Portal')
class _PortalTypeDataStairs(_PortalTypeDataBase):
    STAIR_SHOO_POLYGON_PADDING = Tunable(description='\n        When a sim uses a stair case with a stair landing, any sims who are\n        in the way will be shooed. The polygon that determines which sims are\n        shooed is based on the portals on that landing, but can be padded using\n        this constant.\n        ', tunable_type=float, default=0.3)
    FACTORY_TUNABLES = {'supports_landing_shoo': Tunable(description='\n            If True, sims standing on a stair landing on the object on which\n            this portal exists will be shooed from the path of the stairs if\n            another sim attempts to use the stairs. This is to avoid clipping.\n            ', tunable_type=bool, default=False)}

    @property
    def portal_type(self):
        return PortalType.PortalType_Animate

    def get_stair_count(self, obj):
        return build_buy.get_stair_count(obj.id, obj.zone_id)

    def notify_in_use(self, user, portal_instance, portal_object):
        if self.supports_landing_shoo:
            routing_surface = None
            exit_location = portal_instance.there_exit
            if exit_location.routing_surface.type == SurfaceType.SURFACETYPE_OBJECT:
                exit_height = terrain.get_terrain_height(exit_location.position.x, exit_location.position.z, routing_surface=exit_location.routing_surface)
                routing_surface = exit_location.routing_surface
                landing_points = []
                for (there_start, there_end, back_start, back_end, _) in self.get_portal_locations(portal_object):
                    for portal_location in (there_start, there_end, back_start, back_end):
                        if portal_location.routing_surface.type == SurfaceType.SURFACETYPE_OBJECT:
                            portal_height = terrain.get_terrain_height(portal_location.position.x, portal_location.position.z, routing_surface=portal_location.routing_surface)
                            if math.isclose(portal_height, exit_height):
                                landing_points.append(portal_location.position)
                polygon = Polygon(landing_points)
                polygon = polygon.get_convex_hull()
                polygon = inflate_polygon(polygon, _PortalTypeDataStairs.STAIR_SHOO_POLYGON_PADDING)
                UserFootprintHelper.force_move_sims_in_polygon(polygon, routing_surface, exclude=(user,))

    def add_portal_data(self, actor, portal_instance, is_mirrored, walkstyle):
        node_data = routing_protocols.RouteNodeData()
        obj = portal_instance.obj
        stair_count = self.get_stair_count(obj)
        node_data.type = routing_protocols.RouteNodeData.DATA_STAIRS
        op = routing_protocols.RouteStairsData()
        op.traversing_up = not is_mirrored
        op.stair_count = stair_count
        op.walkstyle = walkstyle
        op.stairs_per_cycle = 1
        node_data.data = op.SerializeToString()
        node_data.do_stop_transition = True
        node_data.do_start_transition = True
        return node_data

    def get_portal_duration(self, portal_instance, is_mirrored, walkstyle, age, gender, species):
        walkstyle_info_dict = routing.get_walkstyle_info_full(walkstyle, age, gender, species)
        builder_name = hash_util.hash32('stairs_down_cycle') if is_mirrored else hash_util.hash32('stairs_up_cycle')
        if builder_name not in walkstyle_info_dict:
            builder_name = hash_util.hash32('stairs_down_cycle_r') if is_mirrored else hash_util.hash32('stairs_up_cycle_r')
            if builder_name not in walkstyle_info_dict:
                logger.error('Failed to find stair builder for walkstyle {}.', walkstyle)
                return 0
        obj = portal_instance.obj
        stair_count = self.get_stair_count(obj)
        info = walkstyle_info_dict[builder_name]
        duration = info['duration']*stair_count
        return duration

    def get_portal_locations(self, obj):
        stair_lanes = routing.get_stair_portals(obj.id, obj.zone_id)
        if not stair_lanes:
            return ()
        locations = []
        for lane in stair_lanes:
            ((there_start, there_end), (back_start, back_end)) = lane
            (there_start_position, there_start_routing_surface) = there_start
            (there_end_position, there_end_routing_surface) = there_end
            (back_start_position, back_start_routing_surface) = back_start
            (back_end_position, back_end_routing_surface) = back_end
            if there_start_routing_surface == there_end_routing_surface:
                required_flags = PortalFlags.STAIRS_PORTAL_SHORT
            else:
                required_flags = PortalFlags.STAIRS_PORTAL_LONG
            locations.append((Location(there_start_position, routing_surface=there_start_routing_surface), Location(there_end_position, routing_surface=there_end_routing_surface), Location(back_start_position, routing_surface=back_start_routing_surface), Location(back_end_position, routing_surface=back_end_routing_surface), required_flags))
        return locations
