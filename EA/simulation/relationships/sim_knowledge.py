from protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom careers.career_unemployment import CareerUnemploymentimport servicesimport sims4logger = sims4.log.Logger('Relationship', default_owner='jjacobson')
class SimKnowledge:
    __slots__ = ('_rel_data', '_known_traits', '_knows_career', '_known_stats')

    def __init__(self, rel_data):
        self._rel_data = rel_data
        self._known_traits = None
        self._knows_career = False
        self._known_stats = None

    def add_known_trait(self, trait, notify_client=True):
        if trait.is_personality_trait:
            if self._known_traits is None:
                self._known_traits = set()
            self._known_traits.add(trait)
            if notify_client:
                self._rel_data.relationship.send_relationship_info()
        else:
            logger.error("Try to add non personality trait {} to Sim {}'s knowledge about to Sim {}", trait, self._rel_data.sim_id, self._rel_data.target_sim_id)

    @property
    def known_traits(self):
        if self._known_traits is None:
            return ()
        return self._known_traits

    @property
    def knows_career(self):
        return self._knows_career

    def add_knows_career(self, notify_client=True):
        self._knows_career = True
        if notify_client:
            self._rel_data.relationship.send_relationship_info()

    def remove_knows_career(self, notify_client=True):
        self._knows_career = False
        if notify_client:
            self._rel_data.relationship.send_relationship_info()

    def get_known_careers(self):
        if self._knows_career:
            target_sim_info = self._rel_data.find_target_sim_info()
            if target_sim_info is not None:
                if target_sim_info.career_tracker.has_career:
                    careers = tuple(career for career in target_sim_info.careers.values() if career.is_visible_career)
                    if careers:
                        return careers
                if target_sim_info.career_tracker.retirement is not None:
                    return (target_sim_info.career_tracker.retirement,)
                else:
                    return (CareerUnemployment(target_sim_info),)
        return ()

    def get_known_careertrack_ids(self):
        return (career_track.current_track_tuning.guid64 for career_track in self.get_known_careers())

    def add_known_stat(self, stat, notify_client=True):
        if self._known_stats is None:
            self._known_stats = set()
        self._known_stats.add(stat)
        if notify_client:
            self._rel_data.relationship.send_relationship_info()

    def get_known_stats(self):
        return self._known_stats

    def get_save_data(self):
        save_data = protocols.SimKnowledge()
        for trait in self.known_traits:
            save_data.trait_ids.append(trait.guid64)
        save_data.knows_career = self._knows_career
        if self._known_stats is not None:
            for stat in self._known_stats:
                save_data.stats.append(stat.guid64)
        return save_data

    def load_knowledge(self, save_data):
        trait_manager = services.get_instance_manager(sims4.resources.Types.TRAIT)
        stat_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
        for trait_inst_id in save_data.trait_ids:
            trait = trait_manager.get(trait_inst_id)
            if trait is not None:
                if self._known_traits is None:
                    self._known_traits = set()
                self._known_traits.add(trait)
        for stat_id in save_data.stats:
            if self._known_stats is None:
                self._known_stats = set()
            stat = stat_manager.get(stat_id)
            if stat is not None:
                self._known_stats.add(stat)
        self._knows_career = save_data.knows_career
