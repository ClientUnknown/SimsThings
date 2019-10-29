from event_testing.results import TestResultfrom sims4.math import MAX_INT32
class RouteEventBase:

    def __init__(self, time=None, *args, **kwargs):
        self.time = time
        self.event_data = None
        self._run_duration = MAX_INT32

    @property
    def duration(self):
        return self._run_duration

    def copy_from(self, other):
        self.time = other.time
        self.event_data = other.event_data
        self._run_duration = other.duration

class RouteEventDataBase:

    @classmethod
    def test(cls, actor, event_data_tuning):
        return TestResult.TRUE

    def prepare(self, actor):
        raise NotImplementedError

    def is_valid_for_scheduling(self, actor, path):
        return True

    def should_remove_on_execute(self):
        return True

    def execute(self, actor, **kwargs):
        raise NotImplementedError

    def process(self, actor):
        raise NotImplementedError
