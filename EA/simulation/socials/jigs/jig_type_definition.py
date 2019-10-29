from interactions.utils.routing import fgl_and_get_two_person_transforms_for_jigfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableReferenceimport placementimport services
class SocialJigFromDefinition(AutoFactoryInit, HasTunableSingletonFactory):
    FACTORY_TUNABLES = {'jig_definition': TunableReference(description='\n            The jig to use for finding a place to do the social.\n            ', manager=services.definition_manager())}

    def get_transforms_gen(self, actor, target, actor_slot_index=0, target_slot_index=1, stay_outside=False, fallback_routing_surface=None, **kwargs):
        (actor_transform, target_transform, routing_surface) = fgl_and_get_two_person_transforms_for_jig(self.jig_definition, actor, actor_slot_index, target, target_slot_index, stay_outside, fallback_routing_surface=fallback_routing_surface, **kwargs)
        yield (actor_transform, target_transform, routing_surface, ())

    def get_footprint_polygon(self, sim_a, sim_b, sim_a_transform, sim_b_transform, routing_surface):
        return placement.get_placement_footprint_compound_polygon(sim_b_transform.translation, sim_b_transform.orientation, routing_surface, self.jig_definition.get_footprint(0))
