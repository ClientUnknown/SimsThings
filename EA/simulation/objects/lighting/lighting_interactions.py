from event_testing.results import TestResultfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom objects.components.lighting_component import LightingComponentfrom objects.lighting.lighting_dialog import UiDialogLightColorAndIntensityfrom objects.lighting.lighting_utils import LightingHelper, TunableLightTargetVariantfrom sims4.localization import TunableLocalizedStringfrom sims4.math import almost_equalfrom sims4.tuning.tunable import TunableTuple, TunableList, TunableColor, AutoFactoryInit, HasTunableSingletonFactory, TunableVariantfrom sims4.tuning.tunable_base import ExportModesimport sims4.loglogger = sims4.log.Logger('Lighting')
class LightColorTuning:

    class TunableLightTuple(TunableTuple):

        def __init__(self, *args, **kwargs):
            super().__init__(color=TunableColor.TunableColorRGBA(description='\n                Tunable RGBA values used to set the color of a light. Tuning the\n                A value will not do anything as it is not used.\n                '), name=TunableLocalizedString(description=' \n                The name of the color that appears when you mouse over it.\n                '))

    LIGHT_COLOR_VARIATION_TUNING = TunableList(description='\n        A list of all of the different colors you can set the lights to be.\n        ', tunable=TunableLightTuple(), maxlength=18, export_modes=(ExportModes.ClientBinary,))

class SwitchLightImmediateInteraction(ImmediateSuperInteraction):

    class _FromTuning(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'lighting_settings': LightingHelper.TunableFactory()}

        def test(self, target):
            if not self.lighting_settings.light_target.is_multi_light:
                dimmer_value = target.get_light_dimmer_value()
                lighting_settings_dimmer_value = self.lighting_settings.dimmer_value.get_dimmer_value(target)
                if lighting_settings_dimmer_value == LightingComponent.LIGHT_AUTOMATION_DIMMER_VALUE and dimmer_value < 0:
                    return TestResult(False, 'Light is already being automated')
                dimmer_equivalent_value = target.get_overridden_dimmer_value(lighting_settings_dimmer_value)
                lighting_settings_light_color = self.lighting_settings.light_color.get_light_color(target)
                if almost_equal(dimmer_equivalent_value, dimmer_value, epsilon=0.0001) and lighting_settings_light_color == target.get_light_color():
                    return TestResult(False, 'Light is already at the desired dimmer and color value.')
            return TestResult.TRUE

        def execute(self, interaction):
            self.lighting_settings.execute_lighting_helper(interaction)

    class _FromUi(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'light_target': TunableLightTargetVariant(description='\n                Define the set of lights this operation applies to (e.g. All\n                Lights, This Room, All Candles, etc...)\n                ')}

        def test(self, target):
            return TestResult.TRUE

        def execute(self, interaction):

            def _on_update(*, color, intensity):
                for light_target in self.light_target.get_light_target_gen(interaction):
                    light_target.set_user_intensity_override(intensity)
                    light_target.set_light_color(color)

            color = interaction.target.get_light_color()
            if color is not None:
                (r, g, b, _) = sims4.color.to_rgba_as_int(color)
            else:
                r = g = b = sims4.color.MAX_INT_COLOR_VALUE
            intensity = interaction.target.get_user_intensity_overrides()
            dialog = UiDialogLightColorAndIntensity(interaction.target, r, g, b, intensity, on_update=_on_update)
            dialog.show_dialog()

    INSTANCE_TUNABLES = {'lighting_setting_operation': TunableVariant(description="\n            Define the operation we're going to execute. We can either apply\n            settings from the tuning or display UI that allows the player to\n            affect this light.\n            ", from_tuning=_FromTuning.TunableFactory(), from_ui=_FromUi.TunableFactory(), default='from_tuning')}

    @classmethod
    def _test(cls, target, context, **kwargs):
        result = cls.lighting_setting_operation.test(target)
        if not result:
            return result
        return super()._test(target, context, **kwargs)

    def _run_interaction_gen(self, timeline):
        self.lighting_setting_operation.execute(self)
