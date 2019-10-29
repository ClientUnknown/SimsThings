from sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import Tunablefrom sims4.utils import classpropertyfrom situations.ambient.walkby_limiting_tags_mixin import WalkbyLimitingTagsMixinfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import CommonInteractionCompletedSituationState, SituationState, SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateData, CommonSituationStatefrom situations.situation_types import SituationCreationUIOptionimport servicesimport situations
class _HasFrontDoorArrivalState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.visit_state())

    def timer_expired(self):
        self._change_state(self.owner.visit_state())

class _HasNoFrontDoorArrivalState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.visit_state())

    def timer_expired(self):
        self._change_state(self.owner.visit_state())

class _VisitState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner.leave_state())

    def timer_expired(self):
        self._change_state(self.owner.leave_state())

class _LeaveState(CommonSituationState):

    def timer_expired(self):
        self.owner._self_destruct()

class SingleSimVisitorSituation(WalkbyLimitingTagsMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'visitor_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role state for the visitor.\n            '), 'has_front_door_arrival_state': _HasFrontDoorArrivalState.TunableFactory(description='\n            The arrival state for the visitor if the lot has a front door.\n            ', display_name='1. Has Front Door Arrival State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'has_no_front_door_arrival_state': _HasNoFrontDoorArrivalState.TunableFactory(description='\n            The arrival state for the visitor if the lot has a front door.\n            ', display_name='1. Has No Front Door Arrival State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'visit_state': _VisitState.TunableFactory(description="\n            The state for the visitor to interact with the lot and it's owner.\n            ", display_name='2. Visit State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'leave_state': _LeaveState.TunableFactory(description='\n            The state for the visitor to leave the lot.\n            ', display_name='3. Leave State', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _HasFrontDoorArrivalState, factory=cls.has_front_door_arrival_state), SituationStateData(2, _HasNoFrontDoorArrivalState, factory=cls.has_no_front_door_arrival_state), SituationStateData(3, _VisitState, factory=cls.visit_state), SituationStateData(4, _LeaveState, factory=cls.leave_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.visitor_job_and_role.job, cls.visitor_job_and_role.role_state)]

    @classmethod
    def default_job(cls):
        pass

    def start_situation(self):
        super().start_situation()
        if services.get_door_service().has_front_door():
            self._change_state(self.has_front_door_arrival_state())
        else:
            self._change_state(self.has_no_front_door_arrival_state())

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return 1

    @property
    def _should_cancel_leave_interaction_on_premature_removal(self):
        return True

    @classproperty
    def situation_serialization_option(cls):
        return situations.situation_types.SituationSerializationOption.OPEN_STREETS
lock_instance_tunables(SingleSimVisitorSituation, exclusivity=BouncerExclusivityCategory.WALKBY, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)