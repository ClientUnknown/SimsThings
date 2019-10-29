from event_testing.resolver import SingleSimResolverfrom familiars.familiar_enums import FamiliarTypefrom interactions import ParticipantTypeSinglefrom interactions.utils.interaction_elements import XevtTriggeredElementfrom sims.sim_info_types import Speciesfrom sims4.log import Loggerfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumEntry, HasTunableSingletonFactory, TunableVariantfrom ui.ui_dialog_generic import UiDialogTextInputOkfrom ui.ui_dialog_notification import UiDialogNotificationlogger = Logger('Familiars', default_owner='jjacobson')
class BindPetFamiliar(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The Participant to Bind as a Familiar to the Sim.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.TargetSim), 'bound_familiar_tns': UiDialogNotification.TunableFactory(description='\n            TNS that is displayed when this pet is bound as a familiar.\n            ')}

    def bind_familiar(self, interaction, familiar_owner, familiar_tracker):
        familiar = interaction.get_participant(self.participant)
        if familiar.species == Species.CAT:
            familiar_type = FamiliarType.CAT
        elif familiar.species == Species.DOG:
            familiar_type = FamiliarType.DOG
        else:
            logger.error('Attempting to bind a Sim, {}, of species, {}, as a familiar which is unsupported behavior.', familiar, familiar.species)
            return
        familiar_tracker.bind_familiar(familiar_type, pet_familiar=familiar)
        dialog = self.bound_familiar_tns(familiar_owner, interaction.get_resolver())
        dialog.show_dialog()
TEXT_INPUT_NEW_NAME = 'new_name'
class BindObjectFamiliar(HasTunableSingletonFactory, AutoFactoryInit):
    RENAME_DIALOG = UiDialogTextInputOk.TunableFactory(description='\n        The dialog to select a new Name for the familiar.\n        ', text_inputs=(TEXT_INPUT_NEW_NAME,))
    FACTORY_TUNABLES = {'familiar_type': TunableEnumEntry(description='\n            The type of familiar to bind.\n            ', tunable_type=FamiliarType, default=FamiliarType.CAT, invalid_enums=(FamiliarType.CAT, FamiliarType.DOG))}

    def bind_familiar(self, interaction, familiar_owner, familiar_tracker):
        new_familiar = familiar_tracker.bind_familiar(self.familiar_type)

        def on_response(dialog_response):
            if not dialog_response.accepted:
                return
            name = dialog_response.text_input_responses.get(TEXT_INPUT_NEW_NAME)
            familiar_tracker.set_familiar_name(new_familiar, name)

        familiar_icon = familiar_tracker.get_familiar_icon(new_familiar)
        familiar_description = familiar_tracker.get_familiar_description(new_familiar)
        text_input_overrides = {TEXT_INPUT_NEW_NAME: lambda *_, **__: familiar_tracker.get_familiar_name(new_familiar)}
        sim_info = familiar_owner.sim_info
        dialog = BindObjectFamiliar.RENAME_DIALOG(sim_info, SingleSimResolver(sim_info))
        dialog.show_dialog(on_response=on_response, text_input_overrides=text_input_overrides, icon_override=familiar_icon, text_override=familiar_description)

class BindFamiliarElement(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The Sim to bind the familiar to.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'bind_familiar_action': TunableVariant(description='\n            The action that will be taken to bind the familiar.\n            ', object_familiar=BindObjectFamiliar.TunableFactory(), pet_familiar=BindPetFamiliar.TunableFactory(), default='object_familiar')}

    def _do_behavior(self):
        familiar_owner = self.interaction.get_participant(self.participant)
        familiar_tracker = familiar_owner.sim_info.familiar_tracker
        if familiar_tracker is None:
            logger.error('Trying to bind a familiar to a Sim that does not have a familiar tracker.')
            return
        self.bind_familiar_action.bind_familiar(self.interaction, familiar_owner, familiar_tracker)

class DismissFamiliarElement(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The Sim to bind the familiar to.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor)}

    def _do_behavior(self):
        familiar_owner = self.interaction.get_participant(self.participant)
        familiar_tracker = familiar_owner.sim_info.familiar_tracker
        if familiar_tracker is None:
            logger.error('Trying to dismiss the active familiar of a Sim that does not have a familiar tracker.')
            return
        familiar_tracker.dismiss_familiar()
