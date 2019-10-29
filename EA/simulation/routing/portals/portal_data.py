from weakref import WeakKeyDictionaryfrom sims4.tuning.geometric import TunableDistanceSquaredfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, OptionalTunable, TunableRange, TunableVariant, TunableEnumFlags, TunableTuple, Tunablefrom singletons import DEFAULTimport sims4from routing import add_portal, update_portal_costfrom routing.portals.portal_cost import TunablePortalCostVariantfrom routing.portals.portal_data_animation import _PortalTypeDataAnimationfrom routing.portals.portal_data_dynamic import _PortalTypeDataDynamicfrom routing.portals.portal_data_dynamic_stairs import _PortalTypeDataDynamicStairsfrom routing.portals.portal_data_elevator import _PortalTypeDataElevatorfrom routing.portals.portal_data_locomotion import _PortalTypeDataLocomotionfrom routing.portals.portal_data_ocean_ladders import _PortalTypeDataOceanLaddersfrom routing.portals.portal_data_posture import _PortalTypeDataPosturefrom routing.portals.portal_data_stairs import _PortalTypeDataStairsfrom routing.portals.portal_data_teleport import _PortalTypeDataTeleportfrom routing.portals.portal_data_variable_jump import _PortalTypeDataVariableJumpfrom routing.portals.portal_tuning import PortalTuning, PortalFlagsfrom snippets import define_snippetfrom tag import TunableTagsimport placementimport serviceslogger = sims4.log.Logger('Portal', default_owner='shouse')
class _Portal(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'traversal_cost': TunablePortalCostVariant(description='\n            Define how expensive it is, in meters, to traverse this portal.\n            '), 'traversal_type': TunableVariant(description='\n            Define the type of traversal for this portal.\n            ', locomotion=_PortalTypeDataLocomotion.TunableFactory(), animation=_PortalTypeDataAnimation.TunableFactory(), variable_jump=_PortalTypeDataVariableJump.TunableFactory(), dynamic_jump=_PortalTypeDataDynamic.TunableFactory(), teleport=_PortalTypeDataTeleport.TunableFactory(), posture_change=_PortalTypeDataPosture.TunableFactory(), stairs=_PortalTypeDataStairs.TunableFactory(), dynamic_stairs=_PortalTypeDataDynamicStairs.TunableFactory(), elevator=_PortalTypeDataElevator.TunableFactory(), ocean_ladder=_PortalTypeDataOceanLadders.TunableFactory(), default='locomotion'), 'required_flags': OptionalTunable(description='\n            If specified, only actors with a routing context that match\n            the required flags are allowed to traverse the portal.\n            ', tunable=TunableEnumFlags(description='\n                Required flags for this portal.\n                ', enum_type=PortalFlags)), 'discouragement_flags': OptionalTunable(description="\n            If specified, only actors that have a routing context that doesn't \n            match these flags, will be discouraged from traversing through\n            the portal.\n            ", tunable=TunableEnumFlags(description='\n                Discouragement flags for this portal.\n                ', enum_type=PortalFlags)), 'usage_penalty': OptionalTunable(description='\n            If specified, the cost of this portal increases any time a Sim uses\n            it. This encourages other Sims to use different portals.\n            ', tunable=TunableRange(tunable_type=float, default=1, minimum=0, maximum=9999), enabled_name='Usage_Penalty', disabled_name='No_Usage_Penalty', disabled_value=-1), 'use_vehicle_after_traversal': OptionalTunable(description='\n            When enabled allows this object to act as a sort of docking location\n            for vehicles (like the water scooter).\n            ', tunable=TunableTuple(description='\n                The data to specify which vehicles this portal supports and\n                at what distance.\n                ', vehicle_tags=TunableTags(description='\n                    A list of tags used to identify vehicle objects.\n                    '), max_distance=TunableDistanceSquared(description='\n                    The max distance a vehicle can be away from the portal\n                    and still be considered\n                    ', default=15.0))), 'allow_teleport_style_interaction_to_skip_portal': Tunable(description='\n            If true, a Sim can skip the portal when using a teleport style.  \n            If false, a Sim must use the portal rather than teleporting past it.\n            ', tunable_type=bool, default=True)}

    class _PortalInstance:
        INVALID_PORTAL_ID = 4294967295
        __slots__ = ('there', 'portal_template', 'there_exit', 'back_entry', 'obj', 'back', 'there_entry', 'back_exit', 'there_cost', 'back_cost', '_cost_override', '_cost_override_map')

        def __init__(self, portal_template, obj, there, back, there_entry, there_exit, there_cost, back_entry, back_exit, back_cost):
            self.portal_template = portal_template
            self.obj = obj
            self.there = there
            self.back = back
            self.there_entry = there_entry
            self.there_exit = there_exit
            self.back_entry = back_entry
            self.back_exit = back_exit
            self.there_cost = there_cost
            self.back_cost = back_cost
            self._cost_override = None
            self._cost_override_map = None

        @property
        def portal_type(self):
            return self.traversal_type.portal_type

        @property
        def traversal_type(self):
            return self.portal_template.traversal_type

        @property
        def outfit_change(self):
            return self.traversal_type.outfit_change

        def swap_there_and_back(self):
            self.there = self.back
            self.back = self.there
            self.there_entry = self.back_entry
            self.back_entry = self.there_entry
            self.there_exit = self.back_exit
            self.back_exit = self.there_exit
            self.there_cost = self.back_cost
            self.back_cost = self.there_cost

        def split_path_on_portal(self):
            return self.traversal_type.split_path_on_portal()

        def add_portal_data(self, portal_id, actor, *args, **kwargs):
            is_mirrored = True if portal_id == self.back else False
            return self.traversal_type.add_portal_data(actor, self, is_mirrored, *args, **kwargs)

        def get_portal_locations(self, portal_id):
            if portal_id == self.there:
                return (self.there_entry, self.there_exit)
            elif portal_id == self.back:
                return (self.back_entry, self.back_exit)
            return (None, None)

        def get_portal_duration(self, portal_id, *args, **kwargs):
            is_mirrored = True if portal_id == self.back else False
            return self.traversal_type.get_portal_duration(self, is_mirrored, *args, **kwargs)

        def get_posture_change(self, portal_id, initial_posture):
            is_mirrored = True if portal_id == self.back else False
            return self.traversal_type.get_posture_change(self, is_mirrored, initial_posture)

        def provide_route_events(self, portal_id, route_event_context, sim, path, **kwargs):
            is_mirrored = True if portal_id == self.back else False
            return self.traversal_type.provide_route_events(route_event_context, sim, path, is_mirrored=is_mirrored, **kwargs)

        def get_portal_asm_params(self, portal_id, sim):
            return self.traversal_type.get_portal_asm_params(self, portal_id, sim)

        def get_target_surface(self, portal_id):
            if portal_id == self.back:
                return self.back_exit.routing_surface
            return self.there_exit.routing_surface

        def get_portal_cost(self, portal_id):
            if portal_id == self.back:
                return self.back_cost
            return self.there_cost

        def get_portal_cost_override(self):
            cost = None
            if self._cost_override_map:
                cost = max(self._cost_override_map.values())
            if self._cost_override is not None:
                cost = max(cost or 0, self._cost_override)
            return cost

        @property
        def lock_portal_on_use(self):
            return self.traversal_type.lock_portal_on_use

        def set_portal_cost_override(self, cost, sim=None):
            if sim is None:
                self._cost_override = cost
                sim_override_cost = 0
            else:
                if self._cost_override_map is None:
                    self._cost_override_map = WeakKeyDictionary()
                sim_override_cost = self.get_portal_cost_override() or 0
                self._cost_override_map[sim] = cost
            self._refresh_portal_cost(sim=sim, sim_override_cost=sim_override_cost)

        def clear_portal_cost_override(self, sim=None):
            if sim is None:
                self._cost_override = None
            else:
                del self._cost_override_map[sim]
                if not self._cost_override_map:
                    self._cost_override_map = None
            self._refresh_portal_cost(sim=sim)

        def _refresh_portal_cost(self, sim=None, sim_override_cost=None):
            if sim is not None:
                routing_context = sim.get_routing_context()
                sim_cost = self._cost_override_map.get(sim) if self._cost_override_map is not None else None
            else:
                routing_context = None
                sim_cost = None
            portal_cost_override = self.get_portal_cost_override()

            def refresh_cost(portal_id):
                cost = self.get_portal_cost(portal_id) if portal_cost_override is None else portal_cost_override
                if sim_cost is not None and sim_override_cost is not None:
                    routing_context.override_portal_cost(portal_id, sim_override_cost)
                update_portal_cost(portal_id, cost)
                if sim is not None and sim_cost is None:
                    routing_context.clear_override_portal_cost(portal_id)

            if self.there:
                refresh_cost(self.there)
            if self.back:
                refresh_cost(self.back)

        def is_ungreeted_sim_disallowed(self):
            return self.traversal_type.is_ungreeted_sim_disallowed()

        def get_entry_clothing_change(self, interaction, portal_id, **kwargs):
            if self.outfit_change is None:
                return
            if portal_id == self.back:
                return
            return self.outfit_change.get_on_entry_change(interaction, **kwargs)

        def get_exit_clothing_change(self, interaction, portal_id, **kwargs):
            if self.outfit_change is None:
                return
            if portal_id == self.there:
                return
            return self.outfit_change.get_on_exit_change(interaction, **kwargs)

        def get_on_entry_outfit(self, interaction, portal_id, **kwargs):
            if self.outfit_change is None:
                return
            if portal_id == self.back:
                return
            return self.outfit_change.get_on_entry_outfit(interaction, **kwargs)

        def get_on_exit_outfit(self, interaction, portal_id, **kwargs):
            if self.outfit_change is None:
                return
            if portal_id == self.there:
                return
            return self.outfit_change.get_on_exit_outfit(interaction, **kwargs)

    def _validate_portal_positions(self, obj_ids_to_ignore, entry_location, exit_location):
        if self.traversal_type.requires_los_between_points:
            start = sims4.math.Vector3(entry_location.position.x, entry_location.position.y + PortalTuning.SURFACE_PORTAL_HEIGH_OFFSET, entry_location.position.z)
            end = sims4.math.Vector3(exit_location.position.x, exit_location.position.y + PortalTuning.SURFACE_PORTAL_HEIGH_OFFSET, exit_location.position.z)
            if placement.ray_intersects_placement_3d(services.current_zone_id(), start, end, objects_to_ignore=obj_ids_to_ignore):
                return False
        return True

    def get_portal_instances(self, obj, portal_creation_mask=None):
        tuned_allowed_key_mask = int(self.required_flags) if self.required_flags is not None else 0
        discouraged_key_mask = int(self.discouragement_flags) if self.discouragement_flags is not None else 0
        portal_instances = []
        portal_base_object = obj
        if hasattr(obj, 'proxied_obj'):
            portal_base_object = obj.proxied_obj if not obj.proxied_obj.parts else obj
        base_object_is_proxy = portal_base_object is not obj
        obj_ids_to_ignore = [obj.id] + services.object_manager().get_objects_to_ignore_portal_validation_cache()
        for (there_entry, there_exit, back_entry, back_exit, additional_required_flags) in self.traversal_type.get_portal_locations(portal_base_object):
            if portal_creation_mask is not None and portal_creation_mask & additional_required_flags == 0:
                pass
            else:
                if base_object_is_proxy:
                    for location in (there_entry, there_exit, back_entry, back_exit):
                        if location is not None:
                            transform = location.transform
                            diff_transform = sims4.math.get_difference_transform(portal_base_object.transform, transform)
                            location.transform = sims4.math.Transform.concatenate(diff_transform, obj.transform)
                if not all(location is None or location.routing_surface.valid for location in (there_entry, there_exit, back_entry, back_exit)):
                    pass
                elif not self._validate_portal_positions(obj_ids_to_ignore, there_entry, there_exit):
                    pass
                else:
                    allowed_key_mask = tuned_allowed_key_mask | additional_required_flags

                    def _add_portal_instance_id(portal_entry, portal_exit, debug_name):
                        if portal_entry is not None and portal_exit is not None:
                            cost = self.traversal_cost(portal_entry, portal_exit)
                            portal_id = add_portal(portal_entry, portal_exit, self.traversal_type.portal_type, obj.id, cost, allowed_key_mask, self.usage_penalty, discouraged_key_mask)
                            if portal_id == _Portal._PortalInstance.INVALID_PORTAL_ID:
                                logger.error('_PortalInstance: {} failed add_portal {} portal instance {}, {}, {}', obj, debug_name, portal_entry, portal_exit, self.traversal_type.portal_type)
                                portal_id = None
                                cost = None
                            elif portal_id is None:
                                logger.error('_PortalInstance: {} bad args for add_portal {} portal instance - args: {}', obj, debug_name, (portal_entry, portal_exit, self.traversal_type.portal_type, obj.id, cost, allowed_key_mask, self.usage_penalty, discouraged_key_mask))
                                portal_id = None
                                cost = None
                        else:
                            portal_id = None
                            cost = None
                        return (portal_id, cost)

                    (there, there_cost) = _add_portal_instance_id(there_entry, there_exit, debug_name='there')
                    (back, back_cost) = _add_portal_instance_id(back_entry, back_exit, debug_name='back')
                    if not there is not None:
                        if back is not None:
                            portal_instances.append(_Portal._PortalInstance(self, obj, there, back, there_entry, there_exit, there_cost, back_entry, back_exit, back_cost))
                    portal_instances.append(_Portal._PortalInstance(self, obj, there, back, there_entry, there_exit, there_cost, back_entry, back_exit, back_cost))
        return portal_instances

    def get_dynamic_portal_locations_gen(self, *args, **kwargs):
        if isinstance(self.traversal_type, _PortalTypeDataDynamic):
            yield from self.traversal_type.get_dynamic_portal_locations_gen(*args, **kwargs)
(TunablePortalReference, _) = define_snippet('Portal_Data', _Portal.TunableFactory())