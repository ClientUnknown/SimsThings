from open_street_director.open_street_director import OpenStreetDirectorPriorityimport alarmsimport enumimport servicesimport sims4.loglogger = sims4.log.Logger('OpenStreetDirector', default_owner='jjacobson')
class OpenStreetDirectorRequestState(enum.Int, export=False):
    CREATED = ...
    ADDED_TO_MANAGER = ...
    ACTIVE_REQUEST = ...
    SHUTDOWN = ...
    DEAD = ...

class OpenStreetDirectorRequest:

    def __init__(self, open_street_director, preroll_start_time=None, timeout=None, timeout_callback=None, premature_destruction_callback=None, priority=OpenStreetDirectorPriority.DEFAULT):
        self._open_street_director = open_street_director
        if not self.is_factory:
            self._open_street_director.request = self
        self._preroll_start_time = preroll_start_time
        self._timeout = timeout
        self._timeout_callback = timeout_callback
        self._timeout_alarm_handle = None
        self._premature_destruction_callback = premature_destruction_callback
        self._manager = None
        self._timestamp = None
        self._priority = priority
        self._state = OpenStreetDirectorRequestState.CREATED

    @property
    def is_factory(self):
        return False

    @property
    def open_street_director(self):
        return self._open_street_director

    @property
    def manager(self):
        return self._manager

    @property
    def priority(self):
        return self._priority

    def validate_request(self):
        if self._open_street_director is None:
            logger.error('{} failed to be a valid open street director request because its open street director is None.', self)
            return False
        return True

    def _timeout_alarm_callback(self, _):
        if self._timeout_callback is not None:
            self._timeout_callback()
        self.manager.withdraw_request(self)

    def on_added_to_manager(self, manager):
        if self._state != OpenStreetDirectorRequestState.CREATED:
            logger.error('Trying to add an open street director request to the manager when it is in an improper state {}', self._state)
            return
        self._state = OpenStreetDirectorRequestState.ADDED_TO_MANAGER
        self._manager = manager
        self._timestamp = services.time_service().sim_now
        if self._timeout is not None:
            self._timeout_alarm_handle = alarms.add_alarm(self, self._timeout, self._timeout_alarm_callback)

    def on_set_as_active_request(self, from_load=False, old_open_street_director_proto=None):
        if self._state != OpenStreetDirectorRequestState.ADDED_TO_MANAGER:
            logger.error('Trying to transition open street director request to being active when it is in an improper state {}', self._state)
            return
        self._state = OpenStreetDirectorRequestState.ACTIVE_REQUEST
        if self._timeout_alarm_handle is not None:
            alarms.cancel_alarm(self._timeout_alarm_handle)
            self._timeout_alarm_handle = None
        if from_load:
            if old_open_street_director_proto is not None:
                self._open_street_director.load(old_open_street_director_proto)
            if self._state == OpenStreetDirectorRequestState.DEAD:
                return
            self._open_street_director.preroll(preroll_time=self._preroll_start_time)
        self._open_street_director.on_startup()

    def shutdown(self, unexpected=False):
        if self._state == OpenStreetDirectorRequestState.SHUTDOWN:
            return
        if self._state != OpenStreetDirectorRequestState.ACTIVE_REQUEST:
            logger.error("Trying to shutdown an open street director request when it isn't active.  Current State: {}", self._state)
            return
        if unexpected and self._premature_destruction_callback is not None:
            self._premature_destruction_callback()
        self._state = OpenStreetDirectorRequestState.SHUTDOWN
        self._open_street_director.clean_up()

    def cleanup(self):
        if self._open_street_director is not None and (self._state == OpenStreetDirectorRequestState.SHUTDOWN or self._state == OpenStreetDirectorRequestState.ACTIVE_REQUEST):
            self._open_street_director.on_shutdown()
        self._state = OpenStreetDirectorRequestState.DEAD
        self._open_street_director = None
        self._preroll_start_time = None
        self._timeout = None
        self._manager = None
        self._timestamp = None
        self._premature_destruction_callback = None
        if self._timeout_alarm_handle is not None:
            alarms.cancel_alarm(self._timeout_alarm_handle)
            self._timeout_alarm_handle = None

    def on_open_director_shutdown(self):
        if self._state == OpenStreetDirectorRequestState.DEAD:
            return
        if self._state != OpenStreetDirectorRequestState.SHUTDOWN and self._state != OpenStreetDirectorRequestState.ACTIVE_REQUEST:
            logger.error('Open street director shut down when request was in an improper state, {}', self._state)
        self._manager.on_request_finished_shutting_down(self)

    def request_destruction(self):
        self._manager.withdraw_request(self)

class OpenStreetDirectorRequestFactory(OpenStreetDirectorRequest):

    def __init__(self, open_street_director_factory, **kwargs):
        super().__init__(*(None,), **kwargs)
        self._open_street_director_factory = open_street_director_factory

    @property
    def is_factory(self):
        return True

    def validate_request(self):
        if self._open_street_director_factory is None:
            logger.error('{} failed to be a valid open street director request because it has no factory method.', self)
            return False
        return True

    def get_request(self):
        try:
            open_street_director = self._open_street_director_factory()
        except Exception:
            logger.exception('Exception while trying to create open street director from factory.')
            return
        request = OpenStreetDirectorRequest(open_street_director, preroll_start_time=self._preroll_start_time, timeout=self._timeout, timeout_callback=self._timeout_callback, priority=self._priority)
        request.on_added_to_manager(self._manager)
        return request

    def cleanup(self):
        super().cleanup()
        self._open_street_director_factory = None
