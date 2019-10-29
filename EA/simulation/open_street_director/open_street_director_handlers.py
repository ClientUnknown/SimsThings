from sims4.gsi.dispatcher import GsiHandlerfrom sims4.gsi.schema import GsiGridSchemaimport servicesopen_street_director_manager_schema = GsiGridSchema(label='Open Street Director Manager')open_street_director_manager_schema.add_field('request', label='Request')open_street_director_manager_schema.add_field('active', label='Active')open_street_director_manager_schema.add_field('state', label='State')open_street_director_manager_schema.add_field('priority', label='Priority')open_street_director_manager_schema.add_field('factory', label='Factory')
@GsiHandler('open_street_director_manager', open_street_director_manager_schema)
def generate_conditional_layer_service_data(zone_id:int=None):
    open_street_director_request_data = []
    zone_director = services.venue_service().get_zone_director()
    if zone_director is None:
        return open_street_director_request_data
    open_street_director_manager = zone_director.open_street_manager
    if open_street_director_manager is None:
        return open_street_director_request_data
    for request in open_street_director_manager.get_all_open_street_director_requests():
        open_street_director_request_data.append({'request': str(request), 'active': str(open_street_director_manager.is_request_active(request)), 'state': request._state.name, 'priority': request.priority.name, 'factory': str(request.is_factory)})
    return open_street_director_request_data
