from _collections import defaultdictfrom collections import namedtupleimport heapqfrom objects import ALL_HIDDEN_REASONSfrom sims.sim_info_types import SimZoneSpinUpActionfrom situations.bouncer.bouncer_types import BouncerRequestPriority, BouncerRequestStatus, BouncerExclusivityCategory, BouncerExclusivityOptionfrom situations.situation_types import SituationCommonBlacklistCategoryfrom tag import Tagfrom world.spawn_point import SpawnPointOptionimport enumimport servicesimport sims.sim_spawner_serviceimport sims4.logimport sims4.randomimport situationslogger = sims4.log.Logger('Bouncer')
class BouncerSimData:

    def __init__(self, bouncer, sim):
        self._sim_ref = sim.ref(lambda _: bouncer._sim_weakref_callback(sim))
        self._requests = []
        self.looking_for_new_situation = False

    def destroy(self):
        self._sim_ref = None
        self._requests.clear()
        self._requests = None

    def add_request(self, request, trump_all_exclusions=False):
        excluded = self._get_excluded_requests(request, trump_all_exclusions=trump_all_exclusions)
        self._requests.append(request)
        return excluded

    def remove_request(self, request):
        try:
            self._requests.remove(request)
        except ValueError:
            pass

    @property
    def requests(self):
        return set(self._requests)

    @property
    def is_obsolete(self):
        return len(self._requests) == 0

    def can_assign_to_request(self, new_request, check_exclusivity=True):
        if new_request in self._requests:
            return False
        for cur_request in self._requests:
            if cur_request._situation is new_request._situation:
                return False
            if check_exclusivity and cur_request._exclusivity_compare(new_request) > 0:
                return False
        return True

    def get_request_with_best_klout(self):
        best_klout = None
        best_request = None
        for request in self._requests:
            klout = request._get_request_klout()
            if not best_request is None:
                if klout is not None and klout < best_klout:
                    best_klout = klout
                    best_request = request
            best_klout = klout
            best_request = request
        return best_request

    def _get_excluded_requests(self, new_request, trump_all_exclusions=False):
        excluded = []
        for cur_request in self._requests:
            compare_result = cur_request._exclusivity_compare(new_request)
            if compare_result > 0:
                if trump_all_exclusions:
                    excluded.append(cur_request)
                else:
                    logger.error('New request: {} is excluded by existing request: {}', new_request, cur_request)
                    if compare_result < 0:
                        excluded.append(cur_request)
            elif compare_result < 0:
                excluded.append(cur_request)
        return excluded

class _BouncerSituationData:

    def __init__(self, situation):
        self._situation = situation
        self._requests = set()
        self._first_assignment_pass_completed = False
        self._reservation_requests = set()

    def add_request(self, request):
        self._requests.add(request)

    def remove_request(self, request):
        self._requests.discard(request)

    @property
    def requests(self):
        return set(self._requests)

    def add_reservation_request(self, request):
        self._reservation_requests.add(request)

    def remove_reservation_request(self, request):
        self._reservation_requests.discard(request)

    @property
    def reservation_requests(self):
        return set(self._reservation_requests)

    @property
    def first_assignment_pass_completed(self):
        return self._first_assignment_pass_completed

    def on_first_assignment_pass_completed(self):
        self._first_assignment_pass_completed = True

class SimRequestScore(namedtuple('SimRequestScore', 'sim_id, request, score')):

    def __eq__(self, o):
        return self.score == o.score

    def __ne__(self, o):
        return self.score != o.score

    def __lt__(self, o):
        return self.score > o.score

    def __le__(self, o):
        return self.score >= o.score

    def __gt__(self, o):
        return self.score < o.score

    def __ge__(self, o):
        return self.score <= o.score

class _BestRequestKlout(namedtuple('BestRequestKlout', 'request, klout')):

    def __eq__(self, o):
        return self.klout == o.klout

    def __ne__(self, o):
        return self.klout != o.klout

    def __lt__(self, o):
        return self.klout < o.klout

    def __le__(self, o):
        return self.klout <= o.klout

    def __gt__(self, o):
        return self.klout > o.klout

    def __ge__(self, o):
        return self.klout >= o.klout

class _WorstRequestKlout(namedtuple('WorstRequestKlout', 'request, klout')):

    def __eq__(self, o):
        return self.klout == o.klout

    def __ne__(self, o):
        return self.klout != o.klout

    def __lt__(self, o):
        return self.klout > o.klout

    def __le__(self, o):
        return self.klout >= o.klout

    def __gt__(self, o):
        return self.klout < o.klout

    def __ge__(self, o):
        return self.klout <= o.klout

class _BouncerUpdateMode(enum.Int, export=False):
    OFFLINE = 0
    FULLY_OPERATIONAL = 1

