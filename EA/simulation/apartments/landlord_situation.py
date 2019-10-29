from sims4.tuning.instances import lock_instance_tunablesfrom situations.ambient.walkby_ring_doorbell_situation import WalkbyRingDoorBellSituationfrom situations.bouncer.bouncer_types import BouncerExclusivityCategory, RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import CommonSituationState, SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_types import SituationCreationUIOptionimport services
class _FixProblemsState(CommonSituationState):
    pass

class LandlordSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'fix_problems_state': _FixProblemsState.TunableFactory(description='\n            Situation State for the Landlord to fix Apartment Problems.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_fix_problems_situation_state'), 'landlord_situation_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The Situation Job and Role State for the Landlord.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _FixProblemsState, factory=cls.fix_problems_state),)

    @classmethod
    def default_job(cls):
        return cls.landlord_situation_job_and_role_state.job

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.landlord_situation_job_and_role_state.job, cls.landlord_situation_job_and_role_state.role_state)]

    @classmethod
    def get_predefined_guest_list(cls):
        guest_list = SituationGuestList(invite_only=True)
        landlord_sim_info = services.get_landlord_service().get_landlord_sim_info()
        guest_list.add_guest_info(SituationGuestInfo(landlord_sim_info.sim_id, cls.landlord_situation_job_and_role_state.job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP, expectation_preference=True))
        return guest_list

    def start_situation(self):
        super().start_situation()
        self._change_state(self.fix_problems_state())
lock_instance_tunables(LandlordSituation, exclusivity=BouncerExclusivityCategory.VISIT, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)
class LandlordWalkbyRingDoorBellSituation(WalkbyRingDoorBellSituation):

    @classmethod
    def get_predefined_guest_list(cls):
        guest_list = SituationGuestList(invite_only=True)
        landlord_sim_info = services.get_landlord_service().get_landlord_sim_info()
        guest_list.add_guest_info(SituationGuestInfo(landlord_sim_info.sim_id, cls.walker_job.situation_job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP, expectation_preference=True))
        return guest_list
