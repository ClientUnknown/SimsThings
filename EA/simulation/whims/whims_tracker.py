from _functools import reduceimport collectionsimport operatorfrom protocolbuffers import DistributorOps_pb2, Sims_pb2, GameplaySaveData_pb2from protocolbuffers.DistributorOps_pb2 import Operation, SetWhimBucksfrom date_and_time import create_time_span, TimeSpanfrom distributor.ops import distributor, GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom event_testing import test_eventsfrom interactions.liability import Liabilityfrom objects import ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZEDfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims4.math import Thresholdfrom sims4.tuning.tunable import TunableReference, TunableTuple, Tunable, TunableEnumEntry, TunableMapping, TunablePercent, TunableSimMinute, HasTunableFactory, OptionalTunable, AutoFactoryInitfrom sims4.utils import classpropertyfrom singletons import EMPTY_SET, DEFAULTfrom situations.situation_serialization import GoalSeedlingimport alarmsimport enumimport event_testingimport servicesimport sims4.logimport sims4.randomimport telemetry_helperimport uidTELEMETRY_GROUP_WHIMS = 'WHIM'TELEMETRY_HOOK_WHIM_EVENT = 'WEVT'TELEMETRY_WHIM_EVENT_TYPE = 'wtyp'TELEMETRY_WHIM_GUID = 'wgui'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_WHIMS)logger = sims4.log.Logger('Whims', default_owner='jjacobson')
class HideWhimsLiability(Liability, HasTunableFactory, AutoFactoryInit):
    LIABILITY_TOKEN = 'HideWhimsLiability'
    FACTORY_TUNABLES = {'_reset_time': OptionalTunable(description='\n            If enabled, when this liability is released, all non-locked whims\n            will be reset if this liability exists for longer than this time.\n            ', tunable=TunableSimMinute(description='\n                The amount of time that needs to pass on liability release that\n                the whims will be reset as well as unhidden.\n                ', default=1, minimum=1))}

    def __init__(self, interaction, **kwargs):
        super().__init__(**kwargs)
        self._starting_time_stamp = None
        self._sim_info = interaction.sim.sim_info

    def on_run(self):
        if self._starting_time_stamp is not None:
            return
        if self._sim_info.whim_tracker is None:
            return
        self._starting_time_stamp = services.time_service().sim_now
        self._sim_info.whim_tracker.hide_whims()

    def release(self):
        if self._starting_time_stamp is None:
            return
        if self._sim_info.whim_tracker is None:
            return
        should_reset = False
        if self._reset_time is not None:
            current_time = services.time_service().sim_now
            elapsed_time = current_time - self._starting_time_stamp
            should_reset = elapsed_time > create_time_span(minutes=self._reset_time)
        self._sim_info.whim_tracker.show_whims(reset=should_reset)

class TelemetryWhimEvents(enum.Int, export=False):
    CANCELED = 0
    NO_LONGER_AVAILABLE = 1
    COMPLETED = 2
    ADDED = 4

class _ActiveWhimData:

    def __init__(self):
        self.whim = None
        self.whimset = None
        self.anti_thrashing_alarm_handle = None

    def __repr__(self):
        return 'ActiveWhimData(Whim: {}, Whimset: {}'.format(self.whim, self.whimset)
