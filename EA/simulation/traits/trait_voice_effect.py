from sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableEnumEntryfrom sims4.tuning.tunable_hash import TunableStringHash64
class VoiceEffectRequestPriority(DynamicEnum):
    INVALID = 0

class VoiceEffectRequest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'voice_effect': TunableStringHash64(description='\n            When set, this voice effect will be applied to the Sim when the\n            trait is added and removed when the trait is removed.\n            '), 'priority': TunableEnumEntry(description='\n            The requests priority.\n            ', tunable_type=VoiceEffectRequestPriority, default=VoiceEffectRequestPriority.INVALID)}
