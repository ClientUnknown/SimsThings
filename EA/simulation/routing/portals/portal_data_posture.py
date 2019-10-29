from _math import Vector3from animation.animation_utils import StubActorfrom animation.arb import Arbfrom buffs.buff import Bufffrom interactions.constraints import get_global_stub_actor, GLOBAL_STUB_CONTAINERfrom postures.base_postures import MobilePosturefrom postures.posture_specs import get_origin_spec_carry, get_origin_specfrom routing import Locationfrom routing.portals import portal_locationfrom routing.portals.portal_data_base import _PortalTypeDataBasefrom routing.portals.portal_enums import PathSplitTypefrom routing.portals.portal_location import TunableRoutingSurfaceVariant, _PortalLocationfrom routing.portals.portal_tuning import PortalTypefrom sims.outfits.outfit_change import TunableOutfitChangefrom sims.sim_info_types import SpeciesExtendedfrom sims4.tuning.tunable import OptionalTunable, TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, TunableEnumSet, Tunable, TunableMapping, TunableTupleimport posturesimport sims4.logimport terrainlogger = sims4.log.Logger('Portal', default_owner='rmccord')
class _PortalLocationsFromPosture(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'bidirectional': Tunable(description='\n            If checked, a "there" and "back" portal will be created. If\n            unchecked, only a "there" portal is created.\n            ', tunable_type=bool, default=True)}

    def __call__(self, obj, posture, routing_surface_start, routing_surface_end, species_overrides):
        species_portals = []

        def get_outer_portal_goal(slot_constraint, stub_actor, entry, routing_surface):
            handles = slot_constraint.get_connectivity_handles(stub_actor, entry=entry, routing_surface_override=routing_surface)
            if not handles:
                slot_constraint.get_connectivity_handles(stub_actor, entry=entry, routing_surface_override=routing_surface, log_none_slots_to_params_as_error=True)
                logger.error('PosturePortal: Species {} has no entry boundary conditions for portal posture', species)
                return
            species_param = SpeciesExtended.get_animation_species_param(stub_actor.species)
            for handle in handles:
                handle_species_param = handle.locked_params.get(('species', 'x'))
                if handle_species_param is None:
                    break
                if handle_species_param == species_param:
                    break
            return
            return next(iter(handle.get_goals()), None)

        posture_species = posture.get_animation_species()
        for species in species_overrides:
            if species == SpeciesExtended.INVALID:
                pass
            elif SpeciesExtended.get_species(species) not in posture_species:
                pass
            else:
                stub_actor = get_global_stub_actor(species)
                portal_posture = postures.create_posture(posture, stub_actor, obj, is_throwaway=True)
                slot_constraint = portal_posture.slot_constraint
                containment_constraint = next(iter(slot_constraint))
                there_start = get_outer_portal_goal(slot_constraint, stub_actor, entry=True, routing_surface=routing_surface_start)
                if there_start is None:
                    pass
                else:
                    there_end = containment_constraint.containment_transform
                    there_entry = Location(there_start.position, orientation=there_start.orientation, routing_surface=routing_surface_start)
                    there_exit = Location(there_end.translation, orientation=there_end.orientation, routing_surface=routing_surface_end)
                    back_entry = None
                    back_exit = None
                    if self.bidirectional:
                        back_start = containment_constraint.containment_transform_exit
                        back_end = get_outer_portal_goal(slot_constraint, stub_actor, entry=False, routing_surface=routing_surface_start)
                        if back_end is None:
                            pass
                        else:
                            back_entry = Location(back_start.translation, orientation=back_start.orientation, routing_surface=routing_surface_end)
                            back_exit = Location(back_end.position, orientation=back_end.orientation, routing_surface=routing_surface_start)
                            species_portals.append((there_entry, there_exit, back_entry, back_exit, SpeciesExtended.get_portal_flag(species)))
                    species_portals.append((there_entry, there_exit, back_entry, back_exit, SpeciesExtended.get_portal_flag(species)))
        return species_portals

