from gsi_handlers.gameplay_archiver import GameplayArchiverfrom gsi_handlers.gsi_utils import format_enum_namefrom performance.performance_commands import get_sim_info_creation_sourcesfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport servicessim_info_lifetime_archive_schema = GsiGridSchema(label='Sim Info Lifetime Archive', sim_specific=False)sim_info_lifetime_archive_schema.add_field('game_time', label='Game/Sim Time', type=GsiFieldVisualizers.TIME)sim_info_lifetime_archive_schema.add_field('total_sim_info_count', label='Total Sim Infos', type=GsiFieldVisualizers.INT)sim_info_lifetime_archive_schema.add_field('event_type', label='Event Type', type=GsiFieldVisualizers.STRING)sim_info_lifetime_archive_schema.add_field('sim_id', label='Sim ID', type=GsiFieldVisualizers.INT)sim_info_lifetime_archive_schema.add_field('sim_name', label='Sim Name', type=GsiFieldVisualizers.STRING)sim_info_lifetime_archive_schema.add_field('creation_source', label='Creation Source', type=GsiFieldVisualizers.STRING)sim_info_lifetime_archive_schema.add_field('situations', label='Situations', type=GsiFieldVisualizers.STRING)sim_info_lifetime_archive_schema.add_field('household_id', label='Household Id', type=GsiFieldVisualizers.INT)sim_info_lifetime_archive_schema.add_field('household_name', label='Household Name', type=GsiFieldVisualizers.STRING)with sim_info_lifetime_archive_schema.add_has_many('creation_sources', GsiGridSchema) as sub_schema:
    sub_schema.add_field('creation_source', label='Creation Source')
    sub_schema.add_field('count', label='Count', type=GsiFieldVisualizers.INT)archiver = GameplayArchiver('sim_info_lifetime', sim_info_lifetime_archive_schema, add_to_archive_enable_functions=True, enable_archive_by_default=True)
def is_archive_enabled():
    return archiver.enabled

def archive_sim_info_event(sim_info, event_type):
    sim_info_manager = services.sim_info_manager()
    if sim_info_manager is None:
        return
    if sim_info is None:
        return
    household = sim_info.household
    household_id = household.id if household is not None else 0
    total_sim_info_count = len(sim_info_manager.values())
    entry = {'game_time': str(services.time_service().sim_now), 'total_sim_info_count': str(total_sim_info_count), 'event_type': event_type, 'sim_id': str(sim_info.id), 'sim_name': sim_info.full_name, 'creation_source': format_enum_name(sim_info.creation_source), 'situations': sim_info.debug_get_current_situations_string(), 'household_id': str(household_id), 'household_name': str(household.name) if household is not None else 'NO HOUSEHOLD'}
    creation_source_info = []
    entry['creation_sources'] = creation_source_info
    creation_sources_and_counts = get_sim_info_creation_sources()
    for (source, count) in creation_sources_and_counts.items():
        creation_source_entry = {'creation_source': source, 'count': str(count)}
        creation_source_info.append(creation_source_entry)
    archiver.archive(entry)
