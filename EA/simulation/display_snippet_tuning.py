from event_testing.resolver import InteractionResolverfrom event_testing.tests import TunableTestSetWithTooltipfrom interactions import ParticipantTypeSimfrom interactions.base.picker_interaction import PickerSuperInteractionfrom interactions.utils.display_mixin import get_display_mixinfrom interactions.utils.localization_tokens import LocalizationTokensfrom interactions.utils.loot import LootActionsfrom interactions.utils.tunable import TunableContinuationfrom sims4.tuning.tunable import TunableEnumFlags, TunableList, TunableTuple, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom singletons import DEFAULTfrom ui.ui_dialog_picker import TunablePickerDialogVariant, ObjectPickerTuningFlags, BasePickerRowimport servicesimport sims4.tuninglogger = sims4.log.Logger('Display Snippet', default_owner='shipark')SnippetDisplayMixin = get_display_mixin(use_string_tokens=True, has_description=True, has_icon=True, has_tooltip=True, enabled_by_default=True)
class DisplaySnippet(SnippetDisplayMixin, metaclass=sims4.tuning.instances.HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.SNIPPET)):
    pass

class DisplaySnippetPickerSuperInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': TunablePickerDialogVariant(description='\n            The item picker dialog.\n            ', available_picker_flags=ObjectPickerTuningFlags.ITEM, tuning_group=GroupNames.PICKERTUNING), 'subject': TunableEnumFlags(description="\n            To whom 'loot on selected' should be applied.\n            ", enum_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor, tuning_group=GroupNames.PICKERTUNING), 'display_snippets': TunableList(description='\n            The list of display snippets available to select and paired loot actions\n            that will run if selected.\n            ', tunable=TunableTuple(display_snippet=TunableReference(description='\n                    A display snippet that holds the display data that will\n                    populate the row in the picker.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions='DisplaySnippet', allow_none=False), loot_on_selected=TunableList(description='\n                    A list of loot actions that will be applied to the subject Sim.\n                    ', tunable=LootActions.TunableReference(description='\n                        A loot action applied to the subject Sim.\n                        ')), tests=TunableTestSetWithTooltip(description='\n                    Test set that must pass for this snippet to be available.\n                    NOTE: A tooltip test result will take priority over any\n                    instance display tooltip tuned in the display snippet.\n                    ')), tuning_group=GroupNames.PICKERTUNING), 'display_snippet_text_tokens': LocalizationTokens.TunableFactory(description='\n            Localization tokens passed into the display snippet text fields.\n            ', tuning_group=GroupNames.PICKERTUNING), 'continuations': TunableList(description='\n            List of continuations to push when a snippet is selected.\n            ', tunable=TunableContinuation(), tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim)
        return True

    @classmethod
    def _display_snippet_selection_gen(cls):
        if cls.display_snippets:
            for display_snippet_data in cls.display_snippets:
                yield (display_snippet_data.display_snippet.display_name, display_snippet_data.display_snippet.display_icon, display_snippet_data.display_snippet.display_description, display_snippet_data.display_snippet.display_tooltip, display_snippet_data.loot_on_selected, display_snippet_data.tests)

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        target = target if target is not DEFAULT else inst.target
        context = context if context is not DEFAULT else inst.context
        resolver = InteractionResolver(cls, inst, target=target, context=context)
        tokens = inst_or_cls.display_snippet_text_tokens.get_tokens(resolver)
        for (name, icon, description, display_tooltip, loot, tests) in inst_or_cls._display_snippet_selection_gen():
            test_result = tests.run_tests(resolver, search_for_tooltip=True)
            is_enable = test_result.result
            if is_enable or test_result.tooltip is not None:
                tooltip = None if test_result.tooltip is None else lambda *_, tooltip=test_result.tooltip: tooltip(*tokens)
                tooltip = None if display_tooltip is None else lambda *_, tooltip=display_tooltip: tooltip(*tokens)
                row = BasePickerRow(is_enable=is_enable, name=name(*tokens), icon=icon, tag=loot, row_description=description(*tokens), row_tooltip=tooltip)
                yield row

    def _on_display_snippet_selected(self, picked_choice, **kwargs):
        if not picked_choice:
            logger.error('Picked choice for interaction {} cannot be empty, there is no result from picked choice', self)
            return
        for participant in self.get_participants(self.subject):
            for loot_action in picked_choice[0].loot_actions:
                loot_action._apply_to_subject_and_target(participant, self.target, self.get_resolver())

    def on_choice_selected(self, picked_choice, **kwargs):
        self._on_display_snippet_selected(picked_choice, **kwargs)
        for continuation in self.continuations:
            self.push_tunable_continuation(continuation)
