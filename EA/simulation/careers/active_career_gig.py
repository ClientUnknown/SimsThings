from careers.career_gig import Gigfrom distributor.shared_messages import create_icon_info_msg, IconInfoDatafrom event_testing.resolver import SingleSimResolverfrom sims4 import mathfrom situations.situation_types import SituationMedalfrom ui.ui_dialog_picker import ObjectPickerRowimport randomimport servicesimport sims4logger = sims4.log.Logger('Gig', default_owner='bosee')
class ActiveGig(Gig):

    @classmethod
    def _verify_tuning_callback(cls):
        for cast in cls.gig_cast:
            if cast.cast_member_rel_bit is not None and cls.gig_cast_rel_bit_collection_id not in cast.cast_member_rel_bit.collection_ids:
                logger.error('Cast member relationship bit needs to be of type {} in {}', cls.gig_cast_rel_bit_collection_id, cls)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cast_list_ids = []

    def get_random_gig_event(self):
        return random.choice(self.career_events)

    def _roll_cast(self):
        resolver = SingleSimResolver(self._owner)
        blacklist_sim_ids = {sim_info.sim_id for sim_info in services.active_household()}
        blacklist_sim_ids.update(set(sim_info.sim_id for sim_info in services.sim_info_manager().instanced_sims_gen()))

        def get_sim_filter_gsi_name():
            return 'Cast member for gig.'

        for potential_cast_member in self.gig_cast:
            if not potential_cast_member.filter_test.run_tests(resolver=resolver):
                pass
            else:
                generated_result = services.sim_filter_service().submit_matching_filter(sim_filter=potential_cast_member.sim_filter, allow_yielding=False, blacklist_sim_ids=blacklist_sim_ids, gsi_source_fn=get_sim_filter_gsi_name)
                for result in generated_result:
                    cast_sim_info = result.sim_info
                    self._owner.relationship_tracker.add_relationship_bit(cast_sim_info.id, potential_cast_member.cast_member_rel_bit)
                    self._cast_list_ids.append(cast_sim_info.id)
                    blacklist_sim_ids.add(cast_sim_info.id)

    def clean_up_gig(self):
        super().clean_up_gig()
        if not services.current_zone().is_zone_shutting_down:
            for cast_id in self._cast_list_ids:
                self._owner.relationship_tracker.remove_relationship_bit_by_collection_id(cast_id, self.gig_cast_rel_bit_collection_id)
        self._cast_list_ids = []

    def set_up_gig(self):
        super().set_up_gig()
        self._roll_cast()

    def get_pay(self, payout_multiplier=None, rabbit_hole=False, **_):
        if rabbit_hole:
            return self.gig_pay.lower_bound
        return math.ceil((self.gig_pay.upper_bound - self.gig_pay.lower_bound)*payout_multiplier) + self.gig_pay.lower_bound

    def build_end_gig_dialog(self, payout):
        owner_sim = self._owner
        resolver = SingleSimResolver(owner_sim)
        medal = payout.medal
        payout_display_data = []
        self._apply_payout_stat(medal, payout_display_data)
        additional_icons = []
        for additional_payout in payout_display_data:
            additional_icons.append(create_icon_info_msg(IconInfoData(additional_payout.threshold_icon), name=additional_payout.threshold_description()))
        end_of_day_dialog = self.end_of_gig_dialog(owner_sim, resolver=resolver)
        return (end_of_day_dialog, additional_icons)

    @classmethod
    def create_picker_row(cls, description, owner=None, **kwargs):
        row_tooltip = None if cls.display_description is None else lambda *_: cls.display_description(owner)
        row = ObjectPickerRow(name=cls.display_name(owner), icon=cls.display_icon, row_description=description, row_tooltip=row_tooltip)
        return row

    def save_gig(self, gig_proto_buff):
        super().save_gig(gig_proto_buff)
        gig_proto_buff.cast_list.extend(self._cast_list_ids)

    def load_gig(self, gig_proto_buff):
        super().load_gig(gig_proto_buff)
        self._cast_list_ids.extend(gig_proto_buff.cast_list)

    @classmethod
    def build_gig_msg(cls, msg, sim, audition_time=None, **kwargs):
        super().build_gig_msg(msg, sim, **kwargs)
        if audition_time is not None:
            msg.audition_time = audition_time

    def collect_rabbit_hole_rewards(self):
        if self.payout_stat_data:
            self._apply_payout_stat(SituationMedal.BRONZE)
