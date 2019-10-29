from sims4.tuning.dynamic_enum import DynamicEnumimport enum
class SicknessDiagnosticActionType(enum.Int):
    EXAM = 0
    TREATMENT = 1

class DiagnosticActionResultType(DynamicEnum):
    DEFAULT = 0
    CORRECT_TREATMENT = 1
    INCORRECT_TREATMENT = 2
    FAILED_TOO_STRESSED = 3
