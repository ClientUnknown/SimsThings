from event_testing.test_events import TestEventfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import OptionalTunable, TunableSimMinutefrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import CommonSituationState, SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleState, TunableInteractionOfInterest, CommonInteractionCompletedSituationStatefrom situations.situation_types import SituationCreationUIOptionfrom venues.cafe_venue.cafe_situations_common import _OrderCoffeeState, _PreOrderCoffeeState, ORDER_COFFEE_TIMEOUT
class _OrderAndWaitForCoffeeState(CommonSituationState):
    FACTORY_TUNABLES = {'interaction_of_interest': TunableInteractionOfInterest(description='\n             The interaction that needs to run to \n             '), 'order_coffee_timeout': OptionalTunable(description="\n            Optional tunable for how long to wait before progressing to the\n            next state. This is basically here if you don't care if they order\n            coffee all of the time.\n            ", tunable=TunableSimMinute(description='\n                The length of time before moving onto the next state.\n                ', default=60))}

    def __init__(self, interaction_of_interest, order_coffee_timeout, **kwargs):
        super().__init__(**kwargs)
        self._interaction_of_interest = interaction_of_interest
        self._order_coffee_timeout = order_coffee_timeout

    def on_activate(self, reader=None):
        super().on_activate(reader)
        for custom_key in self._interaction_of_interest.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionStart, custom_key)
        if self._order_coffee_timeout is not None:
            self._create_or_load_alarm(ORDER_COFFEE_TIMEOUT, self._order_coffee_timeout, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def handle_event(self, sim_info, event, resolver):
        if event != TestEvent.InteractionStart:
            return
        if not resolver(self._interaction_of_interest):
            return
        if not self.owner.sim_of_interest(sim_info):
            return
        self.owner._change_state(self.owner.get_post_coffee_state())

    def timer_expired(self):
        self.owner._change_state(self.owner.get_post_coffee_state())
LEAVE_TIMEOUT = 'leave_timeout'
class _LeaveCafeState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'timeout': TunableSimMinute(description='\n            The length of time before ending the situation.\n            ', default=60)}

    def __init__(self, timeout, **kwargs):
        super().__init__(**kwargs)
        self._timeout = timeout

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if self._timeout is not None:
            self._create_or_load_alarm(LEAVE_TIMEOUT, self._timeout, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()

    def _additional_tests(self, sim_info, event, resolver):
        if not self.owner.sim_of_interest(sim_info):
            return False
        elif not resolver.interaction.is_finishing:
            return False
        return True

    def timer_expired(self):
        self.owner._self_destruct()

class CafeToGoCustomerSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'pre_order_coffee_state': _PreOrderCoffeeState.TunableFactory(description='\n            The situation state used for when a Sim is arriving as a Cafe\n            To Go Customer.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_pre_order_coffee_situation_state'), 'order_coffee_state': _OrderAndWaitForCoffeeState.TunableFactory(description='\n            The situation state used for when a Sim is arriving as a ToGo\n            Customer.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_order_coffee_situation_state'), 'leave_cafe_state': _LeaveCafeState.TunableFactory(description="\n            The state after Sims get coffee. Likely we will want this state to\n            immediately exit, but it's also possible we want the Sim to route\n            to the arrival spawn point with their coffee.\n            ", tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='03_leave_cafe_state'), 'to_go_customer_job': TunableSituationJobAndRoleState(description="\n            The default job for a Sim in this situation. This shouldn't\n            actually matter because the Situation will put the Sim in the Order\n            Coffee State when they are added.\n            ")}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self._to_go_sim = None

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _PreOrderCoffeeState, factory=cls.pre_order_coffee_state), SituationStateData(2, _OrderAndWaitForCoffeeState, factory=cls.order_coffee_state), SituationStateData(3, _LeaveCafeState, factory=cls.leave_cafe_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.to_go_customer_job.job, cls.to_go_customer_job.role_state)]

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._to_go_sim = sim

    def get_order_coffee_state(self):
        return self.order_coffee_state()

    def get_post_coffee_state(self):
        return self.leave_cafe_state()

    @classmethod
    def default_job(cls):
        return cls.to_go_customer_job

    def start_situation(self):
        super().start_situation()
        self._change_state(self.pre_order_coffee_state())

    def sim_of_interest(self, sim_info):
        if self._to_go_sim is not None and self._to_go_sim.sim_info is sim_info:
            return True
        return False
lock_instance_tunables(CafeToGoCustomerSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)