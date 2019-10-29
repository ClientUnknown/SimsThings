from sims4.tuning.tunable import TunableRangeimport date_and_timeimport enumimport sims4.tuning.tunable
class Days(enum.Int):
    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6

def date_and_time_from_hours_minutes(hour, minute):
    return date_and_time.create_date_and_time(hours=hour, minutes=minute)

def date_and_time_from_days_hours_minutes(day, hour, minute):
    return date_and_time.create_date_and_time(days=day, hours=hour, minutes=minute)

def time_span_from_days_hours_minutes(days, hours, minutes):
    return date_and_time.create_time_span(days=days, hours=hours, minutes=minutes)

class TunableTimeOfDay(sims4.tuning.tunable.TunableSingletonFactory):
    __slots__ = ()
    FACTORY_TYPE = staticmethod(date_and_time_from_hours_minutes)

    def __init__(self, description='An Hour(24Hr) and Minute representing a time relative to the beginning of a day.', default_hour=12, default_minute=0, **kwargs):
        super().__init__(hour=sims4.tuning.tunable.TunableRange(int, default_hour, 0, 23, description='Hour of the day'), minute=sims4.tuning.tunable.TunableRange(int, default_minute, 0, 59, description='Minute of Hour'), description=description, **kwargs)

class TunableTimeOfWeek(sims4.tuning.tunable.TunableFactory):
    __slots__ = ()
    FACTORY_TYPE = staticmethod(date_and_time_from_days_hours_minutes)

    def __init__(self, description='A Day, Hour(24hr) and Minute representing a time relative to the beginning of a week.', default_day=Days.SUNDAY, default_hour=12, default_minute=0, **kwargs):
        super().__init__(day=sims4.tuning.tunable.TunableEnumEntry(Days, default_day, needs_tuning=True, description='Day of the week'), hour=sims4.tuning.tunable.TunableRange(int, default_hour, 0, 23, description='Hour of the day'), minute=sims4.tuning.tunable.TunableRange(int, default_minute, 0, 59, description='Minute of Hour'), description=description, **kwargs)

class TunableTimeSpan(sims4.tuning.tunable.TunableFactory):
    __slots__ = ()
    FACTORY_TYPE = staticmethod(time_span_from_days_hours_minutes)

    def __init__(self, description='A duration that may be specified in weeks/days/hours/minutes.', default_days=0, default_hours=0, default_minutes=0, **kwargs):
        super().__init__(days=TunableRange(description='Number of days', tunable_type=int, default=default_days, minimum=0), hours=TunableRange(description='Number of hours', tunable_type=int, default=default_hours, minimum=0, maximum=23), minutes=TunableRange(description='Number of minutes', tunable_type=int, default=default_minutes, minimum=0, maximum=59), description=description, **kwargs)
