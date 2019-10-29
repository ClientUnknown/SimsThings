import objects.doors.doorimport servicesimport sims4.commands
@sims4.commands.Command('door.recalculate_front_door')
def recalculate_front_door(_connection=None):
    services.get_door_service().fix_up_doors(force_refresh=True)
    door = services.get_door_service().get_front_door()
    if door is None:
        sims4.commands.output('No valid front door found', _connection)
    else:
        sims4.commands.output('Front door found.  Door {} on position {}'.format(str(door), door.position), _connection)

@sims4.commands.Command('door.set_front_door')
def set_front_door(obj_id:int, _connection=None):
    door = services.object_manager().get(obj_id)
    if door is not None and isinstance(door, objects.doors.door.Door) and door.is_door_portal:
        services.get_door_service().set_as_front_door(door)
        sims4.commands.output('Object {} set as front door'.format(str(door)), _connection)
    else:
        sims4.commands.output('Object {} is not a door, no door will be set'.format(str(door)), _connection)

@sims4.commands.Command('door.validate_front_door')
def validate_front_door(_connection=None):
    active_lot = services.active_lot()
    if active_lot is None:
        return
    door = services.get_door_service().get_front_door()
    if door is None:
        sims4.commands.output('Lot has no front door set', _connection)
    else:
        sims4.commands.output('Front door found.  Door {} on position {}'.format(str(door), door.position), _connection)
