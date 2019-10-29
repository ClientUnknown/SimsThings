import randomfrom fishing.fishing_interactions import FishingCatchMixerInteractionMixinfrom fishing.fishing_tuning import FishingTuningfrom interactions.base.mixer_interaction import MixerInteractionfrom interactions.utils.outcome import TunableOutcomeActions, InteractionOutcomeSinglefrom objects.components.stored_object_info_tuning import StoredObjectTypefrom objects.components.types import STORED_OBJECT_INFO_COMPONENTfrom sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuningfrom sims4.tuning.tunable import TunableList, TunableReference, TunableTuple, TunableEnumEntryfrom sims4.tuning.tunable_base import GroupNamesfrom ui.ui_dialog_notification import UiDialogNotificationimport element_utilsimport servicesimport sims4.loglogger = sims4.log.Logger('Fishing', default_owner='rfleig')
class FishingTrapCatchMixerInteraction(FishingCatchMixerInteractionMixin, MixerInteraction):
    INSTANCE_TUNABLES = {'fishing_outcomes': TunableTuple(description='\n            This is how we play different content depending on fishing results.\n            ', catch_fish_outcome_actions=TunableOutcomeActions(description='\n                The outcome actions that will be used if a Sim catches a fish.\n                '), catch_junk_outcome_actions=TunableOutcomeActions(description='\n                The outcome actions that will be used if a Sim catches junk.\n                '), catch_treasure_outcome_actions=TunableOutcomeActions(description='\n                The outcome actions that will be used if a Sim catches treasure.\n                '), catch_nothing_outcome_actions=TunableOutcomeActions(description='\n                The outcome actions that will be used if a Sim catches nothing.\n                '), tuning_group=GroupNames.CORE), 'per_item_loots': TunableTuple(description='\n            These are the loots that are applied for each and every item caught.\n            ', each_fish_loot=TunableList(description='\n                A list of loots to apply for each fish caught.\n                ', tunable=TunableReference(description='\n                    A loot to apply.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), each_treasure_loot=TunableList(description='\n                A list of loots to apply for each treasure item caught.\n                ', tunable=TunableReference(description='\n                    A loot to apply.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), each_junk_loot=TunableList(description='\n                A list of loots to apply for each piece of junk in the trap.\n                ', tunable=TunableReference(description='\n                    A loot to apply.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',), pack_safe=True)), tuning_group=GroupNames.CORE), 'catch_item_notification': UiDialogNotification.TunableFactory(description='\n            The notification that is displayed when a Sim successfully catches \n            something in the trap.\n            '), 'fish_header_text': TunableLocalizedStringFactory(description='\n            The string to be used as the header for the bulleted list of fish that\n            were caught.\n            '), 'treasure_header_text': TunableLocalizedStringFactory(description='\n            The string to be used as the header for the bulleted list of treasure\n            that were caught.\n            '), 'junk_notification_text': TunableLocalizedStringFactory(description='\n            The string that describes how much junk was caught, if any was caught \n            at all.\n            \n            0 - pieces of treasure that were caught.\n            '), 'fish_information_text': TunableLocalizedStringFactory(description='\n            The text of the notification that is displayed when a Sim successfully catches a fish.\n            \n            The localization tokens for the Text field are:\n            {0.String} = Fish Type/Default Name\n            {1.String} = Localized Fish Weight, see FishObject tuning to change the localized string for fish weight\n            {2.String} = Fish Value, in usual simoleon format    \n            '), 'empty_trap_text': TunableLocalizedStringFactory(description='\n            The text that appears when the trap is empty.\n            '), 'bait_stored_info_category': TunableEnumEntry(description='\n            The Stored Object Info Type for using to retrieve the correct\n            object data from the Store Object Info Component.\n            ', tunable_type=StoredObjectType, default=StoredObjectType.INVALID)}
    REMOVE_INSTANCE_TUNABLES = ('outcome',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._buff_handle_ids = []

    def get_bait(self):
        if not self.target.has_component(STORED_OBJECT_INFO_COMPONENT):
            return
        stored_object_info_component = self.target.get_component(STORED_OBJECT_INFO_COMPONENT)
        bait_id = stored_object_info_component.get_stored_object_info_id(self.bait_stored_info_category)
        inventory_manager = services.inventory_manager()
        bait = inventory_manager.get(bait_id)
        return bait

    def build_basic_elements(self, sequence=(), **kwargs):
        sequence = super().build_basic_elements(sequence=sequence, **kwargs)
        sequence = element_utils.build_critical_section_with_finally(self._interaction_start, sequence, self._interaction_end)
        return sequence

    def _interaction_start(self, _):
        self._add_bait_buffs()

    def _interaction_end(self, _):
        self._remove_bait_buffs()

    def _add_bait_buffs(self):
        bait = self.get_bait()
        if bait:
            for (tag, bait_data) in FishingTuning.BAIT_TAG_DATA_MAP.items():
                if bait.has_tag(tag):
                    self._buff_handle_ids.append(self.sim.add_buff(bait_data.bait_buff))

    def _remove_bait_buffs(self):
        for handle_id in self._buff_handle_ids:
            self.sim.remove_buff(handle_id)
        self._buff_handle_ids = []

    def _build_outcome_sequence(self):
        (min_catch, max_catch) = self._get_min_max_catch()
        if min_catch <= 0:
            return
        actual_catch = random.randint(min_catch, max_catch)
        sim = self.sim
        junk_count = 0
        fish_caught = []
        treasure_caught = []
        weighted_outcomes = self._get_weighted_choices()
        while len(fish_caught) + len(treasure_caught) + junk_count < actual_catch:
            outcome_actions = sims4.random.weighted_random_item(weighted_outcomes)
            if outcome_actions is self.fishing_outcomes.catch_junk_outcome_actions:
                junk_count += 1
            elif outcome_actions is self.fishing_outcomes.catch_fish_outcome_actions:
                fish = self._get_individual_fish_catch()
                if fish is not None:
                    fish_caught.append(fish)
                    if outcome_actions is self.fishing_outcomes.catch_treasure_outcome_actions:
                        treasure = self._get_individual_treasure_catch()
                        if treasure is not None:
                            treasure_caught.append(treasure)
            elif outcome_actions is self.fishing_outcomes.catch_treasure_outcome_actions:
                treasure = self._get_individual_treasure_catch()
                if treasure is not None:
                    treasure_caught.append(treasure)
        if treasure_caught:
            outcome = InteractionOutcomeSingle(self.fishing_outcomes.catch_treasure_outcome_actions)
        elif fish_caught:
            outcome = InteractionOutcomeSingle(self.fishing_outcomes.catch_fish_outcome_actions)
        elif junk_count:
            outcome = InteractionOutcomeSingle(self.fishing_outcomes.catch_junk_outcome_actions)
        else:
            outcome = InteractionOutcomeSingle(self.fishing_outcomes.catch_nothing_outcome_actions)

        def end(_):
            if sim.is_selectable:
                resolver = self.get_resolver()
                fish_objects = []
                treasure_objects = []
                for treasure in treasure_caught:
                    treasure_object = self.create_object_and_add_to_inventory(sim, treasure, False)
                    if treasure_object is not None:
                        self._apply_loots(self.per_item_loots.each_treasure_loot, resolver)
                        treasure_objects.append(treasure_object)
                for fish in fish_caught:
                    fish_object = self.create_object_and_add_to_inventory(sim, fish, True)
                    if fish_object is not None:
                        self._apply_loots(self.per_item_loots.each_fish_loot, resolver)
                        FishingTuning.add_bait_notebook_entry(self.sim, fish, self.get_bait())
                        fish_objects.append(fish_object)
                for _ in range(junk_count):
                    self._apply_loots(self.per_item_loots.each_junk_loot, resolver)
                self._trap_catch_notification(fish_objects, treasure_objects, junk_count)

        return element_utils.build_critical_section_with_finally(outcome.build_elements(self, update_global_outcome_result=True), end)

    def _get_min_max_catch(self):
        target = self.target
        if target is None:
            logger.error("Trying to determine the min/max catch when there isn't a target.")
            return (0, 0)
        fishing_location_component = target.fishing_location_component
        if fishing_location_component is None:
            logger.error("Trying to run a FishingTrapCatchMixerInteraction on {}, which doesn't have a fishing_location_component.", target)
            return (0, 0)
        return fishing_location_component.get_trap_range_of_outcomes(self.get_bait())

    def _apply_loots(self, loot_list, resolver):
        for loot in loot_list:
            loot.apply_to_resolver(resolver)

    def _trap_catch_notification(self, fish_caught, treasure_caught, junk_count):
        final_string = None
        if treasure_caught:
            final_string = self._get_treasure_caught_text(treasure_caught)
        if fish_caught:
            fish_text = self._get_fish_caught_text(fish_caught)
            if final_string is None:
                final_string = fish_text
            else:
                final_string = LocalizationHelperTuning.NEW_LINE_LIST_STRUCTURE(final_string, fish_text)
        if junk_count > 0:
            junk_text = self._get_junk_caught_text(junk_count)
            if final_string is None:
                final_string = junk_text
            else:
                final_string = LocalizationHelperTuning.NEW_LINE_LIST_STRUCTURE(final_string, junk_text)
        if final_string is None:
            final_string = self.empty_trap_text()
        dialog = self.catch_item_notification(self.sim.sim_info)
        dialog.show_dialog(additional_tokens=(final_string,))

    def _get_fish_caught_text(self, fish_caught):
        all_fish_strings = []
        for fish in fish_caught:
            type_loc_string = LocalizationHelperTuning.get_object_name(fish.definition)
            value_loc_string = LocalizationHelperTuning.get_money(fish.current_value)
            weight_loc_string = fish.get_localized_weight()
            fish_data_text = self.fish_information_text(weight_loc_string, type_loc_string, value_loc_string)
            all_fish_strings.append(fish_data_text)
        final_fish_text = LocalizationHelperTuning.get_bulleted_list(self.fish_header_text(), all_fish_strings)
        return final_fish_text

    def _get_treasure_caught_text(self, treasure_caught):
        treasure_string = LocalizationHelperTuning.get_bulleted_list(self.treasure_header_text(), (LocalizationHelperTuning.get_object_name(treasure) for treasure in treasure_caught))
        return treasure_string

    def _get_junk_caught_text(self, junk_count):
        return self.junk_notification_text(junk_count)
