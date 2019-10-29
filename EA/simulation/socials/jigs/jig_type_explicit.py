from routing import FootprintTypefrom sims4.geometry import PolygonFootprintfrom sims4.tuning.geometric import TunableVector2from sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableTuple, TunableAngle, TunableListfrom socials.jigs.jig_reserved_space import TunableReservedSpacefrom socials.jigs.jig_utils import generate_jig_polygon, _generate_poly_pointsimport sims4.math
class SocialJigExplicit(AutoFactoryInit, HasTunableSingletonFactory):

    class TunablePositionAndOrientation(TunableTuple):

        def __init__(self, **kwargs):
            super().__init__(position=TunableVector2(description='\n                    Position of this actor in the scene.\n                    ', default=sims4.math.Vector2.ZERO()), rotation=TunableAngle(description='\n                    Angle of this actor in the scene.\n                    ', default=0), **kwargs)

    FACTORY_TUNABLES = {'actor_a_reserved_space': TunableReservedSpace(description='\n            The clearance required for the actor Sim.\n            '), 'actor_b_reserved_space': TunableReservedSpace(description='\n            The clearance required for the target Sim.\n            '), 'actor_a': TunablePositionAndOrientation(), 'actor_b': TunableList(description='\n            A list of valid positions the target Sim may be in. Only one is\n            ultimately picked.\n            ', tunable=TunablePositionAndOrientation(), minlength=1)}

    def get_transforms_gen(self, actor, target, actor_loc=None, target_loc=None, fallback_routing_surface=None, fgl_kwargs=None, **kwargs):
        ignored_objects = set()
        if actor is not None:
            loc_a = actor.location
            ignored_objects.add(actor.id)
        loc_a = actor_loc
        if actor_loc is not None and target is not None:
            loc_b = target.location
            ignored_objects.add(target.id)
        loc_b = target_loc
        fgl_kwargs = fgl_kwargs if target_loc is not None and fgl_kwargs is not None else {}
        ignored_ids = fgl_kwargs.get('ignored_object_ids')
        if ignored_ids is not None:
            ignored_objects.update(ignored_ids)
        fgl_kwargs['ignored_object_ids'] = ignored_objects
        for actor_b in self.actor_b:
            (translation_a, orientation_a, translation_b, orientation_b, routing_surface) = generate_jig_polygon(loc_a, self.actor_a.position, self.actor_a.rotation, loc_b, actor_b.position, actor_b.rotation, self.actor_a_reserved_space.left, self.actor_a_reserved_space.right, self.actor_a_reserved_space.front, self.actor_a_reserved_space.back, self.actor_b_reserved_space.left, self.actor_b_reserved_space.right, self.actor_b_reserved_space.front, self.actor_b_reserved_space.back, fallback_routing_surface=fallback_routing_surface, **fgl_kwargs)
            if translation_a is None:
                pass
            else:
                yield (sims4.math.Transform(translation_a, orientation_a), sims4.math.Transform(translation_b, orientation_b), routing_surface, ())

    def get_footprint_polygon(self, sim_a, sim_b, sim_a_transform, sim_b_transform, routing_surface):
        polygon = _generate_poly_points(sim_a_transform.translation, sim_a_transform.orientation.transform_vector(sims4.math.Vector3.Z_AXIS()), sim_b_transform.translation, sim_b_transform.orientation.transform_vector(sims4.math.Vector3.Z_AXIS()), self.actor_a_reserved_space.left, self.actor_a_reserved_space.right, self.actor_a_reserved_space.front, self.actor_a_reserved_space.back, self.actor_b_reserved_space.left, self.actor_b_reserved_space.right, self.actor_b_reserved_space.front, self.actor_b_reserved_space.back)
        return PolygonFootprint(polygon, routing_surface=sim_a.routing_surface, cost=25, footprint_type=FootprintType.FOOTPRINT_TYPE_OBJECT, enabled=True)
