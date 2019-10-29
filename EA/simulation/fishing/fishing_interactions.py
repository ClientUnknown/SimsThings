import randomfrom distributor.shared_messages import IconInfoDatafrom fishing.fishing_tuning import FishingTuningfrom interactions.utils.outcome import TunableOutcomeActionsfrom sims4.tuning.tunable import TunableTuplefrom sims4.tuning.tunable_base import GroupNamesimport buffs.tunableimport build_buyimport element_utilsimport event_testing.resultsimport fishing.fish_objectimport interactions.base.immediate_interactionimport interactions.base.mixer_interactionimport interactions.base.super_interactionimport interactions.utils.outcomeimport interactions.utils.outcome_enumsimport objects.systemimport servicesimport sims4.collectionsimport sims4.localizationimport sims4.logimport sims4.tuning.tunableimport singletonsimport tagimport tunable_multiplierimport ui.ui_dialog_notificationlogger = sims4.log.Logger('Fishing', default_owner='TrevorLindsey')
class MountFishSuperInteraction(interactions.base.immediate_interaction.ImmediateSuperInteraction):

    @classmethod
    def _test(cls, target, context, **interaction_parameters):
        if not isinstance(target, fishing.fish_object.Fish):
            logger.warn('Testing the Mount Fish SI on an object that is not a Fish. This SI should not be tuned on non-Fish objects.')
            return event_testing.results.TestResult(False, 'Testing the MountFish SI on an object that is not a Fish.')
        if target.wall_mounted_object is None:
            return event_testing.results.TestResult(False, "Target Fish doesn't have a wall mounted object tuned.")
        return super()._test(target, context, **interaction_parameters)

    def _run_interaction_gen(self, timeline):
        actor_sim = self.sim
        target_fish = self.target
        mounted_definition = target_fish.wall_mounted_object
        mounted_fish = objects.system.create_object(mounted_definition)
        if mounted_fish is None:
            logger.error('Tried to create the wall mounted version of a fish, {}, and failed to create the object.', self.target)
            return
        weight_stat = fishing.fish_object.Fish.WEIGHT_STATISTIC
        fish_stat_tracker = target_fish.get_tracker(weight_stat)
        mounted_fish_stat_tracker = mounted_fish.get_tracker(weight_stat)
        mounted_fish_stat_tracker.set_value(weight_stat, fish_stat_tracker.get_user_value(weight_stat))
        if target_fish.has_custom_name():
            mounted_fish.set_custom_name(target_fish.custom_name)
        if target_fish.has_custom_description():
            mounted_fish.set_custom_description(target_fish.custom_description)
        owner_id = target_fish.get_sim_owner_id()
        if owner_id is not None:
            mounted_fish.update_ownership(services.sim_info_manager().get(owner_id))
        mounted_fish.base_value = target_fish.current_value
        mounted_fish.update_object_tooltip()
        if not actor_sim.inventory_component.player_try_add_object(mounted_fish):
            mounted_fish.destroy(source=actor_sim, cause='Failed to add mounted fish to sims inventory.')
            logger.error("Failed to add a wall mounted fish to the sim's inventory. Perhaps the object doesn't have the correct inventory component.")

class FishingLocationSuperInteraction(interactions.base.super_interaction.SuperInteraction):

    def get_fishing_data_from_target(self):
        target = self.target
        if target is None:
            logger.error('Trying to run a Fishing Interaction on a None object. {}', self)
            return
        fishing_location_component = target.fishing_location_component
        if fishing_location_component is None:
            logger.error("Trying to run a Fishing Interaction on an object that doesn't have a Fishing Location Component. {} on {}", self, target)
            return
        return fishing_location_component.fishing_data

