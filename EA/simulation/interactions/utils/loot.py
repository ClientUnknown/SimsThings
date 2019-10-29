from broadcasters.broadcaster_loot_op import BroadcasterOneShotLootOpfrom bucks.bucks_loot_op import BucksLoot, AwardPerkLootfrom buffs.dynamic_buff_loot_op import DynamicBuffLootOpfrom business.business_ops import ModifyCustomerFlowfrom careers.career_ops import CareerLevelOp, CareerLootOpfrom clubs.club_ops import SetClubGatheringVibefrom delivery.scheduled_delivery_loot_op import ScheduledDeliveryLootfrom drama_scheduler.drama_node_ops import ScheduleDramaNodeLoot, CancelScheduledDramaNodeLootfrom drama_scheduler.fishing_contest_ops import FishingContestAwardWinnersfrom event_testing.test_event_loots import ProcessEventOpfrom fame.fame_loot_ops import SquadLootOpfrom global_policies.global_policy_loots import GlobalPolicyAddProgressfrom interactions import ParticipantTypefrom interactions.inventory_loot import InventoryLootfrom interactions.money_payout import MoneyChangefrom interactions.object_rewards import ObjectRewardsOperationfrom interactions.social.greeting_socials.greetings import GreetingLootOpfrom interactions.utils import LootTypefrom interactions.utils.apply_overlay_loot import ApplyCanvasOverlayfrom interactions.utils.looping_loot_op import LoopingLootOpfrom interactions.utils.loot_ops import LifeExtensionLootOp, StateChangeLootOp, AddTraitLootOp, RemoveTraitLootOp, HouseholdFundsInterestLootOp, FireLootOp, UnlockLootOp, DialogLootOp, FireDeactivateSprinklerLootOp, ExtinguishNearbyFireLootOp, AwardWhimBucksLootOp, DiscoverClueLootOp, BreakThroughLootOperation, NewCrimeLootOp, RefreshWhimsLootOp, RemoveNotebookEntry, DestroyObjectsFromInventoryLootOp, LockDoor, UnlockDoor, SummonNPC, TravelToTargetSim, UnlockHiddenAspirationTrack, SetPrimaryAspirationTrack, IncrementCommunityChallengeCount, SlotObjects, DoNothingLootOp, ResetAspirationfrom interactions.utils.reactions import ReactionLootOpfrom interactions.utils.visual_effect import PlayVisualEffectLootOpfrom narrative.narrative_loot_ops import NarrativeLootOp, NarrativeGroupProgressionfrom notebook.notebook_entry_ops import NotebookEntryLootOpfrom objects.components import game_componentfrom objects.components.hidden_inventory_tuning import HiddenInventoryTransferLootfrom objects.components.name_component import NameResetLootOp, TransferNameLootOp, SetNameFromObjectRelationshipfrom objects.components.object_relationship_component import ObjectRelationshipLootOpfrom objects.components.ownable_component import TransferOwnershipLootOpfrom objects.components.stored_object_info_component import StoreObjectInfoLootOp, RemoveObjectInfoLootOpfrom objects.components.stored_sim_info_component import TransferStoredSimInfo, RemoveSimInfoLootOp, StoreSimInfoLootOpfrom objects.components.tooltip_component import TransferCustomTooltipfrom objects.components.transfer_painting_state import TransferPaintingStateLootfrom objects.gardening.gardening_loot_ops import CreatePlantAtLocationLootOperationfrom objects.object_creation import ObjectCreationOpfrom objects.object_tag_tuning import ApplyTagsToObjectfrom objects.puddles.puddle_loot_op import CreatePuddlesLootOpfrom pets.missing_pet_tuning import MakePetMissing, PostMissingPetAlertfrom relationships.relationship_bit_change import RelationshipBitChangefrom relationships.relationship_knowledge_ops import KnowOtherSimTraitOp, KnowOtherSimCareerOp, KnowOtherSimsStatfrom relationships.relationship_lock_change import UnlockRelationshipBitLockfrom relics.relic_loot import AddRelicCombofrom restaurants.restaurant_ops import ClaimRestaurantTable, ClaimRestaurantSeat, ReleaseRestaurantTable, RestaurantExpediteGroupOrderfrom rewards.reward_operation import RewardOperationfrom sickness.sickness_loot_ops import GiveSicknessLootOp, RemoveSicknessLootOpfrom sims.favorites.favorites_loot import SetFavoriteLootOpfrom sims4.sim_irq_service import yield_to_irqfrom sims4.tuning.instances import TunedInstanceMetaclass, HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import TunableList, Tunable, TunableVariant, HasTunableReference, HasTunableSingletonFactory, AutoFactoryInit, TunableTuple, TunableReferencefrom sims4.utils import classproperty, flexmethodfrom situations.complex.mother_plant_battle_ops import MotherplantBattleSituationStateChangefrom situations.service_npcs.butler.butler_loot_ops import ButlerSituationStateChangefrom situations.tunable import CreateSituationLootOpfrom statistics.statistic_ops import TunableStatisticChange, SkillEffectivenessLoot, DynamicSkillLootOp, NormalizeStatisticsOp, StatisticOperationfrom topics.tunable import TopicUpdatefrom tunable_multiplier import TunableMultiplierfrom weather.weather_loot_ops import WeatherSetOverrideForecastLootOp, WeatherStartEventLootOp, WeatherSetSeasonLootOpfrom world.floor_feature_loot import FloorFeatureRemoveOpimport assertionsimport buffs.buff_opsimport servicesimport sims.gender_preferenceimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Interactions')
class LootOperationList:

    def __init__(self, resolver, loot_list):
        self._loot_actions = tuple(loot_list)
        self._resolver = resolver

    def apply_operations(self):
        for loot_action in self._loot_actions:
            yield_to_irq()
            loot_action.apply_to_resolver(self._resolver)

