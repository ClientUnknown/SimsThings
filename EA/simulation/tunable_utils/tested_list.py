from event_testing.tests import TunableTestSetfrom sims4.tuning.tunable import TunableList, TunableTuple, Tunable
class _TestedList(tuple):

    def get_all(self):
        for item_data in self:
            yield item_data.item

    def __call__(self, *, resolver):
        for item_data in self:
            if item_data.test.run_tests(resolver):
                yield item_data.item
                if item_data.stop_processing:
                    break

class TunableTestedList(TunableList):
    DEFAULT_LIST = _TestedList()

    def __init__(self, *args, tunable_type, **kwargs):
        super().__init__(*args, tunable=TunableTuple(description='\n                An entry in this tested list.\n                ', test=TunableTestSet(), item=tunable_type, stop_processing=Tunable(description='\n                    If checked, no other element from this list is considered if\n                    this element passes its associated test.\n                    ', tunable_type=bool, default=False)), **kwargs)

    def load_etree_node(self, *args, **kwargs):
        value = super().load_etree_node(*args, **kwargs)
        return _TestedList(value)
