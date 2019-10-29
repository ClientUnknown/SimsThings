import _weakrefutilsimport timefrom sims4.callback_utils import CallableListfrom sims4.service_manager import Serviceimport enumimport gsi_handlersimport id_generatorimport servicesimport sims4.log__unittest__ = 'test.objects.manager_tests'logger = sims4.log.Logger('IndexedManager')production_logger = sims4.log.ProductionLogger('IndexedManager')with sims4.reload.protected(globals()):
    object_load_times = {}
    capture_load_times = False
class ObjectLoadData:

    def __init__(self):
        self.time_spent_adding = 0.0
        self.time_spent_loading = 0.0
        self.adds = 0
        self.loads = 0

class CallbackTypes(enum.Int, export=False):
    ON_OBJECT_ADD = 0
    ON_OBJECT_REMOVE = 1
    ON_OBJECT_LOCATION_CHANGED = 2

class ObjectIDError(Exception):
    pass

class IndexedManager(Service):

    def __init__(self, *args, manager_id=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = manager_id
        self._objects = {}
        self._objects_to_be_removed = []
        self._registered_callbacks = {}
        for key in CallbackTypes:
            self._registered_callbacks[key] = CallableList()

    def __contains__(self, key):
        if not isinstance(key, int):
            raise TypeError('IndexedManager keys must be integers.')
        return key in self._objects

    def __getitem__(self, key):
        if not isinstance(key, int):
            raise TypeError('IndexedManager keys must be integers.')
        return self._objects[key]

    def __iter__(self):
        return iter(self._objects)

    def __len__(self):
        return len(self._objects)

    def __bool__(self):
        if self._objects:
            return True
        return False

    def keys(self):
        return self._objects.keys()

    def values(self):
        return self._objects.values()

    def items(self):
        return self._objects.items()

    ids = property(keys)
    objects = property(values)
    id_object_pairs = property(items)

    def destroy_all_objects(self):
        cur_id = None
        while self._objects:
            try:
                (cur_id, object_being_shutdown) = next(iter(self._objects.items()))
                self.remove(object_being_shutdown)
            except Exception:
                logger.exception('Failed to remove {} from indexed manager', object_being_shutdown)
            finally:
                if cur_id in self._objects:
                    del self._objects[cur_id]

    def stop(self):
        self.destroy_all_objects()

    def register_callback(self, callback_type, callback):
        self._registered_callbacks[callback_type].append(callback)

    def unregister_callback(self, callback_type, callback):
        callback_list = self._registered_callbacks[callback_type]
        if callback in callback_list:
            callback_list.remove(callback)
        else:
            logger.warn('Attempt to remove callback that was not registered on {}: {}:{}', self, callback_type, callback, owner='maxr')

    def add(self, obj):
        if capture_load_times:
            time_stamp = time.time()
        new_id = obj.id or id_generator.generate_object_id()
        if new_id in self._objects:
            existing_obj = self.get(new_id)
            raise ObjectIDError('ID collision detected. ID:{}, New Object:{}, Existing Object:{}'.format(new_id, obj, existing_obj))
        self.call_pre_add(obj, new_id)
        self._objects[new_id] = obj
        obj.manager = self
        obj.id = new_id
        self.call_on_add(obj)
        if hasattr(obj, 'definition'):
            time_elapsed = time.time() - time_stamp
            if obj.definition not in object_load_times:
                object_load_times[obj.definition] = ObjectLoadData()
            object_load_times[obj.definition].time_spent_adding += time_elapsed
            object_load_times[obj.definition].adds += 1
        return new_id

    def remove_id(self, obj_id):
        obj = self._objects.get(obj_id)
        return self.remove(obj)

    def is_removing_object(self, obj):
        if obj.id in self._objects_to_be_removed:
            return True
        return False

    def remove(self, obj):
        if obj.id not in self._objects:
            logger.error('Attempting to remove an object that is not in this manager')
            return
        if obj.id in self._objects_to_be_removed:
            logger.error('Attempting to remove an object {} that is already in the process of being removed.'.format(obj), owner='tastle')
            return
        try:
            self._objects_to_be_removed.append(obj.id)
            self.call_on_remove(obj)
            _weakrefutils.clear_weak_refs(obj)
            del self._objects[obj.id]
            self._objects_to_be_removed.remove(obj.id)
            old_obj_id = obj.id
            obj.id = 0
            self.call_post_remove(obj)
            _weakrefutils.clear_weak_refs(obj)
            object_leak_tracker = services.get_object_leak_tracker()
            if object_leak_tracker is not None:
                object_leak_tracker.track_object(obj, self, old_obj_id)
        except Exception:
            logger.exception('Exception thrown while calling remove on {0}', obj)

    def get(self, obj_id):
        return self._objects.get(obj_id, None)

    def get_all(self):
        return self._objects.values()

    def call_pre_add(self, obj, obj_id):
        if hasattr(obj, 'pre_add'):
            obj.pre_add(self, obj_id)

    def call_on_add(self, obj):
        if hasattr(obj, 'on_add'):
            obj.on_add()
        self._registered_callbacks[CallbackTypes.ON_OBJECT_ADD](obj)

    def call_on_remove(self, obj):
        self._registered_callbacks[CallbackTypes.ON_OBJECT_REMOVE](obj)
        if hasattr(obj, 'on_remove'):
            obj.on_remove()

    def call_post_remove(self, obj):
        if hasattr(obj, 'post_remove'):
            obj.post_remove()
