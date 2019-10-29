from objects.components.types import CARRYABLE_COMPONENTfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, Tunable, TunableVariant
class _HolsteringBehaviorAllowed(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'always_holster_while_routing': Tunable(description='\n            If checked, this Sim will always holster all objects when routing.\n            If unchecked, the Sim will only holster while routing if the object\n            is specifically tuned to exhibit this behavior.\n            ', tunable_type=bool, default=False), 'always_holster_for_non_mobile_transitions': Tunable(description='\n            If checked, this Sim will always holster all objects when executing\n            a transition involving a non-mobile posture (whether it be the\n            source or the destination.)\n            ', tunable_type=bool, default=False)}

    def is_holstering_allowed(self):
        return True

    def is_required_to_holster_while_routing(self, carry_object):
        if self.always_holster_while_routing:
            return True
        carry_component = carry_object.get_component(CARRYABLE_COMPONENT)
        return carry_component.holster_while_routing

    def is_required_to_holster_for_transition(self, source, destination):
        if source.holster_for_entries_and_exits:
            return True
        if destination.holster_for_entries_and_exits:
            return True
        elif not (self.always_holster_for_non_mobile_transitions and source.mobile and destination.mobile):
            return True
        return False

class _HolsteringBehaviorDisallowed(HasTunableSingletonFactory, AutoFactoryInit):

    def is_holstering_allowed(self):
        return False

    def is_required_to_holster_while_routing(self, carry_object):
        return False

    def is_required_to_holster_for_transition(self, source, destination):
        return False

class TunableHolsteringBehaviorVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, allow=_HolsteringBehaviorAllowed.TunableFactory(), disallow=_HolsteringBehaviorDisallowed.TunableFactory(), default='allow', **kwargs)

class _UnholsterWhileRoutingBehaviorNever(HasTunableSingletonFactory, AutoFactoryInit):

    def should_unholster(self, *args, **kwargs):
        return False

class _UnholsterWhileRoutingBehaviorAlways(HasTunableSingletonFactory, AutoFactoryInit):

    def should_unholster(self, *args, **kwargs):
        return True

class _UnholsterWhileRoutingBehaviorLongRoutesOnly(HasTunableSingletonFactory, AutoFactoryInit):

    def should_unholster(self, *args, sim=None, path=None, **kwargs):
        if path is not None and sim is not None:
            walkstyle_behavior = sim.get_walkstyle_behavior()
            if path.length() > walkstyle_behavior.short_walkstyle_distance:
                return True
        return False

class TunableUnholsterWhileRoutingBehaviorVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, never=_UnholsterWhileRoutingBehaviorNever.TunableFactory(), always=_UnholsterWhileRoutingBehaviorAlways.TunableFactory(), long_routes_only=_UnholsterWhileRoutingBehaviorLongRoutesOnly.TunableFactory(), default='never', **kwargs)
