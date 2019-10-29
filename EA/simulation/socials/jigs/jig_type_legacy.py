from routing import FootprintTypefrom sims4.geometry import PolygonFootprintfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, OptionalTunable, TunableEnumEntryfrom socials.jigs.jig_reserved_space import TunableReservedSpacePerSpeciesfrom socials.jigs.jig_utils import JigPositioning, get_default_reserve_space, get_sims3_social_distance, generate_jig_polygon, _generate_poly_pointsimport sims4.math
class SocialJigLegacy(AutoFactoryInit, HasTunableSingletonFactory):
    FACTORY_TUNABLES = {'reserve_space_per_species': OptionalTunable(TunableReservedSpacePerSpecies(description='\n                The reserved space for this Actor is variable based on the\n                species. You can tune any species to an exact value you\n                want, and there are defaults for each species if nothing is\n                tuned that will cover them.\n                ')), 'jig_positioning_type': TunableEnumEntry(description='\n            Determines the type of positioning used for this Jig.\n            ', tunable_type=JigPositioning, default=JigPositioning.RelativeToSimB)}

    def get_reserved_spaces(self, actor, target):
        reserved_space_a = None
        reserved_space_b = None
        if self.reserve_space_per_species is not None:
            if actor.species in self.reserve_space_per_species:
                reserved_space_a = self.reserve_space_per_species[actor.species]
            if target.species in self.reserve_space_per_species:
                reserved_space_b = self.reserve_space_per_species[target.species]
        if reserved_space_a is None:
            reserved_space_a = get_default_reserve_space(actor.species, actor.age)
        if reserved_space_b is None:
            reserved_space_b = get_default_reserve_space(target.species, target.age)
        return (reserved_space_a, reserved_space_b)

    def get_transforms_gen(self, actor, target, fallback_routing_surface=None, fgl_kwargs=None, **kwargs):
        (reserved_space_a, reserved_space_b) = self.get_reserved_spaces(actor, target)
        offset = get_sims3_social_distance(actor.species, actor.age, target.species, target.age)
        fgl_kwargs = fgl_kwargs if fgl_kwargs is not None else {}
        ignored_objects = {actor.id, target.id}
        ignored_ids = fgl_kwargs.get('ignored_object_ids')
        if ignored_ids is not None:
            ignored_objects.update(ignored_ids)
        fgl_kwargs['ignored_object_ids'] = ignored_objects
        (translation_a, orientation_a, translation_b, orientation_b, routing_surface) = generate_jig_polygon(actor.location, sims4.math.Vector2.ZERO(), 0, target.location, sims4.math.Vector2(0, offset), sims4.math.PI, reserved_space_a.left, reserved_space_a.right, reserved_space_a.front, reserved_space_a.back, reserved_space_b.left, reserved_space_b.right, reserved_space_b.front, reserved_space_b.back, positioning_type=self.jig_positioning_type, fallback_routing_surface=fallback_routing_surface, **fgl_kwargs)
        if translation_a is not None:
            yield (sims4.math.Transform(translation_a, orientation_a), sims4.math.Transform(translation_b, orientation_b), routing_surface, ())

    def get_footprint_polygon(self, sim_a, sim_b, sim_a_transform, sim_b_transform, routing_surface):
        (reserved_space_a, reserved_space_b) = self.get_reserved_spaces(sim_a, sim_b)
        polygon = _generate_poly_points(sim_a_transform.translation, sim_a_transform.orientation.transform_vector(sims4.math.Vector3.Z_AXIS()), sim_b_transform.translation, sim_b_transform.orientation.transform_vector(sims4.math.Vector3.Z_AXIS()), reserved_space_a.left, reserved_space_a.right, reserved_space_a.front, reserved_space_a.back, reserved_space_b.left, reserved_space_b.right, reserved_space_b.front, reserved_space_b.back)
        return PolygonFootprint(polygon, routing_surface=sim_a.routing_surface, cost=25, footprint_type=FootprintType.FOOTPRINT_TYPE_OBJECT, enabled=True)
