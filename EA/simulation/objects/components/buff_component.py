from _collections import defaultdictfrom collections import Counterimport collectionsimport itertoolsimport operatorimport randomfrom protocolbuffers import Commodities_pb2, Sims_pb2from protocolbuffers.DistributorOps_pb2 import Operationfrom buffs import Appropriatenessfrom date_and_time import create_time_spanfrom distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom event_testing import test_eventsfrom event_testing.resolver import SingleSimResolverfrom interactions import ParticipantTypeSimfrom interactions.base.picker_interaction import PickerSuperInteractionfrom interactions.utils.tunable import TunableContinuationfrom objects import ALL_HIDDEN_REASONSfrom objects.mixins import AffordanceCacheMixin, ProvidedAffordanceDatafrom routing.route_enums import RouteEventTypefrom sims.sim_info_lod import SimInfoLODLevelfrom sims4.callback_utils import CallableListfrom sims4.localization import TunableLocalizedStringFactory, TunableLocalizedStringfrom sims4.tuning.tunable import TunableReference, Tunable, TunableRange, TunableList, TunableTuple, TunableEnumFlags, TunableResourceKey, OptionalTunablefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom singletons import DEFAULTfrom statistics.statistic_ops import StatisticAddOpfrom teleport.teleport_enums import TeleportStyleSourcefrom teleport.teleport_tuning import TeleportTuningfrom ui.ui_dialog_picker import BasePickerRow, TunablePickerDialogVariant, ObjectPickerTuningFlagsfrom uid import UniqueIdGeneratorimport alarmsimport cachesimport enumimport gsi_handlersimport objects.components.typesimport servicesimport sims4.loglogger = sims4.log.Logger('BuffTracker', default_owner='msantander')
class BuffComponent(objects.components.Component, AffordanceCacheMixin, component_name=objects.components.types.BUFF_COMPONENT):
    DEFAULT_MOOD = TunableReference(services.mood_manager(), description='The default initial mood.')
    UPDATE_INTENSITY_BUFFER = TunableRange(description="\n        A buffer that prevents a mood from becoming active unless its intensity\n        is greater than the current active mood's intensity plus this amount.\n        \n        For example, if this tunable is 1, and the Sim is in a Flirty mood with\n        intensity 2, then a different mood would become the active mood only if\n        its intensity is 3+.\n        \n        If the predominant mood has an intensity that is less than the active\n        mood's intensity, that mood will become the active mood.\n        ", tunable_type=int, default=1, minimum=0)
    EXCLUSIVE_SET = TunableList(description='\n        A list of buff groups to determine which buffs are exclusive from each\n        other within the same group.  A buff cannot exist in more than one exclusive group.\n        \n        The following rule of exclusivity for a group:\n        1. Higher weight will always be added and remove any lower weight buffs\n        2. Lower weight buff will not be added if a higher weight already exist in component\n        3. Same weight buff will always be added and remove any buff with same weight.\n        \n        Example: Group 1:\n                    Buff1 with weight of 5 \n                    Buff2 with weight of 1\n                    Buff3 with weight of 1\n                 Group 2:\n                    Buff4 with weight of 6\n        \n        If sim has Buff1, trying to add Buff2 or Buff3 will not be added.\n        If sim has Buff2, trying to add Buff3 will remove Buff2 and add Buff3\n        If sim has Buff2, trying to add Buff1 will remove Buff 2 and add Buff3\n        If sim has Buff4, trying to add Buff1, Buff2, or Buff3 will be added and Buff4 will stay \n                          on component \n        ', tunable=TunableList(tunable=TunableTuple(buff_type=TunableReference(description='\n                    Buff in exclusive group\n                    ', manager=services.get_instance_manager(sims4.resources.Types.BUFF), pack_safe=True), weight=Tunable(description='\n                    weight to determine if this buff should be added and\n                    remove other buffs in the exclusive group or not added at all.\n                    \n                    Example: Buff1 with weight of 5 \n                             Buff2 with weight of 1\n                             Buff3 with weight of 1\n                    \n                    If sim has Buff1, trying to add Buff2 or Buff3 will not be added.\n                    If sim has Buff2, trying to add Buff3 will remove Buff2 and add Buff3\n                    if sim has Buff2, trying to add Buff1 will remove Buff 2 and add Buff3\n                    ', tunable_type=int, default=1))))

    def __init__(self, owner):
        super().__init__(owner)
        self._active_buffs = {}
        self._get_next_handle_id = UniqueIdGenerator()
        self._success_chance_modification = 0
        self._active_mood = self.DEFAULT_MOOD
        self._active_mood_intensity = 0
        self._active_mood_buff_handle = None
        self.on_mood_changed = CallableList()
        self.on_mood_changed.append(self._publish_mood_update)
        self.on_mood_changed.append(self._send_mood_changed_event)
        self.load_in_progress = False
        self._additional_posture_costs = Counter()
        self.on_buff_added = CallableList()
        self.on_buff_removed = CallableList()
        self._active_teleport_styles = None
        self.buff_update_alarms = {}
        if self._active_mood is None:
            logger.error('No default mood tuned in buff_component.py')
        elif self._active_mood.buffs:
            initial_buff_ref = self._active_mood.buffs[0]
            if initial_buff_ref.buff_type:
                self._active_mood_buff_handle = self.add_buff(initial_buff_ref.buff_type)

    def __iter__(self):
        return self._active_buffs.values().__iter__()

    def __len__(self):
        return len(self._active_buffs)

    def on_sim_ready_to_simulate(self):
        region_instance = services.current_region()
        for region_buff in region_instance.region_buffs:
            self.add_buff_from_op(region_buff)
        weather_service = services.weather_service()
        if weather_service is not None:
            weather_service.apply_weather_option_buffs(self.owner)
        for (buff_type, buff) in tuple(self._active_buffs.items()):
            if buff_type not in self._active_buffs:
                pass
            else:
                buff.on_sim_ready_to_simulate()
        self._publish_mood_update()

    def on_sim_removed(self, *args, **kwargs):
        for buff in tuple(self):
            buff.on_sim_removed(*args, **kwargs)
        self._remove_non_persist_buffs()

    def on_sim_added_to_skewer(self):
        self._create_and_send_buff_clear_all_msg()
        for buff in self:
            self.send_buff_update_msg(buff, True)

    def on_sim_reset(self):
        for buff in self:
            buff.on_sim_reset()

    def clean_up(self):
        for (buff_type, buff_entry) in tuple(self._active_buffs.items()):
            self.remove_auto_update(buff_type)
            buff_entry.clean_up()
        self._active_buffs.clear()
        self.on_mood_changed.clear()
        self.on_buff_added.clear()
        self.on_buff_removed.clear()

    @objects.components.componentmethod
    def add_buff_from_op(self, buff_type, buff_reason=None):
        (can_add, _) = self._can_add_buff_type(buff_type)
        if not can_add:
            return False
        buff_commodity = buff_type.commodity
        if buff_commodity is not None:
            if self.has_buff(buff_type):
                if buff_type.reloot_on_add:
                    buff = self._active_buffs.get(buff_type)
                    buff.apply_all_loot_actions()
                if not buff_type.refresh_on_add:
                    return False
            tracker = self.owner.get_tracker(buff_commodity)
            if buff_commodity.convergence_value == buff_commodity.max_value:
                tracker.set_min(buff_commodity)
            else:
                tracker.set_max(buff_commodity)
            self.set_buff_reason(buff_type, buff_reason, use_replacement=True)
        else:
            self.add_buff(buff_type, buff_reason=buff_reason)
        return True

    @objects.components.componentmethod
    def add_buff(self, buff_type, buff_reason=None, update_mood=True, commodity_guid=None, replacing_buff=None, timeout_string=None, timeout_string_no_next_buff=None, transition_into_buff_id=0, change_rate=None, immediate=False, from_load=False, apply_buff_loot=True, additional_static_commodities_to_add=None, remove_on_zone_unload=True):
        from_load = from_load or self.load_in_progress
        (replacement_buff_type, replacement_buff_reason) = self._get_replacement_buff_type_and_reason(buff_type, buff_reason)
        if replacement_buff_type is not None:
            return self.owner.add_buff(replacement_buff_type, buff_reason=replacement_buff_reason, update_mood=update_mood, commodity_guid=commodity_guid, replacing_buff=buff_type, timeout_string=timeout_string, timeout_string_no_next_buff=timeout_string_no_next_buff, transition_into_buff_id=transition_into_buff_id, change_rate=change_rate, immediate=immediate, from_load=from_load, apply_buff_loot=apply_buff_loot, additional_static_commodities_to_add=additional_static_commodities_to_add, remove_on_zone_unload=remove_on_zone_unload)
        (can_add, conflicting_buff_type) = self._can_add_buff_type(buff_type)
        if not can_add:
            return
        buff = self._active_buffs.get(buff_type)
        if buff is None:
            buff = buff_type(self.owner, commodity_guid, replacing_buff, transition_into_buff_id, additional_static_commodities_to_add=additional_static_commodities_to_add, remove_on_zone_unload=remove_on_zone_unload)
            self._active_buffs[buff_type] = buff
            buff.on_add(from_load=from_load, apply_buff_loot=apply_buff_loot)
            provided_affordances = []
            for provided_affordance in buff.target_super_affordances:
                provided_affordance_data = ProvidedAffordanceData(provided_affordance.affordance, provided_affordance.object_filter, provided_affordance.allow_self)
                provided_affordances.append(provided_affordance_data)
            self.add_to_affordance_caches(buff.super_affordances, provided_affordances)
            self.add_to_actor_mixer_cache(buff.actor_mixers)
            self.add_to_provided_mixer_cache(buff.provided_mixers)
            self._update_chance_modifier()
            if update_mood:
                self._update_current_mood()
            if self.owner.household is not None:
                services.get_event_manager().process_event(test_events.TestEvent.BuffBeganEvent, sim_info=self.owner, sim_id=self.owner.sim_id, buff=buff_type, custom_keys=(buff_type,))
                self.register_auto_update(self.owner, buff_type)
            self.on_buff_added(buff_type, self.owner.id)
            self._additional_posture_costs.update(buff.additional_posture_costs)
        handle_id = self._get_next_handle_id()
        buff.add_handle(handle_id, buff_reason=buff_reason)
        self.send_buff_update_msg(buff, True, change_rate=change_rate, immediate=immediate)
        if conflicting_buff_type is not None:
            self.remove_buff_by_type(conflicting_buff_type)
        return handle_id

    def _get_replacement_buff_type_and_reason(self, buff_type, buff_reason):
        if buff_type.trait_replacement_buffs is not None:
            trait_tracker = self.owner.trait_tracker
            for (trait, replacement_buff_data) in sorted(buff_type.trait_replacement_buffs.items(), key=lambda item: item[1].buff_replacement_priority, reverse=True):
                replacement_buff_type = replacement_buff_data.buff_type
                if trait_tracker.has_trait(trait) and replacement_buff_type.can_add(self.owner):
                    replacement_buff_reason = buff_reason if replacement_buff_data.buff_reason is None else replacement_buff_data.buff_reason
                    return (replacement_buff_type, replacement_buff_reason)
        return (None, None)

    def register_auto_update(self, sim_info_in, buff_type_in):
        if buff_type_in in self.buff_update_alarms:
            self.remove_auto_update(buff_type_in)
        if buff_type_in.visible:
            self.buff_update_alarms[buff_type_in] = alarms.add_alarm(self, create_time_span(minutes=15), lambda _, sim_info=sim_info_in, buff_type=buff_type_in: services.get_event_manager().process_event(test_events.TestEvent.BuffUpdateEvent, sim_info=sim_info, sim_id=sim_info.sim_id, buff=buff_type), True)

    def remove_auto_update(self, buff_type):
        if buff_type in self.buff_update_alarms:
            alarms.cancel_alarm(self.buff_update_alarms[buff_type])
            del self.buff_update_alarms[buff_type]

    @objects.components.componentmethod
    def remove_buff(self, handle_id, update_mood=True, immediate=False, on_destroy=False):
        for (buff_type, buff_entry) in self._active_buffs.items():
            if handle_id in buff_entry.handle_ids:
                should_remove = buff_entry.remove_handle(handle_id)
                if should_remove:
                    del self._active_buffs[buff_type]
                    buff_entry.on_remove(apply_loot_on_remove=not self.load_in_progress and not on_destroy)
                    if not on_destroy:
                        self.update_affordance_caches()
                        if update_mood:
                            self._update_current_mood()
                        self._update_chance_modifier()
                        self.send_buff_update_msg(buff_entry, False, immediate=immediate)
                        services.get_event_manager().process_event(test_events.TestEvent.BuffEndedEvent, sim_info=self.owner, sim_id=self.owner.sim_id, buff=buff_type)
                    if buff_type in self.buff_update_alarms:
                        self.remove_auto_update(buff_type)
                    self.on_buff_removed(buff_type, self.owner.id)
                    self._additional_posture_costs.subtract(buff_type.additional_posture_costs)
                break

    @objects.components.componentmethod
    def get_buff_type(self, handle_id):
        for (buff_type, buff_entry) in self._active_buffs.items():
            if handle_id in buff_entry.handle_ids:
                return buff_type

    @objects.components.componentmethod
    def get_buff_by_type(self, buff_type):
        return self._active_buffs.get(buff_type)

    @objects.components.componentmethod
    def has_buff(self, buff_type):
        return buff_type in self._active_buffs

    @objects.components.componentmethod
    def has_buff_with_tag(self, tag):
        return any(buff.has_tag(tag) for buff in self._active_buffs)

    @objects.components.componentmethod_with_fallback(lambda *_, **__: ())
    def get_all_buffs_with_tag(self, tag):
        return (buff for buff in self._active_buffs if buff.has_tag(tag))

    @objects.components.componentmethod
    def get_active_buff_types(self):
        return self._active_buffs.keys()

    @objects.components.componentmethod
    def get_buff_reason(self, handle_id):
        for buff_entry in self._active_buffs.values():
            if handle_id in buff_entry.handle_ids:
                return buff_entry.buff_reason

    @objects.components.componentmethod
    def debug_add_buff_by_type(self, buff_type):
        (can_add, conflicting_buff_type) = self._can_add_buff_type(buff_type)
        if not can_add:
            return False
        if buff_type.commodity is not None:
            tracker = self.owner.get_tracker(buff_type.commodity)
            state_index = buff_type.commodity.get_state_index_matches_buff_type(buff_type)
            if state_index is not None:
                index = state_index + 1
                if index < len(buff_type.commodity.commodity_states):
                    commodity_to_value = buff_type.commodity.commodity_states[index].value - 1
                else:
                    commodity_to_value = buff_type.commodity.max_value
                tracker.set_value(buff_type.commodity, commodity_to_value)
            else:
                logger.error('commodity ({}) has no states with buff ({}), Buff will not be added.', buff_type.commodity, buff_type)
                return False
        else:
            self.add_buff(buff_type)
        if conflicting_buff_type is not None:
            self.remove_buff_by_type(conflicting_buff_type)
        return True

    @objects.components.componentmethod
    def remove_buffs_by_tags(self, tags, count_to_remove=None, on_destroy=False):
        buffs_tagged = [buff for buff in self._active_buffs.values() if buff.has_any_tag(tags)]
        if count_to_remove is None:
            for buff_entry in buffs_tagged:
                self.remove_buff_entry(buff_entry, on_destroy=on_destroy)
        else:
            random.shuffle(buffs_tagged)
            for buff_entry in buffs_tagged:
                self.remove_buff_entry(buff_entry, on_destroy=on_destroy)
                count_to_remove -= 1
                if count_to_remove <= 0:
                    return

    @objects.components.componentmethod
    def remove_buff_by_type(self, buff_type, on_destroy=False):
        buff_entry = self._active_buffs.get(buff_type, None)
        if buff_entry is not None:
            self.remove_buff_entry(buff_entry, on_destroy=on_destroy)

    @objects.components.componentmethod
    def remove_buff_entry(self, buff_entry, on_destroy=False):
        if buff_entry is not None:
            if buff_entry.commodity is not None:
                tracker = self.owner.get_tracker(buff_entry.commodity)
                commodity_inst = tracker.get_statistic(buff_entry.commodity)
                if commodity_inst is not None and commodity_inst.core:
                    if not on_destroy:
                        logger.callstack('Attempting to explicitly remove the buff {}, which is given by a core commodity.                                           This would result in the removal of a core commodity and will be ignored.', buff_entry, owner='tastle', level=sims4.log.LEVEL_ERROR)
                    return
                tracker.remove_statistic(buff_entry.commodity, on_destroy=on_destroy)
            elif buff_entry.buff_type in self._active_buffs:
                buff_type = buff_entry.buff_type
                del self._active_buffs[buff_type]
                buff_entry.on_remove(apply_loot_on_remove=not self.load_in_progress and not on_destroy)
                if not on_destroy:
                    self.update_affordance_caches()
                    self._update_chance_modifier()
                    self._update_current_mood()
                    self.send_buff_update_msg(buff_entry, False)
                    services.get_event_manager().process_event(test_events.TestEvent.BuffEndedEvent, sim_info=self.owner, buff=buff_type, sim_id=self.owner.id)
                elif self.owner.is_selectable:
                    self._update_current_mood()
                    self.send_buff_update_msg(buff_entry, False)
                self.on_buff_removed(buff_type, self.owner.id)

    @objects.components.componentmethod
    def set_buff_reason(self, buff_type, buff_reason, use_replacement=False):
        buff_commodity = buff_type.commodity
        if use_replacement:
            (replacement_buff_type, replacement_buff_reason) = self._get_replacement_buff_type_and_reason(buff_type, buff_reason)
            if replacement_buff_type is not None:
                buff_type = replacement_buff_type
                buff_reason = replacement_buff_reason
        if buff_reason is None:
            return
        buff_entry = self._active_buffs.get(buff_type)
        if buff_entry is not None:
            buff_entry.buff_reason = buff_reason
            self.send_buff_update_msg(buff_entry, True)
        elif buff_commodity is not None:
            tracker = self.owner.get_tracker(buff_commodity)
            stat = tracker.get_statistic(buff_commodity, add=False)
            if stat is not None:
                stat.force_buff_reason = buff_reason

    @objects.components.componentmethod
    def buff_commodity_changed(self, handle_id, change_rate=None, transition_into_buff_id=0):
        for (_, buff_entry) in self._active_buffs.items():
            if handle_id in buff_entry.handle_ids:
                if buff_entry.show_timeout:
                    buff_entry.transition_into_buff_id = transition_into_buff_id
                    self.send_buff_update_msg(buff_entry, True, change_rate=change_rate)
                break

    @objects.components.componentmethod
    def get_success_chance_modifier(self):
        return self._success_chance_modification

    @objects.components.componentmethod
    def get_actor_scoring_modifier(self, affordance, resolver):
        total = 0
        for buff_entry in self._active_buffs.values():
            total += buff_entry.effect_modification.get_affordance_scoring_modifier(affordance, resolver)
        return total

    @objects.components.componentmethod
    def get_actor_success_modifier(self, affordance, resolver):
        total = 0
        for buff_entry in self._active_buffs.values():
            total += buff_entry.effect_modification.get_affordance_success_modifier(affordance, resolver)
        return total

    @objects.components.componentmethod
    def get_actor_new_pie_menu_icon_and_parent_name(self, affordance, resolver):
        icon = None
        parent = None
        icon_tag = None
        parent_tag = None
        for buff_entry in self._active_buffs.values():
            (new_icon, new_parent, new_icon_tag, new_parent_tag) = buff_entry.effect_modification.get_affordance_new_pie_menu_icon_and_parent_name(affordance, resolver)
            if new_icon is not None:
                if icon is not None and icon is not new_icon:
                    logger.error('different valid pie menu icons specified in {}', self, owner='nabaker')
                else:
                    icon = new_icon
                    if icon_tag is None:
                        icon_tag = new_icon_tag
                    else:
                        icon_tag &= new_icon_tag
            if new_parent is not None:
                if parent is not None and parent is not new_parent:
                    logger.error('different valid pie menu parent names specified in {}', self, owner='nabaker')
                else:
                    parent = new_parent
                    if parent_tag is None:
                        parent_tag = new_parent_tag
                    else:
                        parent_tag &= new_parent_tag
        if icon_tag is None:
            icon_tag = set()
        if parent_tag is None:
            parent_tag = set()
        return (icon, parent, icon_tag, parent_tag)

    @objects.components.componentmethod
    def get_actor_basic_extras_reversed_gen(self, affordance, resolver):
        for buff_entry in self._active_buffs.values():
            yield from buff_entry.effect_modification.get_affordance_basic_extras_reversed_gen(affordance, resolver)

    @objects.components.componentmethod
    def test_pie_menu_modifiers(self, affordance):
        buffs = self._get_buffs_with_pie_menu_modifiers()
        for buff in buffs:
            (visible, tooltip) = buff.effect_modification.test_pie_menu_modifiers(affordance)
            if visible:
                if tooltip is not None:
                    return (visible, tooltip)
            return (visible, tooltip)
        return (True, None)

    @caches.cached
    def _get_buffs_with_pie_menu_modifiers(self):
        return tuple(buff for buff in self._active_buffs.values() if buff.effect_modification.has_pie_menu_modifiers())

    @objects.components.componentmethod
    def get_mood(self):
        return self._active_mood

    @objects.components.componentmethod
    def get_mood_animation_param_name(self):
        param_name = self._active_mood.asm_param_name
        if param_name is not None:
            return param_name
        (mood, _, _) = self._get_largest_mood(predicate=lambda mood: True if mood.asm_param_name else False)
        return mood.asm_param_name

    @objects.components.componentmethod
    def get_mood_intensity(self):
        return self._active_mood_intensity

    @objects.components.componentmethod
    def get_effective_skill_level(self, skill):
        if skill.stat_type == skill:
            skill = self.owner.get_stat_instance(skill) or skill
        user_value = skill.get_user_value()
        modifier = 0
        for buff_entry in self._active_buffs.values():
            modifier += buff_entry.effect_modification.get_effective_skill_modifier(skill)
        return user_value + modifier

    @objects.components.componentmethod
    def effective_skill_modified_buff_gen(self, skill):
        for buff_entry in self._active_buffs.values():
            modifier = buff_entry.effect_modification.get_effective_skill_modifier(skill)
            if modifier != 0:
                yield (buff_entry, modifier)

    @objects.components.componentmethod
    def is_appropriate(self, tags):
        final_appropriateness = Appropriateness.DONT_CARE
        for buff in self._active_buffs:
            appropriateness = buff.get_appropriateness(tags)
            if appropriateness > final_appropriateness:
                final_appropriateness = appropriateness
        if final_appropriateness == Appropriateness.NOT_ALLOWED:
            return False
        else:
            return True

    @objects.components.componentmethod
    def get_additional_posture_costs(self):
        return self._additional_posture_costs

    @objects.components.componentmethod
    def add_venue_buffs(self):
        venue_instance = services.get_current_venue()
        for venue_buff in venue_instance.venue_buffs:
            self.add_buff_from_op(venue_buff.buff_type, buff_reason=venue_buff.buff_reason)

    @objects.components.componentmethod
    def get_super_affordance_availability_gen(self):
        yield from self.get_cached_super_affordances_gen()

    @objects.components.componentmethod
    def get_target_super_affordance_availability_gen(self, context, target):
        yield from self.get_cached_target_super_affordances_gen(context, target)

    @objects.components.componentmethod
    def get_actor_mixers(self, super_interaction):
        return self.get_cached_actor_mixers(super_interaction)

    @objects.components.componentmethod
    def get_provided_mixers_gen(self, super_interaction):
        yield from self.get_cached_provided_mixers_gen(super_interaction)

    @objects.components.componentmethod
    def get_target_provided_affordances_data_gen(self):
        yield from self.get_cached_target_provided_affordances_data_gen()

    def get_provided_super_affordances(self):
        affordances = set()
        target_affordances = list()
        for buff_entry in self:
            affordances.update(buff_entry.super_affordances)
            for provided_affordance in buff_entry.target_super_affordances:
                provided_affordance_data = ProvidedAffordanceData(provided_affordance.affordance, provided_affordance.object_filter, provided_affordance.allow_self)
                target_affordances.append(provided_affordance_data)
        return (affordances, target_affordances)

    def get_actor_and_provided_mixers_list(self):
        actor_mixers = [buff_entry.actor_mixers for buff_entry in self]
        provided_mixers = [buff_entry.provided_mixers for buff_entry in self]
        return (actor_mixers, provided_mixers)

    def get_sim_info_from_provider(self):
        return self.owner

    @objects.components.componentmethod
    def add_teleport_style(self, source_type, teleport_style):
        if self._active_teleport_styles is None:
            self._active_teleport_styles = defaultdict(list)
        self._active_teleport_styles[source_type].append(teleport_style)

    @objects.components.componentmethod
    def remove_teleport_style(self, source_type, teleport_style):
        self._active_teleport_styles[source_type].remove(teleport_style)
        if len(self._active_teleport_styles[source_type]) == 0:
            del self._active_teleport_styles[source_type]
        if not self._active_teleport_styles:
            self._active_teleport_styles = None

    @objects.components.componentmethod
    def get_active_teleport_multiplier(self):
        multiplier = 1
        for buff_entry in self._active_buffs.values():
            if buff_entry.teleport_cost_multiplier:
                multiplier *= buff_entry.teleport_cost_multiplier
        return multiplier

    @objects.components.componentmethod_with_fallback(lambda *_, **__: None)
    def get_active_teleport_style(self):
        if self._active_teleport_styles is None:
            return (None, None, False)
        active_multiplier = self.get_active_teleport_multiplier()
        tuned_liability_style = self._active_teleport_styles.get(TeleportStyleSource.TUNED_LIABILITY, None)
        if tuned_liability_style:
            (teleport_data, cost) = self.get_teleport_data_and_cost(tuned_liability_style[0], active_multiplier)
            return (teleport_data, cost, True)
        for active_teleports in self._active_teleport_styles.values():
            for teleport_style in active_teleports:
                (teleport_data, cost) = self.get_teleport_data_and_cost(teleport_style, active_multiplier)
                if teleport_data is None:
                    pass
                else:
                    return (teleport_data, cost, False)
        return (None, None, False)

    @objects.components.componentmethod_with_fallback(lambda *_, **__: False)
    def can_trigger_teleport_style(self, teleport_style):
        active_multiplier = self.get_active_teleport_multiplier()
        (_, cost) = self.get_teleport_data_and_cost(teleport_style, active_multiplier)
        return cost is not None

    @objects.components.componentmethod
    def get_teleport_data_and_cost(self, teleport_style, active_multiplier):
        teleport_data = TeleportTuning.get_teleport_data(teleport_style)
        cost_tuning = teleport_data.teleport_cost
        if cost_tuning is not None:
            current_value = self.owner.get_stat_value(teleport_data.teleport_cost.teleport_statistic)
            current_cost = active_multiplier*teleport_data.teleport_cost.cost
            if cost_tuning.cost_is_additive:
                if current_value + current_cost < cost_tuning.teleport_statistic.max_value:
                    return (teleport_data, current_cost)
            elif current_value - current_cost > cost_tuning.teleport_statistic.min_value:
                return (teleport_data, current_cost)
            return (None, None)
        return (TeleportTuning.get_teleport_data(teleport_style), None)

    def provide_route_events_from_buffs(self, route_event_context, sim, path, failed_types=None, **kwargs):
        for buff_entry in self:
            if buff_entry.route_events is not None:
                buff_entry.provide_route_events(route_event_context, sim, path, failed_types, **kwargs)

    def get_additional_create_ops_gen(self):
        if self.owner.lod == SimInfoLODLevel.MINIMUM:
            return
        yield GenericProtocolBufferOp(Operation.SIM_MOOD_UPDATE, self._create_mood_update_msg())
        for buff in self:
            if buff.visible:
                yield GenericProtocolBufferOp(Operation.SIM_BUFF_UPDATE, self._create_buff_update_msg(buff, True))

    def _publish_mood_update(self, **kwargs):
        if self.owner.valid_for_distribution and self.owner.visible_to_client == True:
            Distributor.instance().add_op(self.owner, GenericProtocolBufferOp(Operation.SIM_MOOD_UPDATE, self._create_mood_update_msg()))

    def _send_mood_changed_event(self, old_mood=None, new_mood=None):
        if self.owner.whim_tracker is not None:
            self.owner.whim_tracker.refresh_emotion_whim()
        services.get_event_manager().process_event(test_events.TestEvent.MoodChange, sim_info=self.owner, old_mood=old_mood, new_mood=new_mood)

    def _create_mood_update_msg(self):
        mood_msg = Commodities_pb2.MoodUpdate()
        mood_msg.sim_id = self.owner.id
        mood_msg.mood_key = self._active_mood.guid64
        mood_msg.mood_intensity = self._active_mood_intensity
        return mood_msg

    def _create_buff_update_msg(self, buff, equipped, change_rate=None):
        buff_msg = Sims_pb2.BuffUpdate()
        buff_msg.buff_id = buff.guid64
        buff_msg.sim_id = self.owner.id
        buff_msg.equipped = equipped
        if buff.buff_reason is not None:
            buff_msg.reason = buff.buff_reason
        if buff.show_timeout:
            (timeout, rate_multiplier) = buff.get_timeout_time()
            buff_msg.timeout = timeout
            buff_msg.rate_multiplier = rate_multiplier
            if change_rate is not None:
                if change_rate == 0:
                    progress_arrow = Sims_pb2.BUFF_PROGRESS_NONE
                elif change_rate > 0:
                    progress_arrow = Sims_pb2.BUFF_PROGRESS_UP if not buff.flip_arrow_for_progress_update else Sims_pb2.BUFF_PROGRESS_DOWN
                else:
                    progress_arrow = Sims_pb2.BUFF_PROGRESS_DOWN if not buff.flip_arrow_for_progress_update else Sims_pb2.BUFF_PROGRESS_UP
                buff_msg.buff_progress = progress_arrow
        buff_msg.is_mood_buff = buff.is_mood_buff
        buff_msg.commodity_guid = equipped and buff.commodity_guid or 0
        if buff.mood_override is not None:
            buff_msg.mood_type_override = buff.mood_override.guid64
        buff_msg.transition_into_buff_id = buff.transition_into_buff_id
        for (overlay_type, linked_commodity) in buff.motive_panel_overlays.items():
            with ProtocolBufferRollback(buff_msg.motive_overlays) as motive_overlay:
                motive_overlay.overlay_type = overlay_type
                motive_overlay.commodity_guid = linked_commodity.guid64
        return buff_msg

    def send_buff_update_msg(self, buff, equipped, change_rate=None, immediate=False):
        if buff.visible or not buff.motive_panel_overlays:
            return
        if self.owner.valid_for_distribution and self.owner.is_sim and self.owner.is_selectable:
            buff_msg = self._create_buff_update_msg(buff, equipped, change_rate=change_rate)
            if gsi_handlers.buff_handlers.sim_buff_log_archiver.enabled:
                gsi_handlers.buff_handlers.archive_buff_message(buff_msg, equipped, change_rate)
            Distributor.instance().add_op(self.owner, GenericProtocolBufferOp(Operation.SIM_BUFF_UPDATE, buff_msg))

    def _create_and_send_buff_clear_all_msg(self):
        buff_msg = Sims_pb2.BuffClearAll()
        buff_msg.sim_id = self.owner.sim_id
        Distributor.instance().add_op(self.owner, GenericProtocolBufferOp(Operation.SIM_BUFF_CLEAR_ALL, buff_msg))

    def _can_add_buff_type(self, buff_type):
        if not buff_type.can_add(self.owner):
            return (False, None)
        mood = buff_type.mood_type
        if mood is not None and mood.excluding_traits is not None and self.owner.trait_tracker.has_any_trait(mood.excluding_traits):
            return (False, None)
        if buff_type.exclusive_index is None:
            return (True, None)
        for conflicting_buff_type in self._active_buffs:
            if conflicting_buff_type is buff_type:
                pass
            elif conflicting_buff_type.exclusive_index == buff_type.exclusive_index:
                if buff_type.exclusive_weight < conflicting_buff_type.exclusive_weight:
                    return (False, None)
                return (True, conflicting_buff_type)
        return (True, None)

    def _update_chance_modifier(self):
        positive_success_buff_delta = 0
        negative_success_buff_delta = 1
        for buff_entry in self._active_buffs.values():
            if buff_entry.success_modifier > 0:
                positive_success_buff_delta += buff_entry.get_success_modifier
            else:
                negative_success_buff_delta *= 1 + buff_entry.get_success_modifier
        self._success_chance_modification = positive_success_buff_delta - (1 - negative_success_buff_delta)

    def _get_largest_mood(self, predicate=None, buffs_to_ignore=()):
        weights = {}
        polarity_to_changeable_buffs = collections.defaultdict(list)
        polarity_to_largest_mood_and_weight = {}
        mood_modifiers_mapping = {}
        for buff_entry in self._active_buffs.values():
            this_modifier = buff_entry.effect_modification.get_mood_category_weight_mapping()
            for (mood, modifier) in this_modifier.items():
                total_modifier = mood_modifiers_mapping.get(mood, 1)*modifier
                mood_modifiers_mapping[mood] = total_modifier
        for buff_entry in self._active_buffs.values():
            current_mood = buff_entry.mood_type
            current_weight = buff_entry.mood_weight
            if not current_mood is None:
                if current_weight == 0:
                    pass
                elif predicate is not None and not predicate(current_mood):
                    pass
                elif buff_entry in buffs_to_ignore:
                    pass
                else:
                    current_polarity = current_mood.buff_polarity
                    if buff_entry.is_changeable:
                        polarity_to_changeable_buffs[current_polarity].append(buff_entry)
                    else:
                        total_current_weight = weights.get(current_mood, 0)
                        total_current_weight += current_weight*mood_modifiers_mapping.get(current_mood, 1.0)
                        weights[current_mood] = total_current_weight
                        (largest_mood, largest_weight) = polarity_to_largest_mood_and_weight.get(current_polarity, (None, None))
                        if largest_mood is None:
                            polarity_to_largest_mood_and_weight[current_polarity] = (current_mood, total_current_weight)
                        elif total_current_weight > largest_weight:
                            polarity_to_largest_mood_and_weight[current_polarity] = (current_mood, total_current_weight)
        all_changeable_buffs = []
        for (buff_polarity, changeable_buffs) in polarity_to_changeable_buffs.items():
            (largest_mood, largest_weight) = polarity_to_largest_mood_and_weight.get(buff_polarity, (None, None))
            if largest_mood is not None:
                for buff_entry in changeable_buffs:
                    if buff_entry.mood_override is not largest_mood:
                        all_changeable_buffs.append((buff_entry, largest_mood))
                    largest_weight += buff_entry.mood_weight*mood_modifiers_mapping.get(largest_mood, 1.0)
                polarity_to_largest_mood_and_weight[buff_polarity] = (largest_mood, largest_weight)
            else:
                weights = {}
                largest_weight = 0
                for buff_entry in changeable_buffs:
                    if buff_entry.mood_override is not None:
                        all_changeable_buffs.append((buff_entry, None))
                    current_mood = buff_entry.mood_type
                    current_weight = buff_entry.mood_weight
                    total_current_weight = weights.get(current_mood, 0)
                    total_current_weight += current_weight*mood_modifiers_mapping.get(current_mood, 1.0)
                    weights[current_mood] = total_current_weight
                    if total_current_weight > largest_weight:
                        largest_weight = total_current_weight
                        largest_mood = current_mood
                if largest_mood is not None and largest_weight != 0:
                    polarity_to_largest_mood_and_weight[buff_polarity] = (largest_mood, largest_weight)
        largest_weight = 0
        largest_mood = self.DEFAULT_MOOD
        active_mood = self._active_mood
        if polarity_to_largest_mood_and_weight:
            (mood, weight) = max(polarity_to_largest_mood_and_weight.values(), key=operator.itemgetter(1))
            if mood is active_mood:
                largest_weight = weight
                largest_mood = mood
        return (largest_mood, largest_weight, all_changeable_buffs)

    def _update_current_mood(self):
        (largest_mood, largest_weight, changeable_buffs) = self._get_largest_mood()
        if largest_mood is not None:
            intensity = self._get_intensity_from_mood(largest_mood, largest_weight)
            if self._should_update_mood(largest_mood, intensity, changeable_buffs):
                if self._active_mood_buff_handle is not None:
                    active_mood_buff_handle = self._active_mood_buff_handle
                    self.remove_buff(active_mood_buff_handle, update_mood=False)
                    if active_mood_buff_handle == self._active_mood_buff_handle:
                        self._active_mood_buff_handle = None
                    else:
                        return
                old_mood = self._active_mood
                self._active_mood = largest_mood
                self._active_mood_intensity = intensity
                if len(largest_mood.buffs) >= intensity:
                    tuned_buff = largest_mood.buffs[intensity]
                    if tuned_buff.buff_type is not None:
                        self._active_mood_buff_handle = self.add_buff(tuned_buff.buff_type, update_mood=False)
                if gsi_handlers.buff_handlers.sim_mood_log_archiver.enabled and self.owner.valid_for_distribution and self.owner.visible_to_client == True:
                    gsi_handlers.buff_handlers.archive_mood_message(self.owner.id, self._active_mood, self._active_mood_intensity, self._active_buffs, changeable_buffs)
                caches.clear_all_caches()
                self.on_mood_changed(old_mood=old_mood, new_mood=self._active_mood)
        for (changeable_buff, mood_override) in changeable_buffs:
            changeable_buff.mood_override = mood_override
            self.send_buff_update_msg(changeable_buff, True)

    def _get_intensity_from_mood(self, mood, weight):
        intensity = 0
        for threshold in mood.intensity_thresholds:
            if weight >= threshold:
                intensity += 1
            else:
                break
        if intensity < 0:
            fallback_intensity = max(len(mood.intensity_thresholds) - 1, 0)
            logger.error('Intensity became {} for {}, weight: {}. Setting to {}', intensity, mood, weight, fallback_intensity)
            intensity = fallback_intensity
        return intensity

    def _should_update_mood(self, mood, intensity, changeable_buffs):
        active_mood = self._active_mood
        active_mood_intensity = self._active_mood_intensity
        if mood is active_mood:
            return intensity != active_mood_intensity
        total_weight = sum(buff_entry.mood_weight for buff_entry in self._active_buffs.values() if buff_entry.mood_type is active_mood)
        active_mood_intensity = self._get_intensity_from_mood(active_mood, total_weight)
        if not self._active_mood.is_changeable:
            buffs_to_ignore = [changeable_buff for (changeable_buff, _) in changeable_buffs]
            (largest_mood, largest_weight, _) = self._get_largest_mood(buffs_to_ignore=buffs_to_ignore)
            new_intensity = self._get_intensity_from_mood(largest_mood, largest_weight)
            if self._should_update_mood(largest_mood, new_intensity, None):
                active_mood = largest_mood
                active_mood_intensity = new_intensity
        if changeable_buffs and active_mood.is_changeable and mood.buff_polarity == active_mood.buff_polarity:
            return True
        if intensity and intensity < active_mood_intensity:
            return True
        if intensity >= active_mood_intensity + self.UPDATE_INTENSITY_BUFFER:
            return True
        elif mood is self.DEFAULT_MOOD or active_mood is self.DEFAULT_MOOD:
            return True
        return False

    def on_zone_load(self):
        if services.game_services.service_manager.is_traveling:
            self._active_mood = self.DEFAULT_MOOD
            self._active_mood_intensity = 0
            self._active_mood_buff_handle = None

    def on_zone_unload(self):
        if not services.game_services.service_manager.is_traveling:
            return
        self._remove_non_persist_buffs()

    def remove_all_buffs_with_temporary_commodities(self):
        buff_types_to_remove = set()
        for (buff_type, buff) in self._active_buffs.items():
            if buff.has_temporary_commodity:
                buff_types_to_remove.add(buff_type)
        if buff_types_to_remove:
            for buff_type in buff_types_to_remove:
                self.remove_buff_by_type(buff_type)

    def _remove_non_persist_buffs(self):
        buff_types_to_remove = set()
        for (buff_type, buff) in self._active_buffs.items():
            if not buff.commodity is None:
                pass
            if buff._remove_on_zone_unload:
                buff_types_to_remove.add(buff_type)
        if buff_types_to_remove:
            for buff_type in buff_types_to_remove:
                self.remove_buff_by_type(buff_type, True)
            self.update_affordance_caches()

    def on_lod_update(self, old_lod, new_lod):
        if new_lod <= old_lod:
            return
        sim = self.owner.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            return
        resolver = sim.get_resolver()
        for buff_entry in tuple(self._active_buffs.values()):
            for loot_actions in list(itertools.chain(buff_entry._loot_on_instance, buff_entry._loot_on_addition)):
                for loot_action in loot_actions.loot_actions:
                    if isinstance(loot_action, StatisticAddOp):
                        loot_action.apply_to_resolver(resolver)

