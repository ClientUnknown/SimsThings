import randomfrom situations.situation_job import JobChurnOperationimport alarmsimport clockimport date_and_timeimport servicesimport sims4.loglogger = sims4.log.Logger('Situations')
class SituationJobData:

    def __init__(self, job_type, default_role_state_type, situation):
        self._job_type = job_type
        self._default_role_state_type = default_role_state_type
        self._situation = situation
        self._emotional_loot_actions = None
        self._churn_alarm_handle = None
        self._shift_change_alarm_handle = None
        self._sim_id_for_match_filter_request = None
        churn_interval = clock.interval_in_sim_minutes(10)
        if self._get_churn():
            self._churn_alarm_handle = alarms.add_alarm(self, churn_interval, self._churn, repeating=True, use_sleep_time=False)
        elif self._get_shifts():
            self._churn_alarm_handle = alarms.add_alarm(self, churn_interval, self._shift_churn, repeating=True, use_sleep_time=False)
            self._shift_change_alarm_handle = alarms.add_alarm(self, self._get_next_shift_change_time_span(), self._shift_change)

    def destroy(self):
        self._situation = None
        if self._churn_alarm_handle is not None:
            alarms.cancel_alarm(self._churn_alarm_handle)
            self._churn_alarm_handle = None
        if self._shift_change_alarm_handle is not None:
            alarms.cancel_alarm(self._shift_change_alarm_handle)
            self._shift_change_alarm_handle = None

    def set_default_role_state_type(self, role_state_type):
        if role_state_type is None:
            raise AssertionError('Attempting to set a None default role state for job type: {}'.format(self._job_type))
        self._default_role_state_type = role_state_type

    @property
    def default_role_state_type(self):
        return self._default_role_state_type

    def get_sim_filter_gsi_name(self):
        sim_info = services.sim_info_manager().get(self._sim_id_for_match_filter_request)
        return 'Request to check if {} matches filter from situation {}'.format(sim_info or 'Destroyed Sim', self._situation)

    def test_add_sim(self, sim, requesting_sim_info):
        self._sim_id_for_match_filter_request = sim.id
        can_add = self._job_type.can_sim_be_given_job(sim.id, requesting_sim_info, gsi_source_fn=self.get_sim_filter_gsi_name)
        return can_add

    def get_job_type(self):
        return self._job_type

    @property
    def emotional_loot_actions(self):
        return self._emotional_loot_actions

    @emotional_loot_actions.setter
    def emotional_loot_actions(self, loot_actions_type):
        self._emotional_loot_actions = loot_actions_type

    def _get_churn(self):
        if self._job_type.churn is None or not self._job_type.churn.auto_populate_by_time_of_day:
            return
        return self._job_type.churn

    def _get_shifts(self):
        if self._job_type.sim_shifts is None or not self._job_type.sim_shifts.shift_times_and_staffing:
            return
        return self._job_type.sim_shifts

    def _get_num_sims_coming(self):
        num_coming = 0
        for request in self._situation.manager.bouncer.pending_situation_requests_gen(self._situation):
            if request._job_type is self._job_type:
                num_coming += 1
        return num_coming

    def _get_npc_here_longest(self):
        longest_sim = None
        most_time_on_lot = date_and_time.TimeSpan.ZERO
        for sim_in_job in self._situation.get_sims_in_job_for_churn(self._job_type):
            if sim_in_job.is_selectable:
                pass
            else:
                time_span_on_lot = self._situation.manager.get_time_span_sim_has_been_on_lot(sim_in_job)
                if time_span_on_lot > most_time_on_lot:
                    most_time_on_lot = time_span_on_lot
                    longest_sim = sim_in_job
        return longest_sim

    def _choose_random_npc_over_min_duration(self):
        min_time_span_on_lot = date_and_time.create_time_span(minutes=self._job_type.churn.min_duration)
        candidates = []
        for sim_in_job in self._situation.get_sims_in_job_for_churn(self._job_type):
            if sim_in_job.is_selectable:
                pass
            else:
                time_span_on_lot = self._situation.manager.get_time_span_sim_has_been_on_lot(sim_in_job)
                if time_span_on_lot < min_time_span_on_lot:
                    pass
                else:
                    candidates.append(sim_in_job)
        selected_sim = None
        if candidates:
            selected_sim = random.choice(candidates)
        return selected_sim

    def _churn(self, alarm_handle=None):
        churn = self._get_churn()
        if churn is None:
            return
        job_type = self._job_type
        logger.debug('churning job: {} for situation: {}', job_type, self._situation)
        desired_interval = churn.get_auto_populate_interval(services.time_service().sim_now)
        num_here = self._situation.get_num_sims_in_job_for_churn(job_type)
        num_coming = self._get_num_sims_coming()
        num_total = num_here + num_coming
        over_max = False
        op = JobChurnOperation.DO_NOTHING
        if num_total < desired_interval.min:
            op = JobChurnOperation.ADD_SIM
        elif num_here > desired_interval.max:
            op = JobChurnOperation.REMOVE_SIM
            over_max = True
        elif sims4.random.random_chance(churn.chance_to_add_or_remove_sim):
            options = []
            if num_total < desired_interval.max:
                options.append(JobChurnOperation.ADD_SIM)
            if num_here > desired_interval.min:
                options.append(JobChurnOperation.REMOVE_SIM)
            if options:
                op = random.choice(options)
        if op == JobChurnOperation.ADD_SIM:
            logger.debug('Churn: Adding sim in job: {} to situation: {}', job_type, self._situation)
            self._situation._make_late_auto_fill_request(job_type)
        elif op == JobChurnOperation.REMOVE_SIM:
            sim_to_remove = self._choose_random_npc_over_min_duration()
            if over_max:
                sim_to_remove = self._get_npc_here_longest()
            if sim_to_remove is None and sim_to_remove:
                logger.debug('Churn: Removing sim:{} from job: {} in situation: {}', sim_to_remove, job_type, self._situation)
                self._situation.manager.add_sim_to_auto_fill_blacklist(sim_to_remove.id, self._job_type)
                self._situation.manager.make_sim_leave(sim_to_remove)

    def _shift_churn(self, alarm_handle=None):
        sim_shifts = self._get_shifts()
        if not sim_shifts:
            return
        job_type = self._job_type
        logger.debug('Shift churning job: {} for situation: {}', job_type, self._situation)
        num_desired = sim_shifts.get_shift_staffing()
        num_here = self._situation.get_num_sims_in_job_for_churn(job_type)
        num_coming = self._get_num_sims_coming()
        num_total = num_here + num_coming
        op = JobChurnOperation.DO_NOTHING
        if num_total < num_desired:
            op = JobChurnOperation.ADD_SIM
        elif num_here > num_desired:
            op = JobChurnOperation.REMOVE_SIM
        if op == JobChurnOperation.ADD_SIM:
            logger.debug('Churn: Adding sim in job: {} to situation: {}', job_type, self._situation)
            self._situation._make_late_auto_fill_request(job_type)
        elif op == JobChurnOperation.REMOVE_SIM:
            sim_to_remove = self._get_npc_here_longest()
            if sim_to_remove is not None:
                logger.debug('Shift Churn: Removing sim:{} from job: {} in situation: {}', sim_to_remove, job_type, self._situation)
                self._situation.manager.add_sim_to_auto_fill_blacklist(sim_to_remove.id, self._job_type)
                self._situation.manager.make_sim_leave(sim_to_remove)

    def _shift_change(self, alarm_handle=None):
        sim_shifts = self._get_shifts()
        if not sim_shifts:
            return
        job_type = self._job_type
        num_to_add = sim_shifts.get_shift_staffing()
        num_to_add -= self._get_num_sims_coming()
        logger.debug('Shift Change: Adding {} sim(s) in job: {} to situation: {}', num_to_add, job_type, self._situation)
        for _ in range(num_to_add):
            self._situation._make_late_auto_fill_request(job_type)
        if alarm_handle is not None:
            self._shift_change_alarm_handle = alarms.add_alarm(self, self._get_next_shift_change_time_span(), self._shift_change)

    def _get_next_shift_change_time_span(self):
        sim_shifts = self._get_shifts()
        if not sim_shifts:
            return
        return sim_shifts.get_time_span_to_next_shift_time()

    def gsi_get_job_name(self):
        return self._job_type.__name__

    def gsi_has_churn(self):
        return self._get_churn() is not None

    def gsi_get_churn_min(self):
        if self._job_type.churn is None:
            return 0
        interval = self._job_type.churn.get_auto_populate_interval(services.time_service().sim_now)
        return interval.min

    def gsi_get_churn_max(self):
        if self._job_type.churn is None:
            return 0
        interval = self._job_type.churn.get_auto_populate_interval(services.time_service().sim_now)
        return interval.max

    def gsi_get_num_churn_sims_here(self):
        return self._situation.get_num_sims_in_job_for_churn(self._job_type)

    def gsi_get_num_churn_sims_coming(self):
        return self._get_num_sims_coming()

    def gsi_get_remaining_time_until_churn(self):
        if self._churn_alarm_handle is None:
            return date_and_time.TimeSpan.ZERO
        return self._churn_alarm_handle.get_remaining_time()

    def gsi_has_shifts(self):
        return self._get_shifts() is not None

    def gsi_get_shifts_staffing(self):
        shifts = self._get_shifts()
        if shifts is None:
            return 0
        return shifts.get_shift_staffing()

    def gsi_get_remaining_time_until_shift_change(self):
        if self._shift_change_alarm_handle is None:
            return date_and_time.TimeSpan.ZERO
        return self._shift_change_alarm_handle.get_remaining_time()