class FishingLocationGoFishingSuperInteraction(FishingLocationSuperInteraction):
    FISHING_WITH_BAIT_INTERACTION_NAME = sims4.localization.TunableLocalizedStringFactory(description='\n        When a Sim fishes with bait, this is the interaction name. This name\n        will revert to the normal name of the interaction when they run out of\n        bait.\n        \n        Uses the same tokens as the interaction display name.\n        ')
    OUT_OF_BAIT_NOTIFICATION = ui.ui_dialog_notification.UiDialogNotification.TunableFactory(description="\n        This notification will be displayed when the player started using bait but ran out.\n        Token 0 is the actor sim. e.g. {0.SimFirstName}\n        Token 1 is the target fishing location (probably don't want to use this.\n        Token 2 is the bait object they just ran out of. e.g. {2.ObjectCatalogName} will show the type\n        ")

    def __init__(self, aop, context, *args, exit_functions=(), force_inertial=False, additional_post_run_autonomy_commodities=None, **kwargs):
        super().__init__(aop, context, *args, exit_functions=(), force_inertial=False, additional_post_run_autonomy_commodities=None, **kwargs)
        self._bait = None
        self._buff_handle_ids = []

    def build_basic_elements(self, sequence=(), **kwargs):
        sequence = super().build_basic_elements(sequence=sequence, **kwargs)
        sequence = element_utils.build_critical_section_with_finally(self._interaction_start, sequence, self._interaction_end)
        return sequence

    @property
    def bait(self):
        return self._bait

    def _interaction_start(self, _):
        self._bait = self.get_participant(interactions.ParticipantType.PickedObject)
        self._try_apply_bait_and_buffs()

    def _try_apply_bait_and_buffs(self):
        if self._bait:
            if not self.sim.inventory_component.try_move_object_to_hidden_inventory(self._bait):
                logger.error('Tried hiding the bait object, {}, but failed.', self._bait)
                self._bait = None
            else:
                self._add_bait_buffs()
                self.sim.ui_manager.set_interaction_icon_and_name(self.id, icon=None, name=self.create_localized_string(localized_string_factory=self.FISHING_WITH_BAIT_INTERACTION_NAME))

    def _interaction_end(self, _):
        if self._bait is not None:
            sim_inventory = self.sim.inventory_component
            if not sim_inventory.try_remove_object_by_id(self._bait.id):
                logger.error("Tried removing the bait object, {}, but it couldn't be found.", self._bait)
            if not sim_inventory.player_try_add_object(self._bait):
                logger.error("Tried adding the bait object, {}, back into the sim's, {}, inventory but failed.", self._bait, self.sim)
            self._remove_bait_buffs()

    def kill_and_try_reapply_bait(self):
        if self._bait is not None:
            sim_inventory = self.sim.inventory_component
            old_bait = self._bait
            self._bait = sim_inventory.get_item_with_definition(old_bait.definition, ignore_hidden=True)
            if self._bait is not None:
                self._try_apply_bait_and_buffs()
            else:
                self._remove_bait_buffs()
                self.sim.ui_manager.set_interaction_icon_and_name(self.id, icon=None, name=self.get_name())
                notification = self.OUT_OF_BAIT_NOTIFICATION(self.sim, self.get_resolver())
                notification.show_dialog(additional_tokens=(old_bait,))
            if not sim_inventory.try_remove_object_by_id(old_bait.id):
                logger.error("Tried destroying the bait object, {}, but the destroy failed. It probably wasn't found in the sim's inventory or hidden inventory.", old_bait)
            old_bait.make_transient()

    def _add_bait_buffs(self):
        if self._bait:
            for (tag, bait_data) in FishingTuning.BAIT_TAG_DATA_MAP.items():
                if self._bait.has_tag(tag):
                    self._buff_handle_ids.append(self.sim.add_buff(bait_data.bait_buff))

    def _remove_bait_buffs(self):
        for handle_id in self._buff_handle_ids:
            self.sim.remove_buff(handle_id)
        self._buff_handle_ids = []

