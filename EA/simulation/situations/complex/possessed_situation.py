from buffs.tunable import TunableBuffReferencefrom date_and_time import TimeSpanfrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import classpropertyfrom situations.base_situation import _RequestUserDatafrom situations.bouncer.bouncer_types import BouncerRequestPriorityfrom situations.bouncer.specific_sim_request_factory import SpecificSimRequestFactoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonSituationState, SituationStateData, TunableSituationJobAndRoleState, CommonInteractionCompletedSituationState, CommonInteractionStartedSituationState, SituationStatefrom situations.situation_types import SituationSerializationOptionfrom situations.sub_situation_mixin import SubSituationMixinimport alarmsimport servicesimport sims4.loglogger = sims4.log.Logger('PossessedSituation', default_owner='tingyul')
class WaitForSimAssignment(SituationState):

    def _on_set_sim_role_state(self, sim, *args, **kwargs):
        super()._on_set_sim_role_state(sim, *args, **kwargs)
        self.owner._on_sim_assigned()

class _AnimatePossessionState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.possessed_state())

    def _additional_tests(self, sim_info, event, resolver):
        return sim_info is self.owner.sim_info

    def timer_expired(self):
        logger.error('Failed to run possession interaction.')
        self._change_state(self.owner.possessed_state())

class _PossessedState(CommonSituationState):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._possession_check_alarm_handle = None

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        self.schedule_possession_refresh()
        self.owner.sim_info.Buffs.on_buff_removed.register(self._on_buff_removed)

    def on_deactivate(self):
        if self._possession_check_alarm_handle is not None:
            self._possession_check_alarm_handle.cancel()
            self._possession_check_alarm_handle = None
        self.owner.sim_info.sim_info.Buffs.on_buff_removed.unregister(self._on_buff_removed)
        super().on_deactivate()

    def schedule_possession_refresh(self):
        if self._possession_check_alarm_handle is not None:
            return
        self._possession_check_alarm_handle = alarms.add_alarm(self, TimeSpan.ZERO, self._refresh_possession)

    def _refresh_possession(self, e):
        self._possession_check_alarm_handle = None
        buff_type = self.owner.possessed_buff.buff_type
        (buff, buff_duration) = self.owner.owner_situation.get_possession_source()
        if buff is None:
            if self.owner._animate_possession:
                self._change_state(self.owner.animate_timeout_state())
            else:
                self.owner._self_destruct()
            return
        buff_reason = buff.buff_reason
        if buff_reason is None:
            buff_reason = self.owner.possessed_buff.buff_reason
        if self.owner.sim_info.has_buff(buff_type):
            self.owner.sim_info.set_buff_reason(buff_type, buff_reason)
        else:
            self.owner.sim_info.add_buff_from_op(buff_type, buff_reason=buff_reason)
        buff_commodity = self.owner.sim_info.get_statistic(buff_type.commodity, add=False)
        if buff_duration is None:
            if not buff_commodity.has_decay_rate_modifier(0):
                buff_commodity.add_decay_rate_modifier(0)
            buff_commodity.set_value(buff_commodity.max_value)
        else:
            buff_commodity.set_value(buff_duration + 1)
            if buff_commodity.has_decay_rate_modifier(0):
                buff_commodity.remove_decay_rate_modifier(0)

    def _on_buff_removed(self, buff_type, owner_sim_id):
        if buff_type is self.owner.possessed_buff.buff_type:
            self.owner._self_destruct()

class _AnimateTimeoutState(CommonInteractionStartedSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        buff = self.owner.sim_info.Buffs.get_buff_by_type(self.owner.possessed_buff.buff_type)
        if buff is not None:
            commodity = buff.get_commodity_instance()
            if commodity is not None:
                commodity.add_decay_rate_modifier(0)

    def on_deactivate(self):
        self.owner._clean_up_possession_buff()
        super().on_deactivate()

    def _on_interaction_of_interest_started(self, **kwargs):
        self._end_state()

    def _additional_tests(self, sim_info, event, resolver):
        return sim_info is self.owner.sim_info

    def timer_expired(self):
        logger.error('Failed to run timeout interaction.')
        self._end_state()

    def _end_state(self):
        (buff, _) = self.owner.owner_situation.get_possession_source()
        if buff is not None:
            self._change_state(self.animate_possession_state())
        else:
            self.owner._self_destruct()

class PossessedSituation(SubSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'default_job_and_role': TunableSituationJobAndRoleState(description='\n            The job the possessed Sim will be in.\n            ', tuning_group=GroupNames.SITUATION), 'animate_possession_state': _AnimatePossessionState.TunableFactory(display_name='0. Animate Possession State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'possessed_state': _PossessedState.TunableFactory(display_name='1. Possessed State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'animate_timeout_state': _AnimateTimeoutState.TunableFactory(display_name='2. Animate Timeout State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'possessed_buff': TunableBuffReference(description='\n            The visible possession buff. The reason can potentially be\n            overridden by the actual source of possession, e.g. time or from\n            eating infected fruit.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, seed, **kwargs):
        super().__init__(seed, **kwargs)
        self._animate_possession = seed.extra_kwargs.get('animate_possession', True)
        self.sim_info = services.sim_info_manager().get(self._guest_list.host_sim_id)

    @classmethod
    def _states(cls):
        return (SituationStateData.from_auto_factory(0, cls.animate_possession_state), SituationStateData.from_auto_factory(1, cls.possessed_state), SituationStateData.from_auto_factory(2, cls.animate_timeout_state), SituationStateData(3, WaitForSimAssignment))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return ((cls.default_job_and_role.job, cls.default_job_and_role.role_state),)

    @classmethod
    def default_job(cls):
        pass

    @classproperty
    def situation_serialization_option(cls):
        return SituationSerializationOption.DONT

    def start_situation(self):
        super().start_situation()
        if self.sim_info is None:
            self._self_destruct()
            return
        self._change_state(WaitForSimAssignment())

    def _on_sim_assigned(self):
        if self._animate_possession:
            self._change_state(self.animate_possession_state())
        else:
            self._change_state(self.possessed_state())

    def _issue_requests(self):
        request = SpecificSimRequestFactory(self, _RequestUserData(), self.default_job_and_role.job, BouncerRequestPriority.EVENT_DEFAULT_JOB, self.exclusivity, self._guest_list.host_sim_id)
        self.manager.bouncer.submit_request(request)

    def post_remove(self):
        super().post_remove()
        self._clean_up_possession_buff()
        self.sim_info = None

    def on_possession_sources_changed(self):
        if isinstance(self._cur_state, _PossessedState):
            self._cur_state.schedule_possession_refresh()

    def _clean_up_possession_buff(self):
        if self.sim_info is not None:
            self.sim_info.remove_buff_by_type(self.possessed_buff.buff_type)
            sim = self.sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if sim is not None:
                sim.update_animation_overlays()
