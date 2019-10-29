from _weakrefset import WeakSetfrom objects.persistence_groups import PersistenceGroupsfrom sims4.tuning.tunable import TunableSet, TunableEnumEntry, TunableMapping, TunableReference, TunableEnumWithFilterimport objectsimport servicesimport sims4.logimport taglogger = sims4.log.Logger('ObjectManager', default_owner='rmccord')
class AttractorManagerMixin:
    ATTRACTOR_OBJECT_TAGS = TunableSet(description='\n        One or more tags that indicate an object is a type of attractor point.\n        We use attractor points to push Sims near things and reference specific\n        geography in the world.\n        ', tunable=TunableEnumWithFilter(description='\n            A specific tag.\n            ', tunable_type=tag.Tag, default=tag.Tag.INVALID, invalid_enums=(tag.Tag.INVALID,), filter_prefixes=('AtPo',)))
    SPAWN_POINT_ATTRACTORS = TunableMapping(description='\n        Mapping from spawn point tags to attractor objects so we can create\n        attractor points at spawn points.\n        ', key_type=TunableEnumEntry(description='\n            The tag on the spawn point.\n            ', tunable_type=tag.Tag, default=tag.Tag.INVALID, invalid_enums=(tag.Tag.INVALID,)), key_name='spawn point tag', value_type=TunableReference(description='\n            The object we want to create on the Spawn Point.\n            ', manager=services.definition_manager(), pack_safe=True), value_name='attractor point definition')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dynamic_attractor_ids = WeakSet()

    def create_dynamic_attractor_object(self, definition_id, location, tags_to_add=None):
        tags_to_add = set() if tags_to_add is None else tags_to_add

        def setup_obj(obj):
            obj.append_tags(tags_to_add)
            obj.location = location
            obj.persistence_group = PersistenceGroups.NONE

        created_obj = objects.system.create_object(definition_id, init=setup_obj)
        self._dynamic_attractor_ids.add(created_obj)
        if not self.ATTRACTOR_OBJECT_TAGS.intersection(created_obj.get_tags()):
            logger.warn('Attractor object does not have any tags in the ATTRACTOR OBJECT TAGS list. We need to be able to locate attractor objects and keep track of them.')
        return created_obj

    def destroy_dynamic_attractor_object(self, object_id):
        obj_to_destroy = self.get(object_id)
        if obj_to_destroy is None:
            logger.error('Object {} is not a dynamic attractor point.', object_id)
            return
        self._dynamic_attractor_ids.discard(obj_to_destroy)
        obj_to_destroy.destroy(obj_to_destroy, cause='Destroying Dynamic Attractor Point')

    def get_attractor_objects(self):
        return self.get_objects_matching_tags(AttractorManagerMixin.ATTRACTOR_OBJECT_TAGS)

    def create_spawn_point_attractor(self, spawn_point):
        obj_ids = set()
        for (spawn_point_tag, attractor_definition) in self.SPAWN_POINT_ATTRACTORS.items():
            tags = spawn_point.get_tags()
            if spawn_point_tag in tags:
                location = sims4.math.Location(transform=spawn_point.get_approximate_transform(), routing_surface=spawn_point.routing_surface)
                obj = self.create_dynamic_attractor_object(attractor_definition, location, tags_to_add={spawn_point_tag})
                obj_ids.add(obj.id)
        return frozenset(obj_ids)
