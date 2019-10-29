from caches import cachedfrom routing.portals.portal_data_locomotion import _PortalTypeDataLocomotionfrom routing.portals.portal_tuning import PortalTypefrom tag import TunableTagsimport services
class _PortalTypeDataTeleport(_PortalTypeDataLocomotion):
    FACTORY_TUNABLES = {'destination_object_tags': TunableTags(description='\n            A list of tags used to find objects that this object connects with\n            to form two sides of a portal. \n            When the portals are created all of the objects on the lot with at \n            least one of the tags found in this list are found and a portal is \n            created between the originating object and the described object.\n            ')}

    @property
    def requires_los_between_points(self):
        return False

    @property
    def portal_type(self):
        return PortalType.PortalType_Wormhole

    @cached
    def get_portal_locations(self, obj):
        object_manager = services.object_manager()
        locations = []
        for connected_object in object_manager.get_objects_with_tags_gen(*self.destination_object_tags):
            if connected_object is obj:
                pass
            else:
                for portal_entry in self.object_portals:
                    entry_location = portal_entry.location_entry(obj)
                    exit_location = portal_entry.location_exit(connected_object)
                    if portal_entry.is_bidirectional:
                        locations.append((entry_location, exit_location, exit_location, entry_location, 0))
                    else:
                        locations.append((entry_location, exit_location, None, None, 0))
        return locations

    @cached
    def get_destination_objects(self):
        object_manager = services.object_manager()
        destination_objects = tuple(object_manager.get_objects_with_tags_gen(*self.destination_object_tags))
        return destination_objects
