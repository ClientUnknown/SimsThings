import randomfrom animation.animation_utils import AnimationOverridesfrom buffs.tunable import TunableBuffReferencefrom objects.collection_manager import CollectionIdentifier, ObjectCollectionDatafrom objects.components.state import ObjectStateValue, ObjectStatefrom objects.persistence_groups import PersistenceGroupsfrom objects.system import create_objectfrom sims4.tuning.tunable import AutoFactoryInit, TunableEnumEntry, TunableReference, TunableTuple, Tunable, TunableEnumWithFilter, TunableList, TunableMapping, TunableRange, HasTunableFactoryfrom statistics.statistic import Statisticimport servicesimport sims4import taglogger = sims4.log.Logger('GameCardBattle', default_owner='camilogarcia')
class CardBattleBehavior(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'collectable_type': TunableEnumEntry(description='\n            Id for the card battle collection where the collectible items\n            will be read when a new card needs to be created.\n            ', tunable_type=CollectionIdentifier, default=CollectionIdentifier.Unindentified, invalid_enums=(CollectionIdentifier.Unindentified,)), 'card_slot_type': TunableReference(description='\n            Slot type where player card should appear.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SLOT_TYPE)), 'practice_card': TunableReference(description='\n            Object reference to use as the default definition as the opponent\n            card.  This is to have the same dummy as the opponent when game is\n            only played by one player.\n            ', manager=services.definition_manager()), 'challenger_buff': TunableBuffReference(description='\n            The buff to apply to the Sim that started the game.  This is used\n            to be able to guarantee we maintain the challenger Sim consistent\n            since the setup mixers and turns can be run by other Sims\n            depending on route time and other aspects.\n            '), 'card_information': TunableTuple(description='\n            Challenger and defender information that will be used to identify\n            specific behavior of the cards depending on their placement.\n            ', challenge_state_value=ObjectStateValue.TunableReference(description='\n                The state value cards will have when they are selected for \n                a game challenge.\n                '), default_state_value=ObjectStateValue.TunableReference(description='\n                Default state value of cards after a challenge is done.\n                '), level_state=ObjectState.TunableReference(description='\n                Level states defining the state values that the card has\n                representing its experience level.\n                '), challenger_prop_override=Tunable(description='\n                Prop override name for the card placed on the challenger slot.\n                Name for prop should match prop name on swing. \n                ', tunable_type=str, default=''), defender_prop_override=Tunable(description='\n                Prop override name for the card placed on the defender slot.\n                Name for prop should match prop name on swing.\n                ', tunable_type=str, default='')), 'card_scoring': TunableTuple(description='\n            Scoring tunables to apply to a card when the game ends.\n            ', level_statistic=Statistic.TunableReference(description='\n                This statistic is used as the level statistic value to be\n                increased when the card has won a game.\n                '), game_won_statistic_increase=TunableRange(description='\n                Statistic value to increase if the game is won.\n                Final score increase is affected by the state to stat\n                multiplier.\n                ', tunable_type=int, default=1, minimum=0), game_lost_statistic_increase=TunableRange(description='\n                Statistic value to increase if the game is lost.\n                Final score increase is affected by the state to stat\n                multiplier.\n                ', tunable_type=int, default=1, minimum=0), state_to_stat_multiplier=TunableMapping(description="\n                Mapping of card state value to stat multiplier when a game is \n                finished.\n                This value will be multiplied by the \n                game_won_statistic_increase or game_lost_statistic_increase\n                depending if it's a win or a loss.\n                e.g. If card has LEVEL_TWO state value, experience per win is \n                game_won_statistic_increase * multiplier corresponding to the\n                LEVEL_TWO state value.\n                ", key_type=ObjectStateValue.TunableReference(description='\n                    State value the card should have to apply this multiplier\n                    to the statistic increase.\n                    '), value_type=TunableRange(description='\n                    Multiplier that affects the game won statistic increase \n                    on the card.\n                    ', tunable_type=float, default=1, minimum=0))), 'placement_state_buff': TunableList(description='\n            List of states and buffs to be applied to the Sim when a card\n            with active state value.\n            ', tunable=TunableTuple(description='\n                Tuple of state and buff that will be added to the Sim when\n                a card with that specific state value is played.\n                ', state_value=ObjectStateValue.TunableReference(description='\n                    Object state value card needs to have to add the buff\n                    into the Sim.\n                    ', pack_safe=True), buff=TunableBuffReference(description='\n                    The buff to apply to the Sim when a card with this state\n                    is played.\n                    ', pack_safe=True))), 'card_tag': TunableEnumWithFilter(description='\n            Tag to look for when iterating through objects to know if they\n            are of the card type.\n            ', tunable_type=tag.Tag, filter_prefixes=['object', 'func'], default=tag.Tag.INVALID, invalid_enums=(tag.Tag.INVALID,))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._players_cards = {}
        self.challenger_definition = None
        self.defender_definition = None
        self._arena_obj = None

    def on_player_added(self, sim, target):
        self._arena_obj = target.part_owner
        candidate_cards = []
        player_card = None
        sim_inventory = sim.inventory_component
        from_inventory = True
        player_slot = self._get_slot_for_sim_position(target, sim.position)
        slotted_objects = player_slot.children
        if slotted_objects:
            player_card = player_slot.children[0]
            if sim.is_npc:
                from_inventory = False
        else:
            for obj in sim_inventory:
                if obj.definition.has_build_buy_tag(self.card_tag):
                    if obj.state_value_active(self.card_information.challenge_state_value):
                        player_card = obj
                        player_card.set_state(self.card_information.default_state_value.state, self.card_information.default_state_value)
                        break
                    candidate_cards.append(obj)
            if player_card is None:
                if candidate_cards:
                    player_card = random.choice(candidate_cards)
                else:
                    from_inventory = False
                    card_options = ObjectCollectionData.get_collection_data(self.collectable_type).object_list
                    if not card_options:
                        logger.error('Collection {} is an invalid id', self.collectable_type)
                        return
                    card_definition = random.choice(card_options).collectable_item
                    player_card = create_object(card_definition)
                    card_level_state_value = random.choice(self.card_information.level_state.values)
                    player_card.set_state(card_level_state_value.state, card_level_state_value)
                    player_card.persistence_group = PersistenceGroups.NONE
        if player_card is None:
            logger.error('Failed to create card for player {} for card candidates {}', sim, candidate_cards)
        card_definition = player_card.get_game_animation_definition()
        if card_definition is None:
            logger.error('Card {} has no game animation definition tuned and will not be displayed on the card battle object', player_card)
            return
        if self.challenger_definition is None:
            self.challenger_definition = card_definition
            sim.add_buff_from_op(buff_type=self.challenger_buff.buff_type, buff_reason=self.challenger_buff.buff_reason)
        else:
            self.defender_definition = card_definition
        self._create_card_on_slot(player_card, player_slot)
        self._apply_card_placement_bonus(sim, player_card)
        reservation_handler = player_card.get_reservation_handler(sim)
        reservation_handler.begin_reservation()
        self._players_cards[sim] = (player_card, from_inventory, reservation_handler)

    def on_game_ended(self, winning_team):
        for sim in list(self._players_cards):
            if winning_team is not None:
                if sim in winning_team.players:
                    self._update_card_scoring(sim, self.card_scoring.game_won_statistic_increase)
                else:
                    self._update_card_scoring(sim, self.card_scoring.game_lost_statistic_increase)
            self.on_player_removed(sim, from_game_ended=True)
        self.challenger_definition = None
        self.defender_definition = None
        self._arena_obj = None

    def _update_card_scoring(self, sim, win_loss_score):
        (card, from_inventory, _) = self._players_cards[sim]
        if card is None:
            logger.error('Game ended but Sim {} was removed earlier, this will cause cards to not be updated', sim)
            return
        if not from_inventory:
            return
        level_state_value = card.get_state(self.card_information.level_state)
        if level_state_value is None:
            logger.error("Card {} doesn't support the state {} used for card scoring", card, self.card_information.level_state)
            return
        score_multiplier = self.card_scoring.state_to_stat_multiplier.get(level_state_value)
        if score_multiplier is None:
            logger.error('Card scoring tuning error, state value {} is not tuned inside the multiplier range of the game', level_state_value)
            return
        level_statistic = card.get_stat_instance(self.card_scoring.level_statistic, add=True)
        level_statistic.tracker.add_value(self.card_scoring.level_statistic, win_loss_score*score_multiplier)

    def _apply_card_placement_bonus(self, sim, card):
        for placement_modifier in self.placement_state_buff:
            if card.state_value_active(placement_modifier.state_value):
                sim.add_buff_from_op(buff_type=placement_modifier.buff.buff_type, buff_reason=placement_modifier.buff.buff_reason)

    def on_player_removed(self, sim, from_game_ended=False):
        if sim not in self._players_cards:
            return
        if not from_game_ended:
            self._update_card_scoring(sim, self.card_scoring.game_lost_statistic_increase)
        (card, from_inventory, reservation_handler) = self._players_cards[sim]
        reservation_handler.end_reservation()
        if from_inventory:
            sim.inventory_component.player_try_add_object(card)
        else:
            card.set_parent(None)
            card.destroy(source=self, cause='GameComponent: Placeholder game card removed.')
        del self._players_cards[sim]
        if sim.has_buff(self.challenger_buff.buff_type):
            sim.remove_buff_by_type(self.challenger_buff.buff_type)

    def _create_card_on_slot(self, card, slot):
        if slot is not None and slot.empty:
            slot.add_child(card)

    def _get_slot_for_sim_position(self, target, sim_position):
        max_magnitude = None
        closest_slot = None
        for runtime_slot in target.part_owner.get_runtime_slots_gen(slot_types={self.card_slot_type}):
            difference_vector = runtime_slot.position - sim_position
            difference_magnitude = difference_vector.magnitude()
            if not max_magnitude is None:
                if difference_magnitude < max_magnitude:
                    closest_slot = runtime_slot
                    max_magnitude = difference_magnitude
            closest_slot = runtime_slot
            max_magnitude = difference_magnitude
        return closest_slot

    def additional_anim_overrides_gen(self):
        prop_overrides = {}
        if self.challenger_definition is not None:
            self._set_prop_override(prop_overrides, self.card_information.challenger_prop_override, self.challenger_definition)
            if self.defender_definition is None:
                self._set_prop_override(prop_overrides, self.card_information.defender_prop_override, self.practice_card)
        if self.defender_definition is not None:
            self._set_prop_override(prop_overrides, self.card_information.defender_prop_override, self.defender_definition)
            if self.challenger_definition is None:
                self._set_prop_override(prop_overrides, self.card_information.challenger_prop_override, self.practice_card)
        yield AnimationOverrides(props=prop_overrides)

    def _set_prop_override(self, prop_overrides, override_name, card_definition):
        prop_overrides[override_name] = sims4.collections.FrozenAttributeDict({'states_to_override': (), 'from_actor': None, 'definition': card_definition, 'sharing': None, 'set_as_actor': None})
