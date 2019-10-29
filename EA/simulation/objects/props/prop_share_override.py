import itertoolsfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, Tunable, TunableList, TunableVariant, OptionalTunable
class PropShareOverride(HasTunableSingletonFactory, AutoFactoryInit):

    class _PropShareKeyActor(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'actor_name': Tunable(description='\n                The actor that is to be used as a key.\n                ', tunable_type=str, default='x')}

        def get_resolved_key(self, asm):
            return asm.get_actor_by_name(self.actor_name)

    class _PropShareKeyParameter(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'actor_name': OptionalTunable(description="\n                The actor for which this parameter's value is to be used.\n                ", tunable=Tunable(description='\n                    The actor name.\n                    ', tunable_type=str, default='x'), enabled_name='Specified', disabled_name='Global'), 'parameter_name': Tunable(description='\n                The parameter whose value is to be used.\n                ', tunable_type=str, default=None)}

        def get_resolved_key(self, asm):
            for (key, param_value) in itertools.chain.from_iterable(d.items() for d in asm.get_all_parameters()):
                if not isinstance(key, str):
                    if key[1] != self.actor_name:
                        pass
                    else:
                        key = key[0]
                        if key != self.parameter_name:
                            pass
                        else:
                            return param_value
                if key != self.parameter_name:
                    pass
                else:
                    return param_value

    class _PropShareKeyStringLiteral(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'literal': Tunable(description='\n                The literal string that is to be used as a key.\n                ', tunable_type=str, default='')}

        def get_resolved_key(self, asm):
            return self.literal

    FACTORY_TUNABLES = {'key': TunableList(description='\n            A list of elements that form the key for this share. For keys that\n            are identical, props are shared.\n            ', tunable=TunableVariant(actor=_PropShareKeyActor.TunableFactory(), parameter=_PropShareKeyParameter.TunableFactory(), literal=_PropShareKeyStringLiteral.TunableFactory(), default='actor'), minlength=1)}

    def get_prop_share_key(self, asm):
        return tuple(key.get_resolved_key(asm) for key in self.key)
