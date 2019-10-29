from _collections import defaultdictfrom collections import Counterimport timefrom contextlib import contextmanagerfrom sims4.utils import create_csvimport enumimport servicesimport sims4.logimport sims4.reloadlogger = sims4.log.Logger('Autonomy')with sims4.reload.protected(globals()):
    sim_id_to_sub_autonomy_ping = None
    info_start_time = None
    g_autonomy_profile_data = None
class AutonomyPingRequestRecord:

    def __init__(self, sim_id, first_name, last_name, autonomy_type, time_stamp, is_npc):
        self._sim_id = sim_id
        self._sim_first_name = first_name
        self._sim_last_name = last_name
        self.time_stamp = time_stamp
        self.end_time = None
        self.total_time_slicing = 0
        self.autonomy_type = autonomy_type
        self.total_distance_estimation = 0
        self.mixers_considered = 0
        self.is_npc = is_npc
        self.start_time = time.time()

    def add_record_to_profiling_data(self):
        self.end_time = time.time()
        g_autonomy_profile_data.add_request_record(self)

    def write_record(self, file):
        total_time = self.end_time - self.start_time
        working_time = total_time - self.total_time_slicing
        percent_distance_estimation = 0
        if working_time != 0:
            percent_distance_estimation = self.total_distance_estimation/working_time
        file.write('{},{},{},{},{},{},{:0.02f},{:0.02f},{:0.02f},{:0.02f},{}\n'.format(self._sim_id, self._sim_first_name, self._sim_last_name, self.autonomy_type, self.is_npc, self.time_stamp, total_time, working_time, self.total_time_slicing, self.total_distance_estimation, percent_distance_estimation))

class AutonomyCumulativePingRecord:

    def __init__(self):
        self._count = [0, 0]
        self._total_time = [0.0, 0.0]
        self._total_time_max = [0.0, 0.0]
        self._working_time = [0.0, 0.0]
        self._working_time_max = [0.0, 0.0]
        self._total_time_slicing = [0.0, 0.0]
        self._total_time_slicing_max = [0.0, 0.0]
        self._total_distance_estimation = [0.0, 0.0]
        self._total_distance_estimation_max = [0.0, 0.0]
        self._percent_distance_estimation = [0.0, 0.0]
        self._percent_distance_estimation_max = [0.0, 0.0]

    def add_request_record(self, request_record):
        total_time = request_record.end_time - request_record.start_time
        if total_time < 0:
            logger.error('Attempting to add a record with negative total time to cumulative record.')
        working_time = total_time - request_record.total_time_slicing
        if working_time < 0:
            logger.error('Attempting to add a record with negative working time to cumulative record.')
        percent_distance_estimation = 0
        if working_time != 0:
            percent_distance_estimation = request_record.total_distance_estimation/working_time
        index = 1
        if request_record.is_npc:
            index = 0
        self._count[index] += 1
        self._total_time[index] += total_time
        self._total_time_max[index] = max(total_time, self._total_time_max[index])
        self._working_time[index] += working_time
        self._working_time_max[index] = max(working_time, self._working_time_max[index])
        self._total_time_slicing[index] += request_record.total_time_slicing
        self._total_time_slicing_max[index] = max(request_record.total_time_slicing, self._total_time_slicing_max[index])
        self._total_distance_estimation[index] += request_record.total_distance_estimation
        self._total_distance_estimation_max[index] = max(request_record.total_distance_estimation, self._total_distance_estimation_max[index])
        self._percent_distance_estimation[index] += percent_distance_estimation
        self._percent_distance_estimation_max[index] = max(percent_distance_estimation, self._percent_distance_estimation_max[index])

    def write_record(self, autonomy_type, file):
        total_count = self._count[0] + self._count[1]
        if total_count == 0:
            return
        file.write('\n{} (All),{:0.03f},{:0.03f},{:0.03f},{:0.03f},{:0.03f},{:0.03f},{:0.03f},{:0.03f},{:0.03f},{:0.03f},{:0.03f},{},{}'.format(autonomy_type, self._total_time[0] + self._total_time[1], (self._total_time[0] + self._total_time[1])/total_count, max(self._total_time_max[0], self._total_time_max[1]), self._working_time[0] + self._working_time[1], (self._working_time[0] + self._working_time[1])/total_count, max(self._working_time_max[0], self._working_time_max[1]), self._total_time_slicing[0] + self._total_time_slicing[1], (self._total_time_slicing[0] + self._total_time_slicing[1])/total_count, max(self._total_time_slicing_max[0], self._total_time_slicing_max[1]), (self._total_distance_estimation[0] + self._total_distance_estimation[1])/total_count, max(self._total_distance_estimation_max[0], self._total_distance_estimation_max[1]), (self._percent_distance_estimation[0] + self._percent_distance_estimation[1])/total_count, max(self._percent_distance_estimation_max[0], self._percent_distance_estimation_max[1])))
        for index in range(0, 2):
            count = self._count[index]
            if count == 0:
                pass
            else:
                file.write('\n  {} {},{:0.03f},{:0.03f},{:0.03f},{:0.03f},{:0.03f},{:0.03f},{:0.03f},{:0.03f},{:0.03f},{:0.03f},{:0.03f},{},{}'.format(autonomy_type, '(NPC)' if index == 0 else '(PC)', self._total_time[index], self._total_time[index]/count, self._total_time_max[index], self._working_time[index], self._working_time[index]/count, self._working_time_max[index], self._total_time_slicing[index], self._total_time_slicing[index]/count, self._total_time_slicing_max[index], self._total_distance_estimation[index]/count, self._total_distance_estimation_max[index], self._percent_distance_estimation[index]/count, self._percent_distance_estimation_max[index]))

