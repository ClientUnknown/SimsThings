from event_testing.test_events import TestEventfrom situations.complex.service_npc_situation import ServiceNpcSituationimport services
class ServiceNpcNannySituation(ServiceNpcSituation):

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        services.get_event_manager().process_event(TestEvent.AvailableDaycareSimsChanged, sim_info=self.service_sim().sim_info)
