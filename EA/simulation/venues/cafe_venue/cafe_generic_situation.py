from sims4.tuning.instances import lock_instance_tunablesfrom situations.base_situation import _RequestUserDatafrom situations.bouncer.bouncer_request import BouncerRequestFactoryfrom situations.bouncer.bouncer_types import BouncerExclusivityCategory, BouncerRequestPriority, RequestSpawningOptionfrom situations.situation import Situationfrom situations.situation_complex import CommonSituationState, SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleState, SituationStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfo, SituationInvitationPurposefrom situations.situation_types import SituationCreationUIOptionfrom venues.cafe_venue.cafe_situations_common import _OrderCoffeeState, _PreOrderCoffeeStateimport services
class _CafeGenericBehaviorState(CommonSituationState):
    pass

class CafeGenericCustomerSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'pre_order_coffee_state': _PreOrderCoffeeState.TunableFactory(description='\n            The situation state used for when a Sim is arriving as a Cafe\n            Generic Sim.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_pre_order_coffee_situation_state'), 'order_coffee_state': _OrderCoffeeState.TunableFactory(description='\n            The situation state used for when a Sim is ordering coffee as a Cafe\n            Generic Sim.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_order_coffee_situation_state'), 'cafe_generic_state': _CafeGenericBehaviorState.TunableFactory(description='\n            The main state of the situation. This is where Sims will do \n            behavior after ordering coffee\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='03_generic_behavior_state'), 'cafe_generic_job': TunableSituationJobAndRoleState(description="\n            The default job and role state for a Sim in this situation. This\n            shouldn't actually matter because the Situation will put the Sim in\n            the Order Coffee State when they are added.\n            ")}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cafe_sim = None

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _PreOrderCoffeeState, factory=cls.pre_order_coffee_state), SituationStateData(2, _OrderCoffeeState, factory=cls.order_coffee_state), SituationStateData(3, _CafeGenericBehaviorState, factory=cls.cafe_generic_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.cafe_generic_job.job, cls.cafe_generic_job.role_state)]

    def get_order_coffee_state(self):
        return self.order_coffee_state()

    def get_post_coffee_state(self):
        return self.cafe_generic_state()

    @classmethod
    def default_job(cls):
        return cls.cafe_generic_job.job

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._cafe_sim = sim

    def start_situation(self):
        super().start_situation()
        self._change_state(self.pre_order_coffee_state())

    def sim_of_interest(self, sim_info):
        if self._cafe_sim is not None and self._cafe_sim.sim_info is sim_info:
            return True
        return False
lock_instance_tunables(CafeGenericCustomerSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0, _implies_greeted_status=False)
class _CafeGenericState(SituationState):
    pass

class CafeGenericBackgroundSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'generic_sim_job': TunableSituationJobAndRoleState(description="\n            A job and role state that essentially does nothing but filter out\n            Sims that shouldn't be placed in the generic cafe sim situation.\n            "), 'cafe_generic_customer_situation': Situation.TunableReference(description='\n            The individual, generic cafe customer situation we want to use for\n            Sims that show up at the Cafe so they can go get coffee.\n            ', class_restrictions=('CafeGenericCustomerSituation',))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _CafeGenericState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.generic_sim_job.job, cls.generic_sim_job.role_state)]

    @classmethod
    def default_job(cls):
        return cls.generic_sim_job.job

    def start_situation(self):
        super().start_situation()
        self._change_state(_CafeGenericState())

    def _issue_requests(self):
        request = BouncerRequestFactory(self, callback_data=_RequestUserData(role_state_type=self.generic_sim_job.role_state), job_type=self.generic_sim_job.job, request_priority=BouncerRequestPriority.BACKGROUND_MEDIUM, user_facing=False, exclusivity=self.exclusivity)
        self.manager.bouncer.submit_request(request)

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        situation_manager = services.get_zone_situation_manager()
        guest_list = SituationGuestList(invite_only=True)
        guest_info = SituationGuestInfo(sim.sim_info.id, self.cafe_generic_customer_situation.default_job(), RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_MEDIUM)
        guest_list.add_guest_info(guest_info)
        situation_manager.create_situation(self.cafe_generic_customer_situation, guest_list=guest_list, user_facing=False)
lock_instance_tunables(CafeGenericBackgroundSituation, exclusivity=BouncerExclusivityCategory.PRE_VISIT, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0, _implies_greeted_status=False)