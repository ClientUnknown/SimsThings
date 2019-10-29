import builtinsimport functoolsimport inspectimport os.pathimport pathsimport randomimport sysimport timeimport weakrefimport sims4.logimport sims4.repr_utilslogger = sims4.log.Logger('Utils')
def decorator(user_decorator):

    @functools.wraps(user_decorator)
    def better_user_decorator(fn=None, **kwargs):
        if fn is None:
            return lambda fn: user_decorator(fn, **kwargs)
        if not callable(fn):
            raise TypeError('[bhill] Non-function arguments must be passed to the decorator as keyword arguments.')
        return user_decorator(fn, **kwargs)

    return better_user_decorator

def find_class_by_name(name):
    parts = name.rsplit('.', 1)
    if len(parts) != 2:
        raise ValueError('Name {0} must be fully qualified'.format(name))
    (path, class_name) = parts
    builtins.__import__(path)
    module = sys.modules[path]
    if module is None:
        raise ValueError('Path {0} is not a valid module'.format(path))
    cls = vars(module).get(class_name)
    if cls is None:
        raise ValueError('Type {0} in module {1} does not exist'.format(class_name, path))
    if not isinstance(cls, type):
        raise ValueError('Name {0} is not a type'.format(name))
    return cls

def filename_to_module_fqn(filename):
    prefix_list = sorted([os.path.commonprefix([os.path.abspath(m), filename]) for m in sys.path if filename.startswith(os.path.abspath(m))], key=len, reverse=True)
    if not prefix_list:
        logger.error('Path {0} not under sys.path: {1}', filename, sys.path)
        return
    prefix = prefix_list[0]
    rel_path = os.path.relpath(filename, prefix)
    norm_path = os.path.normpath(rel_path)
    module_name = norm_path.replace('.py', '')
    module_name = module_name.replace('\\__init__', '')
    fqn = module_name.translate(str.maketrans('\\/', '..'))
    fqn = fqn.strip('.')
    return fqn

def get_nested_class_list(cls):
    return [cls.__module__] + cls.__qualname__.split('.')

def all_subclasses(cls):
    subclasses = []
    pending = cls.__subclasses__()
    while pending:
        subclass = pending.pop()
        subclasses.append(subclass)
        pending.extend(subclass.__subclasses__())
    return subclasses

@decorator
def c_api_can_fail(fn, error_return_values=(-1,)):

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        ret = fn(*args, **kwargs)
        if ret in error_return_values:
            logger.error('Invoke of {} returned error code: {}', fn, ret)
        return ret

    return wrapper

@decorator
def exception_protected(fn, default_return=None, log_invoke=False):

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            if log_invoke:
                logger.info('Invoking {} with args {}', fn, args)
                ret = fn(*args, **kwargs)
                logger.info('Invoked {} Successfully', fn)
                return ret
            return fn(*args, **kwargs)
        except Exception as exception:
            try:
                logger.exception('Exception in {}, args: {}, kwargs: {}\n{!r}', fn, args, kwargs, exception)
            except Exception as logging_exception:
                logger.error('Exception while logging exception in {}, args: {}, kwargs: {}Exception being logged:\n{!r}', fn, args, kwargs, exception)
                logger.error('Exception was {!r}', logging_exception)
            return default_return

    return wrapper

class flexproperty:
    __slots__ = ('fget',)

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, inst, owner):
        return self.fget(owner, inst)

class flexmethod:
    __slots__ = ('__wrapped_method__',)

    def __init__(self, method):
        self.__wrapped_method__ = method

    def __get__(self, instance, owner):
        return functools.partial(self.__wrapped_method__, owner, instance)

class classproperty:
    __slots__ = ('fget',)

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, inst, owner):
        return self.fget(owner)

    @staticmethod
    def __reload_update__(oldobj, newobj, update_fn):
        oldobj.fget = newobj.fget
        return oldobj

class staticproperty:
    __slots__ = ('fget',)

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, inst, owner):
        return self.fget()

    @staticmethod
    def __reload_update__(oldobj, newobj, update_fn):
        oldobj.fget = newobj.fget
        return oldobj

def constproperty(fn):
    return fn()

def setdefault_callable(collection, key, default_callable):
    if key in collection:
        return collection[key]
    value = collection[key] = default_callable()
    return value

def enumerate_reversed(sequence):
    for i in range(len(sequence) - 1, -1, -1):
        yield (i, sequence[i])

class Result:
    __slots__ = ('value', 'reason')
    TRUE = None
    CANCELED = None
    ROUTE_PLAN_FAILED = None
    ROUTE_FAILED = None

    def __init__(self, value, reason=None):
        self.value = value
        self.reason = reason

    def __bool__(self):
        if self.value:
            return True
        return False

    def __repr__(self):
        if self.reason:
            return sims4.repr_utils.standard_repr(self, self.value, repr(self.reason))
        return sims4.repr_utils.standard_repr(self, self.value)
Result.TRUE = Result(True)Result.CANCELED = Result(False, 'Canceled.')Result.ROUTE_PLAN_FAILED = Result(False, 'Route plan failed.')Result.ROUTE_FAILED = Result(False, 'Route failed.')Result.NO_RUNTIME_SLOTS = Result(False, 'No Runtime Slots')
class RegistryHandle:

    def __init__(self, release_fn):
        self._release_fn = release_fn

    def release(self):
        if self._release_fn is not None:
            self._release_fn()
            self._release_fn = None

def create_csv(filename:str, callback=None, connection=None):
    if filename is None or callback is None:
        return
    output = None
    if connection is not None:
        output = sims4.commands.CheatOutput(connection)
    current_time = time.strftime('%Y-%m-%d-%H-%M-%S', time.gmtime())
    file_path = '{}_{}.csv'.format(filename, current_time)
    if not os.path.isabs(file_path):
        file_path = os.path.join(paths.DUMP_ROOT, file_path)
    with open(file_path, 'w') as fd:
        try:
            callback(fd)
        except Exception as e:
            if output is not None:
                output('Exception when writing to file {}.\n{}'.format(file_path, e))
    if output is not None:
        output('File written at the executable directory: {}.'.format(file_path))

class ImmutableType:

    def __hash__(self):
        return hash(frozenset(self.__dict__.items()))

    def __eq__(self, other):
        if other is self:
            return True
        return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

    def __delattr__(self, attr):
        raise AttributeError("Cannot delete attributes on immutable {}. It's supposed to be immutable. [bhill]".format(type(self).__qualname__))

class InternMixin:
    __slots__ = ()

    def intern(self):
        try:
            return self._interned_instances[self]
        except KeyError:
            self._interned_instances[self] = self
        except AttributeError:
            self.__class__._interned_instances = {self: self}
        return self

class strformatter:
    __slots__ = ('s', 'args')

    def __init__(self, s, *args):
        self.s = s
        self.args = args

    def __str__(self):
        return self.s.format(*self.args)
