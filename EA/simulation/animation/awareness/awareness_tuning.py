from animation.awareness.awareness_enums import AwarenessChannel, AwarenessChannelEvaluationTypefrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableRange, TunableMapping, HasTunableFactory, Tunable, TunableEnumEntry, TunableVariant, TunableTuple, OptionalTunablefrom singletons import DEFAULT, UNSET
class AwarenessChannelData(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'evaluation_type': TunableEnumEntry(description='\n            Define how Sims evaluate scores for this channel.\n            ', tunable_type=AwarenessChannelEvaluationType, default=AwarenessChannelEvaluationType.PEAK), 'limit': TunableRange(description='\n            Define a limit beyond which scores are no longer added. For example,\n            imagine a SMELL channel evaluated using SUM (to make Sims aware of\n            new smells, for instance). It would be unrealistic for the nth plate\n            of food (where n is large) to produce a reaction. Use limit to\n            define this characteristic.\n            ', tunable_type=float, default=256, minimum=0)}

class AwarenessModifiers(HasTunableSingletonFactory, AutoFactoryInit):

    class _AwarenessChannelOptions(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'gate': TunableRange(description="\n                Any individual value lower than this gate is treated as 0. This\n                is essentially a noise filter: it prevents Sims from\n                overreacting to a large stimulus made up of very small stimuli.\n                \n                For example, imagine air conditioners producing very little\n                noise. If there were many air conditioners, a Sim might react.\n                Instead, if the noise level is below this value, the scores are\n                effectively discarded and don't contribute to the overall score.\n                ", tunable_type=float, default=0, minimum=0), 'gain': TunableRange(description="\n                A multiplier to apply to the awareness score. This allows Sims\n                to be more reactive than other Sims for the same stimulus.\n                \n                For example, you can tune a cat with extra-good hearing to\n                multiply the Audio Volume channel, so they'll react to noises\n                that are softer.\n                ", tunable_type=float, default=1, minimum=0), 'threshold': TunableRange(description='\n                A value below which Sims do not react to stimuli for this\n                channel. This allows different Sims to have different\n                tolerances.\n                \n                This can be used to dampen a Sim\'s awareness. For example, a\n                "Chill" cat might have this value set higher for the Proximity\n                channel, so that Sims close to it don\'t produce as much of a\n                reaction as other cats.\n                ', tunable_type=float, default=0.5, minimum=0)}

    FACTORY_TUNABLES = {'awareness_options': TunableMapping(description="\n            Specify the Sim's reaction to specific awareness channels.\n            ", key_type=AwarenessChannel, value_type=TunableVariant(description='\n                Define how this Sim reacts to the specified stimulus.\n                ', modified_reaction=_AwarenessChannelOptions.TunableFactory(), locked_args={'default_reaction': DEFAULT, 'no_reaction': UNSET}, default='modified_reaction')), 'proximity_modifiers': TunableTuple(description='\n            Override how this Sim reacts to proximity, i.e. other Sims being\n            nearby.\n            ', inner_radius=OptionalTunable(description="\n                If enabled, the Sim's inner proximity radius is modified to be\n                this value. Any distance within this radius scores a full value\n                of 1.\n                \n                NOTE: If more than one modifier is present, the greatest value\n                is used.\n                ", tunable=TunableRange(tunable_type=float, default=1.1, minimum=0)), outer_radius=OptionalTunable(description="\n                If enabled, the Sim's outer proximity radius is modified to be\n                this value. Any distance outside of this radius scores nothing,\n                i.e. a value of 0.\n                \n                NOTE: If more than one modifier is present, the lowest value is\n                used.\n                ", tunable=TunableRange(tunable_type=float, default=1.25, minimum=0)))}

    def apply_modifier(self, sim):
        if sim is None:
            return
        for (awareness_channel, awareness_options) in self.awareness_options.items():
            sim.add_awareness_modifier(awareness_channel, awareness_options)
        if self.proximity_modifiers.inner_radius is not None or self.proximity_modifiers.outer_radius is not None:
            sim.add_proximity_modifier(self.proximity_modifiers)

    def remove_modifier(self, sim):
        if sim is None:
            return
        for (awareness_channel, awareness_options) in self.awareness_options.items():
            sim.remove_awareness_modifier(awareness_channel, awareness_options)
        if self.proximity_modifiers.inner_radius is not None or self.proximity_modifiers.outer_radius is not None:
            sim.remove_proximity_modifier(self.proximity_modifiers)

class AwarenessSourceRequest(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'awareness_sources': TunableMapping(description="\n            A mapping of awareness channels and scores. The score is cumulative,\n            with all requests for the same channel contributing to an object's\n            awareness source score.\n            ", key_type=TunableEnumEntry(description='\n                The channel to add an awareness score to.\n                ', tunable_type=AwarenessChannel, default=AwarenessChannel.PROXIMITY, invalid_enums=tuple(AwarenessChannel)), value_type=Tunable(description='\n                The awareness score for this object, for the specified channel.\n                ', tunable_type=float, default=1))}

    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target = target

    def start(self, *_, **__):
        self._target.add_awareness_scores(self.awareness_sources)

    def stop(self, *_, **__):
        self._target.remove_awareness_scores(self.awareness_sources)

class AwarenessTuning:
    AWARENESS_CHANNEL_DATA = TunableMapping(description='\n        Define data specific to the tuned awareness channels. If no data is\n        specified, default values are used.\n        ', key_type=AwarenessChannel, value_type=AwarenessChannelData.TunableFactory())