_ActiveWhimsetData = collections.namedtuple('_ActiveWhimsetData', ['target', 'callback_data'])
class WhimsTracker(SimInfoTracker):
    MAX_GOALS = 2
    EMOTIONAL_WHIM_PRIORITY = 1

    class WhimAwardTypes(enum.Int):
        MONEY = 0
        BUFF = 1
        OBJECT = 2
        TRAIT = 3
        CASPART = 4

    SATISFACTION_STORE_ITEMS = TunableMapping(description='\n        A list of Sim based Tunable Rewards offered from the Satisfaction Store.\n        ', key_type=TunableReference(description='\n            The reward to offer.\n            ', manager=services.get_instance_manager(sims4.resources.Types.REWARD), pack_safe=True), value_type=TunableTuple(description='\n            A collection of data about this reward.\n            ', cost=Tunable(tunable_type=int, default=100), award_type=TunableEnumEntry(WhimAwardTypes, WhimAwardTypes.MONEY)))
    WHIM_THRASHING_CHANCE = TunablePercent(description='\n        The tunable percent chance that the activation of a whimset will try\n        and cancel a whim of a lower whimset priority as long as that whim is\n        not locked, and not on the anti thrashing cooldown.\n        ', default=50)
    WHIM_ANTI_THRASHING_TIME = TunableSimMinute(description='\n        The amount of time in sim minutes that a whim will not be overwritten\n        by another whimset becoming active.  This is essentially a period of\n        time after a whim becomes active that it is considered locked.\n        ', default=5)

    @classproperty
    def max_whims(cls):
        return WhimsTracker.MAX_GOALS + 1

    @classproperty
    def emotional_whim_index(cls):
        return WhimsTracker.MAX_GOALS

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._goal_id_generator = uid.UniqueIdGenerator(1)
        self._active_whimsets_data = {}
        self._active_whims = [_ActiveWhimData() for _ in range(self.max_whims)]
        self._hidden = False
        self._cooldown_alarms = {}
        self._whim_goal_proto = None
        self._completed_goals = {}
        self._test_results_map = {}
        self._goals_dirty = True
        self._score_multipliers = []

    def start_whims_tracker(self):
        self._offer_whims()

    def activate_whimset_from_objective_completion(self, whimset):
        self._activate_whimset(whimset)
        self._try_and_thrash_whims(whimset.activated_priority)

    def validate_goals(self):
        sim = self._sim_info.get_sim_instance()
        if sim is None:
            return
        for whim_data in self._active_whims:
            whim = whim_data.whim
            if whim is None:
                pass
            else:
                required_sim_info = whim.get_required_target_sim_info()
                if not whim.can_be_given_as_goal(sim, None, inherited_target_sim_info=required_sim_info):
                    self._remove_whim(whim, TelemetryWhimEvents.NO_LONGER_AVAILABLE)
        self._offer_whims()

    def whims_and_parents_gen(self):
        for whim_data in self._active_whims:
            if whim_data.whim is None:
                pass
            else:
                yield (whim_data.whim, whim_data.whimset)

    def get_active_whimsets(self):
        whim_sets = set(self._active_whimsets_data.keys())
        if self._sim_info.primary_aspiration is not None and self._sim_info.primary_aspiration.whim_set is not None:
            whim_sets.add(self._sim_info.primary_aspiration.whim_set)
        current_venue = services.get_current_venue()
        if current_venue.whim_set is not None:
            whim_sets.add(current_venue.whim_set)
        for trait in self._sim_info.trait_tracker:
            if trait.whim_set is not None:
                whim_sets.add(trait.whim_set)
        season_service = services.season_service()
        if season_service is not None:
            season_content = season_service.season_content
            if season_content.whim_set is not None:
                whim_sets.add(season_content.whim_set)
        object_manager = services.object_manager()
        whim_sets.update(object_manager.active_whim_sets)
        zone_director = services.venue_service().get_zone_director()
        open_street_director = zone_director.open_street_director
        if open_street_director is not None and open_street_director.whim_set:
            whim_sets.add(open_street_director.whim_set)
        return whim_sets

    def get_active_whim_data(self):
        return tuple(self._active_whims)

    def get_whimset_target(self, whimset):
        whimset_data = self._active_whimsets_data.get(whimset)
        if whimset_data is None:
            return
        return whimset_data.target

    def get_emotional_whimset(self):
        return self._sim_mood().whim_set

    def refresh_emotion_whim(self):
        emotional_whim = self._active_whims[self.emotional_whim_index].whim
        if emotional_whim is not None:
            self._remove_whim(emotional_whim, TelemetryWhimEvents.NO_LONGER_AVAILABLE)
        self._offer_whims()

    def get_priority(self, whimset):
        return whimset.get_priority(self._sim_info)

    def clean_up(self):
        for whim_data in self._active_whims:
            whim = whim_data.whim
            if whim is not None:
                whim.destroy()
            if whim_data.anti_thrashing_alarm_handle is not None:
                alarms.cancel_alarm(whim_data.anti_thrashing_alarm_handle)
        self._active_whims.clear()
        for alarm_handle in self._cooldown_alarms.values():
            alarms.cancel_alarm(alarm_handle)
        self._cooldown_alarms.clear()
        self._test_results_map.clear()

    def refresh_whim(self, whim_type):
        whim = self._get_whim_by_whim_type(whim_type)
        if whim is None:
            logger.error('Trying to refresh whim type {} when there are no active whims of that type.', whim_type)
            return
        self._remove_whim(whim, TelemetryWhimEvents.CANCELED)
        self._offer_whims(prohibited_whims={whim_type})

    def toggle_whim_lock(self, whim_type):
        whim = self._get_whim_by_whim_type(whim_type)
        if whim is None:
            logger.error('Trying to toggle the locked status of whim type {} when there are no active whims of that type.', whim_type)
            return
        whim.toggle_locked_status()
        self._goals_dirty = True
        self._send_goals_update()

    def hide_whims(self):
        if self._hidden:
            logger.error('Trying to hide whims when they are already hidden.')
            return
        self._hidden = True
        self._goals_dirty = True
        self._send_goals_update()

    def show_whims(self, reset=False):
        if not self._hidden:
            logger.error("Trying to show whims when they aren't hidden.")
            return
        self._hidden = False
        self._goals_dirty = True
        if reset:
            self.refresh_whims()
        self._send_goals_update()

    def refresh_whims(self):
        prohibited_whims = set()
        for whim_data in self._active_whims:
            whim = whim_data.whim
            if whim is not None:
                if whim.locked:
                    pass
                else:
                    prohibited_whims.add(type(whim))
                    self._remove_whim(whim, TelemetryWhimEvents.CANCELED)
        self._offer_whims(prohibited_whims=prohibited_whims)

    def add_score_multiplier(self, multiplier):
        self._score_multipliers.append(multiplier)
        self._goals_dirty = True
        self._send_goals_update()

    def get_score_multiplier(self):
        return reduce(operator.mul, self._score_multipliers, 1)

    def get_score_for_whim(self, score):
        return int(score*self.get_score_multiplier())

    def remove_score_multiplier(self, multiplier):
        if multiplier in self._score_multipliers:
            self._score_multipliers.remove(multiplier)
        self._goals_dirty = True
        self._send_goals_update()

    def purchase_whim_award(self, reward_guid64):
        reward_instance = services.get_instance_manager(sims4.resources.Types.REWARD).get(reward_guid64)
        award = reward_instance
        cost = self.SATISFACTION_STORE_ITEMS[reward_instance].cost
        if self._sim_info.get_whim_bucks() < cost:
            logger.debug('Attempting to purchase a whim award with insufficient funds: Cost: {}, Funds: {}', cost, self._sim_info.get_whim_bucks())
            return
        self._sim_info.add_whim_bucks(-cost, SetWhimBucks.PURCHASED_REWARD, source=reward_guid64)
        award.give_reward(self._sim_info)

    def send_satisfaction_reward_list(self):
        msg = Sims_pb2.SatisfactionRewards()
        for (reward, data) in self.SATISFACTION_STORE_ITEMS.items():
            reward_msg = Sims_pb2.SatisfactionReward()
            reward_msg.reward_id = reward.guid64
            reward_msg.cost = data.cost
            reward_msg.affordable = True if data.cost <= self._sim_info.get_whim_bucks() else False
            reward_msg.available = reward.is_valid(self._sim_info)
            reward_msg.type = data.award_type
            msg.rewards.append(reward_msg)
        msg.sim_id = self._sim_info.id
        distributor = Distributor.instance()
        distributor.add_op_with_no_owner(GenericProtocolBufferOp(Operation.SIM_SATISFACTION_REWARDS, msg))

    def cache_whim_goal_proto(self, whim_tracker_proto, skip_load=False):
        if skip_load:
            return
        if self._sim_info.is_npc:
            return
        if self._sim_info.whim_tracker is None:
            return
        self._whim_goal_proto = GameplaySaveData_pb2.WhimsetTrackerData()
        self._whim_goal_proto.CopyFrom(whim_tracker_proto)

    def load_whims_info_from_proto(self):
        if self._sim_info.is_npc:
            return
        if self._whim_goal_proto is None:
            return
        for whim_data in self._active_whims:
            whim = whim_data.whim
            if whim is not None:
                self._remove_whim(whim, None)
        if len(self._whim_goal_proto.active_whims) > self.max_whims:
            logger.error('More whims saved than the max number of goals allowed')
        aspiration_manager = services.get_instance_manager(sims4.resources.Types.ASPIRATION)
        sim_info_manager = services.sim_info_manager()
        for active_whim_msg in self._whim_goal_proto.active_whims:
            if not active_whim_msg.HasField('index'):
                pass
            else:
                whimset = aspiration_manager.get(active_whim_msg.whimset_guid)
                if whimset is None:
                    logger.info('Trying to load unavailable ASPIRATION resource: {}', active_whim_msg.whimset_guid)
                else:
                    goal_seed = GoalSeedling.deserialize_from_proto(active_whim_msg.goal_data)
                    if goal_seed is None:
                        pass
                    else:
                        target_sim_info = None
                        if goal_seed.target_id:
                            target_sim_info = sim_info_manager.get(goal_seed.target_id)
                            if target_sim_info is None:
                                pass
                            else:
                                secondary_sim_info = None
                                if goal_seed.secondary_target_id:
                                    secondary_sim_info = sim_info_manager.get(goal_seed.secondary_target_id)
                                    if secondary_sim_info is None:
                                        pass
                                    else:
                                        whim_index = active_whim_msg.index
                                        goal = goal_seed.goal_type(sim_info=self._sim_info, goal_id=self._goal_id_generator(), inherited_target_sim_info=target_sim_info, secondary_sim_info=secondary_sim_info, count=goal_seed.count, reader=goal_seed.reader, locked=goal_seed.locked)
                                        goal.setup()
                                        goal.register_for_on_goal_completed_callback(self._on_goal_completed)
                                        whim_data = self._active_whims[whim_index]
                                        whim_data.whim = goal
                                        whim_data.whimset = whimset
                                        self._create_anti_thrashing_cooldown(whim_data)
                                        self._goals_dirty = True
                                        logger.info('Whim {} loaded.', goal_seed.goal_type)
                                else:
                                    whim_index = active_whim_msg.index
                                    goal = goal_seed.goal_type(sim_info=self._sim_info, goal_id=self._goal_id_generator(), inherited_target_sim_info=target_sim_info, secondary_sim_info=secondary_sim_info, count=goal_seed.count, reader=goal_seed.reader, locked=goal_seed.locked)
                                    goal.setup()
                                    goal.register_for_on_goal_completed_callback(self._on_goal_completed)
                                    whim_data = self._active_whims[whim_index]
                                    whim_data.whim = goal
                                    whim_data.whimset = whimset
                                    self._create_anti_thrashing_cooldown(whim_data)
                                    self._goals_dirty = True
                                    logger.info('Whim {} loaded.', goal_seed.goal_type)
                        else:
                            secondary_sim_info = None
                            if goal_seed.secondary_target_id:
                                secondary_sim_info = sim_info_manager.get(goal_seed.secondary_target_id)
                                if secondary_sim_info is None:
                                    pass
                                else:
                                    whim_index = active_whim_msg.index
                                    goal = goal_seed.goal_type(sim_info=self._sim_info, goal_id=self._goal_id_generator(), inherited_target_sim_info=target_sim_info, secondary_sim_info=secondary_sim_info, count=goal_seed.count, reader=goal_seed.reader, locked=goal_seed.locked)
                                    goal.setup()
                                    goal.register_for_on_goal_completed_callback(self._on_goal_completed)
                                    whim_data = self._active_whims[whim_index]
                                    whim_data.whim = goal
                                    whim_data.whimset = whimset
                                    self._create_anti_thrashing_cooldown(whim_data)
                                    self._goals_dirty = True
                                    logger.info('Whim {} loaded.', goal_seed.goal_type)
                            else:
                                whim_index = active_whim_msg.index
                                goal = goal_seed.goal_type(sim_info=self._sim_info, goal_id=self._goal_id_generator(), inherited_target_sim_info=target_sim_info, secondary_sim_info=secondary_sim_info, count=goal_seed.count, reader=goal_seed.reader, locked=goal_seed.locked)
                                goal.setup()
                                goal.register_for_on_goal_completed_callback(self._on_goal_completed)
                                whim_data = self._active_whims[whim_index]
                                whim_data.whim = goal
                                whim_data.whimset = whimset
                                self._create_anti_thrashing_cooldown(whim_data)
                                self._goals_dirty = True
                                logger.info('Whim {} loaded.', goal_seed.goal_type)
        self._whim_goal_proto = None
        self._send_goals_update()

    def save_whims_info_to_proto(self, whim_tracker_proto):
        if self._sim_info.is_npc:
            return
        if self._whim_goal_proto is not None:
            whim_tracker_proto.CopyFrom(self._whim_goal_proto)
            return
        for (index, active_whim_data) in enumerate(self._active_whims):
            active_whim = active_whim_data.whim
            if active_whim is None:
                pass
            else:
                with ProtocolBufferRollback(whim_tracker_proto.active_whims) as active_whim_msg:
                    active_whim_msg.whimset_guid = active_whim_data.whimset.guid64
                    active_whim_msg.index = index
                    goal_seed = active_whim.create_seedling()
                    goal_seed.finalize_creation_for_save()
                    goal_seed.serialize_to_proto(active_whim_msg.goal_data)

    def debug_activate_whimset(self, whimset, chained):
        if not whimset.update_on_load:
            return
        self._activate_whimset(whimset)
        self._try_and_thrash_whims(whimset.activated_priority)

    def debug_activate_whim(self, whim):
        whim_data = self._active_whims[0]
        if whim_data.whim is not None:
            self._remove_whim(whim_data.whim, TelemetryWhimEvents.CANCELED)
        goal = whim(sim_info=self._sim_info, goal_id=self._goal_id_generator())
        goal.setup()
        goal.register_for_on_goal_completed_callback(self._on_goal_completed)
        goal.show_goal_awarded_notification()
        whim_data.whim = goal
        whim_data.whimset = next(iter(self._active_whimsets_data.keys()))
        self._create_anti_thrashing_cooldown(whim_data)
        self._goals_dirty = True
        self._send_goals_update()

    def debug_offer_whim_from_whimset(self, whimset):
        if whimset.update_on_load:
            self._activate_whimset(whimset)
        whim_data = self._active_whims[0]
        if whim_data.whim is not None:
            self._remove_whim(whim_data.whim, TelemetryWhimEvents.CANCELED)
        goal = self._create_whim(whimset, set())
        goal.setup()
        goal.register_for_on_goal_completed_callback(self._on_goal_completed)
        goal.show_goal_awarded_notification()
        whim_data.whim = goal
        whim_data.whimset = whimset
        self._create_anti_thrashing_cooldown(whim_data)
        self._goals_dirty = True
        self._send_goals_update()

    @property
    def _whims_needed(self):
        return self.max_whims - sum(1 for whim_info in self._active_whims if whim_info.whim is not None)

    @property
    def _sim_mood(self):
        return self._sim_info.get_mood()

    def _get_currently_active_whim_types(self):
        return {type(whim_data.whim) for whim_data in self._active_whims if whim_data.whim is not None}

    def _get_currently_used_whimsets(self):
        return {whim_data.whimset for whim_data in self._active_whims if whim_data.whimset is not None}

    def _get_whimsets_on_cooldown(self):
        return set(self._cooldown_alarms.keys())

    def _get_whim_data(self, whim):
        for whim_data in self._active_whims:
            if whim is whim_data.whim:
                return whim_data

    def _get_whim_by_whim_type(self, whim_type):
        for whim_data in self._active_whims:
            if isinstance(whim_data.whim, whim_type):
                return whim_data.whim

    def _get_target_for_whimset(self, whimset):
        if whimset.force_target is None:
            whimset_data = self._active_whimsets_data.get(whimset)
            if whimset_data is not None:
                return whimset_data.target
            return
        else:
            return whimset.force_target(self._sim_info)

    def _deactivate_whimset(self, whimset):
        if whimset not in self._active_whimsets_data:
            return
        logger.info('Deactivating Whimset {}', whimset)
        if whimset.cooldown_timer > 0:

            def _cooldown_ended(_):
                if whimset in self._cooldown_alarms:
                    del self._cooldown_alarms[whimset]

            self._cooldown_alarms[whimset] = alarms.add_alarm(self, create_time_span(minutes=whimset.cooldown_timer), _cooldown_ended)
        if whimset.timeout_retest is not None:
            resolver = event_testing.resolver.SingleSimResolver(self._sim_info)
            if resolver(whimset.timeout_retest.objective_test):
                self._activate_whimset(whimset)
                return
        del self._active_whimsets_data[whimset]
        if self._sim_info.aspiration_tracker is not None:
            self._sim_info.aspiration_tracker.reset_milestone(whimset)
        self._sim_info.remove_statistic(whimset.priority_commodity)

    def _activate_whimset(self, whimset, target=None, chained=False):
        if chained:
            new_priority = whimset.chained_priority
        else:
            new_priority = whimset.activated_priority
        if new_priority == 0:
            return
        self._sim_info.set_stat_value(whimset.priority_commodity, new_priority, add=True)
        whimset_data = self._active_whimsets_data.get(whimset)
        if whimset_data is None:
            stat = self._sim_info.get_stat_instance(whimset.priority_commodity)
            threshold = Threshold(whimset.priority_commodity.convergence_value, operator.le)

            def remove_active_whimset(_):
                self._deactivate_whimset(whimset)

            callback_data = stat.create_and_add_callback_listener(threshold, remove_active_whimset)
            self._active_whimsets_data[whimset] = _ActiveWhimsetData(target, callback_data)
            stat.decay_enabled = True
            logger.info('Setting whimset {} to active at priority {}.', whimset, new_priority)
        else:
            logger.info('Setting whimset {} which is already active to new priority value {}.', whimset, new_priority)

    def _remove_whim(self, whim, telemetry_event):
        whim.decommision()
        whim_data = self._get_whim_data(whim)
        whim_data.whim = None
        whim_data.whimset = None
        if whim_data.anti_thrashing_alarm_handle is not None:
            alarms.cancel_alarm(whim_data.anti_thrashing_alarm_handle)
            whim_data.anti_thrashing_alarm_handle = None
        if telemetry_event is not None:
            with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_WHIM_EVENT, sim_info=self._sim_info) as hook:
                hook.write_int(TELEMETRY_WHIM_EVENT_TYPE, telemetry_event)
                hook.write_guid(TELEMETRY_WHIM_GUID, whim.guid64)
        logger.info('Whim {} removed from whims tracker.', whim)
        self._goals_dirty = True

    def _on_goal_completed(self, whim, whim_completed):
        if not whim_completed:
            self._goals_dirty = True
            self._send_goals_update()
            return
        whim_data = self._get_whim_data(whim)
        parent_whimset = whim_data.whimset
        whim_type = type(whim)
        self._completed_goals[whim_type] = (whim, parent_whimset)
        inherited_target_sim_info = whim.get_actual_target_sim_info()
        self._remove_whim(whim, TelemetryWhimEvents.COMPLETED)
        services.get_event_manager().process_event(test_events.TestEvent.WhimCompleted, sim_info=self._sim_info, whim_completed=whim)
        should_deactivate_parent_whimset = parent_whimset.deactivate_on_completion
        highest_chained_priority = 0
        for set_to_chain in parent_whimset.connected_whim_sets:
            if set_to_chain is parent_whimset:
                should_deactivate_parent_whimset = False
            if set_to_chain.chained_priority > highest_chained_priority:
                highest_chained_priority = set_to_chain.chained_priority
            self._activate_whimset(set_to_chain, target=inherited_target_sim_info, chained=True)
        connected_whimsets = parent_whimset.connected_whims.get(whim)
        if connected_whimsets is not None:
            for set_to_chain in connected_whimsets:
                if set_to_chain is parent_whimset:
                    should_deactivate_parent_whimset = False
                if set_to_chain.chained_priority > highest_chained_priority:
                    highest_chained_priority = set_to_chain.chained_priority
                self._activate_whimset(set_to_chain, target=inherited_target_sim_info, chained=True)
        if should_deactivate_parent_whimset:
            self._deactivate_whimset(parent_whimset)
        op = distributor.ops.SetWhimComplete(whim_type.guid64)
        Distributor.instance().add_op(self._sim_info, op)
        score = self.get_score_for_whim(whim.score)
        if score > 0:
            self._sim_info.add_whim_bucks(score, SetWhimBucks.WHIM, source=whim.guid64)
        logger.info('Goal completed: {}, from Whim Set: {}', whim, parent_whimset)
        thrashed = False
        if highest_chained_priority > 0:
            thrashed = self._try_and_thrash_whims(highest_chained_priority, extra_prohibited_whims={whim_type})
        if not thrashed:
            self._offer_whims(prohibited_whims={whim_type})

    def _create_whim(self, whimset, prohibited_whims):
        potential_target = self._get_target_for_whimset(whimset)
        if potential_target is None and whimset.force_target is not None:
            return
        if whimset.secondary_target is not None:
            secondary_target = whimset.secondary_target(self._sim_info)
            if secondary_target is None:
                return
        else:
            secondary_target = None
        sim = self._sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED)
        disallowed_whims = self._get_currently_active_whim_types() | prohibited_whims
        weighted_whims = [(possible_whim.weight, possible_whim.goal) for possible_whim in whimset.whims if possible_whim.goal not in disallowed_whims]
        while weighted_whims:
            selected_whim = sims4.random.pop_weighted(weighted_whims)
            old_whim_instance_and_whimset = self._completed_goals.get(selected_whim)
            if old_whim_instance_and_whimset is not None and old_whim_instance_and_whimset[0].is_on_cooldown():
                pass
            else:
                pretest = selected_whim.can_be_given_as_goal(sim, None, inherited_target_sim_info=potential_target)
                if pretest:
                    whim = selected_whim(sim_info=self._sim_info, goal_id=self._goal_id_generator(), inherited_target_sim_info=potential_target, secondary_sim_info=secondary_target)
                    return whim

    def _create_anti_thrashing_cooldown(self, whim_data):

        def end_cooldown(_):
            whim_data.anti_thrashing_alarm_handle = None

        whim_data.anti_thrashing_alarm_handle = alarms.add_alarm(self, create_time_span(minutes=WhimsTracker.WHIM_ANTI_THRASHING_TIME), end_cooldown)

    def _offer_whims(self, prohibited_whimsets=EMPTY_SET, prohibited_whims=EMPTY_SET):
        if self._whims_needed == 0:
            return
        if self._sim_info.is_npc:
            return
        if not self._sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED):
            return
        if services.current_zone().is_zone_shutting_down:
            return
        whimsets_on_cooldown = self._get_whimsets_on_cooldown()
        for (index, whim_data) in enumerate(self._active_whims):
            if whim_data.whim is not None:
                pass
            else:
                if index == self.emotional_whim_index:
                    emotional_whimset = self.get_emotional_whimset()
                    if emotional_whimset is None:
                        logger.info('No emotional whimset found for mood {}.', self._sim_mood)
                    else:
                        possible_whimsets = {emotional_whimset}
                        possible_whimsets -= self._get_currently_used_whimsets()
                        possible_whimsets -= prohibited_whimsets
                        possible_whimsets -= whimsets_on_cooldown
                        prioritized_whimsets = [(self.get_priority(whimset), whimset) for whimset in possible_whimsets]
                        while prioritized_whimsets:
                            whimset = sims4.random.pop_weighted(prioritized_whimsets)
                            if whimset is None:
                                break
                            goal = self._create_whim(whimset, prohibited_whims)
                            if goal is None:
                                pass
                            else:
                                goal.setup()
                                goal.register_for_on_goal_completed_callback(self._on_goal_completed)
                                goal.show_goal_awarded_notification()
                                whim_data.whim = goal
                                whim_data.whimset = whimset
                                self._create_anti_thrashing_cooldown(whim_data)
                                with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_WHIM_EVENT, sim_info=self._sim_info) as hook:
                                    hook.write_int(TELEMETRY_WHIM_EVENT_TYPE, TelemetryWhimEvents.ADDED)
                                    hook.write_guid(TELEMETRY_WHIM_GUID, goal.guid64)
                                self._goals_dirty = True
                                break
                else:
                    possible_whimsets = self.get_active_whimsets()
                possible_whimsets -= self._get_currently_used_whimsets()
                possible_whimsets -= prohibited_whimsets
                possible_whimsets -= whimsets_on_cooldown
                prioritized_whimsets = [(self.get_priority(whimset), whimset) for whimset in possible_whimsets]
                while prioritized_whimsets:
                    whimset = sims4.random.pop_weighted(prioritized_whimsets)
                    if whimset is None:
                        break
                    goal = self._create_whim(whimset, prohibited_whims)
                    if goal is None:
                        pass
                    else:
                        goal.setup()
                        goal.register_for_on_goal_completed_callback(self._on_goal_completed)
                        goal.show_goal_awarded_notification()
                        whim_data.whim = goal
                        whim_data.whimset = whimset
                        self._create_anti_thrashing_cooldown(whim_data)
                        with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_WHIM_EVENT, sim_info=self._sim_info) as hook:
                            hook.write_int(TELEMETRY_WHIM_EVENT_TYPE, TelemetryWhimEvents.ADDED)
                            hook.write_guid(TELEMETRY_WHIM_GUID, goal.guid64)
                        self._goals_dirty = True
                        break
        self._send_goals_update()

    def _try_and_thrash_whims(self, priority, extra_prohibited_whims=EMPTY_SET):
        whims_thrashed = set()
        for (index, whim_data) in enumerate(self._active_whims):
            if index == self.emotional_whim_index:
                pass
            elif whim_data.whim is None:
                pass
            elif not whim_data.anti_thrashing_alarm_handle is not None:
                if whim_data.whim.locked:
                    pass
                elif self.get_priority(whim_data.whimset) >= priority:
                    pass
                elif not sims4.random.random_chance(WhimsTracker.WHIM_THRASHING_CHANCE*100):
                    pass
                else:
                    whims_thrashed.add(type(whim_data.whim))
                    self._remove_whim(whim_data.whim, TelemetryWhimEvents.CANCELED)
        if not whims_thrashed:
            return False
        prohibited_whims = whims_thrashed | extra_prohibited_whims
        self._offer_whims(prohibited_whims=prohibited_whims)
        return True

    def _send_goals_update(self):
        if not self._goals_dirty:
            return
        logger.debug('Sending whims update for {}.  Current active whims: {}', self._sim_info, self._active_whims, owner='jjacobson')
        current_whims = []
        for (index, whim_data) in enumerate(self._active_whims):
            whim = whim_data.whim
            if whim is None or self._hidden:
                whim_goal = DistributorOps_pb2.WhimGoal()
                current_whims.append(whim_goal)
            else:
                goal_target_id = 0
                goal_whimset = whim_data.whimset
                goal_target = whim.get_required_target_sim_info()
                goal_target_id = goal_target.id if goal_target is not None else 0
                whim_goal = DistributorOps_pb2.WhimGoal()
                whim_goal.whim_guid64 = whim.guid64
                whim_name = whim.get_display_name()
                if whim_name is not None:
                    whim_goal.whim_name = whim_name
                whim_goal.whim_score = self.get_score_for_whim(whim.score)
                whim_goal.whim_noncancel = whim.noncancelable
                whim_display_icon = whim.display_icon
                if whim_display_icon is not None:
                    whim_goal.whim_icon_key.type = whim_display_icon.type
                    whim_goal.whim_icon_key.group = whim_display_icon.group
                    whim_goal.whim_icon_key.instance = whim_display_icon.instance
                whim_goal.whim_goal_count = whim.max_iterations
                whim_goal.whim_current_count = whim.completed_iterations
                whim_goal.whim_target_sim = goal_target_id
                whim_tooltip = whim.get_display_tooltip()
                if whim_tooltip is not None:
                    whim_goal.whim_tooltip = whim_tooltip
                if index == self.emotional_whim_index:
                    whim_goal.whim_mood_guid64 = self._sim_mood().guid64
                else:
                    whim_goal.whim_mood_guid64 = 0
                whim_goal.whim_tooltip_reason = goal_whimset.whim_reason(*whim.get_localization_tokens())
                whim_goal.whim_locked = whim.locked
                current_whims.append(whim_goal)
        if self._goals_dirty:
            self._sim_info.current_whims = current_whims
            self._goals_dirty = False

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.FULL

    def on_lod_update(self, old_lod, new_lod):
        if new_lod < self._tracker_lod_threshold:
            self.clean_up()
        elif old_lod < self._tracker_lod_threshold:
            sim_msg = services.get_persistence_service().get_sim_proto_buff(self._sim_info.id)
            if sim_msg is not None:
                self._sim_info.set_whim_bucks(sim_msg.gameplay_data.whim_bucks, SetWhimBucks.LOAD)
                self.cache_whim_goal_proto(sim_msg.gameplay_data.whim_tracker)
