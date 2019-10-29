import typesimport time
def create_labeled_profiler_function(self, label, fn):
    code = fn.__code__
    filename = code.co_filename.replace('.py', '') + '_' + label
    y_code = types.CodeType(code.co_argcount, code.co_kwonlyargcount, code.co_nlocals, code.co_stacksize, code.co_flags, code.co_code, code.co_consts, code.co_names, code.co_varnames, filename, code.co_name, code.co_firstlineno, code.co_lnotab, code.co_freevars, code.co_cellvars)
    profiler_fn = types.FunctionType(y_code, fn.__globals__, fn.__name__, fn.__defaults__, fn.__closure__)
    return types.MethodType(profiler_fn, self)

def create_custom_named_profiler_function(name, use_generator=False):
    name = name[:32]
    if use_generator:

        def y(fn):
            result = yield from fn()
            return result

    else:

        def y(fn):
            return fn()

    y_code = types.CodeType(y.__code__.co_argcount, y.__code__.co_kwonlyargcount, y.__code__.co_nlocals, y.__code__.co_stacksize, y.__code__.co_flags, y.__code__.co_code, y.__code__.co_consts, y.__code__.co_names, y.__code__.co_varnames, y.__code__.co_filename, name, hash(name) % 2147483648, y.__code__.co_lnotab)
    return types.FunctionType(y_code, y.__globals__, name)

class _TimedContext:

    def __init__(self):
        self._enter_time = None
        self.elapsed_seconds = 0.0

    def reset(self):
        self.elapsed_seconds = 0.0

    def __enter__(self):
        self._enter_time = time.perf_counter()

    def __exit__(self, exc_type, exc_val, exc_tb):
        now = time.perf_counter()
        delta = now - self._enter_time
        self._enter_time = None
        self.elapsed_seconds += delta
        return False

class _TimedContextStub:

    def __init__(self):
        pass

    @property
    def elapsed_seconds(self):
        return 0.0

    def reset(self):
        pass

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

def get_timed_context(is_profiling):
    if is_profiling:
        return _TimedContext
    else:
        return _TimedContextStub
TimedContext = _TimedContextStub