
class AudioEffectData:

    def __init__(self, effect_id, track_flags=None):
        self._effect_id = effect_id
        self._track_flags = track_flags

    @property
    def effect_id(self):
        return self._effect_id

    @property
    def track_flags(self):
        return self._track_flags
