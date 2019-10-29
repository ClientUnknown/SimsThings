from _collections import defaultdictfrom protocolbuffers import Business_pb2, ResourceKey_pb2, DistributorOps_pb2from distributor.ops import GenericProtocolBufferOpfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom gsi_handlers import business_handlersfrom objects import ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZEDimport servicesimport sims4.mathlogger = sims4.log.Logger('Business', default_owner='trevor')
class BusinessCustomerData:

    def __init__(self, business_manager, sim_id, from_load=False):
        self._business_manager = business_manager
        self._sim_id = sim_id
        self._star_rating_vfx_handle = None
        self._critic_banner_vfx_handle = None
        self._buff_bucket_totals = defaultdict(float)
        self._last_rating_change_buff_id = None
        self._buffs_to_load = None
        if not from_load:
            self._post_sim_info_loaded_init()

    def _post_sim_info_loaded_init(self):
        star_rating = self._calculate_star_rating_from_buff_bucket_totals()
        self.set_star_rating_stat_value(star_rating)
        self._trigger_star_vfx_change(from_init=True)
        self._add_buff_callbacks()
        if self._last_rating_change_buff_id is None:
            return
        for (buff, buff_data) in self._business_manager.tuning_data.customer_star_rating_buff_data.items():
            if buff.guid64 == self._last_rating_change_buff_id:
                self._send_customer_review_event_message(buff_data.buff_bucket, buff_data.buff_bucket_delta > 0)
                break

    def _add_buff_callbacks(self):
        buff_manager = services.sim_info_manager().get(self._sim_id).Buffs
        buff_manager.on_buff_added.append(self._on_buff_added)
        buff_manager.on_buff_removed.append(self._on_buff_removed)

    def get_star_rating(self):
        return sims4.math.clamp(self._business_manager.tuning_data.min_and_max_star_rating.lower_bound, int(self.get_star_rating_stat_value()), self._business_manager.tuning_data.min_and_max_star_rating.upper_bound)

    def get_star_rating_stat_value(self):
        if self._business_manager.tuning_data.customer_star_rating_statistic is None:
            return
        sim_info = services.sim_info_manager().get(self._sim_id)
        stat_instance = sim_info.get_statistic(self._business_manager.tuning_data.customer_star_rating_statistic, add=True)
        return stat_instance.get_value()

    def set_star_rating_stat_value(self, value):
        if self._business_manager.tuning_data.customer_star_rating_statistic is None:
            return
        sim_info = services.sim_info_manager().get(self._sim_id)
        sim_info.add_statistic(self._business_manager.tuning_data.customer_star_rating_statistic, value)

    @property
    def buff_bucket_totals(self):
        return self._buff_bucket_totals

    def on_remove(self):
        sim_info = services.sim_info_manager().get(self._sim_id)
        if sim_info is not None:
            sim_info.Buffs.on_buff_added.remove(self._on_buff_added)
            sim_info.Buffs.on_buff_removed.remove(self._on_buff_removed)
            tags_to_remove = self._business_manager.tuning_data.customer_buffs_to_remove_tags
            if tags_to_remove:
                sim_info.remove_buffs_by_tags(tags_to_remove)
        self._stop_star_rating_vfx()
        self._stop_critic_banner_vfx()
        self._trigger_final_star_rating_vfx()

    def _on_buff_added(self, buff_type, sim_id):
        for (buff, buff_data) in self._business_manager.tuning_data.customer_star_rating_buff_data.items():
            if buff_type is buff.buff_type:
                buff_bucket = buff_data.buff_bucket
                if business_handlers.business_archiver.enabled:
                    business_handlers.archive_business_event('Customer', None, 'Buff Added:{} bucket:{}'.format(buff_type, buff_bucket), sim_id=sim_id)
                self._buff_bucket_totals[buff_bucket] += buff_data.buff_bucket_delta
                if buff_data.update_star_rating_on_add:
                    self._last_rating_change_buff_id = buff.guid64
                    self._update_star_rating(buff_data)
                return

    def _on_buff_removed(self, buff_type, sim_id):
        for (buff, buff_data) in self._business_manager.tuning_data.customer_star_rating_buff_data.items():
            if buff_type is buff.buff_type:
                buff_bucket = buff_data.buff_bucket
                if business_handlers.business_archiver.enabled:
                    business_handlers.archive_business_event('Customer', None, 'Buff Removed:{} bucket:{}'.format(buff_type, buff_bucket), sim_id=sim_id)
                self._buff_bucket_totals[buff_bucket] -= buff_data.buff_bucket_delta
                if buff_data.update_star_rating_on_remove:
                    self._last_rating_change_buff_id = buff.guid64
                    self._update_star_rating(buff_data)
                return

    def _stop_star_rating_vfx(self):
        if self._star_rating_vfx_handle is not None:
            self._star_rating_vfx_handle.stop()
            self._star_rating_vfx_handle = None

    def _stop_critic_banner_vfx(self):
        if self._critic_banner_vfx_handle is not None:
            self._critic_banner_vfx_handle.stop()
            self._critic_banner_vfx_handle = None

    def _trigger_star_vfx_change(self, from_init=False):
        sim_info = services.sim_info_manager().get(self._sim_id)
        if sim_info is None:
            logger.error('Trying to trigger vfx on a customer with no sim info. Customer ID = {}', self._sim_id)
            return
        sim = sim_info.get_sim_instance()
        if sim is None:
            return
        tuning_data = self._business_manager.tuning_data
        star_rating = self.get_star_rating()
        is_critic = tuning_data.critic is not None and sim.has_trait(tuning_data.critic.critic_trait)
        if is_critic:
            vfx_mapping = tuning_data.critic.critic_star_rating_vfx_mapping
            if from_init:
                self._critic_banner_vfx_handle = tuning_data.critic.critic_banner_vfx(sim)
                self._critic_banner_vfx_handle.start()
        else:
            vfx_mapping = tuning_data.customer_star_rating_vfx_mapping
        star_rating_vfx_tuning = vfx_mapping.get(star_rating)
        if from_init:
            star_vfx = star_rating_vfx_tuning.initial_vfx
        else:
            star_vfx = star_rating_vfx_tuning.rating_change_vfx
        self._stop_star_rating_vfx()
        self._star_rating_vfx_handle = star_vfx(sim)
        self._star_rating_vfx_handle.start()
        if business_handlers.business_archiver.enabled:
            business_handlers.archive_business_event('Customer', sim, 'Star rating change - playing effect: {} , from init: {}'.format(star_vfx.effect_name, from_init))
        if tuning_data.customer_max_star_rating_vfx is not None and star_rating == tuning_data.min_and_max_star_rating.upper_bound:
            max_star_vfx = tuning_data.customer_max_star_rating_vfx(sim)
            max_star_vfx.start()

    def _trigger_final_star_rating_vfx(self):
        if self._business_manager.tuning_data.customer_final_star_rating_vfx is None:
            return
        sim_info = services.sim_info_manager().get(self._sim_id)
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS_EXCEPT_UNINITIALIZED)
        if sim is None:
            logger.error("Trying to trigger the final star rating vfx on a customer that isn't instanced. {}", self._sim_id)
            return
        if not sim.is_hidden():
            final_star_vfx = self._business_manager.tuning_data.customer_final_star_rating_vfx(sim)
            final_star_vfx.start()

    def _calculate_star_rating_from_buff_bucket_totals(self):
        if not self._buff_bucket_totals:
            return self._business_manager.tuning_data.default_customer_star_rating
        actual_bucket_total = 0
        for bucket_type in self._business_manager.tuning_data.customer_star_rating_buff_bucket_data:
            actual_bucket_total += self._business_manager.get_interpolated_buff_bucket_value(bucket_type, self._buff_bucket_totals[bucket_type])
        if business_handlers.business_archiver.enabled:
            sim_info = services.sim_info_manager().get(self._sim_id)
            business_handlers.archive_business_event('Customer', sim_info, 'Calculating Star Rating: Bucket Total:{}'.format(actual_bucket_total))
        return sims4.math.clamp(self._business_manager.tuning_data.min_and_max_star_rating.lower_bound, self._business_manager.tuning_data.customer_star_buff_bucket_to_rating_curve.get(actual_bucket_total), self._business_manager.tuning_data.min_and_max_star_rating.upper_bound)

    def _update_star_rating(self, buff_data):
        new_star_rating = self._calculate_star_rating_from_buff_bucket_totals()
        self._set_star_rating(new_star_rating, buff_data)

    def _set_star_rating(self, new_star_rating_value, buff_data):
        sim = services.sim_info_manager().get(self._sim_id).get_sim_instance()
        if sim is None:
            logger.error("Trying to set a customer's star rating but the sim isn't instanced. {}", self._sim_id)
            return
        buff_bucket = buff_data.buff_bucket
        old_star_rating_value = self.get_star_rating_stat_value()
        old_star_rating = self.get_star_rating()
        self.set_star_rating_stat_value(new_star_rating_value)
        new_star_rating = self.get_star_rating()
        bucket_data = self._business_manager.tuning_data.customer_star_rating_buff_bucket_data.get(buff_bucket)
        is_positive = buff_data.buff_bucket_delta > 0
        vfx_to_play = None
        if is_positive:
            if self._business_manager.tuning_data.customer_star_rating_vfx_increase_arrow is not None:
                self._business_manager.tuning_data.customer_star_rating_vfx_increase_arrow(sim).start_one_shot()
            vfx_to_play = bucket_data.positive_bucket_vfx
        else:
            if self._business_manager.tuning_data.customer_star_rating_vfx_decrease_arrow is not None:
                self._business_manager.tuning_data.customer_star_rating_vfx_decrease_arrow(sim).start_one_shot()
            vfx_to_play = bucket_data.negative_bucket_vfx
        if vfx_to_play is not None:
            vfx_to_play(sim).start_one_shot()
        if business_handlers.business_archiver.enabled:
            if vfx_to_play is not None:
                business_handlers.archive_business_event('Customer', sim, 'Star rating value change: old_value:{} new_value:{} - playing effect: {}'.format(old_star_rating_value, new_star_rating_value, vfx_to_play.effect_name))
            else:
                business_handlers.archive_business_event('Customer', sim, 'No Star rating value change: current_value:{}'.format(new_star_rating_value))
        if old_star_rating != new_star_rating:
            self._trigger_star_vfx_change()
        self._send_customer_review_event_message(buff_bucket, is_positive=is_positive)

    def save_data(self, customer_save_data):
        sim_info = services.sim_info_manager().get(self._sim_id)
        if sim_info is None:
            logger.error('Trying to save customer data for a sim with no sim info. {}', self._sim_id)
            return
        customer_save_data.customer_id = self._sim_id
        customer_save_data.customer_buffs.extend(buff.guid64 for buff in sim_info.get_all_buffs_with_tag(self._business_manager.tuning_data.customer_buffs_to_save_tag))
        for (buff_bucket, bucket_total) in self._buff_bucket_totals.items():
            with ProtocolBufferRollback(customer_save_data.buff_bucket_totals) as bucket_totals_data:
                bucket_totals_data.buff_bucket = buff_bucket
                bucket_totals_data.buff_bucket_total = bucket_total
        if self._last_rating_change_buff_id is not None:
            customer_save_data.last_buff_id = self._last_rating_change_buff_id

    def load_data(self, customer_save_data):
        for bucket_save_data in customer_save_data.buff_bucket_totals:
            self._buff_bucket_totals[bucket_save_data.buff_bucket] = bucket_save_data.buff_bucket_total
        self._buffs_to_load = []
        self._buffs_to_load.extend(customer_save_data.customer_buffs)
        self._last_rating_change_buff_id = customer_save_data.last_buff_id

    def setup_customer(self):
        if self._buffs_to_load is not None:
            sim_info = services.sim_info_manager().get(self._sim_id)
            if sim_info.is_instanced():
                buff_manager = services.buff_manager()
                for buff_id in self._buffs_to_load:
                    buff = buff_manager.get(buff_id)
                    if buff is not None:
                        sim_info.add_buff(buff)
                self._buffs_to_load = None
                self._post_sim_info_loaded_init()

    def on_loading_screen_animation_finished(self):
        self._trigger_star_vfx_change(from_init=True)

    def _send_customer_review_event_message(self, buff_bucket, is_positive=True):
        event_msg = Business_pb2.BusinessCustomerReviewEvent()
        buff_bucket_data = self._business_manager.tuning_data.customer_star_rating_buff_bucket_data[buff_bucket]
        event_msg.sim_id = self._sim_id
        event_msg.event_name = buff_bucket_data.bucket_positive_text() if is_positive else buff_bucket_data.bucket_negative_text()
        event_msg.event_icon = ResourceKey_pb2.ResourceKey()
        event_msg.event_icon.instance = buff_bucket_data.bucket_icon.instance
        event_msg.event_icon.group = buff_bucket_data.bucket_icon.group
        event_msg.event_icon.type = buff_bucket_data.bucket_icon.type
        event_msg.is_event_positive = is_positive
        op = GenericProtocolBufferOp(DistributorOps_pb2.Operation.BUSINESS_CUSTOMER_REVIEW_EVENT, event_msg)
        Distributor.instance().add_op_with_no_owner(op)
