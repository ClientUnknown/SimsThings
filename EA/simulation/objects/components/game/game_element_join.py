from element_utils import build_elementfrom elements import ParentElementfrom interactions.liability import Liabilityfrom objects.components.game.game_challenge_liability import GameChallengeLiabilityfrom objects.components.game.game_transition_liability import GameTransitionLiabilityfrom objects.components.game_component import GameRules, get_game_referencesfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableFactory, Tunable, TunableList, TunableReferenceimport servicesimport sims4.resourcesfrom singletons import DEFAULT
class _GameElementJoinLiability(Liability):
    LIABILITY_TOKEN = '_GameElementJoinLiability'

    def __init__(self, game_element_join, **kwargs):
        super().__init__(**kwargs)
        self._interaction = None
        self._game_element_join = game_element_join

    def merge(self, interaction, key, new_liability):
        (target_game, _) = get_game_references(interaction)
        if target_game is not None:
            target_game.move_player(interaction.sim, interaction.target)
        return self

    def on_add(self, interaction):
        if self._interaction is not None:
            self._interaction = interaction
            return
        self._interaction = interaction
        (target_game, _) = get_game_references(interaction)
        if target_game is None:
            return
        if target_game.current_game is None:
            target_game.set_current_game(self._game_element_join.game_type)
        if type(target_game.current_game) is self._game_element_join.game_type:
            target_game.add_player(interaction.sim, interaction.target, source=interaction.source)
            target_game.take_turn()
        if self._game_element_join.ensure_setup:
            target_game.setup_game()
        challenge_liability = interaction.get_liability(GameChallengeLiability.LIABILITY_TOKEN)
        if challenge_liability is not None:
            challenge_liability.on_game_started(target_game)

    def release(self):
        if self._interaction is None:
            return
        (target_game, _) = get_game_references(self._interaction)
        if target_game is not None:
            target_game.remove_player(self._interaction.sim)

    def should_transfer(self, continuation):
        continuation_type = continuation.get_interaction_type()
        return continuation_type in self._game_element_join.game_affordances

class GameElementJoin(ParentElement, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'game_type': GameRules.TunableReference(description='\n            The game to create or join.\n            '), 'game_affordances': TunableList(description='\n            Any affordance in this list, when pushed as a continuation of this\n            interaction, will preserve the game, as if the Sim never left it.\n            ', tunable=TunableReference(description='\n                An affordance that, when pushed as a continuation of this\n                interaction, preserves the game.\n                ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions='SuperInteraction')), 'ensure_setup': Tunable(description='\n            If checked, ensure that the game is properly set up on join.\n            ', tunable_type=bool, default=False)}

    def __init__(self, interaction, *args, sequence=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.interaction = interaction
        self.sequence = sequence

    @classmethod
    def on_affordance_loaded_callback(cls, affordance, game_join_element, object_tuning_id=DEFAULT):
        affordance.add_additional_basic_liability(lambda *args, **kwargs: GameTransitionLiability(*args, game_type=game_join_element.game_type, **kwargs))

    def _begin_game(self, _):
        self.interaction.add_liability(_GameElementJoinLiability.LIABILITY_TOKEN, _GameElementJoinLiability(self))
        return True

    def _run(self, timeline):
        child_element = build_element((self._begin_game, self.sequence))
        return timeline.run_child(child_element)
