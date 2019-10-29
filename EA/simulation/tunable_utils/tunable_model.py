from sims4.tuning.tunable import TunableSingletonFactory, AutoFactoryInit, HasTunableSingletonFactory, TunableResourceKey, TunableReference, Tunable, TunableVariant, OptionalTunableimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Objects', default_owner='epanero')
class TunableModel(TunableSingletonFactory):

    class _ModelFromResource(AutoFactoryInit, HasTunableSingletonFactory):
        FACTORY_TUNABLES = {'model': TunableResourceKey(description="\n                The model's resource.\n                ", resource_types=(sims4.resources.Types.MODEL,))}

        def get_model(self):
            return self.model

    class _ModelFromDefinition(AutoFactoryInit, HasTunableSingletonFactory):

        @staticmethod
        def _verify_tunable_callback(instance_class, tunable_name, source, value):
            if value.apply_definition:
                original_definition = services.definition_manager().find_first_definition_by_cls(instance_class)
                if original_definition is not None:
                    (result, error) = original_definition.is_similar(value.definition, ignore_rig_footprint=True)
                    if not result:
                        logger.error("<{}>'s client state model swap requires a definition change {} which is incompatible with its own definition {}.\n {}", instance_class.__name__, value.definition, original_definition, error, owner='cjiang')

        FACTORY_TUNABLES = {'definition': TunableReference(description="\n                The model's definition. \n                ", manager=services.definition_manager()), 'apply_definition': Tunable(description='\n                If set, the definition is also swapped. Otherwise, only the\n                model is swapped.\n                ', tunable_type=bool, default=False), 'verify_tunable_callback': _verify_tunable_callback}

        def get_model(self):
            if self.apply_definition:
                return self.definition
            return self.definition.get_model(index=0)

    @staticmethod
    def _factory(model):
        return model.get_model()

    FACTORY_TYPE = _factory

    def __init__(self, **kwargs):
        super().__init__(model=TunableVariant(description='\n                Define the model to use.\n                ', from_resource=TunableModel._ModelFromResource.TunableFactory(), from_definition=TunableModel._ModelFromDefinition.TunableFactory(), default='from_resource'), **kwargs)

class TunableModelOrDefault(OptionalTunable):

    def __init__(self, **kwargs):
        super().__init__(disabled_name='set_to_default_model', enabled_name='set_to_custom_model', tunable=TunableModel(description='\n                Specify the model to use.\n                '), **kwargs)
