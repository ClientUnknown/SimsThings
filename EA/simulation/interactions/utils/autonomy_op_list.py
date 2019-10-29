
class AutonomyAdList:

    def __init__(self, stat_type):
        self._stat_type = stat_type
        self._op_list = []

    @property
    def stat(self):
        return self._stat_type

    def add_op(self, op):
        if op.tested:
            self._op_list.append(op)
        else:
            self._op_list.insert(0, op)

    def remove_op(self, op):
        if op in self._op_list:
            self._op_list.remove(op)
            return True
        return False

    def get_fulfillment_rate(self, interaction):
        return sum(op.get_fulfillment_rate(interaction) for op in self._get_valid_ops_gen(interaction))

    def get_value(self, interaction):
        return sum(op.get_value() for op in self._get_valid_ops_gen(interaction))

    def is_valid(self, interaction):
        for _ in self._get_valid_ops_gen(interaction):
            return True
        return False

    def _get_valid_ops_gen(self, interaction):
        resolver = interaction.get_resolver()
        for op in self._op_list:
            if op.test_resolver(resolver, ignore_chance=True):
                yield op
