from collections import defaultdictfrom weakref import WeakKeyDictionaryimport randomfrom protocolbuffers import Consts_pb2, SimObjectAttributes_pb2 as protocolsfrom alarms import add_alarm, cancel_alarmfrom date_and_time import create_time_span, DateAndTime, DATE_AND_TIME_ZEROfrom distributor.rollback import ProtocolBufferRollbackfrom element_utils import build_critical_section_with_finallyfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestVariant, TunableTestSetfrom interactions.item_consume import ItemCostfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom interactions.utils.loot import LootActionsfrom interactions.utils.tunable import TunableContinuationfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims4.localization import TunableLocalizedStringFactoryVariant, TunableLocalizedStringFactoryfrom sims4.random import weighted_random_itemfrom sims4.tuning.dynamic_enum import DynamicEnumLockedfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, TunableMapping, TunableTuple, TunableList, TunableEnumEntry, Tunable, TunableVariant, TunableRange, TunableInterval, OptionalTunablefrom sims4.utils import classpropertyfrom snippets import define_snippetfrom tunable_multiplier import TunableMultiplierfrom ui.ui_dialog import UiDialog, UiDialogResponsefrom ui.ui_dialog_labeled_icons import UiDialogLabeledIconsfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport clockimport servicesimport sims4.reloadlogger = sims4.log.Logger('Adventure')with sims4.reload.protected(globals()):
    _initial_adventure_moment_key_overrides = WeakKeyDictionary()
def set_initial_adventure_moment_key_override(sim, initial_adventure_moment_key):
    _initial_adventure_moment_key_overrides[sim] = initial_adventure_moment_key

class AdventureTracker(SimInfoTracker):

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._adventure_mappings = dict()
        self._adventure_cooldowns = defaultdict(dict)

    def set_adventure_moment(self, interaction, adventure_moment_id):
        self._adventure_mappings[interaction.guid64] = adventure_moment_id

    def remove_adventure_moment(self, interaction):
        if interaction.guid64 in self._adventure_mappings:
            del self._adventure_mappings[interaction.guid64]

    def set_adventure_moment_cooldown(self, interaction, adventure_moment_id, cooldown):
        moment_dict = self._adventure_cooldowns[interaction.guid64]
        if cooldown == DATE_AND_TIME_ZERO:
            moment_dict[adventure_moment_id] = DATE_AND_TIME_ZERO
        else:
            moment_dict[adventure_moment_id] = services.time_service().sim_now + create_time_span(hours=cooldown)

    def remove_adventure_moment_cooldown(self, interaction, adventure_moment_id):
        if interaction.guid64 in self._adventure_cooldowns:
            moment_dict = self._adventure_cooldowns[interaction.guid64]
            del moment_dict[adventure_moment_id]
            if not moment_dict:
                del self._adventure_cooldowns[interaction.guid64]

    def is_adventure_moment_available(self, interaction, adventure_moment_id, new_cooldown):
        if interaction.guid64 in self._adventure_cooldowns:
            moment_dict = self._adventure_cooldowns[interaction.guid64]
            if adventure_moment_id in moment_dict:
                cooldown = moment_dict[adventure_moment_id]
                if new_cooldown == DATE_AND_TIME_ZERO:
                    if cooldown != DATE_AND_TIME_ZERO:
                        moment_dict[adventure_moment_id] = DATE_AND_TIME_ZERO
                    return False
                if services.time_service().sim_now < cooldown:
                    return False
                self.remove_adventure_moment_cooldown(interaction, adventure_moment_id)
        return True

    def get_adventure_moment(self, interaction):
        return self._adventure_mappings.get(interaction.guid64)

    def _clear_adventure_tracker(self):
        self._adventure_mappings = dict()
        self._adventure_cooldowns = defaultdict(dict)

    def save(self):
        data = protocols.PersistableAdventureTracker()
        for (adventure_id, adventure_moment_id) in self._adventure_mappings.items():
            with ProtocolBufferRollback(data.adventures) as adventure_pair:
                adventure_pair.adventure_id = adventure_id
                adventure_pair.adventure_moment_id = adventure_moment_id
        for (adventure_id, adventure_moment_dict) in self._adventure_cooldowns.items():
            for (adventure_moment_id, cooldown) in adventure_moment_dict.items():
                with ProtocolBufferRollback(data.adventure_cooldowns) as adventure_cooldown_data:
                    adventure_cooldown_data.adventure_id = adventure_id
                    adventure_cooldown_data.adventure_moment_id = adventure_moment_id
                    adventure_cooldown_data.adventure_cooldown = cooldown
        return data

    def load(self, data):
        for adventure_pair in data.adventures:
            self._adventure_mappings[adventure_pair.adventure_id] = adventure_pair.adventure_moment_id
        for adventure_cooldown_data in data.adventure_cooldowns:
            moment_dict = self._adventure_cooldowns[adventure_cooldown_data.adventure_id]
            moment_dict[adventure_cooldown_data.adventure_moment_id] = DateAndTime(adventure_cooldown_data.adventure_cooldown)

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.FULL

    def on_lod_update(self, old_lod, new_lod):
        if new_lod < self._tracker_lod_threshold:
            self._clear_adventure_tracker()
        elif old_lod < self._tracker_lod_threshold:
            sim_msg = services.get_persistence_service().get_sim_proto_buff(self._sim_info.id)
            if sim_msg is not None:
                self.load(sim_msg.attributes.adventure_tracker)