class FishingLocationExamineWaterSuperInteraction(FishingLocationSuperInteraction):
    EXAMINE_SUCCESS_NOTIFICATION = ui.ui_dialog_notification.UiDialogNotification.TunableFactory(description="\n        The notification that is displayed when a Sim successfully examines a fishing location.\n        \n        Notice that the text itself can't be tuned here. Those will be pulled\n        from the Examine Localization Map it a fish is found that requires\n        bait, or we'll use the Generic Examine Notification Text if there are\n        no fish that require bait.\n        ", locked_args={'text': None})
    BAIT_NOTIFICATION_TEXT_MAP = sims4.tuning.tunable.TunableMapping(key_type=sims4.tuning.tunable.TunableReference(manager=services.buff_manager(), pack_safe=True), key_name='Bait Buff', value_type=sims4.localization.TunableLocalizedStringFactory(description='\n            If the Sim examines the water and a fish in the water requires the\n            tuned Bait Buff, there is a chance this is the string that will show\n            up in the TNS.\n            '), value_name='Notification Text')
    GENERIC_EXAMINE_NOTIFICATION_TEXT = sims4.localization.TunableLocalizedStringFactory(description='\n        If the Sim successfully examines the water but there are no fish that\n        require bait, this is the string that will show in the notification.\n        ')
    _notification_bait_types = singletons.EMPTY_SET

    @classmethod
    def _tuning_loaded_callback(cls):
        super()._tuning_loaded_callback()
        cls._notification_bait_types = frozenset(cls.BAIT_NOTIFICATION_TEXT_MAP)

    def _build_outcome_sequence(self):

        def end(_):
            if self.global_outcome_result == interactions.utils.outcome_enums.OutcomeResult.SUCCESS:
                self._show_success_notification()

        sequence = super()._build_outcome_sequence()
        return element_utils.build_critical_section_with_finally(sequence, end)

    def _decide_localized_string(self):
        fishing_data = self.get_fishing_data_from_target()
        if fishing_data is not None:
            required_baits = set()
            resolver = self.get_resolver()
            for fish in fishing_data.get_possible_fish_gen():
                bait = fish.fish.cls.required_bait_buff
                if bait in self._notification_bait_types and fish.fish.cls.can_catch(resolver):
                    required_baits.add(bait)
            if required_baits:
                chosen_bait = random.choice(list(required_baits))
                loc_string = self.BAIT_NOTIFICATION_TEXT_MAP.get(chosen_bait)
                return loc_string(self.sim)
        return self.GENERIC_EXAMINE_NOTIFICATION_TEXT(self.sim)

    def _show_success_notification(self):
        dialog = self.EXAMINE_SUCCESS_NOTIFICATION(self.sim, self.get_resolver(), text=lambda *_: self._decide_localized_string())
        dialog.show_dialog()

class FishingCatchMixerInteractionMixin:

    @property
    def bait(self):
        return self.super_interaction.bait

    def _get_fishing_data(self):
        return self.super_interaction.get_fishing_data_from_target()

    def _get_weighted_choices(self):
        resolver = self.get_resolver()
        fishing_data = self._get_fishing_data()
        weighted_outcomes = [(fishing_data.weight_fish.get_multiplier(resolver), self.fishing_outcomes.catch_fish_outcome_actions), (fishing_data.weight_junk.get_multiplier(resolver), self.fishing_outcomes.catch_junk_outcome_actions), (fishing_data.weight_treasure.get_multiplier(resolver), self.fishing_outcomes.catch_treasure_outcome_actions)]
        return weighted_outcomes

    def _get_individual_fish_catch(self):
        resolver = self.get_resolver()
        fishing_data = self._get_fishing_data()
        return fishing_data.choose_fish(resolver)

    def _get_individual_treasure_catch(self):
        resolver = self.get_resolver()
        fishing_data = self._get_fishing_data()
        return fishing_data.choose_treasure(resolver)

    def create_object_and_add_to_inventory(self, sim, object_to_create, is_fish):
        if object_to_create is not None and sim.is_selectable:
            created_object = objects.system.create_object(object_to_create)
            if created_object is not None:
                created_object.update_ownership(sim)
                if is_fish:
                    created_object.initialize_fish(sim)
                if sim.inventory_component.can_add(created_object):
                    sim.inventory_component.player_try_add_object(created_object)
                elif not build_buy.move_object_to_household_inventory(created_object):
                    logger.error('FishingInteractions: Failed to add object {} to household inventory.', created_object, owner='rmccord')
            return created_object

