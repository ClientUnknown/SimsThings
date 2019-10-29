from broadcasters.broadcaster import Broadcasterfrom broadcasters.broadcaster_effect import _BroadcasterEffectfrom broadcasters.broadcaster_utils import BroadcasterClockTypefrom sims4.tuning.instances import lock_instance_tunables
class BroadcasterEffectEnvironmentScore(_BroadcasterEffect):

    def apply_broadcaster_effect(self, broadcaster, affected_object):
        if affected_object.is_sim:
            affected_object.add_environment_score_broadcaster(broadcaster)

    def remove_broadcaster_effect(self, broadcaster, affected_object):
        if affected_object.is_sim:
            affected_object.remove_environment_score_broadcaster(broadcaster)

class BroadcasterEnvironmentScore(Broadcaster):
    REMOVE_INSTANCE_TUNABLES = ('effects',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.effects = (BroadcasterEffectEnvironmentScore(),)
lock_instance_tunables(BroadcasterEnvironmentScore, clock_type=BroadcasterClockType.REAL_TIME)