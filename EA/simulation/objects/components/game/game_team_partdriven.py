from objects.components.game.game_team import GameTeamfrom sims4.tuning.tunable import TunableVariant, HasTunableSingletonFactory
class GameTeamPartDriven(GameTeam):

    class _PartRequirementAdjacent(HasTunableSingletonFactory):

        def is_on_same_team(self, part_a, part_b):
            if part_a is None or not part_a.is_part:
                return False
            if part_b is None or not part_b.is_part:
                return False
            return part_a is part_b or any(part_a is adjacent_part for adjacent_part in part_b.adjacent_parts_gen())

    FACTORY_TUNABLES = {'part_requirement': TunableVariant(description='\n            Define how part relationships define team structure.\n            ', adjacent=_PartRequirementAdjacent.TunableFactory(), default='adjacent')}

    def add_player(self, game, sim):
        target_object = game.get_target_object_for_sim(sim)
        for team in game._teams:
            if any(self.part_requirement.is_on_same_team(target_object, game.get_target_object_for_sim(other_sim)) for other_sim in team.players):
                team.players.append(sim)
                return
        game.add_team([sim])

    def can_be_on_same_team(self, target_a, target_b):
        return self.part_requirement.is_on_same_team(target_a, target_b)

    def can_be_on_opposing_team(self, target_a, target_b):
        return not self.can_be_on_same_team(target_a, target_b)

    def remove_player(self, game, sim):
        for team in game._teams:
            if sim in team.players:
                team.players.remove(sim)
                if not team.players:
                    game._teams.remove(team)
                break
