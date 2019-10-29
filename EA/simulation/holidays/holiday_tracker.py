from _collections import defaultdictimport itertoolsfrom protocolbuffers import DistributorOps_pb2from date_and_time import DateAndTime, create_time_spanfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom drama_scheduler.drama_node_types import DramaNodeTypefrom holidays.holiday_globals import HolidayTuningfrom holidays.holiday_ops import SendHolidayInfo, SendActiveHolidayInfofrom situations.situation_serialization import SituationSeedimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Holiday', default_owner='jjacobson')
class HolidayTracker:

    def __init__(self, owner):
        self._owner = owner
        self._pre_day_holiday_id = None
        self._active_holiday_id = None
        self._traditions = defaultdict(list)
        self._situation_holiday_type = None
        self._situation_holiday_time = None
        self._situation_seeds = []
        self._cancelled_holiday = None
        self._cancelled_holiday_time = None

    @property
    def upcoming_holiday_id(self):
        return self._pre_day_holiday_id

    @property
    def active_holiday_id(self):
        return self._active_holiday_id

    def get_active_or_upcoming_holiday(self):
        if self._active_holiday_id is None:
            return self._pre_day_holiday_id
        return self._active_holiday_id

    def cancel_holiday(self, holiday_id):
        self._cancelled_holiday = holiday_id
        self._cancelled_holiday_time = services.time_service().sim_now

    def is_holiday_cancelled(self, holiday_id):
        if holiday_id == self._cancelled_holiday and self._cancelled_holiday_time + create_time_span(days=1) > services.time_service().sim_now:
            return True
        self._cancelled_holiday = None
        self._cancelled_holiday_time = None
        return False

    def shutdown(self):
        if self._pre_day_holiday_id is not None:
            for tradition in self._traditions[self._pre_day_holiday_id]:
                tradition.deactivate_pre_holiday()
        if self._active_holiday_id is not None:
            for tradition in self._traditions[self._active_holiday_id]:
                tradition.deactivate_holiday()
        self._pre_day_holiday_id = None
        self._active_holiday_id = None
        self._traditions = None

    def set_holiday_situation_seeds(self, situation_seeds):
        self._situation_seeds = [seed.get_deserializable_seed_from_serializable_seed() for seed in situation_seeds]
        self._situation_holiday_type = self._active_holiday_id
        self._situation_holiday_time = services.time_service().sim_now

    def save_holiday_tracker(self, msg):
        if self._cancelled_holiday is not None:
            msg.cancelled_holiday_type = self._cancelled_holiday
            msg.cancelled_holiday_time = self._cancelled_holiday_time.absolute_ticks()
        if self._active_holiday_id is not None:
            msg.situation_holiday_type = self._active_holiday_id
            msg.situation_holiday_time = services.time_service().sim_now.absolute_ticks()
            for situation in services.get_zone_situation_manager().get_situations_by_type(HolidayTuning.HOLIDAY_SITUATION):
                with ProtocolBufferRollback(msg.situations) as seed_proto:
                    seed = situation.save_situation()
                    seed.serialize_to_proto(seed_proto)

    def load_holiday_tracker(self, msg):
        if msg.HasField('cancelled_holiday_type'):
            self._cancelled_holiday = msg.cancelled_holiday_type
            self._cancelled_holiday_time = DateAndTime(msg.cancelled_holiday_time)
            if self._cancelled_holiday_time + create_time_span(days=1) < services.time_service().sim_now:
                self._cancelled_holiday = None
                self._cancelled_holiday_time = None
        if msg.HasField('situation_holiday_type'):
            self._situation_holiday_type = msg.situation_holiday_type
            self._situation_holiday_time = DateAndTime(msg.situation_holiday_time)
            for situation_seed_proto in msg.situations:
                seed = SituationSeed.deserialize_from_proto(situation_seed_proto)
                if seed is not None:
                    self._situation_seeds.append(seed)

    def load_holiday_situations(self, holiday_id):
        owner_sims = [sim_info for sim_info in self._owner.sim_infos if sim_info.is_human]
        situation_ids = []
        if self._situation_holiday_type == holiday_id:
            now = services.time_service().sim_now
            if self._situation_holiday_time + create_time_span(days=1) >= now:
                situation_manager = services.get_zone_situation_manager()
                sim_info_manager = services.sim_info_manager()
                for situation_seed in self._situation_seeds:
                    sim_info = sim_info_manager.get(situation_seed.guest_list.host_sim_id)
                    if sim_info in owner_sims:
                        situation_id = situation_manager.create_situation_from_seed(situation_seed)
                        if situation_id is not None:
                            situation_ids.append(situation_id)
                            owner_sims.remove(sim_info)
        self._situation_seeds.clear()
        return (situation_ids, owner_sims)

    def preactivate_holiday(self, holiday_id):
        if self._pre_day_holiday_id is not None:
            logger.error('Holiday {} is already in pre-day holiday state.  Removing one holiday from the pre-day holiday state should occur before starting a different one.', self._pre_day_holiday_id)
            return
        self._pre_day_holiday_id = holiday_id
        for tradition_type in services.holiday_service().get_holiday_traditions(holiday_id):
            tradition = tradition_type()
            self._traditions[holiday_id].append(tradition)
            tradition.activate_pre_holiday()

    def deactivate_pre_holiday(self):
        if self._pre_day_holiday_id is None:
            logger.error("Trying to deactivate pre_holiday when there isn't one in that state.")
            return
        for tradition in self._traditions[self._pre_day_holiday_id]:
            tradition.deactivate_pre_holiday()
        del self._traditions[self._pre_day_holiday_id]
        self._pre_day_holiday_id = None

    def activate_holiday(self, holiday_id, from_load=False):
        if self._active_holiday_id is not None:
            holiday_manager = services.get_instance_manager(sims4.resources.Types.HOLIDAY_DEFINITION)
            active_holiday = holiday_manager.get(self._active_holiday_id)
            if active_holiday is None:
                active_holiday = self._active_holiday_id
            new_holiday = holiday_manager.get(holiday_id)
            if new_holiday is None:
                new_holiday = holiday_id
            logger.error('Trying to start holiday, {}, when holiday, {}, is already active.  Removing one holiday from the active holiday state should occur before starting a different one.', new_holiday, active_holiday)
            return
        self._active_holiday_id = holiday_id
        holiday_service = services.holiday_service()
        if self._pre_day_holiday_id == holiday_id:
            self._pre_day_holiday_id = None
            for tradition in self._traditions[holiday_id]:
                tradition.activate_holiday(from_load=from_load)
        else:
            for tradition_type in holiday_service.get_holiday_traditions(holiday_id):
                tradition = tradition_type()
                self._traditions[holiday_id].append(tradition)
                tradition.activate_holiday(from_load=from_load)
        self.send_active_holiday_info_message(DistributorOps_pb2.SendActiveHolidayInfo.START)

    def deactivate_holiday(self):
        if self._active_holiday_id is None:
            logger.error("Trying to deactivate holiday when there isn't one in that state.")
            return
        for tradition in self._traditions[self._active_holiday_id]:
            tradition.deactivate_holiday()
        self.send_active_holiday_info_message(DistributorOps_pb2.SendActiveHolidayInfo.END)
        del self._traditions[self._active_holiday_id]
        self._active_holiday_id = None

    def get_additional_holiday_walkbys(self, predicate=lambda _: True):
        weighted_situations = []
        if self._active_holiday_id is not None:
            for tradition in self._traditions[self._active_holiday_id]:
                weighted_situations.extend(tradition.get_additional_walkbys(predicate=predicate))
        return weighted_situations

    def send_active_holiday_info_message(self, update_type):
        if self._active_holiday_id is None:
            logger.error("Trying to send active holiday info to UI when there isn't one.")
            return
        holiday_service = services.holiday_service()
        send_active_holiday_info = SendActiveHolidayInfo(update_type, self._active_holiday_id, holiday_service.get_holiday_display_name(self._active_holiday_id), holiday_service.get_holiday_display_icon(self._active_holiday_id), holiday_service.get_holiday_time_off_work(self._active_holiday_id), holiday_service.get_holiday_time_off_school(self._active_holiday_id), holiday_service.get_holiday_traditions(self._active_holiday_id), holiday_service.can_holiday_be_modified(self._active_holiday_id), holiday_service.get_decoration_preset(self._active_holiday_id))
        distributor = Distributor.instance()
        distributor.add_op_with_no_owner(send_active_holiday_info)

    def get_active_traditions(self):
        if self._active_holiday_id is None:
            return tuple()
        return tuple(self._traditions[self._active_holiday_id])

    def get_active_holiday_display_name(self):
        if self._active_holiday_id is None:
            return
        return services.holiday_service().get_holiday_display_name(self._active_holiday_id)

    def get_active_holiday_display_icon(self):
        if self._active_holiday_id is None:
            return
        return services.holiday_service().get_holiday_display_icon(self._active_holiday_id)

    def get_active_holiday_business_price_multiplier(self, business_type):
        if self._active_holiday_id is None:
            return 1
        base_multiplier = 1
        for tradition in self.get_active_traditions():
            base_multiplier *= tradition.get_buiness_multiplier(business_type)
        return base_multiplier

    def on_holiday_modified(self, holiday_id, added_traditions, removed_traditions, ordered_traditions, theme_updated):
        if self._pre_day_holiday_id == holiday_id:
            if removed_traditions:
                for tradition in tuple(self._traditions[self._pre_day_holiday_id]):
                    if type(tradition) in removed_traditions:
                        tradition.deactivate_pre_holiday()
                        self._traditions[holiday_id].remove(tradition)
            for tradition_type in added_traditions:
                tradition = tradition_type()
                self._traditions[holiday_id].append(tradition)
                tradition.activate_pre_holiday()
        elif self._active_holiday_id == holiday_id:
            if removed_traditions:
                for tradition in tuple(self._traditions[self._active_holiday_id]):
                    if type(tradition) in removed_traditions:
                        tradition.deactivate_holiday(from_customization=True)
                        self._traditions[holiday_id].remove(tradition)
            for tradition_type in added_traditions:
                tradition = tradition_type()
                self._traditions[holiday_id].append(tradition)
                tradition.activate_holiday(from_customization=True)
            for situation in services.get_zone_situation_manager().get_situations_by_type(HolidayTuning.HOLIDAY_SITUATION):
                situation.on_holiday_data_changed(added_traditions, removed_traditions, ordered_traditions)
            self.send_active_holiday_info_message(DistributorOps_pb2.SendActiveHolidayInfo.UPDATE)
        if theme_updated and self.get_active_or_upcoming_holiday() == holiday_id:
            lot_decoration_service = services.lot_decoration_service()
            if lot_decoration_service is not None:
                lot_decoration_service.refresh_neighborhood_decorations()
        drama_scheduler = services.drama_scheduler_service()
        calendar_service = services.calendar_service()
        for drama_node in itertools.chain(drama_scheduler.active_nodes_gen(), drama_scheduler.scheduled_nodes_gen()):
            if drama_node.drama_node_type != DramaNodeType.HOLIDAY:
                pass
            elif drama_node.holiday_id != holiday_id:
                pass
            else:
                calendar_service.update_on_calendar(drama_node, advance_notice_time=HolidayTuning.HOLIDAY_DURATION())

    def on_sim_added(self, sim_info):
        if self._active_holiday_id is None:
            return
        drama_scheduler = services.drama_scheduler_service()
        for drama_node in drama_scheduler.active_nodes_gen():
            if drama_node.drama_node_type != DramaNodeType.HOLIDAY:
                pass
            elif drama_node.holiday_id != self._active_holiday_id:
                pass
            else:
                drama_node.on_sim_added(sim_info)
