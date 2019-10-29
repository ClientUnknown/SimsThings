from element_utils import build_critical_section_with_finallyfrom routing.walkstyle.walkstyle_enums import WalkStylePriorityfrom routing.walkstyle.walkstyle_tuning import TunableWalkstylefrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableEnumEntryfrom uid import unique_id
@unique_id('request_id')
class WalkStyleRequest(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'walkstyle': TunableWalkstyle(description='\n            The locomotion resource (i.e. walkstyle) to request. Depending\n            on the tuned priority and other requests active on the Sim, this\n            may or may not apply immediately.\n            '), 'priority': TunableEnumEntry(description='\n            The priority of the walkstyle. Higher priority walkstyles will take\n            precedence over lower priority. Equal priority will favor recent\n            requests.\n            ', tunable_type=WalkStylePriority, default=WalkStylePriority.INVALID, invalid_enums=(WalkStylePriority.INVALID,))}

    def __init__(self, obj, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._obj = obj.ref()

    def start(self, *_, **__):
        obj = self._obj()
        if obj is None:
            return
        obj.request_walkstyle(self, self.request_id)

    def stop(self, *_, **__):
        obj = self._obj()
        if obj is None:
            return
        obj.remove_walkstyle(self.request_id)

    def __call__(self, sequence=()):
        return build_critical_section_with_finally(self.start, sequence, self.stop)
