from interactions.utils.has_display_text_mixin import HasDisplayTextMixinfrom rewards.reward_enums import RewardDestinationfrom sims4.tuning.tunable import HasTunableFactoryfrom sims4.utils import constproperty
class TunableRewardBase(HasTunableFactory, HasDisplayTextMixin):

    @constproperty
    def reward_type():
        pass

    def open_reward(self, sim_info, reward_destination=RewardDestination.HOUSEHOLD, **kwargs):
        raise NotImplementedError

    def valid_reward(self, sim_info):
        return True
