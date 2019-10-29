from event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetWithTooltipfrom interactions import ParticipantTypefrom interactions.base.picker_interaction import PickerSuperInteractionfrom interactions.utils.loot import LootActionsfrom interactions.utils.tunable import TunableContinuationfrom sims4.tuning.tunable import TunableList, TunableTuple, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom ui.ui_dialog_picker import UiItemPicker, BasePickerRowimport servicesimport sims4.resources
class TimedAspirationPickerInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'picker_dialog': UiItemPicker.TunableFactory(description='\n            The timed aspiration picker dialog.\n            ', tuning_group=GroupNames.PICKERTUNING), 'timed_aspirations': TunableList(description='\n            The list of timed aspirations available to select.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='TimedAspiration', pack_safe=True), unique_entries=True, tuning_group=GroupNames.PICKERTUNING), 'actor_continuation': TunableContinuation(description='\n            If specified, a continuation to push on the actor when a picker \n            selection has been made.\n            ', locked_args={'actor': ParticipantType.Actor}, tuning_group=GroupNames.PICKERTUNING), 'loot_on_picker_selection': TunableList(description="\n            Loot that will be applied to the Sim if an aspiration is selected.\n            It will not be applied if the user doesn't select an aspiration.\n            ", tunable=LootActions.TunableReference(), tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        resolver = SingleSimResolver(target.sim_info)
        for timed_aspiration in inst_or_cls.timed_aspirations:
            test_result = timed_aspiration.tests.run_tests(resolver, search_for_tooltip=True)
            is_enable = test_result.result
            if is_enable or test_result.tooltip is not None:
                if test_result.tooltip is not None:
                    row_tooltip = lambda *_, tooltip=test_result.tooltip, **__: inst_or_cls.create_localized_string(tooltip)
                else:
                    row_tooltip = None
                row = BasePickerRow(is_enable=is_enable, name=inst_or_cls.create_localized_string(timed_aspiration.display_name), icon=timed_aspiration.display_icon, row_description=inst_or_cls.create_localized_string(timed_aspiration.display_description), row_tooltip=row_tooltip, tag=timed_aspiration)
                yield row

    def on_choice_selected(self, choice_tag, **kwargs):
        if choice_tag is None:
            return
        self.target.aspiration_tracker.activate_timed_aspiration(choice_tag)
        resolver = self.get_resolver()
        for loot_action in self.loot_on_picker_selection:
            loot_action.apply_to_resolver(resolver)
        if self.actor_continuation:
            self.push_tunable_continuation(self.actor_continuation)
