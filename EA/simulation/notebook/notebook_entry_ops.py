from interactions import ParticipantTypeObjectfrom interactions.utils.loot_basic_op import BaseLootOperationfrom notebook.notebook_entry import SubEntryDatafrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableReference, TunableEnumEntry, TunablePackSafeReference, TunableVariant, OptionalTunable, TunableList, TunableTuplefrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport servicesimport sims4.loglogger = sims4.log.Logger('Notebook')
class NotebookEntryLootOp(BaseLootOperation):

    class _NotebookEntryFromParticipant(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'reference_notebook_entry': TunableReference(description='\n                Reference to a notebook entry where we will get the core notebook\n                data (category, subcategory) but we will use the the object \n                reference to populate the rest of the data. \n                ', manager=services.get_instance_manager(sims4.resources.Types.NOTEBOOK_ENTRY), pack_safe=True), 'entry_participant': TunableEnumEntry(description='\n                Participant on which we will get the noteboook entry information \n                from.\n                ', tunable_type=ParticipantTypeObject, default=ParticipantTypeObject.Object), 'entry_sublist_participant': TunableList(description='\n                List of participants on which we will get the notebook entry \n                sublist information from.\n                ', tunable=TunableEnumEntry(tunable_type=ParticipantTypeObject, default=ParticipantTypeObject.PickedObject), unique_entries=True)}

        def get_entries(self, resolver):
            entry_target = resolver.get_participant(self.entry_participant)
            if entry_target is None:
                logger.error('Notebook entry {} for entry participant {} is None, participant type is probably invalid for this loot.', self, self.entry_participant)
                return
            sub_entries = None
            for sub_entry_participant in self.entry_sublist_participant:
                sub_entry = resolver.get_participant(sub_entry_participant)
                if sub_entry is None:
                    pass
                else:
                    if sub_entries is None:
                        sub_entries = []
                    sub_entries.append(sub_entry)
            return entry_target.get_notebook_information(self.reference_notebook_entry, sub_entries)

    class _NotebookEntryFromReference(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'notebook_entry': TunableReference(description='\n                Create a new entry filling up all the fields for an entry.\n                ', manager=services.get_instance_manager(sims4.resources.Types.NOTEBOOK_ENTRY), pack_safe=True)}

        def get_entries(self, resolver):
            return (self.notebook_entry(),)

    class _NotebookEntryFromRecipe(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'reference_notebook_entry': TunablePackSafeReference(description='\n                Reference to a notebook entry where we will get the core notebook\n                data (category, subcategory).   \n                ', manager=services.get_instance_manager(sims4.resources.Types.NOTEBOOK_ENTRY)), 'recipe': TunablePackSafeReference(description='\n                The recipe to use to create the notebook entry.  This recipe\n                should have the use_ingredients tunable set so the notebook\n                system has data to populate the entry.\n                ', manager=services.recipe_manager())}

        def get_entries(self, resolver):
            if self.recipe is None or self.reference_notebook_entry is None:
                return
            sub_entries = (SubEntryData(self.recipe.guid64, False),)
            return (self.reference_notebook_entry(None, sub_entries=sub_entries),)

    FACTORY_TUNABLES = {'notebook_entry': TunableVariant(description='\n            Type of unlock for notebook entries.\n            ', create_new_entry=_NotebookEntryFromReference.TunableFactory(), create_entry_from_participant=_NotebookEntryFromParticipant.TunableFactory(), create_entry_from_recipe=_NotebookEntryFromRecipe.TunableFactory()), 'notifications': TunableTuple(description='\n            Notifications to show when adding notebook entry.\n            ', unlocked_success_notification=OptionalTunable(description='\n                If enabled, a notification will be shown when a new\n                notebook entry is successfully unlocked.\n                ', tunable=TunableUiDialogNotificationSnippet()), unlocked_failed_notification=OptionalTunable(description='\n                If enabled, a notification will be shown when failing to \n                unlock a new notebook entry because the notebook already has \n                identical entry.\n                ', tunable=TunableUiDialogNotificationSnippet()))}

    def __init__(self, *args, notebook_entry, notifications, **kwargs):
        super().__init__(*args, **kwargs)
        self.notebook_entry = notebook_entry
        self.notifications = notifications

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if not subject.is_sim:
            return False
        if subject.notebook_tracker is None:
            logger.warn('Trying to unlock a notebook entry on {}, but the notebook tracker is None. LOD issue?', subject)
            return False
        unlocked_entries = self.notebook_entry.get_entries(resolver)
        if not unlocked_entries:
            return False
        for unlocked_entry in unlocked_entries:
            subject.notebook_tracker.unlock_entry(unlocked_entry, notifications=self.notifications, resolver=resolver)
