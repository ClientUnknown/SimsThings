import itertoolsimport operatorimport randomfrom protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom element_utils import build_critical_section_with_finallyfrom event_testing.resolver import SingleObjectResolverfrom interactions import ParticipantTypefrom interactions.context import InteractionSourcefrom interactions.utils.loot_ops import BaseGameLootOperationfrom objects.client_object_mixin import ClientObjectMixinfrom objects.components import Component, types, componentmethodfrom objects.components.game.game_card_battle_behavior import CardBattleBehaviorfrom objects.components.game.game_team_autobalanced import GameTeamAutoBalancedfrom objects.components.game.game_team_partdriven import GameTeamPartDrivenfrom objects.components.game.game_transition_liability import GameTransitionDestinationNodeValidatorfrom objects.components.state import ObjectStateValuefrom objects.system import create_objectfrom sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuningfrom sims4.tuning.instances import TunedInstanceMetaclassfrom sims4.tuning.tunable import TunableFactory, TunableInterval, TunableList, TunableReference, Tunable, TunableTuple, TunableRange, OptionalTunable, TunableVariant, HasTunableFactory, HasTunableReferencefrom statistics.skill import Skillfrom statistics.statistic import Statisticfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport enumimport gsi_handlersimport interactions.utilsimport servicesimport sims4.loglogger = sims4.log.Logger('GameComponent')
class GameTargetType(enum.Int):
    OPPOSING_SIM = 0
    OPPOSING_TEAM = 1
    ALL_OPPOSING_TEAMS = 2

