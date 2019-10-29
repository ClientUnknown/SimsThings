from interactions import ParticipantTypeSinglefrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, TunableRange, TunableVariantimport servicesimport sims4.math
class _ObjectGeneratorFromGardening(HasTunableSingletonFactory, AutoFactoryInit):

    class _ObjectTypePlant(HasTunableSingletonFactory, AutoFactoryInit):

        def __call__(self, obj):
            return (obj,)

    class _ObjectTypeHarvestable(HasTunableSingletonFactory, AutoFactoryInit):

        def __call__(self, obj):
            return obj.children

    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The object used as a center point for distance calculations.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), 'distance': TunableRange(description='\n            The distance used to determine which objects are generated.\n            ', tunable_type=float, minimum=sims4.math.EPSILON, default=4), 'object_type': TunableVariant(description='\n            The type of gardening object to return.\n            ', plants=_ObjectTypePlant.TunableFactory(), harvestables=_ObjectTypeHarvestable.TunableFactory(), default='plants')}

    def get_objects(self, resolver, *args, **kwargs):
        center_object = resolver.get_participant(self.participant, *args, **kwargs)
        if center_object is None:
            return ()
        results = []
        gardening_service = services.get_gardening_service()
        for obj in gardening_service.get_gardening_objects(level=center_object.level, center=center_object.position, radius=self.distance):
            results.extend(self.object_type(obj))
        return tuple(results)
