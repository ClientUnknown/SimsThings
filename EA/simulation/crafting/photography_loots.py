from event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom interactions import ParticipantTypefrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableReference, OptionalTunable, TunableTuple, TunableEnumEntryfrom ui.ui_dialog_notification import UiDialogNotificationimport servicesimport sims4logger = sims4.log.Logger('Photography', default_owner='rrodgers')
class DefaultTakePhotoLoot(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'photographer_loot': TunableReference(description='\n            Loot to apply to the Photographer.          \n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)}

    def __init__(self, photographer, interaction, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def apply_loot(self, sim):
        photographer_info = services.sim_info_manager().get(sim.id)
        photographer_resolver = SingleSimResolver(photographer_info)
        if photographer_resolver is not None:
            self.photographer_loot.apply_to_resolver(photographer_resolver)

class RotateTargetPhotoLoot(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'photographer_loot': TunableReference(description='\n            Loot to apply to the Photographer.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True), 'target_loot': TunableReference(description='\n            Loot to give to the Rotate Selfie Target.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True), 'notification': OptionalTunable(description='\n            If enabled, this notification will show after the photo is\n            taken.\n            ', tunable=UiDialogNotification.TunableFactory()), 'statistic_info': OptionalTunable(description="\n            Statistic to be passed in as an additional token available. The\n            token will be the difference between the tuned statistics value\n            before the interaction and after the loot is applied.\n            \n            Use Case: Simstagram Pet interaction gives to the pet's simstagram\n            account, and the player sees a notification with the amount of followers\n            gained.\n            \n            IMPORTANT: The tuned statistic is expected to have a default value of\n            0. If not, the resulting difference token will not be accurate. \n            ", tunable=TunableTuple(description=' \n                Specify the value of a specific statistic from the selected participant.\n                ', participant=TunableEnumEntry(description="\n                    The participant from whom we will fetch the specified\n                    statistic's value.\n                    ", tunable_type=ParticipantType, default=ParticipantType.Actor), statistic=TunableReference(description="\n                    The statistic's whose value we want to fetch.\n                    ", manager=services.statistic_manager())))}

    def __init__(self, photographer, interaction, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.photographer = photographer
        self.stored_statistic_value = 0
        if self.statistic_info is None:
            return
        participant = self.statistic_info.participant
        sim = interaction.get_participant(participant)
        if participant is not None:
            tracker = sim.get_tracker(self.statistic_info.statistic)
            if tracker is not None:
                self.stored_statistic_value = tracker.get_value(self.statistic_info.statistic)

    def apply_loot(self, sim):
        target_info = services.sim_info_manager().get(sim.id)
        target_resolver = SingleSimResolver(target_info)
        self.target_loot.apply_to_resolver(target_resolver)
        photographer_info = services.sim_info_manager().get(self.photographer.id)
        photographer_resolver = SingleSimResolver(photographer_info)
        self.photographer_loot.apply_to_resolver(photographer_resolver)
        tracker = target_info.get_tracker(self.statistic_info.statistic)
        current_statvalue = tracker.get_value(self.statistic_info.statistic)
        change_amount = abs(current_statvalue - self.stored_statistic_value)
        if self.photographer is None:
            logger.error('Got a None Sim {} while applying loot to the photographer.', self.photographer, owner='shipark')
        if self.notification is None:
            return
        notification = self.notification(self.photographer, resolver=DoubleSimResolver(photographer_info, target_info), target_sim_id=sim.id)
        if change_amount > 0:
            notification.show_dialog(additional_tokens=(change_amount,))
        else:
            notification.show_dialog()
