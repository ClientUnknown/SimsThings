import cameraimport servicesimport sims4.commandsimport sims4.math
@sims4.commands.Command('update.camera.information', command_type=sims4.commands.CommandType.Live)
def update_camera_information(sim_id:int=None, target_x:float=None, target_y:float=None, target_z:float=None, camera_x:float=None, camera_y:float=None, camera_z:float=None, follow_mode:bool=None, _connection=None):
    camera.update(sim_id=sim_id, target_position=sims4.math.Vector3(target_x, target_y, target_z), camera_position=sims4.math.Vector3(camera_x, camera_y, camera_z), follow_mode=follow_mode)

@sims4.commands.Command('camera.focus_on_position')
def focus_on_position(x:float, y:float, z:float, _connection=None):
    pos = sims4.math.Vector3(x, y, z)
    client = services.client_manager().get(_connection)
    camera.focus_on_position(pos, client)
    sims4.commands.output('focus on position: {}, {}, {}'.format(x, y, z), _connection)

@sims4.commands.Command('camera.shake')
def shake_camera(duration:float, frequency:float=None, amplitude:float=None, octaves:int=None, fade_multiplier:float=None, _connection=None):
    camera.shake_camera(duration, frequency=frequency, amplitude=amplitude, octaves=octaves, fade_multiplier=fade_multiplier)
