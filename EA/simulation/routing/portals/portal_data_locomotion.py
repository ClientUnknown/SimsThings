from _math import Transform, Vector3from routing import SurfaceTypefrom routing.portals.portal_data_base import _PortalTypeDataBasefrom routing.portals.portal_location import _PortalLocationfrom routing.portals.portal_tuning import PortalTypefrom sims4.tuning.tunable import TunableList, TunableTuple, Tunable, OptionalTunable, TunableVariantimport routingimport servicesimport sims4import terrain
class _PortalTypeDataLocomotion(_PortalTypeDataBase):
    FACTORY_TUNABLES = {'object_portals': TunableList(description='\n            List of entry and exit location points that will define the entry\n            and exit portal to and from this object.\n            ', tunable=TunableTuple(description='\n                Pair of exit and entry portal locations.\n                ', location_entry=_PortalLocation.TunableFactory(description='\n                    The entry portal.\n                    ', locked_args={'orientation': None}), location_exit=_PortalLocation.TunableFactory(description='\n                    The exit portal.\n                    ', locked_args={'orientation': None}), is_bidirectional=Tunable(description='\n                    If checked, then a portal with the same exact properties is\n                    created from the exit location to the entry location.\n                    \n                    If unchecked, then only one portal is created: from the\n                    entry location to the exit location.\n                    ', tunable_type=bool, default=True))), 'bidirectional_portal_offset': OptionalTunable(description='\n            If enabled, portals defined on this object, will have an offset\n            applied to the entry portal of bidirectional portals. \n            The offset will be applied only to the object surface point of the\n            entry portal created by bidirectional portals.\n            For example: If you make a bidirectional portal from ground to a \n            counter, the point on the counter for the entry portal will have\n            an offset applied.\n            This way, portals can be generated for Sims like Cats, where the \n            entry point should have a small difference to the exit due \n            animation constraints.\n            ', tunable=Tunable(description='\n                Offset in meters that will be applied to the entry portal.\n                ', tunable_type=float, default=0.1)), '_height_tolerance': TunableVariant(description="\n            Define the maximum height between the portal points and the object's\n            location. If either the portal entry point or the portal exit point\n            is at a location whose y position differs by more than this amount\n            from the object's, the portal is not created.\n            ", locked_args={'no_tolerance': 0.1, 'allow_step_foundation': 0.26, 'unlimited': None}, default='no_tolerance'), '_require_los': Tunable(description='\n            If checked, portals are created only if the segment between them\n            does not intersect other objects or a wall. If unchecked, no such\n            restriction exists.\n            \n            This should be unchecked on portals that are meant to be traversed\n            through a wall, e.g. a door.\n            ', tunable_type=bool, default=True)}

    @property
    def portal_type(self):
        return PortalType.PortalType_Walk

    @property
    def requires_los_between_points(self):
        return self._require_los

    def get_portal_duration(self, portal_instance, is_mirrored, walkstyle, age, gender, species):
        return 0

    def _get_offset_positions(self, there_entry, there_exit, angle):
        if self.bidirectional_portal_offset is not None and there_entry.routing_surface.type == SurfaceType.SURFACETYPE_OBJECT:
            entry_exit = there_exit.position - there_entry.position
            unit_vector = sims4.math.vector_normalize(entry_exit)
            modified_position = Vector3(there_entry.position.x + unit_vector.x*self.bidirectional_portal_offset, there_entry.position.y, there_entry.position.z + unit_vector.z*self.bidirectional_portal_offset)
            return routing.Location(modified_position, sims4.math.angle_to_yaw_quaternion(angle), routing_surface=there_entry.routing_surface)
        return there_entry

    def _is_offset_from_object(self, portal_position, obj):
        if self._height_tolerance is None:
            return False
        if portal_position.routing_surface.type != SurfaceType.SURFACETYPE_WORLD:
            return False
        portal_height = terrain.get_lot_level_height(portal_position.position.x, portal_position.position.z, portal_position.routing_surface.secondary_id, portal_position.routing_surface.primary_id)
        portal_height_difference = abs(obj.position.y - portal_height)
        return portal_height_difference > self._height_tolerance

    def _is_object_routing_surface_overlap(self, portal_position, obj):
        if portal_position.routing_surface.type != routing.SurfaceType.SURFACETYPE_OBJECT:
            return False
        return obj.is_routing_surface_overlapped_at_position(portal_position.position)

    def get_portal_locations(self, obj):
        locations = []
        for portal_entry in self.object_portals:
            there_entry = portal_entry.location_entry(obj)
            there_exit = portal_entry.location_exit(obj)
            if not self._is_offset_from_object(there_entry, obj):
                if self._is_offset_from_object(there_exit, obj):
                    pass
                elif not self._is_object_routing_surface_overlap(there_entry, obj):
                    if self._is_object_routing_surface_overlap(there_exit, obj):
                        pass
                    else:
                        entry_angle = sims4.math.vector3_angle(there_exit.position - there_entry.position)
                        there_entry.transform = Transform(there_entry.position, sims4.math.angle_to_yaw_quaternion(entry_angle))
                        exit_angle = sims4.math.vector3_angle(there_entry.position - there_exit.position)
                        there_exit.transform = Transform(there_exit.position, sims4.math.angle_to_yaw_quaternion(exit_angle))
                        if portal_entry.is_bidirectional:
                            offset_entry = self._get_offset_positions(there_entry, there_exit, entry_angle)
                            offset_exit = self._get_offset_positions(there_exit, there_entry, exit_angle)
                            if self._is_object_routing_surface_overlap(offset_entry, obj) or not self._is_object_routing_surface_overlap(offset_exit, obj):
                                locations.append((offset_entry, offset_exit, there_exit, there_entry, 0))
                                locations.append((there_entry, there_exit, None, None, 0))
                        else:
                            locations.append((there_entry, there_exit, None, None, 0))
        return locations
