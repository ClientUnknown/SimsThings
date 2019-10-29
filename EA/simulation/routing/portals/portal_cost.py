from sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableRange, TunableVariant
class PortalCostTraversalLength(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'multiplier': TunableRange(tunable_type=float, default=1, minimum=0)}

    def __call__(self, start, end):
        if self.multiplier == 1:
            return -1
        cost = (start.position - end.position).magnitude()*self.multiplier
        return cost

class PortalCostFixed(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'cost': TunableRange(tunable_type=float, default=1, minimum=0, maximum=9999)}

    def __call__(self, *_, **__):
        return self.cost

class TunablePortalCostVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        return super().__init__(*args, traversal_length=PortalCostTraversalLength.TunableFactory(), fixed_cost=PortalCostFixed.TunableFactory(), default='traversal_length', **kwargs)
