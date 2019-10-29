import itertoolsimport randomfrom buffs.tunable import TunableBuffReferencefrom date_and_time import create_time_spanfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.shared_messages import build_icon_info_msg, IconInfoDatafrom event_testing.test_events import TestEventfrom interactions.aop import AffordanceObjectPairfrom interactions.context import InteractionContext, QueueInsertStrategy, InteractionSourcefrom interactions.priority import Priorityfrom objects.components.state import TunableStateValueReferencefrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReference, TunableSimMinute, TunableResourceKey, TunableListfrom sims4.tuning.tunable_base import GroupNamesfrom situations.base_situation import SituationDisplayPriority, _RequestUserDatafrom situations.bouncer.bouncer_request import SelectableSimRequestFactoryfrom situations.bouncer.bouncer_types import BouncerRequestPriorityfrom situations.complex.mother_plant_battle_ops import MotherplantBattleStatesfrom situations.situation_complex import SituationComplexCommon, SituationState, CommonSituationState, SituationStateData, TunableInteractionOfInterestfrom situations.situation_meter import StatBasedSituationMeterDatafrom situations.situation_types import SituationDisplayType, SituationUserFacingTypeimport alarmsimport interactionsimport servicesimport sims4.resourceslogger = sims4.log.Logger('Situations', default_owner='jjacobson')
class PrepareForBattleSituationState(SituationState):

    def _on_set_sim_role_state(self, sim, *args, **kwargs):
        super()._on_set_sim_role_state(sim, *args, **kwargs)
        if self.owner.num_of_sims >= len(self.owner._guest_list):
            self.owner._change_state(self.owner.base_battle_situation_state())

    @property
    def zombie_attack_valid(self):
        return False

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        motherplant = self.owner._get_motherplant()
        return (role_state_type, motherplant)

class BattleThePlantSituationState(CommonSituationState):

    @property
    def zombie_attack_valid(self):
        return True

class AttackBattleThePlantSituationState(CommonSituationState):

    @property
    def zombie_attack_valid(self):
        return True

    def timer_expired(self):
        self.owner._change_state(self.owner.base_battle_situation_state())

class InspireBattleThePlantSituationState(CommonSituationState):

    @property
    def zombie_attack_valid(self):
        return True

    def timer_expired(self):
        self.owner._change_state(self.owner.base_battle_situation_state())

class RallyBattleThePlantSituationState(CommonSituationState):

    @property
    def zombie_attack_valid(self):
        return True

    def timer_expired(self):
        self.owner._change_state(self.owner.base_battle_situation_state())

class WarblingWarcryBattleThePlantSituationState(CommonSituationState):

    @property
    def zombie_attack_valid(self):
        return False

    def timer_expired(self):
        self.owner._change_state(self.owner.base_battle_situation_state())

