from distributor.ops import SetCallToAction, ElementDistributionOpMixinfrom sims4.tuning.tunable import HasTunableFactory, TunableColor, TunableRange, AutoFactoryInitimport distributor.ops
class Glow(ElementDistributionOpMixin, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'color': TunableColor(description='\n            The color of the call to action.\n            '), 'pulse_frequency': TunableRange(description='\n            The frequency at which the highlight pulses.\n            ', tunable_type=float, default=1.0, minimum=0.1), 'thickness': TunableRange(description='\n            The thickness of the highlight.\n            ', tunable_type=float, default=0.002, minimum=0.001, maximum=0.005)}

    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target = target

    def start(self, *args, **kwargs):
        if not self.is_attached:
            self.attach(self._target)

    def stop(self, *args, **kwargs):
        if self.is_attached:
            self.detach()

    def detach(self, *objects):
        super().detach(*objects)
        glowOp = SetCallToAction(0, 0, 0)
        distributor.ops.record(self._target, glowOp)

    def write(self, msg):
        glowOp = SetCallToAction(self.color, self.pulse_frequency, self.thickness)
        glowOp.write(msg)