def _update_buffs_with_exclusive_data(buff_manager):
    for (index, exclusive_set) in enumerate(BuffComponent.EXCLUSIVE_SET):
        for buff_type_data in exclusive_set:
            buff_type = buff_type_data.buff_type
            buff_type.exclusive_index = index
            buff_type.exclusive_weight = buff_type_data.weight
if not sims4.reload.currently_reloading:
    services.get_instance_manager(sims4.resources.Types.BUFF).add_on_load_complete(_update_buffs_with_exclusive_data)
class BuffPickerSuperInteraction(PickerSuperInteraction):

    class BuffHandlingType(enum.IntFlags):
        HIDE = 1
        SELECT = 2
        DISABLE = 4

    INSTANCE_TUNABLES = {'picker_dialog': TunablePickerDialogVariant(description='\n            The item picker dialog.\n            ', available_picker_flags=ObjectPickerTuningFlags.ITEM, tuning_group=GroupNames.PICKERTUNING), 'is_add': Tunable(description='\n            If this interaction is trying to add a buff to the targets\n            or to remove a buff from the target sim.\n            Remove is single target only.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.PICKERTUNING), 'subject': TunableEnumFlags(description='\n            From whom the buffs should be added/removed.\n            ', enum_type=ParticipantTypeSim, default=ParticipantTypeSim.TargetSim, tuning_group=GroupNames.PICKERTUNING), 'handle_existing': TunableEnumFlags(description="\n            How buffs that already exist should be handled.\n            Hide = Doesn't show up\n            Select = Selected by default\n            Disable = Disabled by default\n            \n            Only works if single target\n            ", enum_type=BuffHandlingType, default=BuffHandlingType.HIDE, tuning_group=GroupNames.PICKERTUNING), 'handle_invalid': TunableEnumFlags(description="\n            How buffs that can't be added should be handled.\n            Hide = Doesn't show up\n            Select = Selected by default\n            Disable = Disabled by default\n            \n            Only works if single target\n            ", enum_type=BuffHandlingType, default=BuffHandlingType.DISABLE, tuning_group=GroupNames.PICKERTUNING), 'buffs': TunableList(description='\n            The list of buffs available to select.  If empty will try all.\n            ', tunable=TunableTuple(buff=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.BUFF), pack_safe=True), buff_name=TunableLocalizedStringFactory(allow_none=True), buff_description=TunableLocalizedString(allow_none=True), buff_icon=TunableResourceKey(default=None, resource_types=sims4.resources.CompoundTypes.IMAGE)), tuning_group=GroupNames.PICKERTUNING), 'reason': OptionalTunable(description='\n            If set, specify a reason why the buff(s) were added.\n            ', tunable=TunableLocalizedString(description='\n                The reason the buffs were added. This will be displayed in the\n                buff tooltip.\n                '), tuning_group=GroupNames.PICKERTUNING), 'disabled_row_tooltip': OptionalTunable(description='\n            If set, specify a tooltip to indicate why the row is disabled\n            ', tunable=TunableLocalizedStringFactory(description='\n                The reason the row is disabled. This will be displayed as the \n                rows tooltip.\n                '), tuning_group=GroupNames.PICKERTUNING), 'continuations': TunableList(description='\n            List of continuations to push if a buff is actually selected.\n            ', tunable=TunableContinuation(), tuning_group=GroupNames.PICKERTUNING)}

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim)
        return True

    @classmethod
    def _buff_type_selection_gen(cls, target):
        if cls.buffs:
            for buff_info in cls.buffs:
                yield (buff_info.buff, buff_info.buff_name, buff_info.buff_icon, buff_info.buff_description)
        else:
            buff_manager = services.get_instance_manager(sims4.resources.Types.BUFF)
            for buff_type in buff_manager.types.values():
                yield (buff_type, buff_type.buff_name, buff_type.icon, buff_type.buff_description)

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        target = target if target is not DEFAULT else inst.target
        context = context if context is not DEFAULT else inst.context
        participants = inst_or_cls.get_participants(inst_or_cls.subject, sim=context.sim, target=target)
        if not participants:
            return
        single_sim = len(participants) == 1
        if single_sim or not inst_or_cls.is_add:
            logger.error('{} is trying to do a remove buff picker with multiple subjects', self)
        target = participants[0]
        for (buff_type, name, icon, description) in inst_or_cls._buff_type_selection_gen(target):
            is_enable = True
            is_selected = False
            row_tooltip = None
            if inst_or_cls.handle_existing & BuffPickerSuperInteraction.BuffHandlingType.HIDE:
                pass
            else:
                is_selected = True
                is_enable = False
                if inst_or_cls.handle_invalid & BuffPickerSuperInteraction.BuffHandlingType.HIDE:
                    pass
                else:
                    is_selected = True
                    is_enable = False
                    row_tooltip = inst_or_cls.disabled_row_tooltip
                    row = BasePickerRow(is_enable=is_enable, name=name(target.sim_info), icon=icon, tag=buff_type, row_description=description, row_tooltip=row_tooltip, is_selected=is_selected)
                    yield row

    def _on_buff_picker_choice_selected(self, choice_tag, **kwargs):
        if choice_tag is None:
            return
        for participant in self.get_participants(self.subject):
            if self.is_add:
                participant.add_buff_from_op(choice_tag, buff_reason=self.reason)
            else:
                participant.remove_buff_by_type(choice_tag)

    def on_choice_selected(self, choice_tag, **kwargs):
        self._on_buff_picker_choice_selected(choice_tag, **kwargs)
        for continuation in self.continuations:
            self.push_tunable_continuation(continuation)

    def on_multi_choice_selected(self, choice_tags, **kwargs):
        if not choice_tags:
            return
        for tag in choice_tags:
            self._on_buff_picker_choice_selected(tag, **kwargs)
        for continuation in self.continuations:
            self.push_tunable_continuation(continuation)
