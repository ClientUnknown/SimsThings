import collectionsfrom filters import sim_filter_handlersfrom filters.tunable import FilterResult, FilterTermTagfrom interactions.liability import Liabilityfrom objects import ALL_HIDDEN_REASONSfrom random import shufflefrom sims4 import randomfrom sims4.service_manager import Servicefrom singletons import EMPTY_SETimport enumimport filtersimport gsi_handlers.sim_filter_service_handlersimport servicesimport sims4.loglogger = sims4.log.Logger('SimFilter')SIM_FILTER_GLOBAL_BLACKLIST_LIABILITY = 'SimFilterGlobalBlacklistLiability'
class SimFilterGlobalBlacklistReason(enum.Int, export=False):
    PHONE_CALL = 1
    SIM_INFO_BEING_REMOVED = 2
    MISSING_PET = 3
    RABBIT_HOLE = 4

class SimFilterGlobalBlacklistLiability(Liability):

    def __init__(self, blacklist_sim_ids, reason, **kwargs):
        super().__init__(**kwargs)
        self._blacklist_sim_ids = blacklist_sim_ids
        self._reason = reason
        self._has_been_added = False

    def on_add(self, _):
        if self._has_been_added:
            return
        sim_filter_service = services.sim_filter_service()
        if sim_filter_service is not None:
            for sim_id in self._blacklist_sim_ids:
                services.sim_filter_service().add_sim_id_to_global_blacklist(sim_id, self._reason)
        self._has_been_added = True

    def release(self):
        sim_filter_service = services.sim_filter_service()
        if sim_filter_service is not None:
            for sim_id in self._blacklist_sim_ids:
                services.sim_filter_service().remove_sim_id_from_global_blacklist(sim_id, self._reason)

class SimFilterRequestState(enum.Int, export=False):
    SETUP = ...
    RAN_QUERY = ...
    SPAWNING_SIMS = ...
    FILLED_RESULTS = ...
    COMPLETE = ...

class _BaseSimFilterRequest:

    def __init__(self, callback=None, callback_event_data=None, blacklist_sim_ids=None, gsi_logging_data=None, sim_gsi_logging_data=None):
        self._state = SimFilterRequestState.SETUP
        self._callback = callback
        self._callback_event_data = callback_event_data
        self._blacklist_sim_ids = set(blacklist_sim_ids) if blacklist_sim_ids is not None else set()
        self._gsi_logging_data = gsi_logging_data
        self._sim_gsi_logging_data = sim_gsi_logging_data

    @property
    def is_complete(self):
        return self._state == SimFilterRequestState.COMPLETE

    def run(self):
        raise NotImplementedError

    def run_without_yielding(self):
        raise NotImplementedError

    def gsi_start_logging(self, request_type, filter_type, yielding, gsi_source_fn):
        if gsi_handlers.sim_filter_service_handlers.archiver.enabled:
            self._gsi_logging_data = gsi_handlers.sim_filter_service_handlers.SimFilterServiceGSILoggingData(request_type, str(filter_type), yielding, gsi_source_fn)
        if sim_filter_handlers.archiver.enabled:
            self._sim_gsi_logging_data = sim_filter_handlers.SimFilterGSILoggingData(request_type, str(filter_type), gsi_source_fn)

    def gsi_add_rejected_sim_info(self, sim_info, reason, filter_term=None):
        if self._gsi_logging_data is not None:
            self._gsi_logging_data.add_rejected_sim_info(sim_info, reason, filter_term)

    def gsi_archive_logging(self, filter_results):
        if self._gsi_logging_data is not None:
            gsi_handlers.sim_filter_service_handlers.archive_filter_request(filter_results, self._gsi_logging_data)
            self._gsi_logging_data = None

