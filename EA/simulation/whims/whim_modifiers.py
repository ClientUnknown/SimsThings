from protocolbuffers.DistributorOps_pb2 import SetWhimBucksfrom date_and_time import create_time_spanfrom game_effect_modifier.base_game_effect_modifier import BaseGameEffectModifierfrom game_effect_modifier.game_effect_type import GameEffectTypefrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableRange, TunableRate, TunableSimMinutefrom sims4.tuning.tunable_base import RateDescriptionsimport alarms
class SatisfactionPointMultiplierModifier(HasTunableSingletonFactory, AutoFactoryInit, BaseGameEffectModifier):
    FACTORY_TUNABLES = {'score_multiplier': TunableRange(description="\n            A multiplier to apply to a Whim's score.\n            ", tunable_type=float, minimum=0, default=1)}

    def __init__(self, **kwargs):
        super().__init__(GameEffectType.WHIM_MODIFIER, **kwargs)

    def apply_modifier(self, sim_info):
        whims_tracker = sim_info.whim_tracker
        if whims_tracker is not None:
            whims_tracker.add_score_multiplier(self.score_multiplier)

    def remove_modifier(self, sim_info, handle):
        whims_tracker = sim_info.whim_tracker
        whims_tracker.remove_score_multiplier(self.score_multiplier)

class SatisfactionPointPeriodicGainModifier(HasTunableSingletonFactory, AutoFactoryInit, BaseGameEffectModifier):
    FACTORY_TUNABLES = {'score_rate': TunableRate(description='\n            The rate at which Sims gain Satisfaction Points.\n            ', rate_description=RateDescriptions.PER_SIM_MINUTE, tunable_type=int, default=1), 'score_interval': TunableSimMinute(description='\n            How often satisfaction points are awarded. Since awarding points has\n            a UI treatment, this affects visible feedback to the player.\n            ', default=8)}

    def __init__(self, **kwargs):
        super().__init__(GameEffectType.WHIM_MODIFIER, **kwargs)

    def apply_modifier(self, sim_info):
        score = int(self.score_interval*self.score_rate)

        def _on_award_satisfaction_points(_):
            sim_info.add_whim_bucks(score, SetWhimBucks.WHIM)

        alarm_handle = alarms.add_alarm(self, create_time_span(minutes=self.score_interval), _on_award_satisfaction_points, repeating=True)
        return alarm_handle

    def remove_modifier(self, sim_info, handle):
        alarms.cancel_alarm(handle)
