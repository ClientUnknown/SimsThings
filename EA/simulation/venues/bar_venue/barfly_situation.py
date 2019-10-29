import randomfrom sims4.common import Pack, is_available_packfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import OptionalTunable, TunableSimMinute, TunableEnumEntryfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationState, SituationComplexCommon, TunableSituationJobAndRoleState, SituationStateDatafrom situations.situation_types import SituationCreationUIOptionimport mtx
class _BarflySituationState(SituationState):
    pass

class BarflySituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'barfly_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role of the barfly.\n            '), 'starting_entitlement': OptionalTunable(description='\n            If enabled, this situation is locked by an entitlement. Otherwise,\n            this situation is available to all players.\n            ', tunable=TunableEnumEntry(description='\n                Pack required for this event to start.\n                ', tunable_type=Pack, default=Pack.BASE_GAME)), 'duration_randomizer': TunableSimMinute(description="\n            A random time between 0 and this tuned time will be added to the\n            situation's duration.\n            ", default=10, minimum=1)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _BarflySituationState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.barfly_job_and_role.job, cls.barfly_job_and_role.role_state)]

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def situation_meets_starting_requirements(cls, **kwargs):
        if cls.starting_entitlement is None:
            return True
        return is_available_pack(cls.starting_entitlement)

    def start_situation(self):
        super().start_situation()
        self._change_state(_BarflySituationState())

    def _get_duration(self):
        if self._seed.duration_override is not None:
            return self._seed.duration_override
        return self.duration + random.randint(0, self.duration_randomizer)
lock_instance_tunables(BarflySituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, _implies_greeted_status=False)