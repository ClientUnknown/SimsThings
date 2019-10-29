from collections import defaultdictfrom distributor.rollback import ProtocolBufferRollbackfrom relationships.bit_timout import BitTimeoutDatafrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom relationships.object_relationship_track_tracker import ObjectRelationshipTrackTrackerfrom relationships.relationship_enums import RelationshipBitCullingPreventionfrom relationships.relationship_track_tracker import RelationshipTrackTrackerfrom relationships.sim_knowledge import SimKnowledgeimport event_testingimport servicesimport sims4import telemetry_helperlogger = sims4.log.Logger('Relationship', default_owner='jjacobson')TELEMETRY_GROUP_RELATIONSHIPS = 'RSHP'TELEMETRY_HOOK_ADD_BIT = 'BADD'TELEMETRY_HOOK_REMOVE_BIT = 'BREM'TELEMETRY_HOOK_CHANGE_LEVEL = 'RLVL'TELEMETRY_FIELD_TARGET_ID = 'taid'TELEMETRY_FIELD_REL_ID = 'rlid'TELEMETRY_FIELD_BIT_ID = 'btid'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_RELATIONSHIPS)
class RelationshipData:
    __slots__ = ('relationship', '_bits', '_bit_timeouts', '_cached_depth', 'cached_depth_dirty', '_relationship_bit_locks', '__weakref__')

    def __init__(self, relationship):
        self.relationship = relationship
        self._bits = {}
        self._bit_timeouts = None
        self._cached_depth = 0
        self.cached_depth_dirty = True
        self._relationship_bit_locks = None

    @property
    def bit_types(self):
        return self._bits.keys()

    @property
    def bit_instances(self):
        return self._bits.values()

    @property
    def depth(self):
        if self.cached_depth_dirty:
            self._refresh_depth_cache()
        return self._cached_depth

    def _refresh_depth_cache(self):
        self._cached_depth = 0
        for bit in self._bits.keys():
            self._cached_depth += bit.depth
        self.cached_depth_dirty = False

    def _sim_ids(self):
        raise NotImplementedError

    def can_cull_relationship(self, consider_convergence, is_played_relationship):
        for bit in self._bits.values():
            if bit.relationship_culling_prevention == RelationshipBitCullingPrevention.ALLOW_ALL:
                pass
            else:
                if bit.relationship_culling_prevention == RelationshipBitCullingPrevention.PLAYED_AND_UNPLAYED:
                    return False
                if is_played_relationship and bit.relationship_culling_prevention == RelationshipBitCullingPrevention.PLAYED_ONLY:
                    return False
        return True

    def _find_timeout_data_by_bit(self, bit):
        if self._bit_timeouts:
            return self._bit_timeouts.get(bit, None)

    def _find_timeout_data_by_bit_instance(self, bit_instance):
        bit_manager = services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT)
        bit = bit_manager.get(bit_instance.guid64)
        return self._find_timeout_data_by_bit(bit)

    def _find_timeout_data_by_handle(self, alarm_handle):
        if self._bit_timeouts:
            for data in self._bit_timeouts.values():
                if alarm_handle is data.alarm_handle:
                    return data

    def _timeout_alarm_callback(self, alarm_handle):
        timeout_data = self._find_timeout_data_by_handle(alarm_handle)
        if timeout_data is not None:
            self.remove_bit(timeout_data.bit)
        else:
            logger.error('Failed to find alarm handle in _bit_timeouts list')

    def _send_telemetry_event_for_bit_change(self, telemetry_hook, bit, sim_info, target_sim_info):
        with telemetry_helper.begin_hook(writer, telemetry_hook, sim_info=sim_info) as hook:
            hook.write_int(TELEMETRY_FIELD_TARGET_ID, target_sim_info.sim_id)
            hook.write_int(TELEMETRY_FIELD_REL_ID, target_sim_info.sim_id)
            hook.write_int(TELEMETRY_FIELD_BIT_ID, bit.guid64)

    def _update_client_for_sim_info_for_bit_add(self, bit_to_add, bit_instance, sim_info, target_sim_info, from_load):
        if sim_info is None:
            return
        sim = sim_info.get_sim_instance()
        if sim is not None:
            bit_instance.on_add_to_relationship(sim, target_sim_info, self.relationship, from_load)
            self.show_bit_added_dialog(bit_instance, sim, target_sim_info)
        if not self.relationship._is_object_rel:
            self._send_telemetry_event_for_bit_change(TELEMETRY_HOOK_ADD_BIT, bit_to_add, sim_info, target_sim_info)
            services.get_event_manager().process_event(event_testing.test_events.TestEvent.AddRelationshipBit, sim_info=sim_info, relationship_bit=bit_to_add, sim_id=sim_info.sim_id, target_sim_id=target_sim_info.sim_id)
            if bit_to_add is RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT and sim_info is not None:
                sim_info.update_spouse_sim_id(target_sim_info.sim_id)

    def _update_client_from_bit_add(self, bit_type, bit_instance, from_load):
        raise NotImplementedError

    def _update_client_for_sim_info_for_bit_remove(self, bit_to_remove, bit_instance, sim_info, target_sim_info):
        if sim_info is None:
            return
        if target_sim_info is not None:
            self._send_telemetry_event_for_bit_change(TELEMETRY_HOOK_REMOVE_BIT, bit_to_remove, sim_info, target_sim_info)
            services.get_event_manager().process_event(event_testing.test_events.TestEvent.RemoveRelationshipBit, sim_info=sim_info, relationship_bit=bit_to_remove, sim_id=sim_info.sim_id, target_sim_id=target_sim_info.sim_id)
            sim = sim_info.get_sim_instance()
            if sim is not None:
                bit_instance.on_remove_from_relationship(sim, target_sim_info)
                self.show_bit_removed_dialog(bit_instance, sim, target_sim_info)
        if bit_to_remove is RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT:
            sim_info.update_spouse_sim_id(None)

    def _update_client_from_bit_remove(self, bit_type, bit_instance):
        raise NotImplementedError

    def add_bit(self, bit_type, bit_instance, from_load=False):
        self.cached_depth_dirty = True
        self._bits[bit_type] = bit_instance
        if not self.relationship.suppress_client_updates:
            self._update_client_from_bit_add(bit_type, bit_instance, from_load)
        if bit_type.timeout > 0:
            timeout_data = self._find_timeout_data_by_bit(bit_type)
            if timeout_data is None:
                timeout_data = BitTimeoutData(bit_type, self._timeout_alarm_callback)
                if self._bit_timeouts is None:
                    self._bit_timeouts = {}
                self._bit_timeouts[bit_type] = timeout_data
            timeout_data.reset_alarm()
        remove_on_threshold = bit_type.remove_on_threshold
        if remove_on_threshold is not None:
            track_type = remove_on_threshold.track
            listener = self.relationship.relationship_track_tracker.create_and_add_listener(track_type, remove_on_threshold.threshold, self._on_remove_bit_threshold_satisfied)
            bit_instance.add_conditional_removal_listener(listener)

    def _on_remove_bit_threshold_satisfied(self, track):
        for bit in self._bits.keys():
            if bit.remove_on_threshold is None:
                pass
            elif bit.remove_on_threshold.track is type(track):
                self.remove_bit(bit)
                return
        logger.error("Got a callback to remove a bit for track {}, but one doesn't exist.", track)

    def remove_bit(self, bit):
        bit_instance = self._bits.get(bit)
        if bit_instance is None:
            logger.warn("Attempting to remove bit of type {} that doesn't exist.", bit)
        if not self.relationship.suppress_client_updates:
            self._update_client_from_bit_remove(bit, bit_instance)
        self.cached_depth_dirty = True
        del self._bits[bit]
        logger.debug('Removed bit {} for {}', bit, self)
        timeout_data = self._find_timeout_data_by_bit(bit)
        if timeout_data is not None:
            timeout_data.cancel_alarm()
            del self._bit_timeouts[bit]
            if not self._bit_timeouts:
                self._bit_timeouts = None
        remove_on_threshold = bit.remove_on_threshold
        if remove_on_threshold is not None:
            listener = bit_instance.remove_conditional_removal_listener()
            if listener is not None:
                self.relationship.relationship_track_tracker.remove_listener(listener)
            else:
                logger.error("Bit {} is meant to have a listener on track {} but it doesn't for {}.".format(bit, remove_on_threshold.track, self))

    def save_relationship_data(self, relationship_data_msg):
        for bit in self._bits:
            if bit.persisted:
                relationship_data_msg.bits.append(bit.guid64)
        if self._bit_timeouts is not None:
            for timeout in self._bit_timeouts.values():
                with ProtocolBufferRollback(relationship_data_msg.timeouts) as timeout_proto_buffer:
                    timeout_proto_buffer.timeout_bit_id_hash = timeout.bit.guid64
                    timeout_proto_buffer.elapsed_time = timeout.get_elapsed_time()
        if self._relationship_bit_locks is not None:
            for relationship_bit_lock in self._relationship_bit_locks.values():
                with ProtocolBufferRollback(relationship_data_msg.relationship_bit_locks) as relationship_bit_lock_proto_buffer:
                    relationship_bit_lock.save(relationship_bit_lock_proto_buffer)

    def load_relationship_data(self, relationship_data_msg, track_to_bit_list_map=None):
        bit_manager = services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT)
        logger.assert_raise(bit_manager, 'Unable to retrieve relationship bit manager.')
        if track_to_bit_list_map is None:
            track_to_bit_list_map = defaultdict(list)
        bit_list = []
        for bit_guid in relationship_data_msg.bits:
            bit = bit_manager.get(bit_guid)
            if bit is None:
                logger.info('Trying to load unavailable RELATIONSHIP_BIT resource: {}', bit_guid)
            elif bit.triggered_track is not None:
                track_inst = self._relationship_track_tracker.get_statistic(bit.triggered_track)
                if track_inst is not None:
                    bit_data_set = track_inst.get_bit_data_set()
                    if bit_data_set and bit in bit_data_set:
                        track_to_bit_list_map[track_inst].append(bit)
                    else:
                        bit_list.append(bit)
                else:
                    bit_list.append(bit)
            else:
                bit_list.append(bit)
        for (track_inst, track_bit_list) in track_to_bit_list_map.items():
            if len(track_bit_list) > 1:
                active_bit = track_inst.get_active_bit_by_value()
                logger.warn('{} has bad persisted Rel Bit value on Rel Track {}.  Fix it by adding bit {} and removing bits {}.', self, track_inst, active_bit, track_bit_list, owner='mkartika')
                bit_list.append(active_bit)
            else:
                bit_list.extend(track_bit_list)
        (sim_id_a, sim_id_b) = self._sim_ids()
        while bit_list:
            bit = bit_list.pop()
            if bit in self._bits:
                pass
            elif not self.relationship.add_relationship_bit(sim_id_a, sim_id_b, bit, notify_client=False, pending_bits=bit_list, from_load=True, send_rel_change_event=False):
                logger.warn('Failed to load relationship bit {}.  This is valid if tuning has changed.', bit)
        if relationship_data_msg.timeouts is not None:
            for timeout_save in relationship_data_msg.timeouts:
                bit = bit_manager.get(timeout_save.timeout_bit_id_hash)
                timeout_data = self._find_timeout_data_by_bit(bit)
                if timeout_data is not None:
                    if not timeout_data.load_bit_timeout(timeout_save.elapsed_time):
                        self.remove_bit(bit)
                else:
                    logger.warn('Attempting to load timeout value on bit {} with no timeout.  This is valid if tuning has changed.', bit)
        relationship_bit_lock_manager = services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_LOCK)
        for relationship_bit_lock_data in relationship_data_msg.relationship_bit_locks:
            lock_type = relationship_bit_lock_manager.get(relationship_bit_lock_data.relationship_bit_lock_type)
            if lock_type is None:
                pass
            else:
                new_lock = self.add_lock(lock_type)
                new_lock.load(relationship_bit_lock_data)

    def destroy(self):
        self.relationship = None
        self._bits.clear()
        self._bit_timeouts = None
        self._cached_depth = 0
        self.cached_depth_dirty = False
        self._relationship_bit_locks = None

    def show_bit_added_dialog(self, relationship_bit, sim, target_sim_info):
        raise NotImplementedError

    def show_bit_removed_dialog(self, relationship_bit, sim, target_sim_info):
        raise NotImplementedError

    def add_lock(self, lock_type):
        if self._relationship_bit_locks is None:
            self._relationship_bit_locks = {}
        current_lock = self._relationship_bit_locks.get(lock_type, None)
        if current_lock is not None:
            return current_lock
        new_lock = lock_type()
        self._relationship_bit_locks[lock_type] = new_lock
        return new_lock

    def get_lock(self, lock_type):
        if self._relationship_bit_locks is None:
            return
        return self._relationship_bit_locks.get(lock_type, None)

    def get_all_locks(self):
        locks = []
        if self._relationship_bit_locks is None:
            return locks
        locks.extend(self._relationship_bit_locks.values())
        return locks

    def on_sim_creation(self, sim):
        for bit_instance in self._bits.values():
            bit_instance.add_buffs_for_bit_add(sim, self.relationship, True)

