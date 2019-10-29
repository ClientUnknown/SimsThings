import collectionsimport gcimport itertoolsimport structimport sysfrom types import FunctionType, ModuleType
def recursive_sizeof(roots, skip_atomic=False):
    handler_cache = {}
    pending = collections.deque((root, root) for root in roots)
    visited = set()
    sizes = {id(root): 0 for root in roots}
    while pending:
        (obj, root) = pending.popleft()
        if id(obj) in visited:
            pass
        else:
            if skip_atomic and gc.is_tracked(obj):
                sizes[id(root)] += sys.getsizeof(obj)
            visited.add(id(obj))
            for child in enumerate_children(obj, handler_cache, HANDLERS):
                if child is None:
                    pass
                else:
                    pending.append((child, root))
    results = []
    for root in roots:
        results.append((root, sizes[id(root)]))
    return results

def report(labeled_roots, skip_atomic=False):
    labels = []
    roots = []
    for (label, root) in labeled_roots:
        labels.append(label)
        roots.append(root)
    results = recursive_sizeof(roots, skip_atomic=skip_atomic)
    counter = collections.Counter()
    for (label, (root, size)) in zip(labels, results):
        counter[label] += size
    return counter

class Node:
    __slots__ = ('sep', 'name', 'obj', 'size', 'sizerec', 'parent', 'child', 'sibling')

    def __init__(self, sep, name, obj, size):
        self.sep = sep
        self.name = name
        self.obj = obj
        self.size = size
        self.sizerec = 0
        self.parent = None
        self.child = None
        self.sibling = None

    def add_child(self, node):
        node.parent = self
        node.sibling = self.child
        self.child = node

    def __str__(self):
        obj = self
        name = ''
        while obj is not None:
            name = '{}{}{}'.format(obj.sep, obj.name, name)
            obj = obj.parent
        return name

def calc_sizerec(node):
    pending = [(node, None)]
    while pending:
        (first, second) = pending.pop()
        if first is not None:
            first.sizerec = first.size
            pending.append((None, first))
            child = first.child
            while child is not None:
                pending.append((child, None))
                child = child.sibling
        elif second is not None and second.parent is not None:
            second.parent.sizerec += second.sizerec

def get_object_tree(labeled_roots, skip_atomic=False, allowed_ids=None, bfs=True, include_cycles=False):
    handler_cache = {}
    root = Node('', 'Root', None, 0)
    visited = {id(root)}
    pending = collections.deque([(obj, '', name, root) for (name, obj) in labeled_roots])
    if pending:
        if bfs:
            (obj, sep, name, parent) = pending.popleft()
        else:
            (obj, sep, name, parent) = pending.pop()
        obj_id = id(obj)
        if obj_id in visited:
            pass
        else:
            visited.add(obj_id)
            if allowed_ids is not None and obj_id not in allowed_ids:
                pass
            elif skip_atomic and not gc.is_tracked(obj):
                pass
            else:
                size = sys.getsizeof(obj)
                node = Node(sep, name, obj, size)
                parent.add_child(node)
                try:
                    for (sep, field, child) in enumerate_children(obj, handler_cache, FIELD_HANDLERS):
                        if child is None:
                            pass
                        elif allowed_ids is not None and id(child) not in allowed_ids:
                            pass
                        elif id(child) in visited:
                            if include_cycles:
                                child_node = Node(sep, field + '&', child, 0)
                                node.add_child(child_node)
                                pending.append((child, sep, field, node))
                        else:
                            pending.append((child, sep, field, node))
                except:
                    pass
    calc_sizerec(root)
    return root

def _store_string(string_table, s):
    if s in string_table:
        return string_table[s]
    index = len(string_table)
    string_table[s] = index
    return index

