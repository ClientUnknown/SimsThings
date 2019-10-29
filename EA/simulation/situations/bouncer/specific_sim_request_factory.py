from situations.bouncer.bouncer_request import BouncerRequestFactory
class SpecificSimRequestFactory(BouncerRequestFactory):

    def __init__(self, situation, callback_data, job_type, request_priority, exclusivity, sim_id):
        super().__init__(situation, callback_data=callback_data, job_type=job_type, request_priority=request_priority, user_facing=False, exclusivity=exclusivity)
        self._sim_id = sim_id

    def _can_assign_sim_to_request(self, sim):
        return sim.sim_id == self._sim_id
