try:
    import ctypes
    HAS_CTYPES = True
except ImportError:
    HAS_CTYPES = Falsetry:
    import stackless
    STACKLESS = True
except ImportError:
    STACKLESS = Falseimport sysif hasattr(sys, 'getobjects'):
    HEAD_EXTRA = True
else:
    HEAD_EXTRA = FalseIS_ABOVE_PY25 = Falsetry:
    if sys.version_info[1] >= 5:
        IS_ABOVE_PY25 = True
except AttributeError:
    passCO_MAXBLOCKS = 20MAX_LOCALS = 256if HAS_CTYPES:

    class PyTryBlockWrapper(ctypes.Structure):
        _fields_ = [('b_type', ctypes.c_int), ('b_handler', ctypes.c_int), ('b_level', ctypes.c_int)]

    class PyObjectHeadWrapper(ctypes.Structure):
        if HEAD_EXTRA:
            _fields_ = [('ob_next', ctypes.c_void_p), ('ob_prev', ctypes.c_void_p), ('ob_refcnt', ctypes.c_size_t), ('ob_type', ctypes.c_void_p)]
        else:
            _fields_ = [('ob_refcnt', ctypes.c_size_t), ('ob_type', ctypes.c_void_p)]

    class PyObjectHeadWrapperVar(ctypes.Structure):
        _anonymous_ = ['_base_']
        _fields_ = [('_base_', PyObjectHeadWrapper), ('ob_size', ctypes.c_size_t)]

    _frame_wrapper_fields = [('_base_', PyObjectHeadWrapperVar), ('f_back', ctypes.c_void_p)]
    if STACKLESS:
        _frame_wrapper_fields.append(('f_execute', ctypes.c_void_p))
    else:
        _frame_wrapper_fields.append(('f_code', ctypes.c_void_p))
    _frame_wrapper_fields += [('f_builtins', ctypes.py_object), ('f_globals', ctypes.py_object), ('f_locals', ctypes.py_object), ('f_valuestack', ctypes.POINTER(ctypes.c_void_p)), ('f_stacktop', ctypes.POINTER(ctypes.c_void_p)), ('f_trace', ctypes.c_void_p), ('f_exc_type', ctypes.c_void_p), ('f_exc_value', ctypes.c_void_p), ('f_exc_traceback', ctypes.c_void_p), ('f_tstate', ctypes.c_void_p), ('f_lasti', ctypes.c_int), ('f_lineno', ctypes.c_int), ('f_iblock', ctypes.c_int), ('f_blockstack', PyTryBlockWrapper*CO_MAXBLOCKS)]
    if STACKLESS:
        _frame_wrapper_fields.append(('f_code', ctypes.c_void_p))
    _frame_wrapper_fields.append(('f_localsplus', ctypes.py_object*MAX_LOCALS))

    class FrameWrapper(ctypes.Structure):
        _anonymous_ = ['_base_']
        _fields_ = _frame_wrapper_fields
if IS_ABOVE_PY25 and 'FrameWrapper' in globals():

    def save_locals(locals_dict, frame):
        co = frame.f_code
        frame_pointer = ctypes.c_void_p(id(frame))
        frame_wrapper = ctypes.cast(frame_pointer, ctypes.POINTER(FrameWrapper))
        for (i, name) in enumerate(co.co_varnames):
            if name in locals_dict:
                frame_wrapper[0].f_localsplus[i] = locals_dict[name]
