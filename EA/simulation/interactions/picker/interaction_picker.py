from event_testing.tests import TunableTestSetfrom interactions.base.picker_interaction import PickerSuperInteractionfrom interactions.context import InteractionSourcefrom interactions.utils.localization_tokens import LocalizationTokensfrom interactions.utils.tunable import TunableContinuationfrom interactions.utils.tunable_icon import TunableIconVariantfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableList, OptionalTunable, HasTunableSingletonFactory, AutoFactoryInitfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom snippets import define_snippetfrom ui.ui_dialog_picker import BasePickerRow, UiItemPicker
class InteractionPickerItem(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'icon': OptionalTunable(description='\n            If enabled, specify the icon to be displayed in UI.\n            ', tunable=TunableIconVariant()), 'name': OptionalTunable(description='\n            If enabled, display this name in the UI.\n            \n            Otherwise the display name of the first affordance\n            in the continuation will be used as the name.\n            ', tunable=TunableLocalizedStringFactory()), 'item_description': OptionalTunable(description='\n            When enabled, the tuned string will be shown as a description.\n            ', tunable=TunableLocalizedStringFactory()), 'item_tooltip': OptionalTunable(description='\n            When enabled, the tuned string will be shown as a tooltip.\n            ', tunable=TunableLocalizedStringFactory()), 'disable_tooltip': OptionalTunable(description='\n            When tuned, and the item is disabled, the tuned string \n            will be shown as a tooltip.\n            \n            Otherwise it will try to grab a tooltip off a failed test.\n            ', tunable=TunableLocalizedStringFactory()), 'continuation': TunableContinuation(description='\n            The continuation to push when this item is selected.\n            ', minlength=1), 'enable_tests': OptionalTunable(description='\n            Tests which would dictate if this option is enabled\n            in the pie menu.  ORs of ANDs.\n            \n            If disabled, it will default to the tests for the\n            first affordance in the continuation chain.\n            ', tunable=TunableTestSet()), 'localization_tokens': OptionalTunable(description="\n            Additional localization tokens for this item\n            to use in the name/description.\n            \n            This is in addition to the display name tokens\n            tuned in the continuation's first affordance.\n            ", tunable=LocalizationTokens.TunableFactory()), 'visibility_tests': OptionalTunable(description='\n            Tests which would dictate if this option is visible\n            in the pie menu.  ORs of ANDs.\n            \n            If disabled, this item will always be visible.\n            ', tunable=TunableTestSet())}
(_, TunableInteractionPickerItemSnippet) = define_snippet('interaction_picker_item', InteractionPickerItem.TunableFactory())
class InteractionPickerSuperInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': UiItemPicker.TunableFactory(description='\n            The item picker dialog.\n            ', tuning_group=GroupNames.PICKERTUNING), 'possible_actions': TunableList(description='\n            A list of the interactions that will show up in the dialog picker\n            ', tunable=TunableInteractionPickerItemSnippet(), minlength=1, tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = cls if inst is None else inst
        cloned_context = context.clone_for_insert_next(source=InteractionSource.SCRIPT_WITH_USER_INTENT)
        for choice in inst_or_cls.possible_actions:
            first_continuation = next(iter(choice.continuation), None)
            if first_continuation is None:
                pass
            else:
                affordance = first_continuation.affordance
                resolver = affordance.get_resolver(target=target, context=cloned_context, **kwargs)
                if not choice.visibility_tests or not choice.visibility_tests.run_tests(resolver):
                    pass
                else:
                    tokens = tuple() if choice.localization_tokens is None else choice.localization_tokens.get_tokens(resolver)
                    display_name = affordance.get_name(target=target, context=cloned_context) if choice.name is None else affordance.create_localized_string(choice.name, tokens, target=target, context=cloned_context, **kwargs)
                    icon_info = None if choice.icon is None else choice.icon(resolver)
                    display_description = None if choice.item_description is None else affordance.create_localized_string(choice.item_description, tokens, target=target, context=cloned_context, **kwargs)
                    row_tooltip = None
                    tag = choice
                    if choice.enable_tests:
                        test_result = choice.enable_tests.run_tests(resolver)
                    else:
                        test_result = affordance.test(target=target, context=cloned_context)
                    row_tooltip = choice.item_tooltip
                    row_tooltip = test_result.tooltip
                    is_enabled = bool(test_result)
                    row_tooltip = choice.disable_tooltip
                    row = BasePickerRow(is_enable=is_enabled, name=display_name, icon_info=icon_info, row_description=display_description, tag=tag, row_tooltip=row_tooltip)
                    yield row

    def on_choice_selected(self, choice, **kwargs):
        if choice is not None:
            self.push_tunable_continuation(choice.continuation)
