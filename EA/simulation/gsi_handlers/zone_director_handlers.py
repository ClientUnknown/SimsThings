from gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.schema import GsiGridSchemaimport serviceszone_director_schema = GsiGridSchema(label='Zone Director')zone_director_schema.add_field('zone_director_type', label='Zone Director Type')zone_director_schema.add_field('zone_id', label='Zone Id')zone_director_schema.add_field('op', label='Op')zone_director_schema.add_field('neighborhood', label='Neighborhood')zone_director_schema.add_field('lot_id', label='Lot Id')zone_director_schema.add_field('venue', label='Venue')with zone_director_schema.add_has_many('lot preparations', GsiGridSchema) as sub_schema:
    sub_schema.add_field('action', label='Action')
    sub_schema.add_field('description', label='Description')with zone_director_schema.add_has_many('spawn objects', GsiGridSchema) as sub_schema:
    sub_schema.add_field('obj_id', label='Obj Id')
    sub_schema.add_field('obj_def', label='Obj Def')
    sub_schema.add_field('parent_id', label='Parent Id')
    sub_schema.add_field('position', label='Position')
    sub_schema.add_field('states', label='States')archiver = GameplayArchiver('zone_director', zone_director_schema, enable_archive_by_default=True, max_records=200, add_to_archive_enable_functions=True)
def log_zone_director_event(zone_director, zone, op, venue):
    (_, _, _, neighborhood_data) = services.current_zone_info()
    archive_data = {'zone_director_type': zone_director.instance_name, 'zone_id': zone.id, 'op': op, 'neighborhood': neighborhood_data.name, 'lot_id': zone.lot.lot_id, 'venue': type(venue).__name__}
    archive_data['lot preparations'] = []
    archive_data['spawn objects'] = []
    archiver.archive(archive_data)

def log_lot_preparations(zone_director, zone, venue, lot_preparation_log):
    (_, _, _, neighborhood_data) = services.current_zone_info()
    archive_data = {'zone_director_type': zone_director.instance_name, 'zone_id': zone.id, 'op': 'prepare lot', 'neighborhood': neighborhood_data.name, 'lot_id': zone.lot.lot_id, 'venue': type(venue).__name__}
    archive_data['lot preparations'] = lot_preparation_log
    archive_data['spawn objects'] = []
    archiver.archive(archive_data)

def log_spawn_objects(zone_director, zone, venue, spawn_objects_log):
    (_, _, _, neighborhood_data) = services.current_zone_info()
    archive_data = {'zone_director_type': zone_director.instance_name, 'zone_id': zone.id, 'op': 'spawn objects', 'neighborhood': neighborhood_data.name, 'lot_id': zone.lot.lot_id, 'venue': type(venue).__name__}
    archive_data['lot preparations'] = []
    archive_data['spawn objects'] = spawn_objects_log
    archiver.archive(archive_data)
