from sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableVariant, TunableReferenceimport servicesimport sims4.resources
class _PostureValidator(HasTunableSingletonFactory, AutoFactoryInit):

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self):
        return hash(self.__dict__)

class PostureValidatorTest(_PostureValidator):
    FACTORY_TUNABLES = {'test_set': TunableReference(description="\n            This test set is provided with a DoubleSimResolver. The Actor\n            participant is the transitioning Sim. The Object/TargetSim\n            participant is the posture container we're testing against.\n            \n            Should the test fail, the posture transition is deemed invalid and\n            is discarded.\n            ", manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('TestSetInstance',))}

    def __call__(self, resolver):
        return self.test_set(resolver)

class TunablePostureValidatorVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, test=PostureValidatorTest.TunableFactory(), default='test', **kwargs)
