from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom distributor.rollback import ProtocolBufferRollbackfrom interactions.utils.loot_basic_op import BaseTargetedLootOperation, BaseLootOperationfrom objects.components import Component, types, componentmethodfrom objects.components.state import TunableStateTypeReferencefrom objects.components.stored_object_info_tuning import StoredObjectTypefrom sims4.tuning.tunable import TunableSet, TunableEnumEntryimport servicesimport sims4.loglogger = sims4.log.Logger('StoredObjectInfoComponent', default_owner='nsavalani')
class StoreObjectInfoLootOp(BaseTargetedLootOperation):
    FACTORY_TUNABLES = {'states_to_store': TunableSet(description='\n            A list of states to be stored, if the source object has that state.\n            ', tunable=TunableStateTypeReference(description='\n                A state to store.\n                ')), 'stored_object_type': TunableEnumEntry(description='\n            The type of object being stored. This will be used to retrieve the\n            stored object from the Stored Object Info Component of the target.\n            ', tunable_type=StoredObjectType, default=StoredObjectType.INVALID, invalid_enums=(StoredObjectType.INVALID,))}

    def __init__(self, *args, states_to_store, stored_object_type, **kwargs):
        super().__init__(*args, **kwargs)
        self._states_to_store = states_to_store
        self._stored_object_type = stored_object_type

    def _get_state_guids_to_store(self, target):
        target_state_guids = set()
        for state in self._states_to_store:
            if target.has_state(state):
                target_state_value = target.get_state(state)
                target_state_guids.add((state.guid64, target_state_value.guid64))
        return target_state_guids

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if not subject.has_component(types.STORED_OBJECT_INFO_COMPONENT):
            subject.add_dynamic_component(types.STORED_OBJECT_INFO_COMPONENT)
        custom_name = target.custom_name if target.has_custom_name() else None
        state_guids_to_store = self._get_state_guids_to_store(target)
        stored_object_component = subject.get_component(types.STORED_OBJECT_INFO_COMPONENT)
        stored_object_component.add_object(self._stored_object_type, target.id, obj_def_id=target.definition.id, custom_name=custom_name, state_guids=state_guids_to_store)

class RemoveObjectInfoLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'stored_object_type': TunableEnumEntry(description='\n            The type of object to remove from the Stored Object Info Component.\n            ', tunable_type=StoredObjectType, default=StoredObjectType.INVALID, invalid_enums=(StoredObjectType.INVALID,))}

    def __init__(self, *args, stored_object_type, **kwargs):
        super().__init__(*args, **kwargs)
        self._stored_object_type = stored_object_type

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            logger.error('Attempting to remove Stored Object Info type {} on a None subject. Loot: {}', self._stored_object_type, self)
            return
        stored_object_component = subject.get_component(types.STORED_OBJECT_INFO_COMPONENT)
        if stored_object_component is None:
            return
        stored_object_component.remove_object(self._stored_object_type)
        if stored_object_component.is_stored_object_empty():
            subject.remove_component(types.STORED_OBJECT_INFO_COMPONENT)

class StoredObjectData:

    def __init__(self, obj_id, obj_def_id, custom_name, state_guids):
        self._object_id = obj_id
        self._object_definition_id = obj_def_id
        self._custom_name = custom_name
        self._state_guids = state_guids

    @property
    def object_id(self):
        return self._object_id

    @property
    def object_definition_id(self):
        return self._object_definition_id

    @property
    def custom_name(self):
        return self._custom_name

    @property
    def state_guids(self):
        return self._state_guids

