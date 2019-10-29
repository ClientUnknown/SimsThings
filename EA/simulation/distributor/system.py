from collections import namedtuplefrom contextlib import contextmanagerimport weakreffrom protocolbuffers import Distributor_pb2 as protocolsfrom protocolbuffers.Consts_pb2 import MSG_OBJECTS_VIEW_UPDATE, MGR_UNMANAGED, MGR_OBJECT, MGR_SIM_INFOimport protocolbuffers.DistributorOps_pb2from distributor import loggerfrom distributor.rollback import ProtocolBufferRollbackfrom graph_algos import topological_sortfrom gsi_handlers.distributor_handlers import archive_operationfrom sims4.callback_utils import consume_exceptionsfrom sims4.repr_utils import standard_reprfrom uid import UniqueIdGeneratorimport elementsimport gsi_handlersimport resetimport servicesimport sims4.reload__all__ = ['Distributor']__unittest__ = 'test.distributor.system_test'with sims4.reload.protected(globals()):
    _distributor_instance = None
    _current_tag_set = set()
    get_next_tag_id = UniqueIdGenerator(min_uid=1)
    _distributor_log_enabled = False
    _send_index = 0DEFAULT_MASK = protocolbuffers.Consts_pb2.OperationChannel.DESCRIPTOR.fields_by_name['mask'].default_value
def get_current_tag_set():
    return _current_tag_set

class Journal:
    JournalEntry = namedtuple('JournalEntry', ('object', 'protocol_buffer', 'payload_type', 'manager_id', 'debug_object_name'))
    JournalEntry.__repr__ = lambda self: standard_repr(self, self.object, self.protocol_buffer, self.payload_type, self.manager_id, self.debug_object_name)
    JournalSeed = namedtuple('JournalSeed', ('op', 'object_id', 'manager_id', 'debug_object_name'))

    def __init__(self):
        self.entries = []
        self._deferred_journal_seeds = []
        self.deferring = False

    def __repr__(self):
        return '<Journal ops={}>'.format(self.op_count)

    @property
    def op_count(self):
        return len(self.entries)

    def start_deferring(self):
        self.deferring = True

    def stop_deferring(self):
        self.deferring = False
        for journal_seed in self._deferred_journal_seeds:
            entry = self._build_journal_entry(journal_seed)
            self.entries.append(entry)
        self._deferred_journal_seeds.clear()

    def add(self, obj, op, ignore_deferral=False):
        for tag in _current_tag_set:
            op.block_on_tag(tag)
        manager_id_override = None
        if op.block_on_task_owner:
            op_task_owner = None
            time_service = services.time_service()
            if time_service.sim_timeline is not None:
                timeline = time_service.sim_timeline
                current_element = timeline.get_current_element()
                while current_element is not None:
                    if isinstance(current_element, reset.ResettableElement):
                        op_task_owner = current_element.obj
                        break
                    if isinstance(current_element, elements.AllElement):
                        break
                    if current_element._parent_handle is None:
                        break
                    current_element = current_element._parent_handle.element
            if obj is None or op_task_owner.id != obj.id:
                op_task_owner_manager = getattr(op_task_owner, 'manager', None)
                if hasattr(op_task_owner_manager, 'id'):
                    op.add_additional_channel(op_task_owner_manager.id, op_task_owner.id, mask=op._primary_channel_mask_override)
                    op._primary_channel_mask_override = 0
        elif obj.manager.id == MGR_SIM_INFO:
            manager_id_override = MGR_OBJECT
        journal_seed = self._build_journal_seed(op, obj, manager_id_override)
        if self.deferring and ignore_deferral:
            entry = self._build_journal_entry(journal_seed)
            self.entries.append(entry)
        else:
            self._deferred_journal_seeds.append(journal_seed)

    def _build_journal_seed(self, op, obj, manager_id):
        object_name = None
        if obj is None:
            object_id = 0
            if manager_id is None:
                manager_id = MGR_UNMANAGED
        else:
            object_id = obj.id
            if manager_id is None:
                manager_id = obj.manager.id if obj.manager is not None else MGR_UNMANAGED
        return Journal.JournalSeed(op, object_id, manager_id, object_name)

    def _build_journal_entry(self, journal_seed):
        op = journal_seed.op
        object_id = journal_seed.object_id
        manager_id = journal_seed.manager_id
        object_name = journal_seed.debug_object_name
        proto_buff = protocolbuffers.DistributorOps_pb2.Operation()
        mask_override = None
        if manager_id == MGR_UNMANAGED:
            mask_override = 0
        if op._force_execution_on_tag:
            mask_override = 0
        elif op._primary_channel_mask_override is not None:
            mask_override = op._primary_channel_mask_override
        if mask_override != DEFAULT_MASK:
            proto_buff.primary_channel_mask_override = mask_override
        for channel in op._additional_channels:
            with ProtocolBufferRollback(proto_buff.additional_channels) as additional_channel_msg:
                additional_channel_msg.id.manager_id = channel[0]
                additional_channel_msg.id.object_id = channel[1]
                if channel[1] == object_id and mask_override is not None:
                    additional_channel_msg.mask = mask_override
                else:
                    additional_channel_msg.mask = channel[2]
        op.write(proto_buff)
        if not (mask_override is not None and proto_buff.IsInitialized()):
            logger.error('Message generated by {} is missing required fields: ' + str(proto_buff.FindInitializationErrors()), op)
        payload_type = op.payload_type
        entry = Journal.JournalEntry(object_id, proto_buff, payload_type, manager_id, object_name)
        return entry

    def clear(self):
        del self.entries[:]

