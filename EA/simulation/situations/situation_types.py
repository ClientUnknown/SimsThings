from collections import namedtuplefrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.dynamic_enum import DynamicEnumLockedfrom sims4.tuning.tunable import TunableEnumEntry, TunableMappingfrom sims4.tuning.tunable_base import ExportModesimport enum
class SituationStage(enum.Int, export=False):
    NEVER_RUN = 0
    SETUP = 1
    RUNNING = 2
    DYING = 4
    DEAD = 5

class SituationCreationUIOption(enum.Int):
    NOT_AVAILABLE = 0
    AVAILABLE = 1
    DEBUG_AVAILABLE = 2
    SPECIFIED_ONLY = 3

class SituationMedal(enum.Int):
    TIN = 0
    BRONZE = 1
    SILVER = 2
    GOLD = 3

class SituationCategoryUid(DynamicEnumLocked, display_sorted=True):
    DEFAULT = 0
    DEBUG = 1

class SituationCategory:
    CATEGORIES = TunableMapping(description='\n\t\tMapping from Uid to Name\n        ', key_type=TunableEnumEntry(description='\n            The Situation Category.\n            ', tunable_type=SituationCategoryUid, default=SituationCategoryUid.DEFAULT), value_type=TunableLocalizedString(description='\n            The Category Name\n            '))

class SituationCallbackOption:
    END_OF_SITUATION_SCORING = 0
    END_OF_SITUATION = 1

class SimJobScore(namedtuple('SimJobScore', 'sim, job_type, score')):

    def __str__(self):
        return 'sim {}, job_type {}, score {}'.format(self.sim, self.job_type, self.score)

class ScoringCallbackData:

    def __init__(self, situation_id, situation_score):
        self.situation_id = situation_id
        self.situation_score = situation_score
        self.sim_job_scores = []

    def add_sim_job_score(self, sim, job_type, score):
        self.sim_job_scores.append(SimJobScore(sim, job_type, score))

    def __str__(self):
        return 'situation id {}, situation score {} sims {}'.format(self.situation_id, self.situation_score, self.sim_job_scores)

class JobHolderNoShowAction(enum.Int):
    END_SITUATION = 0
    REPLACE_THEM = 1
    DO_NOTHING = 2

class JobHolderDiedOrLeftAction(enum.Int):
    END_SITUATION = 0
    REPLACE_THEM = 1
    DO_NOTHING = 2

class GreetedStatus(enum.Int, export=False):
    GREETED = 0
    WAITING_TO_BE_GREETED = 1
    NOT_APPLICABLE = 3

class SituationSerializationOption(enum.Int, export=False):
    DONT = 0
    LOT = 1
    OPEN_STREETS = 2
    HOLIDAY = 3

class SituationCommonBlacklistCategory(enum.IntFlags, export=False):
    ACTIVE_HOUSEHOLD = 1
    ACTIVE_LOT_HOUSEHOLD = 2

class SituationDisplayType(enum.Int, export=False):
    NORMAL = 0
    VET = 1
    SIM_SPECIFIC = 2

class SituationDisplayPriority(enum.Int, export=False):
    HOLIDAY = 1
    NORMAL = 2
    VET = 3

class SituationGoalDisplayType(enum.Int):
    NORMAL = 0
    COMPLETION_ONLY = 1

class SituationUserFacingType(enum.Int):
    SOCIAL_EVENT = 0
    CAREER_EVENT = 1
    VET_SITUATION_EVENT = 2
    HOLIDAY_EVENT = 3
    ACTING_CAREER_EVENT = 4
    MOTHER_PLANT_EVENT = 5