class _SimFilterRequest(_BaseSimFilterRequest):

    def __init__(self, sim_filter=None, requesting_sim_info=None, sim_constraints=None, household_id=None, start_time=None, end_time=None, club=None, tag=FilterTermTag.NO_TAG, optional=True, gsi_source_fn=None, additional_filter_terms=(), **kwargs):
        super().__init__(**kwargs)
        if sim_filter is None:
            sim_filter = filters.tunable.TunableSimFilter.BLANK_FILTER
        self._sim_filter = sim_filter
        self._additional_filter_terms = additional_filter_terms
        self._requesting_sim_info = requesting_sim_info
        self._sim_constraints = sim_constraints
        if household_id is not None:
            self._household_id = household_id
        elif requesting_sim_info:
            self._household_id = requesting_sim_info.household_id
        else:
            self._household_id = 0
        if start_time is not None:
            self._start_time = start_time.time_since_beginning_of_week()
        else:
            self._start_time = None
        if end_time is not None:
            self._end_time = end_time.time_since_beginning_of_week()
        else:
            self._end_time = None
        self._club = club
        self.tag = tag
        self.optional = optional
        self._gsi_source_fn = gsi_source_fn

    def run(self):
        if self._state == SimFilterRequestState.SETUP:
            logger.assert_raise(self._sim_filter is not None, '[rez] Sim Filter is None in _SimFilterRequest.')
            self.gsi_start_logging('_SimFilterRequest', self._sim_filter, False, self._gsi_source_fn)
            results = self._run_filter_query()
            if self._callback is not None:
                self._callback(results, self._callback_event_data)
            self._state = SimFilterRequestState.COMPLETE
            if self._gsi_logging_data is not None:
                self._gsi_logging_data.add_metadata(None, None, self._club, self._blacklist_sim_ids, self.optional)
            self.gsi_archive_logging(results)

    def run_without_yielding(self):
        self.gsi_start_logging('_SimFilterRequest ', self._sim_filter, True, self._gsi_source_fn)
        results = self._run_filter_query()
        if self._gsi_logging_data is not None:
            self._gsi_logging_data.add_metadata(None, None, self._club, self._blacklist_sim_ids, self.optional)
        self.gsi_archive_logging(results)
        return results

    def _get_constrained_sims(self):
        return self._sim_constraints

    def _run_filter_query(self):
        constrained_sim_ids = self._get_constrained_sims()
        results = self._find_sims_matching_filter(constrained_sim_ids=constrained_sim_ids, start_time=self._start_time, end_time=self._end_time, household_id=self._household_id, requesting_sim_info=self._requesting_sim_info, club=self._club, tag=self.tag)
        global_blacklist = services.sim_filter_service().get_global_blacklist()
        for result in tuple(results):
            if not result.sim_info.id in self._blacklist_sim_ids:
                if result.sim_info.id in global_blacklist:
                    results.remove(result)
                    if self._sim_gsi_logging_data is not None:
                        self.gsi_add_rejected_sim_info(result.sim_info, 'Global Blacklisted' if result.sim_info.id in global_blacklist else 'Filter Request Blacklisted')
                        sim_filter_handlers.archive_filter_request(result.sim_info, self._sim_gsi_logging_data, rejected=True, reason='Global Blacklisted' if result.sim_info.id in global_blacklist else 'Filter Request Blacklisted')
            results.remove(result)
            if self._sim_gsi_logging_data is not None:
                self.gsi_add_rejected_sim_info(result.sim_info, 'Global Blacklisted' if result.sim_info.id in global_blacklist else 'Filter Request Blacklisted')
                sim_filter_handlers.archive_filter_request(result.sim_info, self._sim_gsi_logging_data, rejected=True, reason='Global Blacklisted' if result.sim_info.id in global_blacklist else 'Filter Request Blacklisted')
        return results

    def _calculate_sim_filter_score(self, sim_info, filter_terms, start_time=None, end_time=None, tag=FilterTermTag.NO_TAG, **kwargs):
        total_result = FilterResult(sim_info=sim_info, tag=tag)
        start_time_ticks = start_time.absolute_ticks() if start_time is not None else None
        end_time_ticks = end_time.absolute_ticks() if end_time is not None else None
        for filter_term in filter_terms:
            result = filter_term.calculate_score(sim_info, start_time_ticks=start_time_ticks, end_time_ticks=end_time_ticks, **kwargs)
            result.score = max(result.score, filter_term.minimum_filter_score)
            if self._sim_gsi_logging_data is not None:
                self._sim_gsi_logging_data.add_filter(str(filter_term), result.score)
            total_result.combine_with_other_filter_result(result)
            if total_result.score == 0:
                self.gsi_add_rejected_sim_info(sim_info, '0 score', filter_term)
                if self._sim_gsi_logging_data is not None:
                    sim_filter_handlers.archive_filter_request(result.sim_info, self._sim_gsi_logging_data, rejected=True, reason='0 Score')
                break
        return total_result

    def _find_sims_matching_filter(self, constrained_sim_ids=None, **kwargs):
        filter_terms = self._sim_filter.get_filter_terms()
        if self._additional_filter_terms:
            filter_terms += self._additional_filter_terms
        sim_info_manager = services.sim_info_manager()
        results = []
        sim_ids = constrained_sim_ids if constrained_sim_ids is not None else sim_info_manager.keys()
        for sim_id in sim_ids:
            sim_info = sim_info_manager.get(sim_id)
            if sim_info is None:
                pass
            else:
                result = self._calculate_sim_filter_score(sim_info, filter_terms, **kwargs)
                if result.score > 0:
                    results.append(result)
        if self._sim_filter.use_weighted_random and len(results) > filters.tunable.TunableSimFilter.TOP_NUMBER_OF_SIMS_TO_LOOK_AT:
            shuffle(results)
        return results

