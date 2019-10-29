from sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, Tunableimport sims4.loglogger = sims4.log.Logger('VoicePitch', default_owner='rmccord')
class VoicePitchModifier(HasTunableFactory, AutoFactoryInit):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, pitch_modifier=None, pitch_multiplier=None):
        if pitch_multiplier == 1.0 and pitch_modifier == 0.0:
            logger.error('Pitch Multiplier and Adder for {} in {} is set to do nothing.', instance_class, source, owner='rmccord')

    FACTORY_TUNABLES = {'pitch_modifier': Tunable(description="\n            An additive modifier for the Sim's pitch to override it.\n            ", default=0.0, tunable_type=float), 'pitch_multiplier': Tunable(description="\n            A multiplier for the Sim's pitch to override it.\n            ", default=1.0, tunable_type=float), 'verify_tunable_callback': _verify_tunable_callback}

    def __init__(self, target, **kwargs):
        super().__init__(**kwargs)
        self.target = target
        self.expected_override = None

    def start(self):
        if self.target.is_sim:
            if self.target.voice_pitch_override is not None:
                logger.warn('Applying multiple voice pitch overrides for {} which will override previous overrides.', self.target, owner='rmccord')
            self.expected_override = self.target.sim_info.voice_pitch*self.pitch_multiplier + self.pitch_modifier
            self.target.voice_pitch_override = self.expected_override

    def stop(self, *_, **__):
        if self.expected_override is None or self.target.voice_pitch_override == self.expected_override:
            self.target.voice_pitch_override = None
