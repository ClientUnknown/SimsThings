import _traceimport builtinsimport datetimeimport osimport reimport sysimport textwrapimport tracebackfrom sims4.console_colors import ConsoleColorfrom singletons import DEFAULTimport debug_breakpointimport macrosimport sims4.console_colorsERROR_DIALOG_MESSAGE_LINELENGTH = 120TYPE_ASSERT = _trace.TYPE_ASSERTTYPE_VERIFY = _trace.TYPE_VERIFYTYPE_TRACE = _trace.TYPE_TRACETYPE_FAIL = _trace.TYPE_FAILTYPE_LOG = _trace.TYPE_LOGLEVEL_UNDEFINED = _trace.LEVEL_UNDEFINEDLEVEL_DEBUG = _trace.LEVEL_DEBUGLEVEL_INFO = _trace.LEVEL_INFOLEVEL_WARN = _trace.LEVEL_WARNLEVEL_ERROR = _trace.LEVEL_ERRORLEVEL_EXCEPTION = _trace.LEVEL_FATALLEVEL_FATAL = _trace.LEVEL_FATALRESULT_NONE = _trace.RESULT_NONERESULT_BREAK = _trace.RESULT_BREAKRESULT_DISABLE = _trace.RESULT_DISABLEASSERT_RESULT_RETRY = 2ASSERT_RESULT_IGNORE = 3ASSERT_RESULT_DISABLE = 5CONSOLE_COLORS = {LEVEL_EXCEPTION: ConsoleColor.YELLOW | ConsoleColor.BG_DARK_RED, LEVEL_ERROR: ConsoleColor.RED, LEVEL_WARN: ConsoleColor.YELLOW, (LEVEL_INFO, 'Always'): ConsoleColor.BLUE, (LEVEL_INFO, 'Status'): ConsoleColor.GREEN}sim_error_dialog_enabled = Truesim_error_dialog_ignore = set()callback_on_error_or_exception = Nonecallback_on_error_in_progress = FalseGSI_DUMP_STR = '[GSI_DUMP]'config = _trace.configreset = _trace.resetset_level = _trace.set_levelif hasattr(_trace, 'should_trace'):
    should_trace = _trace.should_trace
else:

    def should_trace(trace_type, group, level):
        return True
ring_bell_on_exception = False
def call_callback_on_error_or_exception(message):
    global callback_on_error_in_progress
    if not callback_on_error_in_progress:
        try:
            callback_on_error_in_progress = True
            callback_on_error_or_exception(message)
        except:
            pass
        finally:
            callback_on_error_in_progress = False

def get_console_color(level, group):
    key = (level, group)
    if key in CONSOLE_COLORS:
        return CONSOLE_COLORS[key]
    else:
        key = level
        if key in CONSOLE_COLORS:
            return CONSOLE_COLORS[key]
    return -1

def get_log_zone():
    from sims4.zone_utils import zone_numbers
    zone_id = sims4.zone_utils.zone_id
    return zone_numbers[zone_id]

def format_exc(exc=None):
    if exc is None:
        tb = traceback.format_exc()
    else:
        tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    return tb

def message(message, *args, owner=None):
    if owner:
        message = ('[{owner}] ' + message).format(*args, owner=owner)
    elif args:
        message = message.format(*args)
    frame = sys._getframe(1)
    return _trace.trace(TYPE_TRACE, message, frame=frame)

def log(group, message, *args, level, frame=DEFAULT, owner=None):
    if owner:
        message = ('[{owner}] ' + message).format(*args, owner=owner)
    elif args:
        message = message.format(*args)
    if frame is DEFAULT:
        frame = sys._getframe(1)
    return _trace.trace(TYPE_LOG, message, group, level, get_log_zone(), frame, color=get_console_color(level, group))

def blank_line(group, level, frame, ring_bell=False):
    bell = '\x07' if ring_bell else ''
    if frame is DEFAULT:
        frame = sys._getframe(1)
    _trace.trace(TYPE_LOG, bell + '\r' + '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t', group, level, get_log_zone(), frame, color=ConsoleColor.BG_YELLOW | ConsoleColor.DARK_RED)

