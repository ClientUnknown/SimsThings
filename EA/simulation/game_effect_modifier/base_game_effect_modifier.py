
class BaseGameEffectModifier:

    def __init__(self, modifier_type):
        self.modifier_type = modifier_type

    def apply_modifier(self, sim_info):
        pass

    def remove_modifier(self, sim_info, handle):
        pass
