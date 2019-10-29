from objects.components import Component, types
class StageMarkComponent(Component, allow_dynamic=True, component_name=types.STAGE_MARK_COMPONENT):

    def __init__(self, *args, performance_interactions=(), **kwargs):
        super().__init__(*args, **kwargs)
        self._performance_interactions = performance_interactions

    def component_super_affordances_gen(self, **kwargs):
        yield from self._performance_interactions
