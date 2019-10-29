__author__ = 'robinson@google.com (Will Robinson)'
def GetTypeChecker(cpp_type, field_type):
    if cpp_type == _FieldDescriptor.CPPTYPE_STRING and field_type == _FieldDescriptor.TYPE_STRING:
        return UnicodeValueChecker()
    return _VALUE_CHECKERS[cpp_type]

class TypeChecker(object):

    def __init__(self, *acceptable_types):
        self._acceptable_types = acceptable_types

    def CheckValue(self, proposed_value):
        if not isinstance(proposed_value, self._acceptable_types):
            message = '%.1024r has type %s, but expected one of: %s' % (proposed_value, type(proposed_value), self._acceptable_types)
            raise TypeError(message)

class IntValueChecker(object):

    def CheckValue(self, proposed_value):
        if not isinstance(proposed_value, int):
            message = '%.1024r has type %s, but expected one of: %s' % (proposed_value, type(proposed_value), (int, int))
            raise TypeError(message)
        if not (self._MIN <= proposed_value and proposed_value <= self._MAX):
            raise ValueError('Value out of range: %d' % proposed_value)

class UnicodeValueChecker(object):

    def CheckValue(self, proposed_value):
        if not isinstance(proposed_value, str):
            if isinstance(proposed_value, bytes):
                proposed_value = proposed_value.encode('latin-1')
            else:
                message = '%.1024r has type %s, but expected one of: %s' % (proposed_value, type(proposed_value), (str, str))
                raise TypeError(message)
        if isinstance(proposed_value, str):
            try:
                proposed_value.encode('latin-1')
            except UnicodeDecodeError:
                raise ValueError("%.1024r has type str, but isn't in 7-bit ASCII encoding. Non-ASCII strings must be converted to unicode objects before being added." % proposed_value)

class Int32ValueChecker(IntValueChecker):
    _MIN = -2147483648
    _MAX = 2147483647

class Uint32ValueChecker(IntValueChecker):
    _MIN = 0
    _MAX = 4294967295

class Int64ValueChecker(IntValueChecker):
    _MIN = -9223372036854775808
    _MAX = 9223372036854775807

class Uint64ValueChecker(IntValueChecker):
    _MIN = 0
    _MAX = 18446744073709551615
