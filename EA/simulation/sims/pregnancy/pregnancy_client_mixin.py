from sims4.math import clampimport distributor.fieldsimport distributor.ops
class PregnancyClientMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pregnancy_progress = 0

    @distributor.fields.Field(op=distributor.ops.SetPregnancyProgress, default=None)
    def pregnancy_progress(self):
        return self._pregnancy_progress

    @pregnancy_progress.setter
    def pregnancy_progress(self, value):
        self._pregnancy_progress = clamp(0, value, 1) if value is not None else None
