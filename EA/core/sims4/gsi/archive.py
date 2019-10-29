import jsonimport timeimport zlibfrom sims4.gsi.schema import GsiSchema, CLIENT_GSI_ARCHIVE_UID_FIXfrom uid import UniqueIdGeneratorimport sims4.gsi.dispatcherimport sims4.logimport sims4.reloadimport sims4.zone_utilslogger = sims4.log.Logger('GSI')with sims4.reload.protected(globals()):
    archive_data = {}
    archive_schemas = {}
    all_archivers = {}
    archive_id = UniqueIdGenerator()ARCHIVE_DEFAULT_RECORDS = 50ARCHIVE_MAX_RECORDS = ARCHIVE_DEFAULT_RECORDS
def set_max_archive_records(max_records):
    global ARCHIVE_MAX_RECORDS
    ARCHIVE_MAX_RECORDS = max_records

def set_max_archive_records_default():
    set_max_archive_records(ARCHIVE_DEFAULT_RECORDS)

def set_archive_enabled(archive_type, enable=True):
    if archive_type in all_archivers:
        all_archivers[archive_type].archive_enable_fn(enableLog=enable)
    else:
        logger.error('Tried to enable {} which is not a valid archive name'.format(archive_type))

def set_all_archivers_enabled(enable=True):
    for archiver in all_archivers.values():
        if archiver._enable_on_all_enable:
            archiver.archive_enable_fn(enableLog=enable)

def clear_archive_records(archive_type, sim_id=None):
    if archive_type in all_archivers:
        all_archivers[archive_type].clear_archive(sim_id=sim_id)
    else:
        logger.error('Trying to clear all archive entries from {} which is not a valid archive type.'.format(archive_type))

class BaseArchiver:
    __slots__ = ('_type_name', '_custom_enable_fn', '_archive_enabled', '_enable_on_all_enable', '__weakref__')

    def __init__(self, type_name=None, enable_archive_by_default=False, add_to_archive_enable_functions=False, custom_enable_fn=None):
        self._type_name = type_name
        self._custom_enable_fn = custom_enable_fn
        self._enable_on_all_enable = add_to_archive_enable_functions
        self._archive_enabled = False
        all_archivers[type_name] = self

    @property
    def enabled(self):
        return self._archive_enabled

    def archive_enable_fn(self, *args, enableLog=False, **kwargs):
        self._archive_enabled = enableLog
        if self._custom_enable_fn is not None:
            self._custom_enable_fn(*args, enableLog=enableLog, **kwargs)
        return '{{"log_enabled":{}}}'.format('true' if enableLog else 'false')

    def clear_archive(self, sim_id=None):
        pass

class Archiver(BaseArchiver):
    __slots__ = ('_sim_specific', '_max_records')

    def __init__(self, type_name=None, schema=None, max_records=None, enable_archive_by_default=False, add_to_archive_enable_functions=False, custom_enable_fn=None):
        super().__init__(type_name=type_name, enable_archive_by_default=enable_archive_by_default, add_to_archive_enable_functions=add_to_archive_enable_functions, custom_enable_fn=custom_enable_fn)
        self._sim_specific = schema.is_sim_specific
        self._max_records = max_records
        sims4.gsi.dispatcher.add_handler('{}{}'.format(type_name, sims4.gsi.dispatcher.ARCHIVE_TOGGLE_SUFFIX), None, lambda *args, **kwargs: self.archive_enable_fn(*args, **kwargs))
        register_archive_type(type_name, schema, partition_by_obj=self._sim_specific)

    def clear_archive(self, sim_id=None):
        if self._sim_specific:
            if sim_id is not None:
                del archive_data[self._type_name][sim_id]
                archive_data[self._type_name][sim_id] = []
            else:
                logger.error('No Sim Id provided when trying to clear a sim specific archive.')
        else:
            del archive_data[self._type_name]
            archive_data[self._type_name] = []

    def archive(self, data=None, object_id=None, game_time=None, zone_override=None):
        if zone_override is not None:
            zone_id = zone_override
        else:
            zone_id = sims4.zone_utils.zone_id
            if not zone_id:
                logger.error('Archiving data to zone 0. This data will be inaccessible to the GSI.')
                zone_id = 0
        now = int(time.time())
        record = ArchiveRecord(zone_id=zone_id, object_id=object_id, timestamp=now, game_time=game_time, data=data)
        if self._sim_specific:
            if object_id is None:
                logger.error('Archiving data to a sim_specific archive with no object ID. This data will be inaccessible to the GSI.')
            archive_list = archive_data[self._type_name].get(object_id)
            if archive_list is None:
                archive_list = []
                archive_data[self._type_name][object_id] = archive_list
        else:
            archive_list = archive_data[self._type_name]
        archive_list.append(record)
        num_max_records = ARCHIVE_MAX_RECORDS
        if num_max_records < self._max_records:
            num_max_records = self._max_records
        num_records = len(archive_list)
        if self._max_records is not None and num_records > num_max_records:
            diff = num_records - num_max_records
            while diff > 0:
                del archive_list[0]
                diff -= 1

