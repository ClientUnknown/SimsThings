from date_and_time import create_time_span, TimeSpanfrom event_testing.resolver import SingleSimResolverfrom sims4.repr_utils import standard_reprfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, TunableIntervalfrom tunable_multiplier import TunableMultiplierfrom uid import unique_idimport servicesimport sims4.resources
@unique_id('action_id')
class StoryProgressionAction(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.STORY_PROGRESSION_ACTION)):
    INSTANCE_TUNABLES = {'duration': TunableInterval(description='\n            How long it takes for the Sim to execute this action. Sims can run a\n            limited number of actions at any given time, meaning an action locks\n            them up for a certain duration. That duration is randomly determined\n            by this interval.\n            ', tunable_type=int, default_lower=1440, default_upper=4320, minimum=0), 'score': TunableMultiplier.TunableFactory(description="\n            Define the base score of this action. The score affects the\n            likelihood that this action is picked compared to other actions that\n            the Sim is considering. The score is affected by the change in error\n            to the world's balance.\n            ")}

    def __init__(self, sim_info):
        self._sim_info = sim_info
        self._duration = None
        self._alarm_handle = None

    def __repr__(self):
        return standard_repr(self)

    def load(self, data):
        if data.duration:
            self._duration = TimeSpan(data.duration)

    def save(self, data):
        data.guid = self.guid64
        duration = self.get_duration()
        if duration is not None:
            data.duration = duration.in_ticks()

    @classmethod
    def get_potential_actions_gen(cls, sim_info):
        yield cls(sim_info)

    def cancel_action(self):
        if self._alarm_handle is not None:
            self._alarm_handle.cancel()
            self._alarm_handle = None

    def execute_action(self):
        pass

    def on_execute_action(self, *_, **__):
        self.execute_action()

    def get_score(self):
        resolver = SingleSimResolver(self._sim_info)
        return self.score.get_multiplier(resolver)

    def get_duration(self):
        if self._alarm_handle is not None:
            return self._alarm_handle.get_remaining_time()
        return self._duration

    def set_duration(self):
        duration_timespan = create_time_span(minutes=self.duration.random_int())
        self._duration = duration_timespan

    def set_alarm_handle(self, alarm_handle):
        self._alarm_handle = alarm_handle

    def update_demographics(self, demographics):
        pass
