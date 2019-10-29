import enumfrom sims4.tuning.dynamic_enum import DynamicEnum
class DecorationLocation(enum.Int):
    FOUNDATIONS = 0
    EAVES = 1
    FRIEZES = 2
    FENCES = 3
    SPANDRELS = 4
    COLUMNS = 5

class DecorationPickerCategory(DynamicEnum):
    ALL = 0
LOT_DECORATION_DEFAULT_ID = 0