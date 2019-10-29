from open_street_director.jungle_open_street_director import JungleOpenStreetDirectorfrom sims4.commands import CommandTypefrom temple.temple_tuning import TempleTuningfrom temple.temple_utils import TempleUtilsimport servicesimport sims4.commandsTEMPLE_NAME_LOOKUP = {181306: 'Temple of Abundance', 181307: 'Pristine Temple', 185848: 'Temple of Death', 185849: 'Digsite Temple', 185850: 'Party Temple'}
def _get_jungle_open_street_director():
    venue_service = services.venue_service()
    if venue_service is None:
        return
    zone_director = venue_service.get_zone_director()
    if zone_director is None:
        return
    open_street_director = zone_director.open_street_director
    if open_street_director is None:
        return
    elif not isinstance(open_street_director, JungleOpenStreetDirector):
        return
    return open_street_director

@sims4.commands.Command('temple.unlock_next_room', command_type=CommandType.Live)
def unlock_next_temple_room(_connection=None):
    zone_director = TempleUtils.get_temple_zone_director()
    if zone_director is None:
        sims4.commands.output('You need to be at a temple for this command to work.')
        return False
    zone_director.unlock_next_room()

@sims4.commands.Command('temple.show_room', command_type=CommandType.DebugOnly)
def show_temple_room(room_number:int, show:bool, _connection=None):
    zone_director = TempleUtils.get_temple_zone_director()
    if zone_director is None:
        sims4.commands.output('You need to be at a temple for this command to work.')
        return False
    zone_director.show_room(room_number, show)

@sims4.commands.Command('temple.force_reset', command_type=CommandType.DebugOnly)
def force_reset_temple(temple_id:int=None, _connection=None):
    open_street_director = _get_jungle_open_street_director()
    if open_street_director is None:
        sims4.commands.output('You need to be in a zone attached to the Jungle Open Street Director (the North half of the Jungle world).', _connection)
        return False
    if temple_id is not None and temple_id == open_street_director.current_temple_id:
        sims4.commands.output("You're trying to reset temple {0} with {0}. Temples must be different between resets.".format(temple_id), _connection)
        return False
    open_street_director.reset_temple(new_id=temple_id, force=True)
    new_temple_id = open_street_director.current_temple_id
    sims4.commands.output('Temple reset to ID: {}, {}.'.format(new_temple_id, TEMPLE_NAME_LOOKUP.get(new_temple_id, 'UNKNOWN TEMPLE')), _connection)
    if temple_id is not None:
        sims4.commands.output('If this is not the ID you requested, you probably entered an invalid ID. Use |temple.list to get a list of valid IDs.', _connection)

@sims4.commands.Command('temple.list', command_type=CommandType.DebugOnly)
def list_temples(_connection=None):
    for temple_id in TempleTuning.TEMPLES.keys():
        sims4.commands.output('{} - {}'.format(temple_id, TEMPLE_NAME_LOOKUP.get(temple_id, 'UNKNOWN TEMPLE')), _connection)

@sims4.commands.Command('temple.current_id', command_type=CommandType.DebugOnly)
def current_temple_id(_connection=None):
    open_street_director = _get_jungle_open_street_director()
    if open_street_director is None:
        sims4.commands.output('You need to be in a zone attached to the Jungle Open Street Director (the North half of the Jungle world).', _connection)
        return False
    temple_id = open_street_director.current_temple_id
    sims4.commands.output('{} - {}'.format(temple_id, TEMPLE_NAME_LOOKUP.get(temple_id, 'UNKNOWN TEMPLE')), _connection)
