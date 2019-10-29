from date_and_time import create_time_spanfrom interactions.utils.tunable_icon import TunableIconfrom seasons import seasons_loggerfrom seasons.seasons_enums import SeasonLength, SeasonSegmentfrom seasons.seasons_tuning import SeasonsTuningfrom sims4.localization import TunableLocalizedStringfrom sims4.math import clampfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, HasTunableFactory, AutoFactoryInit, TunableList, TunableMapping, TunableReference, TunableRange, TunableEnumEntry, TunableTuple, HasTunableSingletonFactory, OptionalTunablefrom sims4.tuning.tunable_base import ExportModes, GroupNamesfrom tunable_time import Days, TunableTimeSpan, TunableTimeOfDayfrom ui.screen_slam import TunableScreenSlamSnippetimport date_and_timeimport servicesimport sims4.resources
class DayOfSeason(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'week_of_season': TunableRange(description='\n            Which week of the season this is.  First week is week 0.\n            ', tunable_type=int, default=0, minimum=0, maximum=7), 'day_of_week': TunableEnumEntry(description='\n            Day of the week.\n            ', tunable_type=Days, default=Days.SUNDAY)}

    def __init__(self, season_start_time, **kwargs):
        super().__init__(**kwargs)
        self._date_and_time = season_start_time + create_time_span(days=self.day_of_season)

    def __repr__(self):
        return repr(self._date_and_time)

    @property
    def date_and_time(self):
        return self._date_and_time

    @property
    def day_of_season(self):
        return self.week_of_season*date_and_time.DAYS_PER_WEEK + self.day_of_week.value

class SeasonalContent(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'holidays': TunableMapping(key_type=TunableReference(description='\n                Drama node to be scheduled for this holiday.\n                ', manager=services.get_instance_manager(sims4.resources.Types.HOLIDAY_DEFINITION), pack_safe=True), value_type=TunableList(tunable=DayOfSeason.TunableFactory())), 'segments': TunableTuple(early_season_length=TunableTimeSpan(description='\n                Early season length, in days.\n                ', default_days=2, locked_args={'hours': 0, 'minutes': 0}), late_season_length=TunableTimeSpan(description='\n                Late season length, in days.\n                ', default_days=2, locked_args={'hours': 0, 'minutes': 0}))}

class Season(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.SEASON)):
    INSTANCE_TUNABLES = {'season_icon': TunableIcon(description="\n            The season's icon.\n            ", export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'season_name': TunableLocalizedString(description="\n            The season's name.\n            ", export_modes=ExportModes.All, tuning_group=GroupNames.UI), 'season_length_content': TunableMapping(description='\n            A mapping of season length option to the content contained within.\n            ', key_type=TunableEnumEntry(tunable_type=SeasonLength, default=SeasonLength.NORMAL), value_type=SeasonalContent.TunableFactory()), 'screen_slam': OptionalTunable(description='\n            If enabled, trigger this Screen Slam when transitioning to this season.\n            ', tunable=TunableTuple(description='\n                The screenslam to trigger, and hour of the day when it should\n                appear to the users.\n                ', slam=TunableScreenSlamSnippet(), trigger_time=TunableTimeOfDay(default_hour=6))), 'whim_set': OptionalTunable(description='\n            If enabled then this season will offer a whim set to the Sim\n            when it is that season.\n            ', tunable=TunableReference(description='\n                A whim set that is active when this season is active.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions=('ObjectivelessWhimSet',)))}

    def __init__(self, start_time, **kwargs):
        super().__init__(**kwargs)
        self._start_time = start_time
        self._length_option = None
        self._length_span = None
        self._content_data = None
        self._mid_season_begin = None
        self._absolute_mid = None
        self._late_season_begin = None
        self._end_of_season = None

    def __contains__(self, date_and_time):
        return self._start_time <= date_and_time < self._end_of_season

    @property
    def info(self):
        holiday_formatted = '\n\t'.join(['{} on {}'.format(holiday.__name__, day_of_season.date_and_time) for (holiday, day_of_season) in self.get_holiday_dates()])
        return 'Resource: {}\nLength: {}\nStart: {}\n\tMid-Season Period: {}\n\tAbsolute Mid-Season: {}\n\tLate-Season Period: {}\nEnd: {}\nHolidays:\n\t{}'.format(self.__class__, self._length_span, self._start_time, self._mid_season_begin, self._absolute_mid, self._late_season_begin, self._end_of_season, holiday_formatted)

    @property
    def start_time(self):
        return self._start_time

    @property
    def length(self):
        return self._length_span

    @property
    def end_time(self):
        return self._end_of_season

    @property
    def midpoint_time(self):
        return self._absolute_mid

    def get_date_at_season_progress(self, progress):
        progress = clamp(0, progress, 1)
        return self._start_time + self._length_span*progress

    def get_position(self, date_and_time):
        return date_and_time - self._start_time

    def get_segment(self, date_and_time):
        if not self._verify_in_season(date_and_time):
            return
        if date_and_time < self._mid_season_begin:
            return SeasonSegment.EARLY
        if date_and_time >= self._late_season_begin:
            return SeasonSegment.LATE
        return SeasonSegment.MID

    def get_progress(self, date_and_time):
        if not self._verify_in_season(date_and_time):
            return
        current_ticks = self.get_position(date_and_time).in_ticks()
        total_ticks = self._length_span.in_ticks()
        return current_ticks/total_ticks

    def get_screen_slam_trigger_time(self):
        if self.screen_slam is None:
            return
        return self._start_time.time_of_next_day_time(self.screen_slam.trigger_time)

    def _verify_in_season(self, date_and_time):
        within_season = date_and_time in self
        if not within_season:
            seasons_logger.error('Provided time {} is not within the current season, which is from {} to {}', date_and_time, self._start_time, self._end_of_season)
        return within_season

    def set_length_option(self, length_option):
        if self._length_option == length_option:
            return
        self._length_option = length_option
        self._length_span = SeasonsTuning.SEASON_LENGTH_OPTIONS[length_option]()
        self._calculate_important_dates()

    def _calculate_important_dates(self):
        self._content_data = self.season_length_content[self._length_option]
        self._mid_season_begin = self._start_time + self._content_data.segments.early_season_length()
        self._absolute_mid = self.get_date_at_season_progress(0.5)
        self._late_season_begin = self._start_time + (self._length_span - self._content_data.segments.late_season_length())
        self._end_of_season = self._start_time + self._length_span

    def get_holiday_dates(self):
        holidays_in_season = []
        for (holiday, season_times) in self._content_data.holidays.items():
            holidays_in_season.extend(iter((holiday, day_of_season(self._start_time)) for day_of_season in season_times))
        return holidays_in_season

    def get_all_holiday_data(self):
        holidays_data = []
        for season_length in SeasonLength:
            for (holiday, season_times) in self.season_length_content[season_length].holidays.items():
                holidays_data.extend(iter((season_length, holiday, day(date_and_time.DATE_AND_TIME_ZERO).day_of_season) for day in season_times))
        return holidays_data

    def get_holidays(self, season_length):
        return set(self._content_data.holidays.keys())
