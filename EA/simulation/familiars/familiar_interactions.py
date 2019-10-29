import servicesfrom event_testing.resolver import SingleSimResolverfrom interactions import ParticipantTypefrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom interactions.base.picker_interaction import PickerSuperInteractionfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableVariantfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom ui.ui_dialog_generic import UiDialogTextInputOkCancelfrom ui.ui_dialog_picker import BasePickerRowfrom world import region
class SetActiveFamiliarAction(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, interaction, picked_choice):
        interaction.sim.sim_info.familiar_tracker.set_active_familiar(picked_choice)

class UnbindFamiliarAction(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, interaction, picked_choice):
        interaction.sim.sim_info.familiar_tracker.unbind_familiar(picked_choice)

class FamiliarPickerInteraction(PickerSuperInteraction):
    INSTANCE_TUNABLES = {'picker_action': TunableVariant(description='\n            The action to take after selecting a familiar from the picker.\n            ', set_active_familiar=SetActiveFamiliarAction.TunableFactory(), unbind_familiar=UnbindFamiliarAction.TunableFactory(), default='set_active_familiar', tuning_group=GroupNames.PICKERTUNING), 'incompatible_region_disabled_tooltip': TunableLocalizedStringFactory(description='\n            Tooltip that displays if a pet familiar is in an incompatible region.\n            '), 'rabbit_holed_disabled_tooltip': TunableLocalizedStringFactory(description='\n            Tooltip that displays if a pet familiar is in a rabbit hole.\n            ')}

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        for _ in cls.picker_rows_gen(target, context, **kwargs):
            return True
        return False

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        actor = inst_or_cls.get_participant(sim=context.sim, target=target, participant_type=ParticipantType.Actor, **kwargs)
        familiar_tracker = actor.sim_info.familiar_tracker
        if familiar_tracker is not None:
            rabbit_hole_service = services.get_rabbit_hole_service()
            current_region = services.current_region()
            sim_info_manager = services.sim_info_manager()
            for familiar_info in familiar_tracker:
                is_enable = True
                row_tooltip = None
                if rabbit_hole_service.is_in_rabbit_hole(familiar_info.pet_familiar_id):
                    is_enable = False
                    row_tooltip = inst_or_cls.rabbit_holed_disabled_tooltip
                else:
                    pet_familiar = sim_info_manager.get(familiar_info.pet_familiar_id)
                    sim_region = region.get_region_instance_from_zone_id(pet_familiar.zone_id)
                    is_enable = False
                    row_tooltip = inst_or_cls.incompatible_region_disabled_tooltip
                row = BasePickerRow(name=familiar_info.name, icon_info=familiar_info.icon_info, tag=familiar_info.uid, is_enable=is_enable, row_tooltip=row_tooltip)
                yield row

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim)
        return True

    def on_choice_selected(self, picked_choice, **kwargs):
        if picked_choice is None:
            return
        self.picker_action(self, picked_choice)
TEXT_INPUT_NEW_NAME = 'new_name'
class NameFamiliarInteraction(ImmediateSuperInteraction):
    INSTANCE_TUNABLES = {'rename_dialog': UiDialogTextInputOkCancel.TunableFactory(description='\n            The dialog to select a new Name for the familiar.\n            ', text_inputs=(TEXT_INPUT_NEW_NAME,))}

    def _run_interaction_gen(self, timeline):
        sim_info = self.sim.sim_info
        familiar_tracker = sim_info.familiar_tracker
        if familiar_tracker is None:
            return True
        familiar_to_rename = familiar_tracker.active_familiar_id
        if familiar_to_rename is None:
            return True

        def on_response(dialog_response):
            if not dialog_response.accepted:
                return
            name = dialog_response.text_input_responses.get(TEXT_INPUT_NEW_NAME)
            familiar_tracker.set_familiar_name(familiar_to_rename, name)

        familiar_icon = familiar_tracker.get_familiar_icon(familiar_to_rename)
        familiar_description = familiar_tracker.get_familiar_description(familiar_to_rename)
        text_input_overrides = {TEXT_INPUT_NEW_NAME: lambda *_, **__: familiar_tracker.get_familiar_name(familiar_to_rename)}
        dialog = self.rename_dialog(sim_info, SingleSimResolver(sim_info))
        dialog.show_dialog(on_response=on_response, text_input_overrides=text_input_overrides, icon_override=familiar_icon, text_override=familiar_description)
        return True
