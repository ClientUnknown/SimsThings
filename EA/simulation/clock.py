import collectionsimport mathfrom date_and_time import TimeSpan, DateAndTimefrom sims4.service_manager import Servicefrom sims4.utils import classpropertyfrom tunable_time import TunableTimeOfWeekimport clock_telemetry_helperimport date_and_timeimport distributor.opsimport distributor.systemimport enumimport persistence_error_typesimport pythonutilsimport servicesimport sims4.tuning.dynamic_enumimport sims4.tuning.tunablelogger = sims4.log.Logger('Clock', default_owner='trevor')
class ClockSpeedMode(enum.Int):
    PAUSED = 0
    NORMAL = 1
    SPEED2 = 2
    SPEED3 = 3
    INTERACTION_STARTUP_SPEED = 4
    SUPER_SPEED3 = 5

class GameSpeedChangeSource(enum.Int, export=False):
    SITUATION = 0
    UI_MODAL = 1
    GAMEPLAY = 2
    INITIAL = 3

def interval_in_real_time(duration, time_unit):
    if time_unit is date_and_time.TimeUnit.SECONDS:
        return interval_in_real_seconds(duration)
    if time_unit is date_and_time.TimeUnit.MINUTES:
        return interval_in_real_minutes(duration)
    if time_unit is date_and_time.TimeUnit.HOURS:
        return interval_in_real_hours(duration)
    if time_unit is date_and_time.TimeUnit.DAYS:
        return interval_in_real_days(duration)
    elif time_unit is date_and_time.TimeUnit.WEEKS:
        return interval_in_real_weeks(duration)

def interval_in_real_seconds(seconds):
    return TimeSpan(seconds*date_and_time.TICKS_PER_REAL_WORLD_SECOND)

def interval_in_real_minutes(minutes):
    return TimeSpan(minutes*date_and_time.TICKS_PER_REAL_WORLD_SECOND*date_and_time.SECONDS_PER_MINUTE)

def interval_in_real_hours(hours):
    return TimeSpan(hours*date_and_time.TICKS_PER_REAL_WORLD_SECOND*date_and_time.SECONDS_PER_HOUR)

def interval_in_real_days(days):
    return TimeSpan(days*date_and_time.TICKS_PER_REAL_WORLD_SECOND*date_and_time.SECONDS_PER_DAY)

def interval_in_real_weeks(weeks):
    return TimeSpan(weeks*date_and_time.TICKS_PER_REAL_WORLD_SECOND*date_and_time.SECONDS_PER_WEEK)

def interval_in_sim_time(duration, time_unit):
    if time_unit is date_and_time.TimeUnit.SECONDS:
        return interval_in_sim_seconds(duration)
    if time_unit is date_and_time.TimeUnit.MINUTES:
        return interval_in_sim_minutes(duration)
    if time_unit is date_and_time.TimeUnit.HOURS:
        return interval_in_sim_hours(duration)
    if time_unit is date_and_time.TimeUnit.DAYS:
        return interval_in_sim_days(duration)
    elif time_unit is date_and_time.TimeUnit.WEEKS:
        return interval_in_sim_weeks(duration)

def interval_in_sim_seconds(seconds):
    return TimeSpan(seconds*date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND)

def interval_in_sim_minutes(minutes):
    return TimeSpan(date_and_time.SECONDS_PER_MINUTE*minutes*date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND)

def interval_in_sim_hours(hours):
    return TimeSpan(date_and_time.SECONDS_PER_HOUR*hours*date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND)

def interval_in_sim_days(days):
    return TimeSpan(date_and_time.SECONDS_PER_DAY*days*date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND)

def interval_in_sim_weeks(weeks):
    return TimeSpan(date_and_time.SECONDS_PER_WEEK*weeks*date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND)

def time_until_hour_of_day(now, hour_of_day):
    cur_hour = now.hour() + now.minute()/date_and_time.SECONDS_PER_MINUTE
    cur_day = int(now.absolute_days())
    if cur_hour < hour_of_day:
        future = date_and_time.create_date_and_time(days=cur_day, hours=hour_of_day)
    else:
        future = date_and_time.create_date_and_time(days=cur_day + 1, hours=hour_of_day)
    return future - now
with sims4.reload.protected(globals()):
    break_point_triggered = False
    g_set_game_time_serial_number = 0
def on_break_point_hook():
    global break_point_triggered
    break_point_triggered = True