def exception(group, message, *args, exc=None, log_current_callstack=True, frame=DEFAULT, use_format_stack=False, level=LEVEL_EXCEPTION, owner=None):
    if owner:
        message = ('[{owner}] ' + message).format(*args, owner=owner)
    elif args:
        message = message.format(*args)
    if frame is DEFAULT:
        frame = sys._getframe(1)
    if exc is None:
        (exc_type, exc, exc_tb) = sys.exc_info()
        log_current_callstack_prefix = ''
    else:
        exc_type = type(exc)
        exc_tb = exc.__traceback__
        log_current_callstack_prefix = 'Caught and logged:\n'
    if callback_on_error_or_exception is not None:
        message = GSI_DUMP_STR + message
    tb = format_exc(exc)
    if use_format_stack:
        dialog_text = ''.join(traceback.format_stack(frame))
    else:
        dialog_text = tb
    if exc is not None:
        try:
            headline = str(exc)
        except:
            headline = '<unprintable exception {}>'.format(type(exc).__name__)
        match = re.match("'NoneType' object has no attribute '(.*)'", headline)
        if match:
            attr = match.group(1)
            offending_line = tb.splitlines()[-2]
            match = re.match('\\s*(?:.* = |if |elif |else |for |while )?(.+)\\.{}\\b.*'.format(attr), offending_line)
            if match:
                headline = '"{}" was unexpectedly None'.format(match.group(1))
        classname = exc_type.__name__
        if classname in headline:
            headline = ' ({})'.format(headline)
        elif headline:
            headline = ' ({}: {})'.format(classname, headline)
        else:
            headline = ' ({})'.format(classname)
        message += headline
    message_base = message
    tbx = tb.split('\n', 1)
    message += '\n' + tbx[0] + '\n'
    if log_current_callstack:
        message += log_current_callstack_prefix
        message += ''.join(traceback.format_stack(frame))
    message += tbx[1]
    blank_line(group, level, frame, ring_bell=ring_bell_on_exception)
    _trace.trace(TYPE_LOG, message, group, level, get_log_zone(), frame, color=get_console_color(level, group))
    call_callback_on_error_or_exception(message)
    errorLog = '<report><version>2</version><sessionid>%s</sessionid><type>desync</type>'
    errorLog += '<sku>%s</sku><createtime>'
    errorLog += datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    errorLog += '</createtime><buildsignature>%s</buildsignature>'
    errorLog += '<categoryid>%s</categoryid>'
    errorLog += '<desyncid>%s</desyncid>'
    errorLog += '<systemconfig/><screenshot/>'
    errorLog += '<desyncdata>%s</desyncdata></report>\n'
    _trace.log_exception(errorLog, message, frame)
    sim_error_dialog(message_base, exc_tb, dialog_text, level=level)

def sim_error_dialog(message, exc_tb, exc_tb_text, level=LEVEL_EXCEPTION):
    global sim_error_dialog_enabled
    return
    if level < LEVEL_ERROR:
        return
    exc_fname = 'unknown'
    exc_line = 0
    if exc_tb is not None:
        cur_frame = exc_tb
        depth = 0
        max_depth = 100
        while cur_frame and depth < max_depth:
            depth += 1
            exc_line = cur_frame.tb_lineno
            exc_fname = cur_frame.tb_frame.f_code.co_filename
            cur_frame = cur_frame.tb_next
    exc_loc = (exc_fname, exc_line)
    if exc_loc in sim_error_dialog_ignore:
        return
    sim_id = 0
    obj_id_list = []
    exc_tb_text = exc_tb_text.replace('\n', os.linesep)
    message = textwrap.fill(message, width=ERROR_DIALOG_MESSAGE_LINELENGTH)
    message = message.replace('\n', os.linesep)
    result = _trace.show_sim_error(message, exc_tb_text, sim_id, obj_id_list)
    if result == ASSERT_RESULT_DISABLE:
        sim_error_dialog_enabled = False
    elif result == ASSERT_RESULT_IGNORE:
        sim_error_dialog_ignore.add(exc_loc)

def generate_message_with_callstack(message, *args, frame=DEFAULT, owner=None):
    if owner:
        message = ('[{owner}] ' + message).format(*args, owner=owner)
    elif args:
        message = message.format(*args)
    if frame is DEFAULT:
        frame = sys._getframe(1)
    tb = traceback.format_stack(frame)
    tb = ''.join(tb)
    return '{0}\n{1}'.format(message, tb)

def callstack(group, message, *args, level=LEVEL_DEBUG, frame=DEFAULT, owner=None):
    if frame is DEFAULT:
        frame = sys._getframe(1)
    msg = generate_message_with_callstack(message, *args, frame=frame, owner=owner)
    _trace.trace(TYPE_LOG, msg, group, level, get_log_zone(), frame, color=get_console_color(level, group))
vars(builtins)['_macro_should_trace'] = should_tracevars(builtins)['_macro_trace'] = _trace.tracevars(builtins)['_macro_get_log_zone'] = get_log_zonevars(builtins)['_macro_getframe'] = sys._getframevars(builtins)['_macro_ConsoleColor'] = ConsoleColorvars(builtins)['_macro_get_console_color'] = get_console_color
@macros.macro
def debug(group, message, *args, owner=None, trigger_breakpoint=False):
    pass

@macros.macro
def info(group, message, *args, owner=None, trigger_breakpoint=False):
    pass

@macros.macro
def warn(group, message, *args, owner=None, trigger_breakpoint=False):
    pass

