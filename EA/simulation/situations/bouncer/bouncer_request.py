from objects import ALL_HIDDEN_REASONSfrom sims4.tuning.tunable import TunableSimMinutefrom sims4.tuning.tunable_base import FilterTagfrom situations.bouncer.bouncer_types import BouncerRequestStatus, BouncerRequestPriority, BouncerExclusivityOption, RequestSpawningOptionfrom uid import UniqueIdGenerator, unique_idimport clockimport gsi_handlers.situation_handlersimport servicesimport simsimport sims4.logimport situations.bouncer.bouncerimport worldlogger = sims4.log.Logger('Bouncer')
def exclusivity_compare(current_request, other_request):
    rule = situations.bouncer.bouncer.Bouncer.are_mutually_exclusive(current_request._exclusivity, other_request._exclusivity)
    if rule is None:
        return 0

    def determine_result(trumping_category):
        if current_request._exclusivity == trumping_category:
            return 1
        else:
            return -1

    option = rule[2]
    if option == BouncerExclusivityOption.EXPECTATION_PREFERENCE:
        if current_request._expectation_preference and not other_request._expectation_preference:
            return determine_result(current_request._exclusivity)
        if current_request._expectation_preference or other_request._expectation_preference:
            return determine_result(other_request._exclusivity)
        if current_request._expectation_preference and other_request._expectation_preference:
            if current_request._creation_id >= other_request._creation_id:
                return determine_result(current_request._exclusivity)
            return determine_result(other_request._exclusivity)
        return determine_result(rule[0])
    if option == BouncerExclusivityOption.NONE:
        return determine_result(rule[0])
    if option == BouncerExclusivityOption.ERROR:
        logger.error('Unexpected Bouncer exclusivity pairing Request:{}, Request:{}. Tell jjacobson', current_request, other_request)
        return determine_result(rule[0])
    elif option == BouncerExclusivityOption.ALREADY_ASSIGNED:
        return determine_result(current_request._exclusivity)

@unique_id('_creation_id')
class SimReservationRequest:

    def __init__(self, situation, sim_id, exclusivity, job_type, request_priority, spawning_option=RequestSpawningOption.DONT_CARE, expectation_preference=False):
        self._situation = situation
        self._sim_id = sim_id
        self._exclusivity = exclusivity
        self._expectation_preference = expectation_preference
        self._job_type = job_type
        self._request_priority = request_priority
        self._spawning_option = spawning_option

    @property
    def sim_id(self):
        return self._sim_id

    @property
    def situation(self):
        return self._situation

    @property
    def exlcusivity(self):
        return self._exclusivity

    @property
    def expectation_preference(self):
        return self._expectation_preference

    @property
    def job_type(self):
        return self._job_type

    @property
    def request_priority(self):
        return self._request_priority

    @property
    def spawning_option(self):
        return self._spawning_option

    def exclusivity_compare(self, other):
        return exclusivity_compare(self, other)

