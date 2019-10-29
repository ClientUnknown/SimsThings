from sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import TunableEnumEntry, Tunableimport enumimport sims4.loglogger = sims4.log.Logger('Autonomy')
class AutonomyState(enum.Int):
    UNDEFINED = -1
    DISABLED = 0
    LIMITED_ONLY = 1
    MEDIUM = 2
    FULL = 3

class AutonomyRandomization(enum.Int):
    UNDEFINED = -1
    DISABLED = 0
    ENABLED = 1

class AutonomySettingsGroup(DynamicEnum):
    DEFAULT = 0

class AutonomySettingItem:
    __slots__ = ('state', 'randomization')

    def __init__(self, state:AutonomyState=AutonomyState.UNDEFINED, randomization:AutonomyRandomization=AutonomyRandomization.UNDEFINED):
        self.state = state
        self.randomization = randomization

class _AutonomySettings:

    def __init__(self, use_tuned_defaults=False):
        if use_tuned_defaults:
            self._autonomy_settings = {AutonomyRandomization: AutonomySettings.STARTING_DEFAULT_RANDOMIZATION, AutonomyState: AutonomySettings.STARTING_DEFAULT_AUTONOMY_STATE}
        else:
            self._autonomy_settings = {AutonomyRandomization: AutonomyRandomization.UNDEFINED, AutonomyState: AutonomyState.UNDEFINED}

    def get_setting(self, autonomy_setting_class):
        setting = self._autonomy_settings.get(autonomy_setting_class)
        if setting is None:
            logger.error('Failed to find autonomy setting for class: {}', autonomy_setting_class, owner='rez')
        return setting

    def set_setting(self, autonomy_setting_class, setting_value):
        self._autonomy_settings[autonomy_setting_class] = setting_value

class AutonomySettings:
    STARTING_DEFAULT_AUTONOMY_STATE = TunableEnumEntry(description='\n        The autonomy state for the "default" layer.  If a Sim doesn\'t have\n        anything that overrides their autonomy state, this will be used instead.\n        It is NOT used to define the default option in the autonomy options\n        menu, it applies to all Sims that don\'t have an overridden autonomy\n        state setting.  Sims in the playable household will all have an\n        overridden setting.\n        ', tunable_type=AutonomyState, default=AutonomyState.FULL)
    STARTING_DEFAULT_RANDOMIZATION = TunableEnumEntry(description='\n        The randomization state for the "default" layer.  If a Sim doesn\'t have\n        anything that overrides their randomization state, this will be used\n        instead.\n        ', tunable_type=AutonomyRandomization, default=AutonomyRandomization.ENABLED)
    STARTING_HOUSEHOLD_AUTONOMY_STATE = TunableEnumEntry(description="\n        The default autonomy setting when one hasn't been loaded.  This is the\n        default value for the autonomy drop-down in the options menu.\n        ", tunable_type=AutonomyState, default=AutonomyState.FULL)
    STARTING_SELECTED_SIM_AUTONOMY = Tunable(description="\n        The default autonomy setting for the selected sim's autonomy.  If\n        checked, the selected sim will behave normally according to the autonomy\n        state.  If unchecked, the selected sim will not run autonomy at all.\n        ", tunable_type=bool, default=True)

    def __init__(self, **kwargs):
        self._setting_groups = {settings_group: _AutonomySettings(**kwargs) for settings_group in AutonomySettingsGroup}

    def get_setting(self, setting_type, settings_group):
        return self._setting_groups[settings_group].get_setting(setting_type)

    def set_setting(self, setting_value, settings_group):
        return self._setting_groups[settings_group].set_setting(type(setting_value), setting_value)