def write_object_tree(node, fd):
    pending = [node]
    ns = struct.Struct('<4QL1s3L')
    string_table = collections.OrderedDict()
    fd.write(struct.pack('=b', 1))
    node_count = 0
    node_count_offset = fd.tell()
    fd.write(struct.pack('<Q', 0))
    while pending:
        node_count += 1
        node = pending.pop()
        parent_id = id(node.parent.obj) if node.parent is not None else 0
        fd.write(ns.pack(id(node.obj), parent_id, id(type(node.obj)), node.sizerec, node.size, node.sep.encode('utf-8'), sys.getrefcount(node.obj), _store_string(string_table, node.name), _store_string(string_table, short_str(node.obj))))
        child = node.child
        while child is not None:
            pending.append(child)
            child = child.sibling
    string_table_offset = fd.tell()
    fd.seek(node_count_offset)
    fd.write(struct.pack('<Q', node_count))
    fd.seek(string_table_offset)
    fd.write(struct.pack('<Q', len(string_table)))
    for s in string_table:
        try:
            utf8 = s.encode('utf-8', errors='xmlcharrefreplace')
        except:
            utf8 = ('UTF-8 error: ' + repr(s)).encode('utf-8', errors='replace')
        fd.write(struct.pack('<L', len(utf8)))
        fd.write(utf8)

def enumerate_children(obj, handler_cache, handlers):
    t = type(obj)
    if t not in handler_cache:
        for st in t.__mro__:
            handler = handlers.get(st)
            if handler is not None:
                handler_cache[t] = handler
                break
        handler_cache[t] = None
    handler = handler_cache[t]
    if handler is not None:
        return handler(obj)
    return ()

def object_iter(obj):
    children = []
    for attr in dir(obj):
        try:
            v = getattr(obj, attr, None)
        except:
            continue
        ref = sys.getrefcount(v)
        if not v is None:
            if ref <= 2:
                pass
            else:
                children.append(v)
    return children

def module_iter(module):
    name = module.__name__
    members = []
    module_dict = vars(module)
    for value in module_dict.values():
        if isinstance(value, (type, FunctionType)) and value.__module__ != name:
            pass
        else:
            members.append(value)
    members.append(vars(module))
    return members
child_iter = iterdict_iter = lambda obj: itertools.chain.from_iterable(obj.items())HANDLERS = {ModuleType: module_iter, object: object_iter, dict: dict_iter, tuple: child_iter, set: child_iter, list: child_iter, frozenset: child_iter, collections.deque: child_iter}
def safe_str(obj):
    try:
        return str(obj)
    except:
        pass
    try:
        return object.__str__(obj)
    except:
        pass
    try:
        t = type(obj)
        return '<{}.{} object at {:#X}>'.format(t.__module__, t.__qualname__, id(obj))
    except:
        pass
    return '<??? object at {:#X}>'.format(id(obj))

def short_str(obj, maxlen=64, tail=17):
    s = safe_str(obj)
    if len(s) > maxlen:
        s = '{}...{}'.format(s[0:maxlen - tail - 3], s[len(s) - tail:])
    return s

def list_fields(obj):
    for (i, value) in enumerate(obj):
        field = sys.intern('[{}]'.format(i))
        yield ('', field, value)

def dict_fields(obj):
    try:
        for (key, value) in obj.items():
            yield ('.', short_str(key), value)
    except:
        pass
    yield from list_fields(obj)

def module_fields(module):
    name = module.__name__
    members = []
    module_dict = vars(module)
    for (name, value) in module_dict.items():
        if isinstance(value, (type, FunctionType)) and value.__module__ != name:
            pass
        else:
            members.append(('.', name, value))
    return members

def object_fields(obj):
    children = []
    children.append(('.', '__type__', type(obj)))
    ids = set()
    ids.add(id(type(obj)))
    ref_ids = set(id(v) for v in gc.get_referents(obj))
    for attr in dir(obj):
        if attr == '__qualname__':
            pass
        else:
            try:
                v = getattr(obj, attr, None)
            except:
                continue
            vid = id(v)
            if vid not in ref_ids:
                pass
            else:
                ids.add(vid)
                ref = sys.getrefcount(v)
                if not v is None:
                    if ref <= 2:
                        pass
                    elif attr == '__annotations__' and ref == 3 and not v:
                        delattr(obj, attr)
                    else:
                        children.append(('.', attr, v))
    refs = gc.get_referents(obj)
    for v in refs:
        if id(v) not in ids:
            children.append(('.', '<gcref>', v))
    return children
FIELD_HANDLERS = {ModuleType: module_fields, object: object_fields, dict: dict_fields, tuple: list_fields, set: list_fields, list: list_fields, frozenset: list_fields, collections.deque: list_fields}