class BouncerRequest:
    TARDY_SIM_TIME = TunableSimMinute(description='Amount of time until a sim coming to a situation is considered tardy', default=30, tuning_filter=FilterTag.EXPERT_MODE)
    _get_next_creation_id = UniqueIdGenerator(1)
    BOUNCER_PRIORITY_INDEX_MULTIPLIER = 2

    def __init__(self, situation, callback_data, job_type, request_priority, user_facing, exclusivity, requested_sim_id=0, accept_alternate_sim=False, blacklist_sim_ids=None, spawning_option=RequestSpawningOption.DONT_CARE, requesting_sim_info=None, expectation_preference=False, common_blacklist_categories=0, for_persisted_sim=False, elevated_importance_override=False, accept_looking_for_more_work=False, specific_spawn_point=None, specific_position=None):
        self._situation = situation
        self._callback_data = callback_data
        self._job_type = job_type
        self._sim_filter = job_type.filter
        self._spawner_tags = job_type.sim_spawner_tags
        self._spawn_at_lot = job_type.spawn_at_lot
        self._spawn_action = job_type.sim_spawn_action
        self._spawn_point_option = job_type.sim_spawner_leave_option
        self._saved_spawner_tags = job_type.sim_spawner_leave_saved_tags
        self._requested_sim_id = requested_sim_id
        self._constrained_sim_ids = {requested_sim_id} if requested_sim_id != 0 else None
        self._continue_if_constraints_fail = accept_alternate_sim
        self._blacklist_sim_ids = blacklist_sim_ids
        self._status = BouncerRequestStatus.INITIALIZED
        self._sim = None
        self._user_facing = user_facing
        self._request_priority = request_priority
        self._spawning_option = spawning_option
        self._requesting_sim_info = requesting_sim_info
        self._exclusivity = exclusivity
        self._creation_id = self._get_next_creation_id()
        self._expectation_preference = expectation_preference
        self._common_blacklist_categories = common_blacklist_categories
        self._for_persisted_sim = for_persisted_sim
        self.elevated_importance_override = elevated_importance_override
        if self._is_explicit:
            unfulfilled_index = 0
        else:
            unfulfilled_index = len(BouncerRequestPriority)*self.BOUNCER_PRIORITY_INDEX_MULTIPLIER
        unfulfilled_index += self._request_priority*self.BOUNCER_PRIORITY_INDEX_MULTIPLIER
        if not self.elevated_importance_override:
            unfulfilled_index += 1
        self._unfulfilled_index = unfulfilled_index
        self._sim_spawner_service_request = None
        self._accept_looking_for_more_work = accept_looking_for_more_work
        self._specific_spawn_point = specific_spawn_point
        self._specific_position = specific_position

    @property
    def situation(self):
        return self._situation

    def _destroy(self, reason=None):
        self._status = BouncerRequestStatus.DESTROYED
        self._sim_spawner_service_request = None
        self._sim = None
        if gsi_handlers.situation_handlers.bouncer_archiver.enabled:
            gsi_handlers.situation_handlers.archive_bouncer_request(self, 'DESTROYED', status_reason=reason)

    def __str__(self):
        return 'Request(situation: {}, sim id: {}, filter: {})'.format(self._situation, self._requested_sim_id, self._sim_filter)

    def _submit(self):
        self._status = BouncerRequestStatus.SUBMITTED
        self._reset_tardy()
        if gsi_handlers.situation_handlers.bouncer_archiver.enabled:
            gsi_handlers.situation_handlers.archive_bouncer_request(self, 'SUBMITTED')

    def _can_assign_sim_to_request(self, sim):
        return True

    def _assign_sim(self, sim, silently=False):
        if self._sim is not None:
            raise AssertionError('Attempting to assign sim: {} to a request: {} that already has a sim: {}'.format(sim, self, self._sim))
        self._status = BouncerRequestStatus.FULFILLED
        self._sim = sim
        if gsi_handlers.situation_handlers.bouncer_archiver.enabled:
            gsi_handlers.situation_handlers.archive_bouncer_request(self, 'SIM ASSIGNED')
        if silently == False:
            self._situation.on_sim_assigned_to_request(sim, self)

    def _unassign_sim(self, sim, silently=False):
        if self._status == BouncerRequestStatus.DESTROYED:
            return
        if self._is_sim_assigned_to_request(sim) == False:
            raise AssertionError('Attempting to unassign sim {} from a request {} that it is not assigned to{}'.format(sim, self))
        self._sim = None
        if gsi_handlers.situation_handlers.bouncer_archiver.enabled:
            gsi_handlers.situation_handlers.archive_bouncer_request(self, 'SIM UNASSIGNED', sim_override=sim)
        if silently == False:
            self._situation.on_sim_unassigned_from_request(sim, self)

    def _change_assigned_sim(self, new_sim):
        if gsi_handlers.situation_handlers.bouncer_archiver.enabled:
            gsi_handlers.situation_handlers.archive_bouncer_request(self, 'ASSIGNEMENT CHANGED START')
        old_sim = self._sim
        self._unassign_sim(old_sim, silently=True)
        self._assign_sim(new_sim, silently=True)
        self._situation.on_sim_replaced_in_request(old_sim, new_sim, self)
        if gsi_handlers.situation_handlers.bouncer_archiver.enabled:
            gsi_handlers.situation_handlers.archive_bouncer_request(self, 'ASSIGNEMENT CHANGED END')

    def _is_sim_assigned_to_request(self, sim):
        return self._sim is sim

    @property
    def _assigned_sim(self):
        return self._sim

    @property
    def _allows_spawning(self):
        if self._spawning_option == RequestSpawningOption.CANNOT_SPAWN:
            return False
        if self._requested_sim_id == 0:
            return True
        sim_info = services.sim_info_manager().get(self._requested_sim_id)
        if sim_info is None:
            return True
        elif sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is not None:
            return False
        return True

    def _can_spawn_now(self, during_zone_spin_up_service):
        if not self._allows_spawning:
            return False
        if not during_zone_spin_up_service:
            return True
        return self._situation.spawn_sims_during_zone_spin_up

    @property
    def _requires_spawning(self):
        return self._spawning_option == RequestSpawningOption.MUST_SPAWN

    @property
    def spawn_at_lot(self):
        return self._spawn_at_lot

    def spawner_tags(self, during_zone_spin_up=False):
        if during_zone_spin_up and self._situation.is_traveling_situation:
            return (world.spawn_point.SpawnPoint.ARRIVAL_SPAWN_POINT_TAG,)
        return self._spawner_tags

    def raw_spawner_tags(self):
        return self._spawner_tags

    @property
    def sim_spawn_reason(self):
        if self._situation.is_situation_of_elevated_importance:
            return sims.sim_spawner_service.SimSpawnReason.IMPORTANT_SITUATION
        if self._situation.situation_serialization_option == situations.situation_types.SituationSerializationOption.LOT:
            return sims.sim_spawner_service.SimSpawnReason.ZONE_SITUATION
        if self._situation.situation_serialization_option == situations.situation_types.SituationSerializationOption.OPEN_STREETS:
            return sims.sim_spawner_service.SimSpawnReason.OPEN_STREETS_SITUATION
        return sims.sim_spawner_service.SimSpawnReason.DEFAULT

    @property
    def should_preroll_during_zone_spin_up(self):
        return not self._situation.is_traveling_situation

    @property
    def elevated_importance(self):
        return self._job_type.elevated_importance or self.elevated_importance_override

    @property
    def spawn_point_option(self):
        return self._spawn_point_option

    @property
    def saved_spawner_tags(self):
        return self._saved_spawner_tags

    @property
    def _initiating_sim_info(self):
        return self._situation.initiating_sim_info

    @property
    def _should_use_auto_fill_blacklist(self):
        return self._request_priority == BouncerRequestPriority.EVENT_AUTO_FILL or (self._request_priority == BouncerRequestPriority.BACKGROUND_HIGH or (self._request_priority == BouncerRequestPriority.BACKGROUND_MEDIUM or self._request_priority == BouncerRequestPriority.BACKGROUND_LOW))

    def _get_blacklist(self):
        if self._blacklist_sim_ids:
            blacklist = set(self._blacklist_sim_ids)
        else:
            blacklist = set()
        if self._should_use_auto_fill_blacklist:
            blacklist = blacklist | services.get_zone_situation_manager().get_auto_fill_blacklist(self._job_type)
        return blacklist

    @property
    def common_blacklist_categories(self):
        return self._common_blacklist_categories

    @property
    def _is_obsolete(self):
        return self._status == BouncerRequestStatus.FULFILLED and self._sim is None

    @property
    def _is_tardy(self):
        if self._status == BouncerRequestStatus.FULFILLED or self._status == BouncerRequestStatus.DESTROYED:
            return False
        return self._tardy_time < services.time_service().sim_now

    def _reset_tardy(self):
        self._tardy_time = services.time_service().sim_now + clock.interval_in_sim_minutes(BouncerRequest.TARDY_SIM_TIME)

    @property
    def _is_fulfilled(self):
        return self._status == BouncerRequestStatus.FULFILLED

    @property
    def _is_explicit(self):
        return self._requested_sim_id != 0

    @property
    def _has_assigned_sims(self):
        return self._sim is not None

    def _exclusivity_compare(self, other):
        return exclusivity_compare(self, other)

    @property
    def _is_factory(self):
        return False

    def _get_request_klout(self):
        if self._situation.has_no_klout:
            return
        klout = self._request_priority*4
        if not self.elevated_importance:
            klout += 1
        if not self._user_facing:
            klout += 2
        return klout

    def get_additional_filter_terms(self):
        return self._job_type.get_location_based_filter_terms()

    @property
    def callback_data(self):
        return self._callback_data

    def clone_for_replace(self, only_if_explicit=False):
        if only_if_explicit and not self._is_explicit:
            return
        request = BouncerRequest(self._situation, self._callback_data, self._job_type, self._request_priority, user_facing=self._user_facing, exclusivity=self._exclusivity, blacklist_sim_ids=self._blacklist_sim_ids, spawning_option=self._spawning_option, requesting_sim_info=self._requesting_sim_info, accept_looking_for_more_work=self._accept_looking_for_more_work)
        return request

    @property
    def assigned_sim(self):
        return self._assigned_sim

    @property
    def requested_sim_id(self):
        return self._requested_sim_id

    @property
    def is_factory(self):
        return self._is_factory

    @property
    def job_type(self):
        return self._job_type

    @property
    def spawning_option(self):
        return self._spawning_option

    @property
    def request_priority(self):
        return self._request_priority

    @property
    def expectation_preference(self):
        return self._expectation_preference

    @property
    def accept_alternate_sim(self):
        return self._continue_if_constraints_fail

    @property
    def specific_spawn_point(self):
        return self._specific_spawn_point

    @property
    def specific_position(self):
        return self._specific_position

