from sims4.tuning.instances import lock_instance_tunablesfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationStateData, CommonInteractionCompletedSituationState, TunableSituationJobAndRoleStatefrom situations.situation_types import SituationCreationUIOptionCUSTOMER_TOKEN = 'customer_id'
class BrowseItemsState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()

class YardSaleCustomerSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'browse_items_state': BrowseItemsState.TunableFactory(tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_browse_items_state'), 'customer_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state for the customer who wants to check out the\n            craft sales table.\n            ')}

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self.customer = None

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.customer_job_and_role_state.job, cls.customer_job_and_role_state.role_state)]

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self.customer = sim

    @classmethod
    def _states(cls):
        return (SituationStateData(1, BrowseItemsState, factory=cls.browse_items_state),)

    def start_situation(self):
        super().start_situation()
        self._change_state(self.browse_items_state())

    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES
lock_instance_tunables(YardSaleCustomerSituation, exclusivity=BouncerExclusivityCategory.WALKBY_SNATCHER, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)