from event_testing.resolver import SingleSimResolverfrom role.role_state import RoleStatefrom sims4.tuning.tunable import TunableTuplefrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.situation_complex import CommonSituationState, SituationComplexCommon, SituationStateDatafrom situations.situation_guest_list import SituationGuestInfofrom situations.situation_job import SituationJobimport event_testingimport servicesimport sims4logger = sims4.log.Logger('IslandSpiritsVisitSituation', default_owner='bnguyen')
class VisitState(CommonSituationState):
    pass

class IslandSpiritsVisitSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'visit_state': VisitState.TunableFactory(description='\n            The state in which spirits will perform a set tuned of interactions.\n            ', display_name='01_visit_state', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'island_spirit': TunableTuple(situation_job=SituationJob.TunableReference(description="\n                Island spirit's job during the visit.\n                "), situation_role_state=RoleState.TunableReference(description="\n                Island spirit's role state during the visit.\n                "), tuning_group=GroupNames.ROLES), 'island_elemental': TunableTuple(situation_job=SituationJob.TunableReference(description="\n                Island elemental's job during the visit.\n                "), situation_role_state=RoleState.TunableReference(description="\n                Island elemental's role state during the visit.\n                "), spawn_tests=event_testing.tests.TunableTestSet(description='\n                Tests that must be passed for the island elemental to be spawned.\n                '), tuning_group=GroupNames.ROLES)}

    def start_situation(self):
        super().start_situation()
        self._change_state(self.visit_state())

    @classmethod
    def _states(cls):
        return (SituationStateData.from_auto_factory(1, cls.visit_state),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.island_elemental.situation_job, cls.island_elemental.situation_role_state), (cls.island_spirit.situation_job, cls.island_spirit.situation_role_state)]

    @classmethod
    def default_job(cls):
        pass

    def _expand_guest_list_based_on_tuning(self):
        super()._expand_guest_list_based_on_tuning()
        sim_info_manager = services.sim_info_manager()
        sim_info = sim_info_manager.get(self._guest_list.host_sim_id)
        if sim_info == None:
            logger.error('Host sim id {} is invalid while creating the island spirit visit situation', self._guest_list.host_sim_id)
        resolver = SingleSimResolver(sim_info)
        if not self.island_elemental.spawn_tests.run_tests(resolver):
            return
        guest_info = SituationGuestInfo(0, self.island_elemental.situation_job, spawning_option=RequestSpawningOption.DONT_CARE, request_priority=BouncerRequestPriority.EVENT_VIP, expectation_preference=True, accept_alternate_sim=True)
        self._guest_list.add_guest_info(guest_info)
