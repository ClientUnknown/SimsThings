from buffs.buff import Bufffrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonSituationState, SituationStateData, CommonInteractionCompletedSituationState, TunableSituationJobAndRoleStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_types import SituationCreationUIOption, SituationSerializationOptionimport servicesimport sims4.loglogger = sims4.log.Logger('EveryoneTakeATurnOnceSituation', default_owner='jwilkinson')
class GatherTogetherState(CommonInteractionCompletedSituationState):

    def timer_expired(self):
        self.owner.cleanup_expired_sims()
        if self.owner is None:
            return
        self._change_state(self.owner.taking_turns_state())

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, self.owner.target_object)

    def handle_event(self, sim_info, event, resolver):
        try:
            self._sim_info = sim_info
            super().handle_event(sim_info, event, resolver)
        finally:
            self._sim_info = None

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner.set_sim_as_ready(self._sim_info)
        if not self.owner.gathering_sim_ids:
            self._change_state(self.owner.taking_turns_state())

class TakingTurnsState(CommonSituationState):

    def on_activate(self, reader=None):
        self.owner.do_next_turn(set_others_waiting=True)
        if self.owner is None:
            return
        super().on_activate(reader=reader)

class EveryoneTakeATurnOnceSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'gather_together_state': GatherTogetherState.TunableFactory(description='\n            The state of the situation when the situation first starts,\n            which lasts until every sim is in place and ready to take a turn.\n            ', tuning_group=GroupNames.STATE), 'taking_turns_state': TakingTurnsState.TunableFactory(description='\n            The state that means all Sims have gathered and are taking turns.\n            ', tuning_group=GroupNames.STATE), 'job_and_role_state': TunableSituationJobAndRoleState(description='\n            Job and Role State.\n            '), 'sim_took_turn_buff': Buff.TunableReference(description='\n            The buff that is on a Sim that has already taken a turn.\n            '), 'sub_situation': Situation.TunableReference(description='\n            Each participating Sim will in their own instance of this situation.\n            ', class_restrictions=('EveryoneTakeATurnOnceSubSituation',))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._guest_sub_situation_dict = {}
        self.gathering_sim_ids = set()
        self._ready_sim_ids = set()
        self.target_object = self._get_target_object()

    def _get_target_object(self):
        target_object = None
        default_target_id = self._seed.extra_kwargs.get('default_target_id', None)
        if default_target_id is not None:
            target_object = services.object_manager().get(default_target_id)
        return target_object

    def _get_sub_situations(self):
        sub_situations = set()
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None:
            return sub_situations
        for situation_id in self._guest_sub_situation_dict.values():
            situation = situation_manager.get(situation_id)
            if situation is not None:
                sub_situations.add(situation)
        return sub_situations

    @classmethod
    def default_job(cls):
        return cls.job_and_role_state.job

    @classmethod
    def _states(cls):
        return [SituationStateData(1, GatherTogetherState, factory=cls.gather_together_state), SituationStateData(2, TakingTurnsState, factory=cls.taking_turns_state)]

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.job_and_role_state.job, cls.job_and_role_state.role_state)]

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        situation_manager = services.get_zone_situation_manager()
        guest_list = SituationGuestList(invite_only=True)
        guest_list.add_guest_info(SituationGuestInfo(sim.sim_id, self.sub_situation.job_and_role_state.job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP))
        sub_situation_id = situation_manager.create_situation(self.sub_situation, guest_list=guest_list, background_situation_id=self.id, user_facing=False)
        self._guest_sub_situation_dict[sim.id] = sub_situation_id
        self.gathering_sim_ids.add(sim.id)

    def _get_sub_situation_for_sim_id(self, sim_id):
        sub_situation = None
        sub_situation_id = self._guest_sub_situation_dict.get(sim_id, None)
        if sub_situation_id is not None:
            situation_manager = services.get_zone_situation_manager()
            if situation_manager is not None:
                sub_situation = situation_manager.get(sub_situation_id)
        return sub_situation

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        self.gathering_sim_ids.discard(sim.id)
        sub_situation = self._get_sub_situation_for_sim_id(sim.id)
        if sub_situation is not None:
            situation_manager = services.get_zone_situation_manager()
            situation_manager.destroy_situation_by_id(sub_situation.id)
        self._guest_sub_situation_dict.pop(sim.id, None)

    def _destroy(self):
        self._cleanup_sub_situations()
        super()._destroy()

    def start_situation(self):
        super().start_situation()
        self._change_state(self.gather_together_state())

    def set_sim_as_ready(self, sim_info):
        if sim_info is not None:
            self.gathering_sim_ids.discard(sim_info.id)
            if not sim_info.has_buff(self.sim_took_turn_buff.buff_type):
                self._ready_sim_ids.add(sim_info.id)

    def do_next_turn(self, set_others_waiting=False):
        if self._ready_sim_ids:
            sim_id = self._ready_sim_ids.pop()
            sub_situation = self._get_sub_situation_for_sim_id(sim_id)
            if sub_situation is not None:
                if self._ready_sim_ids:
                    if set_others_waiting:
                        for waiting_sims_id in self._ready_sim_ids:
                            waiting_sub_situation = self._get_sub_situation_for_sim_id(waiting_sims_id)
                            if waiting_sub_situation is not None:
                                waiting_sub_situation.wait_for_turn()
                    sub_situation.take_turn()
                else:
                    sub_situation.take_last_turn()
                return
        self._self_destruct()

    def cleanup_expired_sims(self):
        sim_info_manager = services.sim_info_manager()
        for sim_id in tuple(self.gathering_sim_ids):
            sim_info = sim_info_manager.get(sim_id)
            if sim_info is not None:
                sim = sim_info.get_sim_instance()
                if sim is not None and self.is_sim_in_situation(sim):
                    self.remove_sim_from_situation(sim)

    def _cleanup_sub_situations(self):
        for situation in self._get_sub_situations():
            if situation is not None:
                situation._self_destruct()