class MotherPlantBattleSituation(SituationComplexCommon):
    MOTHER_PLANT_METER_ID = 1
    PLAYER_HEALTH_METER_ID = 2
    INSTANCE_TUNABLES = {'player_job': TunableReference(description='\n            Job for the main player sim that fights the plant.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), 'player_sim_role_state': TunableReference(description='\n            Role state for the main player sim Role.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE)), 'other_player_jobs': TunableReference(description='\n            Job for the other player Sims that are not the main Sim and are not\n            participating as helpers.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), 'other_player_sims_role_state': TunableReference(description='\n            Role state for the other player Sims.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE)), 'helper_1_job': TunableReference(description='\n            Job for one of the helper Sims for the fight.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), 'helper_2_job': TunableReference(description='\n            Job for one of the helper Sims for the fight.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), 'helper_3_job': TunableReference(description='\n            Job for one of the helper Sims for the fight.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), 'helper_sim_prepare_role_state_1': TunableReference(description='\n            Role state for helper Sim 1 when preparing for battle.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE)), 'helper_sim_prepare_role_state_2': TunableReference(description='\n            Role state for helper Sim 2 when preparing for battle.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE)), 'helper_sim_prepare_role_state_3': TunableReference(description='\n            Role state for helper Sim 3 when preparing for battle.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE)), 'zombie_job': TunableReference(description='\n            Job for the Zombies for the fight.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), 'zombie_prepare_role_state': TunableReference(description='\n            Role state for the zombie Sims when preparing for battle.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE)), 'zombie_fight_interaction': TunableReference(description='\n            Interaction pushed on zombies to get them to fight a Sim.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'zombie_fight_interaction_timer': TunableSimMinute(description='\n            Timer for the amount of time between zombie attacks.\n            ', minimum=1, default=30), 'player_health_statistic': TunableReference(description="\n            The statistic that we will use in order to determine the Sim's\n            health for the motherplant.\n            ", manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), 'motherplant_health_statisic': TunableReference(description="\n            The statistic that we will use in order to determine the Sim's\n            health for the motherplant.\n            ", manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), 'victory_interaction_of_interest': TunableInteractionOfInterest(description='\n            The interaction of interest that we are looking for to determine\n            victory.\n            '), 'retreat_interaction_of_interest': TunableInteractionOfInterest(description='\n            The interaction of interest that we are looking for to determine\n            retreat.\n            '), 'loss_interaction_mixer': TunableReference(description='\n            The affordance that will be pushed on the primary Sims if they\n            lose.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'fight_affordance': TunableReference(description='\n            The primary fight interaction that we will use to run the defeat\n            mixer the player Sim.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'helper_victory_affordance': TunableReference(description='\n            The affordance that will be pushed on the helper Sims if they\n            achieve victory.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'helper_lose_affordance': TunableReference(description='\n            The affordance that will be pushed on the helper Sims if they\n            lose.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'mother_plant_definition': TunableReference(description='\n            The actual mother plant itself.\n            ', manager=services.definition_manager()), 'base_battle_situation_state': BattleThePlantSituationState.TunableFactory(locked_args={'allow_join_situation': True, 'time_out': None}, tuning_group=GroupNames.STATE), 'attack_battle_situation_state': AttackBattleThePlantSituationState.TunableFactory(locked_args={'allow_join_situation': True}, tuning_group=GroupNames.STATE), 'inspire_battle_situation_state': InspireBattleThePlantSituationState.TunableFactory(locked_args={'allow_join_situation': True}, tuning_group=GroupNames.STATE), 'rally_battle_sitaution_state': RallyBattleThePlantSituationState.TunableFactory(locked_args={'allow_join_situation': True}, tuning_group=GroupNames.STATE), 'warbling_warcry_battle_situation_state': WarblingWarcryBattleThePlantSituationState.TunableFactory(locked_args={'allow_join_situation': True}, tuning_group=GroupNames.STATE), 'save_lock_tooltip': TunableLocalizedString(description='\n            The tooltip/message to show when the player tries to save the game\n            while this situation is running. Save is locked when situation starts.\n            ', tuning_group=GroupNames.UI), 'mother_plant_meter_settings': StatBasedSituationMeterData.TunableFactory(description='\n            The meter used to track the health of the mother plant.\n            ', tuning_group=GroupNames.SITUATION, locked_args={'_meter_id': MOTHER_PLANT_METER_ID}), 'player_health_meter_settings': StatBasedSituationMeterData.TunableFactory(description='\n            The meter used to track the health of the player team.\n            ', tuning_group=GroupNames.SITUATION, locked_args={'_meter_id': PLAYER_HEALTH_METER_ID}), 'mother_plant_icon': TunableResourceKey(description='\n            Icon to be displayed in the situation UI beside the mother plant\n            health bar.\n            ', resource_types=sims4.resources.CompoundTypes.IMAGE, default=None, allow_none=True, tuning_group=GroupNames.SITUATION), 'states_to_set_on_start': TunableList(description='\n            A list of states to set on the motherplant on start.\n            ', tunable=TunableStateValueReference(description='\n                The state to set.\n                ')), 'states_to_set_on_end': TunableList(description='\n            A list of states to set on the motherplant on end.\n            ', tunable=TunableStateValueReference(description='\n                The state to set.\n                ')), 'victory_reward': TunableReference(description='\n            The Reward received when the Sim wins the situation.\n            ', manager=services.get_instance_manager(sims4.resources.Types.REWARD)), 'victory_audio_sting': TunableResourceKey(description='\n            The sound to play when the Sim wins the battle.\n            ', resource_types=(sims4.resources.Types.PROPX,), default=None, tuning_group=GroupNames.AUDIO), 'defeat_audio_sting': TunableResourceKey(description='\n            The sound to play when the Sim loses the battle.\n            ', resource_types=(sims4.resources.Types.PROPX,), default=None, tuning_group=GroupNames.AUDIO), 'possessed_buff': TunableBuffReference(description='\n            Possessed Buff for zombie Sims. \n            ')}

    @property
    def user_facing_type(self):
        return SituationUserFacingType.MOTHER_PLANT_EVENT

    @property
    def situation_display_type(self):
        return SituationDisplayType.VET

    @property
    def situation_display_priority(self):
        return SituationDisplayPriority.VET

    @classmethod
    def _states(cls):
        return (SituationStateData(1, PrepareForBattleSituationState), SituationStateData.from_auto_factory(2, cls.base_battle_situation_state), SituationStateData.from_auto_factory(3, cls.attack_battle_situation_state), SituationStateData.from_auto_factory(4, cls.inspire_battle_situation_state), SituationStateData.from_auto_factory(5, cls.rally_battle_sitaution_state), SituationStateData.from_auto_factory(6, cls.warbling_warcry_battle_situation_state))

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return ((cls.player_job, cls.player_sim_role_state), (cls.other_player_jobs, cls.other_player_sims_role_state), (cls.helper_1_job, cls.helper_sim_prepare_role_state_1), (cls.helper_2_job, cls.helper_sim_prepare_role_state_2), (cls.helper_3_job, cls.helper_sim_prepare_role_state_3), (cls.zombie_job, cls.zombie_prepare_role_state))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zombie_attack_alarm_handle = None
        self._registered_test_events = set()
        self._player_health_tracking_situation_goal = None
        self._statistic_watcher_handle = None
        self._victory = False

    @property
    def end_audio_sting(self):
        if self._victory:
            return self.victory_audio_sting
        return self.defeat_audio_sting

    def _get_reward(self):
        if self._victory:
            return self.victory_reward

    def _get_motherplant(self):
        return next(iter(services.object_manager().get_objects_of_type_gen(self.mother_plant_definition)))

    def _push_loss_on_player(self):
        motherplant = self._get_motherplant()
        for (sim, situation_sim) in self._situation_sims.items():
            if situation_sim.current_job_type is self.player_job:
                parent_si = sim.si_state.get_si_by_affordance(self.fight_affordance)
                if parent_si is not None:
                    interaction_context = InteractionContext(sim, InteractionSource.PIE_MENU, Priority.Critical)
                    aop = AffordanceObjectPair(self.loss_interaction_mixer, motherplant, self.fight_affordance, parent_si)
                    if not aop.test_and_execute(interaction_context):
                        logger.error('Attempting to push Motherplant Battle Ending Interaction, but failed.')
        self._push_interaction_on_all_helpers(self.helper_lose_affordance)

    def on_goal_completed(self, goal):
        super().on_goal_completed(goal)
        self._push_loss_on_player()
        self._self_destruct()

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        if job_type is self.zombie_job:
            sim.add_buff_from_op(self.possessed_buff.buff_type, buff_reason=self.possessed_buff.buff_reason)

    def _on_statistic_updated(self, stat_type, old_value, new_value):
        if stat_type is self.player_health_statistic:
            self._player_health_tracking_situation_goal.set_count(new_value)
            self._player_health_meter.send_update_if_dirty()
        elif stat_type is self.motherplant_health_statisic:
            self._mother_plant_meter.send_update_if_dirty()

    def _zombie_attack(self, _):
        if not self._cur_state.zombie_attack_valid:
            return
        zombies = []
        for (sim, situation_sim) in self._situation_sims.items():
            if situation_sim.current_job_type is self.zombie_job:
                zombies.append(sim)
        zombie_to_attack = random.choice(zombies)
        context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.High, insert_strategy=QueueInsertStrategy.NEXT, bucket=interactions.context.InteractionBucketType.DEFAULT)
        zombie_to_attack.push_super_affordance(self.zombie_fight_interaction, None, context)

    def _push_interaction_on_all_helpers(self, interaction_to_push):
        for (sim, situation_sim) in self._situation_sims.items():
            if not situation_sim.current_job_type is self.helper_2_job:
                if situation_sim.current_job_type is self.helper_3_job:
                    context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.High, insert_strategy=QueueInsertStrategy.NEXT, bucket=interactions.context.InteractionBucketType.DEFAULT)
                    sim.push_super_affordance(interaction_to_push, None, context)
            context = InteractionContext(sim, InteractionContext.SOURCE_SCRIPT, interactions.priority.Priority.High, insert_strategy=QueueInsertStrategy.NEXT, bucket=interactions.context.InteractionBucketType.DEFAULT)
            sim.push_super_affordance(interaction_to_push, None, context)

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event != TestEvent.InteractionComplete:
            return
        if resolver(self.victory_interaction_of_interest):
            self._push_interaction_on_all_helpers(self.helper_victory_affordance)
            self._victory = True
            self._self_destruct()
        elif resolver(self.retreat_interaction_of_interest):
            self._push_loss_on_player()
            self._self_destruct()

    def start_situation(self):
        services.get_persistence_service().lock_save(self)
        super().start_situation()
        self._change_state(PrepareForBattleSituationState())
        motherplant = self._get_motherplant()
        motherplant.set_stat_value(self.player_health_statistic, 0, add=True)
        motherplant.set_stat_value(self.motherplant_health_statisic, self.motherplant_health_statisic.max_value, add=True)
        for state_value in self.states_to_set_on_start:
            motherplant.set_state(state_value.state, state_value)
        statistic_tracker = motherplant.statistic_tracker
        self._statistic_watcher_handle = statistic_tracker.add_watcher(self._on_statistic_updated)
        self._setup_situation_meters()
        self._zombie_attack_alarm_handle = alarms.add_alarm(self, create_time_span(minutes=self.zombie_fight_interaction_timer), self._zombie_attack, repeating=True)
        for custom_key in itertools.chain(self.victory_interaction_of_interest.custom_keys_gen(), self.retreat_interaction_of_interest.custom_keys_gen()):
            custom_key_tuple = (TestEvent.InteractionComplete, custom_key)
            self._registered_test_events.add(custom_key_tuple)
            services.get_event_manager().register_with_custom_key(self, TestEvent.InteractionComplete, custom_key)

    def _setup_situation_meters(self):
        motherplant = self._get_motherplant()
        self._mother_plant_meter = self.mother_plant_meter_settings.create_meter_with_sim_info(self, motherplant)
        self._player_health_meter = self.player_health_meter_settings.create_meter_with_sim_info(self, motherplant)

    def build_situation_start_message(self):
        msg = super().build_situation_start_message()
        with ProtocolBufferRollback(msg.meter_data) as meter_data_msg:
            self.mother_plant_meter_settings.build_data_message(meter_data_msg)
        with ProtocolBufferRollback(msg.meter_data) as meter_data_msg:
            self.player_health_meter_settings.build_data_message(meter_data_msg)
        build_icon_info_msg(IconInfoData(icon_resource=self.mother_plant_icon), None, msg.icon_info)
        return msg

    def _destroy(self):
        super()._destroy()
        services.get_persistence_service().unlock_save(self)
        for (event_type, custom_key) in self._registered_test_events:
            services.get_event_manager().unregister_with_custom_key(self, event_type, custom_key)
        motherplant = self._get_motherplant()
        statistic_tracker = motherplant.statistic_tracker
        statistic_tracker.remove_watcher(self._statistic_watcher_handle)
        for state_value in self.states_to_set_on_end:
            motherplant.set_state(state_value.state, state_value)
        self._registered_test_events.clear()
        if self._mother_plant_meter is not None:
            self._mother_plant_meter.destroy()
        if self._player_health_meter is not None:
            self._player_health_meter.destroy()

    def get_lock_save_reason(self):
        return self.save_lock_tooltip

    def set_motherplant_situation_state(self, motherplant_battle_state):
        if motherplant_battle_state == MotherplantBattleStates.ATTACK:
            self._change_state(self.attack_battle_situation_state())
        elif motherplant_battle_state == MotherplantBattleStates.INSPIRE:
            self._change_state(self.inspire_battle_situation_state())
        elif motherplant_battle_state == MotherplantBattleStates.RALLY:
            self._change_state(self.rally_battle_sitaution_state())
        elif motherplant_battle_state == MotherplantBattleStates.WARBLING_WARCRY:
            self._change_state(self.warbling_warcry_battle_situation_state())

    def _on_proxy_situation_goal_added(self, goal):
        self._player_health_tracking_situation_goal = goal

    def _issue_requests(self):
        super()._issue_requests()
        request = SelectableSimRequestFactory(self, _RequestUserData(), self.other_player_jobs, self.exclusivity, request_priority=BouncerRequestPriority.EVENT_DEFAULT_JOB)
        self.manager.bouncer.submit_request(request)
lock_instance_tunables(MotherPlantBattleSituation, audio_sting_on_start=None, main_goal_audio_sting=None)