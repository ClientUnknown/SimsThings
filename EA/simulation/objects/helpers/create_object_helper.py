from element_utils import build_critical_section_with_finallyfrom objects.system import create_objectimport servicesimport sims4.loglogger = sims4.log.Logger('CreateObjectHelper')
class CreateObjectHelper:
    __slots__ = ('_object', '_claimed', '_reserver', 'sim', 'def_id', 'tag', 'create_kwargs', '_object_to_clone', '_object_cleaned_up')

    def __init__(self, sim, definition, reserver, tag='(no tag)', object_to_clone=None, **create_kwargs):
        self._object = None
        self._claimed = False
        self._reserver = reserver
        self.sim = sim
        self.def_id = definition
        self.tag = tag
        self._object_to_clone = object_to_clone
        self.create_kwargs = create_kwargs
        self._object_cleaned_up = False

    def __call__(self):
        return self.object

    def create_object(self):
        if self._object_to_clone is not None:
            self._object = self._object_to_clone.clone(definition_override=self.def_id, **self.create_kwargs)
        else:
            if self.def_id is None:
                raise RuntimeError('Trying to create object with None definition from interaction: {} tag: {}'.format(self._reserver, self.tag))
            if 'obj_id' in self.create_kwargs and self.create_kwargs['obj_id'] is None:
                raise RuntimeError('Trying to create object with None obj_id from interaction: {} tag: {}'.format(self._reserver, self.tag))
            self._object = create_object(self.def_id, **self.create_kwargs)
        return self._object

    def create(self, *args):
        reservation_handler = None

        def _create(_):
            nonlocal reservation_handler
            self._object = self.create_object()
            if self._object is None:
                return False
            if self.sim is not None and self._reserver is not None:
                reservation_handler = self.object.get_reservation_handler(self.sim, reservation_interaction=self._reserver)
                reservation_handler.begin_reservation()
                self._reserver.map_create_target(self.object)
            return True

        def _cleanup(_):
            if self._object is not None:
                if reservation_handler is not None:
                    reservation_handler.end_reservation()
                if not self._claimed:
                    current_zone = services.current_zone()
                    if current_zone is not None and not current_zone.is_zone_shutting_down:
                        self._object.destroy(source=self.sim, cause="Created object wasn't claimed.")
                    self._object = None
                self._object_cleaned_up = True

        return build_critical_section_with_finally(_create, args, _cleanup)

    def claim(self, *_, **__):
        if self._object is None:
            raise RuntimeError('CreateObjectHelper: Attempt to claim object before it was created: {}'.format(self.tag))
        if self._claimed:
            raise RuntimeError('CreateObjectHelper: Attempt to claim object multiple times: {}'.format(self.tag))
        self._claimed = True

    @property
    def object(self):
        if self._object is None and not self._object_cleaned_up:
            raise RuntimeError('CreateObjectHelper: Attempt to get object before it was created: {}'.format(self.tag))
        return self._object

    @property
    def is_object_none(self):
        return self._object is None

    @property
    def claimed(self):
        return self._claimed
