from role.role_state import RoleStatefrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableTuple, TunableEnumEntryfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationState, SituationComplexCommon, SituationStateDatafrom situations.situation_job import SituationJobfrom situations.situation_types import SituationCreationUIOptionfrom tag import Tagimport services
class _DJSituationState(SituationState):
    pass

class DJSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'job': TunableTuple(description='\n            The job and role which the career Sim is placed into.\n            ', situation_job=SituationJob.TunableReference(description='\n                A reference to a SituationJob that can be performed at this Situation.\n                '), role_state=RoleState.TunableReference(description='\n                A role state the Sim assigned to the job will perform.\n                ')), 'can_start_tag': TunableEnumEntry(description='\n            A specific tag that an object on this lot must have for this\n            situation to be allowed to start.\n            ', tunable_type=Tag, default=Tag.INVALID, invalid_enums=(Tag.INVALID,))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _DJSituationState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.job.situation_job, cls.job.role_state)]

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def situation_meets_starting_requirements(cls, **kwargs):
        object_manager = services.object_manager()
        for _ in object_manager.get_objects_with_tag_gen(cls.can_start_tag):
            return True
        return False

    def start_situation(self):
        super().start_situation()
        self._change_state(_DJSituationState())
lock_instance_tunables(DJSituation, exclusivity=BouncerExclusivityCategory.VENUE_EMPLOYEE, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)