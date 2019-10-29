from situations.situation import Situationfrom venues.scheduling_zone_director import SchedulingZoneDirectorimport services
class CafeZoneDirector(SchedulingZoneDirector):
    INSTANCE_TUNABLES = {'cafe_generic_arrival_situation': Situation.TunableReference(description='\n            The situation that is always runnning at the Cafe to make sure any\n            Sims that show up beyond the schedule tuning will get coffee. These\n            could be Sims the player invites, the player themselves, and clique\n            Sims. \n            \n            Note, the situation that this points to will be a very\n            generic situation that spins up a CafeGenericSimSituation for that\n            individual Sim. This is so that Sims can get coffee on their own\n            autonomy and be independent of one another.\n            ', class_restrictions=('CafeGenericBackgroundSituation',))}

    def add_sim_info_into_arrival_situation(self, sim_info, during_spin_up=False):
        situation_manager = services.get_zone_situation_manager()
        situation = situation_manager.get_situation_by_type(self.cafe_generic_arrival_situation)
        if situation is None:
            situation_manager.create_situation(self.cafe_generic_arrival_situation, guest_list=None, user_facing=False, creation_source=self.instance_name)

    def create_situations_during_zone_spin_up(self):
        super().create_situations_during_zone_spin_up()
        situation_manager = services.get_zone_situation_manager()
        situation_manager.create_situation(self.cafe_generic_arrival_situation, guest_list=None, user_facing=False, creation_source=self.instance_name)

    def handle_sim_summon_request(self, sim_info, purpose):
        self.add_sim_info_into_arrival_situation(sim_info)
