from singletons import DEFAULTimport servicesimport sims4
@sims4.commands.Command('curfew.set_curfew', command_type=sims4.commands.CommandType.Live)
def set_curfew(time:int, zone_id=DEFAULT, _connection=None):
    if zone_id is DEFAULT:
        zone_id = services.current_zone_id()
    curfew_service = services.get_curfew_service()
    curfew_service.set_zone_curfew(zone_id, time)

@sims4.commands.Command('curfew.print_zones_curfew', command_type=sims4.commands.CommandType.Live)
def print_zones_curfew(zone_id=DEFAULT, _connection=None):
    if zone_id is DEFAULT:
        zone_id = services.current_zone_id()
    curfew_service = services.get_curfew_service()
    curfew_setting = curfew_service.get_zone_curfew(zone_id)
    sims4.commands.output('The curfew setting for zone {} is {}'.format(zone_id, curfew_setting), _connection)
