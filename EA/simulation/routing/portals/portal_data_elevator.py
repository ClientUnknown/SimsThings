from _animation import get_joint_transform_from_rigfrom plex.plex_enums import PlexBuildingTypefrom routing import Location, SurfaceIdentifier, SurfaceTypefrom routing.portals.portal_data_base import _PortalTypeDataBasefrom routing.portals.portal_tuning import PortalTypefrom sims4.tuning.tunable import TunableEnumEntryfrom sims4.tuning.tunable_hash import TunableStringHash32from tag import Tagimport servicesimport sims4.loglogger = sims4.log.Logger('Elevator', default_owner='tingyul')
class _PortalTypeDataElevator(_PortalTypeDataBase):
    FACTORY_TUNABLES = {'shell_bone_name': TunableStringHash32(description='\n            The elevator builds a portal between itself and the shell object on\n            the lot. The exact portal end points are positioned based on bone\n            positions on the elevator and shell models.\n            \n            This is the name of the bone on the shell where the shell end of the\n            portal should be.\n            ', default='_route_0'), 'elevator_bone_name': TunableStringHash32(description='\n            The elevator builds a portal between itself and the shell object on\n            the lot. The exact portal end points are positioned based on bone\n            positions on the elevator and shell models.\n            \n            This is the name of the bone on the elevator where the elevator end\n            of the portal should be.\n            ', default='_route_'), 'shell_tag': TunableEnumEntry(description='\n            Tag to find the shell by. There should only be one such object on\n            the lot the elevator is on.\n            ', tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,))}

    @property
    def requires_los_between_points(self):
        return False

    @property
    def portal_type(self):
        return PortalType.PortalType_Wormhole

    @staticmethod
    def _get_bone_position(obj, bone_name):
        if obj is None or obj.rig is None or obj.rig == sims4.resources.INVALID_KEY:
            rig_name = str(obj.rig) if obj.rig is not None else 'No Rig'
            logger.error('Setup Portal: Unable to get position for bone {} in object {} with rig {}.', bone_name, str(obj), rig_name)
            return
        joint_transform = get_joint_transform_from_rig(obj.rig, bone_name)
        return obj.transform.transform_point(joint_transform.translation)

    def _get_shell(self):
        candidates = list(services.object_manager().get_objects_with_tag_gen(self.shell_tag))
        if not candidates:
            zone_id = services.current_zone_id()
            if services.get_plex_service().is_zone_an_apartment(zone_id, consider_penthouse_an_apartment=True):
                logger.error('Failed to find shell. Tag: {}.', self.shell_tag)
            return
        if len(candidates) > 1:
            logger.error('Found multiple shells. Candidates: {}. Tag: {}.', candidates, self.shell_tag)
        return candidates[0]

    def get_portal_locations(self, obj):
        shell = self._get_shell()
        if shell is None:
            return ()
        elevator_pos = self._get_bone_position(obj, self.elevator_bone_name)
        if elevator_pos is None:
            return ()
        shell_pos = self._get_bone_position(shell, self.shell_bone_name)
        if shell_pos is None:
            return ()
        elevator_loc = Location(elevator_pos, routing_surface=obj.routing_surface)
        shell_routing_surface = SurfaceIdentifier(services.current_zone_id(), 0, SurfaceType.SURFACETYPE_WORLD)
        shell_loc = Location(shell_pos, routing_surface=shell_routing_surface)
        return ((shell_loc, elevator_loc, elevator_loc, shell_loc, 0),)

    def is_ungreeted_sim_disallowed(self):
        zone_id = services.current_zone_id()
        active_household = services.active_household()
        if active_household is not None and active_household.home_zone_id == zone_id:
            return False
        else:
            plex_service = services.get_plex_service()
            if plex_service.get_plex_building_type(zone_id) != PlexBuildingType.PENTHOUSE_PLEX:
                return False
        return True
