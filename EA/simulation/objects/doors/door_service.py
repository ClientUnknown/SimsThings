from collections import namedtupleimport operatorfrom native.routing.connectivity import Handlefrom objects.doors.door import Doorfrom objects.doors.door_enums import VenueFrontdoorRequirementfrom plex.plex_enums import PlexBuildingTypefrom routing.portals.portal_tuning import PortalFlagsfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableEnumFlagsfrom sims4.utils import classpropertyfrom singletons import EMPTY_SETfrom venues.venue_constants import VenueTuningimport persistence_error_typesimport routingimport servicesimport sims4.loglogger = sims4.log.Logger('DoorService', default_owner='tingyul')ExteriorDoorInfo = namedtuple('ExteriorDoorInfo', ('door', 'distance', 'is_backwards'))PlexDoorInfo = namedtuple('PlexDoorInfo', ('door_id', 'zone_id', 'is_backwards'))
class DoorConnectivityHandle(Handle):

    def __init__(self, location, routing_surface, *, door, is_front):
        super().__init__(location, routing_surface)
        self.door = door
        self.is_front = is_front

class DoorService(Service):
    FRONT_DOOR_ALLOWED_PORTAL_FLAGS = TunableEnumFlags(description="\n        Door Service does a routability check to all doors from the lot's\n        arrival spawn point to find doors that are reachable without crossing\n        other doors.\n        \n        These flags are supplied to the routability check's PathPlanContext, to\n        tell it what portals are usable. For example, stair portals should be\n        allowed (e.g. for front doors off the ground level, or house is on a\n        foundation).\n        ", enum_type=PortalFlags)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._front_door_id = None
        self._plex_door_infos = EMPTY_SET

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_DOOR_SERVICE

    def has_front_door(self):
        return self._front_door_id is not None

    def get_front_door(self):
        return services.object_manager().get(self._front_door_id)

    def on_door_removed(self, door):
        if door.id == self._front_door_id:
            self._front_door_id = None

    def fix_up_doors(self, force_refresh=False):
        building_type = services.get_plex_service().get_plex_building_type(services.current_zone_id())
        if building_type == PlexBuildingType.DEFAULT or building_type == PlexBuildingType.PENTHOUSE_PLEX or building_type == PlexBuildingType.COASTAL:
            self._fix_up(force_refresh=force_refresh)
        elif building_type == PlexBuildingType.FULLY_CONTAINED_PLEX:
            self._fix_up_for_apartments()
        services.object_manager().on_front_door_candidates_changed()

    def _fix_up(self, force_refresh):
        (exterior_door_infos, interior_doors) = self._get_exterior_and_interior_doors()
        backward_doors = set(info.door for info in exterior_door_infos if info.is_backwards)
        self._flip_backward_doors(backward_doors)
        self._set_front_door_availabilities(exterior_door_infos, interior_doors)
        preferred_door_id = self._front_door_id if not force_refresh else None
        new_front_door = self._choose_front_door(exterior_door_infos, preferred_door_id=preferred_door_id)
        self.set_as_front_door(new_front_door)

    def set_as_front_door(self, door):
        if door is None and self._front_door_id is None:
            return
        if door is not None and self._front_door_id == door.id:
            return
        old_door = services.object_manager().get(self._front_door_id)
        if old_door is not None:
            old_door.set_front_door_status(False)
        self._front_door_id = None
        if door is not None:
            door.set_front_door_status(True)
            self._front_door_id = door.id

    def _flip_backward_doors(self, doors):
        for door in doors:
            door.swap_there_and_back()

    def _set_front_door_availabilities(self, exterior_door_infos, interior_doors):
        zone_requires_front_door = self._zone_requires_front_door()
        for info in exterior_door_infos:
            info.door.set_front_door_availability(zone_requires_front_door)
        for door in interior_doors:
            door.set_front_door_availability(False)

    def _zone_requires_front_door(self):
        zone = services.current_zone()
        venue = zone.venue_service.venue
        requires_front_door = venue.venue_requires_front_door
        if requires_front_door == VenueFrontdoorRequirement.NEVER:
            return False
        if requires_front_door == VenueFrontdoorRequirement.ALWAYS:
            return True
        if requires_front_door == VenueFrontdoorRequirement.OWNED_OR_RENTED:
            if services.travel_group_manager().is_current_zone_rented():
                return True
            return zone.lot.owner_household_id != 0
        logger.error('Current venue {} at Zone {} has front door requirement set to invalid value: {}', venue, zone, requires_front_door, owner='trevor')
        return False

    def _choose_front_door(self, exterior_door_infos, preferred_door_id=None):
        if not self._zone_requires_front_door():
            return
        if preferred_door_id is not None:
            for info in exterior_door_infos:
                if info.door.id == preferred_door_id:
                    return info.door
        if not exterior_door_infos:
            return
        info = min(exterior_door_infos, key=operator.attrgetter('distance'))
        return info.door

    def _object_is_door(self, obj):
        if not isinstance(obj, Door):
            return False
        elif not obj.is_door_portal:
            return False
        return True

    def _get_doors(self):
        doors = frozenset(obj for obj in services.object_manager().values() if self._object_is_door(obj))
        return doors

    def _get_arrival_point(self):
        zone = services.current_zone()
        spawn_point = zone.active_lot_arrival_spawn_point
        if spawn_point is not None:
            return spawn_point.get_approximate_center()
        logger.error('Active lot missing lot arrival spawn points. This will cause incorrect front door behavior.', zone.lot.lot_id)
        return zone.lot.corners[1]

    def _get_exterior_and_interior_doors(self):
        zone = services.current_zone()
        doors = self._get_doors()
        source_point = self._get_arrival_point()
        source_handles = set()
        source_handle = Handle(source_point, routing.SurfaceIdentifier(zone.id, 0, routing.SurfaceType.SURFACETYPE_WORLD))
        source_handles.add(source_handle)
        routing_context = routing.PathPlanContext()
        for door in doors:
            for portal_handle in door.get_portal_pairs():
                routing_context.lock_portal(portal_handle.there)
                routing_context.lock_portal(portal_handle.back)
        routing_context.set_key_mask(routing.FOOTPRINT_KEY_ON_LOT | routing.FOOTPRINT_KEY_OFF_LOT)
        routing_context.set_portal_key_mask(DoorService.FRONT_DOOR_ALLOWED_PORTAL_FLAGS)
        dest_handles = set()
        for door in doors:
            (front_position, back_position) = door.get_door_positions()
            if not front_position is None:
                if back_position is None:
                    pass
                else:
                    dest_handles.add(DoorConnectivityHandle(front_position, door.routing_surface, door=door, is_front=True))
                    dest_handles.add(DoorConnectivityHandle(back_position, door.routing_surface, door=door, is_front=False))
        connections = ()
        if dest_handles:
            connections = routing.estimate_path_batch(source_handles, dest_handles, routing_context=routing_context)
            if connections is None:
                connections = ()
        exterior_door_to_infos = {}
        for (_, handle, distance) in connections:
            old_info = exterior_door_to_infos.get(handle.door)
            if old_info is not None and not handle.is_front:
                pass
            else:
                is_backwards = not handle.is_front
                info = ExteriorDoorInfo(door=handle.door, distance=distance, is_backwards=is_backwards)
                exterior_door_to_infos[handle.door] = info
        interior_doors = frozenset(door for door in doors if door not in exterior_door_to_infos)
        return (frozenset(exterior_door_to_infos.values()), interior_doors)

    def _fix_up_for_apartments(self):
        plex_door_infos = self.get_plex_door_infos(force_refresh=True)
        backward_doors = set()
        active_zone_id = services.current_zone_id()
        object_manager = services.object_manager()
        for info in plex_door_infos:
            household_id = services.get_persistence_service().get_household_id_from_zone_id(info.zone_id)
            door = object_manager.get(info.door_id)
            if door is None:
                logger.error('Plex Door {} does not exist.', info.door_id, owner='rmccord')
            else:
                if info.is_backwards:
                    backward_doors.add(door)
                    current_zone = services.current_zone()
                    lot = current_zone.lot
                    world_description_id = services.get_world_description_id(current_zone.world_id)
                    lot_description_id = services.get_lot_description_id(lot.lot_id, world_description_id)
                    neighborhood_id = current_zone.neighborhood_id
                    neighborhood_data = services.get_persistence_service().get_neighborhood_proto_buff(neighborhood_id)
                    logger.error('For WB: An apartment door facing the common area needs to be flipped. Lot desc id: {}, World desc id: {}. Neighborhood id: {}, Neighborhood Name: {}', lot_description_id, world_description_id, neighborhood_id, neighborhood_data.name)
                door.set_household_owner_id(household_id)
                if info.zone_id == active_zone_id:
                    self.set_as_front_door(door)
                else:
                    door.set_inactive_apartment_door_status(True)
        self._flip_backward_doors(backward_doors)

    def unlock_all_doors(self):
        doors = self._get_doors()
        for door in doors:
            door.remove_locks()

    def get_plex_door_infos(self, force_refresh=False):
        if self._plex_door_infos and not force_refresh:
            return self._plex_door_infos
        plex_service = services.get_plex_service()
        doors = self._get_doors()
        plex_door_infos = set()
        for door in doors:
            (front_position, back_position) = door.get_door_positions()
            if front_position is None or back_position is None:
                logger.error("Door '{}' has broken portals.", door)
            else:
                front_zone_id = plex_service.get_plex_zone_at_position(front_position, door.level)
                back_zone_id = plex_service.get_plex_zone_at_position(back_position, door.level)
                if front_zone_id is None and back_zone_id is None:
                    current_zone = services.current_zone()
                    lot = current_zone.lot
                    world_description_id = services.get_world_description_id(current_zone.world_id)
                    lot_description_id = services.get_lot_description_id(lot.lot_id, world_description_id)
                    neighborhood_id = current_zone.neighborhood_id
                    neighborhood_data = services.get_persistence_service().get_neighborhood_proto_buff(neighborhood_id)
                    logger.error("Door isn't part of any plex. This will require WB fix. Door: {}, Lot desc id: {}, World desc id: {}. Neighborhood id: {}, Neighborhood Name: {}", door, lot_description_id, world_description_id, neighborhood_id, neighborhood_data.name)
                elif front_zone_id == back_zone_id:
                    pass
                else:
                    zone_id = front_zone_id or back_zone_id
                    is_backwards = front_zone_id is not None
                    info = PlexDoorInfo(door_id=door.id, zone_id=zone_id, is_backwards=is_backwards)
                    plex_door_infos.add(info)
        self._plex_door_infos = frozenset(plex_door_infos)
        return self._plex_door_infos

    def save(self, zone_data=None, **kwargs):
        if self._front_door_id is not None:
            zone_data.front_door_id = self._front_door_id

    def load(self, zone_data=None):
        for door in self._get_doors():
            door.set_front_door_status(False)
            door.set_front_door_availability(False)
            door.set_inactive_apartment_door_status(False)
        if zone_data is not None and zone_data.HasField('front_door_id'):
            door = services.object_manager().get(zone_data.front_door_id)
            if door is not None:
                self.set_as_front_door(door)
