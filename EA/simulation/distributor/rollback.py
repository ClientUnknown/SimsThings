from distributor import logger
class ProtocolBufferRollbackExpected(Exception):
    pass

class ProtocolBufferRollback:

    def __init__(self, repeated_field):
        self._repeated_field = repeated_field

    def __enter__(self):
        return self._repeated_field.add()

    def __exit__(self, exc_type, value, tb):
        del self._repeated_field[len(self._repeated_field) - 1]
        if exc_type is not None and exc_type is not ProtocolBufferRollbackExpected:
            logger.exception('Exception occurred while attempting to populate a repeated field:')
        return True