class Clock:
    __slots__ = '_ticks'

    def __init__(self, initial_ticks):
        self._ticks = int(initial_ticks)

    def set_ticks(self, ticks):
        self._ticks = ticks

    def _unit_test_advance_minutes(self, delta):
        self._ticks += math.ceil(delta*date_and_time.REAL_MILLISECONDS_PER_SIM_SECOND*date_and_time.SECONDS_PER_MINUTE)

class GameClock(Service):
    NEW_GAME_START_TIME = TunableTimeOfWeek(description='The time the game starts at when a player starts a new game.')
    MAX_GAME_CLOCK_TICK_STEP = 5000
    SECONDS_BETWEEN_CLOCK_BROADCAST = 5
    PAUSED_SPEED_MULTIPLIER = 0
    NORMAL_SPEED_MULTIPLIER = 1
    ignore_game_speed_requests = False

    def __init__(self):
        super().__init__()
        date_and_time.send_clock_tuning()
        ticks = services.server_clock_service().ticks()
        self._initial_server_ticks = ticks
        new_game_start_time = GameClock.NEW_GAME_START_TIME()
        self._initial_ticks = new_game_start_time.absolute_ticks()
        self._previous_absolute_ticks = ticks
        self._game_clock = Clock(0)
        self._tick_to_next_message = 0
        self._error_accumulation = 0
        self._last_speed_change_server_time = self._initial_server_ticks
        self._server_ticks_spent_in_speed = collections.Counter()
        self._loading_monotonic_ticks = 0
        self.clock_speed_multiplier_type = ClockSpeedMultiplierType.DEFAULT
        self._clock_speed = ClockSpeedMode.PAUSED
        self._non_ui_clock_speed = ClockSpeedMode.PAUSED
        self.speed_controllers = collections.defaultdict(_SpeedController)
        self.speed_controllers[GameSpeedChangeSource.INITIAL].push_speed(ClockSpeedMode.PAUSED, reason='Initial Speed')
        self.set_game_time_callback = None

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_GAME_CLOCK

    def _update_speed(self, immediate=False):
        for speed_request in self.game_speed_requests_gen():
            if not speed_request.validity_check is None:
                if speed_request.validity_check():
                    new_speed = speed_request.speed
                    break
            new_speed = speed_request.speed
            break
        logger.error('No valid game speeds in the game speed controllers: {}', self.speed_controllers, owner='bhill')
        new_speed = ClockSpeedMode.PAUSED
        old_speed = self._clock_speed
        if old_speed == new_speed:
            return
        self._update_time_spent_in_speed(old_speed)
        self._clock_speed = new_speed
        if new_speed == ClockSpeedMode.NORMAL and self.clock_speed_multiplier_type != ClockSpeedMultiplierType.DEFAULT:
            self._set_clock_speed_multiplier_type(ClockSpeedMultiplierType.DEFAULT, do_sync=False)
        if new_speed == ClockSpeedMode.SUPER_SPEED3:
            services.get_zone_situation_manager().ss3_make_all_npcs_leave_now()
        self._sync_clock_and_broadcast_gameclock(immediate=immediate)
        if new_speed == ClockSpeedMode.PAUSED:
            gc2_triggered = pythonutils.try_highwater_gc()
            if gc2_triggered:
                logger.debug('Pausing the game has triggered highwater GC2.', owner='manus')

    def stop(self):
        self._game_clock = None
        self.speed_controllers = None

    def tick_game_clock(self, absolute_ticks):
        global break_point_triggered
        if self.clock_speed != ClockSpeedMode.PAUSED:
            scale = self.current_clock_speed_scale()
            diff = absolute_ticks - self._previous_absolute_ticks
            if diff < 0:
                logger.error('game clock ticking backwards. absolute ticks: {}, previous absolute ticks: {}', absolute_ticks, self._previous_absolute_ticks)
                return
            if break_point_triggered:
                diff = 1
                self._tick_to_next_message = 0
                break_point_triggered = False
            if diff > GameClock.MAX_GAME_CLOCK_TICK_STEP:
                logger.warn('Gameplay clock experienced large server tick step: {}. Ignoring large time step and using {} as tick increment.', diff, GameClock.MAX_GAME_CLOCK_TICK_STEP)
                clock_telemetry_helper.report_max_tick_spike(self.clock_speed, diff, GameClock.MAX_GAME_CLOCK_TICK_STEP)
                diff = GameClock.MAX_GAME_CLOCK_TICK_STEP
                self._tick_to_next_message = 0
            ideal_tick_increment = diff*scale + self._error_accumulation
            rounded = math.floor(ideal_tick_increment + 0.5)
            error = ideal_tick_increment - rounded
            self._error_accumulation = self._error_accumulation + sims4.math.clamp(-1, error, 1)
            self._game_clock.set_ticks(rounded + self._game_clock._ticks)
        distributor.system.Distributor.instance().add_op_with_no_owner(distributor.ops.Heartbeat())
        self._previous_absolute_ticks = absolute_ticks
        if absolute_ticks > self._tick_to_next_message:
            self._tick_to_next_message = absolute_ticks + self.SECONDS_BETWEEN_CLOCK_BROADCAST*date_and_time.TICKS_PER_REAL_WORLD_SECOND
            self._sync_clock_and_broadcast_gameclock()

    def enter_zone_spin_up(self):
        self._loading_monotonic_ticks = 0

    def advance_for_hitting_their_marks(self):
        loading_clock_speed = self._clock_speed_to_scale(ClockSpeedMode.INTERACTION_STARTUP_SPEED)
        increment = math.floor(33*loading_clock_speed)
        self._loading_monotonic_ticks += increment
        self._sync_clock_and_broadcast_gameclock()

    def exit_zone_spin_up(self):
        self.pop_speed(ClockSpeedMode.INTERACTION_STARTUP_SPEED)

    def monotonic_time(self):
        return DateAndTime(self._game_clock._ticks + self._loading_monotonic_ticks)

    def _sync_clock_and_broadcast_gameclock(self, immediate=False):
        global g_set_game_time_serial_number
        server_time = services.server_clock_service().ticks()
        clock_speed = self.clock_speed
        game_speed = self.current_clock_speed_scale()
        super_speed = clock_speed == ClockSpeedMode.SUPER_SPEED3
        if super_speed:
            clock_speed = ClockSpeedMode.SPEED3
        if clock_speed == ClockSpeedMode.INTERACTION_STARTUP_SPEED:
            game_time = self._loading_monotonic_ticks
            monotonic_time = self._loading_monotonic_ticks
        else:
            game_time = self._game_clock._ticks
            monotonic_time = game_time + self._loading_monotonic_ticks
        g_set_game_time_serial_number += 1
        op = distributor.ops.SetGameTime(server_time, monotonic_time, game_time, game_speed, clock_speed, self._initial_ticks, super_speed, g_set_game_time_serial_number)
        if immediate:
            distributor.system.Distributor.instance().send_op_with_no_owner_immediate(op)
        else:
            distributor.system.Distributor.instance().add_op_with_no_owner(op)
        if self.set_game_time_callback is not None:
            self.set_game_time_callback(server_time, monotonic_time, game_time, game_speed, clock_speed, self._initial_ticks, super_speed)

    def now(self):
        return DateAndTime(self._game_clock._ticks + self._initial_ticks)

    def push_speed(self, speed, source=GameSpeedChangeSource.GAMEPLAY, validity_check=None, reason='', immediate=False):
        if source == GameSpeedChangeSource.UI_MODAL:
            controllers = self.speed_controllers.get(source)
            if not controllers:
                self._non_ui_clock_speed = self._clock_speed
        request = self.speed_controllers[source].push_speed(speed, reason=str(reason), validity_check=validity_check)
        self._update_speed(immediate=immediate)
        return request

    def pop_speed(self, speed=None, source=GameSpeedChangeSource.GAMEPLAY, reason='', immediate=False):
        request = self.speed_controllers[source].pop_speed(speed)
        self._update_speed(immediate=immediate)
        return request

    def remove_request(self, request, source=GameSpeedChangeSource.GAMEPLAY, reason='', immediate=False):
        if request in self.speed_controllers[source]:
            self.speed_controllers[source].remove(request)
        self._update_speed(immediate=immediate)

    def set_clock_speed(self, speed, source=GameSpeedChangeSource.GAMEPLAY, reason='', immediate=False) -> bool:
        if speed not in ClockSpeedMode.values:
            logger.error('Attempting to set clock speed to something invalid: {}', speed)
            return False
        logger.debug('set_clock_speed CALLED ...\n    speed: {}, change_source: {}, reason: {}', speed, source, reason)
        self.speed_controllers[source][:] = [request for request in self.speed_controllers[source] if request.speed == ClockSpeedMode.SUPER_SPEED3]
        if speed != ClockSpeedMode.SPEED3:
            self.speed_controllers[source].push_speed(speed, reason=str(reason))
        else:
            for speed_request in self.game_speed_requests_gen():
                if not speed_request.validity_check is None:
                    if speed_request.validity_check():
                        secondary_speed = speed_request.speed
                        break
                secondary_speed = speed_request.speed
                break
            secondary_speed = None
            if secondary_speed != ClockSpeedMode.SUPER_SPEED3:
                self.speed_controllers[source].push_speed(speed, reason=str(reason))
        self._update_speed(immediate=immediate)
        logger.debug('set_clock_speed SUCCEEDED. speed: {}, change_source: {}, reason: {}', speed, source, reason)
        return True

    @property
    def clock_speed(self):
        return self._clock_speed

    @property
    def persistable_clock_speed(self):
        if self.speed_controllers[GameSpeedChangeSource.UI_MODAL]:
            return self._non_ui_clock_speed
        return self._clock_speed

    def current_clock_speed_scale(self):
        return self._clock_speed_to_scale(self.clock_speed)

    def _clock_speed_to_scale(self, clock_speed):
        if clock_speed == ClockSpeedMode.PAUSED:
            return self.PAUSED_SPEED_MULTIPLIER
        if clock_speed == ClockSpeedMode.NORMAL:
            return self.NORMAL_SPEED_MULTIPLIER
        if clock_speed == ClockSpeedMode.SPEED2:
            return ClockSpeedMultipliers.speed_two_multiplier(self.clock_speed_multiplier_type)
        if clock_speed == ClockSpeedMode.SPEED3:
            return ClockSpeedMultipliers.speed_three_multiplier(self.clock_speed_multiplier_type)
        if clock_speed == ClockSpeedMode.SUPER_SPEED3:
            return ClockSpeedMultipliers.super_speed_three_multiplier(self.clock_speed_multiplier_type)
        elif clock_speed == ClockSpeedMode.INTERACTION_STARTUP_SPEED:
            return ClockSpeedMultipliers.get_interaction_startup_speed_multiplier()

    def on_client_connect(self, client):
        self._sync_clock_and_broadcast_gameclock()
        logger.debug('Clock.on_client_connect {}', self.now())

    def restore_saved_clock_speed(self):
        if not services.current_zone().is_in_build_buy:
            self.pop_speed(ClockSpeedMode.PAUSED)

    def on_client_disconnect(self, client):
        self._update_time_spent_in_speed(self.clock_speed)
        total_time_spent = services.server_clock_service().ticks() - self._initial_server_ticks
        for speed in ClockSpeedMode:
            time_spent_in_speed = self._server_ticks_spent_in_speed[speed]
            precentage_time_in_speed = time_spent_in_speed/float(total_time_spent)*100
            time_spent_in_speed = time_spent_in_speed/date_and_time.TICKS_PER_REAL_WORLD_SECOND
            clock_telemetry_helper.report_change_speed(speed, time_spent_in_speed, precentage_time_in_speed)
        self.set_clock_speed(ClockSpeedMode.PAUSED)

    def set_game_time(self, hours, minutes, seconds):
        current_date_and_time = self.now()
        days = int(current_date_and_time.absolute_days())
        current_time_minus_days = current_date_and_time - DateAndTime(interval_in_sim_days(days).in_ticks())
        requested_time = interval_in_sim_hours(hours) + interval_in_sim_minutes(minutes) + interval_in_sim_seconds(seconds)
        time_difference = requested_time - current_time_minus_days
        if time_difference.in_hours() < 0:
            time_difference = time_difference + interval_in_sim_hours(24)
        self._add_to_game_time_and_send_update(time_difference.in_ticks())

    def advance_game_time(self, hours=0, minutes=0, seconds=0):
        requested_increment = interval_in_sim_hours(hours) + interval_in_sim_minutes(minutes) + interval_in_sim_seconds(seconds)
        self._add_to_game_time_and_send_update(requested_increment.in_ticks())

    def _add_to_game_time_and_send_update(self, time_difference_in_ticks):
        self._initial_ticks += time_difference_in_ticks
        self._sync_clock_and_broadcast_gameclock()

    def game_speed_requests_gen(self):
        for source in sorted(GameSpeedChangeSource.values):
            yield from reversed(self.speed_controllers[source])

    def _update_time_spent_in_speed(self, current_speed):
        server_time = services.server_clock_service().ticks()
        server_ticks_spent_in_current_speed = server_time - self._last_speed_change_server_time
        self._server_ticks_spent_in_speed[current_speed] += server_ticks_spent_in_current_speed
        self._last_speed_change_server_time = server_time

    def save(self, zone_data=None, save_slot_data=None, **kwargs):
        if save_slot_data is not None:
            save_ticks = services.time_service().sim_now.absolute_ticks()
            save_slot_data.gameplay_data.world_game_time = save_ticks

    def setup(self, gameplay_zone_data=None, save_slot_data=None):
        if save_slot_data.HasField('gameplay_data'):
            self._initial_ticks = save_slot_data.gameplay_data.world_game_time

    def set_initial_ticks_for_zone_startup(self, absolute_ticks):
        self._initial_ticks = absolute_ticks
        self._game_clock.set_ticks(0)

    def _set_clock_speed_multiplier_type(self, clock_speed_multiplier_type, do_sync=True):
        if self.clock_speed_multiplier_type != clock_speed_multiplier_type:
            self.clock_speed_multiplier_type = clock_speed_multiplier_type
            if do_sync:
                self._sync_clock_and_broadcast_gameclock()
            return True
        return False