class _PortalLocationsFromTuning(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'location_entry': _PortalLocation.TunableFactory(description='\n            The there entry portal location.\n            ', locked_args={'routing_surface': portal_location.ROUTING_SURFACE_TERRAIN, 'orientation': None}), 'location_exit': _PortalLocation.TunableFactory(description='\n            The there exit portal location.\n            ', locked_args={'routing_surface': portal_location.ROUTING_SURFACE_TERRAIN, 'orientation': None}), 'bidirectional': Tunable(description='\n            If checked, the portal will generate a there and back. If unchecked,\n            only a there portal will be created.\n            ', tunable_type=bool, default=True)}

    def __call__(self, obj, posture, routing_surface_start, routing_surface_end, species_overrides):
        species_portals = []
        posture_species = posture.get_animation_species()
        for species in species_overrides:
            if species == SpeciesExtended.INVALID:
                pass
            elif SpeciesExtended.get_species(species) not in posture_species:
                pass
            else:
                location_entry = self.location_entry(obj).position
                location_exit = self.location_exit(obj).position
                back_entry = None
                back_exit = None
                if self.bidirectional:
                    exit_x_offset = Vector3(location_entry.x - location_exit.x, 0, 0)
                    location_exit = location_exit + exit_x_offset
                    there_angle = sims4.math.vector3_angle(location_exit - location_entry)
                    there_orientation = sims4.math.angle_to_yaw_quaternion(there_angle)
                    there_entry = Location(location_entry, orientation=there_orientation, routing_surface=routing_surface_start)
                    there_exit = Location(location_exit, orientation=there_orientation, routing_surface=routing_surface_end)
                    back_angle = sims4.math.vector3_angle(location_entry - location_exit)
                    back_orientation = sims4.math.angle_to_yaw_quaternion(back_angle)
                    back_entry_position = location_exit + back_orientation.transform_vector(exit_x_offset)
                    back_entry = Location(back_entry_position, orientation=back_orientation, routing_surface=routing_surface_end)
                    back_exit_position = location_entry + back_orientation.transform_vector(exit_x_offset)
                    back_exit = Location(back_exit_position, orientation=back_orientation, routing_surface=routing_surface_start)
                else:
                    there_angle = sims4.math.vector3_angle(location_exit - location_entry)
                    there_orientation = sims4.math.angle_to_yaw_quaternion(there_angle)
                    there_entry = Location(location_entry, orientation=there_orientation, routing_surface=routing_surface_start)
                    there_exit = Location(location_exit, orientation=there_orientation, routing_surface=routing_surface_end)
                species_portals.append((there_entry, there_exit, back_entry, back_exit, SpeciesExtended.get_portal_flag(species)))
        return species_portals