@macros.macro
def error(group, message, *args, owner=None, trigger_breakpoint=False):
    pass

@macros.macro
def always(group, message, *args, owner=None, color:int=150, trigger_breakpoint=False):
    if owner:
        message = ('[{owner}] ' + message).format(*args, owner=owner)
    elif args:
        message = message.format(*args)
    _macro_trace(4, message, group, color, _macro_get_log_zone(), _macro_getframe(1), color=_macro_get_console_color(color, group))

@macros.macro
def assert_log(group, condition, message, *args, owner=None, trigger_breakpoint=False):
    pass

@macros.macro
def assert_raise(group, condition, message, *args, owner=None, trigger_breakpoint=False):
    if not condition:
        if owner:
            message = ('[{group}] [{owner}] ' + message).format(*args, group=group, owner=owner)
        else:
            message = ('[{group}] ' + message).format(*args, group=group)
        raise AssertionError(message)

class StackVar:

    def __init__(self, attr_names, check_privates=True, check_locals=True):
        self._attr_names = set(attr_names)
        self._check_privates = check_privates
        self._check_locals = check_locals
        self._attr_values = {}
        self._find_values()

    def __repr__(self):
        debug_str = '\n\nStackVar: '
        debug_str += '\n\tFound: '
        for (attr_name, attr_value) in self._attr_values.items():
            debug_str += '\n\t\t'
            debug_str += attr_name + ' = ' + str(attr_value)
        debug_str += '\n\tNot Found: '
        for attr_name in self._attr_names:
            debug_str += '\n\t\t'
            debug_str += attr_name
        return debug_str + '\n'

    def _find_values(self):
        stack_frame = sys._getframe(2)
        while stack_frame and self._attr_names:
            for attr_name in self._attr_names.copy():
                attr_value = None
                info_name = None
                stack_self = stack_frame.f_locals.get('self', None)
                if stack_self is not None:
                    if hasattr(stack_self, attr_name):
                        attr_value = getattr(stack_self, attr_name)
                        info_name = '(' + str(stack_self) + ').' + attr_name
                    if self._check_privates:
                        private_attr_name = '_{}'.format(attr_name)
                        if hasattr(stack_self, private_attr_name):
                            attr_value = getattr(stack_self, private_attr_name)
                            info_name = '(' + str(stack_self) + ').' + private_attr_name
                if attr_name in stack_frame.f_locals.keys():
                    attr_value = stack_frame.f_locals.get(attr_name)
                    info_name = 'Local Var ' + attr_name
                if attr_value is None and self._check_locals and attr_value is not None:
                    self._attr_values[info_name] = attr_value
                    self._attr_names.discard(attr_name)
            stack_frame = stack_frame.f_back

@macros.macro
class Logger:
    suppress = False

    def __init__(self, group, *, default_owner=None, key_words=None):
        self.group = group
        self.default_owner = default_owner
        self.key_words = None

    def log(self, message, *args, level, owner=None, trigger_breakpoint=False):
        pass

    def debug(self, message, *args, owner=None, trigger_breakpoint=False):
        pass

    def info(self, message, *args, owner=None, trigger_breakpoint=False):
        pass

    def warn(self, message, *args, owner=None, trigger_breakpoint=False):
        pass

    def error(self, message, *args, owner=None, trigger_breakpoint=False, trigger_callback_on_error_or_exception=True):
        pass

    def always(self, message, *args, owner=None, color:int=150, trigger_breakpoint=False):
        owner = owner or self.default_owner
        if owner:
            if args:
                message = ('[{owner}] ' + message).format(*args, owner=owner)
            else:
                message = '[' + owner + '] ' + message
        elif args:
            message = message.format(*args)
        if self.key_words is not None and not any(key_word in message.lower() for key_word in self.key_words):
            return
        _macro_trace(4, message, self.group, color, _macro_get_log_zone(), _macro_getframe(1), color=_macro_get_console_color(color, self.group))

    def exception(self, message, *args, exc=None, log_current_callstack=True, level=150, owner=None, trigger_breakpoint=False):
        if Logger.suppress:
            return
        if exc is None:
            try:
                frame1 = _macro_getframe(1)
                frame = _macro_getframe(2)
            except:
                frame = frame1
        else:
            frame = _macro_getframe(1)
        owner = owner or self.default_owner
        sims4.log.exception(self.group, message, *args, exc=exc, log_current_callstack=log_current_callstack, frame=frame, owner=owner, level=level)

    def callstack(self, message, *args, level=25, owner=None, trigger_breakpoint=False, trigger_gsi_dump=True):
        if Logger.suppress:
            return
        owner = owner or self.default_owner
        sims4.log.callstack(self.group, message, *args, level=level, owner=owner, frame=_macro_getframe(1))
        if trigger_gsi_dump and level == LEVEL_ERROR:
            call_callback_on_error_or_exception(message)

    def assert_log(self, condition, message, *args, **kwargs):
        if not condition:
            self.error(message, *args, **kwargs)

    def assert_raise(self, condition, message, *args, owner=None, trigger_breakpoint=False, **kwargs):
        if not condition:
            owner = owner or self.default_owner
            message = ('[{group}] [{owner}] ' + message).format(*args, group=self.group, owner=owner)
            raise AssertionError(message)

