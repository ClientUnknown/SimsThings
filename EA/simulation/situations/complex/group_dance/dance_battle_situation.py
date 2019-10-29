from event_testing.test_events import TestEventfrom interactions.interaction_finisher import FinishingTypefrom sims4.tuning.tunable import TunableReference, TunableRangefrom situations.complex.group_dance.group_dance_situation import GroupDanceSituationfrom situations.situation_complex import CommonInteractionCompletedSituationState, SituationStateDataimport event_testingimport servicesimport sims4.loglogger = sims4.log.Logger('DanceBattle', default_owner='trevor')
class _DanceBattleStateBase(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        next_state = self.owner.get_next_dance_state()
        self._change_state(next_state())

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionComplete and resolver._interaction.affordance is self.owner.constraint_affordance:
            self.owner._self_destruct()
        super().handle_event(sim_info, event, resolver)

class _DanceBattleDanceState(_DanceBattleStateBase):
    pass

class _DanceBattleWatchState(_DanceBattleStateBase):
    pass

class _DanceBattleReactState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()
DANCE_GROUP = 'Dance'
class DanceBattleSituation(GroupDanceSituation):
    INSTANCE_TUNABLES = {'dance_state': _DanceBattleDanceState.TunableFactory(description='\n            The first situation state where the leader Sim dances and the\n            follower watches.\n            ', tuning_group=DANCE_GROUP), 'watch_state': _DanceBattleWatchState.TunableFactory(description='\n            The second situation state where the leader Sim watches and the\n            follower Sim dances.\n            ', tuning_group=DANCE_GROUP), 'react_state': _DanceBattleReactState.TunableFactory(description='\n            The final situation state where the Sims will react to their\n            performance.\n            ', tuning_group=DANCE_GROUP), 'dance_battle_jig': TunableReference(description='\n            The jig to use for the dance battle.\n            ', manager=services.definition_manager(), tuning_group=DANCE_GROUP), 'number_of_battles': TunableRange(description='\n            This is the number of times the Dance->Watch cycle will happen\n            before the react state happens and the situation ultimately ends.\n            ', tunable_type=int, default=1, minimum=1, tuning_group=DANCE_GROUP)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._battle_count = 0

    @classmethod
    def _states(cls):
        base_states = super()._states()
        situation_states = [SituationStateData(2, _DanceBattleDanceState, cls.dance_state), SituationStateData(3, _DanceBattleWatchState, cls.watch_state), SituationStateData(4, _DanceBattleReactState, cls.react_state)]
        return base_states + tuple(situation_states)

    def _check_route_sim(self, sim):
        if self.num_of_sims == self.num_invited_sims:
            self._create_situation_geometry()
            for sim in self.all_sims_in_situation_gen():
                self._route_sim(sim, self.get_and_increment_sim_jig_index(sim))
            self._change_state(self.pre_situation_state.situation_state())

    def _self_destruct(self):
        for sim in self.all_sims_in_situation_gen():
            for si in list(sim.running_interactions_gen(self.constraint_affordance)):
                si.cancel(FinishingType.SITUATIONS, cancel_reason_msg='Dance Battle Ended.')
        super()._self_destruct()

    def get_jig_definition(self):
        return self.dance_battle_jig

    def get_next_dance_state(self):
        if isinstance(self._cur_state, _DanceBattleWatchState):
            self._battle_count += 1
            if self._battle_count >= self.number_of_battles:
                return self.react_state
            return self.dance_state
        if isinstance(self._cur_state, _DanceBattleDanceState):
            return self.watch_state
        return self.dance_state
