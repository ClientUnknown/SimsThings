from _collections import defaultdictfrom interactions.liability import Liability
class GameTransitionDestinationNodeValidator:

    def __init__(self, game_type, teams=None, **kwargs):
        super().__init__(**kwargs)
        self._game_type = game_type
        self._teams = list(teams) if teams is not None else None
        self._destinations = defaultdict(set)
        self._interactions = set()

    def register_interaction(self, interaction):
        self._interactions.add(interaction)

    def transfer_interaction(self, old_interaction, new_interaction):
        self._interactions.discard(old_interaction)
        self._interactions.add(new_interaction)
        if new_interaction.sim in self._destinations:
            self._destinations[new_interaction.sim].discard(old_interaction.target)
            if new_interaction.target.is_part:
                self._destinations[new_interaction.sim].add(new_interaction.target)

    def unregister_interaction(self, interaction):
        self._interactions.discard(interaction)
        if self._teams is not None:
            for team in self._teams:
                if interaction.sim in team:
                    team.discard(interaction.sim)
                    if not team:
                        self._teams.remove(team)
                    break
            if interaction.sim in self._destinations:
                del self._destinations[interaction.sim]
        if not self._interactions:
            interaction.target.clear_active_game_transition_node_validator(transition_node_validator=self)

    def invalidate_registered_interactions(self):
        for interaction in self._interactions:
            transition_liability = interaction.get_liability(GameTransitionLiability.LIABILITY_TOKEN)
            if transition_liability is None:
                pass
            else:
                transition_liability.set_game_transition_node_validator(interaction, game_type=self._game_type)

    def _add_sim_to_team_if_necessary(self, sim):
        if self._teams is None:
            self._teams = []
        if any(sim in team for team in self._teams):
            return
        if len(self._teams) < self._game_type.teams_per_game.upper_bound:
            self._teams.append(set((sim,)))
        else:
            team = min(self._teams, key=len)
            team.add(sim)

    def is_valid_destination(self, sim, target):
        self._add_sim_to_team_if_necessary(sim)
        if target in self._destinations[sim]:
            return True
        for (other_sim, other_targets) in self._destinations.items():
            is_on_same_team = any(sim in team and other_sim in team for team in self._teams)
            if is_on_same_team:
                if not all(self._game_type.can_be_on_same_team(target, other_target) for other_target in other_targets):
                    return False
                    if not all(self._game_type.can_be_on_opposing_team(target, other_target) for other_target in other_targets):
                        return False
            elif not all(self._game_type.can_be_on_opposing_team(target, other_target) for other_target in other_targets):
                return False
        self._destinations[sim].add(target)
        return True

class GameTransitionLiability(Liability):
    LIABILITY_TOKEN = 'GameTransitionLiability'

    def __init__(self, interaction, *args, game_transition_destination_node_validator=None, game_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._interaction = interaction
        if game_transition_destination_node_validator is None:
            game_transition_destination_node_validator = self._interaction.interaction_parameters.get('game_transition_destination_node_validator')
        self.set_game_transition_node_validator(interaction, game_transition_destination_node_validator, game_type)

    def set_game_transition_node_validator(self, interaction, game_transition_destination_node_validator=None, game_type=None):
        if interaction.is_finishing:
            return
        if game_transition_destination_node_validator is None:
            game_transition_destination_node_validator = self._interaction.target.get_game_transition_destination_node_validator(interaction, game_type)
        self._game_transition_destination_node_validator = game_transition_destination_node_validator
        self._game_transition_destination_node_validator.register_interaction(interaction)
        self._interaction.target.set_active_game_transition_node_validator(self._game_transition_destination_node_validator)

    def _add_validator_test(self, interaction):
        interaction.additional_destination_validity_tests.append(lambda target: self._game_transition_destination_node_validator.is_valid_destination(interaction.sim, target))

    def on_add(self, interaction):
        self._add_validator_test(interaction)

    def release(self):
        self._game_transition_destination_node_validator.unregister_interaction(self._interaction)
        return super().release()

    def transfer(self, interaction):
        self._game_transition_destination_node_validator.transfer_interaction(self._interaction, interaction)
        self._add_validator_test(interaction)
        self._interaction = interaction
