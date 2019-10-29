from _collections import defaultdictfrom _sims4_collections import frozendictimport itertoolsfrom protocolbuffers import Consts_pb2, Situations_pb2import protocolbuffersfrom buffs.tunable import TunableBuffReferencefrom clock import GameSpeedChangeSource, ClockSpeedModefrom date_and_time import DateAndTime, TimeSpanfrom distributor import shared_messagesfrom event_testing.resolver import SingleSimResolver, DataResolverfrom objects import ALL_HIDDEN_REASONSfrom objects.object_manager import DistributableObjectManagerfrom sims4.callback_utils import CallableListfrom sims4.tuning.tunable import TunableSet, TunableEnumWithFilterfrom sims4.tuning.tunable_base import FilterTagfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer import Bouncerfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_guest_list import SituationGuestListfrom situations.situation_job import SituationJobfrom situations.situation_serialization import SituationSeed, SeedPurpose, GLOBAL_SITUATION_LINKED_SIM_IDfrom situations.situation_types import SituationStage, GreetedStatus, SituationSerializationOptionfrom tag import Tagfrom uid import UniqueIdGeneratorfrom venues.venue_constants import NPCSummoningPurposeimport date_and_timeimport distributor.systemimport id_generatorimport persistence_error_typesimport servicesimport simsimport sims4.logimport sims4.tuning.tunableimport situations.complex.leave_situationimport situations.complex.single_sim_leave_situationimport tagimport telemetry_helperimport venueslogger = sims4.log.Logger('Situations')TELEMETRY_GROUP_SITUATIONS = 'SITU'TELEMETRY_HOOK_CREATE_SITUATION = 'SITU'TELEMETRY_HOOK_GUEST = 'GUES'writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_SITUATIONS)
class _SituationManagerSimData:

    def __init__(self, sim_id):
        self._sim_id = sim_id
        self._created_time = None
        self._blacklist_times = defaultdict(DateAndTime)

    def set_created_time(self, created_time):
        self._created_time = created_time

    @property
    def created_time(self):
        return self._created_time

    def load(self, blacklist_data_proto):
        for blacklist_data in blacklist_data_proto.tag_data:
            try:
                tag = Tag(blacklist_data.tag)
            except KeyError:
                continue
            self._blacklist_times[tag] = DateAndTime(blacklist_data.time)

    def blacklist(self, sim_job, blacklist_all_jobs_time=None):
        if blacklist_all_jobs_time is None:
            if sim_job is None:
                logger.error('Attempting to blacklist a sim {} with a no sim_job and no blacklist_all_jobs_time.', self._sim_id)
                return
            for bi in sim_job.blacklist_info:
                new_blacklisted_till_time = services.time_service().sim_now + date_and_time.create_time_span(hours=bi.blacklist_time)
                if bi.blacklist_tag in self._blacklist_times and self._blacklist_times[bi.blacklist_tag] >= new_blacklisted_till_time:
                    pass
                else:
                    self._blacklist_times[bi.blacklist_tag] = new_blacklisted_till_time
        else:
            self._blacklist_times[SituationJob.BLACKLIST_FROM_ALL_JOBS_TAG] = services.time_service().sim_now + date_and_time.create_time_span(hours=blacklist_all_jobs_time)

    def whitelist(self, sim_job=None):
        if sim_job is not None:
            for bi in sim_job.blacklist_info:
                if bi.blacklist_tag in self._blacklist_times:
                    self._blacklist_times.pop(bi.blacklist_tag)
        elif SituationJob.BLACKLIST_FROM_ALL_JOBS_TAG in self._blacklist_times:
            del self._blacklist_times[SituationJob.BLACKLIST_FROM_ALL_JOBS_TAG]

    def is_blacklisted(self, sim_job=None):
        time_now = services.time_service().sim_now
        if sim_job is None or SituationJob.BLACKLIST_FROM_ALL_JOBS_TAG in self._blacklist_times:
            for blacklist_time in self._blacklist_times.values():
                if time_now < blacklist_time:
                    return True
        if sim_job is not None:
            for bi in sim_job.blacklist_info:
                if bi.blacklist_tag in self._blacklist_times and time_now < self._blacklist_times[bi.blacklist_tag]:
                    return True
        return False

    def get_blacklist_info(self):
        blacklist_info = []
        for (tag, time) in self._blacklist_times.items():
            time_remaining = time - services.time_service().sim_now
            if time_remaining > TimeSpan.ZERO:
                blacklist_info.append((tag, time_remaining))
        return blacklist_info

class DelayedSituationDestruction:

    def __enter__(self):
        situation_manager = services.get_zone_situation_manager()
        situation_manager._delay_situation_destruction_ref_count += 1

    def __exit__(self, exc_type, exc_value, traceback):
        situation_manager = services.get_zone_situation_manager()
        situation_manager._delay_situation_destruction_ref_count -= 1
        if situation_manager._delay_situation_destruction_ref_count == 0:
            for situation in situation_manager._situations_for_delayed_destruction:
                situation._self_destruct()
            situation_manager._situations_for_delayed_destruction.clear()

