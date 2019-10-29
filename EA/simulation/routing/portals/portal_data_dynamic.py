from _math import Transform, Vector3, Quaternionfrom placement import ItemTypefrom routing import Locationfrom routing.portals import PY_OBJ_DATA, SURFACE_OBJ_ID, portal_locationfrom routing.portals.portal_data_variable_jump import _PortalTypeDataVariableJumpfrom sims4.tuning.tunable import TunableList, TunableTuple, TunableRange, OptionalTunable, TunableAngleimport servicesimport sims4.math
class _PortalTypeDataDynamic(_PortalTypeDataVariableJump):
    PORTAL_SEARCH_RADIUS = 2.0
    PORTAL_PART_SEARCH_RADIUS = 2.7
    FACTORY_TUNABLES = {'object_portals': TunableList(description='\n            List of entry and exit location points that will define the entry\n            and exit portal to and from this object.\n            ', tunable=TunableTuple(description='\n                Pair of exit and entry portal locations.\n                ', location_entry=portal_location._PortalLocation.TunableFactory(description='\n                    The entry portal.\n                    ', locked_args={'orientation': None, 'routing_surface': portal_location.ROUTING_SURFACE_OBJECT}))), 'additional_search_radius': TunableRange(description='\n            Define an additional value in meters to increase the search for \n            other surfaces when a dynamic portal is generated.\n            This should be tuned for objects where the width is too high and \n            we need to take into account their placements can be farther apart\n            than a regular object like a counter which only uses the default \n            radius.\n            ', tunable_type=float, default=0.0, minimum=0.0), 'entry_offset': TunableRange(description='\n            Define an offset that will be used for any dynamic portal entering\n            this object.\n            By definition all dynamic portals use the center, but by tuning\n            this the portal may allow for an offset from the center so the \n            Sim can get in closer to the edge of the object whenever it wants\n            to enter.\n            ', tunable_type=float, default=0.0, minimum=0.0), 'exit_offset': TunableRange(description='\n            Define an offset that will be used for any dynamic portal exiting\n            this object.\n            By definition all dynamic portals use the center, but by tuning\n            this the portal may allow for an offset from the center so the \n            Sim can get in closer to the edge of the object whenever it wants\n            to exit.\n            ', tunable_type=float, default=0.0, minimum=0.0), 'angle_restriction': OptionalTunable(description="\n            If enabled, dynamic portals will only be generated when the angle \n            is within the angle restriction (counter-clockwise from start-angle\n            to end-angle).\n            \n            This won't be necessary for many cases. However, when dynamic \n            portal only be allowed to generate from specific sides of the \n            object (ex. front and left sides for Hamster Cage object), this\n            will be useful.\n            ", tunable=TunableTuple(description='\n                Angle restriction in degrees, value range of 0-360.\n                ', start_angle=TunableAngle(0), end_angle=TunableAngle(sims4.math.PI)))}

    def get_dynamic_portal_locations_gen(self, obj):
        for portal_entry in self.object_portals:
            yield (portal_entry.location_entry(obj), self.angle_restriction)

    def _is_angle_valid(self, entry_orientation, obj, angle_restriction):
        rel_orientation = Quaternion.concatenate(sims4.math.invert_quaternion(obj.transform.orientation), entry_orientation)
        angle = sims4.math.yaw_quaternion_to_angle(rel_orientation)
        if sims4.math.is_angle_in_between(angle, angle_restriction.start_angle, angle_restriction.end_angle):
            return True
        return False

    def _update_portal_location(self, locations, there_entry, there_exit, obj, other_obj, other_obj_angle_restriction):
        if there_entry.position == there_exit.position:
            return
        entry_in_position = there_entry.position + sims4.math.vector_normalize(there_exit.position - there_entry.position)*self.entry_offset
        entry_out_position = there_entry.position + sims4.math.vector_normalize(there_exit.position - there_entry.position)*self.exit_offset
        entry_in_position = Vector3(entry_in_position.x, there_entry.position.y, entry_in_position.z)
        entry_out_position = Vector3(entry_out_position.x, there_entry.position.y, entry_out_position.z)
        entry_angle = sims4.math.vector3_angle(there_exit.position - entry_in_position)
        exit_angle = sims4.math.vector3_angle(entry_in_position - there_exit.position)
        entry_orientation = sims4.math.angle_to_yaw_quaternion(entry_angle)
        exit_orientation = sims4.math.angle_to_yaw_quaternion(exit_angle)
        if self.angle_restriction is not None and not self._is_angle_valid(entry_orientation, obj, self.angle_restriction):
            return
        if other_obj_angle_restriction is not None and not self._is_angle_valid(exit_orientation, other_obj, other_obj_angle_restriction):
            return
        _there_in_entry = Location(entry_in_position, entry_orientation, there_entry.routing_surface)
        _there_out_entry = Location(entry_out_position, entry_orientation, there_entry.routing_surface)
        there_exit.transform = Transform(there_exit.position, exit_orientation)
        locations.append((_there_in_entry, there_exit, there_exit, _there_out_entry, 0))

    def get_portal_locations(self, obj):
        locations = []
        for portal_entry in self.object_portals:
            there_entry = portal_entry.location_entry(obj)
            bounds = sims4.geometry.QtCircle(sims4.math.Vector2(there_entry.position.x, there_entry.position.z), self.PORTAL_SEARCH_RADIUS + self.additional_search_radius)
            try:
                object_surfaces = services.sim_quadtree().query(bounds=bounds, surface_id=there_entry.routing_surface, filter=ItemType.ROUTABLE_OBJECT_SURFACE, flags=sims4.geometry.ObjectQuadTreeQueryFlag.IGNORE_SURFACE_TYPE)
            except:
                continue
            for object_data in object_surfaces:
                obj_id = object_data[PY_OBJ_DATA][SURFACE_OBJ_ID]
                other_obj = services.object_manager().get(obj_id)
                if other_obj is None:
                    pass
                elif other_obj.id == obj.id:
                    pass
                else:
                    for (there_exit, other_obj_angle_restriction) in other_obj.get_dynamic_portal_locations_gen():
                        self._update_portal_location(locations, there_entry, there_exit, obj, other_obj, other_obj_angle_restriction)
                    if other_obj.parts is None:
                        pass
                    else:
                        for part in other_obj.parts:
                            distance = (obj.position - part.position).magnitude_2d()
                            if distance <= self.PORTAL_PART_SEARCH_RADIUS + self.additional_search_radius:
                                for portal_data in part.part_definition.portal_data:
                                    for (there_exit, other_obj_angle_restriction) in portal_data.get_dynamic_portal_locations_gen(part):
                                        self._update_portal_location(locations, there_entry, there_exit, obj, other_obj, other_obj_angle_restriction)
        return locations