class LootActionVariant(TunableVariant):

    def __init__(self, *args, statistic_pack_safe=False, **kwargs):
        super().__init__(*args, actions=TunableReference(description='\n                Apply a set of loot operations.\n                ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'), pack_safe=True), apply_canvas_overlay=ApplyCanvasOverlay.TunableFactory(), statistics=TunableStatisticChange(statistic_override=StatisticOperation.get_statistic_override(pack_safe=statistic_pack_safe)), relationship_bits_loot=RelationshipBitChange.TunableFactory(description='A list of relationship bit operations to perform'), relationship_bits_lock=UnlockRelationshipBitLock.TunableFactory(), money_loot=MoneyChange.TunableFactory(), topic_loot=TopicUpdate.TunableFactory(target_participant_type_options={'optional': True}), buff=buffs.buff_ops.BuffOp.TunableFactory(), buff_removal=buffs.buff_ops.BuffRemovalOp.TunableFactory(), buff_transfer=buffs.buff_ops.BuffTransferOp.TunableFactory(target_participant_type_options={'description': '\n                    Buffs are transferred from this Sim to the Subject.\n                    ', 'default_participant': ParticipantType.Actor}), normalize_stat=NormalizeStatisticsOp.TunableFactory(target_participant_type_options={'description': '\n                    The Sim from which to transfer the listed stats from.\n                    ', 'default_participant': ParticipantType.Actor}), skill_effectiveness=SkillEffectivenessLoot.TunableFactory(), take_turn=game_component.TakeTurn.TunableFactory(), team_score=game_component.TeamScore.TunableFactory(), team_score_points=game_component.TeamScorePoints.TunableFactory(), game_over=game_component.GameOver.TunableFactory(), reset_high_score=game_component.ResetHighScore.TunableFactory(), reset_game=game_component.ResetGame.TunableFactory(), setup_game=game_component.SetupGame.TunableFactory(), dynamic_skill_loot=DynamicSkillLootOp.TunableFactory(locked_args={'exclusive_to_owning_si': False}), fix_gender_preference=sims.gender_preference.GenderPreferenceOp.TunableFactory(), inventory_loot=InventoryLoot.TunableFactory(subject_participant_type_options={'description': '\n                     The participant type who has the inventory that the\n                     object goes into during this loot.\n                     ', 'optional': True}, target_participant_type_options={'description': '\n                    The participant type of the object which would get to\n                    switch inventory in the loot\n                    ', 'default_participant': ParticipantType.CarriedObject}), dynamic_buff_loot=DynamicBuffLootOp.TunableFactory(), object_rewards=ObjectRewardsOperation.TunableFactory(), reward=RewardOperation.TunableFactory(), transfer_ownership=TransferOwnershipLootOp.TunableFactory(), create_object=ObjectCreationOp.TunableFactory(), create_puddles=CreatePuddlesLootOp.TunableFactory(target_participant_type_options={'description': '\n                    The participant of the interaction whom the puddle\n                    should be placed near.\n                    ', 'default_participant': ParticipantType.Object}), create_situation=CreateSituationLootOp.TunableFactory(), life_extension=LifeExtensionLootOp.TunableFactory(), notification_and_dialog=DialogLootOp.TunableFactory(), state_change=StateChangeLootOp.TunableFactory(), trait_add=AddTraitLootOp.TunableFactory(), trait_remove=RemoveTraitLootOp.TunableFactory(), know_other_sims_trait=KnowOtherSimTraitOp.TunableFactory(target_participant_type_options={'description': '\n                    The Sim or Sims whose information the subject Sim is learning.\n                    ', 'default_participant': ParticipantType.TargetSim}), know_other_sims_career=KnowOtherSimCareerOp.TunableFactory(target_participant_type_options={'description': '\n                    The Sim or Sims whose information the subject Sim is learning.\n                    ', 'default_participant': ParticipantType.TargetSim}), know_other_sims_statistics=KnowOtherSimsStat.TunableFactory(target_participant_type_options={'description': '\n                    The Sim or Sims whose information the subject Sim is learning.\n                    ', 'default_participant': ParticipantType.TargetSim}), object_relationship=ObjectRelationshipLootOp.TunableFactory(target_participant_type_options={'description': '\n                    The object whose relationship to modify.\n                    ', 'default_participant': ParticipantType.Object}), interest_income=HouseholdFundsInterestLootOp.TunableFactory(), career_level=CareerLevelOp.TunableFactory(), career_loot=CareerLootOp.TunableFactory(career_options={'pack_safe': True}), fire=FireLootOp.TunableFactory(), unlock_item=UnlockLootOp.TunableFactory(), fire_deactivate_sprinkler=FireDeactivateSprinklerLootOp.TunableFactory(), fire_clean_scorch=FloorFeatureRemoveOp.TunableFactory(), extinguish_nearby_fire=ExtinguishNearbyFireLootOp.TunableFactory(), award_whim_bucks=AwardWhimBucksLootOp.TunableFactory(), discover_clue=DiscoverClueLootOp.TunableFactory(), new_crime=NewCrimeLootOp.TunableFactory(), create_notebook_entry=NotebookEntryLootOp.TunableFactory(), breakthrough_moment=BreakThroughLootOperation.TunableFactory(), destroy_objects_from_inventory=DestroyObjectsFromInventoryLootOp.TunableFactory(), bucks_loot=BucksLoot.TunableFactory(), award_perk=AwardPerkLoot.TunableFactory(), refresh_whims=RefreshWhimsLootOp.TunableFactory(), remove_notebook_entry=RemoveNotebookEntry.TunableFactory(), lock_door=LockDoor.TunableFactory(), unlock_door=UnlockDoor.TunableFactory(), reaction=ReactionLootOp.TunableFactory(), greeting=GreetingLootOp.TunableFactory(), event=ProcessEventOp.TunableFactory(), schedule_drama_node=ScheduleDramaNodeLoot.TunableFactory(), cancel_scheduled_drama_node=CancelScheduledDramaNodeLoot.TunableFactory(), set_club_gathering_vibe=SetClubGatheringVibe.TunableFactory(), summon_npc=SummonNPC.TunableFactory(), travel_to_target_sim=TravelToTargetSim.TunableFactory(), increment_community_challenge_count=IncrementCommunityChallengeCount.TunableFactory(), unlock_hidden_aspiration_track=UnlockHiddenAspirationTrack.TunableFactory(), set_primary_aspiration_track=SetPrimaryAspirationTrack.TunableFactory(), claim_table=ClaimRestaurantTable.TunableFactory(), claim_seat=ClaimRestaurantSeat.TunableFactory(), release_table=ReleaseRestaurantTable.TunableFactory(), restaurant_expedite_order=RestaurantExpediteGroupOrder.TunableFactory(), business_modify_customer_flow=ModifyCustomerFlow.TunableFactory(), butler_state_change=ButlerSituationStateChange.TunableFactory(), slot_objects=SlotObjects.TunableFactory(), looping_loot_ops=LoopingLootOp.TunableFactory(), give_sickness=GiveSicknessLootOp.TunableFactory(), remove_sickness=RemoveSicknessLootOp.TunableFactory(), apply_tags_to_object=ApplyTagsToObject.TunableFactory(), make_pet_missing=MakePetMissing.TunableFactory(), name_reset=NameResetLootOp.TunableFactory(), post_missing_pet_alert=PostMissingPetAlert.TunableFactory(), vfx=PlayVisualEffectLootOp.TunableFactory(), add_relic_combo=AddRelicCombo.TunableFactory(), oneshot_broadcaster=BroadcasterOneShotLootOp.TunableFactory(), store_object_info=StoreObjectInfoLootOp.TunableFactory(), remove_object_info=RemoveObjectInfoLootOp.TunableFactory(), store_sim_info=StoreSimInfoLootOp.TunableFactory(), remove_stored_sim_info=RemoveSimInfoLootOp.TunableFactory(), weather_set_override_forecast=WeatherSetOverrideForecastLootOp.TunableFactory(locked_args={'subject': ParticipantType.Actor}), weather_set_season=WeatherSetSeasonLootOp.TunableFactory(locked_args={'subject': ParticipantType.Actor}), weather_start_event=WeatherStartEventLootOp.TunableFactory(locked_args={'subject': ParticipantType.Actor}), hidden_inventory_transfer=HiddenInventoryTransferLoot.TunableFactory(), transfer_painting_state=TransferPaintingStateLoot.TunableFactory(), squad_loot=SquadLootOp.TunableFactory(), stored_sim_info_transfer=TransferStoredSimInfo.TunableFactory(), custom_tooltip_transfer=TransferCustomTooltip.TunableFactory(), transfer_name_loot=TransferNameLootOp.TunableFactory(), reset_aspiration=ResetAspiration.TunableFactory(), narrative=NarrativeLootOp.TunableFactory(), narrative_progression=NarrativeGroupProgression.TunableFactory(), scheduled_delivery=ScheduledDeliveryLoot.TunableReference(), motherplant_battle_change=MotherplantBattleSituationStateChange.TunableFactory(), global_policy_add_progress=GlobalPolicyAddProgress.TunableFactory(locked_args={'text': None}), fishing_contest_get_reward=FishingContestAwardWinners.TunableFactory(), set_name_from_object_relationship=SetNameFromObjectRelationship.TunableFactory(), create_plant=CreatePlantAtLocationLootOperation.TunableFactory(), set_favorite=SetFavoriteLootOp.TunableFactory(), **kwargs)

