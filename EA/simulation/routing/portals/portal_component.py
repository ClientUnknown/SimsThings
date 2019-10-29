from _math import Vector3Immutablefrom collections import namedtuplefrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableList, OptionalTunableimport sims4.utilsfrom objects.components import Component, types, componentmethod_with_fallback, componentmethodfrom objects.components.portal_locking_component import PortalLockingComponentfrom routing import remove_portalfrom routing.portals.portal_animation_component import PortalAnimationComponentfrom routing.portals.portal_data import TunablePortalReferencefrom routing.portals.portal_enums import PathSplitTypefrom routing.portals.portal_tuning import PortalTypefrom tag import TunableTagsimport servicesimport tag_PortalPair = namedtuple('_PortalPair', ['there', 'back'])
class PortalComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=types.PORTAL_COMPONENT):
    PORTAL_DIRECTION_THERE = 0
    PORTAL_DIRECTION_BACK = 1
    PORTAL_LOCATION_ENTRY = 0
    PORTAL_LOCATION_EXIT = 1
    FACTORY_TUNABLES = {'_portal_data': TunableList(description='\n            The portals that are to be created for this object.\n            ', tunable=TunablePortalReference(pack_safe=True)), '_portal_animation_component': OptionalTunable(description='\n            If enabled, this portal animates in response to agents traversing\n            it. Use Enter/Exit events to control when and for how long an\n            animation plays.\n            ', tunable=PortalAnimationComponent.TunableFactory()), '_portal_locking_component': OptionalTunable(description='\n            If enabled then this object will be capable of being locked using\n            the same system as Portal Objects.\n            \n            If not enabled then it will not have a portal locking component\n            and will therefore not be lockable.\n            ', tunable=PortalLockingComponent.TunableFactory()), '_portal_disallowed_tags': TunableTags(description='\n            A set of tags used to prevent Sims in particular role states from\n            using this portal.\n            ', filter_prefixes=tag.PORTAL_DISALLOWANCE_PREFIX)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._portals = {}
        self._custom_portals = None
        self._enable_refresh = True

    def get_subcomponents_gen(self):
        yield from super().get_subcomponents_gen()
        if self._portal_locking_component is not None:
            portal_locking_component = self._portal_locking_component(self.owner)
            yield from portal_locking_component.get_subcomponents_gen()
        if self._portal_animation_component is not None:
            portal_animation_component = self._portal_animation_component(self.owner)
            yield from portal_animation_component.get_subcomponents_gen()

    @property
    def refresh_enabled(self):
        return self._enable_refresh

    @refresh_enabled.setter
    def refresh_enabled(self, value):
        self._enable_refresh = bool(value)

    def on_buildbuy_exit(self, *_, **__):
        self._refresh_portals()

    def on_location_changed(self, *_, **__):
        zone = services.current_zone()
        if zone.is_in_build_buy or zone.is_zone_loading:
            return
        self._refresh_portals()

    def finalize_portals(self):
        self._refresh_portals()

    def _refresh_portals(self):
        if self.refresh_enabled:
            self._remove_portals()
            self._add_portals()
            self.owner.refresh_locks()

    def on_add(self, *_, **__):
        services.object_manager().add_portal_to_cache(self.owner)

    def on_remove(self, *_, **__):
        self._remove_portals()
        services.object_manager().remove_portal_from_cache(self.owner)

    @componentmethod
    @sims4.utils.exception_protected(default_return=0)
    def c_api_get_portal_duration(self, portal_id, walkstyle, age, gender, species):
        portal = self._portals.get(portal_id)
        if portal is not None:
            return portal.get_portal_duration(portal_id, walkstyle, age, gender, species)
        return 0

    @componentmethod
    def add_portal_data(self, portal_id, actor, walkstyle):
        portal = self._portals.get(portal_id)
        if portal is not None:
            return portal.add_portal_data(portal_id, actor, walkstyle)

    @componentmethod
    def split_path_on_portal(self, portal_id):
        portal = self._portals.get(portal_id)
        if portal is not None:
            return portal.split_path_on_portal()
        return PathSplitType.PathSplitType_DontSplit

    @componentmethod
    def get_posture_change(self, portal_id, initial_posture):
        portal = self._portals.get(portal_id)
        if portal is not None:
            return portal.get_posture_change(portal_id, initial_posture)
        return (initial_posture, initial_posture)

    @componentmethod
    def provide_route_events(self, portal_id, route_event_context, sim, path, **kwargs):
        if portal_id in self._portals:
            portal = self._portals.get(portal_id)
            return portal.provide_route_events(portal_id, route_event_context, sim, path, **kwargs)

    @componentmethod
    def add_portal_events(self, portal_id, actor, time, route_pb):
        portal = self._portals.get(portal_id)
        if portal is not None:
            portal.traversal_type.add_portal_events(portal_id, actor, self.owner, time, route_pb)
            portal.traversal_type.notify_in_use(actor, portal, self.owner)

    @componentmethod
    def get_portal_asm_params(self, portal_id, sim):
        portal = self._portals.get(portal_id)
        if portal is not None:
            return portal.get_portal_asm_params(portal_id, sim)
        return {}

    @componentmethod
    def get_portal_owner(self, portal_id):
        portal = self._portals.get(portal_id)
        if portal is not None:
            return portal.obj
        return self.owner

    @componentmethod
    def get_target_surface(self, portal_id):
        portal = self._portals.get(portal_id)
        if portal is not None:
            return portal.get_target_surface(portal_id)
        return self.owner.routing_surface

    def _add_portals(self):
        for portal_data in self._portal_data:
            self._add_portal_internal(self.owner, portal_data)
        if self.owner.parts is not None:
            for part in self.owner.parts:
                part_definition = part.part_definition
                for portal_data in part_definition.portal_data:
                    self._add_portal_internal(part, portal_data)
        if self._custom_portals is not None:
            for (location_point, portal_data, mask, _) in self._custom_portals:
                self._add_portal_internal(location_point, portal_data, mask)

    def _add_portal_internal(self, obj, portal_data, portal_creation_mask=None):
        portal_instance_ids = []
        for portal in portal_data.get_portal_instances(obj, portal_creation_mask):
            if portal.there is not None:
                self._portals[portal.there] = portal
                portal_instance_ids.append(portal.there)
            if portal.back is not None:
                self._portals[portal.back] = portal
                portal_instance_ids.append(portal.back)
        return portal_instance_ids

    def _remove_portal_internal(self, portal_id):
        if portal_id in self._portals:
            remove_portal(portal_id)
            portal = self._portals[portal_id]
            if portal.there is not None and portal.there == portal_id:
                portal.there = None
            elif portal.back == portal_id:
                portal.back = None
            del self._portals[portal_id]

    def _remove_portals(self):
        for portal_id in self._portals:
            remove_portal(portal_id)
        self._portals.clear()
        if self._custom_portals is not None:
            self._custom_portals.clear()
            self._custom_portals = None

    @componentmethod_with_fallback(lambda *_, **__: False)
    def has_portals(self, check_parts=True):
        if self._portal_data or self._custom_portals:
            return True
        elif check_parts and self.owner.parts is not None:
            return any(part.part_definition is not None and part.part_definition.portal_data is not None for part in self.owner.parts)
        return False

    @componentmethod_with_fallback(lambda *_, **__: [])
    def get_portal_pairs(self):
        return set(_PortalPair(portal.there, portal.back) for portal in self._portals.values())

    @componentmethod_with_fallback(lambda *_, **__: None)
    def get_portal_data(self):
        return self._portal_data

    @componentmethod
    def get_portal_instances(self):
        return frozenset(self._portals.values())

    @componentmethod
    def get_portal_type(self, portal_id):
        portal = self._portals.get(portal_id)
        if portal is not None:
            return portal.portal_type
        return PortalType.PortalType_Animate

    @componentmethod
    def update_portal_cache(self, portal, portal_id):
        self._portals[portal_id] = portal

    @componentmethod_with_fallback(lambda *_, **__: None)
    def get_portal_by_id(self, portal_id):
        return self._portals.get(portal_id, None)

    @componentmethod_with_fallback(lambda *_, **__: ())
    def get_dynamic_portal_locations_gen(self):
        for portal_data in self._portal_data:
            yield from portal_data.get_dynamic_portal_locations_gen(self.owner)

    @componentmethod
    def get_single_portal_locations(self):
        portal_pair = next(iter(self._portals.values()), None)
        if portal_pair is not None:
            portal_there = self.get_portal_by_id(portal_pair.there)
            portal_back = self.get_portal_by_id(portal_pair.back)
            front_location = None
            if portal_there is not None:
                front_location = portal_there.there_entry
            back_location = None
            if portal_back is not None:
                back_location = portal_back.back_entry
            return (front_location, back_location)
        return (None, None)

    @componentmethod
    def set_portal_cost_override(self, portal_id, cost, sim=None):
        portal = self._portals.get(portal_id)
        if portal is not None:
            portal.set_portal_cost_override(cost, sim=sim)

    @componentmethod
    def get_portal_cost(self, portal_id):
        portal = self._portals.get(portal_id)
        if portal is not None:
            return portal.get_portal_cost(portal_id)

    @componentmethod
    def get_portal_cost_override(self, portal_id):
        portal = self._portals.get(portal_id)
        if portal is not None:
            return portal.get_portal_cost_override()

    @componentmethod_with_fallback(lambda *_, **__: True)
    def lock_portal_on_use(self, portal_id):
        portal = self._portals.get(portal_id)
        if portal is not None:
            return portal.lock_portal_on_use
        return True

    @componentmethod
    def clear_portal_cost_override(self, portal_id, sim=None):
        portal = self._portals.get(portal_id)
        if portal is not None:
            portal.clear_portal_cost_override(sim=sim)

    @componentmethod
    def is_ungreeted_sim_disallowed(self):
        return any(p.is_ungreeted_sim_disallowed() for p in self._portals.values())

    @componentmethod
    def get_portal_disallowed_tags(self):
        return self._portal_disallowed_tags

    @componentmethod
    def get_entry_clothing_change(self, interaction, portal_id, **kwargs):
        portal = self._portals.get(portal_id)
        if portal is not None:
            return portal.get_entry_clothing_change(interaction, portal_id, **kwargs)

    @componentmethod
    def get_exit_clothing_change(self, interaction, portal_id, **kwargs):
        portal = self._portals.get(portal_id)
        if portal is not None:
            return portal.get_exit_clothing_change(interaction, portal_id, **kwargs)

    @componentmethod
    def get_on_entry_outfit(self, interaction, portal_id, **kwargs):
        portal = self._portals.get(portal_id)
        if portal is not None:
            return portal.get_on_entry_outfit(interaction, portal_id, **kwargs)

    @componentmethod
    def get_on_exit_outfit(self, interaction, portal_id, **kwargs):
        portal = self._portals.get(portal_id)
        if portal is not None:
            return portal.get_on_exit_outfit(interaction, portal_id, **kwargs)

    @componentmethod
    def get_gsi_portal_items_list(self, key_name, value_name):
        gsi_portal_items = self.owner.get_gsi_portal_items(key_name, value_name)
        return gsi_portal_items

    @componentmethod
    def get_nearest_posture_change(self, sim):
        shortest_dist = sims4.math.MAX_FLOAT
        nearest_portal_id = None
        nearest_portal = None
        sim_position = sim.position
        for (portal_id, portal_instance) in self._portals.items():
            (posture_entry, posture_exit) = portal_instance.get_posture_change(portal_id, None)
            if posture_entry is posture_exit:
                pass
            else:
                (entry_loc, _) = portal_instance.get_portal_locations(portal_id)
                dist = (entry_loc.position - sim_position).magnitude_squared()
                if not nearest_portal is None:
                    if shortest_dist > dist:
                        shortest_dist = dist
                        nearest_portal = portal_instance
                        nearest_portal_id = portal_id
                shortest_dist = dist
                nearest_portal = portal_instance
                nearest_portal_id = portal_id
        if nearest_portal is None:
            return (None, None)
        return nearest_portal.get_posture_change(nearest_portal_id, None)

    @componentmethod_with_fallback(lambda *_, **__: False)
    def has_posture_portals(self):
        for (portal_id, portal_instance) in self._portals.items():
            (posture_entry, _) = portal_instance.get_posture_change(portal_id, None)
            if posture_entry is not None:
                return True

    def add_custom_portal(self, location_point, portal_data, portal_creation_mask=None):
        portal_ids = self._add_portal_internal(location_point, portal_data, portal_creation_mask)
        if portal_ids:
            if self._custom_portals is None:
                self._custom_portals = []
            self._custom_portals.append((location_point, portal_data, portal_creation_mask, portal_ids))
        return portal_ids

    def remove_custom_portals(self, portal_ids):
        if self._custom_portals is None:
            return
        for custom_portal in list(self._custom_portals):
            (location_point, portal_data, mask, custom_portal_ids) = custom_portal
            portal_ids_to_remove = []
            if all(custom_portal_id in portal_ids for custom_portal_id in custom_portal_ids):
                self._custom_portals.remove(custom_portal)
                portal_ids_to_remove = custom_portal_ids
            else:
                portal_ids_to_remove = [custom_portal_id for custom_portal_id in custom_portal_ids if custom_portal_id in portal_ids]
                if portal_ids_to_remove:
                    portal_ids_to_keep = [custom_portal_id for custom_portal_id in custom_portal_ids if custom_portal_id not in portal_ids_to_remove]
                    self._custom_portals.remove(custom_portal)
                    self._custom_portals.append((location_point, portal_data, mask, portal_ids_to_keep))
            for portal_id in portal_ids_to_remove:
                self._remove_portal_internal(portal_id)
        if not self._custom_portals:
            self._custom_portals = None

    def clear_custom_portals(self):
        if self._custom_portals is not None:
            portal_ids_to_remove = [portal_id for custom_portal in self._custom_portals for portal_id in custom_portal[3]]
            self.remove_custom_portals(portal_ids_to_remove)
            self._custom_portals.clear()
            self._custom_portals = None

    def get_vehicles_nearby_portal_id(self, portal_id):
        object_manager = services.object_manager()
        owner_position = Vector3Immutable(self.owner.position.x, 0, self.owner.position.z)
        portal_inst = self.get_portal_by_id(portal_id)
        if portal_inst is None:
            return []
        if portal_inst.portal_template.use_vehicle_after_traversal is None:
            return []
        target_surface = portal_inst.get_target_surface(portal_id)
        results = []
        portal_vehicle_tuning = portal_inst.portal_template.use_vehicle_after_traversal
        for vehicle in object_manager.get_objects_with_tags_gen(*portal_vehicle_tuning.vehicle_tags):
            if vehicle.routing_surface.type != target_surface.type:
                pass
            else:
                vehicle_position = Vector3Immutable(vehicle.position.x, 0, vehicle.position.z)
                distance = (owner_position - vehicle_position).magnitude_squared()
                if distance > portal_inst.portal_template.use_vehicle_after_traversal.max_distance:
                    pass
                else:
                    results.append(vehicle)
        return results

    def get_portal_location_by_type(self, portal_type, portal_direction, portal_location):
        portal_pairs = self.get_portal_pairs()
        for (portal_there, portal_back) in portal_pairs:
            if portal_there is None and portal_back is None:
                pass
            else:
                there_instance = self.get_portal_by_id(portal_there)
                if there_instance.portal_template is portal_type.value:
                    location = self._get_desired_location(portal_there, portal_back, portal_direction, portal_location)
                    if location is None:
                        pass
                    else:
                        return location

    def _get_desired_location(self, portal_there_id, portal_back_id, portal_direction, portal_location):
        if portal_direction == PortalComponent.PORTAL_DIRECTION_THERE:
            portal_instance = self.get_portal_by_id(portal_there_id)
        else:
            if portal_back_id is None:
                return
            portal_instance = self.get_portal_by_id(portal_back_id)
            if portal_instance is None:
                return
        location = portal_instance.there_entry if portal_location == PortalComponent.PORTAL_LOCATION_ENTRY else portal_instance.there_exit
        return location
