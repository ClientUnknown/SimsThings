from collections import namedtuplefrom protocolbuffers import SituationPersistence_pb2from date_and_time import DateAndTimefrom default_property_stream_reader import DefaultPropertyStreamReaderfrom distributor.rollback import ProtocolBufferRollbackfrom sims.sim_spawner import SimSpawnerfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposefrom situations.situation_types import SituationCommonBlacklistCategoryimport date_and_timeimport enumimport servicesimport sims4.loglogger = sims4.log.Logger('Situations')
class SeedPurpose(enum.Int, export=False):
    NORMAL = 0
    TRAVEL = 1
    PERSISTENCE = 2

class GoalTrackerType(enum.Int, export=False):
    STANDARD_GOAL_TRACKER = 0
    DYNAMIC_GOAL_TRACKER = 1

class _SituationSimpleSeedling:

    def __init__(self, phase_index, remaining_phase_time):
        self.phase_index = phase_index
        self.remaining_phase_time = remaining_phase_time

class _SituationComplexSeedling:

    def __init__(self):
        self._situation_custom_reader = None
        self._situation_custom_writer = None
        self._situation_custom_writer_data = None
        self._state_custom_writer = None
        self._state_custom_reader = None
        self._state_custom_writer_data = None

    def setup_for_load(self, situation_data, state_data):
        if situation_data is not None:
            self._situation_custom_writer_data = situation_data
            self._situation_custom_reader = DefaultPropertyStreamReader(situation_data)
        if state_data is not None:
            self._state_custom_writer_data = state_data
            self._state_custom_reader = DefaultPropertyStreamReader(state_data)

    def setup_for_save(self):
        self._situation_custom_writer = sims4.PropertyStreamWriter()
        self._state_custom_writer = sims4.PropertyStreamWriter()

    def setup_for_custom_init_params(self, writer):
        if writer is not None:
            self._situation_custom_writer_data = writer.close()
            self._situation_custom_reader = DefaultPropertyStreamReader(self._situation_custom_writer_data)

    def finalize_creation_for_save(self):
        if self._situation_custom_writer is not None:
            data = self._situation_custom_writer.close()
            if self._situation_custom_writer.count > 0:
                self._situation_custom_writer_data = data
            self._situation_custom_writer = None
        if self._state_custom_writer is not None:
            data = self._state_custom_writer.close()
            if self._state_custom_writer.count > 0:
                self._state_custom_writer_data = data
            self._state_custom_writer = None

    @property
    def situation_custom_reader(self):
        return self._situation_custom_reader

    @property
    def state_custom_reader(self):
        return self._state_custom_reader

    @property
    def situation_custom_writer(self):
        return self._situation_custom_writer

    @property
    def state_custom_writer(self):
        return self._state_custom_writer

    @property
    def situation_custom_data(self):
        return self._situation_custom_writer_data

    @property
    def state_custom_data(self):
        return self._state_custom_writer_data

class GoalSeedling:

    def __init__(self, goal_type, actor_id=0, target_id=0, secondary_target_id=0, count=0, locked=False, completed_time=None):
        self._goal_type = goal_type
        self._actor_id = actor_id
        self._target_id = target_id
        self._secondary_target_id = secondary_target_id
        self._count = count
        self._completed = False
        self._chain_id = 0
        self._reader = None
        self._writer = None
        self._custom_data = None
        self._locked = locked
        self._completed_time = completed_time

    def set_completed(self):
        self._completed = True

    @property
    def completed(self):
        return self._completed

    @property
    def goal_type(self):
        return self._goal_type

    @property
    def actor_id(self):
        return self._actor_id

    @property
    def target_id(self):
        return self._target_id

    @property
    def secondary_target_id(self):
        return self._secondary_target_id

    @property
    def count(self):
        return self._count

    @property
    def chain_id(self):
        return self._chain_id

    @chain_id.setter
    def chain_id(self, chain_id):
        self._chain_id = chain_id

    @property
    def locked(self):
        return self._locked

    @property
    def completed_time(self):
        return self._completed_time

    @property
    def writer(self):
        if self._writer is None:
            self._writer = sims4.PropertyStreamWriter()
        return self._writer

    @property
    def reader(self):
        if self._custom_data is not None:
            self._reader = DefaultPropertyStreamReader(self._custom_data)
        return self._reader

    def finalize_creation_for_save(self):
        if self._writer:
            self._custom_data = self._writer.close()

    def serialize_to_proto(self, goal_proto):
        goal_proto.goal_type_id = self._goal_type.guid64
        goal_proto.actor_id = self._actor_id
        goal_proto.target_id = self._target_id
        goal_proto.secondary_target_id = self._secondary_target_id
        goal_proto.count = self._count
        if self._completed == True:
            goal_proto.completed = self._completed
        goal_proto.chain_id = self._chain_id
        if self._custom_data:
            goal_proto.custom_data = self._custom_data
        goal_proto.locked = self._locked
        if self._completed_time is not None:
            goal_proto.completed_time = self._completed_time.absolute_ticks()

    @classmethod
    def deserialize_from_proto(cls, goal_proto):
        goal_type = services.situation_goal_manager().get(goal_proto.goal_type_id)
        if goal_type is None:
            logger.warn('Attempted to deserialized goal type which does not exist. type_id:{}', goal_proto.goal_type_id, owner='sscholl')
            return
        goal = GoalSeedling(goal_type, goal_proto.actor_id, goal_proto.target_id, goal_proto.secondary_target_id, goal_proto.count, goal_proto.locked)
        if goal_proto.HasField('completed'):
            goal._completed = goal_proto.completed
        if goal_proto.HasField('chain_id'):
            goal._chain_id = goal_proto.chain_id
        if goal_proto.HasField('custom_data'):
            goal._custom_data = goal_proto.custom_data
        if goal_proto.HasField('completed_time'):
            goal._completed_time = DateAndTime(goal_proto.completed_time)
        return goal

