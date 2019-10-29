import operatorfrom sims4.math import Thresholdfrom sims4.tuning.tunable import TunableSet, OptionalTunable, TunableThreshold, TunableRange, TunableSingletonFactory
class Blacklist:
    __slots__ = ('_items', '_threshold')

    def __init__(self, items, threshold=Threshold(1, operator.ge)):
        self._items = frozenset(items)
        self._threshold = threshold

    def get_items(self):
        return self._items

    def test_collection(self, items):
        count = sum(1 for item in items if item in self._items)
        if self._threshold is None:
            return count != len(items)
        return not self._threshold.compare(count)

    def test_item(self, item):
        return item not in self._items

class TunableBlacklist(TunableSingletonFactory):
    __slots__ = ()

    @staticmethod
    def _factory(blacklist, threshold):
        return Blacklist(blacklist, threshold=threshold)

    FACTORY_TYPE = _factory

    def __init__(self, tunable, description='A tunable blacklist.', **kwargs):
        super().__init__(blacklist=TunableSet(description='\n                Blacklisted items.\n                ', tunable=tunable), threshold=OptionalTunable(description='\n                Tunable option for how many items must be in the blacklist\n                for the blacklist to fail when testing a collection of items.\n                By default, only one object needs to be in the list.\n                ', tunable=TunableThreshold(description='\n                    When testing a collection of items, the number of items in\n                    that collection that are in the blacklist must pass this\n                    threshold test for the blacklist to disallow them all.\n                    ', value=TunableRange(tunable_type=int, default=1, minimum=0), default=Threshold(1, operator.ge)), enabled_by_default=True, disabled_name='all_must_match', enabled_name='threshold'), description=description, **kwargs)
