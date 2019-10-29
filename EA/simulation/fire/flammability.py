from sims4.tuning.tunable import TunableVariant, HasTunableSingletonFactory, Tunable, AutoFactoryInitimport placementimport sims4.math
class TunableFlammableAreaVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, circle_around_object=DefaultObjectRadialFlammability.TunableFactory(), placement_footprint=ObjectFootprintFlammability.TunableFactory(), default='circle_around_object', **kwargs)

class DefaultObjectRadialFlammability(HasTunableSingletonFactory):

    def get_bounds_for_flammable_object(self, obj, fire_retardant_bonus):
        location = sims4.math.Vector2(obj.position.x, obj.position.z)
        radius = obj.object_radius
        if obj.fire_retardant:
            radius += fire_retardant_bonus
        object_bounds = sims4.geometry.QtCircle(location, radius)
        return object_bounds

class ObjectFootprintFlammability(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'use_largest_polygon': Tunable(description="\n            When set, we use the largest polygon in the object's placement\n            footprint to generate the bounding box area.  Use this for complex\n            footprints with multiple placement polys like the large green screen;\n            if we can rely on the largest polygon as a good base.\n            ", tunable_type=bool, default=False)}

    def get_bounds_for_flammable_object(self, obj, fire_retardant_bonus):
        if self.use_largest_polygon:
            placement_footprint = placement.get_placement_footprint_polygon(obj.position, obj.orientation, obj.routing_surface, obj.get_footprint())
        else:
            placement_footprint = placement.get_accurate_placement_footprint_polygon(obj.position, obj.orientation, obj.scale, obj.get_footprint())
        (lower_bound, upper_bound) = placement_footprint.bounds()
        bounding_box = sims4.geometry.QtRect(sims4.math.Vector2(lower_bound.x, lower_bound.z), sims4.math.Vector2(upper_bound.x, upper_bound.z))
        return bounding_box
