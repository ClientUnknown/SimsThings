from interactions import ParticipantTypefrom interactions.liability import Liabilityfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.tunable import TunableSingletonFactory, TunablePackSafeReference, TunableReference, OptionalTunable, TunableFactory, TunableEnumFlags, HasTunableFactoryimport event_testingimport servicesimport sims4.loglogger = sims4.log.Logger('Buffs')
class BuffReference:
    __slots__ = ('_buff_type', '_buff_reason')

    def __init__(self, buff_type=None, buff_reason=None):
        self._buff_type = buff_type
        self._buff_reason = buff_reason

    @property
    def buff_type(self):
        return self._buff_type

    @property
    def buff_reason(self):
        return self._buff_reason

class TunableBuffReference(TunableSingletonFactory):
    __slots__ = ()
    FACTORY_TYPE = BuffReference

    def __init__(self, reload_dependent=False, pack_safe=False, allow_none=False, **kwargs):
        super().__init__(buff_type=TunableReference(manager=services.buff_manager(), description='Buff that will get added to sim.', allow_none=allow_none, reload_dependent=reload_dependent, pack_safe=pack_safe), buff_reason=OptionalTunable(description='\n                            If set, specify a reason why the buff was added.\n                            ', tunable=TunableLocalizedString(description='\n                                The reason the buff was added. This will be displayed in the\n                                buff tooltip.\n                                ')), **kwargs)

class TunablePackSafeBuffReference(TunableSingletonFactory):
    __slots__ = ()
    FACTORY_TYPE = BuffReference

    def __init__(self, reload_dependent=False, allow_none=False, **kwargs):
        super().__init__(buff_type=TunablePackSafeReference(manager=services.buff_manager(), description='Buff that will get added to sim.', allow_none=allow_none, reload_dependent=reload_dependent), buff_reason=OptionalTunable(description='\n                            If set, specify a reason why the buff was added.\n                            ', tunable=TunableLocalizedString(description='\n                                The reason the buff was added. This will be displayed in the\n                                buff tooltip.\n                                ')), **kwargs)

class TunableBuffElement(TunableFactory):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, tests, buff_type, subject):
        if buff_type.buff_type is None:
            return
        if buff_type.buff_type._temporary_commodity_info is not None:
            logger.error('TunableBuffElement: {} has a buff element with a buff {} with a temporary commodity tuned.', instance_class, buff_type.buff_type)

    @staticmethod
    def factory(interaction, subject, tests, buff_type, sequence=()):
        if buff_type.buff_type is not None:
            for sim in interaction.get_participants(subject):
                if tests.run_tests(interaction.get_resolver()):
                    sequence = buff_type.buff_type.build_critical_section(sim, buff_type.buff_reason, sequence)
        return sequence

    FACTORY_TYPE = factory

    def __init__(self, description='A buff that will get added to the subject when running the interaction if the tests succeeds.', **kwargs):
        super().__init__(subject=TunableEnumFlags(ParticipantType, ParticipantType.Actor, description='Who will receive the buff.'), tests=event_testing.tests.TunableTestSet(), buff_type=TunablePackSafeBuffReference(description='The buff type to be added to the Sim.'), verify_tunable_callback=TunableBuffElement._verify_tunable_callback, description=description, **kwargs)

class RemoveBuffLiability(Liability, HasTunableFactory):
    LIABILITY_TOKEN = 'RemoveBuffLiability'
    FACTORY_TUNABLES = {'buff_to_remove': TunablePackSafeReference(description='\n            The buff to remove on the interaction finishing.\n            ', manager=services.buff_manager())}

    def __init__(self, interaction, buff_to_remove, **kwargs):
        super().__init__(**kwargs)
        self._sim_info = interaction.sim.sim_info
        self._buffs_to_remove = set()
        if buff_to_remove is not None:
            self._buffs_to_remove.add(buff_to_remove)

    def merge(self, interaction, key, new_liability):
        new_liability._buffs_to_remove.update(self._buffs_to_remove)
        return new_liability

    def release(self):
        for buff_type in self._buffs_to_remove:
            self._sim_info.remove_buff_by_type(buff_type)
