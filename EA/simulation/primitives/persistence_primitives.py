try:
    import _persistence_primitives
except ImportError:

    class _persistence_primitives:
        PersistVersion = 0

class PersistVersion:
    UNKNOWN = 0
    kPersistVersion_Implementation = 1
    SaveObjectDepreciation = 2
    SaveObjectCreateFromLotTemplate = 3
    SaveLoadSIFirstPass = 4
    GlobalSaveData = 5
