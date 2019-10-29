from _collections import defaultdictfrom collections import namedtuplefrom contextlib import contextmanagerfrom protocolbuffers import Dialog_pb2, Consts_pb2from bucks.bucks_enums import BucksTypefrom bucks.bucks_perk import BucksPerkTunablesfrom bucks.bucks_telemetry import bucks_telemetry_writer, TELEMETRY_HOOK_BUCKS_GAIN, TELEMETRY_FIELD_BUCKS_TYPE, TELEMETRY_FIELD_BUCKS_AMOUNT, TELEMETRY_FIELD_BUCKS_TOTAL, TELEMETRY_FIELD_BUCKS_SOURCE, TELEMETRY_HOOK_BUCKS_SPEND, TELEMETRY_HOOK_BUCKS_REFUNDfrom clock import interval_in_sim_hoursfrom date_and_time import DateAndTimefrom distributor import shared_messagesfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import IconInfoData, create_icon_info_msgfrom distributor.system import Distributorfrom event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom sims4.callback_utils import CallableListfrom sims4.tuning.tunable import TunableRangeimport alarmsimport cachesimport clockimport servicesimport sims4import telemetry_helperlogger = sims4.log.Logger('Bucks', default_owner='tastle')PerkData = namedtuple('PerkData', ('unlocked_by', 'timestamp', 'currently_unlocked'))
class BucksTrackerBase:
    MAX_BUCKS_ALLOWED = TunableRange(description='\n        The max amount of bucks that a tracker is allowed to accrue.\n        ', tunable_type=int, default=9999999, minimum=0, maximum=sims4.math.MAX_INT32)

    def __init__(self, owner):
        self._owner = owner
        self._unlocked_perks = {}
        self._bucks = {}
        self._bucks_modified_callbacks = defaultdict(CallableList)
        self._perk_unlocked_callbacks = defaultdict(CallableList)
        self._active_perk_timers = {}
        self._inactive_perk_timers = {}
        self._recently_locked_perks = defaultdict(set)
        for bucks_type in BucksType:
            self._unlocked_perks[bucks_type] = {}
            self._active_perk_timers[bucks_type] = {}
            self._inactive_perk_timers[bucks_type] = {}

    def clear_bucks_tracker(self):
        self._unlocked_perks = {}
        self._bucks = {}
        self._bucks_modified_callbacks = defaultdict(CallableList)
        self._perk_unlocked_callbacks = defaultdict(CallableList)
        for bucks_type in BucksType:
            self.deactivate_all_temporary_perk_timers_of_type(bucks_type)
            self._unlocked_perks[bucks_type] = {}
            self._active_perk_timers[bucks_type] = {}
            self._inactive_perk_timers[bucks_type] = {}

    def has_bucks_type(self, bucks_type):
        return bucks_type in self._bucks

    def get_bucks_amount_for_type(self, bucks_type):
        return self._bucks.get(bucks_type, 0)

    def add_bucks_modified_callback(self, bucks_type, callback):
        self._bucks_modified_callbacks[bucks_type].register(callback)

    def remove_bucks_modified_callback(self, bucks_type, callback):
        self._bucks_modified_callbacks[bucks_type].unregister(callback)

    def add_perk_unlocked_callback(self, bucks_type, callback):
        self._perk_unlocked_callbacks[bucks_type].register(callback)

    def remove_perk_unlocked_callback(self, bucks_type, callback):
        self._perk_unlocked_callbacks[bucks_type].unregister(callback)

    def has_perk_unlocked_for_bucks_type(self, bucks_type):
        return len(self._unlocked_perks[bucks_type]) > 0

    def is_perk_unlocked(self, perk):
        if perk not in self._unlocked_perks[perk.associated_bucks_type]:
            return False
        return self._unlocked_perks[perk.associated_bucks_type][perk].currently_unlocked

    def _get_perk_unlock_timestamp(self, perk):
        if not self.is_perk_unlocked(perk):
            return
        perk_data = self._unlocked_perks[perk.associated_bucks_type][perk]
        return perk_data.timestamp

    def unlock_perk(self, perk, unlocked_by=None):
        self._award_rewards(perk)
        self._award_buffs(perk)
        self._award_loots(perk.loots_on_unlock)
        if perk.temporary_perk_information is not None and not self._set_up_temporary_perk_timer(perk):
            return
        self._perk_unlocked_callbacks[perk.associated_bucks_type](perk)
        timestamp = services.time_service().sim_now
        self._unlocked_perks[perk.associated_bucks_type][perk] = PerkData(unlocked_by, timestamp, True)
        for sim_info in self._owner_sim_info_gen():
            services.get_event_manager().process_event(TestEvent.BucksPerkUnlocked, sim_info=sim_info)
        for linked_perk in perk.linked_perks:
            if not self.is_perk_unlocked(linked_perk):
                self.unlock_perk(linked_perk, unlocked_by=perk)
        self._handle_unlock_telemetry(perk)
        caches.clear_all_caches()

    def _award_rewards(self, perk, **kwargs):
        if not perk.rewards:
            return
        dummy_sim = next(self._owner.sim_info_gen(), None)
        if dummy_sim is None:
            logger.error('Trying to unlock a Perk for owner {}, but there are no Sims.', self._owner)
            return
        for reward in perk.rewards:
            reward().open_reward(dummy_sim)

    def _award_loots(self, loot_list):
        resolver = SingleSimResolver(self._owner)
        for loot in loot_list:
            loot.apply_to_resolver(resolver)

    def _award_buffs(self, perk):
        if not perk.buffs_to_award:
            return
        for sim_info in self._owner_sim_info_gen():
            for buff in perk.buffs_to_award:
                sim_info.add_buff(buff.buff_type, buff_reason=buff.buff_reason)

    def _owner_sim_info_gen(self):
        yield self._owner

    def pay_for_and_unlock_perk(self, perk):
        if self.is_perk_unlocked(perk):
            logger.error('Attempting to unlock a Perk {} for owner {} that has already been unlocked.', perk, self._owner)
            return False
        if not self.try_modify_bucks(perk.associated_bucks_type, -perk.unlock_cost):
            logger.error('Attempting to unlock a Perk {} for owner {} that they cannot afford.', perk, self._owner)
            return False
        self.unlock_perk(perk)
        if perk.lock_on_purchase is not None:
            for perk_to_lock in perk.lock_on_purchase:
                if self.is_perk_unlocked(perk_to_lock):
                    self.lock_perk(perk_to_lock)
        active_sim = services.get_active_sim()
        services.get_event_manager().process_event(TestEvent.PerkPurchased, sim_info=active_sim.sim_info, bucks_type=perk.associated_bucks_type, perk=perk)
        return True

    def lock_perk(self, perk, refund_cost=False, distribute=True):
        if not self.is_perk_unlocked(perk):
            logger.error('Attempting to lock a Perk {} for owner {} that has not been unlocked.', perk, self._owner)
            return
        if perk.temporary_perk_information is not None:
            self.deactivate_temporary_perk_timer(perk, cancel_remaining_time=True)
        if perk.buffs_to_award:
            for sim_info in self._owner_sim_info_gen():
                for buff in perk.buffs_to_award:
                    sim_info.remove_buff_by_type(buff.buff_type)
        self._award_loots(perk.loots_on_lock)
        if refund_cost:
            self.try_modify_bucks(perk.associated_bucks_type, perk.unlock_cost, distribute=distribute)
        self._unlocked_perks[perk.associated_bucks_type][perk] = PerkData(None, 0, False)
        self._recently_locked_perks[perk.associated_bucks_type].add(perk)
        self._handle_lock_telemetry(perk)

    def lock_all_perks(self, bucks_type, refund_cost=False):
        for perk in list(self._unlocked_perks[bucks_type]):
            self.lock_perk(perk, refund_cost=refund_cost, distribute=False)
        self.distribute_bucks(bucks_type)

    def activate_stored_temporary_perk_timers_of_type(self, bucks_type):
        if bucks_type not in self._inactive_perk_timers:
            return
        for (perk, remaining_ticks) in list(self._inactive_perk_timers[bucks_type].items()):
            self._set_up_temporary_perk_timer(perk, remaining_ticks=remaining_ticks)
            del self._inactive_perk_timers[bucks_type][perk]

    def deactivate_all_temporary_perk_timers_of_type(self, bucks_type):
        if bucks_type not in self._active_perk_timers:
            return
        for perk in list(self._active_perk_timers[bucks_type]):
            self.deactivate_temporary_perk_timer(perk)

    def deactivate_temporary_perk_timer(self, perk, cancel_remaining_time=False):
        if perk in self._active_perk_timers[perk.associated_bucks_type]:
            perk_timer_handle = self._active_perk_timers[perk.associated_bucks_type][perk]
            if perk_timer_handle is not None:
                current_time = services.time_service().sim_now
                remaining_ticks = (perk_timer_handle.finishing_time - current_time).in_ticks()
                if not cancel_remaining_time:
                    self._inactive_perk_timers[perk.associated_bucks_type][perk] = remaining_ticks
                perk_timer_handle.cancel()
            del self._active_perk_timers[perk.associated_bucks_type][perk]
        elif cancel_remaining_time:
            del self._inactive_perk_timers[perk.associated_bucks_type][perk]

    def _set_up_temporary_perk_timer(self, perk, remaining_ticks=None):
        if perk.temporary_perk_information is None:
            logger.error('Attempting to setup and alarm for a Perk that is not temporary. {}', perk)
            return False
        if perk in self._active_perk_timers[perk.associated_bucks_type]:
            logger.error('Attempting to add a timer for a temporary Perk that arleady has a timer set up. {}', perk)
            return False
        if remaining_ticks is None:
            time_until_perk_lock = interval_in_sim_hours(perk.temporary_perk_information.duration)
        else:
            time_until_perk_lock = clock.TimeSpan(remaining_ticks)
        perk_timer_handle = alarms.add_alarm(self, time_until_perk_lock, lambda _: self.lock_perk(perk), cross_zone=True)
        self._active_perk_timers[perk.associated_bucks_type][perk] = perk_timer_handle
        return True

    def all_perks_of_type_gen(self, bucks_type):
        perks_instance_manager = services.get_instance_manager(sims4.resources.Types.BUCKS_PERK)
        for perk in perks_instance_manager.types.values():
            if perk.associated_bucks_type is bucks_type:
                yield perk

    def all_perks_of_type_with_lock_state_gen(self, bucks_type, is_unlocked):
        perks_instance_manager = services.get_instance_manager(sims4.resources.Types.BUCKS_PERK)
        for perk in perks_instance_manager.types.values():
            if perk.associated_bucks_type is bucks_type and self.is_perk_unlocked(perk) is is_unlocked:
                yield perk

    def get_disabled_tooltip_for_perk(self, perk):
        if perk.temporary_perk_information is not None:
            if perk.temporary_perk_information.unlocked_tooltip is not None:
                return perk.temporary_perk_information.unlocked_tooltip()
            return
        perk_data = self._unlocked_perks[perk.associated_bucks_type][perk]
        if perk_data.unlocked_by is not None:
            return BucksPerkTunables.LINKED_PERK_UNLOCKED_TOOLTIP(perk_data.unlocked_by.display_name())
        return BucksPerkTunables.PERK_UNLOCKED_TOOLTIP()

    def send_perks_list_for_bucks_type(self, bucks_type, sort_key=None, reverse=True):
        bucks_msg = Dialog_pb2.GameplayPerkList()
        bucks_msg.bucks_type = bucks_type
        resolver = SingleSimResolver(self._owner)
        perk_messages = []
        for perk in self.all_perks_of_type_gen(bucks_type):
            perk_message = Dialog_pb2.GameplayPerk()
            perk_message.id = perk.guid64
            perk_message.display_name = perk.display_name()
            perk_message.description = self._get_description_string(perk)
            perk_message.icon = create_icon_info_msg(IconInfoData(icon_resource=perk.icon.key))
            perk_message.cost = perk.unlock_cost
            if bucks_type not in self._bucks:
                self._bucks[bucks_type] = 0
            perk_message.affordable = self._bucks[bucks_type] >= perk.unlock_cost
            perk_message.ui_display_flags = perk.ui_display_flags
            if perk.required_unlocks is not None:
                locked = False
                for required_perk in perk.required_unlocks:
                    if not self.is_perk_unlocked(required_perk):
                        locked = True
                    perk_message.required_perks.append(required_perk.guid64)
                perk_message.locked = locked
            result = perk.available_for_puchase_tests.run_tests(resolver=resolver, search_for_tooltip=True)
            if not result:
                perk_message.locked_from_tests = True
                if result.tooltip is not None:
                    perk_message.disabled_tooltip = result.tooltip(self._owner)
            unlocked = self.is_perk_unlocked(perk)
            if unlocked:
                perk_message.purchased = unlocked
                timestamp = self._get_perk_unlock_timestamp(perk)
                if timestamp is not None:
                    perk_message.unlock_timestamp = timestamp
            if self.is_perk_recently_locked(perk):
                perk_message.recently_locked = True
            if unlocked or unlocked:
                disabled_tooltip = self.get_disabled_tooltip_for_perk(perk)
                if disabled_tooltip is not None:
                    perk_message.disabled_tooltip = disabled_tooltip
            if perk.lock_on_purchase:
                for perk_to_lock in perk.lock_on_purchase:
                    perk_message.lock_on_purchase.append(perk_to_lock.guid64)
            if perk.next_level_perk is not None:
                perk_message.next_perk_id = perk.next_level_perk.guid64
            if perk.conflicting_perks is not None:
                for conflicting_perk in perk.conflicting_perks:
                    perk_message.conflicting_perks.append(conflicting_perk.guid64)
            perk_messages.append(perk_message)
        if sort_key is not None:
            perk_messages.sort(key=sort_key, reverse=reverse)
        bucks_msg.perk_list.extend(perk_messages)
        op = shared_messages.create_message_op(bucks_msg, Consts_pb2.MSG_GAMEPLAY_PERK_LIST)
        Distributor.instance().add_op_with_no_owner(op)

    def _get_description_string(self, perk):
        if perk.undiscovered_description is None or perk in self._unlocked_perks[perk.associated_bucks_type]:
            return perk.perk_description()
        return perk.undiscovered_description()

    def on_all_households_and_sim_infos_loaded(self):
        for bucks_type in self._bucks.keys():
            self.try_modify_bucks(bucks_type, 0)

    def on_zone_load(self):
        for bucks_type in self._bucks.keys():
            self.distribute_bucks(bucks_type)
        for perk_dict in self._unlocked_perks.values():
            for (perk, perk_data) in perk_dict.items():
                if perk_data.currently_unlocked:
                    self._award_buffs(perk)

    def distribute_bucks(self, bucks_type):
        raise NotImplementedError

    def try_modify_bucks(self, bucks_type, amount, distribute=True, reason=None, force_refund=False):
        if bucks_type in self._bucks:
            new_amount = self._bucks[bucks_type] + amount
        else:
            new_amount = amount
        if new_amount < 0:
            if force_refund:
                perks_to_lock = []
                for recently_unlocked_perk in self._most_recently_acquired_perks_gen(bucks_type):
                    new_amount += recently_unlocked_perk.unlock_cost
                    perks_to_lock.append(recently_unlocked_perk)
                    if new_amount >= 0:
                        break
                return False
                for perk in perks_to_lock:
                    self.lock_perk(perk, refund_cost=False)
            else:
                return False
        new_amount = min(new_amount, self.MAX_BUCKS_ALLOWED)
        self._bucks[bucks_type] = new_amount
        self._bucks_modified_callbacks[bucks_type]()
        if distribute:
            self.distribute_bucks(bucks_type)
            if amount > 0:
                self._handle_modify_bucks_telemetry(bucks_type, amount, new_amount, source=reason)
        return True

    def validate_perks(self, bucks_type, current_rank):
        pass

    def _most_recently_acquired_perks_gen(self, bucks_type):
        yield from sorted(self._unlocked_perks[bucks_type], key=lambda k: self._unlocked_perks[bucks_type][k].timestamp, reverse=True)

    def is_perk_recently_locked(self, perk):
        if perk.associated_bucks_type in self._recently_locked_perks and perk in self._recently_locked_perks[perk.associated_bucks_type]:
            return True
        return False

    def reset_recently_locked_perks(self, bucks_type=None):
        if bucks_type is None:
            self._recently_locked_perks.clear()
            return
        if bucks_type in self._recently_locked_perks:
            del self._recently_locked_perks[bucks_type]

    def _handle_modify_bucks_telemetry(self, type_gained, amount_gained, new_total, source=None):
        with telemetry_helper.begin_hook(bucks_telemetry_writer, TELEMETRY_HOOK_BUCKS_GAIN) as hook:
            hook.write_int(TELEMETRY_FIELD_BUCKS_TYPE, type_gained)
            hook.write_int(TELEMETRY_FIELD_BUCKS_AMOUNT, amount_gained)
            hook.write_int(TELEMETRY_FIELD_BUCKS_TOTAL, new_total)
            if source is not None:
                hook.write_string(TELEMETRY_FIELD_BUCKS_SOURCE, source)

    def _handle_unlock_telemetry(self, perk):
        new_bucks_total = self.get_bucks_amount_for_type(perk.associated_bucks_type)
        with telemetry_helper.begin_hook(bucks_telemetry_writer, TELEMETRY_HOOK_BUCKS_SPEND) as hook:
            hook.write_int(TELEMETRY_FIELD_BUCKS_TYPE, perk.associated_bucks_type)
            hook.write_int(TELEMETRY_FIELD_BUCKS_AMOUNT, perk.unlock_cost)
            hook.write_int(TELEMETRY_FIELD_BUCKS_TOTAL, new_bucks_total)
            hook.write_guid(TELEMETRY_FIELD_BUCKS_SOURCE, perk.guid64)

    def _handle_lock_telemetry(self, perk):
        new_bucks_total = self.get_bucks_amount_for_type(perk.associated_bucks_type)
        with telemetry_helper.begin_hook(bucks_telemetry_writer, TELEMETRY_HOOK_BUCKS_REFUND) as hook:
            hook.write_int(TELEMETRY_FIELD_BUCKS_TYPE, perk.associated_bucks_type)
            hook.write_int(TELEMETRY_FIELD_BUCKS_AMOUNT, perk.unlock_cost)
            hook.write_int(TELEMETRY_FIELD_BUCKS_TOTAL, new_bucks_total)
            hook.write_guid(TELEMETRY_FIELD_BUCKS_SOURCE, perk.guid64)

    def load_data(self, owner_proto):
        bucks_perk_manager = services.get_instance_manager(sims4.resources.Types.BUCKS_PERK)
        for bucks_data in owner_proto.bucks_data:
            self.try_modify_bucks(bucks_data.bucks_type, bucks_data.amount, distribute=False)
            for perk_data in bucks_data.unlocked_perks:
                perk_ref = bucks_perk_manager.get(perk_data.perk)
                if perk_ref is None:
                    logger.info('Trying to load unavailable BUCKS_PERK resource: {}', perk_data.perk)
                else:
                    unlocked_by = bucks_perk_manager.get(perk_data.unlock_reason)
                    timestamp = DateAndTime(perk_data.timestamp)
                    self._unlocked_perks[perk_ref.associated_bucks_type][perk_ref] = PerkData(unlocked_by, timestamp, perk_data.currently_unlocked)
                    if not perk_data.currently_unlocked:
                        pass
                    else:
                        self._award_buffs(perk_ref)
                        if perk_data.time_left:
                            self._set_up_temporary_perk_timer(perk_ref, perk_data.time_left)

    def save_data(self, owner_msg):
        for bucks_type in BucksType:
            with self._deactivate_perk_timers(bucks_type), ProtocolBufferRollback(owner_msg.bucks_data) as bucks_data:
                bucks_data.bucks_type = bucks_type
                bucks_data.amount = self._bucks.get(bucks_type, 0)
                for (perk, perk_data) in self._unlocked_perks[bucks_type].items():
                    with ProtocolBufferRollback(bucks_data.unlocked_perks) as unlocked_perks:
                        unlocked_perks.perk = perk.guid64
                        unlocked_perks.timestamp = perk_data.timestamp
                        unlocked_perks.currently_unlocked = perk_data.currently_unlocked
                        if perk_data.unlocked_by is not None:
                            unlocked_perks.unlock_reason = perk_data.unlocked_by.guid64
                        if perk in self._inactive_perk_timers[bucks_type]:
                            unlocked_perks.time_left = self._inactive_perk_timers[bucks_type][perk]

    @contextmanager
    def _deactivate_perk_timers(self, bucks_type):
        if self._active_perk_timers[bucks_type]:
            if self._inactive_perk_timers[bucks_type]:
                logger.error('Household {} has both active and inactive temporary Perk timers. This is not expected and will cause save/load issues.', self._owner)
            self.deactivate_all_temporary_perk_timers_of_type(bucks_type)
            had_active_timers = True
        else:
            had_active_timers = False
        try:
            yield None
        finally:
            if had_active_timers:
                self.activate_stored_temporary_perk_timers_of_type(bucks_type)

    def award_unlocked_perks(self, bucks_type, sim_info=None):
        for perk in self.all_perks_of_type_gen(bucks_type):
            if self.is_perk_unlocked(perk):
                self._award_rewards(perk, sim_info=sim_info)
                self._award_buffs(perk)
