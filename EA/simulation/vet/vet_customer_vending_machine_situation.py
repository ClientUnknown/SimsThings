from business.business_situation_mixin import BusinessSituationMixinfrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateData, CommonInteractionCompletedSituationStateimport sims4.tuning.instancesimport situations.bouncer
class VetCustomerState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()

    def _additional_tests(self, sim_info, event, resolver):
        return self.owner.is_sim_info_in_situation(sim_info)

class VetCustomerVendingMachineSituation(BusinessSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'customer_job_and_role_states': TunableSituationJobAndRoleState(description='\n            The job assigned to pet owners and the initial role when the situation starts.\n            ', tuning_group=GroupNames.ROLES), 'situation_state': VetCustomerState.TunableFactory(description='\n            A situation state that looks for them to run an interaction to\n            purchase an item from the vending machine so that the situation\n            can end.\n            ', locked_args={'time_out': None, 'allow_join_situation': True})}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, VetCustomerState, factory=cls.situation_state),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.customer_job_and_role_states.job, cls.customer_job_and_role_states.role_state)]

    @classmethod
    def default_job(cls):
        pass

    @property
    def customer_has_been_seen(self):
        return True

    def start_situation(self):
        super().start_situation()
        self._change_state(self.situation_state())
sims4.tuning.instances.lock_instance_tunables(VetCustomerVendingMachineSituation, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.NORMAL)