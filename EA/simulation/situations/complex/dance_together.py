from interactions.aop import AffordanceObjectPairfrom interactions.context import InteractionContext, InteractionSourcefrom interactions.interaction_finisher import FinishingTypefrom interactions.jig_part_constraint_interaction import JigPartConstraintInteractionfrom interactions.priority import Priorityfrom sims4.tuning.tunable import TunableMapping, Tunable, TunableReferencefrom situations.complex.group_dance.group_dance_situation import GroupDanceSituationfrom situations.situation_complex import CommonInteractionCompletedSituationState, SituationStateDatafrom situations.situation_job import SituationJobimport servicesimport sims4logger = sims4.log.Logger('Dance Together', default_owner='cjiang')
class _DanceState(CommonInteractionCompletedSituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        dancers = list(self.owner.all_sims_in_situation_gen())
        constraint_affordance = self.owner.constraint_affordance
        for sim in dancers:
            if not sim.si_state.is_running_affordance(constraint_affordance):
                self.owner.remove_sim_from_situation(sim)
        leader_sim = self.owner.initiating_sim_info.get_sim_instance()
        interaction_context = InteractionContext(leader_sim, InteractionSource.SCRIPT_WITH_USER_INTENT, Priority.High)
        aop = AffordanceObjectPair(self.owner.dance_affordance, None, self.owner.dance_affordance, None, jig_object=self.owner._jig_object, jig_part_index=0)
        aop.test_and_execute(interaction_context)

    def _on_interaction_of_interest_complete(self, **kwargs):
        self.owner._self_destruct()
DANCE_GROUP = 'Dance'
class DanceTogetherSituation(GroupDanceSituation):
    INSTANCE_TUNABLES = {'dance_leader_job': SituationJob.TunableReference(description='\n            The situation job for dance leader.\n            ', tuning_group=DANCE_GROUP, allow_none=True), 'dance_member_job': SituationJob.TunableReference(description='\n            The situation job for dance member.\n            ', tuning_group=DANCE_GROUP, allow_none=True), 'dance_state': _DanceState.TunableFactory(description='\n            The state that sim is doing dance movements.\n            ', tuning_group=DANCE_GROUP), 'dance_affordance': JigPartConstraintInteraction.TunableReference(description='\n            The affordance for leader sim to run with dance movement mixers tuned in.\n            ', tuning_group=DANCE_GROUP), 'jig_map': TunableMapping(description='\n            The static map to mapping dancing jig with number of sims in the dance group\n            Put it here instead of in the module tuning is for pack safe reason.\n            This should only be tuned on prototype, and not suggesting to change/override\n            in tuning instance unless you have very strong reason.\n            ', key_type=Tunable(tunable_type=int, default=2), key_name='number_of_sim', value_type=TunableReference(manager=services.definition_manager()), value_name='jig_to_use', tuning_group=DANCE_GROUP)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dance_pose_index = 0

    def start_situation(self):
        super().start_situation()
        self._create_situation_geometry()
        self._change_state(self.pre_situation_state.situation_state())

    @classmethod
    def _states(cls):
        base_states = super()._states()
        situation_states = [SituationStateData(2, _DanceState, factory=cls.dance_state)]
        return base_states + tuple(situation_states)

    def get_jig_definition(self):
        owner_sim = self.initiating_sim_info.get_sim_instance()
        ensemble_sims = services.ensemble_service().get_ensemble_sims_for_rally(owner_sim)
        sim_filter_service = services.sim_filter_service()
        filter_result_list = sim_filter_service.submit_filter(self.dance_member_job.filter, None, allow_yielding=False, sim_constraints=[sim.id for sim in ensemble_sims], requesting_sim_info=self.initiating_sim_info, gsi_source_fn=self.get_sim_filter_gsi_name)
        num_of_sims = len(filter_result_list)
        if num_of_sims not in self.jig_map:
            logger.error('Try to get jig for {} sims, which is not supported', num_of_sims)
        return self.jig_map.get(num_of_sims, None)

    def _check_route_sim(self, sim):
        self._route_sim(sim, self.get_and_increment_sim_jig_index(sim))

    def get_next_dance_state(self):
        return self.dance_state

    def get_and_increment_sim_jig_index(self, sim):
        leader_sim = self.initiating_sim_info.get_sim_instance()
        if sim.id == leader_sim.id:
            index = 0
        else:
            index = self._jig_index + 1
            self._jig_index += 1
        return index

    def _cancel_constraint_affordance_for_sim(self, sim):
        for si in sim.get_all_running_and_queued_interactions():
            if si.affordance is self.constraint_affordance:
                si.cancel(FinishingType.SITUATIONS, cancel_reason_msg='GroupDance Situation done.')

    def _on_remove_sim_from_situation(self, sim):
        self._cancel_constraint_affordance_for_sim(sim)
        super()._on_remove_sim_from_situation(sim)

    def _destroy(self):
        for sim in self.all_sims_in_situation_gen():
            self._cancel_constraint_affordance_for_sim(sim)
        super()._destroy()
