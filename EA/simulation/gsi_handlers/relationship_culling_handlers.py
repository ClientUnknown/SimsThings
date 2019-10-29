from collections import namedtuplefrom gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport servicesrelationship_culling_archive_schema = GsiGridSchema(label='Relationship Culling Archive', sim_specific=False)relationship_culling_archive_schema.add_field('game_time', label='Game/Sim Time', type=GsiFieldVisualizers.TIME)relationship_culling_archive_schema.add_field('relationships_culled', label='Relationships Culled', type=GsiFieldVisualizers.INT)with relationship_culling_archive_schema.add_has_many('all_relationships', GsiGridSchema) as sub_schema:
    sub_schema.add_field('culled_status', label='Culled Status')
    sub_schema.add_field('culled_reason', label='Culled Reason')
    sub_schema.add_field('sim_info', label='Sim A')
    sub_schema.add_field('target_sim_info', label='Sim B')
    sub_schema.add_field('total_depth', label='Total Depth', type=GsiFieldVisualizers.INT, width=0.2)
    sub_schema.add_field('rel_bits', label='Relationship Bits')with relationship_culling_archive_schema.add_has_many('not_culled_relationships', GsiGridSchema) as sub_schema:
    sub_schema.add_field('culled_status', label='Culled Status')
    sub_schema.add_field('culled_reason', label='Culled Reason')
    sub_schema.add_field('sim_info', label='Sim A')
    sub_schema.add_field('target_sim_info', label='Sim B')
    sub_schema.add_field('total_depth', label='Total Depth', type=GsiFieldVisualizers.INT, width=0.2)
    sub_schema.add_field('rel_bits', label='Relationship Bits')with relationship_culling_archive_schema.add_has_many('culled_relationships', GsiGridSchema) as sub_schema:
    sub_schema.add_field('culled_status', label='Culled Status')
    sub_schema.add_field('culled_reason', label='Culled Reason')
    sub_schema.add_field('sim_info', label='Sim A')
    sub_schema.add_field('target_sim_info', label='Sim B')
    sub_schema.add_field('total_depth', label='Total Depth', type=GsiFieldVisualizers.INT, width=0.2)
    sub_schema.add_field('rel_bits', label='Relationship Bits')archiver = GameplayArchiver('relationship_culling', relationship_culling_archive_schema, add_to_archive_enable_functions=True, enable_archive_by_default=True)
def is_archive_enabled():
    return archiver.enabled
RelationshipGSIData = namedtuple('RelationshipGSIData', ('sim_info', 'target_sim_info', 'total_depth', 'formated_rel_bits', 'culled_status', 'culled_reason'))
def _add_rel_data(rel_data:RelationshipGSIData, relationships_data):
    rel_entry = {'sim_info': str(rel_data.sim_info), 'target_sim_info': str(rel_data.target_sim_info), 'total_depth': rel_data.total_depth, 'rel_bits': rel_data.formated_rel_bits, 'culled_status': rel_data.culled_status, 'culled_reason': rel_data.culled_reason}
    relationships_data.append(rel_entry)

def archive_relationship_culling(total_culled_count, relationship_data, culled_relationship_data):
    entry = {'relationships_culled': total_culled_count, 'game_time': str(services.time_service().sim_now)}
    all_relationship_data = relationship_data + culled_relationship_data
    all_relationaships = []
    entry['all_relationships'] = all_relationaships
    for rel_data in all_relationship_data:
        _add_rel_data(rel_data, all_relationaships)
    not_culled_relationships = []
    entry['not_culled_relationships'] = not_culled_relationships
    for rel_data in relationship_data:
        _add_rel_data(rel_data, not_culled_relationships)
    culled_relationaships = []
    entry['culled_relationships'] = culled_relationaships
    for rel_data in culled_relationship_data:
        _add_rel_data(rel_data, culled_relationaships)
    archiver.archive(entry)
