import enum
class SimInfoLODLevel(enum.Int):
    MINIMUM = 1
    BASE = 25
    FULL = 100
    ACTIVE = 125

    @staticmethod
    def get_previous_lod(from_lod):
        if from_lod == SimInfoLODLevel.MINIMUM:
            return
        for lod in reversed(SimInfoLODLevel):
            if lod < from_lod:
                return lod

    @staticmethod
    def get_next_lod(from_lod):
        if from_lod == SimInfoLODLevel.FULL:
            return
        for lod in SimInfoLODLevel:
            if lod > from_lod:
                return lod