lock_instance_tunables(EveryoneTakeATurnOnceSituation, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)
class WaitState(CommonSituationState):

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, self.owner.background_situation.target_object)

class TakeTurnState(CommonInteractionCompletedSituationState):

    def __init__(self, *args, last_turn=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_turn = last_turn

    def _finish_turn(self):
        owning_situation = self.owner
        if not self._last_turn:
            self._change_state(self.owner.sim_wait_state())
        owning_situation.background_situation.do_next_turn()

    def timer_expired(self):
        self._finish_turn()

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, self.owner.background_situation.target_object)

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.is_sim_info_in_situation(sim_info)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._finish_turn()

class EveryoneTakeATurnOnceSubSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'sim_wait_state': WaitState.TunableFactory(description='\n            The state of Sims who are not currently taking a turn.\n            ', tuning_group=GroupNames.STATE), 'take_turn_state': TakeTurnState.TunableFactory(description='\n            The state of Sims who are taking a turn.\n            ', tuning_group=GroupNames.STATE), 'take_last_turn_state': TakeTurnState.TunableFactory(description='\n            The state of the Sim who are taking a last turn.\n            ', tuning_group=GroupNames.STATE, locked_args={'last_turn': True}), 'job_and_role_state': TunableSituationJobAndRoleState(description='\n            Job and Role State.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, seed, *args, **kwargs):
        super().__init__(seed, *args, **kwargs)
        background_situation_id = seed.extra_kwargs.get('background_situation_id', None)
        self.background_situation = self._get_background_situation(background_situation_id)

    def _get_background_situation(self, background_situation_id):
        background_situation = None
        if background_situation_id is not None:
            background_situation = services.current_zone().situation_manager.get(background_situation_id)
        if background_situation is None:
            logger.error('Background situation id was None when attempting to create a sub situation for the Everyone Take a Turn Once Situation')
        return background_situation

    @classproperty
    def situation_serialization_option(cls):
        return SituationSerializationOption.DONT

    @classmethod
    def _states(cls):
        return [SituationStateData(1, WaitState, factory=cls.sim_wait_state), SituationStateData(2, TakeTurnState, factory=cls.take_turn_state), SituationStateData(3, TakeTurnState, factory=cls.take_last_turn_state)]

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.job_and_role_state.job, cls.job_and_role_state.role_state)]

    @classmethod
    def default_job(cls):
        pass

    def wait_for_turn(self):
        self._change_state(self.sim_wait_state())

    def take_turn(self):
        self._change_state(self.take_turn_state())

    def take_last_turn(self):
        self._change_state(self.take_last_turn_state())
lock_instance_tunables(EveryoneTakeATurnOnceSituation, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False, duration=0)