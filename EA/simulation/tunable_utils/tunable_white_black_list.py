from sims4.tuning.tunable import OptionalTunable, TunableSingletonFactoryfrom tunable_utils.tunable_blacklist import TunableBlacklistfrom tunable_utils.tunable_whitelist import TunableWhitelist
class WhiteBlackList:
    __slots__ = ('_whitelist', '_blacklist')

    def __init__(self, whitelist=None, blacklist=None):
        self._whitelist = whitelist
        self._blacklist = blacklist

    def get_items(self):
        items = set()
        if self._whitelist:
            for item in self._whitelist.get_items():
                items.add(item)
        if self._blacklist:
            for item in self._blacklist.get_items():
                items.add(item)
        return items

    def test_collection(self, items):
        if self._whitelist is not None and not self._whitelist.test_collection(items):
            return False
        elif self._blacklist is not None and not self._blacklist.test_collection(items):
            return False
        return True

    def test_item(self, item):
        if self._whitelist is not None and not self._whitelist.test_item(item):
            return False
        elif self._blacklist is not None and not self._blacklist.test_item(item):
            return False
        return True

class TunableWhiteBlackList(TunableSingletonFactory):
    __slots__ = ()

    @staticmethod
    def _factory(whitelist, blacklist):
        return WhiteBlackList(whitelist, blacklist)

    FACTORY_TYPE = _factory

    def __init__(self, tunable, description='A tunable whitelist and blacklist.', **kwargs):
        super().__init__(whitelist=OptionalTunable(description='\n                When an item is tested against this white/black list, it is\n                only allowed if it is in the whitelist. If no whitelist is\n                specified, all items are allowed.\n                ', tunable=TunableWhitelist(tunable=tunable), disabled_name='everything', enabled_name='specify'), blacklist=OptionalTunable(description='\n                When an item is tested against this white/black list, it is\n                only allowed if it is not in the blacklist. If no blacklist is\n                specified, no items are disallowed.\n                ', tunable=TunableBlacklist(tunable=tunable), disabled_name='nothing', enabled_name='specify'), description=description, **kwargs)
