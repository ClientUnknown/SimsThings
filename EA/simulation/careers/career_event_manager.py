from collections import namedtuplefrom protocolbuffers import SimObjectAttributes_pb2from date_and_time import create_time_spanfrom event_testing.resolver import SingleSimResolverfrom interactions.utils.death import get_death_interactionfrom objects import ALL_HIDDEN_REASONSfrom sims.outfits.outfit_enums import OutfitChangeReasonfrom sims.sim_spawner import SimSpawnerfrom situations.situation_guest_list import SituationGuestInfo, SituationInvitationPurpose, SituationGuestListfrom situations.situation_serialization import SituationSeedfrom situations.situation_types import SituationCallbackOption, SituationMedalfrom world.travel_service import travel_sim_to_zone, travel_sims_to_zoneimport alarmsimport servicesimport sims4.resourceslogger = sims4.log.Logger('Careers', default_owner='tingyul')CareerEventPayoutInfo = namedtuple('CareerEventPayoutInfo', ['performance_multiplier', 'money_multiplier', 'text_factory', 'medal', 'num_goals_completed'])
class CareerEventManager:

    def __init__(self, career):
        self._career = career
        self._career_events = list()
        self._scorable_situation_id = None
        self._scorable_situation_seed = None
        self._warning_handle = None

    @property
    def scorable_situation_id(self):
        return self._scorable_situation_id

    def request_career_event(self, career_event_type):
        career_event = career_event_type(self._career)
        self._career_events.append(career_event)
        career_event.on_career_event_requested()
        return career_event

    def unrequest_career_event(self):
        if self._career_events:
            career_event = self._career_events.pop()
            career_event.on_career_event_stop()
        else:
            logger.error("Unrequesting career event when there isn't one.")

    def is_valid_zone_id(self, zone_id):
        career_event = self._get_top_career_event()
        if career_event is None:
            return False
        required_zone_id = career_event.get_required_zone_id()
        if required_zone_id is None:
            return True
        return required_zone_id == zone_id

    def _get_top_career_event(self):
        if self._career_events:
            return self._career_events[-1]

    def start_immediately(self, career_event):
        if self._scorable_situation_id is None:
            self._start_scorable_situation_from_tuning()
        career_event.request_zone_director()
        career_event.on_career_event_start()

    def _warning_callback(self, alarm_handle):
        self._cancel_warning_alarm()
        self._career.send_career_message(self._career.career_messages.career_event_end_warning.notification)

    def _create_warning_alarm(self):
        if self._warning_handle is not None:
            return
        if self._career.career_messages.career_event_end_warning is None:
            return
        warn_time = create_time_span(minutes=self._career.career_messages.career_event_end_warning.time)
        end_time = self._career.time_until_end_of_work()
        if end_time >= warn_time:
            self._warning_handle = alarms.add_alarm(self, end_time - warn_time, self._warning_callback, cross_zone=True)

    def _cancel_warning_alarm(self):
        if self._warning_handle is not None:
            self._warning_handle.cancel()
            self._warning_handle = None

    def start(self):
        self._create_warning_alarm()

    def stop(self):
        for career_event in self._career_events:
            career_event.on_career_event_stop()
        self._career_events.clear()
        self._destroy_scorable_situation()
        self._cancel_warning_alarm()

    def start_top_career_event(self, start_situation_fn=None):
        career_event = self._get_top_career_event()
        target_zone_id = career_event.get_required_zone_id()
        sim_info = self._career.sim_info
        if start_situation_fn is not None:

            def _start_travel():
                event_situation_id = start_situation_fn(target_zone_id)
                career_event.set_event_situation_id(event_situation_id)

        else:

            def _start_travel():
                return travel_sim_to_zone(sim_info.id, target_zone_id)

        def _start_event():
            self.start_immediately(career_event)
            if start_situation_fn is not None:
                event_situation_id = start_situation_fn(target_zone_id)
                career_event.set_event_situation_id(event_situation_id)

        if target_zone_id is None:
            target_zone_id = 0
            _start_event()
        elif sim_info.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
            if sim_info.zone_id == target_zone_id:
                _start_event()
            else:
                _start_travel()
        elif services.current_zone_id() == target_zone_id:
            SimSpawner.spawn_sim(sim_info, spawn_action=lambda sim: _start_event())
        else:
            if sim_info.zone_id != target_zone_id:
                sim_info.inject_into_inactive_zone(target_zone_id)
            _start_travel()

    @classmethod
    def post_career_event_travel(cls, sim_info, zone_id_override=None, outfit_change_reason=None):
        target_zone_id = sim_info.household.home_zone_id
        sims_to_move = set()
        if sim_info.zone_id != target_zone_id:
            sims_to_move.add(sim_info)
        if outfit_change_reason is not None:
            outfit_change = sim_info.get_outfit_for_clothing_change(None, outfit_change_reason, SingleSimResolver(sim_info))
            sim_info.set_current_outfit(outfit_change)
        if zone_id_override is not None:
            main_zone_id = zone_id_override
        else:
            main_zone_id = services.get_career_service().get_main_career_event_zone_id_and_unlock_save()
        services.get_career_service().last_career_event_zone_id = None
        if main_zone_id != target_zone_id:
            for household_sim_info in sim_info.household:
                if household_sim_info is not sim_info and household_sim_info.zone_id == main_zone_id:
                    sims_to_move.add(household_sim_info)
        if main_zone_id is not None and target_zone_id == services.current_zone_id():
            for sim_to_move in sims_to_move:
                SimSpawner.spawn_sim(sim_to_move)
            return
        sims_ids_to_travel = set()
        for sim_to_move in sims_to_move:
            if sim_to_move.is_instanced(allow_hidden_flags=ALL_HIDDEN_REASONS):
                sims_ids_to_travel.add(sim_to_move.sim_id)
            else:
                sim_to_move.inject_into_inactive_zone(target_zone_id)
        if sims_ids_to_travel:
            persistence_service = services.get_persistence_service()
            if persistence_service.is_save_locked():
                household = sim_info.household

                def post_save_lock_travel():
                    household_sims = {sim.sim_id: sim for sim in household.instanced_sims_gen()}
                    sim_ids = set(sim_id for sim_id in sims_ids_to_travel if sim_id in household_sims and get_death_interaction(household_sims[sim_id]) is None)
                    if sim_ids:
                        travel_sims_to_zone(sim_ids, target_zone_id)

                persistence_service.add_save_unlock_callback(post_save_lock_travel)
            else:
                travel_sims_to_zone(sims_ids_to_travel, target_zone_id)

    def get_main_zone_id(self):
        if self._career_events:
            return self._career_events[0].get_required_zone_id()

    def _start_scorable_situation_from_tuning(self):
        if self._scorable_situation_id is not None:
            return
        logger.assert_raise(self._career_events, 'Spinning up career event manger with no career events. Manager: {}', self)
        career_event = self._career_events[0]
        if career_event.scorable_situation is None:
            return
        situation = career_event.scorable_situation.situation
        if situation is None:
            return
        guest_info = SituationGuestInfo.construct_from_purpose(self._career.sim_info.sim_id, situation.default_job(), SituationInvitationPurpose.CAREER)
        guest_list = SituationGuestList(invite_only=True, filter_requesting_sim_id=self._career.sim_info.sim_id)
        guest_list.add_guest_info(guest_info)
        situation_manager = services.get_zone_situation_manager()
        duration = self._career.time_until_end_of_work().in_minutes()
        self._scorable_situation_id = situation_manager.create_situation(situation, guest_list=guest_list, duration_override=duration)
        self._scorable_situation_setup()

    def _scorable_situation_setup(self):
        situation_manager = services.get_zone_situation_manager()
        situation_manager.disable_save_to_situation_manager(self._scorable_situation_id)
        situation_manager.register_for_callback(self._scorable_situation_id, SituationCallbackOption.END_OF_SITUATION_SCORING, self._scorable_situation_end_callback)

    def _scorable_situation_end_callback(self, situation_id, callback_option, scoring_callback_data):
        self._career.leave_work_early()

    def _destroy_scorable_situation(self):
        if self._scorable_situation_id is not None:
            situation_manager = services.get_zone_situation_manager()
            situation_manager.unregister_callback(self._scorable_situation_id, SituationCallbackOption.END_OF_SITUATION_SCORING, self._scorable_situation_end_callback)
            situation_manager.destroy_situation_by_id(self._scorable_situation_id)

    def get_career_event_payout_info(self):
        if self._scorable_situation_seed is not None:
            situation = self._scorable_situation_seed.situation_type(self._scorable_situation_seed)
        else:
            situation_manager = services.get_zone_situation_manager()
            situation = situation_manager.get(self._scorable_situation_id)
            if situation is None:
                return
        medal = situation.get_level()
        completed_goals = situation.get_situation_completed_goal_info()
        num_completed_goals = len(completed_goals) if completed_goals is not None else 0
        payout = self._get_career_event_payout_info_from_medal(medal, num_completed_goals)
        return payout

    def _get_career_event_payout_info_from_medal(self, medal, num_goals_completed):
        scorable_situation = self._career_events[0].scorable_situation
        if medal == SituationMedal.BRONZE:
            payout = scorable_situation.medal_payout_bronze
        elif medal == SituationMedal.SILVER:
            payout = scorable_situation.medal_payout_silver
        elif medal == SituationMedal.GOLD:
            payout = scorable_situation.medal_payout_gold
        else:
            payout = scorable_situation.medal_payout_tin
        resolver = SingleSimResolver(self._career.sim_info)
        performance = payout.work_performance.get_multiplier(resolver)
        money = payout.money.get_multiplier(resolver)
        for loot in payout.additional_loots:
            loot.apply_to_resolver(resolver)
        return CareerEventPayoutInfo(performance, money, payout.text, medal, num_goals_completed)

    def create_career_event_situations_during_zone_spin_up(self):
        for career_event in self._career_events:
            career_event.start_from_zone_spin_up()
        if self._scorable_situation_seed is not None:
            situation_manager = services.get_zone_situation_manager()
            self._scorable_situation_seed.duration_override = self._career.time_until_end_of_work().in_minutes()
            self._scorable_situation_id = situation_manager.create_situation_from_seed(self._scorable_situation_seed)
            self._scorable_situation_setup()
            self._scorable_situation_seed = None
        else:
            self._start_scorable_situation_from_tuning()

    def on_career_session_extended(self, reset_warning_alarm=True):
        if self._scorable_situation_id is not None:
            situation_manager = services.get_zone_situation_manager()
            situation = situation_manager.get(self._scorable_situation_id)
            if situation is not None:
                duration = self._career.time_until_end_of_work().in_minutes()
                situation.on_career_session_extended(duration)
        if reset_warning_alarm:
            self._cancel_warning_alarm()
            self._create_warning_alarm()

    def _get_serializable_scorable_situation_seed(self):
        if self._scorable_situation_id is not None:
            situation_manager = services.get_zone_situation_manager()
            if situation_manager is not None:
                situation = situation_manager.get(self._scorable_situation_id)
                if situation is not None:
                    seed = situation.save_situation()
                    return seed

    def save_scorable_situation_for_travel(self):
        if self._scorable_situation_id is not None:
            serializable_seed = self._get_serializable_scorable_situation_seed()
            if serializable_seed is not None:
                self._scorable_situation_seed = serializable_seed.get_deserializable_seed_from_serializable_seed()
            self._scorable_situation_id = None

    def get_career_event_manager_data_proto(self):
        proto = SimObjectAttributes_pb2.CareerEventManagerData()
        for career_event in self._career_events:
            proto.career_events.append(career_event.get_career_event_data_proto())
        if self._scorable_situation_seed is not None:
            self._scorable_situation_seed.serialize_to_proto(proto.scorable_situation_seed)
        elif self._scorable_situation_id is not None:
            seed = self._get_serializable_scorable_situation_seed()
            if seed is not None:
                seed.serialize_to_proto(proto.scorable_situation_seed)
        return proto

    def load_career_event_manager_data_proto(self, proto):
        for career_event_data in proto.career_events:
            career_event_type = services.get_instance_manager(sims4.resources.Types.CAREER_EVENT).get(career_event_data.career_event_id)
            if career_event_type is None:
                pass
            else:
                career_event = career_event_type(self._career)
                career_event.load_from_career_event_data_proto(career_event_data)
                self._career_events.append(career_event)
        self._scorable_situation_seed = SituationSeed.deserialize_from_proto(proto.scorable_situation_seed)

    def request_career_event_zone_director(self):
        career_event = self._get_top_career_event()
        if career_event is not None and services.current_zone_id() == career_event.get_required_zone_id():
            career_event.request_zone_director()