class AdventureMomentKey(DynamicEnumLocked):
    INVALID = 0

class AdventureMoment(HasTunableFactory, AutoFactoryInit):
    LOOT_NOTIFICATION_TEXT = TunableLocalizedStringFactory(description='\n        A string used to recursively build loot notification text. It will be\n        given two tokens: a loot display text string, if any, and the previously\n        built LOOT_NOTIFICATION_TEXT string.\n        ')
    NOTIFICATION_TEXT = TunableLocalizedStringFactory(description='\n        A string used to format notifications. It will be given two arguments:\n        the notification text and the built version of LOOT_NOTIFICATION_TEXT,\n        if not empty.\n        ')
    CHEAT_TEXT = TunableTuple(description='\n        Strings to be used for display text on cheat buttons to trigger all\n        adventure moments. \n        ', previous_display_text=TunableLocalizedStringFactory(description='\n            Text that will be displayed on previous cheat button.\n            '), next_display_text=TunableLocalizedStringFactory(description='\n            Text that will be displayed on next cheat button.\n            '), text_pattern=TunableLocalizedStringFactory(description='\n            Format for displaying next and previous buttons text including the\n            progress.\n            '), tooltip=TunableLocalizedStringFactory(description='\n            Tooltip to show when disabling previous or next button.\n            '))
    COST_TYPE_SIMOLEONS = 0
    COST_TYPE_ITEMS = 1
    CHEAT_PREVIOUS_INDEX = 1
    CHEAT_NEXT_INDEX = 2
    FACTORY_TUNABLES = {'description': '\n            A phase of an adventure. Adventure moments may present\n            some information in a dialog form and for a choice to be\n            made regarding how the overall adventure will branch.\n            ', '_visibility': OptionalTunable(description='\n            Control whether or not this moment provides visual feedback to\n            the player (i.e., a modal dialog).\n            ', tunable=UiDialog.TunableFactory(), disabled_name='not_visible', enabled_name='show_dialog'), '_finish_actions': TunableList(description='\n            A list of choices that can be made by the player to determine\n            branching for the adventure. They will be displayed as buttons\n            in the UI. If no dialog is displayed, then the first available\n            finish action will be selected. If this list is empty, the\n            adventure ends.\n            ', tunable=TunableTuple(availability_tests=TunableTestSet(description='\n                    A set of tests that must pass in order for this Finish\n                    Action to be available on the dialog. A Finish Action failing\n                    all tests is handled as if it were never tuned.\n                    '), display_text=TunableLocalizedStringFactoryVariant(description="\n                   This finish action's title. This will be the button text in\n                   the UI.\n                   ", allow_none=True), display_subtext=TunableLocalizedStringFactoryVariant(description='\n                    If tuned, this text will display below the button for this Finish Action.\n                    \n                    Span tags can be used to change the color of the text to green/positive and red/negative.\n                    <span class="positive">TEXT</span> will make the word TEXT green\n                    <span class="negative">TEXT</span> will make the word TEXT red\n                    ', allow_none=True), disabled_text=OptionalTunable(description="\n                    If enabled, this is the string that will be displayed if \n                    this finishing action is not available because the tests \n                    don't pass.\n                    ", tunable=TunableLocalizedStringFactory()), cost=TunableVariant(description='\n                    The cost associated with this finish action. Only one type\n                    of cost may be tuned. The player is informed of the cost\n                    before making the selection by modifying the display_text\n                    string to include this information.\n                    ', simoleon_cost=TunableTuple(description="The specified\n                        amount will be deducted from the Sim's funds.\n                        ", locked_args={'cost_type': COST_TYPE_SIMOLEONS}, amount=TunableRange(description='How many Simoleons to\n                            deduct.\n                            ', tunable_type=int, default=0, minimum=0)), item_cost=TunableTuple(description="The specified items will \n                        be removed from the Sim's inventory.\n                        ", locked_args={'cost_type': COST_TYPE_ITEMS}, item_cost=ItemCost.TunableFactory()), default=None), action_results=TunableList(description='\n                    A list of possible results that can occur if this finish\n                    action is selected. Action results can award loot, display\n                    notifications, and control the branching of the adventure by\n                    selecting the next adventure moment to run.\n                    ', tunable=TunableTuple(weight_modifiers=TunableList(description='\n                            A list of modifiers that affect the probability that\n                            this action result will be chosen. These are exposed\n                            in the form (test, multiplier). If the test passes,\n                            then the multiplier is applied to the running total.\n                            The default multiplier is 1. To increase the\n                            likelihood of this action result being chosen, tune\n                            multiplier greater than 1. To decrease the\n                            likelihood of this action result being chose, tune\n                            multipliers lower than 1. If you want to exclude\n                            this action result from consideration, tune a\n                            multiplier of 0.\n                            ', tunable=TunableTuple(description='\n                                A pair of test and weight multiplier. If the\n                                test passes, the associated weight multiplier is\n                                applied. If no test is specified, the multiplier\n                                is always applied.\n                                ', test=TunableTestVariant(description='\n                                    The test that has to pass for this weight\n                                    multiplier to be applied. The information\n                                    available to this test is the same\n                                    information available to the interaction\n                                    owning this adventure.\n                                    ', test_locked_args={'tooltip': None}), weight_multiplier=Tunable(description='\n                                    The weight multiplier to apply if the\n                                    associated test passes.\n                                    ', tunable_type=float, default=1))), notification=OptionalTunable(description='\n                            If set, this notification will be displayed.\n                            ', tunable=TunableUiDialogNotificationSnippet()), next_moments=TunableList(description='\n                            A list of adventure moment keys. One of these keys will\n                            be selected to determine which adventure moment is\n                            selected next. If the list is empty, the adventure ends\n                            here. Any of the keys tuned here will have to be tuned\n                            in the _adventure_moments tunable for the owning adventure.\n                            ', tunable=AdventureMomentKey), loot_actions=TunableList(description='\n                            List of Loot actions that are awarded if this action result is selected.\n                            ', tunable=LootActions.TunableReference()), continuation=TunableContinuation(description='\n                            A continuation to push when running finish actions.\n                            '), results_dialog=OptionalTunable(description='\n                            A results dialog to show. This dialog allows a list\n                            of icons with labels.\n                            ', tunable=UiDialogLabeledIcons.TunableFactory()), events_to_send=TunableList(description='\n                            A list of events to send.\n                            ', tunable=TunableEnumEntry(description='\n                                events types to send\n                                ', tunable_type=TestEvent, default=TestEvent.Invalid))))))}

    def __init__(self, parent_adventure, **kwargs):
        super().__init__(**kwargs)
        self._parent_adventure = parent_adventure
        self.resolver = self._interaction.get_resolver()

    @property
    def _interaction(self):
        return self._parent_adventure.interaction

    @property
    def _sim(self):
        return self._interaction.sim

    def run_adventure(self):
        if self._visibility is None:
            if self._finish_actions:
                self._run_first_valid_finish_action()
        else:
            dialog = self._get_dialog()
            if dialog is not None:
                self._parent_adventure.force_action_result = True
                dialog.show_dialog(auto_response=0)

    def _run_first_valid_finish_action(self):
        resolver = self.resolver
        for (action_id, finish_action) in enumerate(self._finish_actions):
            if finish_action.availability_tests.run_tests(resolver):
                return self._run_action_from_index(action_id)

    def _is_action_result_available(self, action_result):
        if not action_result.next_moments:
            return True
        for moment_key in action_result.next_moments:
            if self._parent_adventure.is_adventure_moment_available(moment_key):
                return True
        return False

    def _run_action_from_cheat(self, action_index):
        cheat_index = action_index - len(self._finish_actions) + 1
        if cheat_index == self.CHEAT_PREVIOUS_INDEX:
            self._parent_adventure.run_cheat_previous_moment()
        elif cheat_index == self.CHEAT_NEXT_INDEX:
            self._parent_adventure.run_cheat_next_moment()

    def _get_action_result_weight(self, action_result):
        interaction_resolver = self.resolver
        weight = 1
        for modifier in action_result.weight_modifiers:
            if not modifier.test is None:
                if interaction_resolver(modifier.test):
                    weight *= modifier.weight_multiplier
            weight *= modifier.weight_multiplier
        return weight

    def _apply_action_cost(self, action):
        if action.cost.cost_type == self.COST_TYPE_SIMOLEONS:
            if not self._sim.family_funds.try_remove(action.cost.amount, Consts_pb2.TELEMETRY_INTERACTION_COST, sim=self._sim):
                return False
        elif action.cost.cost_type == self.COST_TYPE_ITEMS:
            item_cost = action.cost.item_cost
            return item_cost.consume_interaction_cost(self._interaction)()
        return True

    def _run_action_from_index(self, action_index):
        try:
            finish_action = self._finish_actions[action_index]
        except IndexError as err:
            logger.exception('Exception {} while attempting to get finish action.\nFinishActions length: {}, ActionIndex: {},\nCurrent Moment: {},\nResolver: {}.\n', err, len(self._finish_actions), action_index, self._parent_adventure._current_moment_key, self.resolver)
            return
        forced_action_result = False
        weight_pairs = [(self._get_action_result_weight(action_result), action_result) for action_result in finish_action.action_results if self._is_action_result_available(action_result)]
        if self._parent_adventure.force_action_result:
            forced_action_result = True
            weight_pairs = [(self._get_action_result_weight(action_result), action_result) for action_result in finish_action.action_results]
        action_result = weighted_random_item(weight_pairs)
        if weight_pairs or action_result is not None or finish_action.action_results or not self._apply_action_cost(finish_action):
            return
        if action_result is not None:
            loot_display_text = None
            resolver = self.resolver
            for actions in action_result.loot_actions:
                for (loot_op, test_ran) in actions.get_loot_ops_gen(resolver):
                    (success, _) = loot_op.apply_to_resolver(resolver, skip_test=test_ran)
                    if success and action_result.notification is not None:
                        current_loot_display_text = loot_op.get_display_text()
                        if current_loot_display_text is not None:
                            if loot_display_text is None:
                                loot_display_text = current_loot_display_text
                            else:
                                loot_display_text = self.LOOT_NOTIFICATION_TEXT(loot_display_text, current_loot_display_text)
            if action_result.notification is not None:
                if loot_display_text is not None:
                    notification_text = lambda *tokens: self.NOTIFICATION_TEXT(action_result.notification.text(*tokens), loot_display_text)
                else:
                    notification_text = action_result.notification.text
                dialog = action_result.notification(self._sim, self.resolver)
                dialog.text = notification_text
                dialog.show_dialog()
            if action_result.next_moments:
                if forced_action_result:
                    next_moment_key = random.choice(action_result.next_moments)
                else:
                    next_moment_key = random.choice(tuple(moment_key for moment_key in action_result.next_moments if self._parent_adventure.is_adventure_moment_available(moment_key)))
                self._parent_adventure.queue_adventure_moment(next_moment_key)
            if action_result.results_dialog:
                dialog = action_result.results_dialog(self._sim, resolver=self.resolver)
                dialog.show_dialog()
            event_manager = services.get_event_manager()
            for event_type in action_result.events_to_send:
                event_manager.process_event(event_type, sim_info=self._sim.sim_info)
            if action_result.continuation:
                self._interaction.push_tunable_continuation(action_result.continuation)

    def _is_cheat_response(self, response):
        cheat_response = response - len(self._finish_actions)
        if cheat_response < 0:
            return False
        return True

    def _on_dialog_response(self, dialog):
        response_index = dialog.response
        if response_index is None:
            return
        if False and self._is_cheat_response(response_index):
            self._run_action_from_cheat(response_index)
            return
        if response_index >= len(self._finish_actions):
            return
        self._run_action_from_index(response_index)

    def _get_action_display_text(self, action):
        display_name = self._interaction.create_localized_string(action.display_text)
        if action.cost is not None:
            if action.cost.cost_type == self.COST_TYPE_SIMOLEONS:
                amount = action.cost.amount
                display_name = self._interaction.SIMOLEON_COST_NAME_FACTORY(display_name, amount)
            elif action.cost.cost_type == self.COST_TYPE_ITEMS:
                item_cost = action.cost.item_cost
                display_name = item_cost.get_interaction_name(self._interaction, display_name)
        return lambda *_, **__: display_name

    def _get_dialog(self):
        resolver = self.resolver
        dialog = self._visibility(self._sim, resolver)
        responses = []
        for (action_id, finish_action) in enumerate(self._finish_actions):
            result = finish_action.availability_tests.run_tests(resolver)
            if not result:
                if finish_action.disabled_text is not None:
                    disabled_text = finish_action.disabled_text if not result else None
                    responses.append(UiDialogResponse(dialog_response_id=action_id, text=self._get_action_display_text(finish_action), subtext=self._interaction.create_localized_string(finish_action.display_subtext), disabled_text=disabled_text() if disabled_text is not None else None))
            disabled_text = finish_action.disabled_text if not result else None
            responses.append(UiDialogResponse(dialog_response_id=action_id, text=self._get_action_display_text(finish_action), subtext=self._interaction.create_localized_string(finish_action.display_subtext), disabled_text=disabled_text() if disabled_text is not None else None))
        if not responses:
            return
        if False and _show_all_adventure_moments:
            responses.extend(self._parent_adventure.get_cheat_responses(action_id))
        dialog.set_responses(responses)
        dialog.add_listener(self._on_dialog_response)
        return dialog
