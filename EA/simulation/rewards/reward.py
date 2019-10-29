from event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetfrom rewards.reward_enums import RewardDestinationfrom rewards.reward_tuning import TunableSpecificReward, TunableRandomRewardfrom sims4 import randomfrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableResourceKey, TunableList, TunableVariant, OptionalTunable, Tunablefrom sims4.tuning.tunable_base import ExportModesfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport servicesimport sims4.resources
class Reward(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.REWARD)):
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'name': TunableLocalizedString(description='\n            The display name for this reward.\n            ', allow_catalog_name=True, export_modes=ExportModes.All), 'reward_description': TunableLocalizedString(description='\n            Description for this reward.\n            ', export_modes=ExportModes.All), 'icon': TunableResourceKey(description='\n            The icon image for this reward.\n            ', resource_types=sims4.resources.CompoundTypes.IMAGE, export_modes=ExportModes.All), 'tests': TunableTestSet(description='\n            A series of tests that must pass in order for reward to be available.\n            '), 'rewards': TunableList(TunableVariant(description='\n                The gifts that will be given for this reward. They can be either\n                a specific reward or a random reward, in the form of a list of\n                specific rewards.\n                ', specific_reward=TunableSpecificReward(), random_reward=TunableList(TunableRandomReward()))), 'notification': OptionalTunable(description='\n            If enabled, this notification will show when the sim/household receives this reward.\n            ', tunable=TunableUiDialogNotificationSnippet())}

    @classmethod
    def give_reward(cls, sim_info, disallowed_reward_types=()):
        raise NotImplementedError

    @classmethod
    def try_show_notification(cls, sim_info):
        if cls.notification is not None:
            dialog = cls.notification(sim_info, SingleSimResolver(sim_info))
            dialog.show_dialog()

    @classmethod
    def is_valid(cls, sim_info):
        if not cls.tests.run_tests(SingleSimResolver(sim_info)):
            return False
        for reward in cls.rewards:
            if not isinstance(reward, tuple):
                reward_instance = reward()
                return reward_instance.valid_reward(sim_info)
            for each_reward in reward:
                reward_instance = each_reward.reward()
                if not reward_instance.valid_reward(sim_info):
                    return False
            return True

class SimReward(Reward):

    @classmethod
    def give_reward(cls, sim_info, disallowed_reward_types=(), force_rewards_to_sim_info_inventory=False):
        return _give_reward_payout(cls, sim_info, RewardDestination.SIM, disallowed_reward_types=disallowed_reward_types, force_rewards_to_sim_info_inventory=force_rewards_to_sim_info_inventory)

class HouseholdReward(Reward):
    INSTANCE_TUNABLES = {'deliver_with_mail': Tunable(description='\n            If checked, the reward will be delivered through the mail instead of\n            directly to the household inventory.\n            ', tunable_type=bool, default=False)}

    @classmethod
    def give_reward(cls, sim_info, disallowed_reward_types=()):
        return _give_reward_payout(cls, sim_info, RewardDestination.MAILBOX if cls.deliver_with_mail else RewardDestination.HOUSEHOLD, disallowed_reward_types=disallowed_reward_types)

def _give_reward_payout(reward_instance, sim_info, reward_destination, disallowed_reward_types=(), force_rewards_to_sim_info_inventory=False):
    payout = []
    for reward in reward_instance.rewards:
        if issubclass(type(reward), tuple):
            weighted_rewards = []
            for random_reward in reward:
                if random_reward.reward is None:
                    weighted_rewards.append((random_reward.weight, None))
                elif random_reward.reward.factory.reward_type in disallowed_reward_types:
                    pass
                else:
                    weighted_rewards.append((random_reward.weight, random_reward.reward))
            chosen_reward_type = random.weighted_random_item(weighted_rewards)
        else:
            chosen_reward_type = reward if reward.factory.reward_type not in disallowed_reward_types else None
        if chosen_reward_type is not None:
            reward = chosen_reward_type()
            reward.open_reward(sim_info, reward_destination=reward_destination, force_rewards_to_sim_info_inventory=force_rewards_to_sim_info_inventory)
            payout.append(reward)
    if payout:
        reward_instance.try_show_notification(sim_info)
    return payout
