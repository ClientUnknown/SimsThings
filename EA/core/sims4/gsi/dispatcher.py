import inspectimport jsonfrom sims4.gsi.schema import GsiSchema, LATEST_GSI_SERVER_VERSION, CLIENT_GSI_BASE_VERSIONfrom sims4.log import LEVEL_WARNimport sims4.logimport sims4.reloadimport sims4.zone_utilslogger = sims4.log.Logger('GSI')ARCHIVE_TOGGLE_SUFFIX = '_toggleLog'gsi_client_version = CLIENT_GSI_BASE_VERSIONwith sims4.reload.protected(globals()):
    dispatch_table = {}
    zone_manager = None
    gsi_handler_exceptions_enabled = False
def get_all_gsi_schema_names():
    archive_schemas = []
    normal_schemas = []
    for gsi_schema_name in dispatch_table:
        if ARCHIVE_TOGGLE_SUFFIX in gsi_schema_name:
            pass
        elif not gsi_schema_name == 'directory':
            if gsi_schema_name == 'command':
                pass
            elif gsi_schema_name + ARCHIVE_TOGGLE_SUFFIX in dispatch_table:
                archive_schemas.append(gsi_schema_name)
            else:
                normal_schemas.append(gsi_schema_name)
    return (normal_schemas, archive_schemas)

class GSIJSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if hasattr(obj, '__call__'):
            return obj()
        return json.JSONEncoder.default(self, obj)

def GsiHandler(path, schema, suppress_json=False):
    if isinstance(schema, GsiSchema):
        schema = schema.output

    def _generate_handler(func):
        full_arg_spec = inspect.getfullargspec(func)

        def _invoke_handler(**kwargs):
            if full_arg_spec.varkw:
                valid_kwargs = kwargs
            else:
                valid_kwargs = {}
                for (key, value) in kwargs.items():
                    if not key in full_arg_spec.args:
                        if key in full_arg_spec.kwonlyargs:
                            valid_kwargs[key] = value
                    valid_kwargs[key] = value
            parse_args(full_arg_spec, valid_kwargs)
            try:
                ret_val = func(**valid_kwargs)
            except Exception as e:
                if gsi_handler_exceptions_enabled:
                    logger.exception('Exception in GSI Handler: {}', func)
                else:
                    logger.warn('Exception in GSI Handler: {} : {}', func, e)
                ret_val = []
            if suppress_json:
                return ret_val
            if ret_val is None:
                return ''
            return json.dumps(ret_val, cls=GSIJSONEncoder)

        add_handler(path, schema, _invoke_handler)

    return _generate_handler

def add_cheat_schema(path, schema):
    if isinstance(schema, GsiSchema):
        schema = schema.output
    dispatch_table[path] = (None, schema)

def add_handler(path, schema, callback):
    path = path.strip('/')
    if path in dispatch_table:
        logger.info('Re-adding a handler to {}.\n\tAlready registered: {}', path, dispatch_table[path])
    dispatch_table[path] = (callback, schema)

def register_zone_manager(manager):
    global zone_manager
    zone_manager = manager

def handle_request(path, query):
    dispatch_data = dispatch_table.get(path)
    if dispatch_data is None:
        return
    (handler, _schema) = dispatch_data
    try:
        if query:
            if 'zone_id' in query:
                zone_id = int(query['zone_id'], 0)
                if zone_manager is not None and zone_manager.get(zone_id) is None:
                    return
                return handler(**query)
            return handler(**query)
        else:
            return handler()
    except Exception:
        logger.exception('Exception while handling a HTTP request to {}', path)
        return

def parse_args(spec, kwargs):
    for name in spec.args:
        arg_type = spec.annotations.get(name)
        if arg_type is not None and name in kwargs:
            kwargs[name] = _parse_arg(arg_type, kwargs[name], name)
    for name in spec.kwonlyargs:
        arg_type = spec.annotations.get(name)
        if arg_type is not None and name in kwargs:
            kwargs[name] = _parse_arg(arg_type, kwargs[name], name)
    return kwargs

def _parse_arg(arg_type, arg_value, name):
    if isinstance(arg_value, str):
        if arg_type is bool:
            if arg_value == 'true':
                return True
            if arg_value == 'false':
                return False
            logger.error("Invalid entry specified for bool {}: {} (Expected 'true' for True, or 'false' for False.)", name, arg_value)
            bool(arg_value)
        try:
            if arg_type is int:
                return int(arg_value, base=0)
            return arg_type(arg_value)
        except Exception:
            logger.error('Invalid entry specified for {} {}: {}', arg_type.__name__, name, arg_value)
            raise
    return arg_value

@GsiHandler('directory', None)
def directory_handler(client_version:int=CLIENT_GSI_BASE_VERSION):
    global gsi_client_version
    if client_version < gsi_client_version:
        logger.error('WARNING: Opening a second GSI Client on the same server and the client version is being changed from {} to {}'.format(gsi_client_version, client_version))
    gsi_client_version = client_version
    directory = {'gsi_server_version': LATEST_GSI_SERVER_VERSION}
    for (path, (_callback, schema)) in dispatch_table.items():
        if path != 'directory' and ARCHIVE_TOGGLE_SUFFIX not in path:
            directory[path] = schema
    return directory