class BouncerRequestFactory(BouncerRequest):

    def __init__(self, situation, callback_data, job_type, request_priority, user_facing, exclusivity, requesting_sim_info=None):
        super().__init__(situation, callback_data, job_type=job_type, request_priority=request_priority, user_facing=user_facing, exclusivity=exclusivity, requesting_sim_info=requesting_sim_info)

    @property
    def _allows_spawning(self):
        return False

    @property
    def _requires_spawning(self):
        return False

    def _is_sim_assigned_to_request(self, sim):
        return False

    def _assign_sim(self, sim, silently=False):
        raise NotImplementedError('Cannot assign sims to a request factory: {}'.format(self))

    def _unassign_sim(self, sim, silently=False):
        raise NotImplementedError('Cannot unassign sims from a request factory: {}'.format(self))

    def _change_assigned_sim(self, sim):
        raise NotImplementedError('Attempting to change_assigned_sim on a request factory:{}'.format(self))

    @property
    def _assigned_sims(self):
        pass

    @property
    def _is_tardy(self):
        return False

    @property
    def _is_obsolete(self):
        return False

    @property
    def _is_explicit(self):
        return False

    @property
    def _has_assigned_sims(self):
        return False

    @property
    def _is_factory(self):
        return True

    def _create_request(self, sim):
        request = BouncerRequest(self._situation, self._callback_data, self._job_type, self._request_priority, user_facing=self._user_facing, exclusivity=self._exclusivity, requested_sim_id=sim.id, blacklist_sim_ids=self._blacklist_sim_ids, spawning_option=RequestSpawningOption.CANNOT_SPAWN, requesting_sim_info=self._requesting_sim_info, expectation_preference=self._expectation_preference, accept_looking_for_more_work=self._accept_looking_for_more_work)
        return request

    def _get_request_klout(self):
        pass

    @property
    def assigned_sim(self):
        pass

    @property
    def requested_sim_id(self):
        return 0

    def clone_for_replace(self, only_if_explicit=False):
        pass

