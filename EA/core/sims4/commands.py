import inspectimport reimport enumimport pathsimport sims4.commonimport sims4.logimport sims4.reloadimport sims4.telemetry__enable_native_commands = Truetry:
    import _commands
except:
    __enable_native_commands = False
class CommandType(enum.Int, export=False):
    DebugOnly = 1
    Automation = 3
    Cheat = 4
    Live = 5

class CommandRestrictionFlags(enum.IntFlags, export=False):
    UNRESTRICTED = 0
    RESTRICT_SAVE_UNLOCKED = 1
logger = sims4.log.Logger('Commands')TELEMETRY_GROUP_CHEATS = 'CHTS'TELEMETRY_HOOK_INTERACTION = 'NTRC'TELEMETRY_HOOK_COMMAND = 'CMND'TELEMETRY_FIELD_NAME = 'name'TELEMETRY_FIELD_TARGET = 'trgt'TELEMETRY_FIELD_ARGS = 'args'cheats_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_CHEATS)BOOL_TRUE = {'t', 'true', 'on', '1', 'yes', 'y', 'enable'}BOOL_FALSE = {'f', 'false', 'off', '0', 'no', 'n', 'disable'}NO_CONTEXT = 18446744073709551615with sims4.reload.protected(globals()):
    is_command_available = lambda command_type: True
def add_command_restrictions(*_, **__):
    pass

def get_command_restrictions(*_, **__):
    return CommandRestrictionFlags.UNRESTRICTED

def add_command_type(*_, **__):
    pass

def get_command_type(*_, **__):
    return CommandType.Live

def get_command_info_gen(*_, **__):
    pass

def register(name, restrictions, handler, description, usage, command_type):
    if __enable_native_commands:
        _commands.register(name, description, usage, handler)

def unregister(name):
    if __enable_native_commands:
        _commands.unregister(name)

def execute(command_line, _connection):
    if __enable_native_commands:
        if _connection is None:
            _connection = 0
        _commands.execute(command_line, _connection)

def describe(search_string=None):
    if __enable_native_commands:
        return _commands.describe(search_string)
    return []

def output(s, context):
    pass

def cheat_output(s, context):
    if __enable_native_commands:
        if context != NO_CONTEXT:
            _commands.output(s, context)
        else:
            logger.always(s)

def automation_output(s, context=0):
    if __enable_native_commands:
        if context != NO_CONTEXT:
            _commands.automation_output(s, context)
        else:
            sims4.log.always('Automation', s)

def client_cheat(s, context):
    logger.assert_log(context, 'Invoking client command with invalid context. command: {}, context: {}', s, context, owner='tingyul')
    if __enable_native_commands:
        _commands.client_cheat(s, context)
REMOVE_ACCOUNT_ARG = re.compile('(, ?)?_account=None', flags=re.IGNORECASE)
def prettify_usage(usage_string):
    usage_string = re.sub(REMOVE_ACCOUNT_ARG, '', usage_string)
    return usage_string

class CustomParam:
    pass

def parse_args(spec, args, account):
    args = list(args)
    for (name, index) in zip(spec.args, range(len(args))):
        arg_type = spec.annotations.get(name)
        if arg_type is not None:
            arg_value = args[index]
            _parse_arg(spec, args, arg_type, arg_value, name, index, account)
    index = 0
    for (name, index) in zip(spec.args, range(len(spec.args))):
        arg_type = spec.annotations.get(name)
        if index < len(args) and isinstance(arg_type, type) and issubclass(arg_type, CustomParam):
            arg_value = args[index]
            if not isinstance(arg_value, arg_type):
                args[index] = arg_type(arg_value)
    if spec.varargs is not None:
        arg_type = spec.annotations.get(spec.varargs)
        if arg_type is not None:
            index += 1
            vararg_list = args[index:]
            name = spec.varargs
            for arg_value in vararg_list:
                _parse_arg(spec, args, arg_type, arg_value, name, index, account)
                index += 1
    return args

