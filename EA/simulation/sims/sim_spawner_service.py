from math import floorfrom objects import ALL_HIDDEN_REASONSfrom sims.sim_info_types import SimZoneSpinUpActionfrom tag import Tagimport date_and_timeimport enumimport gsi_handlersimport interactions.utils.deathimport servicesimport simsimport sims4.tuninglogger = sims4.log.Logger('Sim Spawner')
class SimSpawnReason(enum.Int, export=False):
    ACTIVE_HOUSEHOLD = ...
    TRAVELING = ...
    LOT_OWNER = ...
    IMPORTANT_SITUATION = ...
    SAVED_ON_ZONE = ...
    ZONE_SITUATION = ...
    SAVED_ON_OPEN_STREETS = ...
    OPEN_STREETS_SITUATION = ...
    DEFAULT = ...

class ISimSpawnerServiceCustomer:

    def on_sim_creation_callback(self, sim, request):
        pass

    def on_sim_creation_denied_callback(self, request):
        pass

class SimSpawnPlaceStrategy:

    @property
    def position(self):
        pass

    @property
    def location(self):
        pass

    @property
    def spawner_tags(self):
        pass

    @property
    def spawn_point(self):
        pass

    @property
    def spawn_point_option(self):
        pass

    @property
    def saved_spawner_tags(self):
        pass

    @property
    def spawn_action(self):
        pass

    @property
    def spawn_at_lot(self):
        return True

    @property
    def gsi_entry(self):
        return ''

class SimSpawnPositionStrategy(SimSpawnPlaceStrategy):

    def __init__(self, position):
        self._position = position

    @property
    def position(self):
        return self._position

    @property
    def gsi_entry(self):
        return str(self._position)

class SimSpawnLocationStrategy(SimSpawnPlaceStrategy):

    def __init__(self, location):
        self._location = location

    @property
    def location(self):
        return self._location

    @property
    def gsi_entry(self):
        return str(self._location)

class SimSpawnPointStrategy(SimSpawnPlaceStrategy):

    def __init__(self, spawner_tags, spawn_point_option, spawn_action, saved_spawner_tags=None, spawn_at_lot=True):
        self._spawner_tags = spawner_tags
        self._spawn_point_option = spawn_point_option
        self._spawn_action = spawn_action
        self._saved_spawner_tags = saved_spawner_tags
        self._spawn_at_lot = spawn_at_lot

    @property
    def spawner_tags(self):
        return self._spawner_tags

    @property
    def spawn_point_option(self):
        return self._spawn_point_option

    @property
    def spawn_action(self):
        return self._spawn_action

    @property
    def saved_spawner_tags(self):
        return self._saved_spawner_tags

    @property
    def spawn_at_lot(self):
        return self._spawn_at_lot

    @property
    def gsi_entry(self):
        return str(self._spawner_tags)

class SimSpawnSpecificPointStrategy(SimSpawnPlaceStrategy):

    def __init__(self, spawn_point, spawn_point_option, spawn_action, saved_spawner_tags=None):
        self._spawn_point = spawn_point
        self._spawn_point_option = spawn_point_option
        self._spawn_action = spawn_action
        self._saved_spawner_tags = saved_spawner_tags

    @property
    def spawn_point(self):
        return self._spawn_point

    @property
    def spawn_point_option(self):
        return self._spawn_point_option

    @property
    def spawn_action(self):
        return self._spawn_action

    @property
    def saved_spawner_tags(self):
        return self._saved_spawner_tags

    @property
    def gsi_entry(self):
        return str(self._spawn_point)

class SimSpawnBaseRequest:

    def __init__(self, sim_info, customer, customer_data=None):
        self._sim_info = sim_info
        self._customer = customer
        self._customer_data = customer_data

    @property
    def customer_data(self):
        return self._customer_data

    @property
    def sim_info(self):
        return self._sim_info

    def is_for_sim_info(self, sim_info):
        return self._sim_info is sim_info

    def _is_request_for_same_sim(self, request):
        return self._sim_info is request._sim_info

    def __str__(self):
        return 'sim:{}'.format(self._sim_info)

    def log_to_gsi(self, action, reason=None):
        if reason is None:
            reason = ''
        gsi_handlers.sim_spawner_service_log.archive_sim_spawner_service_log_entry(action, self._sim_info, reason, '', '')

