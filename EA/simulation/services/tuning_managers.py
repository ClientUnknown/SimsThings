from sims4.resources import INSTANCE_TUNING_DEFINITIONS, Typesimport paths
class InstanceTuningManagers(dict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._type_to_def_mapping = {d.TYPE_ENUM_VALUE: d for d in INSTANCE_TUNING_DEFINITIONS}

    def __missing__(self, resource_type_enum):
        if resource_type_enum not in self._type_to_def_mapping:
            raise KeyError('Cannot create manager for {}, key not found in instance tuning manager type map'.format(resource_type_enum))
        definition = self._type_to_def_mapping[resource_type_enum]
        manager = self._create_instance_manager(definition, resource_type_enum)
        self[resource_type_enum] = manager
        return manager

    def clear(self):
        self._type_to_def_mapping.clear()
        super().clear()

    def _create_instance_manager(self, definition, resource_type_enum):
        from sims4.tuning.instance_manager import InstanceManager
        mgr_type = resource_type_enum
        mgr_path = paths.TUNING_ROOTS[definition.resource_type]
        mgr_factory = InstanceManager
        args = (mgr_path, mgr_type)
        kwargs = {}
        kwargs['use_guid_for_ref'] = definition.use_guid_for_ref
        kwargs['base_game_only'] = definition.base_game_only
        kwargs['require_reference'] = definition.require_reference
        if mgr_type == Types.OBJECT:
            from objects.definition_manager import DefinitionManager
            mgr_factory = DefinitionManager
        elif mgr_type == Types.TUNING:
            from sims4.tuning.module_tuning import ModuleTuningManager
            mgr_factory = ModuleTuningManager
        elif mgr_type == Types.ASPIRATION:
            from aspirations.aspiration_instance_manager import AspirationInstanceManager
            mgr_factory = AspirationInstanceManager
        elif mgr_type == Types.INTERACTION:
            from interactions.interaction_instance_manager import InteractionInstanceManager
            mgr_factory = InteractionInstanceManager
        return mgr_factory(*args, **kwargs)
