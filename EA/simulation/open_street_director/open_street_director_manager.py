from conditional_layers.conditional_layer_service import ConditionalLayerRequestSpeedTypefrom open_street_director.open_street_director import OpenStreetDirectorPriority, OpenStreetDirectorBaseimport servicesimport sims4.loglogger = sims4.log.Logger('OpenStreetDirector', default_owner='jjacobson')
class OpenStreetDirectorManager:

    def __init__(self, prior_open_street_director_proto=None):
        self._active = False
        self._active_open_street_director_request = None
        self._open_street_director_requests = []
        for _ in range(len(OpenStreetDirectorPriority)):
            self._open_street_director_requests.append([])
        self._prior_open_street_director_proto = prior_open_street_director_proto
        if self._prior_open_street_director_proto is not None:
            conditional_layer_manager = services.get_instance_manager(sims4.resources.Types.CONDITIONAL_LAYER)
            conditional_layers = conditional_layer_manager.types.values()
            for layer in self._prior_open_street_director_proto.loaded_layers:
                for conditional_layer in conditional_layers:
                    if layer == conditional_layer.layer_name:
                        self._prior_open_street_director_proto.loaded_layer_guids.append(conditional_layer.guid64)
                        break
            del self._prior_open_street_director_proto.loaded_layers[:]

    @property
    def open_street_director(self):
        if self._active_open_street_director_request is None:
            return
        return self._active_open_street_director_request.open_street_director

    @property
    def active(self):
        return self._active

    def get_all_open_street_director_requests(self):
        open_street_director_requests = [request for requests in self._open_street_director_requests for request in requests]
        if self._active_open_street_director_request is not None:
            open_street_director_requests.append(self._active_open_street_director_request)
        return open_street_director_requests

    def is_request_active(self, request):
        return request is self._active_open_street_director_request

    def _pop_next_request(self):
        for requests in reversed(self._open_street_director_requests):
            if not requests:
                pass
            else:
                request = requests[-1]
                if request.is_factory:
                    return request.get_request()
                return requests.pop()

    def on_request_finished_shutting_down(self, request):
        if request is self._active_open_street_director_request:
            request.cleanup()
            self._active_open_street_director_request = None
            new_request = self._pop_next_request()
            if new_request is not None:
                self._set_active_request(new_request)
        else:
            self.withdraw_request(request)

    def cleanup_old_open_street_director(self):
        if self._prior_open_street_director_proto is None:
            return
        conditional_layer_service = services.conditional_layer_service()
        conditional_layer_manager = services.get_instance_manager(sims4.resources.Types.CONDITIONAL_LAYER)
        for layer_guid in self._prior_open_street_director_proto.loaded_layer_guids:
            layer = conditional_layer_manager.get(layer_guid)
            if layer is not None:
                conditional_layer_service.destroy_conditional_layer(layer)
        if self._prior_open_street_director_proto.HasField('resource_key'):
            previous_resource_key = sims4.resources.get_key_from_protobuff(self._prior_open_street_director_proto.resource_key)
            if previous_resource_key is not None:
                open_street_director_type = services.get_instance_manager(sims4.resources.Types.OPEN_STREET_DIRECTOR).get(previous_resource_key.instance)
                if open_street_director_type is not None:
                    open_street_director_type.run_lot_cleanup()

    def activate(self, from_load=False):
        if self._active:
            logger.error('Trying to activate open street manager that is already active.')
            return
        self._active = True
        request = self._pop_next_request()
        if request is None:
            if from_load:
                self.cleanup_old_open_street_director()
        elif from_load:
            self._set_active_request(request, from_load=from_load)
        else:
            self._switch_open_street_directors(request)
        self._prior_open_street_director_proto = None

    def deactivate(self, from_load=False):
        if from_load:
            self.cleanup_old_open_street_director()
            return
        if not self._active:
            logger.error('Trying to deactivate open street manager that is already inactive.')
            return
        self._active = False
        self.shutdown_active_request(unexpected=True)

    def _can_request_displace_active_request(self, request):
        if self._active_open_street_director_request is None:
            return True
        return request.priority >= self._active_open_street_director_request.priority

    def _set_active_request(self, request, from_load=False):
        if not self._active:
            return
        if self._active_open_street_director_request is not None:
            self._active_open_street_director_request.cleanup()
        if request.is_factory:
            request = request.get_request()
        if request is None:
            logger.error('Trying to set None as active request.  This will probably cause the open street directors to stop functioning until a new one is requested.')
            return
        if not request.validate_request():
            logger.error('Trying to set request {} as the active request when it is not valid.', request)
            return
        self._active_open_street_director_request = request
        self._active_open_street_director_request.on_set_as_active_request(from_load=from_load, old_open_street_director_proto=self._prior_open_street_director_proto)

    def _switch_open_street_directors(self, request):
        if self._active_open_street_director_request is None:
            self._set_active_request(request)
        else:
            self.shutdown_active_request(unexpected=True)

    def add_open_street_director_request(self, request):
        if not request.validate_request():
            logger.error('Trying to add invalid request {} to the open street manager.', request)
            return
        self._open_street_director_requests[request.priority].append(request)
        request.on_added_to_manager(self)
        if self._can_request_displace_active_request(request):
            self._switch_open_street_directors(request)

    def shutdown_active_request(self, unexpected=False):
        if self._active_open_street_director_request is None:
            return
        self._active_open_street_director_request.shutdown(unexpected=unexpected)

    def withdraw_request(self, request):
        for requests in self._open_street_director_requests:
            if request in requests:
                requests.remove(request)
        if request is self._active_open_street_director_request:
            self.shutdown_active_request()
        else:
            request.cleanup()

    def destroy_all_requests(self):
        for requests in self._open_street_director_requests:
            for request in requests:
                request.cleanup()
        self._open_street_director_requests.clear()
        if self._active_open_street_director_request is not None:
            self._active_open_street_director_request.cleanup()
            self._active_open_street_director_request = None
