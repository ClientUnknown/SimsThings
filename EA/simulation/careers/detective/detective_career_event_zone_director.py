from buffs.tunable import TunableBuffReferencefrom careers.career_event_zone_director import CareerEventZoneDirectorfrom sims4.tuning.tunable import TunableReferenceimport servicesimport sims4.resources
class DetectiveCareerEventZoneDirector(CareerEventZoneDirector):
    INSTANCE_TUNABLES = {'criminal_trait': TunableReference(description='\n            The trait that signifies that a sim is a criminal at the police station.\n            ', manager=services.get_instance_manager(sims4.resources.Types.TRAIT)), 'in_holding_cell_buff': TunableBuffReference(description='\n            The buff that indicates that this sim is in a holding cell.\n            ')}

    def _did_sim_overstay(self, sim_info):
        if sim_info.has_trait(self.criminal_trait):
            return False
        if sim_info.has_buff(self.in_holding_cell_buff.buff_type):
            return False
        return super()._did_sim_overstay(sim_info)
