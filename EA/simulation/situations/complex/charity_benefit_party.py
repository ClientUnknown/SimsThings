from role.role_state import RoleStatefrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_complex import SituationComplexCommon, SituationState, SituationStateDatafrom situations.situation_job import SituationJobimport sims4.tuning.tunable
class CharityBenefitPartySituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'host': sims4.tuning.tunable.TunableTuple(situation_job=SituationJob.TunableReference(description='\n                        The SituationJob for the host.\n                        '), host_benefit_role_state=RoleState.TunableReference(description="\n                        The host's role state during the benefit.\n                        "), tuning_group=GroupNames.ROLES), 'bartender': sims4.tuning.tunable.TunableTuple(situation_job=SituationJob.TunableReference(description='\n                        The SituationJob for the Bartender.\n                        '), bartender_benefit_role_state=RoleState.TunableReference(description="\n                        Bartender's role state to prepare drinks, socialize, etc. during the benefit.\n                        "), tuning_group=GroupNames.ROLES), 'caterer': sims4.tuning.tunable.TunableTuple(situation_job=SituationJob.TunableReference(description='\n                        The SituationJob for the caterer.\n                        '), caterer_benefit_role_state=RoleState.TunableReference(description="\n                        Caterer's role state for serving the guests.\n                        "), tuning_group=GroupNames.ROLES), 'entertainer': sims4.tuning.tunable.TunableTuple(situation_job=SituationJob.TunableReference(description='\n                        The SituationJob for the entertainer.\n                        '), entertainer_benefit_role_state=RoleState.TunableReference(description="\n                        Entertainer's role state during the benefit.\n                        "), tuning_group=GroupNames.ROLES), 'guest': sims4.tuning.tunable.TunableTuple(situation_job=SituationJob.TunableReference(description='\n                        The SituationJob for the Guests.\n                        '), guest_benefit_role_state=RoleState.TunableReference(description="\n                        Guest's role state during the benefit.\n                        "), tuning_group=GroupNames.ROLES)}
    REMOVE_INSTANCE_TUNABLES = ('venue_invitation_message', 'venue_situation_player_job')

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _BenefitState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.host.situation_job, cls.host.host_benefit_role_state), (cls.bartender.situation_job, cls.bartender.bartender_benefit_role_state), (cls.caterer.situation_job, cls.caterer.caterer_benefit_role_state), (cls.entertainer.situation_job, cls.entertainer.entertainer_benefit_role_state), (cls.guest.situation_job, cls.guest.guest_benefit_role_state)]

    @classmethod
    def default_job(cls):
        return cls.guest.situation_job

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def start_situation(self):
        super().start_situation()
        self._change_state(_BenefitState())

class _BenefitState(SituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.host.situation_job, self.owner.host.host_benefit_role_state)
        self.owner._set_job_role_state(self.owner.bartender.situation_job, self.owner.bartender.bartender_benefit_role_state)
        self.owner._set_job_role_state(self.owner.caterer.situation_job, self.owner.caterer.caterer_benefit_role_state)
        self.owner._set_job_role_state(self.owner.entertainer.situation_job, self.owner.entertainer.entertainer_benefit_role_state)
        self.owner._set_job_role_state(self.owner.guest.situation_job, self.owner.guest.guest_benefit_role_state)