class UnidirectionalRelationshipData(RelationshipData):
    __slots__ = ('_knowledge', '_actor_sim_id', 'bit_added_buffs')

    def __init__(self, relationship, actor_sim_id):
        super().__init__(relationship)
        self._knowledge = None
        self._actor_sim_id = actor_sim_id
        self.bit_added_buffs = None

    def __repr__(self):
        return 'UnidirectionalRelationshipData between: {} and {}'.format(self._actor_sim_id, self._target_sim_id)

    @property
    def _target_sim_id(self):
        return self.relationship.get_other_sim_id(self._actor_sim_id)

    @property
    def knowledge(self):
        return self._knowledge

    def initialize_knowledge(self):
        self._knowledge = SimKnowledge(self)

    def find_target_sim_info(self):
        return services.sim_info_manager().get(self._target_sim_id)

    def _sim_ids(self):
        return (self._actor_sim_id, self._target_sim_id)

    def _update_client_from_bit_add(self, bit_type, bit_instance, from_load):
        sim_info_manager = services.sim_info_manager()
        actor_sim_info = sim_info_manager.get(self._actor_sim_id)
        target_sim_info = sim_info_manager.get(self._target_sim_id)
        self._update_client_for_sim_info_for_bit_add(bit_type, bit_instance, actor_sim_info, target_sim_info, from_load)

    def add_bit(self, bit_type, bit_instance, from_load=False):
        super().add_bit(bit_type, bit_instance, from_load=from_load)
        sim_info = services.sim_info_manager().get(self._actor_sim_id)
        if sim_info:
            bit_instance.add_appropriateness_buffs(sim_info)

    def _update_client_from_bit_remove(self, bit_type, bit_instance):
        sim_info_manager = services.sim_info_manager()
        actor_sim_info = sim_info_manager.get(self._actor_sim_id)
        target_sim_info = sim_info_manager.get(self._target_sim_id)
        self._update_client_for_sim_info_for_bit_remove(bit_type, bit_instance, actor_sim_info, target_sim_info)

    def remove_bit(self, bit):
        if bit not in self._bits:
            logger.debug("Attempting to remove bit for {} that doesn't exist: {}", self, bit)
            return
        bit_instance = self._bits[bit]
        super().remove_bit(bit)
        sim_info = services.sim_info_manager().get(self._actor_sim_id)
        if sim_info is not None:
            bit_instance.remove_appropriateness_buffs(sim_info)

    def save_relationship_data(self, relationship_data_msg):
        super().save_relationship_data(relationship_data_msg)
        if self.bit_added_buffs is not None:
            for buff_id in self.bit_added_buffs:
                relationship_data_msg.bit_added_buffs.append(buff_id)
        if self._knowledge is not None:
            relationship_data_msg.knowledge = self._knowledge.get_save_data()

    def load_relationship_data(self, relationship_data_msg):
        if relationship_data_msg.bit_added_buffs:
            if self.bit_added_buffs is None:
                self.bit_added_buffs = set()
            for bit_added_buff in relationship_data_msg.bit_added_buffs:
                self.bit_added_buffs.add(bit_added_buff)
        super().load_relationship_data(relationship_data_msg)
        if relationship_data_msg.HasField('knowledge'):
            self._knowledge = SimKnowledge(self)
            self._knowledge.load_knowledge(relationship_data_msg.knowledge)

    def destroy(self):
        super().destroy()
        self.bit_added_buffs = None
        self._knowledge = None
        self._actor_sim_id = 0

    def show_bit_added_dialog(self, relationship_bit, sim, target_sim_info):
        if relationship_bit.bit_added_notification is None:
            return
        target_sim = target_sim_info.get_sim_instance()
        if sim.is_selectable and sim.is_human:
            if target_sim is None or target_sim.is_selectable and target_sim.is_pet:
                relationship_bit.show_bit_added_dialog(sim, sim, target_sim_info)
            elif not target_sim_info.relationship_tracker.has_bit(sim.id, type(relationship_bit)):
                relationship_bit.show_bit_added_dialog(sim, sim, target_sim_info)
        elif relationship_bit.bit_added_notification.show_if_unselectable and target_sim_info.is_selectable and target_sim_info.is_human:
            relationship_bit.show_bit_added_dialog(target_sim_info, sim, target_sim_info)

    def show_bit_removed_dialog(self, relationship_bit, sim, target_sim_info):
        if relationship_bit.bit_removed_notification is None:
            return
        if sim.is_selectable and sim.is_pet:
            return
        target_sim = target_sim_info.get_sim_instance()
        if target_sim is not None or target_sim.is_selectable and target_sim.is_pet:
            relationship_bit.show_bit_removed_dialog(sim, target_sim_info)
        elif not target_sim_info.relationship_tracker.has_bit(sim.id, type(self)):
            relationship_bit.show_bit_removed_dialog(sim, target_sim_info)

