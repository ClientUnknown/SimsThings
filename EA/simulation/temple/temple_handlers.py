from sims4.gsi.dispatcher import GsiHandler
    gates_schema.add_field('room_number', label='Room', width=1)
    gates_schema.add_field('gate_state', label='Gate State', type=GsiFieldVisualizers.STRING, width=4)
    gates_schema.add_field('trigger_object', label='Trigger Object', type=GsiFieldVisualizers.STRING, width=4)
    gates_schema.add_field('trigger_interaction', label='Trigger Interaction', type=GsiFieldVisualizers.STRING, width=4)
@GsiHandler('temple', temple_schema)
def generate_temple_view(zone_id:int=None):
    zone_director = TempleUtils.get_temple_zone_director()
    if zone_director is None:
        return ({'temple_id': 0, 'room_count': 0, 'current_room': 0},)
    temple_data = {'temple_id': zone_director._temple_id, 'room_count': zone_director.room_count, 'current_room': zone_director._current_room}
    rooms = []
    temple_data['rooms'] = rooms
    for (i, room_data) in enumerate(zone_director.room_data):
        rooms.append({'room_number': i, 'gate_state': str(room_data.gate.get_state(TempleTuning.GATE_STATE)) if room_data.gate is not None else 'None', 'trigger_object': str(room_data.trigger_object), 'trigger_interaction': str(room_data.trigger_interaction)})
    return (temple_data,)