class SituationManager(DistributableObjectManager):
    DEFAULT_LEAVE_SITUATION = sims4.tuning.tunable.TunableReference(description='\n                                            The situation type for the background leave situation.\n                                            It collects sims who are not in other situations and\n                                            asks them to leave periodically.\n                                            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), class_restrictions=situations.complex.leave_situation.LeaveSituation)
    DEFAULT_LEAVE_NOW_MUST_RUN_SITUATION = sims4.tuning.tunable.TunableReference(description='\n                                            The situation type that drives the sim off the lot pronto.\n                                            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), class_restrictions=situations.complex.single_sim_leave_situation.SingleSimLeaveSituation)
    DEFAULT_VISIT_SITUATION = sims4.tuning.tunable.TunableReference(description='\n                                            The default visit situation used when you ask someone to \n                                            hang out or invite them in.\n                                            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION))
    DEFAULT_TRAVEL_SITUATION = Situation.TunableReference(description=' \n                                            The default situation for when you \n                                            are simply traveling with a group \n                                            of Sims.\n                                            ')
    LEAVE_INTERACTION_TAGS = TunableSet(description='\n                The tags indicating leave lot interactions, but not \n                leave lot must run interactions.\n                These are used to determine if a leave lot interaction is running\n                or cancel one if it is.\n                ', tunable=TunableEnumWithFilter(tunable_type=tag.Tag, default=tag.Tag.INVALID, tuning_filter=FilterTag.EXPERT_MODE, filter_prefixes=tag.INTERACTION_PREFIX))
    SUPER_SPEED_THREE_REQUEST_BUFF = TunableBuffReference(description="\n        The buff to apply to the Sim when we're trying to make them run the\n        leave situation from a super speed three request.\n        ", deferred=True)
    DEFAULT_PLAYER_PLANNED_DRAMA_NODE = sims4.tuning.tunable.TunableReference(description='\n        The drama node that will be scheduled when a player plans an event for the future.\n        ', manager=services.get_instance_manager(sims4.resources.Types.DRAMA_NODE))
    _perf_test_cheat_enabled = False

    def __init__(self, manager_id=0):
        super().__init__(manager_id=manager_id)
        self._get_next_session_id = UniqueIdGenerator(1)
        self._added_to_distributor = set()
        self._callbacks = defaultdict(lambda : defaultdict(CallableList))
        self._departing_situation_seed = None
        self._arriving_situation_seed = None
        self._zone_seeds_for_zone_spinup = []
        self._open_street_seeds_for_zone_spinup = []
        self._debug_sims = set()
        self._leave_situation_id = 0
        self._player_greeted_situation_id = 0
        self._player_waiting_to_be_greeted_situation_id = 0
        self._sim_being_created = None
        self._sim_data = {}
        self._delay_situation_destruction_ref_count = 0
        self._situations_for_delayed_destruction = set()
        self._bouncer = None
        self._pause_handle = None
        self._zone_spin_up_greeted_complete = False

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_SITUATION_MANAGER

    def start(self):
        self._bouncer = Bouncer()

    def stop(self):
        if self._pause_handle is not None:
            pause_handle = self._pause_handle
            self._pause_handle = None
            services.game_clock_service().remove_request(pause_handle, source=GameSpeedChangeSource.SITUATION)

    def destroy_situations_on_teardown(self):
        self.destroy_all_situations(include_system=True)
        self._sim_data.clear()
        self._bouncer.destroy()
        self._bouncer = None

    def reset(self, create_system_situations=True):
        self.destroy_all_situations(include_system=True)
        self._added_to_distributor.clear()
        self._callbacks.clear()
        self._bouncer.reset()
        if create_system_situations:
            self._create_system_situations()

    def update(self):
        if self._bouncer is not None:
            try:
                self._bouncer._update()
            except Exception:
                logger.exception('Exception while updating the Bouncer.')

    def enable_perf_cheat(self, enable=True):
        self._perf_test_cheat_enabled = enable
        self._bouncer.spawning_freeze(enable)
        self._bouncer.cap_cheat(enable)

    def get_all(self):
        return [obj for obj in self._objects.values() if obj._stage == SituationStage.RUNNING]

    def get_new_situation_creation_session(self):
        return self._get_next_session_id()

    @property
    def bouncer(self):
        return self._bouncer

    @property
    def sim_being_created(self):
        return self._sim_being_created

    def add_debug_sim_id(self, sim_id):
        self._debug_sims.add(sim_id)

    def _determine_player_greeted_status_during_zone_spin_up(self):
        if not services.current_zone().venue_service.venue.requires_visitation_rights:
            return GreetedStatus.NOT_APPLICABLE
        active_household = services.active_household()
        if active_household is None:
            return GreetedStatus.NOT_APPLICABLE
        if active_household.considers_current_zone_its_residence():
            return GreetedStatus.NOT_APPLICABLE
        cur_status = GreetedStatus.WAITING_TO_BE_GREETED
        lot_seeds = list(self._zone_seeds_for_zone_spinup)
        if self._arriving_situation_seed is not None:
            lot_seeds.append(self._arriving_situation_seed)
        for seed in lot_seeds:
            status = seed.get_player_greeted_status()
            logger.debug('Player:{} :{}', status, seed.situation_type, owner='sscholl')
            if status == GreetedStatus.GREETED:
                cur_status = status
                break
        return cur_status

    def get_npc_greeted_status_during_zone_fixup(self, sim_info):
        if not services.current_zone().venue_service.venue.requires_visitation_rights:
            return GreetedStatus.NOT_APPLICABLE
        if sim_info.lives_here:
            return GreetedStatus.NOT_APPLICABLE
        cur_status = GreetedStatus.NOT_APPLICABLE
        for seed in self._zone_seeds_for_zone_spinup:
            status = seed.get_npc_greeted_status(sim_info)
            logger.debug('NPC:{} :{} :{}', sim_info, status, seed.situation_type, owner='sscholl')
            if status == GreetedStatus.GREETED:
                cur_status = status
                break
            if status == GreetedStatus.WAITING_TO_BE_GREETED:
                cur_status = status
        return cur_status

    def is_player_greeted(self):
        return self._player_greeted_situation_id != 0

    def is_player_waiting_to_be_greeted(self):
        return self._player_waiting_to_be_greeted_situation_id != 0 and self._player_greeted_situation_id == 0

    def create_situation(self, situation_type, guest_list=None, user_facing=True, duration_override=None, custom_init_writer=None, zone_id=0, scoring_enabled=True, spawn_sims_during_zone_spin_up=False, creation_source=None, travel_request_kwargs=frozendict(), linked_sim_id=GLOBAL_SITUATION_LINKED_SIM_ID, scheduled_time=None, **extra_kwargs):
        zone = services.current_zone()
        if zone.is_zone_shutting_down:
            return
        current_zone_id = services.current_zone_id()
        situation_type = services.narrative_service().get_possible_replacement_situation(situation_type)
        if services.get_zone_modifier_service().is_situation_prohibited(zone_id if zone_id else current_zone_id, situation_type):
            return
        if guest_list is None:
            guest_list = SituationGuestList()
        hire_cost = guest_list.get_hire_cost()
        host_sim_info = guest_list.host_sim_info
        if host_sim_info is not None and not host_sim_info.household.funds.try_remove(situation_type.cost() + hire_cost, Consts_pb2.TELEMETRY_EVENT_COST, host_sim_info):
            return
        situation_id = id_generator.generate_object_id()
        self._send_create_situation_telemetry(situation_type, situation_id, guest_list, hire_cost, zone_id)
        if zone_id and zone_id != current_zone_id and scheduled_time is None:
            return self._create_situation_and_travel(situation_type, situation_id, guest_list, user_facing, duration_override, custom_init_writer, zone_id, scoring_enabled=scoring_enabled, creation_source=creation_source, linked_sim_id=linked_sim_id, travel_request_kwargs=travel_request_kwargs)
        situation_seed = SituationSeed(situation_type, SeedPurpose.NORMAL, situation_id, guest_list, user_facing=user_facing, duration_override=duration_override, zone_id=zone_id, scoring_enabled=scoring_enabled, spawn_sims_during_zone_spin_up=spawn_sims_during_zone_spin_up, creation_source=creation_source, linked_sim_id=linked_sim_id, **extra_kwargs)
        if custom_init_writer is not None:
            situation_seed.setup_for_custom_init_params(custom_init_writer)
        return_id = None
        if scheduled_time is not None:
            schedule_success = services.drama_scheduler_service().schedule_node(self.DEFAULT_PLAYER_PLANNED_DRAMA_NODE, SingleSimResolver(guest_list.host_sim.sim_info), specific_time=scheduled_time, situation_seed=situation_seed)
            return_id = situation_id if schedule_success else None
        else:
            return_id = self.create_situation_from_seed(situation_seed)
        return return_id

    def _create_situation_and_travel(self, situation_type, *args, travel_request_kwargs, **kwargs):
        travel_fn = lambda : self._create_departing_seed_and_travel(situation_type, *args, **kwargs)
        travel_request_situtaion = None
        for situation in self.get_user_facing_situations_gen():
            if travel_request_situtaion is None:
                travel_request_situtaion = situation
            elif situation.travel_request_behavior.restrict > travel_request_situtaion.travel_request_behavior.restrict:
                travel_request_situtaion = situation
        if travel_request_situtaion is not None:
            return travel_request_situtaion.travel_request_behavior(travel_request_situtaion, situation_type, travel_fn, **travel_request_kwargs)
        return travel_fn()

    def create_visit_situation_for_unexpected(self, sim):
        duration_override = None
        if self._perf_test_cheat_enabled:
            duration_override = 0
        self.create_visit_situation(sim, duration_override=duration_override)

    def create_visit_situation(self, sim, duration_override=None, visit_type_override=None):
        situation_id = None
        visit_type = visit_type_override if visit_type_override is not None else self.DEFAULT_VISIT_SITUATION
        if visit_type is not None:
            guest_list = situations.situation_guest_list.SituationGuestList(invite_only=True)
            guest_info = situations.situation_guest_list.SituationGuestInfo.construct_from_purpose(sim.id, visit_type.default_job(), situations.situation_guest_list.SituationInvitationPurpose.INVITED)
            guest_list.add_guest_info(guest_info)
            situation_id = self.create_situation(visit_type, guest_list=guest_list, user_facing=False, duration_override=duration_override)
        if situation_id is None:
            logger.error('Failed to create visit situation for sim: {}', sim)
            self.make_sim_leave(sim)
        return situation_id

    def create_situation_from_seed(self, seed):
        if not seed.allow_creation:
            return
        if seed.user_facing:
            for situation in tuple(self.get_user_facing_situations_gen()):
                if seed.linked_sim_id == GLOBAL_SITUATION_LINKED_SIM_ID and situation.linked_sim_id == GLOBAL_SITUATION_LINKED_SIM_ID:
                    self.destroy_situation_by_id(situation.id)
        if seed.situation_type.is_unique_situation:
            for situation in self.running_situations():
                if type(situation) is seed.situation_type:
                    return
        situation = seed.situation_type(seed)
        try:
            if seed.is_loadable:
                if not situation.load_situation():
                    situation._destroy()
                    return
            else:
                situation.start_situation()
        except Exception:
            logger.exception('Exception thrown while starting situation')
            situation._destroy()
            return
        if situation._stage == SituationStage.DYING:
            return
        self.add(situation)
        if situation.is_user_facing or situation.distribution_override:
            distributor.system.Distributor.instance().add_object(situation)
            self._added_to_distributor.add(situation)
            situation.on_added_to_distributor()
        return situation.id

    def travel_existing_situation(self, situation, zone_id):
        seed = situation.save_situation()
        seed.zone_id = zone_id
        self.travel_seed(seed)
        situation._self_destruct()

    def _create_departing_seed_and_travel(self, situation_type, situation_id, guest_list=None, user_facing=True, duration_override=None, custom_init_writer=None, zone_id=0, scoring_enabled=True, creation_source=None, linked_sim_id=GLOBAL_SITUATION_LINKED_SIM_ID):
        current_zone = services.current_zone()
        if current_zone is not None and not current_zone.is_zone_running:
            logger.error('Unable to travel during spin-up: {}. A travel interaction was save/loaded, which is incorrect. Make it one-shot or non-saveable.', situation_type)
            return
        traveling_sim = guest_list.get_traveler()
        if traveling_sim is None:
            logger.error('No traveling Sim available for creating departing seed for situation: {}.', situation_type)
            return
        if traveling_sim.client is None:
            logger.error('No client on traveling Sim: {} for for situation: {}.', traveling_sim, situation_type)
            return
        if traveling_sim.household is None:
            logger.error('No household on traveling Sim for for situation: {}.', situation_type)
            return
        situation_seed = SituationSeed(situation_type, SeedPurpose.TRAVEL, situation_id, guest_list, user_facing, duration_override, zone_id, scoring_enabled=scoring_enabled, creation_source=creation_source, linked_sim_id=linked_sim_id)
        if situation_seed is None:
            logger.error('Failed to create departing seed for situation: {}.', situation_type)
            return
        if custom_init_writer is not None:
            situation_seed.setup_for_custom_init_params(custom_init_writer)
        return self.travel_seed(situation_seed)

    def travel_seed(self, seed):
        self._departing_situation_seed = seed
        traveling_sim = seed.guest_list.get_traveler()
        travel_info = protocolbuffers.InteractionOps_pb2.TravelSimsToZone()
        travel_info.zone_id = seed.zone_id
        travel_info.sim_ids.append(traveling_sim.id)
        traveling_sim_ids = seed.guest_list.get_other_travelers(traveling_sim)
        travel_info.sim_ids.extend(traveling_sim_ids)
        distributor.system.Distributor.instance().add_event(protocolbuffers.Consts_pb2.MSG_TRAVEL_SIMS_TO_ZONE, travel_info)
        if self._pause_handle is None:
            self._pause_handle = services.game_clock_service().push_speed(ClockSpeedMode.PAUSED, reason='Situation Travel', source=GameSpeedChangeSource.SITUATION)
        logger.debug('Travel seed now time {}', services.time_service().sim_now)
        logger.debug('Travel seed future time {}', services.time_service().sim_future)
        return seed.situation_id

    def _create_system_situations(self):
        self._leave_situation_id = 0
        for situation in self.running_situations():
            if type(situation) is self.DEFAULT_LEAVE_SITUATION:
                self._leave_situation_id = situation.id
                break
        if self._leave_situation_id == 0:
            self._leave_situation_id = self.create_situation(self.DEFAULT_LEAVE_SITUATION, user_facing=False, duration_override=0)

    @property
    def auto_manage_distributor(self):
        return False

    def call_on_remove(self, situation):
        super().call_on_remove(situation)
        self._callbacks.pop(situation.id, None)
        if situation in self._added_to_distributor:
            dist = distributor.system.Distributor.instance()
            dist.remove_object(situation)
            self._added_to_distributor.remove(situation)
            situation.on_removed_from_distributor()

    def is_distributed(self, situation):
        return situation in self._added_to_distributor

    def _request_destruction(self, situation):
        if self._delay_situation_destruction_ref_count == 0:
            return True
        self._situations_for_delayed_destruction.add(situation)
        return False

    def destroy_situation_by_id(self, situation_id):
        if situation_id in self:
            if situation_id == self._leave_situation_id:
                self._leave_situation_id = 0
            if situation_id == self._player_greeted_situation_id:
                self._player_greeted_situation_id = 0
            if situation_id == self._player_waiting_to_be_greeted_situation_id:
                self._player_waiting_to_be_greeted_situation_id = 0
            self.remove_id(situation_id)

    def destroy_all_situations(self, include_system=False):
        all_situations = tuple(self.values())
        for situation in all_situations:
            if include_system == False and situation.id == self._leave_situation_id:
                pass
            else:
                try:
                    self.destroy_situation_by_id(situation.id)
                except Exception:
                    logger.error('Error when destroying situation {}. You are probably screwed.', situation)

    def register_for_callback(self, situation_id, situation_callback_option, callback_fn):
        if situation_id not in self:
            logger.error("Failed to register situation callback. Situation doesn't exist. {}, {}, {}", situation_id, situation_callback_option, callback_fn, owner='rmccord')
            return
        callable_list = self._callbacks[situation_id][situation_callback_option]
        if callback_fn not in callable_list:
            callable_list.append(callback_fn)
        self._callbacks[situation_id][situation_callback_option] = callable_list

    def unregister_callback(self, situation_id, situation_callback_option, callback_fn):
        if situation_id not in self:
            return
        callable_list = self._callbacks[situation_id][situation_callback_option]
        if callback_fn in callable_list:
            callable_list.remove(callback_fn)
        self._callbacks[situation_id][situation_callback_option] = callable_list

    def create_greeted_npc_visiting_npc_situation(self, npc_sim_info):
        services.current_zone().venue_service.venue.summon_npcs((npc_sim_info,), venues.venue_constants.NPCSummoningPurpose.PLAYER_BECOMES_GREETED)

    def _create_greeted_player_visiting_npc_situation(self, sim=None):
        if sim is None:
            guest_list = situations.situation_guest_list.SituationGuestList()
        else:
            guest_list = situations.situation_guest_list.SituationGuestList(host_sim_id=sim.id)
        greeted_situation_type = services.current_zone().venue_service.venue.player_greeted_situation_type
        if greeted_situation_type is None:
            return
        self._player_greeted_situation_id = self.create_situation(greeted_situation_type, user_facing=False, guest_list=guest_list)

    def _create_player_waiting_to_be_greeted_situation(self):
        self._player_waiting_to_be_greeted_situation_id = self.create_situation(services.current_zone().venue_service.venue.player_ungreeted_situation_type, user_facing=False)

    def make_player_waiting_to_be_greeted_during_zone_spin_up(self):
        waiting_situation_type = services.current_zone().venue_service.venue.player_ungreeted_situation_type
        for situation in self.running_situations():
            if type(situation) is waiting_situation_type:
                self._player_waiting_to_be_greeted_situation_id = situation.id
                break
        self._create_player_waiting_to_be_greeted_situation()

    def make_player_greeted_during_zone_spin_up(self):
        greeted_situation_type = services.current_zone().venue_service.venue.player_greeted_situation_type
        for situation in self.running_situations():
            if type(situation) is greeted_situation_type:
                self._player_greeted_situation_id = situation.id
                break
        self._create_greeted_player_visiting_npc_situation()

    def destroy_player_waiting_to_be_greeted_situation(self):
        if self._player_waiting_to_be_greeted_situation_id is 0:
            return
        situation = self.get(self._player_waiting_to_be_greeted_situation_id)
        if situation is None:
            return
        situation._self_destruct()
        self._player_waiting_to_be_greeted_situation_id = 0

    def make_waiting_player_greeted(self, door_bell_ringing_sim=None):
        for situation in self.running_situations():
            situation._on_make_waiting_player_greeted(door_bell_ringing_sim)
        if self._player_greeted_situation_id == 0:
            self._create_greeted_player_visiting_npc_situation(door_bell_ringing_sim)

    def get_situation_by_type(self, situation_type):
        for situation in self.running_situations():
            if type(situation) is situation_type:
                return situation

    def get_situations_by_type(self, *situation_types):
        found_situations = []
        for situation in self.running_situations():
            if isinstance(situation, situation_types):
                found_situations.append(situation)
        return found_situations

    def get_situations_by_tags(self, situation_tags):
        found_situations = []
        for situation in self.running_situations():
            if situation.tags & situation_tags:
                found_situations.append(situation)
        return found_situations

    def is_situation_running(self, situation_type):
        return any(isinstance(situation, situation_type) for situation in self.running_situations())

    def disable_save_to_situation_manager(self, situation_id):
        situation = self.get(situation_id)
        if situation is not None:
            situation.save_to_situation_manager = False

    def save(self, zone_data=None, open_street_data=None, save_slot_data=None, **kwargs):
        if zone_data is None:
            return
        zone = services.current_zone()
        if zone.venue_service.build_buy_edit_mode:
            return self._save_for_edit_mode(zone_data=zone_data, open_street_data=open_street_data, save_slot_data=save_slot_data)
        SituationSeed.serialize_travel_seed_to_slot(save_slot_data, self._departing_situation_seed)
        zone_seeds = []
        street_seeds = []
        holiday_seeds = []
        for situation in self.running_situations():
            if not situation.save_to_situation_manager:
                pass
            else:
                seed = situation.save_situation()
                if seed is not None:
                    if situation.situation_serialization_option == SituationSerializationOption.OPEN_STREETS:
                        street_seeds.append(seed)
                    elif situation.situation_serialization_option == SituationSerializationOption.LOT:
                        zone_seeds.append(seed)
                    else:
                        holiday_seeds.append(seed)
        SituationSeed.serialize_seeds_to_zone(zone_seeds=zone_seeds, zone_data_msg=zone_data, blacklist_data=self._sim_data)
        SituationSeed.serialize_seeds_to_open_street(open_street_seeds=street_seeds, open_street_data_msg=open_street_data)
        active_household = services.active_household()
        if active_household is not None:
            active_household.holiday_tracker.set_holiday_situation_seeds(holiday_seeds)

    def _save_for_edit_mode(self, zone_data=None, open_street_data=None, save_slot_data=None):
        SituationSeed.serialize_travel_seed_to_slot(save_slot_data, self._arriving_situation_seed)
        SituationSeed.serialize_seeds_to_zone(zone_seeds=self._zone_seeds_for_zone_spinup, zone_data_msg=zone_data, blacklist_data=self._sim_data)
        SituationSeed.serialize_seeds_to_open_street(open_street_seeds=self._open_street_seeds_for_zone_spinup, open_street_data_msg=open_street_data)

    def spin_up_for_edit_mode(self):
        self.create_seeds_during_zone_spin_up()

    def load(self, zone_data=None):
        if zone_data is None:
            return
        for blacklist_data in zone_data.gameplay_zone_data.situations_data.blacklist_data:
            sim_id = blacklist_data.sim_id
            sim_data = self._sim_data.setdefault(sim_id, _SituationManagerSimData(sim_id))
            sim_data.load(blacklist_data)

    def create_seeds_during_zone_spin_up(self):
        zone = services.current_zone()
        save_slot_proto = services.get_persistence_service().get_save_slot_proto_buff()
        self._arriving_situation_seed = SituationSeed.deserialize_travel_seed_from_slot(save_slot_proto)
        zone_proto = services.get_persistence_service().get_zone_proto_buff(zone.id)
        if zone_proto is not None:
            self._zone_seeds_for_zone_spinup = SituationSeed.deserialize_seeds_from_zone(zone_proto)
        open_street_proto = services.get_persistence_service().get_open_street_proto_buff(zone.open_street_id)
        if open_street_proto is not None:
            self._open_street_seeds_for_zone_spinup = SituationSeed.deserialize_seeds_from_open_street(open_street_proto)

    def get_arriving_seed_during_zone_spin(self):
        return self._arriving_situation_seed

    def get_zone_persisted_seeds_during_zone_spin_up(self):
        return list(self._zone_seeds_for_zone_spinup)

    def get_open_street_persisted_seeds_during_zone_spin_up(self):
        return list(self._open_street_seeds_for_zone_spinup)

    def create_situations_during_zone_spin_up(self):
        for seed in self._zone_seeds_for_zone_spinup:
            self.create_situation_from_seed(seed)
        for seed in self._open_street_seeds_for_zone_spinup:
            self.create_situation_from_seed(seed)
        self._create_system_situations()
        if self._arriving_situation_seed is not None:
            arrived_id = self.create_situation_from_seed(self._arriving_situation_seed)
            situation = self.get(arrived_id)
            if situation is not None:
                situation.on_arrived()

    def on_all_situations_created_during_zone_spin_up(self):
        self._bouncer.request_all_sims_during_zone_spin_up()

    def on_all_sims_spawned_during_zone_spin_up(self):
        self._bouncer.assign_all_sims_during_zone_spin_up()
        for situation in self.running_situations():
            if situation.should_time_jump():
                situation.on_time_jump()

    def on_hit_their_marks_during_zone_spin_up(self):
        self._bouncer.start_full_operations()

    def make_situation_seed_zone_director_requests(self):
        venue_service = services.current_zone().venue_service
        for seed in itertools.chain((self._arriving_situation_seed,), self._zone_seeds_for_zone_spinup, self._open_street_seeds_for_zone_spinup):
            if seed is None:
                pass
            else:
                (zone_director, request_type) = seed.situation_type.get_zone_director_request()
                if not zone_director is None:
                    if request_type is None:
                        pass
                    elif seed.is_loadable and not seed.situation_type.should_seed_be_loaded(seed):
                        pass
                    else:
                        preserve_state = seed.is_loadable
                        venue_service.request_zone_director(zone_director, request_type, preserve_state=preserve_state)

    def get_sim_serialization_option(self, sim):
        result = sims.sim_info_types.SimSerializationOption.UNDECLARED
        for situation in self.get_situations_sim_is_in(sim):
            option = situation.situation_serialization_option
            if option == situations.situation_types.SituationSerializationOption.LOT:
                result = sims.sim_info_types.SimSerializationOption.LOT
                break
            elif option == situations.situation_types.SituationSerializationOption.OPEN_STREETS:
                result = sims.sim_info_types.SimSerializationOption.OPEN_STREETS
        return result

    def remove_sim_from_situation(self, sim, situation_id):
        situation = self.get(situation_id)
        if situation is None:
            return
        self._bouncer.remove_sim_from_situation(sim, situation)

    def on_sim_reset(self, sim):
        for situation in self.running_situations():
            if situation.is_sim_in_situation(sim):
                situation.on_sim_reset(sim)

    def on_begin_sim_creation_notification(self, sim):
        sim_data = self._sim_data.setdefault(sim.id, _SituationManagerSimData(sim.id))
        sim_data.set_created_time(services.time_service().sim_now)
        self._prune_sim_data()
        self._sim_being_created = sim

    def on_end_sim_creation_notification(self, sim):
        if sim.id in self._debug_sims:
            self._debug_sims.discard(sim.id)
            if self._perf_test_cheat_enabled:
                self.create_visit_situation_for_unexpected(sim)
            else:
                services.current_zone().venue_service.venue.summon_npcs((sim.sim_info,), NPCSummoningPurpose.DEFAULT)
        self._bouncer._on_end_sim_creation_notification(sim)
        self._sim_being_created = None

    def get_situations_sim_is_in(self, sim):
        return [situation for situation in self.values() if situation.is_sim_in_situation(sim) and situation._stage == SituationStage.RUNNING]

    def get_situations_sim_is_in_by_tag(self, sim, tag):
        return [situation for situation in self.get_situations_sim_is_in(sim) if tag in situation.tags]

    def is_user_facing_situation_running(self, global_user_facing_only=False):
        for situation in self.values():
            if not global_user_facing_only:
                return True
            if situation.is_user_facing and situation.linked_sim_id == GLOBAL_SITUATION_LINKED_SIM_ID:
                return True
        return False

    def get_user_facing_situations_gen(self):
        for situation in self.values():
            if situation.is_user_facing:
                yield situation

    def running_situations(self):
        return [obj for obj in self._objects.values() if obj._stage == SituationStage.RUNNING]

    def is_situation_with_tags_running(self, tags):
        for situation in self.values():
            if situation._stage == SituationStage.RUNNING and situation.tags & tags:
                return True
        return False

    def user_ask_sim_to_leave_now_must_run(self, sim):
        if sim.sim_info.is_npc and sim.sim_info.lives_here:
            return
        ask_to_leave = True
        for situation in self.get_situations_sim_is_in(sim):
            if not situation.on_ask_sim_to_leave(sim):
                ask_to_leave = False
                break
        if ask_to_leave:
            self.make_sim_leave_now_must_run(sim)

    def make_sim_leave_now_must_run(self, sim):
        if services.current_zone().is_zone_shutting_down:
            return
        for situation in self.get_situations_sim_is_in(sim):
            if type(situation) is self.DEFAULT_LEAVE_NOW_MUST_RUN_SITUATION:
                return
        leave_now_type = self.DEFAULT_LEAVE_NOW_MUST_RUN_SITUATION
        guest_list = situations.situation_guest_list.SituationGuestList(invite_only=True)
        guest_info = situations.situation_guest_list.SituationGuestInfo(sim.id, leave_now_type.default_job(), RequestSpawningOption.CANNOT_SPAWN, BouncerRequestPriority.EVENT_VIP, expectation_preference=True)
        guest_list.add_guest_info(guest_info)
        self.create_situation(leave_now_type, guest_list=guest_list, user_facing=False)

    def ss3_make_all_npcs_leave_now(self):
        sim_info_manager = services.sim_info_manager()
        current_zone_id = services.current_zone_id()
        for sim in sim_info_manager.instanced_sims_gen():
            if sim.is_npc:
                if sim.is_on_active_lot():
                    pass
                elif sim.sim_info.vacation_or_home_zone_id == current_zone_id:
                    pass
                else:
                    sim.add_buff(buff_type=self.SUPER_SPEED_THREE_REQUEST_BUFF.buff_type, buff_reason=self.SUPER_SPEED_THREE_REQUEST_BUFF.buff_reason)
                    self.make_sim_leave_now_must_run(sim)

    def make_sim_leave(self, sim):
        leave_situation = self.get(self._leave_situation_id)
        if leave_situation is None:
            logger.error('The leave situation is missing. Making the sim leave now must run.')
            self.make_sim_leave_now_must_run(sim)
            return
        leave_situation.invite_sim_to_leave(sim)

    def expedite_leaving(self):
        leave_situation = self.get(self._leave_situation_id)
        if leave_situation is None:
            return
        for sim in leave_situation.all_sims_in_situation_gen():
            self.make_sim_leave_now_must_run(sim)

    def get_time_span_sim_has_been_on_lot(self, sim):
        sim_data = self._sim_data.get(sim.id)
        if sim_data is None:
            return
        if sim_data.created_time is None:
            return
        return services.time_service().sim_now - sim_data.created_time

    def get_blacklist_info(self, sim_id):
        sim_data = self._sim_data.get(sim_id)
        if sim_data is None:
            return
        return sim_data.get_blacklist_info()

    def get_auto_fill_blacklist(self, sim_job=None):
        blacklist = set()
        for (sim_id, sim_data) in tuple(self._sim_data.items()):
            if sim_data.is_blacklisted(sim_job=sim_job):
                blacklist.add(sim_id)
        return blacklist

    def add_sim_to_auto_fill_blacklist(self, sim_id, sim_job=None, blacklist_all_jobs_time=None):
        sim_data = self._sim_data.setdefault(sim_id, _SituationManagerSimData(sim_id))
        sim_data.blacklist(sim_job, blacklist_all_jobs_time=blacklist_all_jobs_time)
        self._prune_sim_data()

    def remove_sim_from_auto_fill_blacklist(self, sim_id, sim_job=None):
        sim_data = self._sim_data.get(sim_id)
        if sim_data is not None:
            sim_data.whitelist(sim_job=sim_job)
        self._prune_sim_data()

    def send_situation_start_ui(self, actor, target=None, situations_available=None, creation_time=None):
        msg = Situations_pb2.SituationPrepare()
        msg.situation_session_id = self.get_new_situation_creation_session()
        msg.creation_time = creation_time if creation_time is not None else 0
        msg.sim_id = actor.id
        if target is not None:
            msg.is_targeted = True
            msg.target_id = target.id
        if situations_available is not None:
            for situation in situations_available:
                msg.situation_resource_id.append(situation.guid64)
        shared_messages.add_message_if_selectable(actor, Consts_pb2.MSG_SITUATION_PREPARE, msg, True)

    def _prune_sim_data(self):
        to_remove_ids = []
        for (sim_id, sim_data) in self._sim_data.items():
            sim_info = services.sim_info_manager().get(sim_id)
            if not sim_info is None:
                pass
            if sim_data.is_blacklisted == False:
                to_remove_ids.append(sim_id)
        for sim_id in to_remove_ids:
            del self._sim_data[sim_id]

    def _issue_callback(self, situation_id, callback_option, data):
        self._callbacks[situation_id][callback_option](situation_id, callback_option, data)

    def _send_create_situation_telemetry(self, situation_type, situation_id, guest_list, hire_cost, zone_id):
        if hasattr(situation_type, 'guid64'):
            with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_CREATE_SITUATION) as hook:
                hook.write_int('situ', situation_id)
                hook.write_int('host', guest_list.host_sim_id)
                hook.write_guid('type', situation_type.guid64)
                hook.write_bool('invi', guest_list.invite_only)
                hook.write_bool('hire', hire_cost)
                hook.write_bool('nzon', zone_id != 0 and services.current_zone().id != zone_id)
            sim_info_manager = services.sim_info_manager()
            if sim_info_manager is not None:
                for guest_infos in guest_list._job_type_to_guest_infos.values():
                    for guest_info in guest_infos:
                        if guest_info.sim_id == 0:
                            pass
                        else:
                            guest_sim = sim_info_manager.get(guest_info.sim_id)
                            if guest_sim is None:
                                pass
                            else:
                                client = services.client_manager().get_client_by_household_id(guest_sim.household_id)
                                with telemetry_helper.begin_hook(writer, TELEMETRY_HOOK_GUEST) as hook:
                                    hook.write_int('situ', situation_id)
                                    hook.write_guid('type', situation_type.guid64)
                                    if client is None:
                                        hook.write_int('npcg', guest_info.sim_id)
                                    else:
                                        hook.write_int('pcgu', guest_info.sim_id)
                                        hook.write_guid('jobb', guest_info.job_type.guid64)
