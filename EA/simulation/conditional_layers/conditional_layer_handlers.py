from gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchema, GsiFieldVisualizersimport date_and_timeimport enumimport servicesconditional_layer_service_schema = GsiGridSchema(label='Conditional Layers/Conditional Layer Service')conditional_layer_service_schema.add_field('conditional_layer', label='Class Name', width=1, unique_field=True)conditional_layer_service_schema.add_field('layer_hash', label='Layer Name', width=1)conditional_layer_service_schema.add_field('objects_created', label='Objects Created', width=1)conditional_layer_service_schema.add_field('requests_waiting', label='Requests Waiting', width=1)conditional_layer_service_schema.add_field('last_request', label='Last Request', width=1)with conditional_layer_service_schema.add_has_many('Objects', GsiGridSchema) as sub_schema:
    sub_schema.add_field('object_id', label='Object Id')
    sub_schema.add_field('object', label='Object')with conditional_layer_service_schema.add_has_many('Requests', GsiGridSchema) as sub_schema:
    sub_schema.add_field('request', label='Request')
    sub_schema.add_field('speed', label='Speed')
    sub_schema.add_field('timer_interval', label='Timer Interval')
    sub_schema.add_field('timer_object_count', label='Timer Object Count')
@GsiHandler('conditional_layer_service', conditional_layer_service_schema)
def generate_conditional_layer_service_data(zone_id:int=None):
    layer_data = []
    conditional_layer_service = services.conditional_layer_service()
    if conditional_layer_service is None:
        return layer_data
    object_manager = services.object_manager()
    for (conditional_layer, layer_info) in conditional_layer_service._layer_infos.items():
        object_data = []
        for object_id in layer_info.objects_loaded:
            obj = object_manager.get(object_id)
            object_data.append({'object_id': str(object_id), 'object': str(obj)})
        request_data = []
        for request in conditional_layer_service.requests:
            if request.conditional_layer is conditional_layer:
                request_data.append({'request': str(request), 'speed': request.speed.name, 'timer_interval': str(request.timer_interval), 'timer_object_count': str(request.timer_object_count)})
        layer_data.append({'layer_hash': str(conditional_layer.layer_name), 'conditional_layer': str(conditional_layer), 'objects_created': str(len(layer_info.objects_loaded)), 'requests_waiting': str(len(request_data)), 'last_request': str(layer_info.last_request_type), 'Objects': object_data, 'Requests': request_data})
    return layer_data

class LayerRequestAction(enum.Int, export=False):
    SUBMITTED = ...
    EXECUTING = ...
    COMPLETED = ...
conditional_layer_request_archive_schema = GsiGridSchema(label='Conditional Layers/Conditional Layer Request Archive', sim_specific=False)conditional_layer_request_archive_schema.add_field('game_time', label='Game/Sim Time', type=GsiFieldVisualizers.TIME)conditional_layer_request_archive_schema.add_field('request', label='Request')conditional_layer_request_archive_schema.add_field('action', label='Action')conditional_layer_request_archive_schema.add_field('layer_hash', label='Layer Hash')conditional_layer_request_archive_schema.add_field('speed', label='Speed')conditional_layer_request_archive_schema.add_field('timer_interval', label='Timer Interval')conditional_layer_request_archive_schema.add_field('timer_object_count', label='Timer Object Count')conditional_layer_request_archive_schema.add_field('objects_in_layer_count', label='Object Count')archiver = GameplayArchiver('conditional_layer_requests', conditional_layer_request_archive_schema, add_to_archive_enable_functions=True)
def is_archive_enabled():
    return archiver.enabled

def archive_layer_request_culling(request, action, objects_in_layer_count=None):
    time_service = services.time_service()
    if time_service.sim_timeline is None:
        time = 'zone not running'
    else:
        time = time_service.sim_now
    entry = {'game_type': str(time), 'request': str(request), 'action': action.name, 'layer_hash': str(hex(request.conditional_layer.layer_name)), 'speed': request.speed.name, 'timer_interval': str(request.timer_interval), 'timer_object_count': str(request.timer_object_count), 'objects_in_layer_count': str(objects_in_layer_count) if objects_in_layer_count else ''}
    archiver.archive(entry)