def _parse_arg(spec, args, arg_type, arg_value, name, index, account):
    if isinstance(arg_value, str):
        if arg_type is bool:
            lower_arg_value = arg_value.lower()
            if lower_arg_value in BOOL_TRUE:
                args[index] = True
            elif lower_arg_value in BOOL_FALSE:
                args[index] = False
            else:
                output('Invalid entry specified for bool {}: {} (Expected one of {} for True, or one of {} for False.)'.format(name, arg_value, BOOL_TRUE, BOOL_FALSE), account)
                raise ValueError('invalid literal for boolean parameter')
        else:
            try:
                if arg_type is int:
                    args[index] = int(arg_value, base=0)
                else:
                    args[index] = arg_type(arg_value)
            except Exception as exc:
                output("Invalid value for {}: '{}' ({})".format(name, arg_value, exc), account)
                if issubclass(arg_type, enum.EnumBase):
                    output('Valid values are: {}{}'.format(', '.join(a.name for a in list(arg_type)[:10]), '...' if len(arg_type) > 10 else ''), account)
                raise

def zone_id_from_args(spec, args):
    for (name, index) in zip(spec.args, range(len(args))):
        if name == 'zone_id':
            arg_value = args[index]
            return arg_value
    return 0

def Command(*aliases, command_type=CommandType.DebugOnly, command_restrictions=CommandRestrictionFlags.UNRESTRICTED, pack=None, console_type=None):
    if console_type is not None and not paths.IS_DESKTOP:
        relevant_type = console_type
    else:
        relevant_type = command_type
    if console_type is not None:
        most_limited_type = min(command_type, console_type)
    else:
        most_limited_type = command_type

    def is_valid_command():
        if relevant_type == CommandType.DebugOnly:
            return False
        elif pack and not sims4.common.is_available_pack(pack):
            return False
        return True

    def named_command(func):
        if not is_valid_command():
            return
        name = aliases[0]
        full_arg_spec = inspect.getfullargspec(func)

        def invoke_command(*args, _session_id=0, **kw):
            if '_account' in full_arg_spec.args or '_account' in full_arg_spec.kwonlyargs:
                kw['_account'] = _session_id
            if '_connection' in full_arg_spec.args or '_connection' in full_arg_spec.kwonlyargs:
                kw['_connection'] = _session_id
            args = parse_args(full_arg_spec, args, _session_id)
            try:
                if not is_command_available(relevant_type):
                    return
                if relevant_type == CommandType.Cheat:
                    with sims4.telemetry.begin_hook(cheats_writer, TELEMETRY_HOOK_COMMAND) as hook:
                        hook.write_string(TELEMETRY_FIELD_NAME, name)
                        hook.write_string(TELEMETRY_FIELD_ARGS, str(args))
                return func(*args, **kw)
            except BaseException as e:
                output('Error: {}'.format(e), _session_id)
                logger.warn('Error executing command')
                raise

        invoke_command.__name__ = 'invoke_command ({})'.format(name)
        usage = prettify_usage(str.format(inspect.formatargspec(*full_arg_spec)))
        description = ''
        for alias in aliases:
            register(alias, command_restrictions, invoke_command, description, usage, most_limited_type)
        return func

    return named_command

class Output:
    __slots__ = ('_context',)

    def __init__(self, context):
        self._context = context

    def __call__(self, s):
        output(s, self._context)

class CheatOutput(Output):

    def __call__(self, s):
        cheat_output(s, self._context)

class AutomationOutput:
    __slots__ = ('_context',)

    def __init__(self, context):
        self._context = context

    def __call__(self, s):
        automation_output(s, self._context)

class FileOutput:
    __slots__ = ('_context', '_file_path')

    def __init__(self, file_path, context):
        self._file_path = file_path
        if not paths.AUTOMATION_MODE:
            self._file_path = None
        if self._file_path is not None:
            output('Saving command output to {}'.format(self._file_path), context)

    def __call__(self, s):
        if self._file_path is not None:
            with open(self._file_path, 'a') as f:
                f.write('{0}\n'.format(s))

class NoneIntegerOrString(CustomParam):

    def __new__(cls, value:str):
        if value == 'None':
            return
        try:
            return int(value, 0)
        except:
            pass
        return value
