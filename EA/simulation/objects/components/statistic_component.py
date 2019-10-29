from _collections import defaultdictfrom contextlib import contextmanagerimport collectionsimport itertoolsimport weakreffrom autonomy.autonomy_modifier import DEFAULT_AUTONOMY_RULEfrom autonomy.autonomy_outside_supression import OutsideSupressorfrom element_utils import build_critical_section_with_finallyfrom interactions.interaction_finisher import FinishingTypefrom objects.components import Component, componentmethod, types, componentmethod_with_fallback, ComponentPriorityfrom protocolbuffers import SimObjectAttributes_pb2 as persistence_protocolsfrom statistics.statistic_enums import StatisticLockActionfrom statistics.commodity import SkewerAlertTypeimport servicesimport sims4.logimport statistics.base_statistic_trackerimport statistics.commodity_trackerimport statistics.static_commodityimport statistics.statisticimport statistics.statistic_trackerimport uidfrom date_and_time import DateAndTimelogger = sims4.log.Logger('StatisticComponent')
class HasStatisticComponent:

    def _get_or_add_statistic_component(self):
        comp = self.get_component(types.STATISTIC_COMPONENT)
        if comp is None:
            self.add_dynamic_component(types.STATISTIC_COMPONENT)
            comp = self.get_component(types.STATISTIC_COMPONENT)
        return comp

    def add_statistic_component(self):
        statistic_compoenent = self._get_or_add_statistic_component()
        if statistic_compoenent is not None:
            statistic_compoenent.get_statistic_tracker()
            statistic_compoenent.get_commodity_tracker()
            statistic_compoenent.get_static_commodity_tracker()

    def get_tracker(self, stat):
        statistic_compoenent = self._get_or_add_statistic_component()
        if statistic_compoenent is not None:
            return statistic_compoenent.get_tracker(stat)

    @property
    def statistic_tracker(self):
        statistic_compoenent = self._get_or_add_statistic_component()
        if statistic_compoenent is not None:
            return statistic_compoenent.get_statistic_tracker()

    @property
    def commodity_tracker(self):
        statistic_compoenent = self._get_or_add_statistic_component()
        if statistic_compoenent is not None:
            return statistic_compoenent.get_commodity_tracker()

    @property
    def static_commodity_tracker(self):
        statistic_compoenent = self._get_or_add_statistic_component()
        if statistic_compoenent is not None:
            return statistic_compoenent.get_static_commodity_tracker()

class AutonomyModifierEntry:

    def __init__(self, autonomy_modifier):
        self._autonomy_modifier = autonomy_modifier
        self.statistic_modifiers = []
        self._statistic_multipliers = {}
        self.locked_statistics_skipped = None

    @property
    def autonomy_modifier(self):
        return self._autonomy_modifier

    def add_locked_statistics_skipped(self, stat_type):
        if self.locked_statistics_skipped is None:
            self.locked_statistics_skipped = []
        self.locked_statistics_skipped.append(stat_type)

    def clear_locked_statistics_skipped(self):
        if self.locked_statistics_skipped is None:
            return
        self.locked_statistics_skipped.clear()

    def has_multiplier(self, stat_type, tracker):
        if tracker in self._statistic_multipliers:
            return stat_type in self._statistic_multipliers[tracker]
        return False

    def add_multiplier(self, stat_type, tracker):
        if tracker not in self._statistic_multipliers:
            self._statistic_multipliers[tracker] = {stat_type}
            tracker.add_on_remove_callback(self._remove_stat_callback)
        else:
            self._statistic_multipliers[tracker].add(stat_type)

    def _remove_stat_callback(self, stat):
        new_stat_type = stat.stat_type
        for (tracker, stat_type_set) in self._statistic_multipliers.items():
            if new_stat_type in stat_type_set:
                stat_type_set.remove(new_stat_type)
                if not stat_type_set:
                    del self._statistic_multipliers[tracker]
                    return True
        return False

    def clear_multipliers(self):
        for tracker in self._statistic_multipliers:
            tracker.remove_on_remove_callback(self._remove_stat_callback)
        self._statistic_multipliers.clear()

