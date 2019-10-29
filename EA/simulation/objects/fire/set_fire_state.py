import randomfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunablePercentimport services
class SetFireState(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'chance': TunablePercent(description='\n            Chance that the fire will trigger\n            ', default=100)}

    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target

    def start(self, *_, **__):
        if random.random() < self.chance:
            fire_service = services.get_fire_service()
            fire_service.spawn_fire_at_object(self.target)

    def stop(self, *_, **__):
        pass