class GoalChainSeedling:

    def __init__(self, starting_goal_set_type, chosen_goal_set_type, chain_id, display_position):
        self.starting_goal_set_type = starting_goal_set_type
        self.chosen_goal_set_type = chosen_goal_set_type
        self.chain_id = chain_id
        self.display_position = display_position

    def serialize_to_proto(self, chain_proto):
        chain_proto.starting_goal_set_type_id = self.starting_goal_set_type.guid64
        if self.chosen_goal_set_type is not None:
            chain_proto.chosen_goal_set_type_id = self.chosen_goal_set_type.guid64
        chain_proto.chain_id = self.chain_id
        chain_proto.display_position = self.display_position

    @classmethod
    def deserialize_from_proto(cls, chain_proto):
        starting_type = services.situation_goal_set_manager().get(chain_proto.starting_goal_set_type_id)
        if starting_type is None:
            raise KeyError
        chosen_type = None
        if chain_proto.HasField('chosen_goal_set_type_id'):
            chosen_type = services.situation_goal_set_manager().get(chain_proto.chosen_goal_set_type_id)
        chain = GoalChainSeedling(starting_type, chosen_type, chain_proto.chain_id, chain_proto.display_position)
        return chain

class GoalTrackerSeedling:

    def __init__(self, goal_tracker_type, has_offered_goals=True, inherited_target_id=0):
        self._has_offered_goals = has_offered_goals
        self._inherited_target_id = inherited_target_id
        self._main_goal = None
        self._minor_goals = []
        self._chains = []
        self._completed_goals = []
        self._goal_tracker_type = goal_tracker_type

    def add_minor_goal(self, goal):
        self._minor_goals.append(goal)

    def set_main_goal(self, goal):
        self._main_goal = goal

    def add_chain(self, chain):
        self._chains.append(chain)

    def add_completed_goal(self, goal):
        self._completed_goals.append(goal)

    @property
    def main_goal(self):
        return self._main_goal

    @property
    def minor_goals(self):
        return self._minor_goals

    @property
    def chains(self):
        return self._chains

    @property
    def has_offered_goals(self):
        return self._has_offered_goals

    @property
    def inherited_target_id(self):
        return self._inherited_target_id

    @property
    def completed_goals(self):
        return self._completed_goals

    @property
    def goal_tracker_type(self):
        return self._goal_tracker_type

    def finalize_creation_for_save(self):
        if self._main_goal is not None:
            self._main_goal.finalize_creation_for_save()
        for goal in self._minor_goals:
            goal.finalize_creation_for_save()

    def serialize_to_proto(self, goal_tracker_proto):
        goal_tracker_proto.has_offered_goals = self._has_offered_goals
        goal_tracker_proto.inherited_target_id = self._inherited_target_id
        goal_tracker_proto.goal_tracker_type = self._goal_tracker_type
        for chain in self._chains:
            with ProtocolBufferRollback(goal_tracker_proto.chains) as chain_proto:
                chain.serialize_to_proto(chain_proto)
        if self._main_goal:
            self._main_goal.serialize_to_proto(goal_tracker_proto.main_goal)
        for goal in self._minor_goals:
            with ProtocolBufferRollback(goal_tracker_proto.minor_goals) as goal_proto:
                goal.serialize_to_proto(goal_proto)
        for (goal, chosen_goal_set_type) in self._completed_goals:
            with ProtocolBufferRollback(goal_tracker_proto.completed_goals) as completed_goal_proto:
                goal.serialize_to_proto(completed_goal_proto.situation_goal)
                if chosen_goal_set_type is not None:
                    completed_goal_proto.chosen_goal_set_type_id = chosen_goal_set_type.guid64

    @classmethod
    def deserialize_from_proto(cls, goal_tracker_proto):
        goal_tracker_type = GoalTrackerType.STANDARD_GOAL_TRACKER
        if goal_tracker_proto.HasField('goal_tracker_type'):
            goal_tracker_type = goal_tracker_proto.goal_tracker_type
        tracker = GoalTrackerSeedling(goal_tracker_type, goal_tracker_proto.has_offered_goals, goal_tracker_proto.inherited_target_id)
        for chain_proto in goal_tracker_proto.chains:
            tracker.add_chain(GoalChainSeedling.deserialize_from_proto(chain_proto))
        if goal_tracker_proto.HasField('main_goal'):
            tracker._main_goal = GoalSeedling.deserialize_from_proto(goal_tracker_proto.main_goal)
        for minor_goal_proto in goal_tracker_proto.minor_goals:
            goal_seed = GoalSeedling.deserialize_from_proto(minor_goal_proto)
            if goal_seed is not None:
                tracker.add_minor_goal(goal_seed)
        for completed_goal_proto in goal_tracker_proto.completed_goals:
            if completed_goal_proto.HasField('chosen_goal_set_type_id'):
                chosen_type = services.situation_goal_set_manager().get(chain_proto.chosen_goal_set_type_id)
            else:
                chosen_type = None
            goal_seed = GoalSeedling.deserialize_from_proto(completed_goal_proto.situation_goal)
            if goal_seed is not None:
                tracker.add_completed_goal((goal_seed, chosen_type))
        return tracker

