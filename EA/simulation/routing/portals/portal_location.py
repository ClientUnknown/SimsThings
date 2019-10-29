from _animation import get_joint_transform_from_rigfrom _math import Vector3, Quaternionfrom routing import SurfaceIdentifier, SurfaceType, Locationfrom sims4.math import angle_to_yaw_quaternionfrom sims4.tuning.geometric import TunableVector2from sims4.tuning.tunable import HasTunableFactory, OptionalTunable, TunableAngle, TunableVariant, AutoFactoryInit, HasTunableSingletonFactory, TunableEnumEntry, TunableRangefrom sims4.tuning.tunable_hash import TunableStringHash32import servicesimport sims4.resourceslogger = sims4.log.Logger('PortalLocation')ROUTING_SURFACE_TERRAIN = 0ROUTING_SURFACE_OBJECT = 1ROUTING_SURFACE_GLOBAL_OBJECT = 2ROUTING_SURFACE_OCEAN = 3
class _PortalLocationBase(HasTunableFactory, Location):
    FACTORY_TUNABLES = {'routing_surface': TunableVariant(description="\n            Define what surface the point is created on.\n            \n            Terrain: The point is on the ground, on the same level the owning\n            object is on.\n            \n            Object: The point is on the routable surface defined by the object.\n            The point must be within the footprint's bounds.\n            \n            Global object: The point is anywhere on the object routable surface\n            for the level where the object is on. If there is no object that\n            location, the portal is invalid. Use this for objects that connect\n            other objects with routable surfaces.\n            \n            Ocean: The point is in the ocean. Regardless of what level the\n            object is on, we will always assume a surface type of POOL and a\n            level of 0 (which would match the Ocean).\n            ", locked_args={'terrain': ROUTING_SURFACE_TERRAIN, 'object': ROUTING_SURFACE_OBJECT, 'global_object': ROUTING_SURFACE_GLOBAL_OBJECT, 'ocean': ROUTING_SURFACE_OCEAN}, default='terrain')}

    def __init__(self, obj, routing_surface, *args, **kwargs):
        translation = self.get_translation(obj)
        orientation = self.get_orientation(obj)
        if routing_surface == ROUTING_SURFACE_TERRAIN:
            routing_surface = obj.routing_surface
        elif routing_surface == ROUTING_SURFACE_OBJECT:
            routing_surface = obj.provided_routing_surface
        elif routing_surface == ROUTING_SURFACE_GLOBAL_OBJECT:
            routing_surface = SurfaceIdentifier(services.current_zone_id(), obj.routing_surface.secondary_id, SurfaceType.SURFACETYPE_OBJECT)
        elif routing_surface == ROUTING_SURFACE_OCEAN:
            routing_surface = SurfaceIdentifier(services.current_zone_id(), 0, SurfaceType.SURFACETYPE_POOL)
        terrain_object = services.terrain_service.terrain_object()
        translation.y = terrain_object.get_routing_surface_height_at(translation.x, translation.z, routing_surface)
        super().__init__(translation, orientation=orientation, routing_surface=routing_surface)

    def get_translation(self, obj):
        raise NotImplementedError

    def get_orientation(self, obj):
        pass

class _PortalBoneLocation(_PortalLocationBase):
    FACTORY_TUNABLES = {'bone_name': TunableStringHash32(description='\n            The bone to use for this portal location.\n            ')}

    def __init__(self, obj, bone_name, *args, **kwargs):
        self.bone_name = bone_name
        super().__init__(obj, *args, **kwargs)

    def get_translation(self, obj):
        if obj.rig is None or obj.rig == sims4.resources.INVALID_KEY:
            logger.error('Trying to get the translation for a bone {} on obj {} but object has no rig.', self.bone, obj)
        bone_transform = get_joint_transform_from_rig(obj.rig, self.bone_name)
        return obj.transform.transform_point(bone_transform.translation)

class _PortalLocation(_PortalLocationBase):
    FACTORY_TUNABLES = {'translation': TunableVector2(default=TunableVector2.DEFAULT_ZERO), 'orientation': OptionalTunable(description='\n            If enabled, this portal has a specific orientation. If disabled, any\n            orientation is valid.\n            ', tunable=TunableAngle(default=0))}

    def __init__(self, obj, translation, orientation, *args, **kwargs):
        self._translation = translation
        self._orientation = orientation
        super().__init__(obj, *args, **kwargs)

    def get_translation(self, obj):
        return obj.transform.transform_point(Vector3(self._translation.x, 0, self._translation.y))

    def get_orientation(self, obj):
        if self._orientation:
            return Quaternion.concatenate(obj.orientation, angle_to_yaw_quaternion(self._orientation))

class _PortalRoutingSurfaceDefault(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, obj):
        return obj.routing_surface

class _PortalRoutingSurfaceSpecified(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'surface_type': TunableEnumEntry(description='\n            The surface type on which to create the portal.\n            ', tunable_type=SurfaceType, default=SurfaceType.SURFACETYPE_WORLD, invalid_enums=(SurfaceType.SURFACETYPE_UNKNOWN,)), 'level_override': OptionalTunable(description='\n            If enabled, allows this surface to have a level override.\n            ', tunable=TunableRange(description='\n                The level to force this routing surface. This is useful for\n                picking out oceans since they are routing surface type POOL but\n                always on level 0.\n                ', tunable_type=int, default=0, minimum=-3, maximum=5))}

    def __call__(self, obj):
        routing_surface = obj.routing_surface
        level = routing_surface.secondary_id
        if self.level_override is not None:
            level = self.level_override
        return SurfaceIdentifier(routing_surface.primary_id, level, self.surface_type)

class TunableRoutingSurfaceVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, same=_PortalRoutingSurfaceDefault.TunableFactory(), specified=_PortalRoutingSurfaceSpecified.TunableFactory(), default='same', **kwargs)
