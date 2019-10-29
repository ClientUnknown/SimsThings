from interactions.utils.loot_basic_op import BaseLootOperation
class RewardOperation(BaseLootOperation):
    FACTORY_TUNABLES = {'reward': Reward.TunableReference(description='\n            The reward given to the subject of the loot operation.\n            ')}

    def __init__(self, *args, reward, **kwargs):
        super().__init__(*args, **kwargs)
        self.reward = reward

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if not subject.is_sim:
            logger.error('Attempting to apply Reward Loot Op to {} which is not a Sim.', subject)
            return False
        self.reward.give_reward(subject)
        return True
