from event_testing.test_events import TestEventimport sims4logger = sims4.log.Logger('ObjectBoundSituationMixin', default_owner='jdimailig')BOUND_OBJECT_ID = '_bound_object_id'
class ObjectBoundSituationMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        reader = self._seed.custom_init_params_reader
        self._bound_object_id = None
        if reader is not None:
            self._bound_object_id = reader.read_uint64(BOUND_OBJECT_ID, None)

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._bound_object_id is not None:
            writer.write_uint64(BOUND_OBJECT_ID, self._bound_object_id)

    def start_situation(self):
        super().start_situation()
        self._register_test_event(TestEvent.ObjectDestroyed)

    def load_situation(self):
        if not super().load_situation():
            return False
        self._register_test_event(TestEvent.ObjectDestroyed)
        return True

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.ObjectDestroyed:
            destroyed_obj = resolver.get_resolved_arg('obj')
            if self._bound_object_id is not None and self._bound_object_id == destroyed_obj.id:
                self._bound_object_id = None
                self._self_destruct()
                return

    def bind_object(self, obj):
        self._bound_object_id = obj.id

    def bind_object_id(self, obj_id):
        self._bound_object_id = obj_id

    @property
    def bound_object_id(self):
        return self._bound_object_id
