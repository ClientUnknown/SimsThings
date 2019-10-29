from alarms import add_alarm, cancel_alarmfrom clock import ClockSpeedMode, interval_in_sim_days, interval_in_sim_hours, interval_in_sim_minutesfrom date_and_time import DateAndTime, TimeSpanfrom singletons import SingletonMetaclassimport servicesimport sims4.commandslogger = sims4.log.Logger('SimulateToTime', default_owner='bflanagan')
class SimulateToTime(metaclass=SingletonMetaclass):

    def __init__(self):
        self._alarm_handle = None
        self._connection = None

    def _output(self, the_string):
        if self._output_fn is not None:
            self._output_fn(the_string)

    def _start(self, target_hours, target_minutes, days, speed):
        self._set_expected_time(target_hours, target_minutes, days)
        self._target_speed = speed
        self._alarm_handle = add_alarm(self, TimeSpan.ONE, self._tick, repeating=True)
        if self._alarm_handle is None:
            logger.error('_start() failed to create alarm')
        else:
            self._output('SimulateToTime:  Started')
            zone = services.current_zone()
            self._old_auto_respond = zone.ui_dialog_service.auto_respond
            zone.ui_dialog_service.set_auto_respond(True)
            self._output('SimulateToTime:  Currently {}'.format(self._current_date_and_time))
            self._output('SimulateToTime:  Run until {}'.format(self._expected_data_and_time))
            self._set_target_speed()

    def start(self, target_hours:int=None, target_minutes:int=None, days_ahead:int=None, target_speed:int=None, output_fn=None):
        canceled = False
        if self._alarm_handle != None:
            self.cancel()
            canceled = True
        self._output_fn = output_fn
        if target_hours is None and (target_minutes is None and days_ahead is None) and target_speed is None:
            if canceled:
                self._output('SimulateToTime:  no parameters given, so just canceled previous instance')
            else:
                self._output('SimulateToTime:  no parameters given, no work done')
            return True
        if target_hours is None and target_minutes is None:
            self._output('SimulateToTime:  usage error, hours and minutes must be set')
            return False
        days = days_ahead or 0
        speed = target_speed or 3
        self._start(target_hours, target_minutes, days, speed)
        return True

    def _set_speed_on_clock(self, target_speed):
        clock_service = services.game_clock_service()
        if clock_service.clock_speed != target_speed:
            clock_service.set_clock_speed(target_speed, immediate=True)
            self._output('SimulateToTime:  Set simulation speed = {}'.format(target_speed))

    def cancel(self):
        if self._alarm_handle != None:
            cancel_alarm(self._alarm_handle)
            self._alarm_handle = None
            self._output('SimulateToTime:  Stopped')
            self._set_speed_on_clock(ClockSpeedMode.PAUSED)
            zone = services.current_zone()
            zone.ui_dialog_service.set_auto_respond(self._old_auto_respond)

    def _set_target_speed(self):
        target_speed = ClockSpeedMode.SPEED3
        if self._target_speed <= 1:
            target_speed = ClockSpeedMode.NORMAL
        elif self._target_speed == 2:
            target_speed = ClockSpeedMode.SPEED2
        self._set_speed_on_clock(target_speed)

    def _set_expected_time(self, target_hours, target_minutes, days_ahead):
        clock = services.game_clock_service()
        self._current_date_and_time = clock.now()
        clock_days = int(self._current_date_and_time.absolute_days())
        time_span = self._current_date_and_time - DateAndTime(interval_in_sim_days(clock_days).in_ticks())
        current_date_and_time_minus_days = DateAndTime(time_span.in_ticks())
        clock_hours = int(current_date_and_time_minus_days.absolute_hours())
        time_span = current_date_and_time_minus_days - DateAndTime(interval_in_sim_hours(clock_hours).in_ticks())
        current_date_and_time_minus_hours = DateAndTime(time_span.in_ticks())
        clock_minutes = int(current_date_and_time_minus_hours.absolute_minutes())
        delta_days = days_ahead
        clock_day_minutes = clock_hours*60 + clock_minutes
        target_day_minutes = target_hours*60 + target_minutes
        delta_day_minutes = target_day_minutes - clock_day_minutes
        if delta_day_minutes < 0:
            delta_day_minutes += 1440
        self._expected_data_and_time = self._current_date_and_time + interval_in_sim_days(delta_days) + interval_in_sim_minutes(delta_day_minutes)

    def _tick(self, alarm_id):
        if self._alarm_handle is None:
            return True
        self._set_target_speed()
        clock = services.game_clock_service()
        current_date_and_time = clock.now()
        if current_date_and_time >= self._expected_data_and_time:
            self._output('SimulateToTime:  Reached target time')
            self.cancel()
        return True
