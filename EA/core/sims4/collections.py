from _pythonutils import tupledescriptorfrom _sims4_collections import frozendictimport collectionsimport sims4.logfrom singletons import SingletonTypelogger = sims4.log.Logger('Collections')CACHED_IMMUTABLE_SLOTS = {}CACHED_TUPLE_DESCRIPTORS = {}
class ListSet(list):
    __slots__ = ()

    def __init__(self, iterable=()):
        super().__init__(())
        self.update(iterable)

    def add(self, value):
        if value not in self:
            super().append(value)

    def update(self, iterable):
        for value in iterable:
            self.add(value)

    def discard(self, value):
        if value in self:
            self.remove(value)

    def __eq__(self, other_set):
        if len(self) != len(other_set):
            return False
        return all(i in self for i in other_set)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __getitem__(self, key):
        raise TypeError('ListSet object does not support indexing.')

    def __setitem__(self, key, value):
        raise TypeError('ListSet object does not support item assignment.')

    def __delitem__(self, key):
        raise TypeError('ListSet object does not support item deletion.')

    append = extend = __add__ = None

class AttributeDict(dict):
    __slots__ = ()
    __dict__ = property(lambda self: self)
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __getattr__(self, name):
        try:
            return dict.__getitem__(self, name)
        except KeyError:
            raise AttributeError("Key '{}' not found in {}".format(name, self))

    def __repr__(self):
        return '{}({})'.format(type(self).__name__, dict.__repr__(self))

    def copy(self):
        return self.__class__(self.items())

class FrozenAttributeDict(AttributeDict, frozendict):
    __slots__ = ()
    __setattr__ = frozendict.__setitem__
    __delattr__ = frozendict.__delitem__

    def clone_with_overrides(self, **kwargs):
        return self.__class__(self.items(), **kwargs)

class RestrictedFrozenAttributeDict(FrozenAttributeDict):
    __slots__ = ()

    def __bool__(self):
        return True

    def __len__(self):
        raise TypeError("'RestrictedFrozenAttributeDict' object does not support __len__.")

    def __contains__(self, key):
        raise TypeError("'RestrictedFrozenAttributeDict' object does not support __contains__.")

    def __getitem__(self, index):
        raise TypeError("'RestrictedFrozenAttributeDict' object does not support __getitem__.")

    def __setitem__(self, index, value):
        raise TypeError("'RestrictedFrozenAttributeDict' object does not support __setitem__.")

    def __delitem__(self, index):
        raise TypeError("'RestrictedFrozenAttributeDict' object does not support __delitem__.")

    def get(self, key, default=None):
        raise TypeError("'RestrictedFrozenAttributeDict' object does not support get.")

    def pop(self, key, default=None):
        raise TypeError("'RestrictedFrozenAttributeDict' object does not support pop.")

    def update(self, key, default=None):
        raise TypeError("'RestrictedFrozenAttributeDict' object does not support update.")

class _ImmutableSlotsBase(tuple):
    __slots__ = ()
    _cls_keys = None
    _cls_base_hash = None

    def __new__(cls, values):
        return super().__new__(cls, (values[k] for k in cls._cls_keys))

    def clone_with_overrides(self, **kwargs):
        values = dict(self, **kwargs)
        return self.__class__(values)

    def __hash__(self):
        return hash((self._cls_base_hash,) + self)

    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return False
        return super().__eq__(other)

    def __bool__(self):
        return True

    def items(self):
        return zip(self._cls_keys, self.values())

    __iter__ = items
    values = tuple.__iter__

    def __repr__(self):
        return '{}({})'.format(type(self).__name__, dict(self))

    def __setattr__(self, attr, value):
        raise TypeError("'ImmutableSlots' object does not support item assignment.")

    def __delattr__(self, attr):
        raise TypeError("'ImmutableSlots' object does not support item deletion.")

    def __len__(self):
        raise TypeError("'ImmutableSlots' object does not support __len__.")

    def __contains__(self, key):
        raise TypeError("'ImmutableSlots' object does not support __contains__.")

    def __setitem__(self, index, value):
        raise TypeError("'ImmutableSlots' object does not support __setitem__.")

    def __delitem__(self, index):
        raise TypeError("'ImmutableSlots' object does not support __delitem__.")

    def get(self, key, default=None):
        raise TypeError("'ImmutableSlots' object does not support get.")

    def pop(self, key, default=None):
        raise TypeError("'ImmutableSlots' object does not support pop.")

    def update(self, key, default=None):
        raise TypeError("'ImmutableSlots' object does not support update.")

def make_immutable_slots_class(keys):
    keys = tuple(sorted(keys))
    if keys in CACHED_IMMUTABLE_SLOTS:
        return CACHED_IMMUTABLE_SLOTS[keys]

    class ImmutableSlots(_ImmutableSlotsBase):
        __slots__ = ()
        _cls_keys = keys
        _cls_base_hash = hash(keys)

    for (index, name) in enumerate(keys):
        try:
            tuple_descriptor = CACHED_TUPLE_DESCRIPTORS[index]
        except KeyError:
            tuple_descriptor = tupledescriptor(index)
            CACHED_TUPLE_DESCRIPTORS[index] = tuple_descriptor
        setattr(ImmutableSlots, name, tuple_descriptor)
    CACHED_IMMUTABLE_SLOTS[keys] = ImmutableSlots
    return ImmutableSlots

class enumdict(collections.MutableMapping):
    __slots__ = ('_key_type', '_values')

    class _enumdictunset(SingletonType):
        pass

    _enumdict__unset = _enumdictunset()
    _key_maps = dict()

    def __init__(self, key_type, *args, **kwargs):
        if key_type not in self._key_maps:
            self._key_maps[key_type] = frozendict({value: index for (index, value) in enumerate(key_type)})
        self._key_type = key_type
        self._values = [self._enumdict__unset]*len(self._key_maps[key_type])
        self.update(*args, **kwargs)

    def __len__(self):
        return sum(1 for v in self._values if v is not self._enumdict__unset)

    def __iter__(self):
        for (k, i) in self._key_maps[self._key_type].items():
            if self._values[i] is not self._enumdict__unset:
                yield k

    def items(self):
        for (k, i) in self._key_maps[self._key_type].items():
            v = self._values[i]
            if v is not self._enumdict__unset:
                yield (k, v)

    def update(self, *args, **kwargs):
        if args:
            other = args[0]
            for (key, value) in other.items():
                self[key] = value
        if kwargs:
            raise NotImplementedError

    def __getitem__(self, key):
        index = self._key_maps[self._key_type][key]
        v = self._values[index]
        if v is self._enumdict__unset:
            raise KeyError
        return v

    def __setitem__(self, key, value):
        index = self._key_maps[self._key_type][key]
        self._values[index] = value

    def __delitem__(self, key):
        index = self._key_maps[self._key_type][key]
        v = self._values[index]
        if v is self._enumdict__unset:
            raise KeyError
        self._values[index] = self._enumdict__unset

    def __contains__(self, key):
        index = self._key_maps[self._key_type][key]
        return self._values[index] is not self._enumdict__unset