class _MatchingFilterRequest(_SimFilterRequest):

    def __init__(self, number_of_sims_to_find=1, continue_if_constraints_fail=False, zone_id=None, allow_instanced_sims=False, optional=True, gsi_source_fn=None, **kwargs):
        super().__init__(**kwargs)
        self._continue_if_constraints_fail = continue_if_constraints_fail
        self._number_of_sims_to_find = number_of_sims_to_find
        self._filter_results = []
        self._zone_id = zone_id
        self._allow_instanced_sims = allow_instanced_sims
        self.optional = optional
        self._gsi_source_fn = gsi_source_fn

    def _select_sims_from_results(self, results, sims_to_spawn):
        self._filter_results = []
        self._filter_results_info = []
        global_blacklist = services.sim_filter_service().get_global_blacklist()
        for result in tuple(results):
            if not result.sim_info.id in self._blacklist_sim_ids:
                if result.sim_info.id in global_blacklist:
                    results.remove(result)
            results.remove(result)
        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
        if self._sim_filter.use_weighted_random:
            index = filters.tunable.TunableSimFilter.TOP_NUMBER_OF_SIMS_TO_LOOK_AT
            randomization_group = [(result.score, result) for result in sorted_results[:index]]
            while index < len(sorted_results) and len(self._filter_results) < sims_to_spawn:
                random_choice = random.pop_weighted(randomization_group)
                if index < len(sorted_results):
                    randomization_group.append((sorted_results[index].score, sorted_results[index]))
                    index += 1
                logger.info('Sim ID matching request {0}', random_choice)
                self._filter_results.append(random_choice)
                self._filter_results_info.append(random_choice.sim_info)
                index += 1
            if randomization_group:
                while True:
                    while randomization_group and len(self._filter_results) < self._number_of_sims_to_find:
                        random_choice = random.pop_weighted(randomization_group)
                        logger.info('Sim ID matching request {0}', random_choice)
                        self._filter_results.append(random_choice)
                        self._filter_results_info.append(random_choice.sim_info)
        else:
            for result in sorted_results:
                if len(self._filter_results) == sims_to_spawn:
                    break
                logger.info('Sim ID matching request {0}', result.sim_info)
                self._filter_results.append(result)
                self._filter_results_info.append(result.sim_info)
        if self._sim_gsi_logging_data is not None:
            for result in self._filter_results:
                sim_filter_handlers.archive_filter_request(result.sim_info, self._sim_gsi_logging_data, rejected=False, reason='Score > 0 and chosen for spawning')
        return self._filter_results

    def _run_filter_query(self):
        results = None
        constrained_sim_ids = self._get_constrained_sims()
        if constrained_sim_ids is not None:
            results = self._find_sims_matching_filter(constrained_sim_ids=constrained_sim_ids, start_time=self._start_time, end_time=self._end_time, household_id=self._household_id, requesting_sim_info=self._requesting_sim_info, club=self._club, tag=self.tag)
            if results or not self._continue_if_constraints_fail:
                return self._filter_results
            self._select_sims_from_results(results, self._number_of_sims_to_find)
            if len(self._filter_results) == self._number_of_sims_to_find or not self._continue_if_constraints_fail:
                return self._filter_results
        results = self._find_sims_matching_filter(start_time=self._start_time, end_time=self._end_time, household_id=self._household_id, requesting_sim_info=self._requesting_sim_info, club=self._club, tag=self.tag)
        if results:
            self._filter_results.extend(self._select_sims_from_results(results, self._number_of_sims_to_find - len(self._filter_results)))

    def _create_sim_info(self):
        blacklist_sim_ids = tuple(self._blacklist_sim_ids)
        blacklist_sim_ids += tuple(result.sim_info.sim_id for result in self._filter_results)
        if not self._sim_filter.repurpose_game_breaker:
            blacklist_sim_ids += tuple(sim.sim_info.sim_id for sim in services.sim_info_manager().instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS))
        create_result = self._sim_filter.create_sim_info(zone_id=self._zone_id, household_id=self._household_id, requesting_sim_info=self._requesting_sim_info, blacklist_sim_ids=blacklist_sim_ids, start_time=self._start_time, end_time=self._end_time, additional_filter_terms=self._additional_filter_terms)
        if create_result:
            fake_filter_result = FilterResult(sim_info=create_result.sim_info, tag=self.tag)
            self._filter_results.append(fake_filter_result)
            logger.info('Created Sim ID to match request {0}', create_result.sim_info.id)
            if self._gsi_logging_data is not None:
                self._gsi_logging_data.add_created_household(create_result.sim_info.household, was_successful=True)
            if self._sim_gsi_logging_data is not None:
                sim_filter_handlers.archive_filter_request(create_result.sim_info, self._sim_gsi_logging_data, rejected=False, reason='Created to match the filter')
            return True
        else:
            if self._gsi_logging_data is not None and create_result.sim_info is not None:
                self._gsi_logging_data.add_created_household(create_result.sim_info.household, was_successful=False)
            return False

    def _create_sim_infos(self):
        while len(self._filter_results) < self._number_of_sims_to_find:
            if not self._create_sim_info():
                break

    def run(self):
        if self._state == SimFilterRequestState.SETUP:
            self.gsi_start_logging('_MatchingFilterRequest', self._sim_filter, False, self._gsi_source_fn)
            self._run_filter_query()
            if len(self._filter_results) == self._number_of_sims_to_find or not (self._sim_constraints and self._continue_if_constraints_fail):
                self._state = SimFilterRequestState.FILLED_RESULTS
            else:
                self._state = SimFilterRequestState.RAN_QUERY
        if self._state == SimFilterRequestState.RAN_QUERY:
            self._state = SimFilterRequestState.SPAWNING_SIMS
            return
        if self._state == SimFilterRequestState.SPAWNING_SIMS:
            result = self._create_sim_info()
            if result and len(self._filter_results) == self._number_of_sims_to_find:
                self._state = SimFilterRequestState.FILLED_RESULTS
        if self._state == SimFilterRequestState.FILLED_RESULTS:
            self._callback(self._filter_results, self._callback_event_data)
            self._state = SimFilterRequestState.COMPLETE
            if self._gsi_logging_data is not None:
                self._gsi_logging_data.add_metadata(self._number_of_sims_to_find, self._allow_instanced_sims, self._club, self._blacklist_sim_ids, self.optional)
            self.gsi_archive_logging(self._filter_results)

    def run_without_yielding(self):
        self.gsi_start_logging('_MatchingFilterRequest', self._sim_filter, True, self._gsi_source_fn)
        self._run_filter_query()
        if self._sim_constraints and self._continue_if_constraints_fail:
            self._create_sim_infos()
        if self._gsi_logging_data is not None:
            self._gsi_logging_data.add_metadata(self._number_of_sims_to_find, self._allow_instanced_sims, self._club, self._blacklist_sim_ids, self.optional)
        self.gsi_archive_logging(self._filter_results)
        return self._filter_results