class ServerClock(Service):

    def __init__(self, *args, ticks=0, **kwargs):
        super().__init__()
        self._server_clock = Clock(ticks)

    def tick_server_clock(self, absolute_ticks):
        self._server_clock.set_ticks(absolute_ticks)

    def start(self):
        return True

    def stop(self):
        self._server_clock = None

    def now(self):
        return DateAndTime(self._server_clock._ticks)

    def ticks(self):
        return self._server_clock._ticks

class SpeedRequest:
    __slots__ = ('speed', 'validity_check', 'reason')

    def __init__(self, speed, validity_check=None, reason=''):
        self.speed = speed
        self.validity_check = validity_check
        self.reason = reason

    def __repr__(self):
        return 'SpeedRequest(speed={}, {})<0x{:x}>'.format(self.speed, self.reason, id(self))

class _SpeedController(list):
    __slots__ = ()

    def push_speed(self, new_speed, validity_check=None, reason=''):
        new_request = SpeedRequest(new_speed, validity_check=validity_check, reason=reason)
        self.append(new_request)
        return new_request

    def pop_speed(self, speed=None):
        if not self:
            return
        if speed is None:
            return self.pop()
        for request in reversed(self):
            if request.speed == speed:
                self.remove(request)
                return request

    def clear_requests(self):
        while self:
            self.pop_speed()

