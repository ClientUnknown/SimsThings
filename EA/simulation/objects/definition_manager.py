from _collections import defaultdictimport weakreffrom sims4.tuning.instance_manager import InstanceManagerfrom sims4.tuning.merged_tuning_manager import UnavailablePackSafeResourceErrorfrom sims4.tuning.tunable import TunableList, TunableReferenceimport build_buyimport objects.systemimport pathsimport protocolbuffers.FileSerialization_pb2 as file_serializationimport servicesimport sims4.core_servicesimport sims4.loglogger = sims4.log.Logger('DefinitionManager')
class TunableDefinitionList(TunableList):

    def __init__(self, pack_safe=False, class_restrictions=(), **kwargs):
        super().__init__(TunableReference(description='\n                The definition of the object.\n                ', manager=services.definition_manager(), pack_safe=pack_safe, class_restrictions=class_restrictions), **kwargs)
PROTOTYPE_INSTANCE_ID = 15013
class DefinitionManager(InstanceManager):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._definitions_cache = {}
        self._definitions_tag_cache = defaultdict(list)
        if paths.SUPPORT_RELOADING_RESOURCES:
            self._dependencies = {}

    def on_start(self):
        if paths.SUPPORT_RELOADING_RESOURCES:
            sims4.core_services.file_change_manager().create_set(sims4.resources.Types.OBJECTDEFINITION, sims4.resources.Types.OBJECTDEFINITION)
        super().on_start()
        self.refresh_build_buy_tag_cache(refresh_definition_cache=False)

    def on_stop(self):
        if paths.SUPPORT_RELOADING_RESOURCES:
            sims4.core_services.file_change_manager().remove_set(sims4.resources.Types.OBJECTDEFINITION)
        super().on_stop()

    def get_changed_files(self):
        changed = super().get_changed_files()
        changed.extend(sims4.core_services.file_change_manager().consume_set(sims4.resources.Types.OBJECTDEFINITION))
        return changed

    def get(self, def_id, obj_state=0, pack_safe=False, get_fallback_definition_id=True):
        def_id = int(def_id)
        if get_fallback_definition_id:
            current_zone_id = services.current_zone_id()
            if current_zone_id is not None:
                def_id = build_buy.get_vetted_object_defn_guid(current_zone_id, 0, def_id)
                if def_id is None:
                    return
        key = (def_id, obj_state) if obj_state else def_id
        definition = self._definitions_cache.get(key)
        if definition is not None:
            return definition
        return self._load_definition_and_tuning(def_id, obj_state, pack_safe=pack_safe)

    def get_object_tuning(self, definition_id):
        definition = self.get(definition_id)
        if definition is not None:
            return definition.cls

    @property
    def loaded_definitions(self):
        return self._definitions_cache.values()

    def refresh_build_buy_tag_cache(self, refresh_definition_cache=True):
        for key in sorted(sims4.resources.list(type=sims4.resources.Types.OBJECTDEFINITION)):
            definition = self.get(key.instance, get_fallback_definition_id=False)
            if definition is None:
                logger.error('Definition is None for instance id {}. Key: {}', key.instance, key)
            else:
                definition.assign_build_buy_tags()
        if refresh_definition_cache:
            for definition in self._definitions_cache.values():
                definition.assign_build_buy_tags()

    def register_definition(self, def_id, interested_party):
        if paths.SUPPORT_RELOADING_RESOURCES:
            objects_with_def = self._dependencies.get(def_id)
            if objects_with_def is None:
                objects_with_def = weakref.WeakSet()
                self._dependencies[def_id] = objects_with_def
            objects_with_def.add(interested_party)

    def unregister_definition(self, def_id, interested_party):
        if paths.SUPPORT_RELOADING_RESOURCES:
            objects_with_def = self._dependencies.get(def_id)
            if objects_with_def is not None:
                objects_with_def.remove(interested_party)
                if not objects_with_def:
                    del self._dependencies[def_id]

    def get_definitions_for_tags_gen(self, tag_set):
        key = tuple(sorted(tag_set))
        if key not in self._definitions_tag_cache:
            for definition in self.loaded_definitions:
                if definition.has_build_buy_tag(*tag_set):
                    self._definitions_tag_cache[key].append(definition)
        yield from self._definitions_tag_cache[key]

    def get_tuning_file_id(self, def_id):
        if def_id in self._definitions_cache:
            return self._definitions_cache[def_id].tuning_file_id

    def reload_by_key(self, key):
        raise RuntimeError('[manus] Reloading tuning is not supported for optimized python builds.')
        if key.type == sims4.resources.Types.OBJECTDEFINITION:
            self._reload_definition(key.instance)
        elif key.type == self.TYPE:
            super().reload_by_key(key)
            object_tuning = super().get(key)
            object_guid64 = getattr(object_tuning, 'guid64', None)
            reload_list = set()
            for (definition_key, definition) in self._definitions_cache.items():
                def_cls = definition.cls
                def_cls_guid64 = getattr(def_cls, 'guid64', None)
                if object_guid64 is not None and def_cls_guid64 is not None and object_guid64 == def_cls_guid64:
                    reload_list.add(definition_key)
            for cache_key in reload_list:
                del self._definitions_cache[cache_key]
            for definition_key in reload_list:
                self._reload_definition(definition_key)

    def _reload_definition(self, key):
        if paths.SUPPORT_RELOADING_RESOURCES:
            sims4.resources.purge_cache()
            if isinstance(key, tuple):
                (def_id, state) = key
            else:
                def_id = key
                state = 0
            definition = self._load_definition_and_tuning(def_id, state)
            if def_id in self._dependencies:
                list_copy = list(self._dependencies.get(def_id))
                self._dependencies[def_id].clear()
                for gameobject in list_copy:
                    if gameobject.is_sim:
                        pass
                    else:
                        loc_type = gameobject.item_location
                        object_list = file_serialization.ObjectList()
                        save_data = gameobject.save_object(object_list.objects)
                        try:
                            gameobject.manager.remove(gameobject)
                        except:
                            logger.exception('exception in removing game object {}', gameobject)
                            continue
                        try:
                            dup = objects.system.create_object(definition, obj_id=gameobject.id, loc_type=loc_type)
                            dup.load_object(save_data)
                            if gameobject.location is not None:
                                dup.location = gameobject.location
                            inventory = dup.get_inventory()
                            if inventory is not None:
                                inventory.system_add_object(dup)
                            logger.error('reloading game object with ID {}', dup.id)
                        except:
                            logger.exception('exception in reinitializing game object {}', gameobject)
            return definition

    def _load_definition_and_tuning(self, def_id, obj_state, pack_safe=False):
        try:
            definition = self._load_definition(def_id)
        except KeyError:
            if pack_safe:
                raise UnavailablePackSafeResourceError
            logger.error('Failed to load definition with id {}', def_id, owner='tingyul')
            return
        try:
            tuning_file_id = definition.tuning_file_id
            if tuning_file_id == 0:
                tuning_file_id = PROTOTYPE_INSTANCE_ID
            cls = super().get(tuning_file_id)
            if cls is None:
                logger.info('Failed to load object-tuning-id {} for definition {}. This is valid for SP14 objects mimic based on EP04 objects.', tuning_file_id, definition)
                cls = super().get(PROTOTYPE_INSTANCE_ID)
            if cls is None:
                return
            cls = cls.get_class_for_obj_state(obj_state)
        except:
            logger.exception('Unable to create a script object for definition id: {0}', def_id)
            return
        definition.set_class(cls)
        key = (def_id, obj_state) if obj_state else def_id
        self._definitions_cache[key] = definition
        definition.assign_build_buy_tags()
        return definition

    def _load_definition(self, def_id):
        key = sims4.resources.Key(sims4.resources.Types.OBJECTDEFINITION, def_id)
        resource = sims4.resources.load(key)
        properties = sims4.PropertyStreamReader(resource)
        return objects.definition.Definition(properties, def_id)

    def find_first_definition_by_cls(self, cls):
        for definition in self._definitions_cache.values():
            if definition.cls is cls:
                return definition
