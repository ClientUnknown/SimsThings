from sims.sim_info_lod import SimInfoLODLevelfrom sims4.utils import classproperty
class BaseLODTracker:
    __slots__ = ()

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.BASE

    @classmethod
    def is_valid_for_lod(cls, lod):
        if lod >= cls._tracker_lod_threshold:
            return True
        return False

class SimInfoTracker(BaseLODTracker):
    __slots__ = ()

    def on_lod_update(self, old_lod, new_lod):
        pass
