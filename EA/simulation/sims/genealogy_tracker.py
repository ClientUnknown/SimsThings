from _sims4_collections import frozendictfrom contextlib import contextmanagerimport collectionsfrom protocolbuffers import SimObjectAttributes_pb2 as protocolsfrom distributor.rollback import ProtocolBufferRollbackfrom interactions.utils.death import DeathTypefrom sims import sim_info_utilsfrom sims.sim_info_lod import SimInfoLODLevelfrom sims.sim_info_tracker import SimInfoTrackerfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableList, TunableReference, TunableEnumEntryfrom sims4.utils import classpropertyimport enumimport servicesimport sims4.loglogger = sims4.log.Logger('Genealogy')
class FamilyRelationshipIndex(enum.Int):
    MOTHER = 0
    FATHER = 1
    MOTHERS_MOM = 2
    MOTHERS_FATHER = 3
    FATHERS_MOM = 4
    FATHERS_FATHER = 5
_genealogy_cache = None
@contextmanager
def genealogy_caching():
    global _genealogy_cache
    if _genealogy_cache is not None:
        yield None
    else:
        _genealogy_cache = collections.defaultdict(set)
        sim_info_manager = services.sim_info_manager()
        for (sim_id, sim_info) in sim_info_manager.items():
            for parent_id in sim_info.genealogy.get_parent_sim_ids_gen():
                _genealogy_cache[parent_id].add(sim_id)
        try:
            yield None
        finally:
            _genealogy_cache = None

class FamilyRelationshipTuning:
    MATRIX = TunableList(description="\n        This matrix is mirrored in RelationshipHelper.cpp in CAS Systems code.\n        Please discuss with a GPE and CAS engineer if you wish to update this\n        tuning.\n                     \n                   Sim Y's ancestry depth  ----> \n            +-------------+-------------+-------------+\n            |             |             |             |\n            |   Spouse    |    Parent   | Grandparent |  Sim X's \n            |             |             |             | ancestry\n            +-------------+-------------+-------------+  depth\n            |             |             |             |    |\n            |   Child     |   Sibling   | Uncle/Aunt  |    |\n            |             |             |             |    |\n            +-------------+-------------+-------------+    V   \n            |             |             |             |\n            | Grandchild  |   Nephew    |   Cousin    |\n            |             |             |             |\n            +-------------+-------------+-------------+\n        ", tunable=TunableList(tunable=TunableReference(services.get_instance_manager(Types.RELATIONSHIP_BIT))))
    SIBLING_RELATIONSHIP_BIT = TunableReference(description="\n        A bit indicating that one Sim is another Sim's sibling.\n        ", manager=services.get_instance_manager(Types.RELATIONSHIP_BIT))
    GRANDPARENT_RELATIONSHIP_BIT = TunableReference(description="\n        A bit indicating that one Sim is another Sim's grandparent.\n        ", manager=services.get_instance_manager(Types.RELATIONSHIP_BIT))
    GRANDCHILD_RELATIONSHIP_BIT = TunableReference(description="\n        A bit indicating that one Sim is another Sim's grandchild.\n        ", manager=services.get_instance_manager(Types.RELATIONSHIP_BIT))
    DIVORCED_SPOUSE_RELATIONSHIP_BIT = TunableReference(description="\n        A bit indicating that one Sim is another Sim's estranged spouse.\n        ", manager=services.get_instance_manager(Types.RELATIONSHIP_BIT))
    DEAD_SPOUSE_RELATIONSHIP_BIT = TunableReference(description="\n        A bit indicating that one Sim is another Sim's deceased spouse.\n        ", manager=services.get_instance_manager(Types.RELATIONSHIP_BIT))