class LootActions(HasTunableReference, HasTunableSingletonFactory, AutoFactoryInit, metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.ACTION)):
    INSTANCE_TUNABLES = {'run_test_first': Tunable(description='\n           If left unchecked, iterate over the actions and if its test succeeds\n           apply the action at that moment.\n           \n           If checked, run through all the loot actions and collect all actions\n           that passes their test.  Then apply all the actions that succeeded.\n           ', tunable_type=bool, default=False), 'loot_actions': TunableList(description='\n           List of loots operations that will be awarded.\n           ', tunable=LootActionVariant(statistic_pack_safe=True))}
    FACTORY_TUNABLES = INSTANCE_TUNABLES
    _simoleon_loot = None

    @classmethod
    def _tuning_loaded_callback(cls):
        cls._simoleon_loot = None
        for action in cls.loot_actions:
            if hasattr(action, 'get_simoleon_delta'):
                if cls._simoleon_loot is None:
                    cls._simoleon_loot = []
                cls._simoleon_loot.append(action)

    @classmethod
    def _verify_tuning_callback(cls):
        cls._validate_recursion()

    @classmethod
    @assertions.not_recursive
    def _validate_recursion(cls):
        for action in cls.loot_actions:
            if action.loot_type == LootType.ACTIONS:
                try:
                    action._validate_recursion()
                except AssertionError:
                    logger.error('{} is an action in {} but that creates a circular dependency', action, cls, owner='epanero')

    @classproperty
    def loot_type(self):
        return LootType.ACTIONS

    @classmethod
    def get_simoleon_delta(cls, *args, **kwargs):
        total_funds_category = None
        total_funds_delta = 0
        if cls._simoleon_loot is not None:
            for action in cls._simoleon_loot:
                (funds_delta, funds_category) = action.get_simoleon_delta(*args, **kwargs)
                if funds_category is not None:
                    total_funds_category = funds_category
                total_funds_delta += funds_delta
        return (total_funds_delta, total_funds_category)

    @flexmethod
    def get_loot_ops_gen(cls, inst, resolver=None, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        if resolver is None or not inst_or_cls.run_test_first:
            for action in inst_or_cls.loot_actions:
                if action.loot_type == LootType.ACTIONS:
                    yield from action.get_loot_ops_gen(resolver=resolver, **kwargs)
                else:
                    yield (action, False)
        else:
            actions_that_can_be_applied = []
            for action in inst_or_cls.loot_actions:
                if action.loot_type == LootType.ACTIONS or action.test_resolver(resolver):
                    actions_that_can_be_applied.append(action)
            for action in actions_that_can_be_applied:
                if action.loot_type == LootType.ACTIONS:
                    yield from action.get_loot_ops_gen(resolver=resolver, **kwargs)
                else:
                    yield (action, True)

    @classmethod
    def apply_to_resolver_and_get_display_texts(cls, resolver):
        display_texts = []
        for (action, test_ran) in cls.get_loot_ops_gen(resolver=resolver):
            try:
                (success, _) = action.apply_to_resolver(resolver, skip_test=test_ran)
                if success:
                    display_texts.append(action.get_display_text(resolver=resolver))
            except Exception as ex:
                logger.exception('Exception when applying action {} for loot {}', action, cls)
                raise ex
        return display_texts

    @flexmethod
    def apply_to_resolver(cls, inst, resolver, skip_test=False):
        inst_or_cls = inst if inst is not None else cls
        for (action, test_ran) in inst_or_cls.get_loot_ops_gen(resolver):
            try:
                action.apply_to_resolver(resolver, skip_test=test_ran)
            except Exception as ex:
                logger.exception('Exception when applying action {} for loot {}', action, cls)
                raise ex
LootActions.TunableFactory(description='[rez] <Unused>')
class WeightedSingleSimLootActions(HasTunableReference, HasTunableSingletonFactory, AutoFactoryInit, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.ACTION)):
    INSTANCE_TUNABLES = {'loot_actions': TunableList(description='\n            A list of weighted Loot Actions that operate only on one Sim.\n            ', tunable=TunableTuple(buff_loot=DynamicBuffLootOp.TunableFactory(), weight=Tunable(description='\n                    Accompanying weight of the loot.\n                    ', tunable_type=int, default=1)))}

    def __iter__(self):
        return iter(self.loot_actions)

    @classmethod
    def pick_loot_op(cls):
        weighted_loots = [(loot.weight, loot.buff_loot) for loot in cls.loot_actions]
        loot_op = sims4.random.weighted_random_item(weighted_loots)
        return loot_op