class ArchiveRecord:
    __slots__ = ('zone_id', 'object_id', 'timestamp', 'uid', 'compressed_json')

    def __init__(self, zone_id=None, object_id=None, timestamp=None, game_time=None, data=None):
        self.zone_id = zone_id
        self.object_id = object_id
        self.timestamp = timestamp
        self.uid = archive_id()
        full_dict = {'zone_id': hex(zone_id), 'object_id': hex(object_id) if object_id is not None else 'None', 'timestamp': timestamp, 'game_time': game_time, 'uid': self.uid}
        for (key, field) in data.items():
            full_dict[key] = field
        uncompressed_json = json.dumps(full_dict)
        self.compressed_json = zlib.compress(uncompressed_json.encode())

def register_archive_type(type_name, schema, partition_by_obj=False):
    if isinstance(schema, GsiSchema):
        schema = schema.output
    if type_name in archive_schemas:
        logger.error('Replacing archive type for {}.', type_name)
        del archive_schemas[type_name]
    path = type_name.strip('/')
    new_archive = archive_data.get(type_name)
    if new_archive is None:
        if partition_by_obj:
            new_archive = {}
        else:
            new_archive = []
        archive_data[type_name] = new_archive
    actual_schema = {'archive': True, 'perf_toggle': True, 'unique_field': 'uid', 'definition': [{'name': 'zone_id', 'type': 'string', 'label': 'Zone', 'hidden': True}, {'name': 'object_id', 'type': 'string', 'label': 'Object ID', 'hidden': True}, {'name': 'timestamp', 'type': 'int', 'label': 'Time', 'is_time': True, 'axis': 'xField', 'sort_field': 'uid'}, {'name': 'game_time', 'type': 'string', 'label': 'Game Time', 'hidden': True}, {'name': 'uid', 'type': 'int', 'label': 'UId', 'hidden': True}]}
    for (key, entry) in schema.items():
        if key == 'definition':
            for definition_entry in entry:
                actual_schema['definition'].append(definition_entry)
        else:
            actual_schema[key] = entry
    for (key, value) in schema.items():
        if key not in ('definition', 'associations'):
            actual_schema[key] = value
    archive_schemas[type_name] = actual_schema

    def archive_handler(zone_id:int=None, object_id:int=None, sim_id:int=None, timestamp:int=None, uid:int=None, uncompress:bool=True):
        if sim_id is not None:
            object_id = sim_id
        if object_id is None and partition_by_obj:
            archive_data_list = archive_data[type_name].get(object_id)
            if archive_data_list is None:
                return '[]'
        else:
            archive_data_list = archive_data[type_name]
        json_output = '[]'
        try:
            record_data = []
            for record in archive_data_list:
                if zone_id is not None and zone_id != record.zone_id:
                    pass
                elif object_id is not None and object_id != record.object_id:
                    pass
                else:
                    if sims4.gsi.dispatcher.gsi_client_version < CLIENT_GSI_ARCHIVE_UID_FIX:
                        if timestamp is not None and timestamp >= record.timestamp:
                            pass
                        else:
                            record_data.append(record.compressed_json)
                    elif uid is not None and uid >= record.uid:
                        pass
                    else:
                        record_data.append(record.compressed_json)
                    record_data.append(record.compressed_json)
            if uncompress:
                json_output = '[{}]'.format(','.join(zlib.decompress(record).decode('utf-8') for record in record_data))
            else:
                return record_data
        except MemoryError:
            logger.error('Archive Data[{}] has too many entries: {}', type_name, len(archive_data_list))
            json_output = '[]'
        return json_output

    sims4.gsi.dispatcher.GsiHandler(path, actual_schema, suppress_json=True)(archive_handler)