class AutonomyProfilingData:
    MAX_RECORDS = 2000

    def __init__(self):
        self.start_time = services.time_service().sim_now
        self.autonomy_requests = []
        self.sim_id_to_autonomy_types = defaultdict(Counter)
        self.cumulative_records = defaultdict(AutonomyCumulativePingRecord)

    def add_request_record(self, request_record):
        if len(self.autonomy_requests) < self.MAX_RECORDS:
            self.autonomy_requests.append(request_record)
            self.sim_id_to_autonomy_types[request_record._sim_id][request_record.autonomy_type] += 1
        self.cumulative_records[request_record.autonomy_type].add_request_record(request_record)

    def write_profiling_data_to_file(self, file):
        end_time = services.time_service().sim_now
        file.write('TotalTime,{}\n\n'.format(end_time - self.start_time))
        file.write('GameTime(Start),{}\n'.format(self.start_time))
        file.write('GameTime(End),{}\n'.format(end_time))
        file.write('\nAutonomyType,SumTaken (s),AvgTaken (s),MaxTaken (s),SumWorking (s),AvgWorking (s),MaxWorking (s),SumSlept (s),AvgSlept (s),MaxSlept (s),AvgCalculatingRouteTime (s),MaxCalculatingRouteTime (s),AvgPercentOfTimeCalculatingRouteTime (s),MaxPercentOfTimeCalculatingRouteTime (s)')
        autonomy_key_order = ['FullAutonomy', 'SubActionAutonomy', 'SocialAutonomy', 'ParameterizedAutonomy', 'CraftingRequest']
        cumulative_records_copy = self.cumulative_records.copy()
        for autonomy_key in autonomy_key_order:
            record = cumulative_records_copy.pop(autonomy_key, None)
            if record is not None:
                record.write_record(autonomy_key, file)
        autonomy_key_order = list(cumulative_records_copy.keys())
        autonomy_key_order.sort()
        for autonomy_key in autonomy_key_order:
            cumulative_records_copy[autonomy_key].write_record(autonomy_key, file)
        file.write('\n\nSimId, AutonomyType, Count\n')
        for (sim_id, counter) in self.sim_id_to_autonomy_types.items():
            for autonomy_type in sorted(counter.keys()):
                count = counter[autonomy_type]
                file.write('{},{},{}\n'.format(sim_id, autonomy_type, count))
        file.write('\nSimId,FirstName,LastName,AutonomyType,NPC,TimeStamp,TotalTimeTaken (s),TotalTimeWorking (s),TotalTimeSlept (s),TotalTimeCalculatingRouteTime (s),PercentOfTimeCalculatingRouteTime (s)\n')
        for request_record in self.autonomy_requests:
            request_record.write_record(file)
        if len(self.autonomy_requests) >= self.MAX_RECORDS:
            file.write('Max records kept.')

    def reset_profiling_data(self):
        self.start_time = services.time_service().sim_now
        self.autonomy_requests.clear()
        self.autonomy_requests = []
        self.sim_id_to_autonomy_types.clear()
        self.cumulative_records.clear()

