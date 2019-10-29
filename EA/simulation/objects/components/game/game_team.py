from sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory
class GameTeam(HasTunableSingletonFactory, AutoFactoryInit):

    def add_player(self, game, sim):
        raise NotImplementedError

    def can_be_on_same_team(self, target_a, target_b):
        return True

    def can_be_on_opposing_team(self, target_a, target_b):
        return True

    def remove_player(self, game, sim):
        raise NotImplementedError
