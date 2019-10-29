from interactions.context import InteractionContext, InteractionSourcefrom interactions.liability import Liabilityfrom interactions.priority import Priorityfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableVariant, TunableReferenceimport servicesimport sims4.loglogger = sims4.log.Logger('Sim Spawner')
class SpawnActionFadeIn:

    def __call__(self, sim):
        sim.fade_in()
        return True

class SpawnActionLiability(Liability):
    LIABILITY_TOKEN = 'SpawnActionLiability'

    def __init__(self, sim, spawn_affordance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._spawn_affordance = spawn_affordance
        self._sim = sim

    def release(self):
        if not self._sim.opacity:
            logger.error('{} failed to make {} visible. Fading them in.', self._spawn_affordance, self._sim)
            self._sim.fade_in()

class SpawnActionAffordance(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'spawn_affordance': TunableReference(description='\n            The affordance that is pushed on the Sim as soon as they are spawned\n            on the lot.\n            ', manager=services.affordance_manager(), class_restrictions=('SuperInteraction',))}

    def __call__(self, sim):
        context = InteractionContext(sim, InteractionSource.SCRIPT, Priority.Critical)
        result = sim.push_super_affordance(self.spawn_affordance, None, context)
        if not result:
            logger.error('{} failed to run, with result {}. Fading {} in.', self.spawn_affordance, result, sim)
            sim.fade_in()
        result.interaction.add_liability(SpawnActionLiability.LIABILITY_TOKEN, SpawnActionLiability(sim, self.spawn_affordance))
        return True

class TunableSpawnActionVariant(TunableVariant):

    def __init__(self, **kwargs):
        super().__init__(affordance=SpawnActionAffordance.TunableFactory(), locked_args={'fade_in': SpawnActionFadeIn()}, default='fade_in', **kwargs)