class _PortalTypeDataPosture(_PortalTypeDataBase):
    FACTORY_TUNABLES = {'posture_start': MobilePosture.TunableReference(description='\n            Define the entry posture as you cross through this portal. e.g. For\n            the pool, the start posture is stand.\n            '), 'routing_surface_start': TunableRoutingSurfaceVariant(description="\n            The routing surface of the portal's entry position. Sims are on this\n            surface while in the starting posture.\n            "), 'posture_end': MobilePosture.TunableReference(description='\n            Define the exit posture as you cross through this portal. e.g. For\n            the pool, the end posture is swim.\n            '), 'routing_surface_end': TunableRoutingSurfaceVariant(description="\n            The routing surface of the portal's exit position. Sims are on this\n            surface when in the ending posture.\n            "), '_outfit_change': OptionalTunable(tunable=TunableOutfitChange(description='\n                Define the outfit change that happens when a Sim enters or exits\n                this portal.\n                ')), 'portal_locations': TunableVariant(description='\n            Define the behavior that determines the entry and exit points.\n            ', from_posture=_PortalLocationsFromPosture.TunableFactory(), from_tuning=_PortalLocationsFromTuning.TunableFactory(), default='from_posture'), 'species_overrides': OptionalTunable(description='\n            If enabled, we will override the species we generate these portals\n            for. However, the species are still restricted to those that are\n            supported by the posture. If the species cannot enter the posture,\n            then they will not generate portals.\n            ', tunable=TunableEnumSet(description='\n                The Species we want this portal to support.\n                ', enum_type=SpeciesExtended, enum_default=SpeciesExtended.HUMAN, invalid_enums=SpeciesExtended.INVALID), disabled_value=SpeciesExtended), 'requires_los_between_entry_and_exit': Tunable(description='\n            If checked, this portal will only be valid if there is LOS between\n            the entry and exit points. If unchecked, LOS is not required.\n            ', tunable_type=bool, default=True), 'buff_asm_parameters': TunableMapping(description='\n            A mapping of buffs to parameters to set on the actor in the ASM when \n            traversing this portal.\n            ', key_type=Buff.TunableReference(description='\n                If the Sim has this buff, the corresponding ASM parameters will\n                be set on the ASM for this portal.\n                '), value_type=TunableTuple(description='\n                The parameter name and value to set on the ASM.\n                ', parameter_name=Tunable(description='\n                    The parameter name.\n                    ', tunable_type=str, default=None), parameter_value=Tunable(description='\n                    The value of the parameter if the Sim has the corresponding\n                    buff.\n                    ', tunable_type=str, default=None)))}

    @property
    def portal_type(self):
        return PortalType.PortalType_Animate

    @property
    def outfit_change(self):
        return self._outfit_change

    @property
    def requires_los_between_points(self):
        return self.requires_los_between_entry_and_exit

    def get_portal_duration(self, portal_instance, is_mirrored, walkstyle, age, gender, species):
        stub_actor = StubActor(1, species=species)
        arb = Arb()
        portal_posture = postures.create_posture(self.posture_end, stub_actor, GLOBAL_STUB_CONTAINER)
        source_posture = postures.create_posture(self.posture_start, stub_actor, None)
        portal_posture.append_transition_to_arb(arb, source_posture, locked_params={('age', 'x'): age, 'is_mirrored': is_mirrored})
        (_, duration, _) = arb.get_timing()
        return duration

    def get_posture_change(self, portal_instance, is_mirrored, initial_posture):
        if initial_posture is not None and initial_posture.carry_target is not None:
            start_posture = get_origin_spec_carry(self.posture_start)
            end_posture = get_origin_spec_carry(self.posture_end)
        else:
            start_posture = get_origin_spec(self.posture_start)
            end_posture = get_origin_spec(self.posture_end)
        if is_mirrored:
            return (end_posture, start_posture)
        else:
            return (start_posture, end_posture)

    def split_path_on_portal(self):
        return PathSplitType.PathSplitType_Split

    def get_portal_locations(self, obj):
        routing_surface_start = self.routing_surface_start(obj)
        routing_surface_end = self.routing_surface_end(obj)
        portals = self.portal_locations(obj, self.posture_end, routing_surface_start, routing_surface_end, self.species_overrides)
        return portals

    def get_portal_asm_params(self, portal_instance, portal_id, sim):
        if portal_id == portal_instance.back:
            entry_location = portal_instance.back_entry
            exit_location = portal_instance.back_exit
        else:
            entry_location = portal_instance.there_entry
            exit_location = portal_instance.there_exit
        final_entry_height = terrain.get_terrain_height(entry_location.position.x, entry_location.position.z, entry_location.routing_surface)
        final_entry_position = sims4.math.Vector3(entry_location.position.x, final_entry_height, entry_location.position.z)
        final_exit_height = terrain.get_terrain_height(exit_location.position.x, exit_location.position.z, exit_location.routing_surface)
        final_exit_position = sims4.math.Vector3(exit_location.position.x, final_exit_height, exit_location.position.z)
        params = {('InitialTranslation', 'x'): final_entry_position, ('InitialOrientation', 'x'): entry_location.orientation, ('TargetTranslation', 'x'): final_exit_position, ('TargetOrientation', 'x'): exit_location.orientation}
        if self.buff_asm_parameters:
            for (buff, param) in self.buff_asm_parameters.items():
                if sim.has_buff(buff.buff_type):
                    params.update({(param.parameter_name, 'x'): param.parameter_value})
        return params
