import randomfrom date_and_time import create_time_spanfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReference, Tunable, TunableSimMinutefrom sims4.utils import classpropertyfrom situations.base_situation import _RequestUserDatafrom situations.bouncer.bouncer_request import SelectableSimRequestFactoryfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonSituationState, CommonInteractionCompletedSituationState, SituationStateDatafrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_types import SituationCreationUIOption, SituationSerializationOptionfrom zone_director import ZoneDirectorBaseimport alarmsimport servicesimport sims4.resources
class WaitForTurnState(CommonSituationState):
    pass

class TakeTurnState(CommonInteractionCompletedSituationState):

    def timer_expired(self):
        self.owner.on_turn_finished()

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner.on_turn_finished()

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner is not None and self.owner.sim_of_interest(sim_info):
            return True
        return False

class OpenMicContestant(SituationComplexCommon):
    INSTANCE_TUNABLES = {'wait_for_turn_state': WaitForTurnState.TunableFactory(locked_args={'time_out': None, 'allow_join_situation': True}), 'take_turn_state': TakeTurnState.TunableFactory(locked_args={'allow_join_situation': True}), 'contestant_job': TunableReference(description='\n            The job for the contestant Sim.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, WaitForTurnState, factory=cls.wait_for_turn_state), SituationStateData(2, TakeTurnState, factory=cls.take_turn_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.wait_for_turn_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def default_job(cls):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._contestant_sim = None

    def start_situation(self):
        super().start_situation()
        self._change_state(self.wait_for_turn_state())

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._contestant_sim = sim

    def sim_of_interest(self, sim_info):
        if self._contestant_sim is not None and self._contestant_sim.sim_info is sim_info:
            return True
        return False

    def start_turn(self):
        self._change_state(self.take_turn_state())

    def on_turn_finished(self):
        self._change_state(self.wait_for_turn_state())
        services.venue_service().get_zone_director().select_next_contestant()
lock_instance_tunables(OpenMicContestant, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0, _implies_greeted_status=False)
class PlayerSituationState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, sim_info=None, **kwargs):
        if sim_info is None:
            return
        services.venue_service().get_zone_director().request_player_turn(sim_info)

class OpenMicPlayerControllerSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'situation_state': PlayerSituationState.TunableFactory(locked_args={'time_out': None, 'allow_join_situation': True}), 'player_job': TunableReference(description='\n            The job for the player Sim.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, PlayerSituationState, factory=cls.situation_state),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.situation_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def default_job(cls):
        pass

    @classproperty
    def situation_serialization_option(cls):
        return SituationSerializationOption.DONT

    def start_situation(self):
        super().start_situation()
        self._change_state(self.situation_state())

    def _issue_requests(self):
        request = SelectableSimRequestFactory(self, _RequestUserData(), self.player_job, self.exclusivity)
        self.manager.bouncer.submit_request(request)
NPC_CONTESTANTS_TOKEN = 'npc_contestants'PLAYER_CONTESTANTS_TOKEN = 'player_contestants'CURRENT_CONTESTANT_TOKEN = 'current_contestant'
class OpenMicNightZoneDirector(ZoneDirectorBase):
    INSTANCE_TUNABLES = {'bartender_situation': TunableReference(description='\n            The situation for the bar tender.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION)), 'bartender_count': Tunable(description='\n            The number of bar tenders that we want at the open mic night.\n            ', tunable_type=int, default=1), 'npc_contestant_situation': TunableReference(description='\n            The open mic contestant situation for npcs.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION)), 'npc_contestant_count': Tunable(description='\n            The number of npc contestants that we want at the open mic night.\n            ', tunable_type=int, default=1), 'player_contestant_situation': TunableReference(description='\n            The open mic contestant situation for player Sims\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION)), 'player_controller_situation': TunableReference(description='\n            The situation for player Sims to control them \n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION)), 'check_contestant_alarm_timer': TunableSimMinute(description='\n            The amount of time we will wait between checks to add a contestant\n            if there is not a contestant currently taking their turn.\n            ', default=10, minimum=1)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._npc_contestant_sitaution_ids = []
        self._player_contestant_situation_ids = []
        self._current_contestant_situation_id = None
        self._select_next_contestant_alarm = None

    def _check_for_contestant(self, _):
        if self._current_contestant_situation_id is None:
            self.select_next_contestant()

    def on_startup(self):
        self._select_next_contestant_alarm = alarms.add_alarm(self, create_time_span(minutes=self.check_contestant_alarm_timer), self._check_for_contestant, repeating=True)
        super().on_startup()
        if services.current_zone().is_zone_running:
            self.create_situations_during_zone_spin_up()

    def on_shutdown(self):
        if self._select_next_contestant_alarm is not None:
            self._select_next_contestant_alarm.cancel()
            self._select_next_contestant_alarm = None
        situation_manager = services.get_zone_situation_manager()
        self._player_contestant_situation_ids = self._prune_stale_situations(self._player_contestant_situation_ids)
        for situation_id in self._player_contestant_situation_ids:
            situation_manager.destroy_situation_by_id(situation_id)
        self._npc_contestant_sitaution_ids = self._prune_stale_situations(self._npc_contestant_sitaution_ids)
        for situation_id in self._npc_contestant_sitaution_ids:
            situation_manager.destroy_situation_by_id(situation_id)
        player_controller_situation = situation_manager.get_situation_by_type(self.player_controller_situation)
        if player_controller_situation is not None:
            situation_manager.destroy_situation_by_id(player_controller_situation.id)
        super().on_shutdown()

    def create_situations_during_zone_spin_up(self):
        situation_manager = services.get_zone_situation_manager()
        self._npc_contestant_sitaution_ids = self._prune_stale_situations(self._npc_contestant_sitaution_ids)
        while len(self._npc_contestant_sitaution_ids) < self.npc_contestant_count:
            guest_list = SituationGuestList(invite_only=True)
            situation_id = situation_manager.create_situation(self.npc_contestant_situation, guest_list=guest_list, user_facing=False, scoring_enabled=False, spawn_sims_during_zone_spin_up=True)
            self._npc_contestant_sitaution_ids.append(situation_id)
        if situation_manager.get_situation_by_type(self.bartender_situation) is None:
            guest_list = SituationGuestList(invite_only=True)
            situation_manager.create_situation(self.bartender_situation, guest_list=guest_list, user_facing=False, scoring_enabled=False, spawn_sims_during_zone_spin_up=True)
        guest_list = SituationGuestList(invite_only=True)
        situation_manager.create_situation(self.player_controller_situation, guest_list=guest_list, user_facing=False, scoring_enabled=False)

    def request_player_turn(self, sim_info):
        guest_list = SituationGuestList(invite_only=True)
        guest_list.add_guest_info(SituationGuestInfo(sim_info.sim_id, self.player_contestant_situation.contestant_job, RequestSpawningOption.CANNOT_SPAWN, BouncerRequestPriority.EVENT_VIP))
        situation_id = services.get_zone_situation_manager().create_situation(self.player_contestant_situation, guest_list=guest_list, user_facing=False, scoring_enabled=False)
        if situation_id is None:
            return
        self._player_contestant_situation_ids.append(situation_id)

    def select_next_contestant(self):
        self._player_contestant_situation_ids = self._prune_stale_situations(self._player_contestant_situation_ids)
        self._npc_contestant_sitaution_ids = self._prune_stale_situations(self._npc_contestant_sitaution_ids)
        if self._player_contestant_situation_ids:
            self._current_contestant_situation_id = self._player_contestant_situation_ids.pop(0)
        else:
            possible_contestants = [situation_id for situation_id in self._npc_contestant_sitaution_ids if self._current_contestant_situation_id is None or situation_id != self._current_contestant_situation_id]
            if not possible_contestants:
                self._current_constestant_situation_id = None
                return
            self._current_contestant_situation_id = random.choice(possible_contestants)
        situation_manager = services.get_zone_situation_manager()
        situation = situation_manager.get(self._current_contestant_situation_id)
        situation.start_turn()

    def _load_custom_zone_director(self, zone_director_proto, reader):
        self._npc_contestant_sitaution_ids = reader.read_uint64s(NPC_CONTESTANTS_TOKEN, [])
        self._player_contestant_situation_ids = reader.read_uint64s(PLAYER_CONTESTANTS_TOKEN, [])
        self._current_contestant_situation_id = reader.read_uint64(CURRENT_CONTESTANT_TOKEN, None)

    def _save_custom_zone_director(self, zone_director_proto, writer):
        writer.write_uint64s(NPC_CONTESTANTS_TOKEN, self._npc_contestant_sitaution_ids)
        writer.write_uint64s(PLAYER_CONTESTANTS_TOKEN, self._player_contestant_situation_ids)
        if self._current_contestant_situation_id is not None:
            writer.write_uint64(CURRENT_CONTESTANT_TOKEN, self._current_contestant_situation_id)