class ClockSpeedMultiplierType(sims4.tuning.dynamic_enum.DynamicEnumLocked):
    DEFAULT = 0
    LOW_PERFORMANCE = 1

class TunableClockSpeedMultipliers(sims4.tuning.tunable.TunableTuple):

    def __init__(self, **kwargs):
        super().__init__(speed_two_multiplier=sims4.tuning.tunable.Tunable(description='\n                How much faster speed two goes than normal speed. The game clock will\n                have its speed multiplied by this number.\n                ', tunable_type=float, default=3.0), speed_three_multiplier=sims4.tuning.tunable.Tunable(description='\n                How much faster speed three goes than normal speed. The game clock will\n                have its speed multiplied by this number.\n                ', tunable_type=float, default=7.0), super_speed_three_multiplier=sims4.tuning.tunable.Tunable(description='\n                How much faster super speed three goes than normal speed. The\n                game clock will have its speed multiplied by this number.\n                ', tunable_type=float, default=36.0), **kwargs)

class ClockSpeedMultipliers:
    TUNABLE_INTERACTION_STARTUP_SPEED_MULTIPLIER = sims4.tuning.tunable.Tunable(description='\n        How much faster preroll autonomy speed goes than normal speed.\n        ', tunable_type=float, default=5.0)
    CLOCK_SPEED_TYPE_MULTIPLIER_MAP = sims4.tuning.tunable.TunableMapping(description='\n        A mapping of ClockSpeedMultiplierTypes to clock speed multipliers.\n        ', key_type=sims4.tuning.tunable.TunableEnumEntry(description='\n            The ClockSpeedMultiplier to which we apply the multipliers.\n            ', tunable_type=ClockSpeedMultiplierType, default=ClockSpeedMultiplierType.DEFAULT), key_name='Clock Speed Multiplier Type', value_type=TunableClockSpeedMultipliers(), value_name='Clock Speed Multipliers')

    @classmethod
    def get_interaction_startup_speed_multiplier(cls):
        return cls.TUNABLE_INTERACTION_STARTUP_SPEED_MULTIPLIER

    @classmethod
    def speed_two_multiplier(cls, clock_speed_multiplier_type):
        return cls.CLOCK_SPEED_TYPE_MULTIPLIER_MAP.get(clock_speed_multiplier_type).speed_two_multiplier

    @classmethod
    def speed_three_multiplier(cls, clock_speed_multiplier_type):
        return cls.CLOCK_SPEED_TYPE_MULTIPLIER_MAP.get(clock_speed_multiplier_type).speed_three_multiplier

    @classmethod
    def super_speed_three_multiplier(cls, clock_speed_multiplier_type):
        return cls.CLOCK_SPEED_TYPE_MULTIPLIER_MAP.get(clock_speed_multiplier_type).super_speed_three_multiplier