class Bouncer(sims.sim_spawner_service.ISimSpawnerServiceCustomer):
    SPAWN_COOLDOWN_MINUTES = 5
    EXCLUSIVITY_RULES = [(BouncerExclusivityCategory.NORMAL, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.EXPECTATION_PREFERENCE), (BouncerExclusivityCategory.NORMAL, BouncerExclusivityCategory.PRE_VISIT, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.NORMAL, BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.NORMAL_UNPOSSESSABLE, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.EXPECTATION_PREFERENCE), (BouncerExclusivityCategory.NORMAL_UNPOSSESSABLE, BouncerExclusivityCategory.PRE_VISIT, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.NORMAL_UNPOSSESSABLE, BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.NORMAL_UNPOSSESSABLE, BouncerExclusivityCategory.INFECTED, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.WALKBY, BouncerExclusivityCategory.NORMAL, BouncerExclusivityOption.EXPECTATION_PREFERENCE), (BouncerExclusivityCategory.WALKBY, BouncerExclusivityCategory.NORMAL_UNPOSSESSABLE, BouncerExclusivityOption.EXPECTATION_PREFERENCE), (BouncerExclusivityCategory.WALKBY, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.EXPECTATION_PREFERENCE), (BouncerExclusivityCategory.WALKBY, BouncerExclusivityCategory.WALKBY, BouncerExclusivityOption.ALREADY_ASSIGNED), (BouncerExclusivityCategory.WALKBY, BouncerExclusivityCategory.VENUE_BACKGROUND, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.WALKBY, BouncerExclusivityCategory.NON_WALKBY_BACKGROUND, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.SERVICE, BouncerExclusivityCategory.WALKBY, BouncerExclusivityOption.ALREADY_ASSIGNED), (BouncerExclusivityCategory.SERVICE, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.EXPECTATION_PREFERENCE), (BouncerExclusivityCategory.SERVICE, BouncerExclusivityCategory.NORMAL, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.SERVICE, BouncerExclusivityCategory.NORMAL_UNPOSSESSABLE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.SERVICE, BouncerExclusivityCategory.SERVICE, BouncerExclusivityOption.ALREADY_ASSIGNED), (BouncerExclusivityCategory.SERVICE, BouncerExclusivityCategory.FESTIVAL_GOER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.SERVICE, BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.VISIT, BouncerExclusivityCategory.WALKBY, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.VISIT, BouncerExclusivityCategory.SERVICE, BouncerExclusivityOption.EXPECTATION_PREFERENCE), (BouncerExclusivityCategory.VISIT, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.VISIT, BouncerExclusivityCategory.UNGREETED, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.VISIT, BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.VISIT, BouncerExclusivityCategory.PRE_VISIT, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.NORMAL, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.NORMAL_UNPOSSESSABLE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.WALKBY, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.SERVICE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.VISIT, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.PRE_VISIT, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityOption.ALREADY_ASSIGNED), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.UNGREETED, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.NEUTRAL, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.VENUE_EMPLOYEE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.VENUE_BACKGROUND, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.CLUB_GATHERING, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.FESTIVAL_BACKGROUND, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.FESTIVAL_GOER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.LEAVE_NOW, BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.UNGREETED, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.EXPECTATION_PREFERENCE), (BouncerExclusivityCategory.UNGREETED, BouncerExclusivityCategory.NORMAL, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.UNGREETED, BouncerExclusivityCategory.NORMAL_UNPOSSESSABLE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.UNGREETED, BouncerExclusivityCategory.WALKBY, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.UNGREETED, BouncerExclusivityCategory.SERVICE, BouncerExclusivityOption.ALREADY_ASSIGNED), (BouncerExclusivityCategory.UNGREETED, BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.PRE_VISIT, BouncerExclusivityCategory.WALKBY, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.PRE_VISIT, BouncerExclusivityCategory.SERVICE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.PRE_VISIT, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.PRE_VISIT, BouncerExclusivityCategory.UNGREETED, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.PRE_VISIT, BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.WORKER, BouncerExclusivityCategory.WALKBY, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.WORKER, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.WORKER, BouncerExclusivityCategory.NORMAL, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.WORKER, BouncerExclusivityCategory.NORMAL_UNPOSSESSABLE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.WORKER, BouncerExclusivityCategory.SERVICE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.WORKER, BouncerExclusivityCategory.VISIT, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.WORKER, BouncerExclusivityCategory.PRE_VISIT, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.WORKER, BouncerExclusivityCategory.NEUTRAL, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.WORKER, BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.VENUE_EMPLOYEE, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.EXPECTATION_PREFERENCE), (BouncerExclusivityCategory.VENUE_EMPLOYEE, BouncerExclusivityCategory.NORMAL, BouncerExclusivityOption.EXPECTATION_PREFERENCE), (BouncerExclusivityCategory.VENUE_EMPLOYEE, BouncerExclusivityCategory.NORMAL_UNPOSSESSABLE, BouncerExclusivityOption.EXPECTATION_PREFERENCE), (BouncerExclusivityCategory.VENUE_EMPLOYEE, BouncerExclusivityCategory.WALKBY, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.VENUE_EMPLOYEE, BouncerExclusivityCategory.VENUE_BACKGROUND, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.VENUE_EMPLOYEE, BouncerExclusivityCategory.VENUE_EMPLOYEE, BouncerExclusivityOption.ALREADY_ASSIGNED), (BouncerExclusivityCategory.VENUE_EMPLOYEE, BouncerExclusivityCategory.CLUB_GATHERING, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.VENUE_EMPLOYEE, BouncerExclusivityCategory.FESTIVAL_GOER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.VENUE_EMPLOYEE, BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.VENUE_EMPLOYEE, BouncerExclusivityCategory.SQUAD, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.CLUB_GATHERING, BouncerExclusivityCategory.CLUB_GATHERING, BouncerExclusivityOption.ALREADY_ASSIGNED), (BouncerExclusivityCategory.CLUB_GATHERING, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.CLUB_GATHERING, BouncerExclusivityCategory.WALKBY, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.CLUB_GATHERING, BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.FESTIVAL_BACKGROUND, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.FESTIVAL_BACKGROUND, BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.FESTIVAL_BACKGROUND, BouncerExclusivityCategory.FESTIVAL_GOER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.FESTIVAL_GOER, BouncerExclusivityCategory.FESTIVAL_GOER, BouncerExclusivityOption.ALREADY_ASSIGNED), (BouncerExclusivityCategory.FESTIVAL_GOER, BouncerExclusivityCategory.NORMAL, BouncerExclusivityOption.EXPECTATION_PREFERENCE), (BouncerExclusivityCategory.FESTIVAL_GOER, BouncerExclusivityCategory.NORMAL_UNPOSSESSABLE, BouncerExclusivityOption.EXPECTATION_PREFERENCE), (BouncerExclusivityCategory.FESTIVAL_GOER, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.EXPECTATION_PREFERENCE), (BouncerExclusivityCategory.FESTIVAL_GOER, BouncerExclusivityCategory.WALKBY, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.FESTIVAL_GOER, BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityCategory.WALKBY, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.CAREGIVER, BouncerExclusivityCategory.WALKBY, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.CAREGIVER, BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.CAREGIVER, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.VENUE_GOER, BouncerExclusivityCategory.VENUE_GOER, BouncerExclusivityOption.ALREADY_ASSIGNED), (BouncerExclusivityCategory.VENUE_GOER, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.VENUE_GOER, BouncerExclusivityCategory.WALKBY_SNATCHER, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.SQUAD, BouncerExclusivityCategory.LEAVE, BouncerExclusivityOption.NONE), (BouncerExclusivityCategory.NEUTRAL_UNPOSSESSABLE, BouncerExclusivityCategory.INFECTED, BouncerExclusivityOption.NONE)]
    INDEXES_PER_BOUNCER_REQUEST_PRIORITY = 4
    MAX_UNFULFILLED_INDEX = len(BouncerRequestPriority)*INDEXES_PER_BOUNCER_REQUEST_PRIORITY
    _exclusivity_rules = None
    _spawning_freeze_enabled = False
    _cap_cheat_enabled = False

    def __init__(self):
        self._unfulfilled_requests = []
        for unfulfilled_index in range(Bouncer.MAX_UNFULFILLED_INDEX):
            self._unfulfilled_requests.insert(unfulfilled_index, [])
        self._sim_filter_service_in_progress = False
        self._fulfilled_requests = []
        self._sim_to_bouncer_sim_data = {}
        self._situation_to_bouncer_situation_data = {}
        self._update_mode = _BouncerUpdateMode.OFFLINE
        self._reserved_sims = defaultdict(list)
        self._situation_id_for_filter_gsi = None

    def destroy(self):
        self.stop()
        self._clear_silently()

    def request_all_sims_during_zone_spin_up(self):
        self._spawn_all_during_zone_spin_up()

    def assign_all_sims_during_zone_spin_up(self):
        self._assign_instanced_sims_to_unfulfilled_requests()

    def start_full_operations(self):
        self._update_mode = _BouncerUpdateMode.FULLY_OPERATIONAL
        services.sim_spawner_service().register_on_npc_count_updated(self._monitor_npc_soft_cap)

    def stop(self):
        services.sim_spawner_service().unregister_on_npc_count_updated(self._monitor_npc_soft_cap)
        self._update_mode = _BouncerUpdateMode.OFFLINE

    def reset(self):
        self.stop()
        self._clear_silently()
        self.start_full_operations()

    def _clear_silently(self):
        for priority_list in self._unfulfilled_requests:
            for request in priority_list:
                request._destroy()
            priority_list.clear()
        self._sim_filter_service_in_progress = False
        for request in self._fulfilled_requests:
            request._destroy()
        self._fulfilled_requests.clear()
        for data in self._sim_to_bouncer_sim_data.values():
            data.destroy()
        self._sim_to_bouncer_sim_data.clear()
        self._situation_to_bouncer_situation_data.clear()

    def submit_request(self, request):
        self._unfulfilled_requests[request._unfulfilled_index].append(request)
        request._submit()
        situation_data = self._situation_to_bouncer_situation_data.setdefault(request._situation, _BouncerSituationData(self))
        situation_data.add_request(request)

    def withdraw_request(self, request, silently=False, reason=None):
        if request is None or request._status == BouncerRequestStatus.DESTROYED:
            return
        sims_removed_from_request = []
        if request._assigned_sim is not None:
            sims_removed_from_request.append(request._assigned_sim)
            self._unassign_sim_from_request(request._assigned_sim, request, silently=silently)
        if request in self._fulfilled_requests:
            self._fulfilled_requests.remove(request)
        elif request in self._unfulfilled_requests[request._unfulfilled_index]:
            self._unfulfilled_requests[request._unfulfilled_index].remove(request)
        if request._status == BouncerRequestStatus.SIM_FILTER_SERVICE:
            self._sim_filter_service_in_progress = False
        if request._status == BouncerRequestStatus.SPAWN_REQUESTED and request._sim_spawner_service_request is not None:
            services.sim_spawner_service().withdraw_request(request._sim_spawner_service_request)
        situation_data = self._situation_to_bouncer_situation_data.get(request._situation, None)
        if situation_data:
            situation_data.remove_request(request)
        request._destroy(reason=reason)
        for sim in sims_removed_from_request:
            data = self._sim_to_bouncer_sim_data.get(sim, None)
            if data is None:
                pass
            elif data.is_obsolete:
                data.destroy()
                self._sim_to_bouncer_sim_data.pop(sim)

    def submit_reservation_request(self, reservation_request):
        if reservation_request.sim_id in self._reserved_sims:
            requests_to_withdraw = []
            for current_request in self._reserved_sims[reservation_request.sim_id]:
                exclusivity_result = current_request.exclusivity_compare(reservation_request)
                if exclusivity_result == 1:
                    return
                if exclusivity_result == -1:
                    requests_to_withdraw.append(current_request)
            for request in requests_to_withdraw:
                self.withdraw_reservation_request(request)
        else:
            sim_spawner_service = services.sim_spawner_service()
            sim_spawner_service.add_npc_cap_modifier(1)
        situation_data = self._situation_to_bouncer_situation_data.setdefault(reservation_request.situation, _BouncerSituationData(self))
        situation_data.add_reservation_request(reservation_request)
        self._reserved_sims[reservation_request.sim_id].append(reservation_request)

    def withdraw_reservation_request(self, reservation_request):
        if reservation_request.sim_id not in self._reserved_sims:
            return
        situation_data = self._situation_to_bouncer_situation_data.get(reservation_request.situation, None)
        if situation_data:
            situation_data.remove_reservation_request(reservation_request)
        self._reserved_sims[reservation_request.sim_id].remove(reservation_request)
        if not self._reserved_sims[reservation_request.sim_id]:
            sim_spawner_service = services.sim_spawner_service()
            sim_spawner_service.add_npc_cap_modifier(-1)
            del self._reserved_sims[reservation_request.sim_id]

    def replace_reservation_request(self, bouncer_request):
        if bouncer_request.requested_sim_id == 0:
            logger.error("Attempting to replace a bouncer reservation request with a bouncer request that isn't explicit for .  This is unsupported behavior.")
        reservation_requests = self._reserved_sims.get(bouncer_request.requested_sim_id, tuple())
        for reservation_request in reservation_requests:
            if reservation_request.situation is bouncer_request.situation and reservation_request.sim_id == bouncer_request.requested_sim_id:
                self.withdraw_reservation_request(reservation_request)
        self.submit_request(bouncer_request)

    def remove_sim_from_situation(self, sim, situation):
        data = self._sim_to_bouncer_sim_data.get(sim, None)
        if data is None:
            return
        for request in data.requests:
            if request._situation == situation:
                self._unassign_sim_from_request_and_optionally_withdraw(sim, request)
                break

    def on_situation_destroy(self, situation):
        situation_data = self._situation_to_bouncer_situation_data.get(situation, None)
        if not situation_data:
            return
        for request in situation_data.requests:
            self.withdraw_request(request, silently=True, reason='Situation Destroyed')
        for reservation_request in situation_data.reservation_requests:
            self.withdraw_reservation_request(reservation_request)
        del self._situation_to_bouncer_situation_data[situation]

    def situation_requests_gen(self, situation):
        situation_data = self._situation_to_bouncer_situation_data.get(situation, None)
        if not situation_data:
            return
        for request in situation_data.requests:
            if request._is_obsolete == False and request._status != BouncerRequestStatus.DESTROYED:
                yield request

    def situation_reservation_requests_gen(self, situation):
        situation_data = self._situation_to_bouncer_situation_data.get(situation, None)
        if not situation_data:
            return
        for request in situation_data.reservation_requests:
            yield request

    def pending_situation_requests_gen(self, situation):
        for request in self.situation_requests_gen(situation):
            if request._is_fulfilled or request._allows_spawning:
                yield request

    def get_most_important_request_for_sim(self, sim):
        data = self._sim_to_bouncer_sim_data.get(sim, None)
        if data is None or not data.requests:
            return
        best_requests = []
        best_klout = None
        for request in data.requests:
            klout = request._get_request_klout()
            if klout is None:
                pass
            elif best_klout is None:
                best_requests.append(request)
                best_klout = klout
            elif klout == best_klout:
                best_requests.append(request)
            elif klout < best_klout:
                best_requests.clear()
                best_requests.append(request)
                best_klout = klout
        if not best_requests:
            return
        best_requests.sort(key=lambda request: request._creation_id)
        return best_requests[0]

    def get_most_important_situation_for_sim(self, sim):
        request = self.get_most_important_request_for_sim(sim)
        if request is None:
            return
        return request._situation

    def get_unfulfilled_situations_by_tag(self, situation_tag):
        unfulfilled_situations = {}
        for unfulfilled_index in range(self.MAX_UNFULFILLED_INDEX):
            requests = self._unfulfilled_requests[unfulfilled_index]
            for request in requests:
                situation = request._situation
                if situation_tag in situation.tags and situation.id not in unfulfilled_situations:
                    unfulfilled_situations[situation.id] = situation
        return unfulfilled_situations

    @classmethod
    def are_mutually_exclusive(cls, cat1, cat2):
        cls._construct_exclusivity()
        key = cat1 | cat2
        rule = cls._exclusivity_rules.get(key, None)
        return rule

    def spawning_freeze(self, value):
        self._spawning_freeze_enabled = value

    def cap_cheat(self, value):
        self._cap_cheat_enabled = value

    def _set_request_for_sim_filter_gsi(self, request):
        self._situation_id_for_filter_gsi = request.situation.id

    def get_sim_filter_gsi_name(self):
        situation_manager = services.get_zone_situation_manager()
        situation = situation_manager.get(self._situation_id_for_filter_gsi) if situation_manager is not None else None
        return 'Bouncer for Situation: {}'.format(situation)

    @classmethod
    def _construct_exclusivity(cls):
        if cls._exclusivity_rules is not None:
            return
        cls._exclusivity_rules = {}
        for rule in cls.EXCLUSIVITY_RULES:
            cat1 = rule[0]
            cat2 = rule[1]
            key = cat1 | cat2
            if cls._exclusivity_rules.get(key) is not None:
                logger.error('Duplicate situation exclusivity rule for {} and {}', cat1, cat2)
            cls._exclusivity_rules[key] = rule

    def _update(self):
        if self._update_mode == _BouncerUpdateMode.OFFLINE:
            return
        with situations.situation_manager.DelayedSituationDestruction():
            self._assign_instanced_sims_to_unfulfilled_requests()
            self._assigned_sims_looking_for_new_situations_to_unfulfilled_requests()
            self._spawn_sim_for_next_request()
            self._check_for_tardy_requests()

    def _assign_instanced_sims_to_unfulfilled_requests(self):
        with situations.situation_manager.DelayedSituationDestruction():
            all_candidate_sim_ids = set()
            for sim in services.sim_info_manager().instanced_sims_gen():
                if not sim.is_simulating:
                    pass
                elif not sim.visible_to_client:
                    pass
                else:
                    all_candidate_sim_ids.add(sim.id)
            if len(all_candidate_sim_ids) == 0:
                return
            (spawning_sim_ids, active_household_sim_ids, active_lot_household_sim_ids) = self._get_common_blacklists()
            sim_filter_service = services.sim_filter_service()
            for unfulfilled_index in range(Bouncer.MAX_UNFULFILLED_INDEX):
                candidate_requests = list(self._unfulfilled_requests[unfulfilled_index])
                sim_request_score_heap = []
                for request in candidate_requests:
                    if not request._requires_spawning:
                        if request._status != BouncerRequestStatus.SUBMITTED:
                            pass
                        else:
                            candidate_sim_ids = {sim_id for sim_id in all_candidate_sim_ids if self._can_assign_sim_id_to_request(sim_id, request)}
                            if request._constrained_sim_ids:
                                candidate_sim_ids = candidate_sim_ids & request._constrained_sim_ids
                            if not candidate_sim_ids:
                                pass
                            else:
                                if request.job_type.sim_auto_invite_use_common_blacklists_on_instanced_sims:
                                    blacklist = set()
                                    self._apply_common_blacklists(request, blacklist, spawning_sim_ids, active_household_sim_ids, active_lot_household_sim_ids)
                                else:
                                    blacklist = request._get_blacklist()
                                self._set_request_for_sim_filter_gsi(request)
                                filter_results = sim_filter_service.submit_filter(request._sim_filter, callback=None, sim_constraints=list(candidate_sim_ids), blacklist_sim_ids=blacklist, requesting_sim_info=request._requesting_sim_info, allow_yielding=False, additional_filter_terms=request.get_additional_filter_terms(), gsi_source_fn=self.get_sim_filter_gsi_name)
                                for filter_result in filter_results:
                                    heapq.heappush(sim_request_score_heap, SimRequestScore(sim_id=filter_result.sim_info.id, request=request, score=filter_result.score))
                while sim_request_score_heap:
                    sim_request_score = heapq.heappop(sim_request_score_heap)
                    request = sim_request_score.request
                    if request._is_fulfilled:
                        pass
                    else:
                        sim = services.object_manager().get(sim_request_score.sim_id)
                        if sim is None:
                            pass
                        elif self._can_assign_sim_to_request(sim, request):
                            if request._is_factory:
                                request = request._create_request(sim)
                                self.submit_request(request)
                            self._assign_sim_to_request(sim, request)
            for (situation, situation_data) in self._situation_to_bouncer_situation_data.items():
                if not situation_data.first_assignment_pass_completed:
                    situation.on_first_assignment_pass_completed()
                    situation_data.on_first_assignment_pass_completed()

    def _assigned_sims_looking_for_new_situations_to_unfulfilled_requests(self):
        with situations.situation_manager.DelayedSituationDestruction():
            all_candidate_sim_ids = [sim.sim_id for (sim, bouncer_data) in self._sim_to_bouncer_sim_data.items() if bouncer_data.looking_for_new_situation]
            if not all_candidate_sim_ids:
                return
            sim_filter_service = services.sim_filter_service()
            for unfulfilled_index in range(Bouncer.MAX_UNFULFILLED_INDEX):
                candidate_requests = list(self._unfulfilled_requests[unfulfilled_index])
                sim_request_score_heap = []
                for request in candidate_requests:
                    self._set_request_for_sim_filter_gsi(request)
                    if request._accept_looking_for_more_work:
                        if request._status != BouncerRequestStatus.SUBMITTED:
                            pass
                        else:
                            candidate_sim_ids = {sim_id for sim_id in all_candidate_sim_ids if self._can_assign_sim_id_to_request(sim_id, request, check_exclusivity=False)}
                            if request._constrained_sim_ids:
                                candidate_sim_ids = candidate_sim_ids & request._constrained_sim_ids
                            if not candidate_sim_ids:
                                pass
                            else:
                                filter_results = sim_filter_service.submit_filter(request._sim_filter, callback=None, sim_constraints=list(candidate_sim_ids), blacklist_sim_ids=request._get_blacklist(), requesting_sim_info=request._requesting_sim_info, allow_yielding=False, additional_filter_terms=request.get_additional_filter_terms(), gsi_source_fn=self.get_sim_filter_gsi_name)
                                for filter_result in filter_results:
                                    heapq.heappush(sim_request_score_heap, SimRequestScore(sim_id=filter_result.sim_info.id, request=request, score=filter_result.score))
                while sim_request_score_heap:
                    sim_request_score = heapq.heappop(sim_request_score_heap)
                    request = sim_request_score.request
                    if request._is_fulfilled:
                        pass
                    else:
                        sim = services.object_manager().get(sim_request_score.sim_id)
                        if sim is None:
                            pass
                        elif self._can_assign_sim_to_request(sim, request, check_exclusivity=False):
                            if request._is_factory:
                                request = request._create_request(sim)
                                self.submit_request(request)
                            self._assign_sim_to_request(sim, request, trump_all_exclusions=True)
            for (situation, situation_data) in self._situation_to_bouncer_situation_data.items():
                if not situation_data.first_assignment_pass_completed:
                    situation.on_first_assignment_pass_completed()
                    situation_data.on_first_assignment_pass_completed()

    def _assign_sim_to_request(self, sim, request, trump_all_exclusions=False):
        with situations.situation_manager.DelayedSituationDestruction():
            data = self._sim_to_bouncer_sim_data.setdefault(sim, BouncerSimData(self, sim))
            excluded = data.add_request(request, trump_all_exclusions=trump_all_exclusions)
            request._assign_sim(sim)
            if request._is_fulfilled:
                self._unfulfilled_requests[request._unfulfilled_index].remove(request)
                self._fulfilled_requests.append(request)
            for ex_request in excluded:
                self._unassign_sim_from_request_and_optionally_withdraw(sim, ex_request)

    def _unassign_sim_from_request(self, sim, request, silently=False):
        data = self._sim_to_bouncer_sim_data.get(sim, None)
        if data:
            data.remove_request(request)
        request._unassign_sim(sim, silently)

    def _unassign_sim_from_request_and_optionally_withdraw(self, sim, request, silently=False):
        self._unassign_sim_from_request(sim, request, silently)
        if request._status != BouncerRequestStatus.DESTROYED and request._is_obsolete:
            self.withdraw_request(request, reason='Sim reassigned')

    def _check_request_against_reservation_request(self, sim_id, request, check_exclusivity):
        if not check_exclusivity:
            return True
        if sim_id in self._reserved_sims:
            for request in self._reserved_sims[sim_id]:
                if request.exclusivity_compare(request) > 0:
                    return False
        return True

    def _can_assign_sim_id_to_request(self, sim_id, new_request, check_exclusivity=True):
        sim_info = services.sim_info_manager().get(sim_id)
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) if sim_info is not None else None
        if sim is None:
            return True
        if not self._check_request_against_reservation_request(sim_id, new_request, check_exclusivity):
            return False
        return self._can_assign_sim_to_request(sim, new_request, check_exclusivity=check_exclusivity)

    def _can_assign_sim_to_request(self, sim, new_request, check_exclusivity=True):
        if not new_request._can_assign_sim_to_request(sim):
            return False
        data = self._sim_to_bouncer_sim_data.get(sim, None)
        if data is None:
            return True
        if not self._check_request_against_reservation_request(sim.sim_id, new_request, check_exclusivity):
            return False
        return data.can_assign_to_request(new_request, check_exclusivity=check_exclusivity)

    def _get_common_blacklists(self):
        active_household = services.active_household()
        sim_spawner_service = services.sim_spawner_service()
        spawning_sim_ids = sim_spawner_service.get_set_of_requested_sim_ids()
        if active_household is None:
            active_household_sim_ids = set()
        else:
            active_household_sim_ids = {sim_info.sim_id for sim_info in active_household.sim_info_gen()}
        active_lot_household = services.current_zone().get_active_lot_owner_household()
        if active_lot_household is None:
            active_lot_household_sim_ids = set()
        else:
            active_lot_household_sim_ids = {sim_info.sim_id for sim_info in active_lot_household.sim_info_gen()}
        return (spawning_sim_ids, active_household_sim_ids, active_lot_household_sim_ids)

    def _apply_common_blacklists(self, request, blacklist, spawning_sim_ids, active_household_sim_ids, active_lot_household_sim_ids):
        blacklist.update(request._get_blacklist())
        if request.common_blacklist_categories & SituationCommonBlacklistCategory.ACTIVE_HOUSEHOLD:
            blacklist.update(active_household_sim_ids)
        if request.common_blacklist_categories & SituationCommonBlacklistCategory.ACTIVE_LOT_HOUSEHOLD:
            blacklist.update(active_lot_household_sim_ids)
        if not request._constrained_sim_ids:
            blacklist.update(spawning_sim_ids)

    def _spawn_sim_for_next_request(self):
        if self._spawning_freeze_enabled:
            return
        if self._sim_filter_service_in_progress:
            return
        active_household = services.active_household()
        if active_household is None:
            return
        (spawning_sim_ids, active_household_sim_ids, active_lot_household_sim_ids) = self._get_common_blacklists()
        for unfulfilled_index in range(Bouncer.MAX_UNFULFILLED_INDEX):
            requests = self._unfulfilled_requests[unfulfilled_index]
            if not requests:
                pass
            else:
                requests = [request for request in requests if request._can_spawn_now(False) and request._status == BouncerRequestStatus.SUBMITTED]
                if not requests:
                    pass
                else:
                    request = sims4.random.random.choice(requests)
                    self._sim_filter_service_in_progress = True
                    request._status = BouncerRequestStatus.SIM_FILTER_SERVICE
                    sim_constraints = list(request._constrained_sim_ids) if request._constrained_sim_ids else None
                    blacklist = set()
                    self._apply_common_blacklists(request, blacklist, spawning_sim_ids, active_household_sim_ids, active_lot_household_sim_ids)
                    self._set_request_for_sim_filter_gsi(request)
                    services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=1, sim_filter=request._sim_filter, callback=self._sim_filter_service_callback, callback_event_data=request, sim_constraints=sim_constraints, continue_if_constraints_fail=request._continue_if_constraints_fail, blacklist_sim_ids=blacklist, requesting_sim_info=request._requesting_sim_info, additional_filter_terms=request.get_additional_filter_terms(), gsi_source_fn=self.get_sim_filter_gsi_name)

    def _spawn_all_during_zone_spin_up(self):
        (spawning_sim_ids, active_household_sim_ids, active_lot_household_sim_ids) = self._get_common_blacklists()
        spawning_sim_ids = set()
        for unfulfilled_index in range(Bouncer.MAX_UNFULFILLED_INDEX):
            requests = tuple(self._unfulfilled_requests[unfulfilled_index])
            for request in requests:
                if request._status != BouncerRequestStatus.SUBMITTED:
                    pass
                else:
                    if not request._for_persisted_sim:
                        if request._can_spawn_now(True):
                            request._status = BouncerRequestStatus.SIM_FILTER_SERVICE
                            sim_constraints = list(request._constrained_sim_ids) if request._constrained_sim_ids else None
                            blacklist = set()
                            self._apply_common_blacklists(request, blacklist, spawning_sim_ids, active_household_sim_ids, active_lot_household_sim_ids)
                            logger.debug('_spawn_all_during_zone_spin_up request:{} blacklist:{}', request, blacklist)
                            if request._for_persisted_sim and not request._job_type.should_revalidate_sim_on_load:
                                sim_filter = None
                            else:
                                sim_filter = request._sim_filter
                            self._set_request_for_sim_filter_gsi(request)
                            filter_results = services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=1, sim_filter=sim_filter, sim_constraints=sim_constraints, continue_if_constraints_fail=request._continue_if_constraints_fail, blacklist_sim_ids=blacklist, requesting_sim_info=request._requesting_sim_info, allow_yielding=False, additional_filter_terms=request.get_additional_filter_terms(), gsi_source_fn=self.get_sim_filter_gsi_name)
                            if filter_results:
                                spawning_sim_ids.add(filter_results[0].sim_info.sim_id)
                            self._sim_filter_service_callback(filter_results, request)
                    request._status = BouncerRequestStatus.SIM_FILTER_SERVICE
                    sim_constraints = list(request._constrained_sim_ids) if request._constrained_sim_ids else None
                    blacklist = set()
                    self._apply_common_blacklists(request, blacklist, spawning_sim_ids, active_household_sim_ids, active_lot_household_sim_ids)
                    logger.debug('_spawn_all_during_zone_spin_up request:{} blacklist:{}', request, blacklist)
                    if request._for_persisted_sim and not request._job_type.should_revalidate_sim_on_load:
                        sim_filter = None
                    else:
                        sim_filter = request._sim_filter
                    self._set_request_for_sim_filter_gsi(request)
                    filter_results = services.sim_filter_service().submit_matching_filter(number_of_sims_to_find=1, sim_filter=sim_filter, sim_constraints=sim_constraints, continue_if_constraints_fail=request._continue_if_constraints_fail, blacklist_sim_ids=blacklist, requesting_sim_info=request._requesting_sim_info, allow_yielding=False, additional_filter_terms=request.get_additional_filter_terms(), gsi_source_fn=self.get_sim_filter_gsi_name)
                    if filter_results:
                        spawning_sim_ids.add(filter_results[0].sim_info.sim_id)
                    self._sim_filter_service_callback(filter_results, request)

    def _check_for_tardy_requests(self):
        for unfulfilled_index in range(Bouncer.MAX_UNFULFILLED_INDEX):
            requests = list(self._unfulfilled_requests[unfulfilled_index])
            for request in requests:
                if request._is_tardy:
                    request._situation.on_tardy_request(request)
                    if request._status != BouncerRequestStatus.DESTROYED:
                        request._reset_tardy()

    def _is_request_with_assigned_npc_who_is_not_leaving(self, request):
        sim = request.assigned_sim
        if sim is None or sim.sim_info.is_npc and sim.sim_info.lives_here:
            return False
        return services.sim_spawner_service().sim_is_leaving(sim) == False

    def _is_request_for_npc(self, request):
        sim = services.object_manager().get(request.requested_sim_id)
        if sim is None:
            return True
        return sim.sim_info.is_npc

    def _monitor_npc_soft_cap(self):
        if self._cap_cheat_enabled:
            return
        if services.active_household() is None:
            return
        if not services.current_zone().is_zone_running:
            return
        situation_manager = services.get_zone_situation_manager()
        sim_spawner_service = services.sim_spawner_service()
        if sim_spawner_service.number_of_npcs_instantiated > sim_spawner_service.npc_soft_cap:
            situation_manager.expedite_leaving()
        num_here_but_not_leaving = sim_spawner_service.number_of_npcs_instantiated - sim_spawner_service.number_of_npcs_leaving
        excess_npcs_not_leaving = num_here_but_not_leaving - sim_spawner_service.npc_soft_cap
        if excess_npcs_not_leaving > 0:
            self._make_npcs_leave_now_must_run(excess_npcs_not_leaving)
        elif excess_npcs_not_leaving == 0:
            unfulfilled_heap = self._get_unfulfilled_request_heap_by_best_klout(filter_func=self._is_request_for_npc)
            fulfilled_heap = self._get_assigned_request_heap_by_worst_klout(filter_func=self._is_request_with_assigned_npc_who_is_not_leaving)
            if unfulfilled_heap and fulfilled_heap:
                best_unfulfilled = heapq.heappop(unfulfilled_heap)
                worst_fulfilled = heapq.heappop(fulfilled_heap)
                if best_unfulfilled.klout < worst_fulfilled.klout:
                    situation_manager.make_sim_leave_now_must_run(worst_fulfilled.request.assigned_sim)

    def _get_assigned_request_heap_by_worst_klout(self, filter_func=None):
        klout_heap = []
        for sim_data in self._sim_to_bouncer_sim_data.values():
            request = sim_data.get_request_with_best_klout()
            if request is None:
                pass
            elif filter_func is not None and not filter_func(request):
                pass
            else:
                klout = request._get_request_klout()
                if klout is None:
                    pass
                else:
                    heapq.heappush(klout_heap, _WorstRequestKlout(request=request, klout=klout))
        return klout_heap

    def _get_unfulfilled_request_heap_by_best_klout(self, filter_func=None):
        klout_heap = []
        for unfulfilled_index in range(Bouncer.MAX_UNFULFILLED_INDEX):
            requests = self._unfulfilled_requests[unfulfilled_index]
            for request in requests:
                klout = request._get_request_klout()
                if klout is not None:
                    if filter_func is not None and not filter_func(request):
                        pass
                    else:
                        heapq.heappush(klout_heap, _BestRequestKlout(request=request, klout=klout))
        return klout_heap

    def _make_npcs_leave_now_must_run(self, sim_count):
        situation_manager = services.get_zone_situation_manager()
        klout_heap = self._get_assigned_request_heap_by_worst_klout(filter_func=self._is_request_with_assigned_npc_who_is_not_leaving)
        while klout_heap and sim_count > 0:
            worst = heapq.heappop(klout_heap)
            situation_manager.make_sim_leave_now_must_run(worst.request.assigned_sim)
            sim_count -= 1

    def _sim_filter_service_callback(self, filter_results, bouncer_request):
        self._sim_filter_service_in_progress = False
        logger.debug('_sim_filter_service_callback for sims {} for request {}', filter_results, bouncer_request)
        if bouncer_request._status == BouncerRequestStatus.DESTROYED:
            return
        if bouncer_request._status != BouncerRequestStatus.SIM_FILTER_SERVICE:
            logger.error('_sim_filter_service_callback for wrong request!')
            return
        current_zone = services.current_zone()
        if current_zone.is_zone_shutting_down:
            return
        during_zone_spin_up = not current_zone.is_zone_running
        if filter_results:
            sim_info = filter_results[0].sim_info
            if sim_info.is_baby:
                logger.error('Bouncer request tried spawning baby which is invalid: {}', bouncer_request)
                bouncer_request._situation.on_failed_to_spawn_sim_for_request(bouncer_request)
                self.withdraw_request(bouncer_request, reason='Trying to spawn baby')
                return
            if not bouncer_request._for_persisted_sim:
                spin_up_action = SimZoneSpinUpAction.NONE
                if bouncer_request.should_preroll_during_zone_spin_up:
                    spin_up_action = SimZoneSpinUpAction.PREROLL
                bouncer_request._status = BouncerRequestStatus.SPAWN_REQUESTED
                if during_zone_spin_up and bouncer_request.specific_position is not None:
                    spawn_strategy = sims.sim_spawner_service.SimSpawnPositionStrategy(bouncer_request.specific_position)
                elif bouncer_request.specific_spawn_point is not None:
                    spawn_strategy = sims.sim_spawner_service.SimSpawnSpecificPointStrategy(spawn_point=bouncer_request.specific_spawn_point, spawn_point_option=bouncer_request.spawn_point_option, spawn_action=bouncer_request._spawn_action, saved_spawner_tags=bouncer_request.saved_spawner_tags)
                else:
                    spawn_strategy = sims.sim_spawner_service.SimSpawnPointStrategy(spawner_tags=bouncer_request.spawner_tags(during_zone_spin_up), spawn_point_option=bouncer_request.spawn_point_option, spawn_action=bouncer_request._spawn_action, saved_spawner_tags=bouncer_request.saved_spawner_tags, spawn_at_lot=bouncer_request.spawn_at_lot)
                sim_spawn_request = sims.sim_spawner_service.SimSpawnRequest(sim_info, bouncer_request.sim_spawn_reason, spawn_strategy, secondary_priority=bouncer_request._unfulfilled_index, customer=self, customer_data=bouncer_request, spin_up_action=spin_up_action, game_breaker=bouncer_request.request_priority == BouncerRequestPriority.GAME_BREAKER)
                bouncer_request._sim_spawner_service_request = sim_spawn_request
                services.sim_spawner_service().submit_request(sim_spawn_request)
            else:
                listener_request = sims.sim_spawner_service.SimListenerRequest(sim_info, customer=self, customer_data=bouncer_request)
                bouncer_request._sim_spawner_service_request = listener_request
                services.sim_spawner_service().submit_listener(listener_request)
        else:
            bouncer_request._situation.on_failed_to_spawn_sim_for_request(bouncer_request)
            self.withdraw_request(bouncer_request, reason='Failed to find/create SimInfo')

    def on_sim_creation_callback(self, sim, sim_spawner_service_request):
        logger.debug('on_sim_creation_callback request:{}', sim_spawner_service_request)
        bouncer_request = sim_spawner_service_request.customer_data
        if bouncer_request._status == BouncerRequestStatus.DESTROYED:
            return
        bouncer_request._sim_spawner_service_request = None
        if self._can_assign_sim_to_request(sim, bouncer_request):
            self._assign_sim_to_request(sim, bouncer_request)
            if services.current_zone().is_zone_running:
                sim.run_full_autonomy_next_ping()
        else:
            bouncer_request._state = BouncerRequestStatus.SUBMITTED

    def on_sim_creation_denied_callback(self, sim_spawner_service_request):
        logger.debug('on_sim_creation_denied_callback request:{}', sim_spawner_service_request)
        bouncer_request = sim_spawner_service_request.customer_data
        bouncer_request._situation.on_failed_to_spawn_sim_for_request(bouncer_request)
        self.withdraw_request(bouncer_request, reason='Failed to spawn in sim')

    def _on_end_sim_creation_notification(self, sim):
        if self._update_mode == _BouncerUpdateMode.FULLY_OPERATIONAL:
            self._assign_instanced_sims_to_unfulfilled_requests()

    def _sim_weakref_callback(self, sim):
        logger.debug('Bouncer:_sim_weakref_callback: {}', sim, owner='sscholl')
        data = self._sim_to_bouncer_sim_data.get(sim, None)
        if data is None:
            return
        requests_sim_was_in = list(data.requests)
        data.destroy()
        self._sim_to_bouncer_sim_data.pop(sim)
        for request in requests_sim_was_in:
            self._unassign_sim_from_request_and_optionally_withdraw(sim, request)

    def _all_requests_gen(self):
        for unfulfilled_index in range(Bouncer.MAX_UNFULFILLED_INDEX):
            for request in self._unfulfilled_requests[unfulfilled_index]:
                yield request
        for request in self._fulfilled_requests:
            yield request

    def set_sim_looking_for_new_situation(self, sim):
        data = self._sim_to_bouncer_sim_data.get(sim, None)
        if data is None:
            return
        data.looking_for_new_situation = True
