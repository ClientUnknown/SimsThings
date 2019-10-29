import operatorfrom business.business_enums import BusinessEmployeeTypefrom filters.tunable import TunableSimFilterfrom interactions import ParticipantTypefrom interactions.base.picker_interaction import PickerSuperInteractionfrom interactions.context import QueueInsertStrategyfrom interactions.utils.tunable import TunableContinuationfrom sims.outfits.outfit_enums import OutfitCategory, TODDLER_PROHIBITED_OUTFIT_CATEGORIESfrom sims.sim_info_types import Genderfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableEnumEntry, TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, OptionalTunable, TunableListfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom ui.ui_dialog_picker import TunableUiOutfitPickerSnippet, OutfitPickerRow, UiSimPicker, SimPickerRowimport services
class OutfitPickerSuperInteraction(PickerSuperInteraction):

    class _OutfitPickerActionPushInteraction(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'continuation': TunableContinuation(description='\n                The continuation to push. The selected outfits are the picked\n                item of the pushed interaction.\n                ')}

        def get_disabled_tooltip(self):
            pass

        def on_choice_selected(self, interaction, picked_items, **kwargs):
            interaction.push_tunable_continuation(self.continuation, insert_strategy=QueueInsertStrategy.LAST, picked_item_ids=picked_items)

    class _OutfitActionDeleteOutfit(HasTunableSingletonFactory, AutoFactoryInit):

        def get_disabled_tooltip(self):
            pass

        def on_choice_selected(self, interaction, picked_items, **kwargs):
            outfit_participant = interaction.outfit_sim_info.get_outfit_sim_info(interaction)
            outfits = outfit_participant.get_outfits()
            current_outfit = outfit_participant.get_current_outfit()
            for outfit in sorted(picked_items, key=operator.itemgetter(1), reverse=True):
                if current_outfit[1] >= outfit[1]:
                    current_outfit = (current_outfit[0], current_outfit[1] - 1)
                outfits.remove_outfit(*outfit)
            sim_info = outfits.get_sim_info()
            sim_info.resend_outfits()
            sim_info.set_current_outfit(current_outfit)

    class _OutfitActionApplyCareerOutfit(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'picker_dialog': UiSimPicker.TunableFactory(description='\n                The picker dialog to show when selecting Sims to apply this\n                outfit on.\n                '), 'sim_filter': TunableSimFilter.TunableReference(description='\n                The set of available Sims to show in the Sim picker.\n                '), 'pie_menu_test_tooltip': OptionalTunable(description='\n                If enabled, then a greyed-out tooltip will be displayed if there\n                are no valid choices.\n                ', tunable=TunableLocalizedStringFactory(description='\n                    The tooltip text to show in the greyed-out tooltip when no\n                    valid choices exist.\n                    '))}

        def get_disabled_tooltip(self):
            if self.pie_menu_test_tooltip is None:
                return
            else:
                filter_results = self._get_filter_results()
                if not filter_results:
                    return self.pie_menu_test_tooltip

        def get_sim_filter_gsi_name(self):
            return str(self)

        def _get_filter_results(self):
            return services.sim_filter_service().submit_filter(self.sim_filter, None, allow_yielding=False, gsi_source_fn=self.get_sim_filter_gsi_name)

        def _get_on_sim_choice_selected(self, interaction, picked_items):

            def _on_sim_choice_selected(dialog):
                if dialog.accepted:
                    outfit_source = interaction.outfit_sim_info.get_outfit_sim_info(interaction)
                    for sim_info in dialog.get_result_tags():
                        sim_info.generate_merged_outfit(outfit_source, (OutfitCategory.CAREER, 0), sim_info.get_current_outfit(), picked_items[0])
                        sim_info.resend_current_outfit()

            return _on_sim_choice_selected

        def on_choice_selected(self, interaction, picked_items, **kwargs):
            dialog = self.picker_dialog(interaction.sim, title=lambda *_, **__: interaction.get_name(apply_name_modifiers=False), resolver=interaction.get_resolver())
            for filter_result in self._get_filter_results():
                dialog.add_row(SimPickerRow(filter_result.sim_info.sim_id, tag=filter_result.sim_info))
            dialog.add_listener(self._get_on_sim_choice_selected(interaction, picked_items))
            dialog.show_dialog()

    class _OutfitSimInfoSelectorParticipant(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n                The participant that has outfits that we want to display. This\n                must be either a Sim or an object with a component that supports\n                outfits, such as the Mannequin component.\n                ', tunable_type=ParticipantType, default=ParticipantType.Actor)}

        def get_outfit_sim_info(self, interaction, **kwargs):
            return interaction.get_participant(self.participant, **kwargs)

    class _OutfitSimInfoSelectorBusiness(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'employee_type': TunableEnumEntry(description='\n                The employee type for the business we should select outfits for.\n                If this employee type is not valid for the business on this lot,\n                nothing will happen.\n                ', tunable_type=BusinessEmployeeType, default=BusinessEmployeeType.INVALID, invalid_enums=(BusinessEmployeeType.INVALID,)), 'gender': TunableEnumEntry(description="\n                The gender of the retail store's employee uniform mannequin from\n                which we want to select outfits.\n                ", tunable_type=Gender, default=Gender.MALE)}

        def get_outfit_sim_info(self, interaction, **_):
            business_manager = services.business_service().get_business_manager_for_zone()
            if business_manager is None:
                return
            elif business_manager.is_valid_employee_type(self.employee_type):
                return business_manager.get_employee_uniform_data(self.employee_type, self.gender)

    INSTANCE_TUNABLES = {'picker_dialog': TunableUiOutfitPickerSnippet(description="\n            The interaction's outfit picker.\n            ", tuning_group=GroupNames.PICKERTUNING), 'outfit_sim_info': TunableVariant(description='\n            Define the Sim or object whose outfits are to be displayed.\n            ', from_participant=_OutfitSimInfoSelectorParticipant.TunableFactory(), from_business=_OutfitSimInfoSelectorBusiness.TunableFactory(), default='from_participant', tuning_group=GroupNames.PICKERTUNING), 'allow_current_outfit': OptionalTunable(description='\n            Whether or not the current outfit is a selectable entry.\n            ', tunable=TunableLocalizedStringFactory(description='\n                The tooltip to show on the current outfit.\n                '), enabled_name='Disallow', disabled_name='Allow', tuning_group=GroupNames.PICKERTUNING), 'outfit_actions': TunableList(description='\n            All the actions to undertake once a selection has been made.\n            ', tunable=TunableVariant(description='\n                The action to undertake once a selection has been made.\n                ', push_affordance=_OutfitPickerActionPushInteraction.TunableFactory(), delete_outfit=_OutfitActionDeleteOutfit.TunableFactory(), apply_career_outfit=_OutfitActionApplyCareerOutfit.TunableFactory(), default='push_affordance'), tuning_group=GroupNames.PICKERTUNING)}

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        if not cls._has_valid_outfit_choice(target, context, **kwargs):
            return False
        elif not cls._has_valid_outfit_action():
            return False
        return True

    @classmethod
    def _has_valid_outfit_choice(cls, target, context, **kwargs):
        outfit_participant = cls._get_outfit_participant(target, context, **kwargs)
        if outfit_participant is None:
            return False
        else:
            outfits = outfit_participant.get_outfits()
            outfit_categories = cls._get_valid_outfit_categories(outfit_participant)
            if not any(outfit_category in outfit_categories and outfit_list for (outfit_category, outfit_list) in outfits.get_all_outfits()):
                return False
        return True

    @classmethod
    def _has_valid_outfit_action(cls):
        return cls._get_invalid_outfit_action() is None

    @classmethod
    def _get_invalid_outfit_action(cls):
        for outfit_action in cls.outfit_actions:
            disabled_tooltip = outfit_action.get_disabled_tooltip()
            if disabled_tooltip is not None:
                return disabled_tooltip

    @classmethod
    def _get_valid_outfit_categories(cls, outfit_participant):
        outfit_categories = set(cls.picker_dialog.outfit_categories)
        if outfit_participant is not None:
            outfits = outfit_participant.get_outfits()
            if outfits.is_toddler:
                outfit_categories -= TODDLER_PROHIBITED_OUTFIT_CATEGORIES
        return outfit_categories

    @flexmethod
    def _get_outfit_participant(cls, inst, target, context, **kwargs):
        if inst is not None:
            return inst.outfit_sim_info.get_outfit_sim_info(inst)
        return cls.outfit_sim_info.get_outfit_sim_info(cls, sim=context.sim, target=target, **kwargs)

    @classmethod
    def get_disabled_tooltip(cls, *args, **kwargs):
        if not cls._has_valid_outfit_choice(*args, **kwargs):
            return cls.pie_menu_test_tooltip
        return cls._get_invalid_outfit_action()

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim, target=self.target)
        return True

    def _setup_dialog(self, dialog, **kwargs):
        super()._setup_dialog(dialog, **kwargs)
        if self.picker_dialog.show_filter:
            outfit_participant = self._get_outfit_participant(self.target, self.context, **kwargs)
            dialog.outfit_category_filters = self._get_valid_outfit_categories(outfit_participant)

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        outfit_participant = inst_or_cls._get_outfit_participant(target, context, **kwargs)
        if outfit_participant is not None:
            current_outfit = outfit_participant.get_current_outfit()
            outfits = outfit_participant.get_outfits()
            outfit_sim_info = outfits.get_sim_info()
            outfit_categories = inst_or_cls._get_valid_outfit_categories(outfit_participant)
            for (outfit_category, outfit_list) in outfits.get_all_outfits():
                if outfit_category not in outfit_categories:
                    pass
                else:
                    for (outfit_index, _) in enumerate(outfit_list):
                        outfit_key = (outfit_category, outfit_index)
                        if not inst_or_cls.allow_current_outfit is not None or current_outfit == outfit_key:
                            is_enable = False
                            row_tooltip = lambda *_, **__: inst_or_cls.create_localized_string(inst_or_cls.allow_current_outfit)
                        else:
                            is_enable = True
                            row_tooltip = None
                        yield OutfitPickerRow(outfit_sim_id=outfit_sim_info.sim_id, outfit_category=outfit_category, outfit_index=outfit_index, is_enable=is_enable, row_tooltip=row_tooltip, tag=outfit_key)

    def _on_picker_selected(self, dialog):
        if dialog.accepted:
            picked_items = dialog.get_result_tags()
            for outfit_action in self.outfit_actions:
                outfit_action.on_choice_selected(self, picked_items)
