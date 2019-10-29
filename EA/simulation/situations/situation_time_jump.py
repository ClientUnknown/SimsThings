from sims4.tuning.tunable import HasTunableSingletonFactory, TunableVariantimport services
class _SituationTimeJump:

    def should_load(self, seed):
        raise NotImplementedError

    def require_guest_list_regeneration(self, situation):
        raise NotImplementedError

class SituationTimeJumpDisallow(HasTunableSingletonFactory):

    def should_load(self, seed):
        if services.current_zone().time_has_passed_in_world_since_zone_save():
            return False
        return True

    def require_guest_list_regeneration(self, situation):
        return False

class SituationTimeJumpAllow(HasTunableSingletonFactory):

    def should_load(self, seed):
        return True

    def require_guest_list_regeneration(self, situation):
        if services.current_zone().time_has_passed_in_world_since_zone_save():
            return True
        return False

class SituationTimeJumpSimulate(SituationTimeJumpAllow):

    def should_load(self, seed):
        if not services.current_zone().time_has_passed_in_world_since_zone_save():
            return True
        else:
            situation_type = seed.situation_type
            if situation_type is not None and situation_type.should_load_after_time_jump(seed):
                seed.allow_time_jump = True
                return True
        return False
SITUATION_TIME_JUMP_DISALLOW = SituationTimeJumpDisallow()
class TunableSituationTimeJumpVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        return super().__init__(*args, disallow=SituationTimeJumpDisallow.TunableFactory(), allow=SituationTimeJumpAllow.TunableFactory(), simulate=SituationTimeJumpSimulate.TunableFactory(), default='disallow', **kwargs)
