import routingimport servicesimport sims4.resourcesfrom routing import SurfaceTypefrom routing.portals.portal_tuning import PortalFlagsfrom sims4.tuning.tunable import TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, TunableSet, TunableEnumEntry, TunableEnumFlags, TunableReferencefrom tag import Tagfrom tunable_utils.tunable_whitelist import TunableWhitelist
class TunableObjectFilterVariant(TunableVariant):

    class _FilterByTags(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'tags': TunableSet(description='\n                The object must have any of these tags in order to satisfy the\n                requirement.\n                ', tunable=TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,), pack_safe=True), minlength=1)}

        def is_object_valid(self, obj):
            if not hasattr(obj, 'has_any_tag'):
                return False
            elif not obj.has_any_tag(self.tags):
                return False
            return True

    class _FilterBySim(HasTunableSingletonFactory, AutoFactoryInit):

        def is_object_valid(self, obj):
            return obj.is_sim

    class _FilterByTerrain(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'disallowed_surfaces': TunableSet(description='\n                Routing surfaces where the placement of this object should\n                fail.\n                ', tunable=TunableEnumEntry(tunable_type=SurfaceType, default=SurfaceType.SURFACETYPE_POOL, invalid_enums=(SurfaceType.SURFACETYPE_UNKNOWN,)))}

        def is_object_valid(self, obj):
            if not obj.is_terrain:
                return False
            routing_surface = obj.routing_surface
            if routing_surface.type in self.disallowed_surfaces:
                return False
            elif not routing.test_point_placement_in_navmesh(routing_surface, obj.position):
                return False
            return True

    class _FilterByPortalFlags(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'portal_flags': TunableEnumFlags(description='\n                The object must have any of these portal flags in order to\n                satisfy the requirement.\n                ', enum_type=PortalFlags)}

        def is_object_valid(self, obj):
            if getattr(obj, 'parts', None):
                return any(self.is_object_valid(part.part_definition) for part in obj.parts)
            surface_portal_constraint = getattr(obj, 'surface_portal_constraint', None)
            if surface_portal_constraint is None:
                return False
            if surface_portal_constraint.required_portal_flags is None:
                return False
            return surface_portal_constraint.required_portal_flags & self.portal_flags

    class _FilterByState(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'states': TunableWhitelist(description='\n                The required states to pass this test.\n                ', tunable=TunableReference(description='\n                    The state value.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',), pack_safe=True))}

        def is_object_valid(self, obj):
            if obj.state_component is None:
                return False
            return self.states.test_collection(set(obj.state_component.values()))

    class _FilterAllowAll(HasTunableSingletonFactory, AutoFactoryInit):

        def is_object_valid(self, obj):
            return True

    FILTER_ALL = 'allow_all'
    FILTER_SIM = 'filter_by_sim'

    def __init__(self, *args, default=FILTER_SIM, **kwargs):
        super().__init__(*args, filter_by_sim=TunableObjectFilterVariant._FilterBySim.TunableFactory(), filter_by_tags=TunableObjectFilterVariant._FilterByTags.TunableFactory(), filter_by_terrain=TunableObjectFilterVariant._FilterByTerrain.TunableFactory(), filter_by_portal_flags=TunableObjectFilterVariant._FilterByPortalFlags.TunableFactory(), filter_by_state=TunableObjectFilterVariant._FilterByState.TunableFactory(), allow_all=TunableObjectFilterVariant._FilterAllowAll.TunableFactory(), default=default, **kwargs)
