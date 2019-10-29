from plex.plex_enums import PlexBuildingTypeimport servicesimport sims4.commands
@sims4.commands.Command('plex.print_plex_zones')
def print_plex_zones(_connection=None):
    plex_service = services.get_plex_service()
    for (zone_id, master_id) in plex_service.zone_to_master_map_gen():
        sims4.commands.output('Zone Id: {}, Master Id: {}'.format(zone_id, master_id), _connection)

@sims4.commands.Command('plex.print_plex_rents')
def print_plex_rents(_connection=None):
    persistence_service = services.get_persistence_service()
    plex_service = services.get_plex_service()
    for (zone_id, _) in plex_service.zone_to_master_map_gen():
        house_description_id = persistence_service.get_house_description_id(zone_id)
        rent = services.get_rent(house_description_id)
        sims4.commands.output('Zone Id: {}, Rent: {}'.format(zone_id, rent), _connection)

@sims4.commands.Command('plex.print_plex_types')
def print_plex_types(_connection=None):
    persistence_service = services.get_persistence_service()
    plex_service = services.get_plex_service()
    for (zone_id, _) in plex_service.zone_to_master_map_gen():
        house_description_id = persistence_service.get_house_description_id(zone_id)
        building_type = PlexBuildingType(services.get_building_type(house_description_id))
        sims4.commands.output('Zone Id: {}, Rent: {}'.format(zone_id, building_type), _connection)
