import enum
class CareerCategory(enum.Int):
    Invalid = 0
    Work = 1
    School = 2
    TeenPartTime = 3
    Volunteer = 4
    AdultPartTime = 5

class CareerPanelType(enum.Int):
    NORMAL_CAREER = 0
    AGENT_BASED_CAREER = 1
    FREELANCE_CAREER = 2
    ODD_JOB_CAREER = 3
WORK_CAREER_CATEGORIES = (CareerCategory.Work, CareerCategory.TeenPartTime, CareerCategory.AdultPartTime)
class GigResult(enum.Int):
    GREAT_SUCCESS = 0
    SUCCESS = 1
    FAILURE = 2
    CRITICAL_FAILURE = 3
    CANCELED = 4

class CareerOutfitGenerationType(enum.Int):
    CAREER_TUNING = 0
    ZONE_DIRECTOR = 1

class CareerShiftType(enum.Int):
    ALL_DAY = 0
    MORNING = 1
    EVENING = 2

class ReceiveDailyHomeworkHelp(enum.Int):
    UNCHECKED = 0
    CHECKED_RECEIVE_HELP = 1
    CHECKED_NO_HELP = 2