class _AggregateFilterRequest(_BaseSimFilterRequest):

    def __init__(self, aggregate_filter=None, filter_sims_with_matching_filter_request=True, gsi_source_fn=None, additional_filter_terms=(), **kwargs):
        super().__init__(**kwargs)
        self._aggregate_filter = aggregate_filter
        self._additional_filter_terms = additional_filter_terms
        self._filter_sims_with_matching_filter_request = filter_sims_with_matching_filter_request
        logger.assert_raise(aggregate_filter is not None, 'Filter is None in _AggregateFilterRequest.')
        self._leader_filter_request = None
        self._non_leader_filter_requests = []
        self._leader_sim_info = None
        self._filter_results = []
        self._gsi_source_fn = gsi_source_fn

    def run(self):
        if self._state == SimFilterRequestState.SETUP:
            self.gsi_start_logging('_AggregateFilterRequest', self._aggregate_filter, False, self._gsi_source_fn)
            self._create_leader()
            if self._leader_sim_info is None:
                self._state = SimFilterRequestState.COMPLETE
                self._callback([], self._callback_event_data)
                if self._gsi_logging_data is not None:
                    self._gsi_logging_data.add_metadata(None, None, None, self._blacklist_sim_ids, None)
                self.gsi_archive_logging(self._filter_results)
                return
            self._create_non_leader_filter_requests()
            self._state = SimFilterRequestState.SPAWNING_SIMS
            return
        if self._state == SimFilterRequestState.SPAWNING_SIMS:
            if self._non_leader_filter_requests:
                filter_to_run = self._non_leader_filter_requests.pop()
                result = self._run_sim_filter(filter_to_run)
                if result or filter_to_run.optional:
                    return
                self._filter_results.clear()
                self._state = SimFilterRequestState.FILLED_RESULTS
                return
            self._state = SimFilterRequestState.FILLED_RESULTS
        if self._state == SimFilterRequestState.FILLED_RESULTS:
            self._callback(self._filter_results, self._callback_event_data)
            self._state = SimFilterRequestState.COMPLETE
            if self._gsi_logging_data is not None:
                self._gsi_logging_data.add_metadata(None, None, None, self._blacklist_sim_ids, None)
            self.gsi_archive_logging(self._filter_results)

    def run_without_yielding(self):
        self.gsi_start_logging('_AggregateFilterRequest', self._aggregate_filter, True, self._gsi_source_fn)
        self._create_leader()
        if self._leader_sim_info is None:
            return []
        self._create_non_leader_filter_requests()
        for filter_to_run in self._non_leader_filter_requests:
            result = self._run_sim_filter(filter_to_run)
            if not result:
                if filter_to_run.optional:
                    pass
                else:
                    self._filter_results.clear()
                    return self._filter_results
        if self._gsi_logging_data is not None:
            self._gsi_logging_data.add_metadata(None, None, None, self._blacklist_sim_ids, None)
        self.gsi_archive_logging(self._filter_results)
        return self._filter_results

    def _create_leader(self):
        self._create_leader_filter_request()
        filter_results = self._leader_filter_request.run_without_yielding()
        if not filter_results:
            return
        self._leader_sim_info = filter_results[0].sim_info
        self._filter_results.append(filter_results[0])
        self._blacklist_sim_ids.add(self._leader_sim_info.sim_id)

    def _create_leader_filter_request(self):
        if self._gsi_logging_data is not None:
            request_type = '_AggregateFilterRequest:_MatchingFilterRequest' if self._filter_sims_with_matching_filter_request else '_AggregateFilterRequest:_SimFilterRequest'
            sub_gsi_logging_data = gsi_handlers.sim_filter_service_handlers.SimFilterServiceGSILoggingData(request_type, 'LeaderFilter:{}'.format(self._aggregate_filter.leader_filter), self._gsi_logging_data.yielding, self._gsi_logging_data.gsi_source_fn)
        else:
            sub_gsi_logging_data = None
        if self._filter_sims_with_matching_filter_request:
            self._leader_filter_request = _MatchingFilterRequest(sim_filter=self._aggregate_filter.leader_filter.filter, blacklist_sim_ids=self._blacklist_sim_ids, gsi_logging_data=sub_gsi_logging_data, tag=self._aggregate_filter.leader_filter.tag, additional_filter_terms=self._additional_filter_terms)
        else:
            self._leader_filter_request = _SimFilterRequest(sim_filter=self._aggregate_filter.leader_filter.filter, blacklist_sim_ids=self._blacklist_sim_ids, gsi_logging_data=sub_gsi_logging_data, tag=self._aggregate_filter.leader_filter.tag, additional_filter_terms=self._additional_filter_terms)

    def _create_non_leader_filter_requests(self):
        if self._filter_sims_with_matching_filter_request:
            for sim_filter in self._aggregate_filter.filters:
                sub_gsi_logging_data = None
                if self._gsi_logging_data is not None:
                    sub_gsi_logging_data = gsi_handlers.sim_filter_service_handlers.SimFilterServiceGSILoggingData('_AggregateFilterRequest:_MatchingFilterRequest', 'NonLeaderFilter:{}'.format(sim_filter.filter), self._gsi_logging_data.yielding, self._gsi_logging_data.gsi_source_fn)
                self._non_leader_filter_requests.append(_MatchingFilterRequest(sim_filter=sim_filter.filter, blacklist_sim_ids=self._blacklist_sim_ids, requesting_sim_info=self._leader_sim_info, gsi_logging_data=sub_gsi_logging_data, tag=sim_filter.tag, optional=sim_filter.optional))
        else:
            for sim_filter in self._aggregate_filter.filters:
                sub_gsi_logging_data = None
                if self._gsi_logging_data is not None:
                    sub_gsi_logging_data = gsi_handlers.sim_filter_service_handlers.SimFilterServiceGSILoggingData('_AggregateFilterRequest:_SimFilterRequest', 'NonLeaderFilter:{}'.format(sim_filter.filter), self._gsi_logging_data.yielding)
                self._non_leader_filter_requests.append(_SimFilterRequest(sim_filter=sim_filter.filter, blacklist_sim_ids=self._blacklist_sim_ids, requesting_sim_info=self._leader_sim_info, gsi_logging_data=sub_gsi_logging_data, tag=sim_filter.tag, optional=sim_filter.optional))

    def _run_sim_filter(self, filter_to_run):
        filter_results = filter_to_run.run_without_yielding()
        if filter_results:
            for result in filter_results:
                self._filter_results.append(result)
                self._blacklist_sim_ids.add(result.sim_info.sim_id)
        return bool(filter_results)

