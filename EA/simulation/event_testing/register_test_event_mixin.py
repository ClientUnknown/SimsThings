import services
class RegisterTestEventMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._registered_test_events = set()

    def _register_test_event_for_keys(self, test_event, custom_keys):
        for custom_key in custom_keys:
            self._register_test_event(test_event, custom_key)

    def _register_test_event(self, test_event, custom_key=None):
        custom_key_tuple = (test_event, custom_key)
        self._registered_test_events.add(custom_key_tuple)
        services.get_event_manager().register_with_custom_key(self, test_event, custom_key)

    def _unregister_test_event(self, test_event, custom_key=None):
        custom_key_tuple = (test_event, custom_key)
        if custom_key_tuple in self._registered_test_events:
            self._registered_test_events.remove(custom_key_tuple)
            services.get_event_manager().unregister_with_custom_key(self, test_event, custom_key)

    def _unregister_for_all_test_events(self):
        for (event_type, custom_key) in self._registered_test_events:
            services.get_event_manager().unregister_with_custom_key(self, event_type, custom_key)
        self._registered_test_events.clear()