class SimSpawnRequest(SimSpawnBaseRequest):

    def __init__(self, sim_info, spawn_reason, place_strategy, secondary_priority=0, customer=None, customer_data=None, game_breaker=False, from_load=False, spin_up_action=SimZoneSpinUpAction.NONE):
        super().__init__(sim_info, customer, customer_data=customer_data)
        self._spawn_reason = spawn_reason
        self._secondary_priority = secondary_priority
        self._place_strategy = place_strategy
        self._game_breaker = game_breaker
        self._from_load = from_load
        self._spin_up_action = spin_up_action

    @property
    def spawn_reason(self):
        return self._spawn_reason

    @property
    def secondary_priority(self):
        return self._secondary_priority

    def __str__(self):
        return 'sim:{}, reason:{} priority:{} spin up_action:{} placement:{}'.format(self._sim_info, self._spawn_reason, self._secondary_priority, self._spin_up_action, self._place_strategy.gsi_entry)

    def log_to_gsi(self, action, reason=None):
        if reason is None:
            reason = self._spawn_reason
        gsi_handlers.sim_spawner_service_log.archive_sim_spawner_service_log_entry(action, self._sim_info, reason, self._secondary_priority, self._place_strategy.gsi_entry)

class SimListenerRequest(SimSpawnBaseRequest):
    pass

class _SpawningMode(enum.Int, export=False):
    BATCH_COLLECTION = 0
    BATCH_SPAWNING = 1
    WAITING_HITTING_MARKS = 2
    UPDATE = 3