class JobData:

    def __init__(self, role_state_type, emotional_loot_actions_type=None):
        self.role_state_type = role_state_type
        self.emotional_loot_actions_type = emotional_loot_actions_type

    def __str__(self):
        return 'role {}, emotion {}'.format(self.role_state_type, self.emotional_loot_actions_type)
GLOBAL_SITUATION_LINKED_SIM_ID = 0
class SituationSeed:

    def __init__(self, situation_type, seed_purpose, situation_id, guest_list, user_facing=False, duration_override=None, zone_id=0, start_time=date_and_time.INVALID_DATE_AND_TIME, scoring_enabled=True, spawn_sims_during_zone_spin_up=False, main_goal_visiblity=True, creation_source=None, linked_sim_id=GLOBAL_SITUATION_LINKED_SIM_ID, **extra_kwargs):
        self._situation_type = situation_type
        self._situation_id = situation_id
        self._purpose = seed_purpose
        self._guest_list = guest_list
        self._user_facing = user_facing
        self._zone_id = zone_id
        self._duration_override = duration_override
        self._job_data = {}
        self._simple = None
        self._score = 0
        self._complex = None
        self._goal_tracker = None
        self._start_time = start_time
        self._scoring_enabled = scoring_enabled
        self._allow_creation = True
        self._allow_time_jump = False
        self._main_goal_visiblity = main_goal_visiblity
        self._spawn_sims_during_zone_spin_up = spawn_sims_during_zone_spin_up
        self._travel_time = None
        self.extra_kwargs = extra_kwargs
        self._creation_source = creation_source
        self._linked_sim_id = linked_sim_id

    def __str__(self):
        return '{}({})'.format(self._situation_type.__name__, self._situation_id)

    @property
    def situation_id(self):
        return self._situation_id

    @situation_id.setter
    def situation_id(self, situation_id):
        self._situation_id = situation_id

    @property
    def situation_type(self):
        return self._situation_type

    @property
    def guest_list(self):
        return self._guest_list

    @property
    def purpose(self):
        return self._purpose

    @property
    def user_facing(self):
        return self._user_facing

    @property
    def duration_override(self):
        return self._duration_override

    @duration_override.setter
    def duration_override(self, value):
        self._duration_override = value

    @property
    def score(self):
        return self._score

    @score.setter
    def score(self, score):
        self._score = score

    @property
    def travel_time(self):
        return self._travel_time

    @property
    def start_time(self):
        if self._start_time == date_and_time.INVALID_DATE_AND_TIME:
            return
        return self._start_time

    @property
    def scoring_enabled(self):
        return self._scoring_enabled

    @property
    def allow_creation(self):
        return self._allow_creation

    @allow_creation.setter
    def allow_creation(self, allow):
        self._allow_creation = allow

    @property
    def allow_time_jump(self):
        return self._allow_time_jump

    @allow_time_jump.setter
    def allow_time_jump(self, value):
        self._allow_time_jump = value

    @property
    def spawn_sims_during_zone_spin_up(self):
        return self._spawn_sims_during_zone_spin_up

    @property
    def main_goal_visibility(self):
        return self._main_goal_visiblity

    @property
    def is_loadable(self):
        return self._purpose == SeedPurpose.PERSISTENCE

    @property
    def zone_id(self):
        return self._zone_id

    @property
    def creation_source(self):
        return self._creation_source

    @property
    def linked_sim_id(self):
        return self._linked_sim_id

    @zone_id.setter
    def zone_id(self, value):
        self._zone_id = value

    def finalize_creation_for_save(self):
        if self._complex is not None:
            self._complex.finalize_creation_for_save()
        if self._goal_tracker is not None:
            self._goal_tracker.finalize_creation_for_save()

    def add_job_data(self, job_type, role_state_type, emotional_loot_actions_type=None):
        self._job_data[job_type] = JobData(role_state_type, emotional_loot_actions_type)

    def get_job_data(self):
        return self._job_data

    @property
    def situation_simple_seedling(self):
        return self._simple

    def add_situation_simple_data(self, phase_index, remaining_phase_time):
        self._simple = _SituationSimpleSeedling(phase_index, remaining_phase_time)
        return self._simple

    @property
    def custom_init_params_reader(self):
        if self._complex is None:
            return
        return self._complex.situation_custom_reader

    @property
    def situation_complex_seedling(self):
        return self._complex

    def setup_for_complex_load(self, situation_custom_data, state_custom_data):
        self._complex = _SituationComplexSeedling()
        self._complex.setup_for_load(situation_custom_data, state_custom_data)
        return self._complex

    def setup_for_complex_save(self):
        self._complex = _SituationComplexSeedling()
        self._complex.setup_for_save()
        return self._complex

    def setup_for_custom_init_params(self, writer):
        self._complex = _SituationComplexSeedling()
        self._complex.setup_for_custom_init_params(writer)
        return self._complex

    def setup_for_goal_tracker_save(self, goal_tracker_type, has_offered_goals=True, inherited_target=None):
        self._goal_tracker = GoalTrackerSeedling(goal_tracker_type, has_offered_goals, inherited_target)
        return self._goal_tracker

    @property
    def goal_tracker_seedling(self):
        return self._goal_tracker

    def set_travel_time(self):
        self._travel_time = services.time_service().sim_now

    @classmethod
    def serialize_seeds_to_zone(cls, zone_seeds=None, zone_data_msg=None, blacklist_data=None):
        if zone_seeds is None or zone_data_msg is None:
            return
        zone_data_msg.gameplay_zone_data.ClearField('situations_data')
        for seed in zone_seeds:
            with ProtocolBufferRollback(zone_data_msg.gameplay_zone_data.situations_data.seeds) as seed_proto:
                seed.serialize_to_proto(seed_proto)
        if blacklist_data is None:
            return
        time_now = services.time_service().sim_now.absolute_ticks()
        for (sim_id, blacklist_data) in blacklist_data.items():
            blacklist_info = blacklist_data.get_blacklist_info()
            if not blacklist_info:
                pass
            else:
                with ProtocolBufferRollback(zone_data_msg.gameplay_zone_data.situations_data.blacklist_data) as blacklist_proto:
                    blacklist_proto.sim_id = sim_id
                    for (blacklist_tag, time_left) in blacklist_info:
                        with ProtocolBufferRollback(blacklist_proto.tag_data) as blacklist_tag_proto:
                            blacklist_tag_proto.tag = int(blacklist_tag)
                            blacklist_tag_proto.time = time_now + time_left.in_ticks()

    @classmethod
    def serialize_seeds_to_open_street(cls, open_street_seeds=None, open_street_data_msg=None):
        if open_street_seeds is None or open_street_data_msg is None:
            return
        open_street_data_msg.ClearField('situation_seeds')
        for seed in open_street_seeds:
            with ProtocolBufferRollback(open_street_data_msg.situation_seeds) as seed_proto:
                seed.serialize_to_proto(seed_proto)

    @classmethod
    def serialize_travel_seed_to_slot(cls, save_slot_data_msg=None, travel_seed=None):
        save_slot_data_msg.gameplay_data.ClearField('travel_situation_seed')
        if travel_seed is not None:
            travel_seed.set_travel_time()
            travel_seed.serialize_to_proto(save_slot_data_msg.gameplay_data.travel_situation_seed)

    def serialize_to_proto(self, seed_proto):
        seed_proto.situation_type_id = self._situation_type.guid64
        seed_proto.situation_id = self._situation_id
        seed_proto.seed_purpose = self._purpose
        seed_proto.host_sim_id = self._guest_list._host_sim_id
        seed_proto.filter_requesting_sim_id = self._guest_list.filter_requesting_sim_id
        seed_proto.invite_only = self._guest_list.invite_only
        seed_proto.user_facing = self._user_facing
        if self._duration_override is not None:
            seed_proto.duration = self._duration_override
        seed_proto.zone_id = self._zone_id
        seed_proto.score = self.score
        if self._travel_time is not None:
            seed_proto.create_time = self._travel_time.absolute_ticks()
        seed_proto.start_time = self._start_time.absolute_ticks() if self._start_time is not None else date_and_time.INVALID_DATE_AND_TIME
        seed_proto.scoring_enabled = self._scoring_enabled
        seed_proto.main_goal_visibility = self._main_goal_visiblity
        seed_proto.linked_sim_id = self._linked_sim_id
        for job_type in self._guest_list.get_set_of_jobs():
            for guest_info in self._guest_list.get_guest_infos_for_job(job_type):
                with ProtocolBufferRollback(seed_proto.assignments) as assignment:
                    assignment.sim_id = guest_info.sim_id
                    assignment.job_type_id = guest_info.job_type.guid64
                    assignment.request_priority = guest_info.request_priority
                    assignment.spawning_option = guest_info.spawning_option
                    assignment.expectation_preference = guest_info.expectation_preference
                    assignment.accept_alternate_sim = guest_info.accept_alternate_sim
                    assignment.common_blacklist_categories = guest_info.common_blacklist_categories
                    assignment.elevated_importance_override = guest_info.elevated_importance_override
                    assignment.reservation = guest_info.reservation
                    if guest_info.persisted_role_state_type is not None:
                        assignment.role_state_type_id = guest_info.persisted_role_state_type.guid64
        for (job_type, job_data) in self._job_data.items():
            with ProtocolBufferRollback(seed_proto.jobs_and_role_states) as data:
                data.job_type_id = job_type.guid64
                data.role_state_type_id = job_data.role_state_type.guid64
                if job_data.emotional_loot_actions_type is not None:
                    data.emotional_loot_actions_type_id = job_data.emotional_loot_actions_type.guid64
        if self._simple is not None:
            seed_proto.simple_data.phase_index = self._simple.phase_index
            seed_proto.simple_data.remaining_phase_time = self._simple.remaining_phase_time
        elif self._complex is not None:
            data = self._complex.situation_custom_data
            if data is not None:
                seed_proto.complex_data.situation_custom_data = data
            data = self._complex.state_custom_data
            if data is not None:
                seed_proto.complex_data.state_custom_data = data
        if self._goal_tracker:
            self._goal_tracker.serialize_to_proto(seed_proto.goal_tracker_data)

    @classmethod
    def deserialize_seeds_from_zone(cls, zone_data_msg):
        zone_seeds = []
        if not zone_data_msg.HasField('gameplay_zone_data'):
            return zone_seeds
        if not zone_data_msg.gameplay_zone_data.HasField('situations_data'):
            return zone_seeds
        for seed_data in zone_data_msg.gameplay_zone_data.situations_data.seeds:
            seed = cls.deserialize_from_proto(seed_data)
            if seed is not None:
                zone_seeds.append(seed)
        return zone_seeds

    @classmethod
    def deserialize_seeds_from_open_street(cls, open_street_data_msg):
        open_street_seeds = []
        for seed_data in open_street_data_msg.situation_seeds:
            seed = cls.deserialize_from_proto(seed_data)
            if seed is not None:
                open_street_seeds.append(seed)
        return open_street_seeds

    @classmethod
    def deserialize_travel_seed_from_slot(cls, save_slot_data_msg):
        if not save_slot_data_msg.HasField('gameplay_data'):
            return
        if not save_slot_data_msg.gameplay_data.HasField('travel_situation_seed'):
            return
        msg = save_slot_data_msg.gameplay_data.travel_situation_seed
        if services.current_zone().id != msg.zone_id:
            return
        return cls.deserialize_from_proto(msg)

    @classmethod
    def deserialize_from_proto(cls, seed_proto):
        situation_type = services.situation_manager().get(seed_proto.situation_type_id)
        if situation_type is None:
            return
        guest_list = SituationGuestList(seed_proto.invite_only, seed_proto.host_sim_id, seed_proto.filter_requesting_sim_id)
        for assignment in seed_proto.assignments:
            job_type = services.situation_job_manager().get(assignment.job_type_id)
            if job_type is None:
                pass
            else:
                role_state_type = services.role_state_manager().get(assignment.role_state_type_id)
                guest_info = SituationGuestInfo(assignment.sim_id, job_type, RequestSpawningOption(assignment.spawning_option), BouncerRequestPriority(assignment.request_priority), assignment.expectation_preference, assignment.accept_alternate_sim, SituationCommonBlacklistCategory(assignment.common_blacklist_categories), elevated_importance_override=assignment.elevated_importance_override, reservation=assignment.reservation)
                guest_info._set_persisted_role_state_type(role_state_type)
                guest_list.add_guest_info(guest_info)
        if seed_proto.HasField('duration'):
            duration = seed_proto.duration
        else:
            duration = None
        seed = SituationSeed(situation_type, seed_proto.seed_purpose, seed_proto.situation_id, guest_list, seed_proto.user_facing, duration, seed_proto.zone_id, date_and_time.DateAndTime(seed_proto.start_time), seed_proto.scoring_enabled, main_goal_visiblity=seed_proto.main_goal_visibility, linked_sim_id=seed_proto.linked_sim_id)
        seed._score = seed_proto.score
        if seed_proto.HasField('create_time'):
            seed._travel_time = DateAndTime(seed_proto.create_time)
        for job_data in seed_proto.jobs_and_role_states:
            job_type = services.situation_job_manager().get(job_data.job_type_id)
            if job_type is None:
                pass
            else:
                role_state_type = services.role_state_manager().get(job_data.role_state_type_id)
                if role_state_type is None:
                    pass
                else:
                    emotional_loot_actions_type = None
                    if job_data.HasField('emotional_loot_actions_type_id'):
                        emotional_loot_actions_type = services.action_manager().get(job_data.emotional_loot_actions_type_id)
                    seed.add_job_data(job_type, role_state_type, emotional_loot_actions_type)
        if seed_proto.HasField('simple_data'):
            seed.add_situation_simple_data(seed_proto.simple_data.phase_index, seed_proto.simple_data.remaining_phase_time)
        elif seed_proto.HasField('complex_data'):
            complex_data = seed_proto.complex_data
            situation_custom_data = complex_data.situation_custom_data if complex_data.HasField('situation_custom_data') else None
            state_custom_data = complex_data.state_custom_data if complex_data.HasField('state_custom_data') else None
            seed.setup_for_complex_load(situation_custom_data, state_custom_data)
        if seed_proto.HasField('goal_tracker_data'):
            seed._goal_tracker = GoalTrackerSeedling.deserialize_from_proto(seed_proto.goal_tracker_data)
        return seed

    def get_deserializable_seed_from_serializable_seed(self):
        proto = SituationPersistence_pb2.SituationSeedData()
        self.serialize_to_proto(proto)
        deserialized_seed = SituationSeed.deserialize_from_proto(proto)
        return deserialized_seed

    def get_player_greeted_status(self):
        return self.situation_type.get_player_greeted_status_from_seed(self)

    def get_npc_greeted_status(self, sim_info):
        return self.situation_type.get_npc_greeted_status_during_zone_fixup(self, sim_info)

    def invited_sim_infos_gen(self):
        return self._guest_list.invited_sim_infos_gen()

    def contains_selectable_sim(self):
        client = services.client_manager().get_first_client()
        if client is None:
            return False
        elif any(sim_info in self.invited_sim_infos_gen() for sim_info in client.selectable_sims):
            return True
        return False

    def contains_sim(self, sim_info):
        return sim_info in self.invited_sim_infos_gen()
