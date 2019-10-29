from sims4.resources import Typesfrom sims4.tuning.tunable import TunablePackSafeResourceKey
class TunableAudioAllPacks(TunablePackSafeResourceKey):

    def __init__(self, *, description='The audio file.', **kwargs):
        super().__init__(*(None,), resource_types=(Types.PROPX,), description=description, **kwargs)

    @property
    def validate_pack_safe(self):
        return False