def record_autonomy_profiling_data():
    global g_autonomy_profile_data
    if g_autonomy_profile_data:
        return
    g_autonomy_profile_data = AutonomyProfilingData()

class SubAutonomyPingData:

    def __init__(self):
        self.num_mixers_cached = []
        self.cache_hits = 0
        self.cache_use_fails = 0
        self.mixers_cleared = 0

def get_info_start_time():
    return info_start_time

def record_autonomy_ping_data(start_time):
    global info_start_time, sim_id_to_sub_autonomy_ping
    if info_start_time:
        return
    info_start_time = start_time
    sim_id_to_sub_autonomy_ping = dict()

def stop_sub_autonomy_ping_data():
    global info_start_time, sim_id_to_sub_autonomy_ping
    if not info_start_time:
        return
    info_start_time = None
    sim_id_to_sub_autonomy_ping.clear()
    sim_id_to_sub_autonomy_ping = None

def print_sub_autonomy_ping_data(current_time, output):
    if not sim_id_to_sub_autonomy_ping:
        output('No recordings have been made.')
        return
    output('Total Time Recording (SimTime): {}'.format(current_time - info_start_time))
    total_request = 0
    total_cached = 0
    total_hits = 0
    total_failures = 0
    total_unused = 0
    num_caches_under_max = 0
    for ping_data in sim_id_to_sub_autonomy_ping.values():
        total_request += len(ping_data.num_mixers_cached)
        total_failures += ping_data.cache_use_fails
        total_hits += ping_data.cache_hits
        total_unused += ping_data.mixers_cleared
        for (num_cached_mixers, max_to_cache) in ping_data.num_mixers_cached:
            total_cached += num_cached_mixers
            if num_cached_mixers < max_to_cache:
                num_caches_under_max += 1
    output('Total Requests: {}'.format(total_request))
    output('Total Mixers Cached: {}'.format(total_cached))
    output('Total Cached Mixers Not Used: {} ({:.2f}%)'.format(total_unused, total_unused/total_cached))
    output('Total Cache Hits: {} ({:.2f}%)'.format(total_hits, total_hits/total_cached))
    output('Total Cache Misses: {} ({:.2f}%)'.format(total_failures, total_failures/total_cached))
    output('Average Cached per request: {}'.format(total_cached/total_request))
    output('Caches Under Max Request: {}'.format(num_caches_under_max))

