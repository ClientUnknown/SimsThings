import sims4.commandsfrom terrain import get_terrain_heightfrom routing import SurfaceIdentifier, SurfaceType
@sims4.commands.Command('world.test_surface_height', command_type=sims4.commands.CommandType.DebugOnly)
def test_surface_height(x:float=0.0, y:float=0.0, z:float=0.0, _connection=None):
    terrain_height = get_terrain_height(x, z, SurfaceIdentifier(0, 0, SurfaceType.SURFACETYPE_WORLD))
    sims4.commands.output('Terrain Surface: {}'.format(terrain_height), _connection)
    object_height = get_terrain_height(x, z, SurfaceIdentifier(0, 0, SurfaceType.SURFACETYPE_OBJECT))
    sims4.commands.output('Object Surface: {}'.format(object_height), _connection)
    water_height = get_terrain_height(x, z, SurfaceIdentifier(0, 0, SurfaceType.SURFACETYPE_POOL))
    sims4.commands.output('Water Surface: {}'.format(water_height), _connection)
    difference = water_height - terrain_height
    sims4.commands.output('Water Height: {}'.format(difference), _connection)

@sims4.commands.Command('world.get_forward', command_type=sims4.commands.CommandType.DebugOnly)
def get_forward(x1:float=0.0, y1:float=0.0, z1:float=0.0, x2:float=0.0, y2:float=0.0, z2:float=0.0, _connection=None):
    sims4.commands.output('{} {}'.format(x2 - x1, z2 - z1), _connection)