class StoredObjectInfoComponent(Component, component_name=types.STORED_OBJECT_INFO_COMPONENT, allow_dynamic=True, persistence_key=protocols.PersistenceMaster.PersistableData.StoredObjectInfoComponent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stored_object_map = {}

    def is_stored_object_empty(self):
        return not self._stored_object_map

    def add_object(self, stored_object_type, obj_id, obj_def_id=None, custom_name=None, state_guids=set()):
        self._stored_object_map[stored_object_type] = StoredObjectData(obj_id, obj_def_id, custom_name, state_guids)

    def remove_object(self, stored_object_type):
        del self._stored_object_map[stored_object_type]

    def _save_stored_object_info(self, stored_object_proto_msg):
        for (stored_object_type, stored_object_data) in self._stored_object_map.items():
            with ProtocolBufferRollback(stored_object_proto_msg.stored_object_data) as entry:
                entry.stored_object_type = stored_object_type
                if stored_object_data.object_id is not None:
                    entry.object_id = stored_object_data.object_id
                if stored_object_data.object_definition_id is not None:
                    entry.object_definition_id = stored_object_data.object_definition_id
                if stored_object_data.custom_name is not None:
                    entry.custom_name = stored_object_data.custom_name
                for (state, state_value) in stored_object_data.state_guids:
                    with ProtocolBufferRollback(entry.states) as state_entry:
                        state_entry.state_name_hash = state
                        state_entry.value_name_hash = state_value

    def get_save_data(self):
        stored_object_info_component_data = protocols.PersistableStoredObjectInfoComponent()
        self._save_stored_object_info(stored_object_info_component_data)
        return stored_object_info_component_data

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.StoredObjectInfoComponent
        stored_object_info_component_data = persistable_data.Extensions[protocols.PersistableStoredObjectInfoComponent.persistable_data]
        self._save_stored_object_info(stored_object_info_component_data)
        persistence_master_message.data.extend([persistable_data])

    def load_stored_object_info(self, stored_object_proto_msg):
        object_id = 0
        if stored_object_proto_msg.HasField('object_id'):
            object_id = stored_object_proto_msg.object_id
        object_definition_id = 0
        if stored_object_proto_msg.HasField('object_definition_id'):
            object_definition_id = stored_object_proto_msg.object_definition_id
        custom_name = None
        if stored_object_proto_msg.HasField('custom_name'):
            custom_name = stored_object_proto_msg.custom_name
        state_guids = set()
        for state_proto in stored_object_proto_msg.states:
            state_guids.add((state_proto.state_name_hash, state_proto.value_name_hash))
        if object_id != 0:
            self._stored_object_map[StoredObjectType.SNOWPAL] = StoredObjectData(object_id, object_definition_id, custom_name, state_guids)
        for stored_object_data_proto in stored_object_proto_msg.stored_object_data:
            object_definition_id = 0
            if stored_object_data_proto.HasField('object_definition_id'):
                object_definition_id = stored_object_data_proto.object_definition_id
            custom_name = None
            if stored_object_data_proto.HasField('custom_name'):
                custom_name = stored_object_data_proto.custom_name
            state_guids = set()
            for state_proto in stored_object_data_proto.states:
                state_guids.add((state_proto.state_name_hash, state_proto.value_name_hash))
            self._stored_object_map[stored_object_data_proto.stored_object_type] = StoredObjectData(stored_object_data_proto.object_id, object_definition_id, custom_name, state_guids)

    def load(self, persistable_data):
        stored_object_info_component_data = persistable_data.Extensions[protocols.PersistableStoredObjectInfoComponent.persistable_data]
        self.load_stored_object_info(stored_object_info_component_data)

    @componentmethod
    def get_stored_objects(self):
        stored_objects = []
        object_manager = services.object_manager()
        for object_data in self._stored_object_map.values():
            obj = object_manager.get(object_data.object_id)
            if obj is not None:
                stored_objects.append(obj)
        return stored_objects

    @componentmethod
    def get_stored_object_info_id(self, stored_object_type):
        stored_object_data = self._stored_object_map.get(stored_object_type, None)
        if stored_object_data is not None:
            return stored_object_data.object_id

    @componentmethod
    def get_stored_object_info_definition_id(self, stored_object_type):
        stored_object_data = self._stored_object_map.get(stored_object_type, None)
        if stored_object_data is not None:
            return stored_object_data.object_definition_id

    @componentmethod
    def get_stored_object_info_custom_name(self, stored_object_type):
        stored_object_data = self._stored_object_map.get(stored_object_type, None)
        if stored_object_data is not None:
            return stored_object_data.custom_name

    @componentmethod
    def get_stored_object_info_states(self, stored_object_type):
        stored_object_data = self._stored_object_map.get(stored_object_type, None)
        if stored_object_data is not None:
            return stored_object_data.state_guids
