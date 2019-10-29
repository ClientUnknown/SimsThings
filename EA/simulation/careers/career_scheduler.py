from scheduler import WeeklySchedulefrom careers.career_enums import CareerShiftTypefrom sims4.tuning.tunable import HasTunableFactory, TunableVariant, TunableReference, TunableListimport servicesimport sims4.resources
def get_career_schedule_for_level(career_level, join_time=None, schedule_shift_type=CareerShiftType.ALL_DAY):

    class _CareerScheduleHelper:

        @property
        def current_level_tuning(self):
            return career_level

        @property
        def join_time(self):
            return join_time or services.time_service().sim_now

    return career_level.schedule(_CareerScheduleHelper(), init_only=True, schedule_shift_type=schedule_shift_type)

class CareerScheduleBackwardsCompatible(HasTunableFactory):

    def __new__(self, career, *args, **kwargs):
        level_tuning = career.current_level_tuning
        return level_tuning.work_schedule(*args, **kwargs)

class CareerScheduleFixed(HasTunableFactory):
    FACTORY_TUNABLES = {'career_schedule': WeeklySchedule.TunableFactory()}

    def __new__(self, career, *args, career_schedule, **kwargs):
        return career_schedule(*args, **kwargs)

class CareerScheduleFromServiceNpc(HasTunableFactory):
    FACTORY_TUNABLES = {'career_service_npc': TunableReference(description='\n            The service to be used for scheduling. The work hours match whatever\n            is tuned on the service.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SERVICE_NPC))}

    def __new__(self, career, *args, career_service_npc, **kwargs):
        return career_service_npc.work_hours(*args, **kwargs)

class CareerScheduleShifts(HasTunableFactory):
    FACTORY_TUNABLES = {'career_shifts': TunableList(description='\n            The available shifts for the career. The game validates that there\n            is 24/7 coverage.\n            ', tunable=WeeklySchedule.TunableFactory())}

    def __new__(self, career, *args, career_shifts, **kwargs):
        shift_time = career.join_time
        for career_shift in career_shifts:
            career_shift_schedule = career_shift(init_only=True)
            for (start_time, end_time) in career_shift_schedule.get_schedule_entries():
                if shift_time.time_between_week_times(start_time, end_time):
                    return career_shift(*args, **kwargs)
        raise ValueError('Career shift for {} has no coverage at {}'.format(career, shift_time))

class CareerScheduleNoSchedule(HasTunableFactory):

    def __new__(self, career, *args, **kwargs):
        pass

class CareerScheduleShiftsPlayer(HasTunableFactory):
    FACTORY_TUNABLES = {'career_player_shifts': TunableList(description='\n            The available shifts for the career. The game validates that each\n            shift falls under the valid hours.\n            ', tunable=WeeklySchedule.TunableFactory())}

    def __new__(self, career, *args, career_player_shifts, **kwargs):
        for career_player_shift in career_player_shifts:
            return career_player_shift(*args, **kwargs)

class TunableCareerScheduleVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, backwards_compatible=CareerScheduleBackwardsCompatible.TunableFactory(), fixed=CareerScheduleFixed.TunableFactory(), service_npc=CareerScheduleFromServiceNpc.TunableFactory(), shifts=CareerScheduleShifts.TunableFactory(), shifts_player=CareerScheduleShiftsPlayer.TunableFactory(), no_schedule=CareerScheduleNoSchedule.TunableFactory(), default='backwards_compatible', **kwargs)
