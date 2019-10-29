from interactions.utils.tunable_icon import TunableIconfrom sims4.localization import TunableLocalizedString, TunableLocalizedStringFactoryfrom sims4.tuning.tunable import OptionalTunable, TunableTuplefrom sims4.tuning.tunable_base import GroupNames, ExportModesfrom sims4.utils import classproperty
def get_display_mixin(has_description=False, has_icon=False, has_tooltip=False, use_string_tokens=False, export_modes=(), enabled_by_default=False):
    tunable_localized_string_type = TunableLocalizedStringFactory if use_string_tokens else TunableLocalizedString
    export_to_client = ExportModes.ClientBinary in export_modes
    display_properties = {'instance_display_name': OptionalTunable(description='\n            If enabled, specify a display name for this instance.\n            ', tunable=tunable_localized_string_type(description="\n                The instance's name.\n                "), enabled_by_default=True, export_modes=export_modes, enabled_name='enabled_display_name' if export_to_client else 'enabled')}
    if has_description:
        display_properties['instance_display_description'] = OptionalTunable(description='\n            If enabled, specify a display description for this instance.\n            ', tunable=tunable_localized_string_type(description="\n                The instance's description. \n                "), enabled_by_default=True, export_modes=export_modes, enabled_name='enabled_display_description' if export_to_client else 'enabled')
    if has_icon:
        display_properties['instance_display_icon'] = OptionalTunable(description='\n            If enabled, specify a display icon for this instance.\n            ', tunable=TunableIcon(description="\n                The instance's icon.\n                "), enabled_by_default=True, export_modes=export_modes, enabled_name='enabled_display_icon' if export_to_client else 'enabled')
    if has_tooltip:
        display_properties['instance_display_tooltip'] = OptionalTunable(description='\n            If enabled, specify a display tooltip for this instance.\n            ', tunable=tunable_localized_string_type(description="\n                The instance's tooltip. \n                "), enabled_by_default=True, export_modes=export_modes, enabled_name='enabled_display_tooltip' if export_to_client else 'enabled')

    class _HasOptionalDisplayMixin:
        INSTANCE_TUNABLES = {'_display_data': OptionalTunable(description='\n                If enabled, specify display data for this instance.\n                ', tunable=TunableTuple(description="\n                    The instance's display data.\n                    ", export_class_name='OptionalDisplayMixinTunable' if export_to_client else 'TunableTuple', **display_properties), tuning_group=GroupNames.UI, export_modes=export_modes, enabled_name='optional_display_mixin' if export_to_client else 'enabled', enabled_by_default=enabled_by_default)}

    TUNING_FIELD_PREFIX = 'instance_'
    for display_property_name in display_properties:
        if display_property_name.startswith(TUNING_FIELD_PREFIX):
            property_name = display_property_name[len(TUNING_FIELD_PREFIX):]
        else:
            property_name = display_property_name
        setattr(_HasOptionalDisplayMixin, property_name, classproperty(lambda c, attr_name=display_property_name: getattr(c._display_data, attr_name) if c._display_data is not None else None))
    return _HasOptionalDisplayMixin