class Distributor:

    def __init__(self):
        self.journal = Journal()
        self._pending_creates = weakref.WeakSet()
        self.client = None
        self.events = []

    def __repr__(self):
        return '<Distributor events={}>'.format(len(self.events))

    @contextmanager
    def dependent_block(self):
        if not self.journal.deferring:
            with consume_exceptions('Distributor', 'Exception raised during a dependent block:'):
                self.journal.start_deferring()
                try:
                    yield None
                finally:
                    self.journal.stop_deferring()
        else:
            yield None

    @classmethod
    def instance(cls):
        return _distributor_instance

    def add_object(self, obj):
        logger.info('Adding {0}', obj)
        obj.visible_to_client = True
        if not obj.visible_to_client:
            return
        if not services.client_manager():
            return
        op = obj.get_create_op()
        if op is None:
            obj.visible_to_client = False
            return
        self.journal.add(obj, op, ignore_deferral=True)
        self._pending_creates.add(obj)
        if hasattr(obj, 'on_add_to_client'):
            obj.on_add_to_client()

    def remove_object(self, obj, **kwargs):
        logger.info('Removing {0}', obj)
        was_visible = obj.visible_to_client
        if was_visible and hasattr(obj, 'on_remove_from_client'):
            obj.on_remove_from_client()
        if was_visible:
            delete_op = obj.get_delete_op(**kwargs)
            if delete_op is not None:
                self.add_op(obj, delete_op)
            obj.visible_to_client = False

    def add_client(self, client):
        if self.client is not None:
            raise ValueError('Client is already registered')
        self.process()
        logger.info('Adding {0}', client)
        self.client = client
        self._add_ops_for_client_connect(client)

    def _add_ops_for_client_connect(self, client):
        node_gen = client.get_objects_in_view_gen()
        parents_gen_fn = lambda obj: obj.get_create_after_objs()
        create_order = topological_sort(node_gen, parents_gen_fn)
        for obj in create_order:
            create_op = obj.get_create_op()
            if create_op is not None:
                self.journal.add(obj, create_op)

    def remove_client(self, client):
        logger.info('Removing {0}', client)
        self.process()
        self.client = None

    def _debug_validate_op(self, obj, op):
        objs = getattr(obj, 'client_objects_gen', None)
        if objs:
            for sub_obj in objs:
                self._debug_validate_op(sub_obj, op)
        else:
            if obj not in self.created_objects:
                logger.callstack('Target of Op ({}) is not on the client. Operation type: {}. \n                    This will result in errors in client state.', obj, op, level=sims4.log.LEVEL_ERROR)
            if getattr(obj, 'valid_for_distribution', True) or not getattr(op, 'is_create_op', False):
                logger.callstack('Operation is being added for {}, but it is not valid_for_distribution. \n                        Operation type: {}. This will result in errors in client state.', obj, op, level=sims4.log.LEVEL_ERROR)

    def add_op(self, obj, op):
        if self.client is None:
            return
        self.journal.add(obj, op)

    def add_op_with_no_owner(self, op):
        if self.client is None:
            return
        self.journal.add(None, op)

    def send_op_with_no_owner_immediate(self, op):
        global _send_index
        journal_seed = self.journal._build_journal_seed(op, None, None)
        journal_entry = self.journal._build_journal_entry(journal_seed)
        (obj_id, operation, payload_type, manager_id, obj_name) = journal_entry
        view_update = protocols.ViewUpdate()
        entry = view_update.entries.add()
        entry.primary_channel.id.manager_id = manager_id
        entry.primary_channel.id.object_id = obj_id
        entry.operation_list.operations.append(operation)
        if gsi_handlers.distributor_handlers.archiver.enabled or gsi_handlers.distributor_handlers.sim_archiver.enabled:
            _send_index += 1
            if _send_index >= 4294967295:
                _send_index = 0
            archive_operation(obj_id, obj_name, manager_id, operation, payload_type, _send_index, self.client)
        self.client.send_message(MSG_OBJECTS_VIEW_UPDATE, view_update)
        if _distributor_log_enabled:
            logger.error('------- SENT IMMEDIATE --------')

    def add_event(self, msg_id, msg, immediate=False):
        if self.client is None:
            logger.error('Could not add event {0} because there are no attached clients', msg_id)
            return
        self.events.append((msg_id, msg))
        if immediate:
            self.process_events()

    def process(self):
        self.process_events()
        self._send_view_updates()

    def process_events(self):
        for (msg_id, msg) in self.events:
            self.client.send_message(msg_id, msg)
        del self.events[:]

    def _send_view_updates(self):
        journal = self.journal
        if journal.entries:
            ops = list(journal.entries)
            journal.clear()
            try:
                if self.client is not None:
                    self._send_view_updates_for_client(self.client, ops)
            except:
                logger.exception('Error sending view updates to client!')
        self._pending_creates.clear()

    def _send_view_updates_for_client(self, client, all_ops):
        global _send_index
        view_update = None
        last_obj_id = None
        last_manager_id = None
        for (obj_id, operation, payload_type, manager_id, obj_name) in all_ops:
            if view_update is None:
                view_update = protocols.ViewUpdate()
            if obj_id != last_obj_id or manager_id != last_manager_id:
                if _distributor_log_enabled:
                    logger.error('    Object: {}', obj_name or obj_id)
                entry = view_update.entries.add()
                entry.primary_channel.id.manager_id = manager_id
                entry.primary_channel.id.object_id = obj_id
                last_obj_id = obj_id
                last_manager_id = manager_id
            entry.operation_list.operations.append(operation)
            if not gsi_handlers.distributor_handlers.archiver.enabled:
                if gsi_handlers.distributor_handlers.sim_archiver.enabled:
                    _send_index += 1
                    if _send_index >= 4294967295:
                        _send_index = 0
                    archive_operation(obj_id, obj_name, manager_id, operation, payload_type, _send_index, client)
            _send_index += 1
            if _send_index >= 4294967295:
                _send_index = 0
            archive_operation(obj_id, obj_name, manager_id, operation, payload_type, _send_index, client)
        if view_update is not None:
            client.send_message(MSG_OBJECTS_VIEW_UPDATE, view_update)
            if _distributor_log_enabled:
                logger.error('------- SENT --------')
