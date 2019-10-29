import operatorfrom sims4.math import Thresholdfrom sims4.tuning.tunable import TunableSet, OptionalTunable, TunableThreshold, TunableRange, TunableSingletonFactory
class Whitelist:
    __slots__ = ('_items', '_threshold')

    def __init__(self, items, threshold=Threshold(1, operator.ge)):
        self._items = frozenset(items)
        self._threshold = threshold

    def get_items(self):
        return self._items

    def test_collection(self, items):
        count = sum(1 for item in items if item in self._items)
        if self._threshold is None:
            return count == len(items)
        return self._threshold.compare(count)

    def test_item(self, item):
        return item in self._items

class TunableWhitelist(TunableSingletonFactory):
    __slots__ = ()

    @staticmethod
    def _factory(whitelist, threshold):
        return Whitelist(whitelist, threshold=threshold)

    FACTORY_TYPE = _factory

    def __init__(self, tunable, description='A tunable whitelist.', **kwargs):
        super().__init__(whitelist=TunableSet(description='\n                Whitelisted items.\n                ', tunable=tunable), threshold=OptionalTunable(description='\n                Tunable option for how many items must be in the whitelist\n                for the whitelist to pass when testing a collection of items.\n                By default, only one object needs to be in the list.\n                ', tunable=TunableThreshold(description='\n                    When testing a collection of items, the number of items in\n                    that collection that are in the whitelist must pass this\n                    threshold test for the whitelist to allow them all.\n                    ', value=TunableRange(tunable_type=int, default=1, minimum=0), default=Threshold(1, operator.ge)), enabled_by_default=True, disabled_name='all_must_match', enabled_name='threshold'), description=description, **kwargs)
