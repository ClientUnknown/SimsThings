from interactions.aop import AffordanceObjectPairfrom interactions.context import InteractionContext, InteractionSourcefrom interactions.priority import Priorityfrom sims4.tuning.tunable import TunableSimMinute, TunableReferencefrom sims4.utils import classpropertyfrom situations.situation import Situationfrom situations.situation_complex import CommonInteractionCompletedSituationState, CommonSituationState, SituationComplexCommon, SituationStateDatafrom situations.situation_types import SituationSerializationOptionfrom tunable_time import TunableTimeOfDayimport alarmsimport clockimport services
class CelebrateState(CommonSituationState):
    pass

class CountdownState(CommonSituationState):
    FACTORY_TUNABLES = {'countdown_affordance': TunableReference(manager=services.affordance_manager()), 'count_mixer': TunableReference(manager=services.affordance_manager()), 'celebrate_time': TunableTimeOfDay(description='\n            Time of Day to Celebrate\n            ', default_hour=0), 'time_to_start_count': TunableTimeOfDay(description='\n            Time to start performing the Count.\n            ', default_hour=11, default_minute=30), 'interval_between_counts': TunableSimMinute(description='\n            The interval between each count animation.\n            ', minimum=1, default=5)}

    def __init__(self, *args, countdown_affordance=None, count_mixer=None, celebrate_time=None, time_to_start_count=None, interval_between_counts=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.countdown_affordance = countdown_affordance
        self.count_mixer = count_mixer
        self.celebrate_time = celebrate_time
        self.time_to_start_count = time_to_start_count
        self.interval_between_counts = interval_between_counts
        self._celebrate_timer = None
        self._count_timer = None

    def _count_callback(self, _):
        for sim in self.owner.all_sims_in_situation_gen():
            parent_si = sim.si_state.get_si_by_affordance(self.countdown_affordance)
            if parent_si is not None:
                interaction_context = InteractionContext(sim, InteractionSource.PIE_MENU, Priority.Critical)
                aop = AffordanceObjectPair(self.count_mixer, None, self.countdown_affordance, parent_si)
                aop.test_and_execute(interaction_context)

    def _celebrate_callback(self, _):
        self._change_state(self.owner.celebrate_state())

    def on_activate(self, reader=None):
        super().on_activate(reader)
        now = services.game_clock_service().now()
        time_till_first_count = now.time_till_next_day_time(self.time_to_start_count)
        time_till_celebration = now.time_till_next_day_time(self.celebrate_time)
        repeat_time_span = clock.interval_in_sim_minutes(self.interval_between_counts)
        if time_till_first_count > time_till_celebration:
            time_of_first_count = now + time_till_first_count + clock.interval_in_sim_days(-1)
            time_since_first_count = now - time_of_first_count
            time_of_next_count = time_of_first_count + repeat_time_span*(int(time_since_first_count.in_ticks()/repeat_time_span.in_ticks()) + 1)
            time_till_first_count = time_of_next_count - now
        self._count_timer = alarms.add_alarm(self, time_till_first_count, self._count_callback, repeating=True, repeating_time_span=repeat_time_span)
        self._celebrate_timer = alarms.add_alarm(self, time_till_celebration, self._celebrate_callback)

    def on_deactivate(self):
        super().on_deactivate()
        if self._count_timer is not None:
            alarms.cancel_alarm(self._count_timer)
            self._count_timer = None
        if self._celebrate_timer is not None:
            alarms.cancel_alarm(self._celebrate_timer)
            self._celebrate_timer = None

class CountdownSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'celebrate_state': CelebrateState.TunableFactory(locked_args={'time_out': None, 'allow_join_situation': None}), 'countdown_state': CountdownState.TunableFactory(locked_args={'time_out': None, 'allow_join_situation': None})}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, CountdownState, factory=cls.countdown_state), SituationStateData(2, CelebrateState, factory=cls.celebrate_state))

    @classproperty
    def situation_serialization_option(cls):
        return SituationSerializationOption.DONT

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.countdown_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def default_job(cls):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._celebrate_timer = None
        self._count_timer = None

    def start_situation(self):
        super().start_situation()
        self._change_state(self.countdown_state())
