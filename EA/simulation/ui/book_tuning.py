import enumimport sims4.resourceslogger = sims4.log.Logger('Book', default_owner='jdimailig')
class BookDisplayStyle(enum.Int, export=False):
    DEFAULT = 0
    WITCH = 1

class BookCategoryDisplayType(enum.Int):
    DEFAULT = 0
    WITCH_PRACTICAL_SPELL = 1
    WITCH_MISCHIEF_SPELL = 2
    WITCH_UNTAMED_SPELL = 3
    WITCH_POTION = 4

class BookPageType(enum.Int, export=False):
    BLANK = 0
    FRONT = 1
    CATEGORY_LIST = 2
    CATEGORY_FRONT = 3
    CATEGORY = 4

class BookEntryStatusFlag(enum.IntFlags, export=False):
    ENTRY_UNLOCKED = 1
    ENTRY_NEW = 2
