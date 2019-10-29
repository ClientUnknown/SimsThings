from sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumEntryimport enum
class TanLevel(enum.Int):
    NO_TAN = 0
    DEEP = 1
    SUNBURNED = 2

class ChangeTanLevel(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'tan_level': TunableEnumEntry(description='\n            The tan level to set for the Sim.\n            ', tunable_type=TanLevel, default=TanLevel.NO_TAN)}

    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target

    def start(self):
        suntan_tracker = self.target.sim_info.suntan_tracker
        suntan_tracker.set_tan_level(tan_level=self.tan_level)

    def stop(self, *_, **__):
        pass
