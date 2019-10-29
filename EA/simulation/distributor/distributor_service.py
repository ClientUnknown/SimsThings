from sims4.service_manager import Serviceimport distributor.system
class DistributorService(Service):

    def start(self):
        import animation.arb
        animation.arb.set_tag_functions(distributor.system.get_next_tag_id, distributor.system.get_current_tag_set)
        distributor.system._distributor_instance = distributor.system.Distributor()

    def stop(self):
        distributor.system._distributor_instance = None

    def on_tick(self):
        distributor.system._distributor_instance.process()
