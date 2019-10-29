from interactions.base.picker_interaction import PickerSuperInteractionfrom sims4.localization import LocalizationHelperTuning, TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableReference, TunableList, OptionalTunablefrom sims4.utils import flexmethodfrom ui.ui_dialog_generic import UiDialogTextInputOkCancelfrom ui.ui_dialog_picker import ObjectPickerRowimport servicesimport sims4TEXT_INPUT_STAT_VALUE = 'stat_value'
class CheatSetStatSuperInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'stat_value_dialog': UiDialogTextInputOkCancel.TunableFactory(description="\n            The dialog that is displayed (and asks for the user to enter\n            a value to set for the statistic).\n                \n            the selected stat's name is passed as a token as well as the\n            stat's value is passed as an input override.\n            ", text_inputs=(TEXT_INPUT_STAT_VALUE,)), 'stat_value_text': TunableLocalizedStringFactory(description='\n            the string that will show the current value in the picker \n            and within the input override. Should include {0.Number}.\n            ', default=1989018490), 'stat_list': OptionalTunable(tunable=TunableList(description='\n                List of stats we want to allow to be changed by this interaction.\n                If nothing is set, it will just show all the stats on the object.\n                ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), pack_safe=True)))}

    def _get_object_stats_gen(self, target):
        if target.statistic_tracker is not None:
            yield from target.statistic_tracker
        if target.commodity_tracker is not None:
            yield from target.commodity_tracker

    def _get_displayable_stat_name(self, stat):
        if self.stat_list is None or stat.stat_type in self.stat_list:
            return self._get_stat_name(self, stat.stat_type)

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        for stat in cls._get_object_stats_gen(cls, target):
            if cls._get_displayable_stat_name(cls, stat) is not None:
                return True
        return False

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        for stat in inst_or_cls._get_object_stats_gen(target):
            stat_name = cls._get_displayable_stat_name(cls, stat)
            if stat_name is not None:
                stat_tracker = target.get_tracker(stat)
                stat_value = inst_or_cls.stat_value_text(stat_tracker.get_value(stat.stat_type))
                stat_icon = inst_or_cls._get_stat_icon(stat.stat_type)
                yield ObjectPickerRow(name=stat_name, row_description=stat_value, tag=stat.stat_type, icon=stat_icon)

    def _get_stat_name(self, stat):
        stat_name = getattr(stat, 'stat_name', None)
        if stat_name and stat.stat_name.hash is not 0:
            return stat.stat_name
        elif False and self.debug:
            return LocalizationHelperTuning.get_raw_text(stat.__name__)

    def _get_stat_icon(self, stat):
        if hasattr(stat, 'icon'):
            return stat.icon
        else:
            states = getattr(stat, 'states', ())
            if states:
                return stat.states[0].icon

    def on_choice_selected(self, choice_tag, **kwargs):
        if choice_tag is None:
            return
        statistic = choice_tag
        target = self.target

        def on_response(value_dialog):
            if not value_dialog.accepted:
                return
            new_value = value_dialog.text_input_responses.get(TEXT_INPUT_STAT_VALUE)
            try:
                new_value = int(new_value)
            except:
                return
            tracker = target.get_tracker(statistic)
            tracker.set_value(statistic, new_value)

        stat_name = self._get_stat_name(statistic)
        stat_tracker = target.get_tracker(statistic)
        stat_value = self.stat_value_text(stat_tracker.get_value(statistic))
        text_input_overrides = {}
        text_input_overrides[TEXT_INPUT_STAT_VALUE] = lambda *_, **__: stat_value
        tokens = (stat_name, statistic.min_value, statistic.max_value)
        dialog = self.stat_value_dialog(target, self.get_resolver())
        dialog.show_dialog(on_response=on_response, text_input_overrides=text_input_overrides, additional_tokens=tokens)
