from contextlib import contextmanagerimport collectionsimport sims4.log__all__ = ['Metaclass', 'EnumBase', 'Int', 'IntFlags', 'LongFlags']__unittest__ = ['test.enum_test']logger = sims4.log.Logger('Enum')
class Metaclass(type):

    @classmethod
    def __prepare__(meta, name, bases, **kwds):
        return collections.OrderedDict()

    def __call__(cls, value):
        if isinstance(value, str):
            try:
                return cls.name_to_value[value]
            except KeyError:
                value = cls.underlying_type(value)
        try:
            return cls.name_to_value[cls.value_to_name[value]]
        except KeyError:
            return cls._get_unknown_value(value)

    def __new__(meta, classname, bases, class_dict, **kwargs):
        underlying_type = getattr(bases[0], 'underlying_type', bases[0])
        class_enum_values = [(k, v) for (k, v) in class_dict.items() if v is ... or type(v) == underlying_type or isinstance(type(v), Metaclass)]
        class_dict.update(kwargs)
        class_dict['__slots__'] = ()
        class_dict['_mutable'] = True
        class_dict['name_to_value'] = collections.OrderedDict()
        class_dict['value_to_name'] = collections.OrderedDict()
        class_dict['cache_key'] = classname
        class_dict['underlying_type'] = underlying_type

        @contextmanager
        def __reload_context__(oldobj, newobj):
            with oldobj.make_mutable(), newobj.make_mutable():
                yield None

        class_dict['__reload_context__'] = __reload_context__
        enum_type = type.__new__(meta, classname, bases, class_dict)
        enum_type._enum_export_path = enum_type.__module__.replace('.', '-') + '.' + enum_type.__qualname__
        enum_values = collections.OrderedDict()
        for cls in reversed(enum_type.mro()):
            if isinstance(cls, Metaclass):
                enum_values.update(cls.name_to_value)
        enum_values.update(class_enum_values)
        prev_value = None
        for (name, value) in enum_values.items():
            if value is ...:
                value = enum_type._next_auto_value(prev_value)
            prev_value = value
            enum_type._add_new_enum_value(name, value)
        enum_type._mutable = False
        return enum_type

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

    def _add_new_enum_value(cls, name, value):
        enum_value = type.__call__(cls, value)
        setattr(cls, name, enum_value)
        cls.name_to_value[name] = enum_value
        if enum_value not in cls.value_to_name:
            cls.value_to_name[enum_value] = name

    @contextmanager
    def make_mutable(cls):
        old_value = cls._mutable
        type.__setattr__(cls, '_mutable', True)
        try:
            yield None
        finally:
            cls._mutable = old_value

    def __contains__(cls, key):
        return key in cls.value_to_name or key in cls.name_to_value

    def items(cls):
        return cls.name_to_value.items()

    @property
    def names(cls):
        return tuple(cls.name_to_value)

    @property
    def values(cls):
        return tuple(cls.value_to_name)

    def __iter__(cls):
        return iter(cls.name_to_value.values())

    def __len__(cls):
        return len(cls.name_to_value)

    def __reversed__(cls):
        return reversed(tuple(cls.name_to_value.values()))

    def __setattr__(cls, name, value):
        if cls._mutable:
            return super().__setattr__(name, value)
        raise AttributeError("Can't modify enum {}".format(cls.__qualname__))

    def __delattr__(cls, name):
        if cls._mutable:
            return super().__delattr__(name)
        raise AttributeError("Can't modify enum {}".format(cls.__qualname__))

    __getitem__ = type.__getattribute__
    __setitem__ = __setattr__
    __delitem__ = __delattr__

    def __repr__(cls):
        return '<enum {}: {}>'.format(cls.underlying_type, cls.__name__)

    def get_export_path(cls):
        return cls._enum_export_path

class EnumBase(int, metaclass=Metaclass, locked=False, export=True, display_sorted=False, partitioned=False, offset=0):

    @classmethod
    def _get_unknown_value(cls, value):
        raise KeyError('{} does not have value {}'.format(cls, value))

    @property
    def name(self):
        try:
            return self.value_to_name[self]
        except KeyError:
            return 'enum value out of range: {}'.format(self.value)

    @property
    def value(self):
        return self.underlying_type(self)

    @staticmethod
    def _next_auto_value(previous_value):
        if previous_value is None:
            return 0
        return previous_value + 1

    def __str__(self):
        return '%s.%s' % (type(self).__name__, self.name)

    def __repr__(self):
        return '<%s.%s = %s>' % (type(self).__name__, self.name, super().__repr__())

    def __reduce__(self):
        return (type(self), (self.value,))

class Int(EnumBase):

    def __add__(self, other):
        return type(self)(super().__add__(other))

    def __sub__(self, other):
        return type(self)(super().__sub__(other))

    def __and__(self, other):
        int_result = super().__and__(other)
        if int_result:
            return type(self)(int_result)
        else:
            return type.__call__(type(self), 0)

    def __or__(self, other):
        int_result = super().__or__(other)
        if int_result == self:
            return self
        return type(self)(int_result)

    def __xor__(self, other):
        return type(self)(super().__xor__(other))

    def __invert__(self):
        int_value = super().__invert__() & (1 << max(self.value_to_name).bit_length()) - 1
        return type(self)(int_value)

class IntFlags(Int):

    @classmethod
    def _get_unknown_value(cls, value):
        return type.__call__(cls, value)

    @staticmethod
    def _next_auto_value(value):
        if value is None:
            return 1
        return 1 << value.bit_length()

    def _get_bits(self):
        if self < 0:
            raise ValueError('Cannot get all the bits in a negative number: {}'.format(self))
        int_self = int(self)
        remainder = 0
        bits = []
        value_to_name = self.value_to_name
        while int_self:
            lowest_bit = int_self & -int_self
            if lowest_bit in value_to_name:
                bits.append(lowest_bit)
            else:
                remainder |= lowest_bit
            int_self ^= lowest_bit
        return (bits, remainder)

    @property
    def name(self):
        try:
            return self.value_to_name[self]
        except KeyError:
            pass
        if self <= 0:
            return str(self.underlying_type(self))

        def names_gen():
            (bits, remainder) = self._get_bits()
            value_to_name = self.value_to_name
            for bit in bits:
                yield value_to_name[bit]
            if remainder:
                yield str(remainder)

        return '|'.join(names_gen())

    def __iter__(self):
        if self < 0:
            raise ValueError('Cannot iterate over bits in a negative enum value: {}'.format(self))
        value_to_name = self.value_to_name
        name_to_value = self.name_to_value
        (bits, remainder) = self._get_bits()
        for bit in bits:
            yield name_to_value[value_to_name[bit]]
        if remainder:
            yield type.__call__(self.__class__, remainder)

    def __contains__(self, value):
        if value & self:
            return True
        return False

    @classmethod
    def list_values_from_flags(cls, value):
        if value < 0:
            raise ValueError('Flag field enums do not support negative values.')
        if value:
            return list(cls(value))
        return []

class LongFlags(IntFlags):
    pass