class BidirectionalRelationshipData(RelationshipData):
    __slots__ = ('_relationship_track_tracker', '_level_change_watcher_id')

    def __init__(self, relationship):
        super().__init__(relationship)
        if relationship._is_object_rel == False:
            self._relationship_track_tracker = RelationshipTrackTracker(self)
        else:
            self._relationship_track_tracker = ObjectRelationshipTrackTracker(self)
        self._level_change_watcher_id = self._relationship_track_tracker.add_watcher(self._value_changed)

    def __repr__(self):
        return 'BidirectionalRelationshipData between: {} and {}'.format(self.sim_id_a, self.sim_id_b)

    @property
    def sim_id_a(self):
        return self.relationship.sim_id_a

    @property
    def sim_id_b(self):
        return self.relationship.sim_id_b

    def _sim_ids(self):
        return (self.sim_id_a, self.sim_id_b)

    def _value_changed(self, stat_type, old_value, new_value):
        if stat_type.causes_delayed_removal_on_convergence:
            self.relationship._destroy_culling_alarm()
        self.relationship._last_update_time = services.time_service().sim_now

    @property
    def relationship_track_tracker(self):
        return self._relationship_track_tracker

    def get_track_score(self, track):
        return self._relationship_track_tracker.get_user_value(track)

    def set_track_score(self, value, track):
        self._relationship_track_tracker.set_value(track, value)

    def add_track_score(self, increment, track):
        self._relationship_track_tracker.add_value(track, increment)

    def enable_player_sim_track_decay(self, to_enable=True):
        self._relationship_track_tracker.enable_player_sim_track_decay(to_enable)

    def get_track_utility_score(self, track):
        track_inst = self._relationship_track_tracker.get_statistic(track)
        if track_inst is not None:
            return track_inst.autonomous_desire
        else:
            return track.autonomous_desire

    def get_track(self, track, add=False):
        return self._relationship_track_tracker.get_statistic(track, add)

    def get_highest_priority_track_bit(self):
        highest_priority_bit = None
        for track in self._relationship_track_tracker:
            bit = track.get_active_bit()
            if not bit:
                pass
            else:
                if not highest_priority_bit is None:
                    if bit.priority > highest_priority_bit.priority:
                        highest_priority_bit = bit
                highest_priority_bit = bit
        return highest_priority_bit

    def get_prevailing_short_term_context_track(self):
        tracks = [track for track in self._relationship_track_tracker if track.is_short_term_context]
        if tracks:
            return max(tracks, key=lambda t: abs(t.get_value()))
        return self.get_track(RelationshipGlobalTuning.DEFAULT_SHORT_TERM_CONTEXT_TRACK, add=True)

    def track_reached_convergence(self, track_instance):
        if track_instance.causes_delayed_removal_on_convergence and self.relationship.can_cull_relationship():
            logger.debug('{} has been marked for culling.', self)
            self.relationship._create_culling_alarm()
        if track_instance.is_visible:
            logger.debug('Notifying client that {} has reached convergence.', self)
            self.relationship._notify_client()

    def apply_social_group_decay(self):
        for track in self._relationship_track_tracker:
            track.apply_social_group_decay()

    def remove_social_group_decay(self):
        for track in self._relationship_track_tracker:
            track.remove_social_group_decay()

    def _update_client_from_bit_add(self, bit_type, bit_instance, from_load):
        sim_info_manager = services.sim_info_manager()
        sim_info_a = sim_info_manager.get(self.sim_id_a)
        sim_info_b = sim_info_manager.get(self.sim_id_b)
        self._update_client_for_sim_info_for_bit_add(bit_type, bit_instance, sim_info_a, sim_info_b, from_load)
        if sim_info_b is not None:
            self._update_client_for_sim_info_for_bit_add(bit_type, bit_instance, sim_info_b, sim_info_a, from_load)

    def add_bit(self, bit_type, bit_instance, from_load=False):
        super().add_bit(bit_type, bit_instance, from_load=from_load)
        sim_info_manager = services.sim_info_manager()
        sim_info_a = sim_info_manager.get(self.sim_id_a)
        sim_info_b = sim_info_manager.get(self.sim_id_b)
        if sim_info_a is not None:
            bit_instance.add_appropriateness_buffs(sim_info_a)
        if sim_info_b is not None:
            bit_instance.add_appropriateness_buffs(sim_info_b)

    def _update_client_from_bit_remove(self, bit_type, bit_instance):
        sim_info_manager = services.sim_info_manager()
        sim_info_a = sim_info_manager.get(self.sim_id_a)
        sim_info_b = sim_info_manager.get(self.sim_id_b)
        self._update_client_for_sim_info_for_bit_remove(bit_type, bit_instance, sim_info_a, sim_info_b)
        self._update_client_for_sim_info_for_bit_remove(bit_type, bit_instance, sim_info_b, sim_info_a)

    def remove_bit(self, bit):
        if bit not in self._bits:
            logger.debug("Attempting to remove bit for {} that doesn't exist: {}", self, bit)
            return
        bit_instance = self._bits[bit]
        super().remove_bit(bit)
        sim_info_manager = services.sim_info_manager()
        sim_info_a = sim_info_manager.get(self.sim_id_a)
        sim_info_b = sim_info_manager.get(self.sim_id_b)
        if sim_info_a:
            bit_instance.remove_appropriateness_buffs(sim_info_a)
        if sim_info_b:
            bit_instance.remove_appropriateness_buffs(sim_info_b)

    def save_relationship_data(self, relationship_data_msg):
        super().save_relationship_data(relationship_data_msg)
        for track in self._relationship_track_tracker:
            if not track.persisted:
                pass
            elif track.persist_at_convergence or track.is_at_convergence():
                pass
            else:
                with ProtocolBufferRollback(relationship_data_msg.tracks) as track_proto_buffer:
                    track_proto_buffer.track_id = track.type_id()
                    track_proto_buffer.value = track.get_value()
                    track_proto_buffer.visible = track.visible_to_client
                    track_proto_buffer.ticks_until_decay_begins = track.get_saved_ticks_until_decay_begins()

    def load_relationship_data(self, relationship_data_msg):
        track_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
        track_to_bit_list_map = defaultdict(list)
        try:
            self._relationship_track_tracker.suppress_callback_setup_during_load = True
            self._relationship_track_tracker.load_in_progress = True
            for track_data in relationship_data_msg.tracks:
                track_type = track_manager.get(track_data.track_id)
                if track_type is None:
                    pass
                elif track_type.persist_at_convergence or track_data.value == track_type.default_value:
                    pass
                else:
                    track_inst = self._relationship_track_tracker.add_statistic(track_type)
                    if track_inst is not None:
                        track_inst.set_value(track_data.value)
                        track_inst.visible_to_client = track_data.visible
                        track_inst.set_time_until_decay_begins(track_data.ticks_until_decay_begins)
                        track_inst.fixup_callbacks_during_load()
                        track_to_bit_list_map[track_inst] = []
                    else:
                        logger.warn('Failed to load track {}.  This is valid if the tuning has changed.', track_type)
        finally:
            self._relationship_track_tracker.suppress_callback_setup_during_load = False
            self._relationship_track_tracker.load_in_progress = False
        super().load_relationship_data(relationship_data_msg, track_to_bit_list_map=track_to_bit_list_map)
        for track in self._relationship_track_tracker:
            track.update_track_index(self.relationship)

    def destroy(self):
        super().destroy()
        self._relationship_track_tracker.remove_watcher(self._level_change_watcher_id)
        self._level_change_watcher_id = None
        self._relationship_track_tracker.destroy()
        self._relationship_track_tracker = None

    def can_cull_relationship(self, consider_convergence, is_played_relationship):
        if consider_convergence and not self._relationship_track_tracker.are_all_tracks_that_cause_culling_at_convergence():
            return False
        return super().can_cull_relationship(consider_convergence, is_played_relationship)

    def show_bit_added_dialog(self, relationship_bit, sim, target_sim_info):
        if relationship_bit.bit_added_notification is None:
            return
        if sim.is_selectable and sim.is_human:
            relationship_bit.show_bit_added_dialog(sim, sim, target_sim_info)

    def show_bit_removed_dialog(self, relationship_bit, sim, target_sim_info):
        if relationship_bit.bit_removed_notification is None:
            return
        if sim.is_selectable and sim.is_human:
            relationship_bit.show_bit_removed_dialog(sim, target_sim_info)