class _BaseLogger:
    __slots__ = ('group', 'default_owner')

    def __init__(self, group, default_owner=None):
        self.group = group
        self.default_owner = default_owner

    def __repr__(self):
        return 'Logger({}, default_owner={})'.format(self.group, self.default_owner)

    def log(self, *args, **kwargs):
        raise NotImplementedError

    def _log_for_level(level):

        def log_for_level(self, *args, **kwargs):
            return self.log(*args, level=level, **kwargs)

        return log_for_level

    debug = _log_for_level(LEVEL_DEBUG)
    info = _log_for_level(LEVEL_INFO)
    warn = _log_for_level(LEVEL_WARN)
    error = _log_for_level(LEVEL_ERROR)
    del _log_for_level

    def exception(self, message, *args, exc=None, **kwargs):
        message += '\n{}'
        args += (format_exc(exc),)
        return self.log(message, *args, exc=exc, **kwargs)

    def callstack(self, message, *args, **kwargs):
        message += '\n{}'
        args += (''.join(traceback.format_stack()),)
        return self.log(message, *args, **kwargs)

    def assert_log(self, condition, message, *args, level=LEVEL_ERROR, **kwargs):
        if not condition:
            self.log(message, *args, level=level, **kwargs)

    def assert_raise(self, condition, message, *args, owner=None, **kwargs):
        if not condition:
            owner = owner or self.default_owner
            message = ('[{group}] [{owner}] ' + message).format(*args, group=self.group, owner=owner)
            raise AssertionError(message)

class LoggerClass(_BaseLogger):
    __slots__ = ()

    def log(self, message, *args, level, frame=DEFAULT, owner=None, trigger_breakpoint=False, **kwargs):
        owner = owner or self.default_owner
        if owner:
            message = ('[{owner}] ' + message).format(*args, owner=owner)
        elif args:
            message = message.format(*args)
        if frame is DEFAULT:
            frame = sys._getframe(2)
        return _trace.trace(TYPE_LOG, message, self.group, level, get_log_zone(), frame)

    def exception(self, *args, exc=None, owner=None, **kwargs):
        if exc is None:
            frame = _macro_getframe(2)
        else:
            frame = _macro_getframe(1)
        owner = owner or self.default_owner
        return exception(self.group, *args, exc=exc, frame=frame, owner=owner, **kwargs)

    def callstack(self, *args, owner=None, **kwargs):
        frame = sys._getframe(1)
        owner = owner or self.default_owner
        return callstack(self.group, *args, frame=frame, owner=owner, **kwargs)

class ProductionLogger(_BaseLogger):
    __slots__ = ()

    def log(self, message, *args, level=LEVEL_DEBUG, owner=None, **kwargs):
        frame = sys._getframe(1)
        owner = owner or self.default_owner
        if owner:
            message = ('[{owner}] ' + message).format(*args, owner=owner)
        elif args:
            message = message.format(*args)
        return _trace.prod_trace(TYPE_LOG, message, self.group, level, frame)

class CheatLogger(_BaseLogger):
    __slots__ = ('output',)

    def __init__(self, group, connection, *, default_owner=None):
        from sims4.commands import Output
        self.output = Output(connection)
        self.group = group
        self.default_owner = default_owner

    def log(self, message, *args, owner=None, level=None, **kwargs):
        owner = owner or self.default_owner
        if owner:
            message = ('[{owner}] ' + message).format(*args, owner=owner)
        elif args:
            message = message.format(*args)
        return self.output(message)

class OverrideTrace:

    def __init__(self, new_trace, suppress_colors=False):
        self._new_trace = new_trace
        self._old_trace = None
        self._suppress_colors = suppress_colors

    def __enter__(self):
        self._old_trace = _trace.trace
        _trace.trace = self._new_trace
        self._old_colors = sims4.console_colors.colors_enabled
        sims4.console_colors.colors_enabled = not self._suppress_colors
        OverrideTrace._fixup_builtins()

    def __exit__(self, exc_type, exc_value, tb):
        if self._old_trace is not None:
            _trace.trace = self._old_trace
            self._old_trace = None
            sims4.console_colors.colors_enabled = self._old_colors
            OverrideTrace._fixup_builtins()

    @staticmethod
    def _fixup_builtins():
        if '_macro_trace' in vars(builtins):
            vars(builtins)['_macro_trace'] = _trace.trace
