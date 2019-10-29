import enum
class PersistenceGroups(enum.Int, export=False):
    NONE = 0
    OBJECT = 1
    SIM = 2
    IN_OPEN_STREET = 3
