
class SingletonMetaclass(type):

    def __call__(cls, *args):
        try:
            return cls._instance
        except AttributeError:
            cls._instance = type.__call__(cls, *args)
            return cls._instance

class SingletonType(metaclass=SingletonMetaclass):

    def __eq__(self, other):
        return other is self

    def __hash__(self):
        return hash(type(self))

    def __repr__(self):
        return type(self).__name__.replace('Type', '')

    def __reduce__(self):
        return (self.__class__, ())

    @staticmethod
    def __reload_update__(oldobj, newobj, update_fn):
        return oldobj

    @staticmethod
    def __reload_update_class__(oldobj, newobj, update_fn):
        return oldobj

class SingletonEvaluatingFalseType(SingletonType):

    def __bool__(self):
        return False

class DefaultType(SingletonEvaluatingFalseType):
    pass

class UnsetType(SingletonEvaluatingFalseType):
    pass
DEFAULT = DefaultType()UNSET = UnsetType()EMPTY_SET = frozenset()