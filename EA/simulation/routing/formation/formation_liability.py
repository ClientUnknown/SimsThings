from interactions.liability import ReplaceableLiability
class RoutingFormationLiability(ReplaceableLiability):
    LIABILITY_TOKEN = 'RoutingFormationLiability'

    def __init__(self, routing_formation_data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._routing_formation_data = routing_formation_data

    def release(self):
        self._routing_formation_data.release_formation_data()