class GenealogyTracker(SimInfoTracker):

    def __init__(self, sim_info):
        self._owner_id = sim_info.id
        self._family_relations = {}
        self._ancestor_depths = None

    def set_family_relation(self, relation, sim_id):
        if sim_id == self._owner_id:
            return
        self._family_relations[relation] = sim_id
        self._ancestor_depths = None

    def get_family_relation(self, relation):
        return self._family_relations.get(relation)

    def clear_family_relation(self, relation):
        self._ancestor_depths = None
        if relation in self._family_relations:
            del self._family_relations[relation]

    def remove_family_link(self, relationship):
        if _genealogy_cache is not None and relationship in self._family_relations:
            relation_info = services.sim_info_manager().get(self._family_relations[relationship])
            if relation_info is not None:
                _genealogy_cache[relation_info.sim_id].discard(self.sim_id)

    def set_and_propagate_family_relation(self, relation, sim_info):
        if sim_info.id == self._owner_id:
            return
        self.set_family_relation(relation, sim_info.id)
        if relation == FamilyRelationshipIndex.MOTHER:
            mothers_mom = sim_info.get_relation(FamilyRelationshipIndex.MOTHER)
            if mothers_mom is not None:
                self.set_family_relation(FamilyRelationshipIndex.MOTHERS_MOM, mothers_mom)
            mothers_dad = sim_info.get_relation(FamilyRelationshipIndex.FATHER)
            if mothers_dad is not None:
                self.set_family_relation(FamilyRelationshipIndex.MOTHERS_FATHER, mothers_dad)
        elif relation == FamilyRelationshipIndex.FATHER:
            fathers_mom = sim_info.get_relation(FamilyRelationshipIndex.MOTHER)
            if fathers_mom is not None:
                self.set_family_relation(FamilyRelationshipIndex.FATHERS_MOM, fathers_mom)
            fathers_dad = sim_info.get_relation(FamilyRelationshipIndex.FATHER)
            if fathers_dad is not None:
                self.set_family_relation(FamilyRelationshipIndex.FATHERS_FATHER, fathers_dad)

    def get_family_relationship_bit(self, sim_id, output=None):
        bit = None
        sim_x = services.sim_info_manager().get(self._owner_id)
        sim_y = services.sim_info_manager().get(sim_id)
        if sim_y is None:
            if output is not None:
                output('Could not find sim_info for {}.'.format(sim_id))
            return
        x_ancestry = self._get_ancestor_family_tree()
        y_ancestry = sim_y.genealogy._get_ancestor_family_tree()
        common_ancestor_ids = x_ancestry.keys() & y_ancestry.keys()
        if common_ancestor_ids:
            closest_ancestor_id = min(common_ancestor_ids, key=lambda ancestor_id: x_ancestry[ancestor_id] + y_ancestry[ancestor_id])
            x_depth = x_ancestry[closest_ancestor_id]
            y_depth = y_ancestry[closest_ancestor_id]
            bit = FamilyRelationshipTuning.MATRIX[x_depth][y_depth]
        elif sim_x.spouse_sim_id == sim_y.sim_id:
            bit = FamilyRelationshipTuning.MATRIX[0][0]
        if output is not None:
            if bit is None:
                output('Sims {} and {} are not related.'.format(sim_x.full_name, sim_y.full_name))
            else:
                output('Sim {} is {} of Sim {}'.format(sim_x.full_name, bit, sim_y.full_name))
        return bit

    def get_parent_sim_ids_gen(self):
        if FamilyRelationshipIndex.FATHER in self._family_relations:
            yield self._family_relations[FamilyRelationshipIndex.FATHER]
        if FamilyRelationshipIndex.MOTHER in self._family_relations:
            yield self._family_relations[FamilyRelationshipIndex.MOTHER]

    def get_grandparent_sim_ids_gen(self):
        for relation in (FamilyRelationshipIndex.FATHERS_FATHER, FamilyRelationshipIndex.FATHERS_MOM, FamilyRelationshipIndex.MOTHERS_FATHER, FamilyRelationshipIndex.MOTHERS_MOM):
            if relation in self._family_relations:
                yield self._family_relations[relation]

    @sim_info_utils.sim_info_auto_finder
    def get_parent_sim_infos_gen(self):
        yield from self.get_parent_sim_ids_gen()

    def get_children_sim_ids_gen(self):
        if _genealogy_cache is not None:
            children_ids = _genealogy_cache.get(self._owner_id)
            if children_ids:
                yield from children_ids
        else:
            raise RuntimeError('Please use genealogy_caching when using get_children_sim_ids_gen')

    @sim_info_utils.sim_info_auto_finder
    def get_child_sim_infos_gen(self):
        yield from self.get_children_sim_ids_gen()

    def get_siblings_sim_ids_gen(self):

        def get_parent_children_gen(parent_id):
            if _genealogy_cache is not None:
                children_ids = _genealogy_cache.get(parent_id)
                if children_ids:
                    for child_id in children_ids:
                        if child_id != self._owner_id:
                            yield child_id
            else:
                raise RuntimeError('Please use genealogy_caching when using get_siblings_sim_ids_gen')

        for parent_id in self.get_parent_sim_ids_gen():
            yield from get_parent_children_gen(parent_id)

    @sim_info_utils.sim_info_auto_finder
    def get_siblings_sim_infos_gen(self):
        yield from self.get_siblings_sim_ids_gen()

    def get_immediate_family_sim_ids_gen(self):
        yield from self.get_parent_sim_ids_gen()
        yield from self.get_children_sim_ids_gen()
        yield from self.get_siblings_sim_ids_gen()

    def get_family_sim_ids(self, include_self=False):
        if not include_self:
            return self._family_relations.values()
        rels = list(self._family_relations.values())
        rels.append(self._owner_id)
        return rels

    def get_relation(self, relation):
        return self._family_relations.get(relation)

    def _get_ancestor_family_tree(self):
        if self._ancestor_depths is None:
            ancestor_depths = {}
            ancestor_depths[self._owner_id] = 0
            for (relation, sim_id) in self._family_relations.items():
                relation_depth = 1 if relation <= FamilyRelationshipIndex.FATHER else 2
                ancestor_depths[sim_id] = relation_depth
            self._ancestor_depths = frozendict(ancestor_depths)
        return self._ancestor_depths

    def save_genealogy(self):
        save_data = protocols.PersistableGenealogyTracker()
        for (relation, sim_id) in self._family_relations.items():
            with ProtocolBufferRollback(save_data.family_relations) as entry:
                entry.relation_type = relation
                entry.sim_id = sim_id
        return save_data

    def load_genealogy(self, genealogy_proto_msg):
        self._family_relations.clear()
        self._ancestor_depths = None
        for family_relation in genealogy_proto_msg.family_relations:
            if family_relation.sim_id == self._owner_id:
                pass
            else:
                relation_type_int = family_relation.relation_type
                try:
                    relation_type = FamilyRelationshipIndex(relation_type_int)
                except KeyError:
                    logger.error('Failed to load genealogy entry. Invalid to family_relation {} for sim {} to sim_id {}.', relation_type_int, self._owner_id, family_relation.sim_id)
                    continue
                self.set_family_relation(relation_type, family_relation.sim_id)

    def log_contents(self):
        with genealogy_caching():
            self._log_contents()

    def _log_contents(self):
        sim_info_manager = services.sim_info_manager()

        def get_full_name(sim_id):
            if sim_id not in sim_info_manager:
                return '<Pruned>'
            sim_info = sim_info_manager.get(sim_id)
            return '{} {}'.format(sim_info.first_name, sim_info.last_name)

        current = (self._owner_id, 1)

        def set_parent_node(relationship_index):
            nonlocal current
            if current[0] in sim_info_manager:
                sim_info = sim_info_manager.get(current[0])
                parent_ids = tuple(sim_info.genealogy.get_parent_sim_ids_gen())
                if len(parent_ids) > relationship_index:
                    current = (parent_ids[relationship_index], current[1] + 1)
                    return
            current = None

        nodes = []
        while True:
            if nodes or current:
                if current:
                    nodes.append(current)
                    set_parent_node(FamilyRelationshipIndex.MOTHER)
                else:
                    current = nodes.pop()
                    logger.error('\t'*current[1] + get_full_name(current[0]))
                    set_parent_node(FamilyRelationshipIndex.FATHER)

    @classproperty
    def _tracker_lod_threshold(cls):
        return SimInfoLODLevel.MINIMUM