(TunableAdventureMomentReference, TunableAdventureMomentSnippet) = define_snippet('Adventure_Moment', AdventureMoment.TunableFactory())
class Adventure(XevtTriggeredElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'description': '\n            A series of individual moments linked together in a game-like\n            fashion.\n            ', '_adventure_moments': TunableMapping(description='\n            The individual adventure moments for this adventure. Every moment\n            used in the adventure must be defined here. For instance, if there\n            is an adventure moment that triggers another adventure moment, the\n            latter must also be defined in this list.\n            ', key_type=AdventureMomentKey, value_type=TunableTuple(aventure_moment=TunableAdventureMomentSnippet(pack_safe=True), sim_specific_cooldown=TunableVariant(description='\n                    The type of sim specific cooldown,\n                    \n                    Hours means cooldown for specified number of sim hours\n                    No cooldown means no cooldown\n                    One shot means a sim will only see it once.\n                    \n                    (Note:  If we hit a visible (or resumed) adventure, after\n                    that point if all actions are on cooldown, the cooldowns will be\n                    ignored.)\n                    ', hours=TunableRange(description='\n                        A cooldown that last for the specified number of hours\n                        ', tunable_type=float, default=50, minimum=1), locked_args={'one_shot': DATE_AND_TIME_ZERO, 'no_cooldown': None}, default='no_cooldown'))), '_initial_moments': TunableList(description='\n            A list of adventure moments that are valid as initiating moments for\n            this adventure.\n            ', tunable=TunableTuple(description='\n                A tuple of moment key and weight. The higher the weight, the\n                more likely it is this moment will be selected as the initial\n                moment.\n                ', adventure_moment_key=TunableEnumEntry(description='\n                    The key of the initial adventure moment.\n                    ', tunable_type=AdventureMomentKey, default=AdventureMomentKey.INVALID), weight=TunableMultiplier.TunableFactory(description='\n                    The weight of this potential initial moment relative\n                    to other items within this list.\n                    '))), '_trigger_interval': TunableInterval(description='\n            The interval, in Sim minutes, between the end of one adventure\n            moment and the beginning of the next one.\n            ', tunable_type=float, default_lower=8, default_upper=12, minimum=0), '_maximum_triggers': Tunable(description='\n            The maximum number of adventure moments that can be triggered by\n            this adventure. Any moment being generated from the adventure beyond\n            this limit will be discarded. Set to 0 to allow for an unlimited\n            number of adventure moments to be triggered.\n            ', tunable_type=int, default=0), '_resumable': Tunable(description='\n            A Sim who enters a resumable adventure will restart the same\n            adventure at the moment they left it at.\n            ', tunable_type=bool, default=True)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._adventure_moment_count = 0
        self._alarm_handle = None
        self._current_moment_key = None
        self._canceled = False
        self.force_action_result = False

    def _build_outer_elements(self, sequence):
        return build_critical_section_with_finally(sequence, self._end_adventure)

    def _end_adventure(self, *_, **__):
        if self._alarm_handle is not None:
            cancel_alarm(self._alarm_handle)
            self._alarm_handle = None

    def _soft_stop(self):
        self._canceled = True
        return super()._soft_stop()

    @property
    def tracker(self):
        return self.interaction.sim.sim_info.adventure_tracker

    def _get_cheat_display_text(self, display_text, progress, total_progress):
        display_name = self.interaction.create_localized_string(display_text)
        display_name = AdventureMoment.CHEAT_TEXT.text_pattern(display_name, progress, total_progress)
        return lambda *_, **__: display_name

    def get_cheat_responses(self, last_action_id):
        responses = []
        total_moments = len(self._adventure_moment_keys)
        disabled_text = AdventureMoment.CHEAT_TEXT.tooltip
        curr_index = self._adventure_moment_keys.index(self._current_moment_key)
        responses.append(UiDialogResponse(dialog_response_id=last_action_id + AdventureMoment.CHEAT_PREVIOUS_INDEX, text=self._get_cheat_display_text(AdventureMoment.CHEAT_TEXT.previous_display_text, curr_index, total_moments), disabled_text=disabled_text() if curr_index <= 0 else None))
        responses.append(UiDialogResponse(dialog_response_id=last_action_id + AdventureMoment.CHEAT_NEXT_INDEX, text=self._get_cheat_display_text(AdventureMoment.CHEAT_TEXT.next_display_text, curr_index + 2, total_moments), disabled_text=disabled_text() if curr_index >= total_moments - 1 else None))
        return responses

    def run_cheat_previous_moment(self):
        pass

    def run_cheat_next_moment(self):
        pass

    def queue_adventure_moment(self, adventure_moment_key):
        if self._maximum_triggers and self._adventure_moment_count >= self._maximum_triggers:
            return
        time_span = clock.interval_in_sim_minutes(self._trigger_interval.random_float())

        def callback(alarm_handle):
            self._alarm_handle = None
            if not self._canceled:
                self.tracker.remove_adventure_moment(self.interaction)
                self._run_adventure_moment(adventure_moment_key)

        self.tracker.set_adventure_moment(self.interaction, adventure_moment_key)
        self._alarm_handle = add_alarm(self, time_span, callback)

    def _run_adventure_moment(self, adventure_moment_key, count_moment=True):
        if adventure_moment_key in self._adventure_moments:
            adventure_moment_data = self._adventure_moments[adventure_moment_key]
            self._current_moment_key = adventure_moment_key
            self.set_adventure_moment_cooldown(adventure_moment_key)
            adventure_moment_data.aventure_moment(self).run_adventure()
        if count_moment:
            self._adventure_moment_count += 1

    def _get_initial_adventure_moment_key(self):
        initial_adventure_moment_key = _initial_adventure_moment_key_overrides.get(self.interaction.sim)
        if initial_adventure_moment_key is not None and self.is_adventure_moment_available(initial_adventure_moment_key):
            return initial_adventure_moment_key
        if self._resumable:
            initial_adventure_moment_key = self.tracker.get_adventure_moment(self.interaction)
            if initial_adventure_moment_key is not None:
                self.force_action_result = True
                return initial_adventure_moment_key
        participant_resolver = self.interaction.get_resolver()
        return weighted_random_item([(moment.weight.get_multiplier(participant_resolver), moment.adventure_moment_key) for moment in self._initial_moments if self.is_adventure_moment_available(moment.adventure_moment_key)])

    def set_adventure_moment_cooldown(self, adventure_moment_key):
        if adventure_moment_key in self._adventure_moments:
            adventure_moment_data = self._adventure_moments[adventure_moment_key]
            if adventure_moment_data.sim_specific_cooldown is None:
                self.tracker.remove_adventure_moment_cooldown(self.interaction, adventure_moment_key)
                return
            self.tracker.set_adventure_moment_cooldown(self.interaction, adventure_moment_key, adventure_moment_data.sim_specific_cooldown)

    def is_adventure_moment_available(self, adventure_moment_key):
        if adventure_moment_key in self._adventure_moments:
            adventure_moment_data = self._adventure_moments[adventure_moment_key]
            return self.tracker.is_adventure_moment_available(self.interaction, adventure_moment_key, adventure_moment_data.sim_specific_cooldown)
        return True

    def _do_behavior(self):
        if self.tracker is not None:
            initial_moment = self._get_initial_adventure_moment_key()
            if initial_moment is not None:
                self._run_adventure_moment(initial_moment)

@sims4.commands.Command('adventure.toggle_show_all_adventure_moments')
def toggle_show_all_adventure_moments(enable:bool=None, _connection=None):
    global _show_all_adventure_moments
    if enable is None:
        enable = not _show_all_adventure_moments
    _show_all_adventure_moments = enable