class AutonomyAffordanceTimes:

    class AutonomyAffordanceTimesType(enum.Int, export=False):
        TRANSITION_SEQUENCE = 0
        DISTANCE_ESTIMATE = 1
        COMPATIBILITY = 2

    _affordance_times = None

    def __init__(self):
        self._clear()

    def _clear(self):
        self._affordances = {}
        self._clear_temporary()

    def _clear_temporary(self):
        self._current_times = {entry: None for entry in self.AutonomyAffordanceTimesType}
        self._total_reduction_time = 0.0
        self._last_type = None
        self._last_type_start = None
        self._total_start = None
        self._type_stack = []

    def _start_profile(self):
        self._current_times = {entry: 0.0 for entry in self.AutonomyAffordanceTimesType}
        self._total_start = time.time()

    def _finish_profile(self, affordance_name):
        end_time = time.time()
        if self._total_start is None:
            return
        if affordance_name in self._affordances:
            (total_count, total_total, total_distance, total_transition, total_compat) = self._affordances[affordance_name]
        else:
            (total_count, total_total, total_distance, total_transition, total_compat) = (0, 0.0, 0.0, 0.0, 0.0)
        total_total += end_time - self._total_start - self._total_reduction_time
        total_distance += self._current_times[self.AutonomyAffordanceTimesType.DISTANCE_ESTIMATE]
        total_transition += self._current_times[self.AutonomyAffordanceTimesType.TRANSITION_SEQUENCE]
        total_compat += self._current_times[self.AutonomyAffordanceTimesType.COMPATIBILITY]
        self._affordances[affordance_name] = (total_count + 1, total_total, total_distance, total_transition, total_compat)
        self._clear_temporary()

    def _start_section_profile(self, section):
        if self._current_times[section] is not None:
            start_time = time.time()
            if self._last_type is not None:
                self._current_times[self._last_type] += start_time - self._last_type_start
                self._type_stack.append(self._last_type)
            self._last_type = section
            self._last_type_start = time.time()
            self._total_reduction_time += self._last_type_start - start_time

    def _finish_section_profile(self, section):
        if self._current_times[section] is not None:
            start_time = time.time()
            if section != self._last_type:
                logger.error('Mismatched start/end session.  Expected {}, got {}', self._last_type, section)
                self._clear_temporary()
                return
            self._current_times[section] += start_time - self._last_type_start
            if self._type_stack:
                self._last_type = self._type_stack.pop()
            else:
                self._last_type = None
            self._last_type_start = time.time()
            self._total_reduction_time += self._last_type_start - start_time

    @classmethod
    def start(cls):
        if cls._affordance_times is None:
            cls._affordance_times = AutonomyAffordanceTimes()

    @classmethod
    def reset(cls):
        if cls._affordance_times is not None:
            cls._affordance_times._clear()

    @classmethod
    def stop(cls):
        cls._affordance_times = None

    @classmethod
    def dump(cls, connection=None):
        if cls._affordance_times is None:
            return
        affordance_times = cls._affordance_times._affordances
        if not affordance_times:
            return

        def callback(file):
            file.write('Interaction,Count,TotalTime(s),AvgTime(s),TotalDistTime(s),AvgDistTime(s),TotalTransitionTime(s),AvgTransitionTime(s),TotalCompatTime(s),AvgCompatTime(s), Dist %, Transition %, Compat %\n')
            affordances = [(total, dist, transition, compat, count, affordance) for (affordance, (count, total, dist, transition, compat)) in affordance_times.items()]
            for (total, dist, transition, compat, count, affordance) in sorted(affordances, reverse=True):
                percent_multipler = 100/total
                file.write('{},{},{:0.04f},{:0.04f},{:0.04f},{:0.04f},{:0.04f},{:0.04f},{:0.04f},{:0.04f},{:0.02f},{:0.02f},{:0.02f}\n'.format(affordance, count, total, total/count, dist, dist/count, transition, transition/count, compat, compat/count, dist*percent_multipler, transition*percent_multipler, compat*percent_multipler))

        create_csv('autonomy_distance_estimate_times', callback=callback, connection=connection)

    @classmethod
    @contextmanager
    def profile(cls, affordance_name):
        if cls._affordance_times is not None:
            cls._affordance_times._start_profile()
        try:
            yield None
        finally:
            if cls._affordance_times is not None:
                cls._affordance_times._finish_profile(affordance_name)

    @classmethod
    @contextmanager
    def profile_section(cls, section):
        if cls._affordance_times is not None:
            cls._affordance_times._start_section_profile(section)
        try:
            yield None
        finally:
            if cls._affordance_times is not None:
                cls._affordance_times._finish_section_profile(section)
