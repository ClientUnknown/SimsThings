from types import SimpleNamespace
class ImmediateSuperInteraction(SuperInteraction):
    INSTANCE_TUNABLES = {'basic_content': TunableBasicContentSet(no_content=True, default='no_content'), 'basic_extras': TunableList(description='Additional elements to run around the basic content of the interaction.', tunable=TunableVariant(add_to_household=AddToHouseholdElement.TunableFactory(), business_buy_lot=BusinessBuyLot.TunableFactory(), business_employee_action=BusinessEmployeeAction.TunableFactory(), camera_focus=CameraFocusElement.TunableFactory(), create_object=ObjectCreationElement.TunableFactory(), create_photo_memory=CreatePhotoMemory.TunableFactory(), create_sim=SimCreationElement.TunableFactory(), create_situation=CreateSituationElement.TunableFactory(), destroy_object=ObjectDestructionElement.TunableFactory(), display_notebook_ui=NotebookDisplayElement.TunableFactory(), do_command=DoCommand.TunableFactory(), join_situation=JoinSituationElement.TunableFactory(), notification=NotificationElement.TunableFactory(), payment=PaymentElement.TunableFactory(), pregnancy=PregnancyElement.TunableFactory(), push_leave_lot_interaction=PushNpcLeaveLotNowInteraction.TunableFactory(), remove_from_travel_group=TravelGroupRemove.TunableFactory(), save_participant=SaveParticipantElement.TunableFactory(), state_change=TunableStateChange(), vfx=PlayVisualEffectElement.TunableFactory(), walls_up_override=SetWallsUpOverrideElement.TunableFactory()))}

    @classproperty
    def immediate(cls):
        return True
