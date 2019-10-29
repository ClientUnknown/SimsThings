from event_testing.results import TestResultfrom sims.sim_info_interactions import SimInfoInteractionimport services
class RabbitHoleLeaveEarlyInteraction(SimInfoInteraction):

    @classmethod
    def _test(cls, *args, sim_info=None, **kwargs):
        if sim_info is None:
            return TestResult(False, 'No sim info')
        sim_id = sim_info.id
        rabbit_hole_service = services.get_rabbit_hole_service()
        if not rabbit_hole_service.is_in_rabbit_hole(sim_id):
            return TestResult(False, 'Not currently in a rabbit hole')
        if not rabbit_hole_service.is_rabbit_hole_user_cancelable(sim_id):
            return TestResult(False, 'Rabbit hole interaction is not user cancelable')
        return super()._test(*args, **kwargs)

    def _run_interaction_gen(self, timeline):
        sim_id = self._sim_info.id
        rabbit_hole_service = services.get_rabbit_hole_service()
        if rabbit_hole_service.is_in_rabbit_hole(sim_id):
            rabbit_hole_service.remove_sim_from_rabbit_hole(sim_id, canceled=True)
        return True