class RandomWeightedLoot(HasTunableReference, HasTunableSingletonFactory, AutoFactoryInit, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.ACTION)):
    INSTANCE_TUNABLES = {'random_loot_actions': TunableList(description='\n            List of weighted loot actions that can be run.\n            ', tunable=TunableTuple(description='\n                Weighted actions that will be randomly selected when\n                the loot is executed.  The loots will be tested\n                before running to guarantee the random action is valid. \n                ', action=LootActionVariant(do_nothing=DoNothingLootOp.TunableFactory()), weight=TunableMultiplier.TunableFactory(description='\n                    The weight of this potential initial moment relative\n                    to other items within this list.\n                    ')))}
    _simoleon_loot = None

    @classmethod
    def _tuning_loaded_callback(cls):
        cls._simoleon_loot = None
        for random_action in cls.random_loot_actions:
            if hasattr(random_action.action, 'get_simoleon_delta'):
                if cls._simoleon_loot is None:
                    cls._simoleon_loot = []
                cls._simoleon_loot.append(random_action.action)

    @classproperty
    def loot_type(self):
        return LootType.ACTIONS

    @classmethod
    @assertions.not_recursive
    def _validate_recursion(cls):
        for random_action in cls.random_loot_actions:
            if random_action.action.loot_type == LootType.ACTIONS:
                try:
                    random_action.action._validate_recursion()
                except AssertionError:
                    logger.error('{} is an action in {} but that creates a circular dependency', random_action.action, cls, owner='camilogarcia')

    @flexmethod
    def get_loot_ops_gen(cls, inst, resolver=None, auto_select=True):
        inst_or_cls = inst if inst is not None else cls
        if resolver is None:
            for random_action in inst_or_cls.random_loot_actions:
                if random_action.action.loot_type == LootType.ACTIONS:
                    yield from random_action.action.get_loot_ops_gen(resolver=resolver)
                else:
                    yield (random_action.action, False)
        elif auto_select:
            weighted_random_actions = [(ra.weight.get_multiplier(resolver), ra.action) for ra in inst_or_cls.random_loot_actions]
            actions = []
            while weighted_random_actions:
                potential_action_index = sims4.random.weighted_random_index(weighted_random_actions)
                if potential_action_index is None:
                    return
                potential_action = weighted_random_actions.pop(potential_action_index)[1]
                if potential_action is None:
                    pass
                elif potential_action.loot_type == LootType.ACTIONS:
                    valid_actions = []
                    for (action, _) in potential_action.get_loot_ops_gen(resolver=resolver):
                        if action.test_resolver(resolver):
                            valid_actions.append(action)
                    actions = valid_actions
                    break
                elif potential_action.test_resolver(resolver):
                    actions = (potential_action,)
                    break
            for action in actions:
                if action.loot_type == LootType.ACTIONS:
                    yield from action.get_loot_ops_gen(resolver=resolver)
                else:
                    yield (action, True)
        else:
            yield (inst_or_cls, False)

    @flexmethod
    def apply_to_resolver(cls, inst, resolver, skip_test=False):
        inst_or_cls = inst if inst is not None else cls
        for (action, test_ran) in inst_or_cls.get_loot_ops_gen(resolver):
            try:
                action.apply_to_resolver(resolver, skip_test=test_ran)
            except BaseException as ex:
                logger.exception('Exception when applying action {} for loot {}', action, cls)
                raise ex

    @classmethod
    def test_resolver(cls, *_, **__):
        return True

    @flexmethod
    def apply_to_interaction_statistic_change_element(cls, inst, resolver):
        inst_or_cls = inst if inst is not None else cls
        inst_or_cls.apply_to_resolver(resolver, skip_test=True)

    @classmethod
    def get_stat(cls, _interaction):
        pass

    @classmethod
    def get_simoleon_delta(cls, *args, **kwargs):
        total_funds_category = None
        total_funds_delta = 0
        if cls._simoleon_loot is not None:
            for action in cls._simoleon_loot:
                (funds_delta, funds_category) = action.get_simoleon_delta(*args, **kwargs)
                if funds_category is not None:
                    total_funds_category = funds_category
                total_funds_delta += funds_delta
        return (total_funds_delta, total_funds_category)
