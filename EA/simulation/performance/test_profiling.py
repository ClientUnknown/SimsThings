
class ProfileMetrics:

    def __init__(self, is_test_set=False):
        self.count = 0
        self.resolve_time = 0
        self.test_time = 0
        self.is_test_set = is_test_set

    def get_total_time(self, include_test_set=True):
        if self.is_test_set and include_test_set:
            return self.resolve_time + self.test_time
        return self.resolve_time

    def get_average_time(self, include_test_set=True):
        if self.count == 0:
            return 0
        total_time = self.get_total_time(include_test_set=include_test_set)
        if total_time == 0:
            return 0
        return total_time/self.count

    def update(self, resolve_time, test_time):
        self.count += 1
        self.resolve_time += resolve_time
        self.test_time += test_time

class TestProfileRecord:

    def __init__(self, is_test_set=False):
        self.metrics = ProfileMetrics(is_test_set=is_test_set)
        self.resolvers = dict()
