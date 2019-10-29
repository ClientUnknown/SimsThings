from sims4.tuning.tunable import TunableSimMinute, OptionalTunable, TunableIntervalfrom situations.situation_complex import CommonInteractionCompletedSituationState, CommonSituationStateORDER_COFFEE_TIMEOUT = 'order_coffee_timeout'
class _PreOrderCoffeeState(CommonSituationState):
    FACTORY_TUNABLES = {'wait_to_order_duration': TunableInterval(description='\n            The duration in Sim minutes for the Sim to wait before ordering coffee when\n            they spawn at the Cafe. Any behavior can be tuned for ths Sim to\n            perform before ordering coffee.\n            ', tunable_type=TunableSimMinute, default_lower=10, default_upper=100, minimum=0)}

    def __init__(self, wait_to_order_duration, **kwargs):
        super().__init__(**kwargs)
        self._wait_to_order_duration = wait_to_order_duration

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._create_or_load_alarm(ORDER_COFFEE_TIMEOUT, self._wait_to_order_duration.random_float(), lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def timer_expired(self):
        self.owner._change_state(self.owner.get_order_coffee_state())

class _OrderCoffeeState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'order_coffee_timeout': OptionalTunable(description="\n            Optional tunable for how long to wait before progressing to the\n            next state. This is basically here if you don't care if they order\n            coffee all of the time.\n            ", tunable=TunableSimMinute(description='\n                The length of time before moving onto the next state.\n                ', default=60))}

    def __init__(self, order_coffee_timeout, **kwargs):
        super().__init__(**kwargs)
        self._order_coffee_timeout = order_coffee_timeout

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if self._order_coffee_timeout is not None:
            self._create_or_load_alarm(ORDER_COFFEE_TIMEOUT, self._order_coffee_timeout, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._change_state(self.owner.get_post_coffee_state())

    def _additional_tests(self, sim_info, event, resolver):
        if not self.owner.sim_of_interest(sim_info):
            return False
        elif not resolver.interaction.is_finishing:
            return False
        return True

    def timer_expired(self):
        self.owner._change_state(self.owner.get_post_coffee_state())
