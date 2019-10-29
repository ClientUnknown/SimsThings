from animation.focus.focus_ops import SetFocusScorefrom animation.focus.focus_score import TunableFocusScoreVariantfrom objects.components import Component, types, componentmethodfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInitfrom sims4.tuning.tunable_hash import TunableStringHash32import distributor.fields
class FocusComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=types.FOCUS_COMPONENT):
    FACTORY_TUNABLES = {'_focus_bone': TunableStringHash32(description='\n            The bone Sims direct their attention towards when focusing on an\n            object.\n            ', default='_focus_'), '_focus_score': TunableFocusScoreVariant()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_focus_score = self._focus_score

    @distributor.fields.ComponentField(op=SetFocusScore)
    def focus_score(self):
        return self._current_focus_score

    @focus_score.setter
    def focus_score(self, value):
        self._current_focus_score = value

    @componentmethod
    def get_focus_bone(self):
        return self._focus_bone
