from sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit
class Forwarding(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'object_filter': TunableObjectFilterVariant(description='\n            The object we want to forward this interaction *on* must satisfy\n            this filter.\n            ', default=TunableObjectFilterVariant.FILTER_ALL)}

    def is_allowed_to_forward(self, interaction, obj):
        if not self.object_filter.is_object_valid(obj):
            return False
        return True
