from gsi_handlers.object_handlers import _get_model_namefrom objects.components.types import GARDENING_COMPONENTfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemaimport gsi_handlersimport servicesgardening_schema = GsiGridSchema(label='Gardening', auto_refresh=False)gardening_schema.add_field('object_id', label='Object Id', width=1, unique_field=True)gardening_schema.add_field('class', label='Class', width=3)gardening_schema.add_field('definition', label='Definition', width=3)gardening_schema.add_field('model', label='Model', width=3)gardening_schema.add_field('root_stock', label='Root Stock', width=5)with gardening_schema.add_has_many('fruit_spawners', GsiGridSchema) as spawn_data_schema:
    spawn_data_schema.add_field('spawn_definition', label='Spawner Definition', width=3)
    spawn_data_schema.add_field('spawn_weight', label='Spawner Weight', width=1)with gardening_schema.add_view_cheat('objects.focus_camera_on_object', label='Focus On Selected Object') as cheat:
    cheat.add_token_param('object_id')
@GsiHandler('gardening_objects', gardening_schema)
def generate_gardening_objects_data(*args, **kwargs):
    gardening_data = []
    for gardening_object in services.object_manager().get_all_objects_with_component_gen(GARDENING_COMPONENT):
        spawn_data_entry = []
        for spawn_data in gardening_object.gardening_component.fruit_spawners:
            spawn_data_entry.append({'spawn_definition': str(spawn_data.main_spawner), 'spawn_weight': str(spawn_data.spawn_weight)})
        entry = {'object_id': hex(gardening_object.id), 'class': gsi_handlers.gsi_utils.format_object_name(gardening_object), 'definition': str(gardening_object.definition.name), 'model': _get_model_name(gardening_object), 'root_stock': str(gardening_object.gardening_component.root_stock), 'fruit_spawners': spawn_data_entry}
        gardening_data.append(entry)
    return gardening_data
