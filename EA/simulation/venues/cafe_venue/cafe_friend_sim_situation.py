from sims4.tuning.instances import lock_instance_tunablesfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import CommonSituationState, SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleStatefrom situations.situation_types import SituationCreationUIOptionfrom venues.cafe_venue.cafe_situations_common import _OrderCoffeeState, _PreOrderCoffeeState
class _FriendBehaviorState(CommonSituationState):
    pass

class CafeFriendSimSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'pre_order_coffee_state': _PreOrderCoffeeState.TunableFactory(description='\n            The situation state used for when a Sim is arriving as a Cafe\n            Friend Sim.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_pre_order_coffee_situation_state'), 'order_coffee_state': _OrderCoffeeState.TunableFactory(description='\n            The situation state used for when a Sim is ordering coffee as a Cafe\n            Friend Sim.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_order_coffee_situation_state'), 'friend_behavior_state': _FriendBehaviorState.TunableFactory(description='\n            The main state of the situation. This is where Sims will do \n            behavior after ordering coffee\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='03_friend_behavior_state'), 'cafe_friend_job': TunableSituationJobAndRoleState(description="\n            The default job for a Sim in this situation. This shouldn't\n            actually matter because the Situation will put the Sim in the Order\n            Coffee State when they are added.\n            ")}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self._friend_sim = None

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _PreOrderCoffeeState, factory=cls.pre_order_coffee_state), SituationStateData(2, _OrderCoffeeState, factory=cls.order_coffee_state), SituationStateData(3, _FriendBehaviorState, factory=cls.friend_behavior_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.cafe_friend_job.job, cls.cafe_friend_job.role_state)]

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._friend_sim = sim

    def get_order_coffee_state(self):
        return self.order_coffee_state()

    def get_post_coffee_state(self):
        return self.friend_behavior_state()

    @classmethod
    def default_job(cls):
        return cls.cafe_friend_job.job

    def start_situation(self):
        super().start_situation()
        self._change_state(self.pre_order_coffee_state())

    def sim_of_interest(self, sim_info):
        if self._friend_sim is not None and self._friend_sim.sim_info is sim_info:
            return True
        return False
lock_instance_tunables(CafeFriendSimSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)