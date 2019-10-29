from sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInitimport enum
class SimInfoFixupActionTiming(enum.Int):
    ON_FIRST_SIMINFO_LOAD = 0
    ON_ADDED_TO_ACTIVE_HOUSEHOLD = 1

class _SimInfoFixupAction(HasTunableSingletonFactory, AutoFactoryInit):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __call__(self, sim_info):
        raise NotImplementedError