class GameRules(HasTunableReference, metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.GAME_RULESET)):
    ENDING_CONDITION_SCORE = 0
    ENDING_CONDITION_ROUND = 1
    INSTANCE_TUNABLES = {'game_name': TunableLocalizedStringFactory(description='\n            Name of the game.\n            ', default=1860708663), 'team_strategy': TunableVariant(description='\n            Define how Sims are distributed across teams.\n            ', auto_balanced=GameTeamAutoBalanced.TunableFactory(), part_driven=GameTeamPartDriven.TunableFactory(), default='auto_balanced'), 'teams_per_game': TunableInterval(description='\n            An interval specifying the number of teams allowed per game.\n            \n            Joining Sims are put on a new team if the maximum number of teams\n            has not yet been met, otherwise they are put into the team with the\n            fewest number of players.\n            ', tunable_type=int, default_lower=2, default_upper=2, minimum=1), 'players_per_game': TunableInterval(description='\n            An interval specifying the number of players allowed per game.\n            \n            If the maximum number of players has not been met, Sims can\n            continue to join a game.  Joining Sims are put on a new team if the\n            maximum number of teams as specified in the "teams_per_game"\n            tunable has not yet been met, otherwise they are put into the team\n            with the fewest number of players.\n            ', tunable_type=int, default_lower=2, default_upper=2, minimum=1), 'players_per_turn': TunableRange(description='\n            An integer specifying number of players from the active team who\n            take their turn at one time.\n            ', tunable_type=int, default=1, minimum=1), 'initial_state': ObjectStateValue.TunableReference(description="\n            The game's starting object state.\n            ", allow_none=True), 'score_info': TunableTuple(description="\n            Tunables that affect the game's score.\n            ", ending_condition=TunableVariant(description='\n                The condition under which the game ends.\n                ', score_based=TunableTuple(description='\n                    A game that ends when one of the teams wins by reaching a \n                    certain score first\n                    ', locked_args={'end_condition': ENDING_CONDITION_SCORE}, winning_score=Tunable(description='\n                        Score required to win.\n                        ', tunable_type=int, default=100)), round_based=TunableTuple(description='\n                    A game that ends after a certain number of rounds.  The Team\n                    with the highest score at that point wins.\n                    ', locked_args={'end_condition': ENDING_CONDITION_ROUND}, rounds=Tunable(description='\n                        Length of game (in rounds).\n                        ', tunable_type=int, default=3)), default='score_based'), score_increase=TunableInterval(description='\n                An interval specifying the minimum and maximum score increases\n                possible in one turn. A random value in this interval will be\n                generated each time score loot is given.\n                ', tunable_type=int, default_lower=35, default_upper=50, minimum=0), allow_scoring_for_non_active_teams=Tunable(description='\n                If checked, any Sim may score, even if their team is not\n                considered active.\n                ', tunable_type=bool, default=False), skill_level_bonus=Tunable(description="\n                A bonus number of points based on the Sim's skill level in the\n                relevant_skill tunable that will be added to score_increase.\n                \n                ex: If this value is 2 and the Sim receiving score has a\n                relevant skill level of 4, they will receive 8 (2 * 4) extra\n                points.\n                ", tunable_type=float, default=2), relevant_skill=Skill.TunableReference(description="\n                The skill relevant to this game.  Each Sim's proficiency in\n                this skill will effect the score increase they get.\n                ", allow_none=True), use_effective_skill_level=Tunable(description='\n                If checked, we will use the effective skill level rather than\n                the actual skill level of the relevant_skill tunable.\n                ', tunable_type=bool, default=True), progress_stat=Statistic.TunableReference(description='\n                The statistic that advances the progress state of this game.\n                ', allow_none=True), persist_high_score=Tunable(description='\n                If checked, the high score and the team Sim ids will be\n                saved onto the game component.\n                ', tunable_type=bool, default=False)), 'clear_score_on_player_join': Tunable(description='\n            Tunable that, when checked, will clear the game score when a player joins.\n            \n            This essentially resets the game.\n            ', tunable_type=bool, default=False), 'alternate_target_object': OptionalTunable(description='\n            Tunable that, when enabled, means the game should create an alternate object\n            in the specified slot on setup that will be modified as the game goes on\n            and destroyed when the game ends.\n            ', tunable=TunableTuple(target_game_object=TunableReference(description='\n                    The definition of the object that will be created/destroyed/altered\n                    by the game.\n                    ', manager=services.definition_manager()), parent_slot=TunableVariant(description='\n                    The slot on the parent object where the target_game_object object should go. This\n                    may be either the exact name of a bone on the parent object or a\n                    slot type, in which case the first empty slot of the specified type\n                    in which the child object fits will be used.\n                    ', by_name=Tunable(description='\n                        The exact name of a slot on the parent object in which the target\n                        game object should go.  \n                        ', tunable_type=str, default='_ctnm_'), by_reference=TunableReference(description='\n                        A particular slot type in which the target game object should go.  The\n                        first empty slot of this type found on the parent will be used.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE))), destroy_at_end=Tunable(description='\n                    If True, the alternate target object will get destroyed at the end of the game.\n                    ', tunable_type=bool, default=True))), 'game_over_notification': OptionalTunable(description="\n            If enabled, when any Sim involved in the game is a player-controlled\n            Sim, display a notification when the game is over.\n            \n            NOTE: As of now, this only triggers when there are *exactly* two\n            teams. To support more teams, we'll need to extend the possible\n            string permutation.\n            ", tunable=TunableTuple(one_v_one=TunableUiDialogNotificationSnippet(description="\n                    The notification to show when the game is 1v1.\n                    \n                     * Token 0 is the object the game is being played on\n                     * Token 1 is the winner\n                     * Token 2 is the loser\n                     * Token 3 is the winner's score\n                     * Token 4 is the loser's score\n                    "), one_v_many_winner=TunableUiDialogNotificationSnippet(description="\n                    The notification to show when the game is 1 v many, and the\n                    single Sim is the winner.\n                    \n                    * Token 0 is the object the game is being played on\n                    * Token 1 is the winner\n                    * Token 2 is a list of losers (Alice, Bob, and Carol)\n                    * Token 3 is the winner's score\n                    * Token 4 is the loser's score\n                    "), one_v_many_loser=TunableUiDialogNotificationSnippet(description="\n                    The notification to show when the game is 1 v many, and the\n                    single Sim is the loser.\n                    \n                    * Token 0 is the object the game is being played on\n                    * Token 1 is a list of winners (Alice, Bob, and Carol)\n                    * Token 2 is the loser\n                    * Token 3 is the winner's score\n                    * Token 4 is the loser's score\n                    "), many_v_many=TunableUiDialogNotificationSnippet(description="\n                    The notification to show when the game is many v many.\n                    \n                    * Token 0 is the object the game is being played on\n                    * Token 1 is a list of winners (Alice and Bob)\n                    * Token 2 is a list of losers (Carol, Dan, and Erin)\n                    * Token 3 is the winner's score\n                    * Token 4 is the loser's score\n                    "))), 'game_over_winner_only_notification': OptionalTunable(description='\n            If enabled, when any Sim involved in the game is a player-controlled\n            Sim, display a notification when the game is over.\n            \n            NOTE: This will show only the winners of the game with the highest \n            score. The winners can be more than one team if they have same \n            score.\n            ', tunable=TunableTuple(play_alone=TunableUiDialogNotificationSnippet(description="\n                    The notification to show when Sim play alone.\n                    \n                    * Token 0 is the object the game is being played on\n                    * Token 1 is the Sim's name\n                    * Token 2 is the Sim's score\n                    "), winner=TunableUiDialogNotificationSnippet(description="\n                    The notification to show when the game has 1 team winner.\n                    \n                    * Token 0 is the object the game is being played on\n                    * Token 1 is the winner\n                    * Token 2 is the winner's score\n                    "))), 'additional_game_behavior': OptionalTunable(description='\n            If enabled additional behavior will be run for this type of game\n            on multiple phases like creating destroying additional objects on \n            setup of end phases.\n            ', tunable=TunableVariant(description="\n                Variant of type of games that will add very specific behavior\n                to the game component.\n                e.g. Card battle behavior will create cards and destroy them\n                depending on each actor's inventory.\n                ", card_battle=CardBattleBehavior.TunableFactory(), default='card_battle'))}

    def __init__(self, game_component, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._game_component = game_component
        self.additional_game_behavior = self.additional_game_behavior() if self.additional_game_behavior is not None else None

    def add_player(self, sim):
        self.team_strategy.add_player(self._game_component, sim)

    @classmethod
    def can_be_on_same_team(cls, target_a, target_b):
        return cls.team_strategy.can_be_on_same_team(target_a, target_b)

    @classmethod
    def can_be_on_opposing_team(cls, target_a, target_b):
        return cls.team_strategy.can_be_on_opposing_team(target_a, target_b)

    def remove_player(self, sim):
        self.team_strategy.remove_player(self._game_component, sim)

class GameTeam:

    def __init__(self, players):
        self.players = players
        self.score = 0
        self.next_player = 0
        self.rounds_taken = 0

class GameComponent(Component, HasTunableFactory, component_name=types.GAME_COMPONENT, persistence_key=protocols.PersistenceMaster.PersistableData.GameComponent):
    FACTORY_TUNABLES = {'games': TunableList(description='\n            All the games that can be played on this object.\n            ', tunable=GameRules.TunableReference(description='\n                A game that can be played on this object.\n                ', pack_safe=True))}

    def __init__(self, owner, games, **kwargs):
        super().__init__(owner)
        self.owner = owner
        self.games = games
        self._teams = []
        self.active_sims = []
        self.challenge_sims = None
        self._game_targets = {}
        self.active_team = None
        self.round = 0
        self.winning_team = None
        self.losing_team = None
        self.current_game = None
        self.has_started = False
        self.requires_setup = False
        self.target_object = None
        self.has_user_directed = False
        self.high_score = None
        self.high_score_sim_ids = None
        self._active_transition_destination_node_validator = None

    @property
    def number_of_players(self):
        return sum(len(team.players) for team in self._teams)

    @property
    def number_of_teams(self):
        return len(self._teams)

    def get_team_name(self, team_number):
        return 'Team #' + str(team_number + 1)

    def is_joinable(self, sim=None):
        if self.current_game is None or self.number_of_players < self.current_game.players_per_game.upper_bound:
            if sim is None:
                return True
            for team in self._teams:
                if sim in team.players:
                    return False
            return True
        return False

    def is_joinable_autonomously_after_user_directed(self, context):
        if context.source == InteractionSource.AUTONOMY and self.has_user_directed:
            return False
        return True

    @property
    def game_state_dirty(self):
        if self.target_object is None:
            return False
        elif self.current_game.initial_state is not None and not self.target_object.state_component.state_value_active(self.current_game.initial_state):
            return True
        return False

    @property
    def game_has_ended(self):
        if self.current_game is not None and self.winning_team is None:
            return False
        return True

    @property
    def progress_stat(self):
        score_info = self.current_game.score_info
        if score_info.ending_condition.end_condition == GameRules.ENDING_CONDITION_SCORE:
            max_score = max(team.score for team in self._teams)
            progress = max_score/self.current_game.score_info.ending_condition.winning_score
        else:
            progress = self.round/self.current_game.score_info.ending_condition.rounds
        progress *= self.current_game.score_info.progress_stat.max_value_tuning
        return progress

    def get_game_target(self, actor_sim=None):
        if self.number_of_teams <= 1 or self.active_team is None:
            return
        if actor_sim is None:
            actor_team = self.active_team
        else:
            for (actor_team, team) in enumerate(self._teams):
                if actor_sim in team.players:
                    break
            return
        random_team = random.randrange(self.number_of_teams - 1)
        if random_team >= actor_team:
            random_team += 1
        random_sim = random.choice(self._teams[random_team].players)
        return random_sim

    def get_target_object_for_sim(self, sim):
        return self._game_targets.get(sim)

    @componentmethod
    def get_game_transition_destination_node_validator(self, interaction, game_type):
        if self._active_transition_destination_node_validator is not None:
            return self._active_transition_destination_node_validator
        transition_destination_node_validator = GameTransitionDestinationNodeValidator(game_type)
        return transition_destination_node_validator

    @componentmethod
    def set_active_game_transition_node_validator(self, transition_destination_node_validator):
        if self._active_transition_destination_node_validator is not None:
            return
        self._active_transition_destination_node_validator = transition_destination_node_validator

    @componentmethod
    def clear_active_game_transition_node_validator(self, transition_node_validator=None):
        if self._active_transition_destination_node_validator is None:
            return
        if transition_node_validator is not None and self._active_transition_destination_node_validator is not transition_node_validator:
            return
        transition_destination_node_validator = self._active_transition_destination_node_validator
        self._active_transition_destination_node_validator = None
        transition_destination_node_validator.invalidate_registered_interactions()

    def _build_active_sims(self):
        del self.active_sims[:]
        (self.active_sims, next_player) = self._generate_active_sims()
        self._teams[self.active_team].next_player = next_player

    def _generate_active_sims(self):
        temporary_active_sims = []
        team = self._teams[self.active_team].players
        next_player = self._teams[self.active_team].next_player
        next_player %= len(team)
        i = 0
        while i < self.current_game.players_per_turn:
            temporary_active_sims.append(team[next_player])
            i += 1
            next_player += 1
            next_player %= len(team)
        return (temporary_active_sims, next_player)

    def reset_high_scores(self):
        self.high_score = None
        self.high_score_sim_ids = None

    def clear_scores(self):
        for team in self._teams:
            team.score = 0
            team.rounds_taken = 0
        self.winning_team = None
        self.losing_team = None
        self.round = 0
        if gsi_handlers.game_component_handlers.game_log_archiver.enabled:
            gsi_handlers.game_component_handlers.archive_game_log_entry(self.target_object, 'Cleared all scores.')

    @componentmethod
    def get_display_number(self):
        if not self._teams:
            return []
        return [int(team.score) for team in self._teams]

    def add_team(self, sims):
        if self.current_game is None:
            logger.error('Cannot add a team when no game is running.', owner='tastle')
            return
        if self.number_of_teams >= self.current_game.teams_per_game.upper_bound:
            logger.error('Cannot add a team to a game that already has the maximum number of allowed teams.', owner='tastle')
            return
        self._teams.append(GameTeam(sims))
        if gsi_handlers.game_component_handlers.game_log_archiver.enabled:
            team_name = self.get_team_name(len(self._teams) - 1)
            team_str = 'Added team: ' + team_name
            gsi_handlers.game_component_handlers.archive_game_log_entry(self.target_object, team_str)

    def add_player(self, sim, target, source=None):
        if self.current_game is None:
            logger.error('Cannot add a player when no game is running.', owner='tastle')
            return
        if self.number_of_players >= self.current_game.players_per_game.upper_bound:
            logger.error('Cannot add any players to a game that already has the maximum number of allowed players.', owner='tastle')
            return
        if gsi_handlers.game_component_handlers.game_log_archiver.enabled:
            player_str = 'Added player: ' + str(sim)
            gsi_handlers.game_component_handlers.archive_game_log_entry(self.target_object, player_str)
        if not self.has_started:
            self.requires_setup = True
        self._game_targets[sim] = target
        self.current_game.add_player(sim)
        if source == InteractionSource.PIE_MENU:
            self.has_user_directed = True
        if self.game_state_dirty and source is not None and self.current_game.clear_score_on_player_join:
            self.clear_scores()
        if self.current_game.additional_game_behavior is not None:
            self.current_game.additional_game_behavior.on_player_added(sim, target)

    def move_player(self, sim, target):
        self._game_targets[sim] = target

    def remove_player(self, sim):
        if self.current_game is None:
            return
        if self.current_game.additional_game_behavior is not None:
            self.current_game.additional_game_behavior.on_player_removed(sim)
        self.current_game.remove_player(sim)
        if sim in self._game_targets:
            del self._game_targets[sim]
        if self.number_of_players < self.current_game.players_per_game.lower_bound:
            self.has_started = False
            self.has_user_directed = False
            self.active_team = None
            del self.active_sims[:]
            if self.game_state_dirty:
                self.requires_setup = True
        if not (self.has_started and self.current_game is not None and self.number_of_teams):
            self.end_game()
        elif self.active_team is not None and self.active_team <= self.number_of_teams:
            self.active_team = random.randrange(self.number_of_teams)
            self._build_active_sims()

    def add_challenger(self, sim):
        if self.challenge_sims is None:
            self.challenge_sims = set()
        self.challenge_sims.add(sim)

    def remove_challenger(self, sim):
        if self.challenge_sims is not None:
            self.challenge_sims.discard(sim)

    def is_sim_turn(self, sim):
        if self.active_team is not None and self.can_play() and sim in self.active_sims:
            return True
        return False

    def can_play(self):
        if self.current_game is None:
            return False
        team_len = self.number_of_teams
        player_len = self.number_of_players
        teams_per_game = self.current_game.teams_per_game
        if not (teams_per_game.lower_bound <= team_len and team_len <= teams_per_game.upper_bound):
            return False
        else:
            players_per_game = self.current_game.players_per_game
            if not (players_per_game.lower_bound <= player_len and player_len <= players_per_game.upper_bound):
                return False
        return True

    def take_turn(self, sim=None):
        if gsi_handlers.game_component_handlers.game_log_archiver.enabled and self.active_team is not None:
            team_name = self.get_team_name(self.active_team)
            turn_str = str(sim) + ' (' + team_name + ') ' + 'just finished taking their turn'
            gsi_handlers.game_component_handlers.archive_game_log_entry(self.target_object, turn_str)
        if not self.can_play():
            return False
        if sim and sim in self.active_sims:
            self.active_sims.remove(sim)
        if self.active_sims:
            return False
        if self.active_team is None:
            self.clear_scores()
            self.active_team = random.randrange(self.number_of_teams)
            self.has_started = True
        else:
            self._teams[self.active_team].rounds_taken += 1
            self.active_team += 1
            self.active_team %= self.number_of_teams
            self.round = self._teams[self.active_team].rounds_taken
            score_info = self.current_game.score_info
            if score_info.ending_condition.end_condition == GameRules.ENDING_CONDITION_ROUND:
                if self.round >= score_info.ending_condition.rounds:
                    self.winning_team = max(self._teams, key=operator.attrgetter('score'))
                    self.losing_team = min(self._teams, key=operator.attrgetter('score'))
                self.update_high_score()
                if score_info.progress_stat is not None:
                    self.target_object.statistic_tracker.set_value(score_info.progress_stat, self.progress_stat)
        self._build_active_sims()
        return True

    def set_current_game(self, game_type):
        if self.current_game is not None:
            self.end_game()
        self.current_game = game_type(self)
        if self.current_game.alternate_target_object is None:
            self.target_object = self.owner
        if gsi_handlers.game_component_handlers.game_log_archiver.enabled:
            game_str = 'Setting current game to ' + str(self.current_game)
            gsi_handlers.game_component_handlers.archive_game_log_entry(self.target_object, game_str)
            target_str = 'Target Object is ' + str(self.target_object)
            gsi_handlers.game_component_handlers.archive_game_log_entry(self.target_object, target_str)

    def increase_score_by_points(self, sim, score_increase):
        if self.target_object is None:
            return
        for (team_number, team) in enumerate(self._teams):
            if sim not in team.players:
                pass
            else:
                score_info = self.current_game.score_info
                if score_info.allow_scoring_for_non_active_teams or self.active_team is not None and team_number != self.active_team:
                    return
                team.score += score_increase
                if gsi_handlers.game_component_handlers.game_log_archiver.enabled:
                    team_name = self.get_team_name(team_number)
                    increase_str = str(sim) + ' scored ' + str(score_increase) + ' points for ' + team_name
                    gsi_handlers.game_component_handlers.archive_game_log_entry(self.target_object, increase_str)
                    if score_info.ending_condition.end_condition == GameRules.ENDING_CONDITION_SCORE:
                        score_str = 'Score for ' + team_name + ' is now ' + str(team.score) + ' / ' + str(score_info.ending_condition.winning_score)
                    else:
                        score_str = 'Score for ' + team_name + ' is now ' + str(team.score)
                    gsi_handlers.game_component_handlers.archive_game_log_entry(self.target_object, score_str)
                if score_info.ending_condition.end_condition == GameRules.ENDING_CONDITION_SCORE:
                    if team.score >= score_info.ending_condition.winning_score:
                        self.winning_team = self._teams[team_number]
                        self.losing_team = min(self._teams, key=operator.attrgetter('score'))
                        if gsi_handlers.game_component_handlers.game_log_archiver.enabled:
                            team_name = self.get_team_name(team_number)
                            win_str = team_name + ' has won the game'
                            gsi_handlers.game_component_handlers.archive_game_log_entry(self.target_object, win_str)
                    self.update_high_score()
                    if score_info.progress_stat is not None:
                        self.target_object.statistic_tracker.set_value(score_info.progress_stat, self.progress_stat)
                return
        logger.error('The given Sim {} is not a member of any team, so we cannot increase its score.', sim, owner='tastle')

    def increase_score(self, sim):
        if self.current_game is None:
            return
        score_info = self.current_game.score_info
        score_increase = sims4.random.uniform(score_info.score_increase.lower_bound, score_info.score_increase.upper_bound)
        relevant_skill = score_info.relevant_skill
        if relevant_skill is not None:
            skill_or_skill_type = sim.get_stat_instance(relevant_skill) or relevant_skill
            if score_info.use_effective_skill_level:
                skill_level = sim.get_effective_skill_level(skill_or_skill_type)
            else:
                skill_level = skill_or_skill_type.get_user_value()
            score_increase += score_info.skill_level_bonus*skill_level
        self.increase_score_by_points(sim, score_increase)

    def update_high_score(self):
        if self.current_game.score_info.persist_high_score:
            high_score_team = max(self._teams, key=operator.attrgetter('score'))
            if self.high_score is None or high_score_team.score > self.high_score:
                self.high_score = high_score_team.score
                self.high_score_sim_ids = [sim.id for sim in high_score_team.players]

    def end_game(self):
        if self.current_game is not None and self.current_game.additional_game_behavior is not None:
            self.current_game.additional_game_behavior.on_game_ended(self.winning_team)
        if gsi_handlers.game_component_handlers.game_log_archiver.enabled:
            game_over_str = 'Game ' + str(self.current_game) + ' has ended'
            gsi_handlers.game_component_handlers.archive_game_log_entry(self.target_object, game_over_str)
        if self.target_object is not None and self.target_object is not self.owner and (self.current_game.alternate_target_object is None or self.current_game.alternate_target_object.destroy_at_end):
            self.target_object.destroy(source=self.target_object, cause='game ended', fade_duration=ClientObjectMixin.FADE_DURATION)
        self.target_object = None
        self.current_game = None
        self.active_team = None
        self.winning_team = None
        self.losing_team = None
        self.has_started = False
        self.has_user_directed = False
        del self._teams[:]
        del self.active_sims[:]
        self.challenge_sims = None
        self._game_targets.clear()
        self.clear_active_game_transition_node_validator()

    def setup_game(self):
        self.requires_setup = False
        if self.target_object is not None:
            return
        if gsi_handlers.game_component_handlers.game_log_archiver.enabled:
            setup_str = 'Game ' + str(self.current_game) + ' has been set up'
            gsi_handlers.game_component_handlers.archive_game_log_entry(self.target_object, setup_str)
        self.clear_scores()
        slot_hash = None
        alternate_target_object = self.current_game.alternate_target_object
        parent_slot = alternate_target_object.parent_slot
        if isinstance(parent_slot, str):
            slot_hash = sims4.hash_util.hash32(parent_slot)
        for child in self.owner.children:
            if child.definition is alternate_target_object.target_game_object:
                slot = child.parent_slot
                if slot_hash is not None:
                    if slot_hash == slot.slot_name_hash:
                        self.target_object = child
                        return
                        if parent_slot in slot.slot_types:
                            self.target_object = child
                            return
                elif parent_slot in slot.slot_types:
                    self.target_object = child
                    return
        created_object = create_object(alternate_target_object.target_game_object)
        self.target_object = created_object
        self.owner.slot_object(parent_slot=parent_slot, slotting_object=created_object)

    def component_anim_overrides_gen(self):
        if self.current_game is not None and self.current_game.additional_game_behavior is not None:
            yield from self.current_game.additional_game_behavior.additional_anim_overrides_gen()

    def save(self, persistence_master_message):
        persistable_data = protocols.PersistenceMaster.PersistableData()
        persistable_data.type = protocols.PersistenceMaster.PersistableData.GameComponent
        game_component_save = persistable_data.Extensions[protocols.PersistableGameComponent.persistable_data]
        if self.high_score is not None:
            game_component_save.high_score = self.high_score
        if self.high_score_sim_ids is not None:
            game_component_save.high_score_sim_ids.extend(self.high_score_sim_ids)
        persistence_master_message.data.extend([persistable_data])

    def load(self, game_component_message):
        game_component_data = game_component_message.Extensions[protocols.PersistableGameComponent.persistable_data]
        if game_component_data.high_score:
            self.high_score = game_component_data.high_score
        if game_component_data.high_score_sim_ids:
            self.high_score_sim_ids = [sim_id for sim_id in game_component_data.high_score_sim_ids]

def get_game_references(interaction):
    target_group = interaction.get_participant(ParticipantType.SocialGroup)
    target_object = target_group.anchor if target_group is not None else None
    if target_object is not None:
        game = target_object.game_component
        if game is not None:
            return (game, target_object)
        else:
            target_object = interaction.get_participant(ParticipantType.Object)
            if target_object is not None:
                game = target_object.game_component
                if game is not None:
                    return (game, target_object)
    else:
        target_object = interaction.get_participant(ParticipantType.Object)
        if target_object is not None:
            game = target_object.game_component
            if game is not None:
                return (game, target_object)
    return (None, None)

class SetupGame(BaseGameLootOperation):

    @property
    def loot_type(self):
        return interactions.utils.LootType.GAME_SETUP

    def _apply_to_subject_and_target(self, subject, target, resolver):
        (game, _) = get_game_references(resolver)
        if game is None:
            return False
        game.setup_game()

class TakeTurn(BaseGameLootOperation):

    @property
    def loot_type(self):
        return interactions.utils.LootType.TAKE_TURN

    def _apply_to_subject_and_target(self, subject, target, resolver):
        (game, _) = get_game_references(resolver)
        if game is None:
            return False
        subject_obj = self._get_object_from_recipient(subject)
        game.take_turn(subject_obj)
        return True

class TeamScore(BaseGameLootOperation):

    @property
    def loot_type(self):
        return interactions.utils.LootType.TEAM_SCORE

    def _apply_to_subject_and_target(self, subject, target, resolver):
        (game, _) = get_game_references(resolver)
        if game is None:
            return False
        subject_obj = self._get_object_from_recipient(subject)
        game.increase_score(subject_obj)
        return True

class TeamScorePoints(BaseGameLootOperation):

    def __init__(self, score_increase, score_increase_from_stat, **kwargs):
        super().__init__(**kwargs)
        self.score_increase = score_increase
        self.score_increase_from_stat = score_increase_from_stat

    @property
    def loot_type(self):
        return interactions.utils.LootType.TEAM_SCORE

    def _apply_to_subject_and_target(self, subject, target, resolver):
        (game, _) = get_game_references(resolver)
        if game is None:
            return False
        subject_obj = self._get_object_from_recipient(subject)
        if self.score_increase_from_stat is not None:
            stat = subject_obj.get_statistic(self.score_increase_from_stat)
            if stat is None:
                logger.error('Failed to find statistic {} from {}.', self.score_increase_from_stat, subject_obj, owner='mkartika')
                return False
            score_increase = stat.get_value()
        else:
            score_increase = sims4.random.uniform(self.score_increase.lower_bound, self.score_increase.upper_bound)
        game.increase_score_by_points(subject_obj, score_increase)
        return True

    FACTORY_TUNABLES = {'score_increase': TunableInterval(description='\n            An interval specifying the minimum and maximum score increases\n            from this loot. A random value in this interval will be\n            generated each time this loot is given.\n            ', tunable_type=int, default_lower=35, default_upper=50, minimum=0), 'score_increase_from_stat': OptionalTunable(description="\n            If enabled, the score will be increased by this statistic value\n            instead of by 'Score Increase' interval value.\n            ", tunable=TunableReference(description='\n                The stat we are operating on.\n                ', manager=services.statistic_manager()))}

class GameOver(BaseGameLootOperation):

    @property
    def loot_type(self):
        return interactions.utils.LootType.GAME_OVER

    def _show_game_over_notification(self, game):
        game_over_notification = game.current_game.game_over_notification
        if game_over_notification is None:
            return
        if game.number_of_teams != 2:
            return
        winner_sims = tuple(game.winning_team.players)
        loser_sims = tuple(game.losing_team.players)
        for selectable_sim in itertools.chain(winner_sims, loser_sims):
            if selectable_sim.is_selectable:
                break
        return
        winning_score = game.winning_team.score
        losing_score = game.losing_team.score
        if len(winner_sims) == 1 and len(loser_sims) == 1:
            notification_type = game_over_notification.one_v_one
            winner_token = winner_sims[0]
            loser_token = loser_sims[0]
        elif len(winner_sims) == 1:
            notification_type = game_over_notification.one_v_many_winner
            winner_token = winner_sims[0]
            loser_token = LocalizationHelperTuning.get_comma_separated_sim_names(*loser_sims)
        elif len(loser_sims) == 1:
            notification_type = game_over_notification.one_v_many_loser
            winner_token = LocalizationHelperTuning.get_comma_separated_sim_names(*winner_sims)
            loser_token = loser_sims[0]
        else:
            notification_type = game_over_notification.many_v_many
            winner_token = LocalizationHelperTuning.get_comma_separated_sim_names(*winner_sims)
            loser_token = LocalizationHelperTuning.get_comma_separated_sim_names(*loser_sims)
        notification = notification_type(selectable_sim, resolver=SingleObjectResolver(game.owner))
        notification.show_dialog(additional_tokens=(winner_token, loser_token, winning_score, losing_score))

    def _show_game_over_winner_only_notification(self, game):
        game_over_winner_only_notification = game.current_game.game_over_winner_only_notification
        if game_over_winner_only_notification is None:
            return
        for selectable_sim in itertools.chain.from_iterable([team.players for team in game._teams]):
            if selectable_sim.is_selectable:
                break
        return
        game.winning_team = max(game._teams, key=operator.attrgetter('score'))
        winner_sims = tuple(game.winning_team.players)
        winning_score = game.winning_team.score
        if game.number_of_players == 1:
            notification_type = game_over_winner_only_notification.play_alone
            if winner_sims:
                winner_token = winner_sims[0]
            else:
                all_players = [player for team in game._teams for player in team.players]
                winner_token = all_players[0]
                logger.error('Winner Sims {} is empty', winner_sims, owner='mkartika')
        else:
            notification_type = game_over_winner_only_notification.winner
            if len(winner_sims) == 1:
                winner_token = winner_sims[0]
            else:
                winner_token = LocalizationHelperTuning.get_comma_separated_sim_names(*winner_sims)
        notification = notification_type(selectable_sim, resolver=SingleObjectResolver(game.owner))
        notification.show_dialog(additional_tokens=(winner_token, winning_score))

    def _apply_to_subject_and_target(self, subject, target, resolver):
        (game, _) = get_game_references(resolver)
        if game is None:
            return False
        elif game.winning_team is not None:
            self._show_game_over_notification(game)
            self._show_game_over_winner_only_notification(game)
            game.end_game()
            return True
        return False

class ResetHighScore(BaseGameLootOperation):

    @property
    def loot_type(self):
        return interactions.utils.LootType.GENERIC

    def _apply_to_subject_and_target(self, subject, target, resolver):
        (game, _) = get_game_references(resolver)
        if game is None:
            return False
        game.reset_high_scores()
        return True

class ResetGame(BaseGameLootOperation):

    @property
    def loot_type(self):
        return interactions.utils.LootType.GAME_RESET

    def _apply_to_subject_and_target(self, subject, target, resolver):
        (game, _) = get_game_references(resolver)
        if game is None:
            return False
        game.clear_scores()

class TunableSetGameTarget(TunableFactory):

    @staticmethod
    def factory(interaction, sequence=()):
        interaction = interaction
        old_target = interaction.target

        def set_new_target():
            (game, _) = get_game_references(interaction)
            if game is None:
                return
            new_target = game.get_game_target(actor_sim=interaction.sim)
            if new_target is not None:
                interaction.set_target(new_target)

        def revert_target():
            interaction.set_target(old_target)

        sequence = build_critical_section_with_finally(lambda _: set_new_target(), sequence, lambda _: revert_target())
        return sequence

    FACTORY_TYPE = factory

    def __init__(self, description="Set an interaction's target to the appropriate reactive Sim for the given game and change it back when the interaction finishes.", **kwargs):
        super().__init__(description=description, **kwargs)