class BouncerFallbackRequestFactory(BouncerRequestFactory):

    def __init__(self, situation, callback_data, job_type, user_facing, exclusivity):
        super().__init__(situation, callback_data, job_type=job_type, request_priority=BouncerRequestPriority.EVENT_DEFAULT_JOB, user_facing=user_facing, exclusivity=exclusivity)

class BouncerHostRequestFactory(BouncerRequestFactory):

    def __init__(self, situation, callback_data, job_type, user_facing, exclusivity, requesting_sim_info):
        super().__init__(situation, callback_data, job_type=job_type, request_priority=BouncerRequestPriority.EVENT_HOSTING, user_facing=user_facing, exclusivity=exclusivity, requesting_sim_info=requesting_sim_info)

class BouncerNPCFallbackRequestFactory(BouncerRequestFactory):

    def __init__(self, situation, callback_data, job_type, exclusivity, request_priority=BouncerRequestPriority.LEAVE):
        super().__init__(situation, callback_data, job_type=job_type, request_priority=request_priority, user_facing=False, exclusivity=exclusivity)

    def _can_assign_sim_to_request(self, sim):
        return sim.sim_info.is_npc and not sim.sim_info.lives_here

class SelectableSimRequestFactory(BouncerRequestFactory):

    def __init__(self, situation, callback_data, job_type, exclusivity, request_priority=BouncerRequestPriority.EVENT_VIP):
        super().__init__(situation, callback_data=callback_data, job_type=job_type, request_priority=request_priority, user_facing=False, exclusivity=exclusivity)

    def _can_assign_sim_to_request(self, sim):
        return sim.is_selectable