class FishingLocationCatchMixerInteraction(FishingCatchMixerInteractionMixin, interactions.base.mixer_interaction.MixerInteraction):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value, **kwargs):
        if not value:
            logger.error('Junk Objects is empty. It needs at least one junk\n            item. The tuning is located in the\n            FishingLocationCatchMixerInteraction module tuning')

    JUNK_OBJECTS = sims4.tuning.tunable.TunableList(sims4.tuning.tunable.TunableReference(description='\n            The possible junk object a Sim can catch. These will just be randomly\n            picked each time the Sim is supposed to catch junk.\n            ', manager=services.definition_manager()), verify_tunable_callback=_verify_tunable_callback)
    BASE_CATCH_CHANCE = sims4.tuning.tunable.TunablePercent(description='\n        The base chance that a Sim will actually catch something here. This\n        chance can be modified using the skill curve.\n        ', default=80)
    CATCH_CHANCE_MODIFIER_CURVE = tunable_multiplier.TunableSkillModifierCurve.TunableFactory(description='\n        This curve represents the chance to catch something.\n        ', axis_name_overrides=('Skill Level', 'Catch Chance Multiplier'), locked_args={'subject': interactions.ParticipantType.Actor})
    BUFF_CATCH_FISH_WITH_BAIT = buffs.tunable.TunableBuffReference(description='\n        The invisible buff that a sim will get any time they catch a fish while\n        using bait. This will be given along with the buff provided by Buff\n        Catch Any Fish. This is meant to help aspirations/achievements know\n        when a fish was caught with bait.\n        ')
    CATCH_FISH_NOTIFICATION = ui.ui_dialog_notification.UiDialogNotification.TunableFactory(description='\n        The notification that is displayed when a Sim successfully catches a fish.\n        ', locked_args={'text': None, 'icon': None})
    CATCH_FISH_NOTIFICATION_TEXT = sims4.localization.TunableLocalizedStringFactory(description='\n        The text of the notification that is displayed when a Sim successfully catches a fish.\n        \n        The localization tokens for the Text field are:\n        {0} = Sim - e.g. {0.SimFirstName}\n        {1} = The Fishing Location Object - e.g. {1.ObjectName}\n        {2.String} = Fish Type/Default Name\n        {3.String} = Localized Fish Weight, see FishObject tuning to change the localized string for fish weight\n        {4.String} = Fish Value, in usual simoleon format\n        ')
    CATCH_FISH_NOTIFICATION_BAIT_TEXT = sims4.localization.TunableLocalizedStringFactory(description="\n        If the Sim catches a fish because of bait, this is the text that\n        will be displayed in the 'Catch Fish Notification'.\n        {0.String} = Fish Type\n        {1.String} = Bait Type\n        ")
    CATCH_TREASURE_NOTIFICATION = ui.ui_dialog_notification.UiDialogNotification.TunableFactory(description='\n        The notification that is displayed when a Sim catches a treasure chest.\n        The icon will be the object that is caught.\n        In the text, token 2 is the object that is caught. This will allow the\n        use of {2.ObjectName}.\n        ', locked_args={'icon': None})
    TREASURE_PROP_OBJECT = sims4.tuning.tunable.TunableReference(description='\n        The object to use as the treasure chest prop.\n        ', manager=services.definition_manager())
    OUTCOME_TYPE_OTHER = 0
    OUTCOME_TYPE_FISH = 1
    OUTCOME_TYPE_TREASURE = 2
    INSTANCE_TUNABLES = {'fishing_outcomes': TunableTuple(description='\n            This is how we play different content depending on fishing results.\n            ', catch_fish_outcome_actions=TunableOutcomeActions(description='\n                The outcome actions that will be used if a Sim catches a fish.\n                '), catch_junk_outcome_actions=TunableOutcomeActions(description='\n                The outcome actions that will be used if a Sim catches junk.\n                '), catch_treasure_outcome_actions=TunableOutcomeActions(description='\n                The outcome actions that will be used if a Sim catches treasure.\n                '), catch_nothing_outcome_actions=TunableOutcomeActions(description='\n                The outcome actions that will be used if a Sim catches nothing.\n                '), tuning_group=GroupNames.CORE)}
    REMOVE_INSTANCE_TUNABLES = ('outcome',)

    def _get_random_junk(self):
        return random.choice(self.JUNK_OBJECTS)

    def _build_outcome_sequence(self):
        succeeded = self._is_successful_catch()
        object_to_create = None
        created_object = None
        sim = self.sim
        outcome_type = self.OUTCOME_TYPE_OTHER
        outcome_actions = self.fishing_outcomes.catch_nothing_outcome_actions
        prop_override = None
        if succeeded:
            weighted_outcomes = self._get_weighted_choices()
            outcome_actions = sims4.random.weighted_random_item(weighted_outcomes)
            if outcome_actions is self.fishing_outcomes.catch_junk_outcome_actions:
                prop_override = self._get_random_junk()
            else:
                if outcome_actions is self.fishing_outcomes.catch_treasure_outcome_actions:
                    object_to_create = self._get_individual_treasure_catch()
                    prop_override = self.TREASURE_PROP_OBJECT
                    outcome_type = self.OUTCOME_TYPE_TREASURE
                else:
                    object_to_create = self._get_individual_fish_catch()
                    prop_override = object_to_create
                    if object_to_create is not None:
                        outcome_type = self.OUTCOME_TYPE_FISH
                if not object_to_create:
                    outcome_actions = self.fishing_outcomes.catch_nothing_outcome_actions
            if sim.is_selectable:
                created_object = objects.system.create_object(object_to_create)
                if created_object is not None:
                    created_object.update_ownership(sim)
                    self.context.create_target_override = created_object
        bait_ids = None
        if self.bait is not None:
            bait_ids = (self.bait.id,)
        self.interaction_parameters['picked_item_ids'] = bait_ids
        is_fish = outcome_actions is self.fishing_outcomes.catch_fish_outcome_actions
        outcome = FishingLocationCatchOutcome(outcome_actions, prop_override, is_fish)

        def end(_):
            if created_object is None:
                return
            if outcome_type == self.OUTCOME_TYPE_FISH:
                created_object.initialize_fish(sim)
                self._apply_caught_fish_buff(created_object)
                self._show_catch_fish_notification(sim, created_object)
                self.super_interaction.kill_and_try_reapply_bait()
            elif outcome_type == self.OUTCOME_TYPE_TREASURE:
                self._show_catch_treasure_notification(sim, created_object)
            if sim.inventory_component.can_add(created_object):
                sim.inventory_component.player_try_add_object(created_object)
            elif not build_buy.move_object_to_household_inventory(created_object):
                logger.error('FishingInteractions: Failed to add object {} to household inventory.', created_object, owner='rmccord')

        return element_utils.build_critical_section_with_finally(outcome.build_elements(self, update_global_outcome_result=True), end)

    def _is_successful_catch(self):
        modifier = self.CATCH_CHANCE_MODIFIER_CURVE.get_multiplier(self.get_resolver(), self.sim)
        chance = self.BASE_CATCH_CHANCE*100*modifier
        return sims4.random.random_chance(chance)

    def _show_catch_fish_notification(self, sim, fish):
        notification = self.CATCH_FISH_NOTIFICATION(sim, self.get_resolver(), text=lambda *_: self._get_catch_notification_text(fish))
        notification.show_dialog(icon_override=IconInfoData(obj_instance=fish))

    def _get_catch_notification_text(self, fish):
        type_loc_string = sims4.localization.LocalizationHelperTuning.get_object_name(fish.definition)
        value_loc_string = sims4.localization.LocalizationHelperTuning.get_money(fish.current_value)
        weight_loc_string = fish.get_localized_weight()
        text = self.CATCH_FISH_NOTIFICATION_TEXT(*self.get_localization_tokens() + (type_loc_string, weight_loc_string, value_loc_string))
        if self.sim.has_buff(fish.required_bait_buff):
            if self.bait is not None:
                bait_loc_string = sims4.localization.LocalizationHelperTuning.get_object_name(self.bait.definition)
                text = sims4.localization.LocalizationHelperTuning.get_new_line_separated_strings(text, self.CATCH_FISH_NOTIFICATION_BAIT_TEXT(type_loc_string, bait_loc_string))
            else:
                logger.error('Fish ({}) required buff exist, but bait could be found.', fish)
        return text

    def _apply_caught_fish_buff(self, fish):
        for buff_ref in fish.get_catch_buffs_gen():
            self.sim.add_buff_from_op(buff_type=buff_ref.buff_type, buff_reason=buff_ref.buff_reason)
        if self.bait is not None:
            self.sim.add_buff_from_op(buff_type=self.BUFF_CATCH_FISH_WITH_BAIT.buff_type, buff_reason=self.BUFF_CATCH_FISH_WITH_BAIT.buff_reason)

    def _show_catch_treasure_notification(self, sim, treasure):
        notification = self.CATCH_TREASURE_NOTIFICATION(sim, self.get_resolver())
        notification.show_dialog(icon_override=IconInfoData(obj_instance=treasure), additional_tokens=(treasure,))

class FishingLocationCatchOutcome(interactions.utils.outcome.InteractionOutcomeSingle):
    PROP_NAME = 'collectFish'
    FISH_TYPE_NAME = 'fishType'

    def __init__(self, actions, prop_override, is_fish):
        super().__init__(actions)
        self._prop_override = prop_override
        self._is_fish = is_fish

    def _build_elements(self, interaction):
        sim = interaction.sim

        def setup_asm_override(asm):
            result = sim.posture.setup_asm_interaction(asm, sim, None, 'x', None)
            if not result:
                return result
            prop_override = sims4.collections.FrozenAttributeDict({'states_to_override': (), 'from_actor': None, 'definition': self._prop_override, 'sharing': None, 'set_as_actor': None})
            if self._prop_override:
                asm.set_prop_override(self.PROP_NAME, prop_override)
            if self._is_fish:
                asm.set_parameter(self.FISH_TYPE_NAME, self._prop_override.cls.fish_type)
            return True

        return interactions.utils.outcome.build_outcome_actions(interaction, self._actions, setup_asm_override=setup_asm_override)
