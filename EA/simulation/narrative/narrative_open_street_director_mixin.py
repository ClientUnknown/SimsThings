from event_testing.test_events import TestEventfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableMapping, TunableReference, TunableSetimport servicesNARRATIVE_LAYERS_TOKEN = 'narrative_layers'
class NarrativeOpenStreetDirectorMixin:
    INSTANCE_TUNABLES = {'narrative_object_layers': TunableMapping(description='\n            If defined for a narrative, associated conditional layers will be\n            activated while that narrative is active.\n            \n            The layers should be exclusively owned by the narrative system\n            and should not be toggled on/off by any other means. \n            ', key_type=TunableReference(manager=services.get_instance_manager(Types.NARRATIVE), pack_safe=True), value_type=TunableSet(description='\n                List of conditional layers that should be active while the\n                specified narrative is active.\n                ', tunable=TunableReference(manager=services.get_instance_manager(Types.CONDITIONAL_LAYER), pack_safe=True)))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._narrative_layers = set()

    def on_startup(self):
        super().on_startup()
        self._handle_narratives_updated(from_startup=True)
        services.get_event_manager().register_single_event(self, TestEvent.NarrativesUpdated)

    def on_shutdown(self):
        services.get_event_manager().unregister_single_event(self, TestEvent.NarrativesUpdated)
        super().on_shutdown()

    def _load_custom_open_street_director(self, street_director_proto, reader):
        self._narrative_layers.clear()
        if reader is not None:
            layer_tuning_mgr = services.get_instance_manager(Types.CONDITIONAL_LAYER)
            for layer_guid in reader.read_uint64s(NARRATIVE_LAYERS_TOKEN, ()):
                layer = layer_tuning_mgr.get(layer_guid)
                if layer.client_only:
                    pass
                elif layer is not None:
                    self._narrative_layers.add(layer)
        super()._load_custom_open_street_director(street_director_proto, reader)

    def _save_custom_open_street_director(self, street_director_proto, writer):
        writer.write_uint64s(NARRATIVE_LAYERS_TOKEN, tuple(layer.guid64 for layer in self._narrative_layers if not layer.client_only))
        super()._save_custom_open_street_director(street_director_proto, writer)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.NarrativesUpdated:
            self._handle_narratives_updated()

    def _handle_narratives_updated(self, from_startup=False):
        required_layers = set()
        active_narratives = services.narrative_service().active_narratives
        for narrative in (n for n in self.narrative_object_layers if n in active_narratives):
            required_layers.update(self.narrative_object_layers[narrative])
        current_layers = set(self._narrative_layers)
        shut_down_layers = current_layers - required_layers
        start_up_layers = required_layers - current_layers
        load_layer_func = self.load_layer_immediately if from_startup else self.load_layer_gradually
        for layer in shut_down_layers:
            self.remove_layer_objects(layer)
        self._narrative_layers.update(start_up_layers)
        for layer in start_up_layers:
            load_layer_func(layer)

    def on_layer_objects_destroyed(self, conditional_layer):
        super().on_layer_objects_destroyed(conditional_layer)
        if conditional_layer in self._narrative_layers:
            self._narrative_layers.remove(conditional_layer)
