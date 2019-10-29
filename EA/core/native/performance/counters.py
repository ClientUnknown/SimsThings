try:
    from _perf_api import set_counter
except:

    def set_counter(name:str, value:int):
        pass
try:
    from _perf_api import add_counter
except:

    def add_counter(name:str, value:int):
        pass
try:
    from _perf_api import subtract_counter
except:

    def subtract_counter(name:str, value:int):
        pass

class CounterIDs:
    AUTONOMY_QUEUE_LENGTH = 'autonomyQueueLength64'
    AUTONOMY_QUEUE_TIME = 'autonomyQueueTime64'
    EVENT_TIME_DEVIATION = 'eventTimeDeviation64'
    NUM_PENDING_EVENTS = 'numPendingEvents64'
    NUM_PRIMITIVES = 'numPrimitives64'