class StatisticComponent(Component, component_name=types.STATISTIC_COMPONENT, allow_dynamic=True, persistence_key=persistence_protocols.PersistenceMaster.PersistableData.StatisticComponent, persistence_priority=ComponentPriority.PRIORITY_STATISTIC):

    def __init__(self, owner):
        super().__init__(owner)
        self._get_next_statistic_handle = uid.UniqueIdGenerator(1)
        self._statistic_modifiers = {}
        self._locked_commodities = {}
        self._relationship_score_multiplier_with_buff_on_target = defaultdict(list)
        self._object_tags_that_override_off_lot_autonomy_ref_count = collections.defaultdict(int)
        self._situation_type_social_score_multipliers = defaultdict(list)
        self._sit_posture_transition_penalties = []
        self._outside_object_supression = None
        self._commodity_tracker = None
        self._static_commodity_tracker = None
        self._statistic_tracker = None
        self._commodity_distress_refs = []
        self._commodities_added = {}
        self._interaction_modifiers = {}
        self._suspended_modifiers = {}
        self._interaction_score_modifier = []
        self._ui_skill_bar_suppression_count = 0

    def get_statistic_tracker(self):
        if self._statistic_tracker is None:
            self.create_statistic_tracker()
        return self._statistic_tracker

    def get_commodity_tracker(self):
        if self._commodity_tracker is None:
            self._commodity_tracker = statistics.commodity_tracker.CommodityTracker(self.owner)
        return self._commodity_tracker

    def get_static_commodity_tracker(self):
        if self._static_commodity_tracker is None:
            self._static_commodity_tracker = statistics.base_statistic_tracker.BaseStatisticTracker()
        return self._static_commodity_tracker

    @componentmethod_with_fallback(lambda : ())
    def get_all_stats_gen(self):
        if self._statistic_tracker is not None:
            yield from self._statistic_tracker
        if self._commodity_tracker is not None:
            yield from self._commodity_tracker
        if self._static_commodity_tracker is not None:
            yield from self._static_commodity_tracker

    @componentmethod_with_fallback(lambda _: False)
    def is_statistic_type_added_by_modifier(self, statistic_type):
        return statistic_type in self._commodities_added

    @componentmethod
    def create_statistic_tracker(self):
        self._statistic_tracker = statistics.statistic_tracker.StatisticTracker(self.owner)

    @componentmethod
    def get_tracker(self, stat):
        if stat is None:
            return
        stat = stat.stat_type
        if issubclass(stat, statistics.static_commodity.StaticCommodity):
            return self.get_static_commodity_tracker()
        if issubclass(stat, statistics.statistic.Statistic):
            return self.get_statistic_tracker()
        elif stat.continuous:
            return self.get_commodity_tracker()

    @componentmethod_with_fallback(lambda *_, **__: None)
    def get_stat_instance(self, stat_type, **kwargs):
        tracker = self.get_tracker(stat_type)
        if tracker is not None:
            return tracker.get_statistic(stat_type, **kwargs)

    @componentmethod
    def get_stat_value(self, stat_type):
        tracker = self.get_tracker(stat_type)
        if tracker is not None:
            return tracker.get_value(stat_type)

    @componentmethod
    def set_stat_value(self, stat_type, *args, **kwargs):
        tracker = self.get_tracker(stat_type)
        if tracker is not None:
            tracker.set_value(stat_type, *args, **kwargs)

    @componentmethod_with_fallback(lambda : False)
    def update_all_commodities(self):
        if self._commodity_tracker is not None:
            self._commodity_tracker.update_all_commodities()

    def _build_stat_sequence(self, participant, modifier, sequence):
        handle = None
        participant_ref = weakref.ref(participant)

        def _begin(_):
            nonlocal handle
            handle = participant.add_statistic_modifier(modifier, True)

        def _end(_):
            if handle:
                participant_deref = participant_ref()
                if participant_deref is not None:
                    return participant_deref.remove_statistic_modifier(handle)

        return build_critical_section_with_finally(_begin, sequence, _end)

    @componentmethod_with_fallback(lambda _, sequence: sequence)
    def add_modifiers_for_interaction(self, interaction, sequence):
        for modifier in self._interaction_modifiers:
            participants = interaction.get_participants(self._interaction_modifiers[modifier]._subject)
            for participant in participants:
                sequence = self._build_stat_sequence(participant, self._interaction_modifiers[modifier], sequence)
        return sequence

    @componentmethod_with_fallback(lambda _: None)
    def add_modifiers_for_skill(self, skill):
        for (handle, autonomy_modifier_entry) in self._statistic_modifiers.items():
            if handle not in self._suspended_modifiers:
                modifier = autonomy_modifier_entry.autonomy_modifier
                for (tag, mod) in modifier.skill_tag_modifiers.items():
                    if tag in skill.tags:
                        skill.add_statistic_multiplier(mod)

    @componentmethod_with_fallback(lambda *_, **__: None)
    def add_statistic_modifier(self, modifier, interaction_modifier=False, requested_handle=None):
        is_interaction_modifier = modifier._subject and not interaction_modifier
        if is_interaction_modifier and requested_handle in self._interaction_modifiers or requested_handle in self._statistic_modifiers:
            logger.warn('Trying to add a modifier with a requested handle that already exists. Generating a new handle. - trevorlindsey')
            requested_handle = None
        handle = self._get_next_statistic_handle() if requested_handle and requested_handle is None else requested_handle
        if is_interaction_modifier:
            self._interaction_modifiers[handle] = modifier
            return handle
        if interaction_modifier and any(modifier is autonomy_modifier_entry.autonomy_modifier for autonomy_modifier_entry in self._statistic_modifiers.values()):
            return
        autonomy_modifier_entry = AutonomyModifierEntry(modifier)
        for commodity_type in modifier.commodities_to_add:
            if commodity_type is None:
                logger.warn('{} has empty stat in commodities add list. Please fix tuning.', modifier)
            else:
                tracker = self.get_tracker(commodity_type)
                if not tracker.has_statistic(commodity_type):
                    tracker.add_statistic(commodity_type)
                if commodity_type not in self._commodities_added:
                    self._commodities_added[commodity_type] = 1
                else:
                    self._commodities_added[commodity_type] += 1
        if modifier.override_convergence is not None:
            for (commodity_to_override, convergence_value) in modifier.override_convergence.items():
                tracker = self.get_tracker(commodity_to_override)
                tracker.set_convergence(commodity_to_override, convergence_value)
        for stat_type in modifier.locked_stats_gen():
            action_on_lock = StatisticLockAction.DO_NOT_CHANGE_VALUE
            if not interaction_modifier:
                action_on_lock = StatisticLockAction.USE_BEST_VALUE_TUNING
            if not self.lock_statistic(stat_type, action_on_lock):
                autonomy_modifier_entry.add_locked_statistics_skipped(stat_type)
        if modifier.decay_modifiers:
            for (stat_type, decay_modifiers) in modifier.decay_modifiers.items():
                stat = self._commodity_tracker.get_statistic(stat_type, stat_type.add_if_not_in_tracker)
                if stat is not None:
                    stat.add_decay_rate_modifier(decay_modifiers)
                    stat.send_commodity_progress_msg()
        if modifier.decay_modifier_by_category:
            modifier_categories = modifier.decay_modifier_by_category
            for stat_instance in self._commodity_tracker:
                categories = stat_instance.get_categories() & modifier_categories.keys()
                if not categories:
                    pass
                else:
                    for category in categories:
                        value = modifier_categories[category]
                        stat_instance.add_decay_rate_modifier(value)
                    stat_instance.send_commodity_progress_msg()
        if modifier.statistic_modifiers:
            for (stat_type, statistic_modifier) in modifier.statistic_modifiers.items():
                tracker = self.get_tracker(stat_type)
                stat = tracker.get_statistic(stat_type, stat_type.add_if_not_in_tracker)
                if stat is not None and stat_type not in self._locked_commodities:
                    stat.add_statistic_modifier(statistic_modifier)
                    autonomy_modifier_entry.statistic_modifiers.append(stat_type)
        if modifier.relationship_score_multiplier_with_buff_on_target is not None:
            for (buff_type, multiplier) in modifier.relationship_score_multiplier_with_buff_on_target.items():
                self._relationship_score_multiplier_with_buff_on_target[buff_type].append(multiplier)
        if modifier.situation_type_social_score_multiplier is not None:
            for (situation_type, multiplier) in modifier.situation_type_social_score_multiplier.items():
                self._situation_type_social_score_multipliers[situation_type].append(multiplier)
        if modifier.transition_from_sit_posture_penalty is not None:
            self._sit_posture_transition_penalties.append(modifier.transition_from_sit_posture_penalty)
        if modifier.supress_outside_objects is not None:
            self._add_outside_suppression(modifier)
        if modifier.outside_objects_multiplier is not None:
            self._add_outside_multiplier(modifier)
        if modifier.interaction_score_modifier is not None:
            for interaction_score_modifier in modifier.interaction_score_modifier:
                self._interaction_score_modifier.append(interaction_score_modifier)
        if modifier.statistic_multipliers:
            for (stat_type, statistic_multiplier) in modifier.statistic_multipliers.items():
                tracker = self.get_tracker(stat_type)
                stat = tracker.get_statistic(stat_type, stat_type.add_if_not_in_tracker)
                if stat is not None:
                    stat.add_statistic_multiplier(statistic_multiplier)
                    autonomy_modifier_entry.add_multiplier(stat_type, tracker)
        if modifier.object_tags_that_override_off_lot_autonomy is not None:
            for tag in modifier.object_tags_that_override_off_lot_autonomy:
                self._object_tags_that_override_off_lot_autonomy_ref_count[tag] += 1
        owner = self.owner
        if owner.is_sim:
            sims = (owner,)
        elif hasattr(owner, 'get_users'):
            sims = owner.get_users(sims_only=True)
        else:
            sims = ()
        for sim in sims:
            if sim is None:
                pass
            else:
                sim_instance = sim.get_sim_instance() if hasattr(sim, 'get_sim_instance') else sim
                if modifier.super_affordance_suppress_on_add:
                    for interaction in tuple(itertools.chain(sim_instance.si_state, sim_instance.queue)):
                        if modifier.affordance_suppressed(sim_instance, interaction):
                            interaction.cancel(FinishingType.INTERACTION_INCOMPATIBILITY, cancel_reason_msg='Modifier suppression')
                for (skill, mod) in self._get_skill_modifiers(sim, modifier):
                    skill.add_statistic_multiplier(mod)
                sim.relationship_tracker.add_relationship_multipliers(handle, modifier.relationship_multipliers)
        self._statistic_modifiers[handle] = autonomy_modifier_entry
        return handle

    def apply_statistic_modifiers_on_stat(self, stat):
        stat_type = stat.stat_type
        tracker = self.get_tracker(stat)
        for modifier_entry in self._statistic_modifiers.values():
            modifier = modifier_entry.autonomy_modifier
            if modifier.decay_modifiers and stat_type in modifier.decay_modifiers:
                stat.add_decay_rate_modifier(modifier.decay_modifiers[stat_type])
                stat.send_commodity_progress_msg()
            if modifier.decay_modifier_by_category:
                modifier_categories = modifier.decay_modifier_by_category
                categories = stat.get_categories() & modifier_categories.keys()
                if not categories:
                    pass
                else:
                    for category in categories:
                        value = modifier_categories[category]
                        stat.add_decay_rate_modifier(value)
                    stat.send_commodity_progress_msg()
                    if modifier.statistic_multipliers is not None:
                        statistic_multiplier = modifier.statistic_multipliers.get(stat_type, None)
                        if statistic_multiplier is not None and not modifier_entry.has_multiplier(stat_type, tracker):
                            stat.add_statistic_multiplier(statistic_multiplier)
                            modifier_entry.add_multiplier(stat_type, tracker)
            if modifier.statistic_multipliers is not None:
                statistic_multiplier = modifier.statistic_multipliers.get(stat_type, None)
                if statistic_multiplier is not None and not modifier_entry.has_multiplier(stat_type, tracker):
                    stat.add_statistic_multiplier(statistic_multiplier)
                    modifier_entry.add_multiplier(stat_type, tracker)

    def add_statistic_multiplier(self, modifier, subject):
        if modifier.statistic_multipliers:
            for (stat_type, statistic_multiplier) in modifier.statistic_multipliers.items():
                if subject is not None and subject != statistic_multiplier.subject:
                    pass
                else:
                    tracker = self.get_tracker(stat_type)
                    stat = tracker.get_statistic(stat_type, stat_type.add_if_not_in_tracker)
                    if stat is not None:
                        stat.add_statistic_multiplier(statistic_multiplier)

    def _add_outside_suppression(self, modifier):
        if not self.owner.is_sim:
            logger.error('Adding an outside suppression to object {}, outside suppressors will only work on Sims.', self.owner, owner='camilogarcia')
            return
        if self._outside_object_supression is None:
            self._outside_object_supression = OutsideSupressor()
        if modifier.supress_outside_objects:
            self._outside_object_supression.add_lock_counter()
        else:
            self._outside_object_supression.add_unlock_counter()

    def _remove_outside_suppression(self, modifier):
        if self._outside_object_supression is not None:
            if modifier.supress_outside_objects:
                self._outside_object_supression.remove_lock_counter()
            else:
                self._outside_object_supression.remove_unlock_counter()
        else:
            logger.error('Attempting to remove an outside suppressor out of object {} that never got a supressor added', self.owner, owner='camilogarcia')

    def _add_outside_multiplier(self, modifier):
        if not self.owner.is_sim:
            logger.error('Adding an outside multiplier to object {}, outside multiplier will only work on Sims.', self.owner, owner='nabaker')
            return
        if self._outside_object_supression is None:
            self._outside_object_supression = OutsideSupressor()
        self._outside_object_supression.add_multiplier(modifier.outside_objects_multiplier)

    def _remove_outside_multiplier(self, modifier):
        if self._outside_object_supression is not None:
            self._outside_object_supression.remove_multiplier(modifier.outside_objects_multiplier)
        else:
            logger.error('Attempting to remove an outside multiplier out of object {} that never got a multiplier added', self.owner, owner='nabaker')

    @classmethod
    def _get_skill_modifiers(cls, sim, modifier):
        if not modifier.skill_tag_modifiers:
            return []
        tag_to_skills = defaultdict(set)
        for skill in sim.all_skills():
            for tag in skill.tags:
                tag_to_skills[tag].add(skill)
        if not tag_to_skills:
            return []
        skill_mod_pairs = []
        for (tag, mod) in modifier.skill_tag_modifiers.items():
            for skill in tag_to_skills.get(tag, tuple()):
                skill_mod_pairs.append((skill, mod))
        return skill_mod_pairs

    @componentmethod_with_fallback(lambda *_, **__: False)
    def remove_statistic_modifier(self, handle):
        if handle in self._interaction_modifiers:
            del self._interaction_modifiers[handle]
            return True
        if handle in self._suspended_modifiers:
            del self._suspended_modifiers[handle]
            return True
        if handle in self._statistic_modifiers:
            if self.owner.id == 0:
                return True
            else:
                autonomy_modifier_entry = self._statistic_modifiers[handle]
                modifier = autonomy_modifier_entry.autonomy_modifier
                for stat_type in modifier.locked_stats_gen():
                    if autonomy_modifier_entry.locked_statistics_skipped is not None and stat_type in autonomy_modifier_entry.locked_statistics_skipped:
                        pass
                    else:
                        self.unlock_statistic(stat_type, auto_satisfy=modifier.autosatisfy_on_unlock)
                autonomy_modifier_entry.clear_locked_statistics_skipped()
                if modifier.decay_modifiers:
                    for (stat_type, decay_modifier) in modifier.decay_modifiers.items():
                        stat = self._commodity_tracker.get_statistic(stat_type)
                        if stat is not None:
                            stat.remove_decay_rate_modifier(decay_modifier)
                            stat.send_commodity_progress_msg()
                if modifier.decay_modifier_by_category:
                    modifier_categories = modifier.decay_modifier_by_category
                    for stat_instance in self._commodity_tracker:
                        categories = stat_instance.get_categories() & modifier_categories.keys()
                        if not categories:
                            pass
                        else:
                            for category in categories:
                                value = modifier_categories[category]
                                stat_instance.remove_decay_rate_modifier(value)
                            stat_instance.send_commodity_progress_msg()
                if modifier.statistic_modifiers:
                    for (stat_type, statistic_modifier) in modifier.statistic_modifiers.items():
                        if stat_type not in autonomy_modifier_entry.statistic_modifiers:
                            pass
                        else:
                            tracker = self.get_tracker(stat_type)
                            stat = tracker.get_statistic(stat_type)
                            if stat is not None:
                                stat.remove_statistic_modifier(statistic_modifier)
                            elif stat_type.add_if_not_in_tracker and not stat_type.remove_on_convergence:
                                logger.error("Attempting to remove a statistic modifier for a commodity that doesn't exist on object {}: {}", self.owner, stat_type)
                autonomy_modifier_entry.statistic_modifiers.clear()
                if modifier.statistic_multipliers:
                    for (stat_type, statistic_multiplier) in modifier.statistic_multipliers.items():
                        tracker = self.get_tracker(stat_type)
                        if not autonomy_modifier_entry.has_multiplier(stat_type, tracker):
                            pass
                        else:
                            stat = tracker.get_statistic(stat_type)
                            if stat is not None:
                                stat.remove_statistic_multiplier(statistic_multiplier)
                            elif stat_type.add_if_not_in_tracker:
                                logger.error("Attempting to remove a statistic multiplier for a commodity that doesn't exist on object {}: {}", self.owner, stat_type)
                autonomy_modifier_entry.clear_multipliers()
                if modifier.object_tags_that_override_off_lot_autonomy is not None:
                    for tag in modifier.object_tags_that_override_off_lot_autonomy:
                        self._object_tags_that_override_off_lot_autonomy_ref_count[tag] -= 1
                        if self._object_tags_that_override_off_lot_autonomy_ref_count[tag] <= 0:
                            del self._object_tags_that_override_off_lot_autonomy_ref_count[tag]
                if self.owner.is_sim:
                    self.owner.relationship_tracker.remove_relationship_multipliers(handle)
                    for (skill, mod) in self._get_skill_modifiers(self.owner, modifier):
                        skill.remove_statistic_multiplier(mod)
                for commodity_type in modifier.commodities_to_add:
                    if commodity_type in self._commodities_added:
                        if self._commodities_added[commodity_type] > 1:
                            self._commodities_added[commodity_type] -= 1
                        else:
                            del self._commodities_added[commodity_type]
                            tracker = self.get_tracker(commodity_type)
                            tracker.remove_statistic(commodity_type)
                if modifier.relationship_score_multiplier_with_buff_on_target is not None:
                    for (buff_type, multiplier) in modifier.relationship_score_multiplier_with_buff_on_target.items():
                        self._relationship_score_multiplier_with_buff_on_target[buff_type].remove(multiplier)
                if modifier.situation_type_social_score_multiplier is not None:
                    for (situation_type, multiplier) in modifier.situation_type_social_score_multiplier.items():
                        self._situation_type_social_score_multipliers[situation_type].remove(multiplier)
                if modifier.transition_from_sit_posture_penalty is not None:
                    self._sit_posture_transition_penalties.remove(modifier.transition_from_sit_posture_penalty)
                if modifier.supress_outside_objects is not None:
                    self._remove_outside_suppression(modifier)
                if modifier.outside_objects_multiplier is not None:
                    self._remove_outside_multiplier(modifier)
                if modifier.interaction_score_modifier is not None:
                    for interaction_score_modifier in modifier.interaction_score_modifier:
                        self._interaction_score_modifier.remove(interaction_score_modifier)
                if modifier.override_convergence is not None:
                    for commodity_to_override in modifier.override_convergence.keys():
                        tracker = self.get_tracker(commodity_to_override)
                        tracker.reset_convergence(commodity_to_override)
                del self._statistic_modifiers[handle]
                return True
        return False

    @componentmethod
    def get_statistic_modifier(self, handle):
        bad_id = self.owner.id == 0
        if handle in self._statistic_modifiers:
            if bad_id:
                return
            return self._statistic_modifiers[handle].autonomy_modifier
        if handle in self._suspended_modifiers:
            if bad_id:
                return
            else:
                return self._suspended_modifiers[handle]

    @componentmethod
    def get_statistic_modifiers_gen(self):
        yield from self._statistic_modifiers.items()

    @componentmethod
    def suspend_statistic_modifier(self, handle):
        if handle in self._suspended_modifiers:
            return (False, 'Trying to double-suspend a statistic modifier')
        if handle not in self._statistic_modifiers:
            return (False, None)
        autonomy_modifier = self._statistic_modifiers[handle].autonomy_modifier
        self.remove_statistic_modifier(handle)
        self._suspended_modifiers[handle] = autonomy_modifier
        return (True, None)

    @componentmethod
    def resume_statistic_modifier(self, handle):
        if handle in self._suspended_modifiers:
            self.add_statistic_modifier(modifier=self._suspended_modifiers[handle], requested_handle=handle)
            del self._suspended_modifiers[handle]

    @componentmethod
    def get_score_multiplier(self, stat_type):
        score_multiplier = 1
        for autonomy_modifier_entry in self._statistic_modifiers.values():
            score_multiplier *= autonomy_modifier_entry.autonomy_modifier.get_score_multiplier(stat_type)
        return score_multiplier

    @componentmethod
    def get_added_monetary_value(self):
        added_monetary_value = 0
        for statistic in self.get_statistic_tracker().get_monetary_value_statistics():
            added_monetary_value += statistic.get_value()
        return added_monetary_value

    @componentmethod_with_fallback(lambda *_, **__: 1)
    def get_stat_multiplier(self, stat_type, participant_type):
        score_multiplier = 1
        for autonomy_modifier_entry in self._statistic_modifiers.values():
            score_multiplier *= autonomy_modifier_entry.autonomy_modifier.get_stat_multiplier(stat_type, participant_type)
        for modifier in self._interaction_modifiers.values():
            score_multiplier *= modifier.get_stat_multiplier(stat_type, participant_type)
        return score_multiplier

    @componentmethod_with_fallback(lambda *_, **__: False)
    def check_affordance_for_suppression(self, sim, aop, user_directed):
        for autonomy_modifier_entry in self._statistic_modifiers.values():
            if autonomy_modifier_entry.autonomy_modifier.affordance_suppressed(sim, aop, user_directed):
                return True
        for autonomy_modifier in self._suspended_modifiers.values():
            if autonomy_modifier.affordance_suppressed(sim, aop, user_directed):
                return True
        return False

    @componentmethod_with_fallback(lambda _: False)
    def is_in_locked_commodities(self, stat):
        if type(stat) in self._locked_commodities:
            return True
        return False

    @componentmethod_with_fallback(lambda _: False)
    def is_locked(self, stat):
        for autonomy_modifier_entry in self._statistic_modifiers.values():
            if autonomy_modifier_entry.autonomy_modifier.is_locked(type(stat)):
                return True
        if type(stat) in self._locked_commodities:
            return True
        for modifier in self._suspended_modifiers.values():
            if modifier.is_locked(type(stat)):
                return True
        return False

    @componentmethod_with_fallback(lambda _: False)
    def lock_statistic(self, stat_type, action_on_lock):
        if stat_type in self._locked_commodities:
            self._locked_commodities[stat_type] += 1
        else:
            stat = self._commodity_tracker.get_statistic(stat_type, stat_type.add_if_not_in_tracker)
            if stat is not None:
                stat.on_lock(action_on_lock)
                self._locked_commodities[stat_type] = 1
            else:
                return False
        return True

    @componentmethod_with_fallback(lambda _: False)
    def unlock_statistic(self, stat_type, auto_satisfy=True):
        if stat_type in self._locked_commodities:
            if self._locked_commodities[stat_type] <= 1:
                stat = self._commodity_tracker.get_statistic(stat_type)
                if stat is not None:
                    stat.on_unlock(auto_satisfy=auto_satisfy)
                else:
                    logger.warn("Attempting to unlock commodity that doesn't exist on object {},({}) : {}", self.owner, self.owner.id, stat_type)
                del self._locked_commodities[stat_type]
            else:
                self._locked_commodities[stat_type] -= 1
        else:
            logger.error("Locked commodity doesn't exist in the _locked_commodities dict: object {}, stat {}", self.owner, stat_type)

    @componentmethod_with_fallback(lambda _: None)
    def get_relationship_score_multiplier_for_buff_on_target(self):
        return self._relationship_score_multiplier_with_buff_on_target

    @componentmethod_with_fallback(lambda _: None)
    def get_situation_type_social_score_multiplier(self):
        return self._situation_type_social_score_multipliers

    @componentmethod_with_fallback(lambda _: [])
    def get_sit_posture_transition_penalties(self):
        return self._sit_posture_transition_penalties

    @componentmethod_with_fallback(lambda _: (False, 1.0))
    def get_outside_object_score_modification(self):
        weather_service = services.weather_service()
        if weather_service is not None:
            multiplier = weather_service.get_current_precipitation_autonomy_multiplier(self.owner)
        else:
            multiplier = 1.0
        if self._outside_object_supression is not None:
            return (self._outside_object_supression.is_not_allowed_outside(), multiplier*self._outside_object_supression.outside_multiplier)
        return (False, multiplier)

    @componentmethod_with_fallback(lambda _: [])
    def get_interaction_score_modifier(self, interaction):
        return self._interaction_score_modifier

    @componentmethod
    def is_scorable(self, stat_type):
        for autonomy_modifier_entry in self._statistic_modifiers.values():
            if not autonomy_modifier_entry.autonomy_modifier.is_scored(stat_type):
                return False
        return True

    @componentmethod_with_fallback(lambda _: False)
    def object_tags_override_off_lot_autonomy_ref_count(self, object_tag_list):
        for tag in object_tag_list:
            if tag in self._object_tags_that_override_off_lot_autonomy_ref_count:
                return True
        return False

    def _get_off_lot_autonomy_rules(self):
        rules = []
        for autonomy_modifier_entry in self._statistic_modifiers.values():
            rule = autonomy_modifier_entry.autonomy_modifier.off_lot_autonomy_rule
            if rule is not None:
                rules.append(rule)
        return rules or [DEFAULT_AUTONOMY_RULE]

    @componentmethod
    def get_off_lot_autonomy_rule(self):
        return max(self._get_off_lot_autonomy_rules(), key=lambda rule: rule.rule)

    def on_initial_startup(self):
        if self._commodity_tracker is not None:
            self._commodity_tracker.on_initial_startup()
        if self._statistic_tracker is not None:
            self._statistic_tracker.on_initial_startup()
        if self._static_commodity_tracker is not None:
            self._static_commodity_tracker.on_initial_startup()

    def on_remove(self):
        if self._commodity_tracker is not None:
            self._commodity_tracker.destroy()
        if self._statistic_tracker is not None:
            self._statistic_tracker.destroy()
        if self._static_commodity_tracker is not None:
            self._static_commodity_tracker.destroy()

    def on_lod_update(self, old_lod, new_lod):
        if self._commodity_tracker is not None:
            self._commodity_tracker.on_lod_update(old_lod, new_lod)
        if self._statistic_tracker is not None:
            self._statistic_tracker.on_lod_update(old_lod, new_lod)
        if self._static_commodity_tracker is not None:
            self._static_commodity_tracker.on_lod_update(old_lod, new_lod)

    def save(self, persistence_master_message):
        persistable_data = persistence_protocols.PersistenceMaster.PersistableData()
        persistable_data.type = persistence_protocols.PersistenceMaster.PersistableData.StatisticComponent
        saved_any_data = False
        if self._statistic_tracker is not None:
            statistic_data = persistable_data.Extensions[persistence_protocols.PersistableStatisticsTracker.persistable_data]
            regular_statistics = self._statistic_tracker.save()
            statistic_data.statistics.extend(regular_statistics)
            if regular_statistics:
                saved_any_data = True
        if self._commodity_tracker is not None:
            commodity_data = persistable_data.Extensions[persistence_protocols.PersistableCommodityTracker.persistable_data]
            skill_data = persistable_data.Extensions[persistence_protocols.PersistableSkillTracker.persistable_data]
            ranked_statistic_data = persistable_data.Extensions[persistence_protocols.PersistableRankedStatisticTracker.persistable_data]
            (commodities, skill_statistics, ranked_statistics) = self._commodity_tracker.save()
            commodity_data.commodities.extend(commodities)
            commodity_data.time_of_last_save = services.time_service().sim_now.absolute_ticks()
            skill_data.skills.extend(skill_statistics)
            ranked_statistic_data.ranked_statistics.extend(ranked_statistics)
            if commodities or skill_statistics or ranked_statistics:
                saved_any_data = True
        if saved_any_data:
            persistence_master_message.data.extend([persistable_data])

    def load(self, statistic_component_message):
        statistics_to_load = statistic_component_message.Extensions[persistence_protocols.PersistableStatisticsTracker.persistable_data].statistics
        if statistics_to_load:
            self.get_statistic_tracker()
            self._statistic_tracker.load(statistics_to_load)
        if self._commodity_tracker is not None:
            commodity_data = statistic_component_message.Extensions[persistence_protocols.PersistableCommodityTracker.persistable_data]
            self._commodity_tracker.load(commodity_data.commodities)
            skill_component_data = statistic_component_message.Extensions[persistence_protocols.PersistableSkillTracker.persistable_data]
            self._commodity_tracker.load(skill_component_data.skills)
            ranked_statistic_data = statistic_component_message.Extensions[persistence_protocols.PersistableRankedStatisticTracker.persistable_data]
            self._commodity_tracker.load(ranked_statistic_data.ranked_statistics)
            if commodity_data.time_of_last_save > 0:
                time_of_last_save = DateAndTime(commodity_data.time_of_last_save)
                for commodity in tuple(self._commodity_tracker):
                    if commodity.needs_fixup_on_load_for_objects():
                        commodity.fixup_for_time(time_of_last_save, self.is_locked(commodity), decay_enabled=True)

    @componentmethod
    def is_in_distress(self):
        return len(self._commodity_distress_refs) > 0

    @componentmethod
    def enter_distress(self, commodity):
        index = 0
        for commodity_ref in self._commodity_distress_refs:
            if commodity == commodity_ref:
                return
            if commodity.commodity_distress.priority < commodity_ref.commodity_distress.priority:
                self._commodity_distress_refs.insert(index, commodity)
                return
            index += 1
        self._commodity_distress_refs.append(commodity)

    @componentmethod
    def exit_distress(self, commodity):
        if commodity in self._commodity_distress_refs:
            self._commodity_distress_refs.remove(commodity)
        self.update_skewer_alert(commodity)

    def update_skewer_alert(self, commodity):
        if commodity.commodity_distress.skewer_alert is not None:
            alert_type = None
            priority = 0
            for commodity_ref in self._commodity_distress_refs:
                if not alert_type is None:
                    if priority <= commodity_ref.commodity_distress.priority and commodity_ref.commodity_distress.skewer_alert is not None:
                        alert_type = commodity_ref.commodity_distress.skewer_alert
                        priority = commodity_ref.commodity_distress.priority
                alert_type = commodity_ref.commodity_distress.skewer_alert
                priority = commodity_ref.commodity_distress.priority
            if alert_type is None:
                alert_type = SkewerAlertType.NONE
            commodity.create_and_send_sim_alert_update_msg(self.owner, alert_type)

    @contextmanager
    @componentmethod
    def skill_bar_suppression(self, suppress_skill_bars):
        self._ui_skill_bar_suppression_count += 1
        try:
            yield None
        finally:
            if suppress_skill_bars:
                self._ui_skill_bar_suppression_count -= 1

    @componentmethod
    def with_skill_bar_suppression(self, sequence=()):

        def _start_suppression(_):
            self._ui_skill_bar_suppression_count += 1

        def _end_suppression(_):
            self._ui_skill_bar_suppression_count -= 1

        sequence = build_critical_section_with_finally(_start_suppression, sequence, _end_suppression)
        return sequence

    @componentmethod
    def is_skill_bar_suppressed(self):
        if self._ui_skill_bar_suppression_count:
            return True
        return False