class SimFilterService(Service):

    def __init__(self):
        self._filter_requests = []
        self._global_blacklist = collections.defaultdict(list)

    def update(self):
        try:
            if self._filter_requests:
                current_request = self._filter_requests[0]
                current_request.run()
                if current_request.is_complete:
                    del self._filter_requests[0]
        except Exception:
            logger.exception('Exception while updating the sim filter service..')

    def add_sim_id_to_global_blacklist(self, sim_id, reason):
        self._global_blacklist[sim_id].append(reason)

    def remove_sim_id_from_global_blacklist(self, sim_id, reason):
        reasons = self._global_blacklist.get(sim_id)
        if reasons is None:
            logger.error('Trying to remove sim id {} to global blacklist without adding it first.', sim_id, owner='jjacobson')
            return
        if reason not in reasons:
            logger.error('Trying to remove reason {} from global blacklist with sim id {} without adding it first.', reason, sim_id, owner='jjacobson')
            return
        self._global_blacklist[sim_id].remove(reason)
        if not self._global_blacklist[sim_id]:
            del self._global_blacklist[sim_id]

    def get_global_blacklist(self):
        return set(self._global_blacklist.keys())

    def submit_matching_filter(self, number_of_sims_to_find=1, sim_filter=None, callback=None, callback_event_data=None, sim_constraints=None, requesting_sim_info=None, blacklist_sim_ids=EMPTY_SET, continue_if_constraints_fail=False, allow_yielding=True, start_time=None, end_time=None, household_id=None, zone_id=None, club=None, allow_instanced_sims=False, additional_filter_terms=(), gsi_source_fn=None):
        request = None
        if sim_filter is not None and sim_filter.is_aggregate_filter():
            request = _AggregateFilterRequest(aggregate_filter=sim_filter, callback=callback, callback_event_data=callback_event_data, blacklist_sim_ids=blacklist_sim_ids, filter_sims_with_matching_filter_request=True, additional_filter_terms=additional_filter_terms, gsi_source_fn=gsi_source_fn)
        else:
            request = _MatchingFilterRequest(number_of_sims_to_find=number_of_sims_to_find, continue_if_constraints_fail=continue_if_constraints_fail, sim_filter=sim_filter, callback=callback, callback_event_data=callback_event_data, requesting_sim_info=requesting_sim_info, sim_constraints=sim_constraints, blacklist_sim_ids=blacklist_sim_ids, start_time=start_time, end_time=end_time, household_id=household_id, zone_id=zone_id, club=club, allow_instanced_sims=allow_instanced_sims, additional_filter_terms=additional_filter_terms, gsi_source_fn=gsi_source_fn)
        if allow_yielding:
            self._add_filter_request(request)
        else:
            return request.run_without_yielding()

    def submit_filter(self, sim_filter, callback, callback_event_data=None, sim_constraints=None, requesting_sim_info=None, blacklist_sim_ids=EMPTY_SET, allow_yielding=True, start_time=None, end_time=None, household_id=None, club=None, additional_filter_terms=(), gsi_source_fn=None):
        request = None
        if sim_filter is not None and sim_filter.is_aggregate_filter():
            request = _AggregateFilterRequest(aggregate_filter=sim_filter, callback=callback, callback_event_data=callback_event_data, blacklist_sim_ids=blacklist_sim_ids, filter_sims_with_matching_filter_request=False, additional_filter_terms=additional_filter_terms, gsi_source_fn=gsi_source_fn)
        else:
            request = _SimFilterRequest(sim_filter=sim_filter, callback=callback, callback_event_data=callback_event_data, requesting_sim_info=requesting_sim_info, sim_constraints=sim_constraints, blacklist_sim_ids=blacklist_sim_ids, start_time=start_time, end_time=end_time, household_id=household_id, club=club, additional_filter_terms=additional_filter_terms, gsi_source_fn=gsi_source_fn)
        if allow_yielding:
            self._add_filter_request(request)
        else:
            return request.run_without_yielding()

    def _add_filter_request(self, filter_request):
        self._filter_requests.append(filter_request)

    def does_sim_match_filter(self, sim_id, sim_filter=None, requesting_sim_info=None, start_time=None, end_time=None, household_id=None, additional_filter_terms=(), gsi_source_fn=None):
        result = self.submit_filter(sim_filter, None, allow_yielding=False, sim_constraints=[sim_id], requesting_sim_info=requesting_sim_info, start_time=start_time, end_time=end_time, household_id=household_id, additional_filter_terms=additional_filter_terms, gsi_source_fn=gsi_source_fn)
        if result:
            return True
        return False
