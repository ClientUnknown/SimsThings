from sims4.tuning.instances import lock_instance_tunablesfrom sims4.utils import classpropertyfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation_complex import SituationComplexCommon, SituationState, TunableSituationJobAndRoleState, SituationStateDatafrom situations.situation_zone_director_mixin import SituationZoneDirectorMixinfrom venues.venue_constants import ZoneDirectorRequestTypeimport services
class _GoDancingSituationState(SituationState):
    pass

class GoDancingSituation(SituationZoneDirectorMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'party_goer': TunableSituationJobAndRoleState(description='\n            The job and role of Party Goers.\n            '), 'host_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state of the Sim who planned the Go Dancing\n            Situation.\n            ')}
    REMOVE_INSTANCE_TUNABLES = ('_resident_job',)

    @classproperty
    def allow_user_facing_goals(cls):
        return False

    @classmethod
    def get_possible_zone_ids_for_situation(cls, host_sim_info=None, guest_ids=None):
        possible_zones = super().get_possible_zone_ids_for_situation(host_sim_info=host_sim_info, guest_ids=guest_ids)
        current_zone_id = services.current_zone_id()
        if current_zone_id in possible_zones:
            possible_zones.remove(current_zone_id)
        return possible_zones

    @classmethod
    def _get_zone_director_request_type(cls):
        return ZoneDirectorRequestType.GO_DANCING

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _GoDancingSituationState),)

    @classmethod
    def resident_job(cls):
        return cls.host_job_and_role_state.job

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        party_goer_tuples = [(cls.party_goer.job, cls.party_goer.role_state)]
        host_tuples = [(cls.host_job_and_role_state.job, cls.host_job_and_role_state.role_state)] if cls.resident_job() is not None and cls.host_job_and_role_state.role_state is not None and cls.resident_job() is not cls.party_goer.job else []
        return party_goer_tuples + host_tuples

    @classmethod
    def default_job(cls):
        pass

    def start_situation(self):
        super().start_situation()
        self._change_state(_GoDancingSituationState())
lock_instance_tunables(GoDancingSituation, exclusivity=BouncerExclusivityCategory.NORMAL, _implies_greeted_status=False)