class SimSpawnerService(sims4.service_manager.Service):
    LEAVING_INTERACTION_TAGS = sims4.tuning.tunable.TunableSet(description='\n        Interaction tags to detect sims running leave lot interactions.\n        ', tunable=sims4.tuning.tunable.TunableEnumEntry(tunable_type=Tag, default=Tag.INVALID, tuning_filter=sims4.tuning.tunable_base.FilterTag.EXPERT_MODE))
    NPC_SOFT_CAP = sims4.tuning.tunable.Tunable(description='\n                The base value for calculating the soft cap on the maximum \n                number of NPCs instantiated.\n                \n                The actual value of the NPC soft cap will be\n                this tuning value minus the number of sims in the active household.\n                \n                There is no hard cap because certain types of NPCs must always\n                spawn or the game will be broken. The prime example of a \n                game breaker is the Grim Reaper.\n                \n                If the number of NPCs is:\n                \n                1) At or above the soft cap only game breaker NPCs will be spawned.\n                \n                2) Above the soft cap then low priority NPCs will be driven from the lot.\n                \n                3) Equal to the soft cap and there are pending requests for higher priority\n                NPCs, then lower priority NPCs will be driven from the lot.\n                                \n                ', tunable_type=int, default=20, tuning_filter=sims4.tuning.tunable_base.FilterTag.EXPERT_MODE)
    SPAWN_COOLDOWN_MINUTES = 5
    COUNT_NPCS_COOLDOWN_MINUTES = 5
    _cap_cheat_enabled = False
    _npc_soft_cap_override = None

    def __init__(self):
        self._submitted_requests = []
        self._submitted_needs_sorting = False
        self._spawning_requests = []
        self._listening_requests = []
        self._sim_spawned_callbacks = sims4.callback_utils.CallableList()
        self._next_spawn_time = date_and_time.DATE_AND_TIME_ZERO
        self._spawn_cooldown = date_and_time.create_time_span(0, 0, SimSpawnerService.SPAWN_COOLDOWN_MINUTES)
        self._next_npc_count_time = date_and_time.DATE_AND_TIME_ZERO
        self._npc_count_cooldown = date_and_time.create_time_span(0, 0, SimSpawnerService.COUNT_NPCS_COOLDOWN_MINUTES)
        self._number_of_instantiated_npcs = 0
        self._number_of_leaving_npcs = 0
        self._on_npc_count_updated = sims4.callback_utils.CallableList()
        self._npc_cap_modifier = 0
        self._mode = _SpawningMode.BATCH_COLLECTION
        self._gui_smoke_notification_enabled = False
        self._prune_and_sort_submitted_requests_override = None

    def submit_request(self, request):
        if request in self._submitted_requests:
            return
        self._submitted_requests.append(request)
        self._submitted_needs_sorting = True
        if gsi_handlers.sim_spawner_service_log.sim_spawner_service_log_archiver.enabled:
            request.log_to_gsi('Request Submitted')
        logger.debug('Request Submitted :{}', request)

    def withdraw_request(self, request):
        if request in self._submitted_requests:
            self._submitted_requests.remove(request)
            self._submitted_needs_sorting = True
        elif request in self._spawning_requests:
            self._spawning_requests.remove(request)
        if gsi_handlers.sim_spawner_service_log.sim_spawner_service_log_archiver.enabled:
            request.log_to_gsi('Request Withdrawn')
        logger.debug('Request Withdrawn: {}', request)

    def set_prune_and_sort_override(self, override):
        self._prune_and_sort_submitted_requests_override = override
        self._submitted_needs_sorting = True

    def submit_listener(self, request):
        if request in self._listening_requests:
            return
        self._listening_requests.append(request)
        if gsi_handlers.sim_spawner_service_log.sim_spawner_service_log_archiver.enabled:
            request.log_to_gsi('Listener Submitted')
        logger.debug('Listener Submitted: {}', request)

    def register_sim_spawned_callback(self, callback):
        self._sim_spawned_callbacks.register(callback)

    def unregister_sim_spawned_callback(self, callback):
        if callback in self._sim_spawned_callbacks:
            self._sim_spawned_callbacks.remove(callback)

    def get_set_of_requested_sim_ids(self):
        sim_ids = set()
        for request in self._submitted_requests:
            sim_ids.add(request._sim_info.id)
        for request in self._spawning_requests:
            sim_ids.add(request._sim_info.id)
        return sim_ids

    def enable_perf_cheat(self, enable=True):
        self._cap_cheat_enabled = enable

    @property
    def number_of_npcs_instantiated(self):
        return self._number_of_instantiated_npcs

    @property
    def number_of_npcs_leaving(self):
        return self._number_of_leaving_npcs

    @property
    def npc_soft_cap(self):
        cap = self.NPC_SOFT_CAP if self._npc_soft_cap_override is None else self._npc_soft_cap_override
        if services.active_household() is None:
            return 0
        cap -= floor(self._npc_cap_modifier)
        return cap - services.active_household().household_size

    def add_npc_cap_modifier(self, cap_modifier):
        self._npc_cap_modifier += cap_modifier
        if self._npc_cap_modifier < 0:
            logger.error('NPC Cap modifier is {}, which is invalid. Clamping to 0.', self._npc_cap_modifier)
            self._npc_cap_modifier = 0

    def set_npc_soft_cap_override(self, override):
        self._npc_soft_cap_override = override

    def register_on_npc_count_updated(self, callback):
        self._on_npc_count_updated.append(callback)

    def unregister_on_npc_count_updated(self, callback):
        if callback in self._on_npc_count_updated:
            self._on_npc_count_updated.remove(callback)

    def enable_gui_smoke_notification(self):
        self._gui_smoke_notification_enabled = True

    def batch_spawn_during_zone_spin_up(self):
        self._mode = _SpawningMode.BATCH_SPAWNING
        done = False
        while not done:
            done = not self._spawn_next_sim()
        if not self._spawning_requests:
            logger.error('No sims where spawned during zone spin up.', owner='jjacobson')
            self._mode = _SpawningMode.WAITING_HITTING_MARKS

    def on_hit_their_marks(self):
        self._mode = _SpawningMode.UPDATE

    @property
    def batch_spawning_complete(self):
        return self._mode >= _SpawningMode.WAITING_HITTING_MARKS

    def update(self):
        if self._mode != _SpawningMode.UPDATE:
            return
        self._update_info_on_number_of_npcs()
        self._spawn_next_sim()

    def _update_info_on_number_of_npcs(self, force_update=False):
        if self._next_npc_count_time > services.time_service().sim_now and not force_update:
            return
        self._next_npc_count_time = services.time_service().sim_now + self._npc_count_cooldown
        self._number_of_instantiated_npcs = 0
        self._number_of_leaving_npcs = 0
        for sim in services.sim_info_manager().instanced_sims_gen():
            if sim.sim_info.is_npc:
                self._number_of_instantiated_npcs += 1
                if self.sim_is_leaving(sim):
                    self._number_of_leaving_npcs += 1
        self._on_npc_count_updated()

    def sim_is_leaving(self, sim):
        return len(sim.get_running_and_queued_interactions_by_tag(self.LEAVING_INTERACTION_TAGS)) > 0

    def _get_sort_lambda(self):
        return lambda request: (not request._sim_info.is_selectable, request._spawn_reason, request._secondary_priority)

    def _prune_and_sort_submitted_requests(self):
        if not self._submitted_needs_sorting:
            return []
        self._submitted_needs_sorting = False
        if self._prune_and_sort_submitted_requests_override is not None:
            sorted_requests = list(self._submitted_requests)
            self._prune_and_sort_submitted_requests_override(sorted_requests)
            to_prune_set = set(self._submitted_requests)
            sorted_set = set(sorted_requests)
            to_prune_set -= sorted_set
            self._submitted_requests = sorted_requests
            return list(to_prune_set)
        self._submitted_requests.sort(key=self._get_sort_lambda())
        return []

    def _cleanup_submitted_requests(self):
        to_deny = []
        already_instanced = []
        sim_info_manager = services.sim_info_manager()
        for request in self._submitted_requests:
            sim_info = request._sim_info
            if sim_info_manager.get(sim_info.id) is None:
                to_deny.append((request, 'Sim info is not in the sim info manager.'))
            elif sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS):
                already_instanced.append((request, 'Sim info is already instanced.'))
        for (request, reason) in to_deny:
            self._submitted_requests.remove(request)
            self._customer_denied_notification(request, reason)
        for (request, _) in already_instanced:
            self._submitted_requests.remove(request)
            self._customer_success_notification(request._sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS), request)

    def _spawn_next_sim(self):
        self._cleanup_submitted_requests()
        denied_requests = self._prune_and_sort_submitted_requests()
        for request in denied_requests:
            self._customer_denied_notification(request, 'Request was pruned.')
        if not self._submitted_requests:
            return False
        active_household = services.active_household()
        only_spawn_game_breakers_and_selectables = not self._cap_cheat_enabled and (active_household is None or self._number_of_instantiated_npcs >= self.npc_soft_cap)
        request = None
        if not only_spawn_game_breakers_and_selectables:
            request = self._submitted_requests[0]
        else:
            for request_candidate in self._submitted_requests:
                if not request_candidate._sim_info.is_selectable:
                    if request_candidate._game_breaker:
                        request = request_candidate
                        break
                request = request_candidate
                break
        if request is None:
            return False
        else:
            should_spawn = False
            if request._sim_info.is_selectable or (request._game_breaker or self._mode == _SpawningMode.BATCH_SPAWNING) or self._gui_smoke_notification_enabled:
                should_spawn = True
            elif self._next_spawn_time <= services.time_service().sim_now:
                should_spawn = True
            if should_spawn:
                if request._sim_info.is_npc:
                    self._number_of_instantiated_npcs += 1
                self._spawn_requested_sim(request)
                return True
        return False

    def _spawn_requested_sim(self, request):
        for other_request in tuple(self._submitted_requests):
            if request._is_request_for_same_sim(other_request):
                self._submitted_requests.remove(other_request)
                self._spawning_requests.append(other_request)
        for other_request in tuple(self._listening_requests):
            if request._is_request_for_same_sim(other_request):
                self._listening_requests.remove(other_request)
                self._spawning_requests.append(other_request)
        place_strategy = request._place_strategy
        success = sims.sim_spawner.SimSpawner.spawn_sim(request._sim_info, sim_position=place_strategy.position, sim_location=place_strategy.location, sim_spawner_tags=place_strategy.spawner_tags, spawn_point_option=place_strategy.spawn_point_option, saved_spawner_tags=place_strategy.saved_spawner_tags, spawn_action=place_strategy.spawn_action, from_load=request._from_load, spawn_point=place_strategy.spawn_point, spawn_at_lot=place_strategy.spawn_at_lot)
        if success:
            sim_info = request._sim_info
            if services.get_rabbit_hole_service().will_override_spin_up_action(sim_info):
                services.sim_info_manager().schedule_sim_spin_up_action(sim_info, SimZoneSpinUpAction.NONE)
            else:
                services.sim_info_manager().schedule_sim_spin_up_action(sim_info, request._spin_up_action)
            self._next_spawn_time = services.time_service().sim_now + self._spawn_cooldown
            message = 'Spawn Start'
        else:
            if request in self._spawning_requests:
                self._spawning_requests.remove(request)
            message = 'Spawn Failed'
        if gsi_handlers.sim_spawner_service_log.sim_spawner_service_log_archiver.enabled:
            request.log_to_gsi(message)
        logger.debug('{}: {}', message, request)

    def on_sim_creation(self, sim):
        matching_requests = []
        for request in tuple(self._spawning_requests):
            if request._sim_info is sim.sim_info:
                self._spawning_requests.remove(request)
                matching_requests.append(request)
        for request in matching_requests:
            self._customer_success_notification(sim, request)
        self._sim_spawned_callbacks(sim)
        if not self._spawning_requests:
            self._mode = _SpawningMode.WAITING_HITTING_MARKS
            while self._submitted_requests:
                request = self._submitted_requests.pop(0)
                self._customer_denied_notification(request, 'Request denied because batch spawning is complete.')
            while self._listening_requests:
                request = self._listening_requests.pop(0)
                self._customer_denied_notification(request, 'Request denied because batch spawning is complete.')
        if self._mode == _SpawningMode.BATCH_SPAWNING and self._gui_smoke_notification_enabled and not (self._spawning_requests or self._submitted_requests):
            self._gui_smoke_notification_enabled = False
            client = services.client_manager().get_first_client()
            if client:
                output = sims4.commands.AutomationOutput(client.id)
                if output:
                    output('SituationSpawning; Success:True')

    def _customer_success_notification(self, sim, request):
        if request._customer is not None:
            try:
                request._customer.on_sim_creation_callback(sim, request)
            except Exception as exc:
                logger.exception('Exception while notifying customer in sim spawner service', exc=exc)
        if gsi_handlers.sim_spawner_service_log.sim_spawner_service_log_archiver.enabled:
            request.log_to_gsi('Spawn Complete')
        logger.debug('Spawn Complete: {}', request)

    def _customer_denied_notification(self, request, reason):
        if request._customer is not None:
            request._customer.on_sim_creation_denied_callback(request)
        if gsi_handlers.sim_spawner_service_log.sim_spawner_service_log_archiver.enabled:
            request.log_to_gsi('Spawn Denied!', reason=reason)
        logger.debug('Spawn Denied!: {}', request)

    def get_queue_for_gsi(self):
        sorted_pending = sorted(self._submitted_requests, key=self._get_sort_lambda())
        gsi_queue = []
        for request in sorted_pending:
            entry = {'sim': str(request._sim_info), 'reason': str(request._spawn_reason), 'priority': str(request._secondary_priority), 'position': request._place_strategy.gsi_entry}
            gsi_queue.append(entry)
        return gsi_queue
