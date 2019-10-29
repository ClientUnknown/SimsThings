from role.role_state import RoleStatefrom situations.situation import Situationfrom situations.situation_complex import SituationState, SituationStateDatafrom situations.situation_job import SituationJobfrom situations.situation_types import GreetedStatusimport servicesimport sims4.tuning.instancesimport sims4.tuning.tunableimport situations.bouncerimport situations.situation_typesimport venues
class InviteToSituation(situations.situation_complex.SituationComplexCommon):
    INSTANCE_TUNABLES = {'invited_job': sims4.tuning.tunable.TunableTuple(situation_job=SituationJob.TunableReference(description='\n                          A reference to the SituationJob used for the Sims invited to.\n                          '), invited_to_state=RoleState.TunableReference(description='\n                          The state for telling a sim to wait. They will momentarily be\n                          pulled from this situation by a visit or venue situation.\n                          ')), 'purpose': sims4.tuning.tunable.TunableEnumEntry(description='\n                The purpose/reason used to perform the venue specific operation\n                to get this sim in the appropriate situation.\n                This should be tuned to Invite In, but since that is a dynamic enum\n                you must do it yourself.\n                ', tunable_type=venues.venue_constants.NPCSummoningPurpose, default=venues.venue_constants.NPCSummoningPurpose.DEFAULT)}
    REMOVE_INSTANCE_TUNABLES = Situation.SITUATION_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _WaitState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.invited_job.situation_job, cls.invited_job.invited_to_state)]

    @classmethod
    def default_job(cls):
        return cls.invited_job.situation_job

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tick_alarm_handle = None

    def start_situation(self):
        super().start_situation()
        self._change_state(_WaitState())

    def _issue_requests(self):
        pass

    def on_arrived(self):
        zone = services.current_zone()
        venue = zone.venue_service.venue
        for sim_info in self._seed.invited_sim_infos_gen():
            if sim_info.is_npc:
                venue.summon_npcs((sim_info,), self.purpose)

    @classmethod
    def get_player_greeted_status_from_seed(cls, situation_seed):
        for sim_info in situation_seed.invited_sim_infos_gen():
            if sim_info.is_npc and sim_info.lives_here:
                return GreetedStatus.GREETED
        return GreetedStatus.NOT_APPLICABLE
sims4.tuning.instances.lock_instance_tunables(InviteToSituation, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.PRE_VISIT, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE, duration=1, _implies_greeted_status=False)
class _WaitState(SituationState):
    pass
