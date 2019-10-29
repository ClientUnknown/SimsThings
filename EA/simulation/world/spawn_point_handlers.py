from sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersfrom tag import Tagimport servicesschema = GsiGridSchema(label='Spawn Points')schema.add_field('id', label='id', unique_field=True, width=2, type=GsiFieldVisualizers.STRING)schema.add_field('name', label='name', type=GsiFieldVisualizers.STRING, width=3)schema.add_field('x', label='x', type=GsiFieldVisualizers.FLOAT, width=2)schema.add_field('y', label='y', type=GsiFieldVisualizers.FLOAT, width=2)schema.add_field('z', label='z', type=GsiFieldVisualizers.FLOAT, width=2)schema.add_field('lot_id', label='lot_id', type=GsiFieldVisualizers.INT, width=3)schema.add_field('tags', label='tags', type=GsiFieldVisualizers.STRING, width=4)schema.add_view_cheat('debugvis.spawn_points.start', label='Start Visualization')schema.add_view_cheat('debugvis.spawn_points.stop', label='Stop Visualization')with schema.add_cheat('camera.focus_on_position', label='Focus', dbl_click=True) as cheat:
    cheat.add_token_param('x')
    cheat.add_token_param('y')
    cheat.add_token_param('z')
@GsiHandler('spawn_point', schema)
def generate_spawn_point_data(*args, zone_id:int=None, **kwargs):
    data = []
    zone = services.current_zone()
    if zone is None:
        return data
    for spawn_point in zone.spawn_points_gen():
        entry = {}
        entry['id'] = str(spawn_point.spawn_point_id)
        entry['name'] = spawn_point.get_name()
        center = spawn_point.get_approximate_center()
        entry['x'] = center.x
        entry['y'] = center.y
        entry['z'] = center.z
        entry['lot_id'] = spawn_point.lot_id

        def get_tag_name(tag):
            if not isinstance(tag, Tag):
                tag = Tag(tag)
            return tag.name

        entry['tags'] = ','.join(get_tag_name(tag) for tag in spawn_point.get_tags())
        data.append(entry)
    return data
