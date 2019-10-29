from _collections import defaultdictimport itertoolsfrom relationships.relationship_bit import RelationshipBitimport servicesimport sims4.loglogger = sims4.log.Logger('Coworker', default_owner='tingyul')
class CoworkerMixin:
    COWORKER_RELATIONSHIP_BIT = RelationshipBit.TunableReference(description='\n        The relationship bit for coworkers.\n        ')

    def add_coworker_relationship_bit(self):
        if not self.has_coworkers:
            return
        sim_info_manager = services.sim_info_manager()
        for target in sim_info_manager.values():
            if self._sim_info is target:
                pass
            elif not target.career_tracker is None:
                if target.career_tracker.get_career_by_uid(self.guid64) is None:
                    pass
                else:
                    add_coworker_relationship_bit(self._sim_info, target)

    def remove_coworker_relationship_bit(self):
        if not self.has_coworkers:
            return
        for target in self.get_coworker_sim_infos_gen():
            remove_coworker_relationship_bit(self._sim_info, target)

    def get_coworker_sim_infos_gen(self):
        tracker = self._sim_info.relationship_tracker
        for target in tracker.get_target_sim_infos():
            if target is None:
                logger.callstack('SimInfos not all loaded', level=sims4.log.LEVEL_ERROR)
            elif not tracker.has_bit(target.id, self.COWORKER_RELATIONSHIP_BIT):
                pass
            else:
                yield target

def fixup_coworker_relationship_bit():
    career_map = defaultdict(list)
    sim_info_manager = services.sim_info_manager()
    for sim_info in sim_info_manager.values():
        if sim_info.career_tracker is None:
            pass
        else:
            for career in sim_info.careers.values():
                if not career.has_coworkers:
                    pass
                else:
                    career_map[career.guid64].append(sim_info)
    for coworkers in career_map.values():
        for (a, b) in itertools.combinations(coworkers, 2):
            if a is b:
                pass
            elif not a.relationship_tracker.has_bit(b.id, CoworkerMixin.COWORKER_RELATIONSHIP_BIT):
                add_coworker_relationship_bit(a, b)

def add_coworker_relationship_bit(a, b):
    a.relationship_tracker.add_relationship_bit(b.id, CoworkerMixin.COWORKER_RELATIONSHIP_BIT)

def remove_coworker_relationship_bit(a, b):
    a.relationship_tracker.remove_relationship_bit(b.id, CoworkerMixin.COWORKER_RELATIONSHIP_BIT)
